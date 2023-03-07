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
import logging
from datetime import datetime
from pprint import PrettyPrinter, pformat
from typing import Dict, List, Optional, Union, cast

import dpath
from drools import ruleset as lang
from drools.exceptions import (
    MessageNotHandledException,
    MessageObservedException,
)

from ansible_rulebook.builtin import actions as builtin_actions
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import ShutdownException
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import ActionContext, EngineRuleSetQueuePlan
from ansible_rulebook.rules_parser import parse_hosts
from ansible_rulebook.util import substitute_variables

logger = logging.getLogger(__name__)


class RuleSetRunner:
    def __init__(
        self,
        event_log: asyncio.Queue,
        ruleset_queue_plan: EngineRuleSetQueuePlan,
        hosts_facts,
        variables,
        project_data_file: Optional[str] = None,
        parsed_args=None,
        broadcast_method=None,
    ):
        self.action_loop_task = None
        self.event_log = event_log
        self.ruleset_queue_plan = ruleset_queue_plan
        self.name = ruleset_queue_plan.ruleset.name
        self.hosts_facts = hosts_facts
        self.variables = variables
        self.project_data_file = project_data_file
        self.parsed_args = parsed_args
        self.shutdown = None
        self.active_actions = set()
        self.broadcast_method = broadcast_method

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
            logger.info("Cancelled error caught in run_ruleset")
            for task in tasks:
                if not task.done():
                    logger.info("Cancelling (2) task %s", task.get_name())
                    task.cancel()

        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            raise

    async def _cleanup(self):
        logger.info("Cleaning up ruleset %s", self.name)
        if not self.source_loop_task.done():
            self.source_loop_task.cancel()

        for task in self.active_actions:
            logger.info("Cancelling active task %s", task.get_name())
            task.cancel()

        if self.active_actions:
            await asyncio.wait(
                self.active_actions, return_when=asyncio.FIRST_EXCEPTION
            )
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
        logger.info(pformat(stats))

    async def _handle_shutdown(self):
        logger.info(
            "Ruleset: %s, received shutdown: %s",
            self.name,
            str(self.shutdown),
        )
        if self.shutdown.kind == "now":
            logger.info(
                "ruleset: %s has issued an immediate shutdown", self.name
            )
            self.action_loop_task.cancel()
        elif (
            self.ruleset_queue_plan.plan.queue.empty()
            and not self.active_actions
        ):
            logger.info("ruleset: %s shutdown no pending work", self.name)
            self.action_loop_task.cancel()
        else:
            logger.info(
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
                if self.parsed_args and self.parsed_args.print_events:
                    PrettyPrinter(indent=4).pprint(data)

                logger.debug(
                    "Ruleset: %s, received event: %s ", self.name, str(data)
                )
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
                finally:
                    logger.debug(lang.get_pending_events(self.name))
        except asyncio.CancelledError:
            logger.debug("Source Task Cancelled for ruleset %s", self.name)
            raise

    async def _drain_actionplan_queue(self):
        logger.info("Waiting for actions on events from %s", self.name)
        try:
            while True:
                queue_item = await self.ruleset_queue_plan.plan.queue.get()
                action_item = cast(ActionContext, queue_item)
                for action in action_item.actions:
                    task_name = (
                        f"action::{self.ruleset_queue_plan.ruleset.name}"
                    )
                    task = asyncio.create_task(
                        self._call_action(
                            action_item.ruleset,
                            action_item.rule,
                            action.action,
                            action.action_args,
                            action_item.variables,
                            action_item.inventory,
                            action_item.hosts,
                            action_item.rule_engine_results,
                        ),
                        name=task_name,
                    )
                    self.active_actions.add(task)
                    task.add_done_callback(self.active_actions.discard)
                    await task

                if (
                    self.ruleset_queue_plan.plan.queue.empty()
                    and self.shutdown
                ):
                    break
        except asyncio.CancelledError:
            logger.info("Action Plan Task Cancelled for ruleset %s", self.name)
            raise
        finally:
            await self._cleanup()

    async def _call_action(
        self,
        ruleset: str,
        rule: str,
        action: str,
        action_args: Dict,
        variables: Dict,
        inventory: str,
        hosts: List,
        rules_engine_result,
    ) -> None:

        logger.info("call_action %s", action)

        result = None
        if action in builtin_actions:
            try:
                if action == "run_job_template":
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
                    logger.info(
                        "Update variables [%s] with new root [%s]",
                        variables_copy,
                        var_root,
                    )
                    _update_variables(variables_copy, var_root)

                logger.info(
                    "substitute_variables [%s] [%s]",
                    action_args,
                    variables_copy,
                )
                action_args = {
                    k: substitute_variables(v, variables_copy)
                    for k, v in action_args.items()
                }
                logger.info("action args: %s", action_args)

                if "ruleset" not in action_args:
                    action_args["ruleset"] = ruleset

                await builtin_actions[action](
                    event_log=self.event_log,
                    inventory=inventory,
                    hosts=hosts,
                    variables=variables_copy,
                    project_data_file=self.project_data_file,
                    source_ruleset_name=ruleset,
                    source_rule_name=rule,
                    **action_args,
                )
            except KeyError as e:
                logger.exception(
                    "KeyError with variables %s", pformat(variables_copy)
                )
                result = dict(error=e)
            except MessageNotHandledException as e:
                logger.exception("Message cannot be handled: %s", action_args)
                result = dict(error=e)
            except MessageObservedException as e:
                logger.info("MessageObservedException: %s", action_args)
                result = dict(error=e)
            except ShutdownException as e:
                if self.shutdown:
                    logger.info(
                        "A shutdown is already in progress, ignoring this one"
                    )
                else:
                    self.broadcast_method(e.shutdown)
            except asyncio.CancelledError:
                logger.info("Action task caught Cancelled error")
                raise
            except Exception as e:
                logger.exception("Error calling %s", action)
                result = dict(error=e)
        else:
            logger.error("Action %s not supported", action)
            result = dict(error=f"Action {action} not supported")

        if result:
            await self.event_log.put(
                dict(
                    type="Action",
                    action=action,
                    activation_id=settings.identifier,
                    playbook_name=action_args.get("name"),
                    status="failed",
                    run_at=str(datetime.utcnow()),
                    reason=result,
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
