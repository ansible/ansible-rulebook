#  Copyright 2022 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import asyncio
import gc
import logging
import uuid
from pprint import pformat
from types import MappingProxyType
from typing import Dict, List, Optional, Union, cast

import dpath
from drools import ruleset as lang
from drools.exceptions import (
    MessageNotHandledException,
    MessageObservedException,
)
from drools.ruleset import session_stats

from ansible_rulebook import terminal
from ansible_rulebook.action.control import Control
from ansible_rulebook.action.debug import Debug
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.action.noop import Noop
from ansible_rulebook.action.post_event import PostEvent
from ansible_rulebook.action.print_event import PrintEvent
from ansible_rulebook.action.retract_fact import RetractFact
from ansible_rulebook.action.run_job_template import RunJobTemplate
from ansible_rulebook.action.run_module import RunModule
from ansible_rulebook.action.run_playbook import RunPlaybook
from ansible_rulebook.action.run_workflow_template import RunWorkflowTemplate
from ansible_rulebook.action.set_fact import SetFact
from ansible_rulebook.action.shutdown import Shutdown as ShutdownAction
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    ShutdownException,
    UnsupportedActionException,
)
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import (
    Action,
    ActionContext,
    EngineRuleSetQueuePlan,
    ExecutionStrategy,
)
from ansible_rulebook.rules_parser import parse_hosts
from ansible_rulebook.util import (
    run_at,
    send_session_stats,
    substitute_variables,
)

logger = logging.getLogger(__name__)

ACTION_CLASSES = {
    "debug": Debug,
    "print_event": PrintEvent,
    "none": Noop,
    "set_fact": SetFact,
    "post_event": PostEvent,
    "retract_fact": RetractFact,
    "shutdown": ShutdownAction,
    "run_playbook": RunPlaybook,
    "run_module": RunModule,
    "run_job_template": RunJobTemplate,
    "run_workflow_template": RunWorkflowTemplate,
}


class RuleSetRunner:
    def __init__(
        self,
        event_log: asyncio.Queue,
        ruleset_queue_plan: EngineRuleSetQueuePlan,
        hosts_facts,
        variables,
        rule_set,
        project_data_file: Optional[str] = None,
        parsed_args=None,
        broadcast_method=None,
    ):
        self.action_loop_task = None
        self.event_log = event_log
        self.ruleset_queue_plan = ruleset_queue_plan
        self.name = ruleset_queue_plan.ruleset.name
        self.rule_set = rule_set
        self.hosts_facts = hosts_facts
        self.variables = variables
        self.project_data_file = project_data_file
        self.parsed_args = parsed_args
        self.shutdown = None
        self.active_actions = set()
        self.broadcast_method = broadcast_method
        self.event_counter = 0
        self.display = terminal.Display()

    async def run_ruleset(self):
        tasks = []
        try:
            prime_facts(self.name, self.hosts_facts)
            task_name = (
                f"action_plan_task:: {self.ruleset_queue_plan.ruleset.name}"
            )
            self.action_loop_task = asyncio.create_task(
                self._drain_actionplan_queue(), name=task_name
            )
            tasks.append(self.action_loop_task)
            task_name = (
                f"source_reader_task:: {self.ruleset_queue_plan.ruleset.name}"
            )
            self.source_loop_task = asyncio.create_task(
                self._drain_source_queue(), name=task_name
            )
            tasks.append(self.source_loop_task)
            await asyncio.wait([self.action_loop_task])
        except asyncio.CancelledError:
            logger.debug("Cancelled error caught in run_ruleset")
            for task in tasks:
                if not task.done():
                    logger.debug("Cancelling (2) task %s", task.get_name())
                    task.cancel()

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            raise

    async def _cleanup(self):
        logger.debug("Cleaning up ruleset %s", self.name)
        if not self.source_loop_task.done():
            self.source_loop_task.cancel()

        if (
            self.active_actions
            and self.shutdown
            and self.shutdown.kind == "graceful"
        ):
            logger.debug("Waiting for active actions to end")
            await asyncio.wait(
                self.active_actions,
                return_when=asyncio.FIRST_EXCEPTION,
                timeout=self.shutdown.delay,
            )

        for task in self.active_actions:
            logger.debug("Cancelling active task %s", task.get_name())
            task.cancel()
        if self.shutdown:
            await self.event_log.put(
                dict(
                    type="Shutdown",
                    message=self.shutdown.message,
                    delay=self.shutdown.delay,
                    source_plugin=self.shutdown.source_plugin,
                    kind=self.shutdown.kind,
                )
            )
        stats = lang.end_session(self.name)
        if self.parsed_args and self.parsed_args.heartbeat > 0:
            await send_session_stats(self.event_log, stats)
        logger.info(pformat(stats))

    async def _handle_shutdown(self):
        logger.info(
            "Ruleset: %s, received shutdown: %s",
            self.name,
            str(self.shutdown),
        )
        if self.shutdown.kind == "now":
            logger.debug(
                "ruleset: %s has issued an immediate shutdown", self.name
            )
            self.action_loop_task.cancel()
        elif (
            self.ruleset_queue_plan.plan.queue.empty()
            and not self.active_actions
        ):
            logger.debug("ruleset: %s shutdown no pending work", self.name)
            self.action_loop_task.cancel()
        else:
            logger.debug(
                "ruleset: %s waiting %f for shutdown",
                self.name,
                self.shutdown.delay,
            )
            await asyncio.sleep(self.shutdown.delay)
            if not self.action_loop_task.done():
                self.action_loop_task.cancel()

        return

    async def _drain_source_queue(self):
        logger.info("Waiting for events, ruleset: %s", self.name)
        try:
            while True:
                data = await self.ruleset_queue_plan.source_queue.get()
                # Default to output events at debug level.
                level = logging.DEBUG

                # If we are printing events adjust the level to the display's
                # current level to guarantee output.
                if settings.print_events:
                    level = self.display.level

                self.display.banner("received event", level=level)
                self.display.output(f"Ruleset: {self.name}", level=level)
                self.display.output("Event:", level=level)
                self.display.output(data, pretty=True, level=level)
                self.display.banner(level=level)

                if isinstance(data, Shutdown):
                    self.shutdown = data
                    return await self._handle_shutdown()

                if not data:
                    # TODO: is it really necessary to add such event
                    # to event_log?
                    await self.event_log.put(dict(type="EmptyEvent"))
                    continue

                try:
                    logger.debug(
                        "Posting data to ruleset %s => %s",
                        self.name,
                        str(data),
                    )
                    lang.post(self.name, data)
                except MessageObservedException:
                    logger.debug("MessageObservedException: %s", data)
                except MessageNotHandledException:
                    logger.debug("MessageNotHandledException: %s", data)
                except BaseException as e:
                    logger.error(e)
                finally:
                    logger.debug(lang.get_pending_events(self.name))
                    if (
                        settings.gc_after
                        and self.event_counter > settings.gc_after
                    ):
                        self.event_counter = 0
                        gc.collect()
                    else:
                        self.event_counter += 1
                    while self.ruleset_queue_plan.plan.queue.qsize() > 10:
                        await asyncio.sleep(0)
        except asyncio.CancelledError:
            logger.debug("Source Task Cancelled for ruleset %s", self.name)
            raise

    def _handle_action_completion(self, task):
        self.active_actions.discard(task)
        logger.debug(
            "Task %s finished, active actions %d",
            task.get_name(),
            len(self.active_actions),
        )
        if (
            self.ruleset_queue_plan.plan.queue.empty()
            and self.shutdown
            and len(self.active_actions) == 0
        ):
            logger.debug("All actions done")
            if not self.action_loop_task.done():
                self.action_loop_task.cancel()

    async def _drain_actionplan_queue(self):
        logger.info("Waiting for actions on events from %s", self.name)
        try:
            while True:
                queue_item = await self.ruleset_queue_plan.plan.queue.get()
                rule_run_at = run_at()
                action_item = cast(ActionContext, queue_item)
                if self.parsed_args and self.parsed_args.heartbeat > 0:
                    await send_session_stats(
                        self.event_log,
                        session_stats(self.ruleset_queue_plan.ruleset.name),
                    )
                if len(action_item.actions) > 1:
                    task = asyncio.create_task(
                        self._run_multiple_actions(action_item, rule_run_at)
                    )
                    self.active_actions.add(task)
                    task.add_done_callback(self._handle_action_completion)
                else:
                    task = self._run_action(
                        action_item.actions[0], action_item, rule_run_at
                    )

                if (
                    self.rule_set.execution_strategy
                    == ExecutionStrategy.SEQUENTIAL
                ):
                    await task
        except asyncio.CancelledError:
            logger.debug(
                "Action Plan Task Cancelled for ruleset %s", self.name
            )
            raise
        except BaseException as e:
            logger.error(e)
            raise
        finally:
            await self._cleanup()

    async def _run_multiple_actions(
        self, action_item: ActionContext, rule_run_at: str
    ) -> None:
        for action in action_item.actions:
            await self._run_action(action, action_item, rule_run_at)

    def _run_action(
        self, action: Action, action_item: ActionContext, rule_run_at: str
    ) -> asyncio.Task:
        task_name = (
            f"action::{action.action}::"
            f"{self.ruleset_queue_plan.ruleset.name}::"
            f"{action_item.rule}"
        )
        logger.debug("Creating action task %s", task_name)
        metadata = Metadata(
            rule_set=action_item.ruleset,
            rule_set_uuid=action_item.ruleset_uuid,
            rule=action_item.rule,
            rule_uuid=action_item.rule_uuid,
            rule_run_at=rule_run_at,
        )

        task = asyncio.create_task(
            self._call_action(
                metadata,
                action.action,
                MappingProxyType(action.action_args),
                action_item.variables,
                action_item.inventory,
                action_item.hosts,
                action_item.rule_engine_results,
            ),
            name=task_name,
        )
        self.active_actions.add(task)
        task.add_done_callback(self._handle_action_completion)
        return task

    async def _call_action(
        self,
        metadata: Metadata,
        action: str,
        immutable_action_args: MappingProxyType,
        variables: Dict,
        inventory: str,
        hosts: List,
        rules_engine_result,
    ) -> None:
        logger.debug("call_action %s", action)
        action_args = immutable_action_args.copy()

        error = None
        if action in ACTION_CLASSES:
            try:
                if (
                    action == "run_job_template"
                    or action == "run_workflow_template"
                ):
                    limit = dpath.get(
                        action_args,
                        "job_args.limit",
                        separator=".",
                        default=None,
                    )
                    if isinstance(limit, list):
                        hosts = limit
                    elif isinstance(limit, str):
                        hosts = [limit]
                elif action == "shutdown":
                    if self.parsed_args and "delay" not in action_args:
                        action_args["delay"] = self.parsed_args.shutdown_delay

                single_match = None
                keys = list(rules_engine_result.data.keys())
                if len(keys) == 0:
                    single_match = {}
                elif len(keys) == 1 and keys[0] == "m":
                    single_match = rules_engine_result.data[keys[0]]
                else:
                    multi_match = rules_engine_result.data
                variables_copy = variables.copy()
                if single_match is not None:
                    variables_copy["event"] = single_match
                    event = single_match
                    if "meta" in event:
                        if "hosts" in event["meta"]:
                            hosts = parse_hosts(event["meta"]["hosts"])
                else:
                    variables_copy["events"] = multi_match
                    new_hosts = []
                    for event in variables_copy["events"].values():
                        if "meta" in event:
                            if "hosts" in event["meta"]:
                                new_hosts.extend(
                                    parse_hosts(event["meta"]["hosts"])
                                )
                    if new_hosts:
                        hosts = new_hosts

                if "var_root" in action_args:
                    var_root = action_args.pop("var_root")
                    logger.debug(
                        "Update variables [%s] with new root [%s]",
                        variables_copy,
                        var_root,
                    )
                    _update_variables(variables_copy, var_root)

                logger.debug(
                    "substitute_variables [%s] [%s]",
                    action_args,
                    variables_copy,
                )
                action_args = {
                    k: substitute_variables(v, variables_copy)
                    for k, v in action_args.items()
                }
                logger.debug("action args: %s", action_args)

                if "ruleset" not in action_args:
                    action_args["ruleset"] = metadata.rule_set

                control = Control(
                    queue=self.event_log,
                    inventory=inventory,
                    hosts=hosts,
                    variables=variables_copy,
                    project_data_file=self.project_data_file,
                )

                await ACTION_CLASSES[action](
                    metadata,
                    control,
                    **action_args,
                )()

            except KeyError as e:
                logger.error(
                    "KeyError %s with variables %s",
                    str(e),
                    pformat(variables_copy),
                )
                error = e
            except MessageNotHandledException as e:
                logger.error(
                    "Message cannot be handled: %s err %s", action_args, str(e)
                )
                error = e
            except MessageObservedException as e:
                logger.debug("MessageObservedException: %s", action_args)
                error = e
            except ShutdownException as e:
                if self.shutdown:
                    logger.debug(
                        "A shutdown is already in progress, ignoring this one"
                    )
                else:
                    await self.broadcast_method(e.shutdown)
            except asyncio.CancelledError:
                logger.debug("Action task caught Cancelled error")
                raise
            except Exception as e:
                logger.error("Error calling action %s, err %s", action, str(e))
                error = e
            except BaseException as e:
                logger.error(e)
                raise
        else:
            logger.error("Action %s not supported", action)
            error = UnsupportedActionException(
                f"Action {action} not supported"
            )

        if error:
            await self.event_log.put(
                dict(
                    type="Action",
                    action=action,
                    action_uuid=str(uuid.uuid4()),
                    activation_id=settings.identifier,
                    activation_instance_id=settings.identifier,
                    playbook_name=action_args.get("name"),
                    status="failed",
                    run_at=run_at(),
                    rule_run_at=metadata.rule_run_at,
                    message=str(error),
                    rule=metadata.rule,
                    ruleset=metadata.rule_set,
                    rule_uuid=metadata.rule_uuid,
                    ruleset_uuid=metadata.rule_set_uuid,
                )
            )


def prime_facts(name: str, hosts_facts: List[Dict]):
    for data in hosts_facts:
        try:
            lang.assert_fact(name, data)
        except MessageNotHandledException:
            pass


def _update_variables(variables: Dict, var_root: Union[str, Dict]):
    var_roots = {var_root: var_root} if isinstance(var_root, str) else var_root
    if "event" in variables:
        for key, _new_key in var_roots.items():
            new_value = dpath.get(
                variables["event"], key, separator=".", default=None
            )
            if new_value:
                variables["event"] = new_value
                break
    elif "events" in variables:
        for _k, v in variables["events"].items():
            for old_key, new_key in var_roots.items():
                new_value = dpath.get(v, old_key, separator=".", default=None)
                if new_value:
                    variables["events"][new_key] = new_value
                    break
