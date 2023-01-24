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

import argparse
import asyncio
import logging
import os
import runpy
from datetime import datetime
from pprint import PrettyPrinter, pformat
from typing import Any, Dict, List, Optional, cast

from drools import ruleset as lang
from drools.exceptions import (
    MessageNotHandledException,
    MessageObservedException,
)

import ansible_rulebook.rule_generator as rule_generator
from ansible_rulebook.builtin import actions as builtin_actions
from ansible_rulebook.collection import (
    find_source,
    find_source_filter,
    has_source,
    has_source_filter,
    split_collection_name,
)
from ansible_rulebook.conf import settings
from ansible_rulebook.durability import provide_durability
from ansible_rulebook.exception import ShutdownException
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import (
    ActionContext,
    EngineRuleSetQueuePlan,
    EventSource,
    RuleSetQueue,
)
from ansible_rulebook.rules_parser import parse_hosts
from ansible_rulebook.util import (
    collect_ansible_facts,
    json_count,
    substitute_variables,
)

logger = logging.getLogger(__name__)


class FilteredQueue:
    def __init__(self, filters, queue: asyncio.Queue):
        self.filters = filters
        self.queue = queue

    async def put(self, data):
        for f, kwargs in self.filters:
            kwargs = kwargs or {}
            data = f(data, **kwargs)
        await self.queue.put(data)

    def put_nowait(self, data):
        for f, kwargs in self.filters:
            kwargs = kwargs or {}
            data = f(data, **kwargs)
        self.queue.put_nowait(data)


async def start_source(
    source: EventSource,
    source_dirs: List[str],
    variables: Dict[str, Any],
    queue: asyncio.Queue,
) -> None:

    try:
        logger.info("load source")
        if (
            source_dirs
            and source_dirs[0]
            and os.path.exists(
                os.path.join(source_dirs[0], source.source_name + ".py")
            )
        ):
            module = runpy.run_path(
                os.path.join(source_dirs[0], source.source_name + ".py")
            )
        elif has_source(*split_collection_name(source.source_name)):
            module = runpy.run_path(
                find_source(*split_collection_name(source.source_name))
            )
        else:
            raise Exception(
                f"Could not find source plugin for {source.source_name}"
            )

        source_filters = []

        logger.info("load source filters")
        for source_filter in source.source_filters:
            logger.info("loading %s", source_filter.filter_name)
            if os.path.exists(
                os.path.join(
                    "event_filters", source_filter.filter_name + ".py"
                )
            ):
                source_filter_module = runpy.run_path(
                    os.path.join(
                        "event_filters", source_filter.filter_name + ".py"
                    )
                )
            elif has_source_filter(
                *split_collection_name(source_filter.filter_name)
            ):
                source_filter_module = runpy.run_path(
                    find_source_filter(
                        *split_collection_name(source_filter.filter_name)
                    )
                )
            else:
                raise Exception(
                    f"Could not find source filter plugin "
                    f"for {source_filter.filter_name}"
                )
            source_filters.append(
                (source_filter_module["main"], source_filter.filter_args)
            )

        args = {
            k: substitute_variables(v, variables)
            for k, v in source.source_args.items()
        }
        fqueue = FilteredQueue(source_filters, queue)
        logger.info("Calling main in %s", source.source_name)

        try:
            entrypoint = module["main"]
        except KeyError:
            # FIXME(cutwater): Replace with custom exception class
            raise Exception(
                "Entrypoint missing. Source module must have function 'main'."
            )

        # NOTE(cutwater): This check may be unnecessary.
        if not asyncio.iscoroutinefunction(entrypoint):
            # FIXME(cutwater): Replace with custom exception class
            raise Exception("Entrypoint is not a coroutine function.")

        await entrypoint(fqueue, args)

    except KeyboardInterrupt:
        pass
    except asyncio.CancelledError:
        logger.info("Task cancelled")
    except BaseException:
        logger.exception("Source error")
        raise
    finally:
        await queue.put(Shutdown())


async def run_rulesets(
    event_log: asyncio.Queue,
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: Dict,
    parsed_args: argparse.ArgumentParser = None,
    project_data_file: Optional[str] = None,
):

    logger.info("run_ruleset")
    if parsed_args and parsed_args.redis_host_name and parsed_args.redis_port:
        provide_durability(
            lang.get_host(),
            parsed_args.redis_host_name,
            parsed_args.redis_port,
        )

    rulesets_queue_plans = rule_generator.generate_rulesets(
        ruleset_queues, variables, inventory
    )

    if not rulesets_queue_plans:
        return

    for ruleset_queue_plan in rulesets_queue_plans:
        logger.info("ruleset define: %s", ruleset_queue_plan.ruleset.define())

    hosts_facts = []
    for ruleset, _ in ruleset_queues:
        if ruleset.gather_facts and not hosts_facts:
            hosts_facts = collect_ansible_facts(inventory)

    ruleset_tasks = []
    for ruleset_queue_plan in rulesets_queue_plans:
        ruleset_runner = RuleSetRunner(
            event_log=event_log,
            ruleset_queue_plan=ruleset_queue_plan,
            hosts_facts=hosts_facts,
            variables=variables,
            project_data_file=project_data_file,
            parsed_args=parsed_args,
        )
        ruleset_task = asyncio.create_task(ruleset_runner.run_ruleset())
        ruleset_tasks.append(ruleset_task)

    await asyncio.wait(ruleset_tasks, return_when=asyncio.FIRST_COMPLETED)
    logger.info("Canceling all ruleset tasks")
    for task in ruleset_tasks:
        task.cancel()


class RuleSetRunner:
    ANSIBLE_ACTIONS = ("run_playbook", "run_module", "run_job_template")

    def __init__(
        self,
        event_log: asyncio.Queue,
        ruleset_queue_plan: EngineRuleSetQueuePlan,
        hosts_facts,
        variables,
        project_data_file: Optional[str] = None,
        parsed_args=None,
    ):
        self.pa_runner = PlaybookActionRunner()
        self.pa_runner_task = None
        self.action_loop_task = None
        self.event_log = event_log
        self.ruleset_queue_plan = ruleset_queue_plan
        self.name = ruleset_queue_plan.ruleset.name
        self.hosts_facts = hosts_facts
        self.variables = variables
        self.project_data_file = project_data_file
        self.parsed_args = parsed_args
        self.stopped = True

    async def run_ruleset(self):
        self.stopped = False
        prime_facts(self.name, self.hosts_facts, self.variables)
        self.pa_runner_task = asyncio.create_task(
            self.pa_runner.start(self.name), name=self.name
        )
        self.action_loop_task = asyncio.create_task(
            self._drain_actionplan_queue()
        )
        source_loop_task = asyncio.create_task(self._drain_source_queue())
        await asyncio.wait([source_loop_task])

    async def _stop(self):
        # Wait for items in queues to be completed. Mainly for spec tests.
        await asyncio.sleep(0.01)

        logger.info("Attempt to stop ruleset %s", self.name)
        self.stopped = True
        self.pa_runner.stop()
        # helps to break waiting on the plan queue when it is empty
        try:
            self.ruleset_queue_plan.plan.queue.put_nowait(Shutdown())
        except asyncio.QueueFull:
            pass

        await asyncio.wait([self.pa_runner_task, self.action_loop_task])
        await self.event_log.put(dict(type="Shutdown"))
        lang.end_session(self.name)

    async def _drain_source_queue(self):
        logger.info("Waiting for events from %s", self.name)
        while True:
            data = await self.ruleset_queue_plan.source_queue.get()
            if self.parsed_args and self.parsed_args.print_events:
                PrettyPrinter(indent=4).pprint(data)

            logger.debug("Received event : " + str(data))
            json_count(data)
            if isinstance(data, Shutdown):
                await self._stop()
                logger.info("Stopped waiting on events from %s", self.name)
                return
            if not data:
                # TODO: is it really necessary to add such event to event_log?
                await self.event_log.put(dict(type="EmptyEvent"))
                continue

            try:
                lang.post(self.name, data)
            except MessageObservedException:
                logger.debug("MessageObservedException: %s", data)
            except MessageNotHandledException:
                logger.debug("MessageNotHandledException: %s", data)
            finally:
                logger.debug(lang.get_pending_events(self.name))

    async def _drain_actionplan_queue(self):
        logger.info("Waiting for actions on events from %s", self.name)
        while not self.stopped:
            queue_item = await self.ruleset_queue_plan.plan.queue.get()
            if isinstance(queue_item, Shutdown):
                break
            # TODO: consider uncomment the following but it will fail a lot of
            # spec tests because Shutdown is issued immediately after the last
            # event. Spec tests assume every thing is processed without lossing
            # if self.stopped:
            #    break

            action_item = cast(ActionContext, queue_item)
            await self._call_action(*action_item)

        logger.info("Stopped waiting for actions on events from %s", self.name)

    async def _call_action(
        self,
        ruleset: str,
        rule: str,
        action: str,
        action_args: Dict,
        variables: Dict,
        inventory: Dict,
        hosts: List,
        facts: Dict,
        rules_engine_result,
    ) -> None:

        logger.info("call_action %s", action)

        result = None
        if action in builtin_actions:
            try:
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
                    variables_copy["fact"] = single_match
                    event = single_match
                    if "meta" in event:
                        if "hosts" in event["meta"]:
                            hosts = parse_hosts(event["meta"]["hosts"])
                else:
                    variables_copy["events"] = multi_match
                    variables_copy["facts"] = multi_match
                    new_hosts = []
                    for event in variables_copy["events"].values():
                        if "meta" in event:
                            if "hosts" in event["meta"]:
                                new_hosts.extend(
                                    parse_hosts(event["meta"]["hosts"])
                                )
                    if new_hosts:
                        hosts = new_hosts

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

                if facts is None:
                    facts = lang.get_facts(ruleset)
                    logger.info("facts: %s", facts)

                if "ruleset" not in action_args:
                    action_args["ruleset"] = ruleset

                if action in self.ANSIBLE_ACTIONS:
                    action_args["event_log"] = self.event_log
                    action_args["inventory"] = inventory
                    action_args["hosts"] = hosts
                    action_args["variables"] = variables_copy
                    action_args["facts"] = facts
                    action_args["project_data_file"] = self.project_data_file
                    action_args["source_ruleset_name"] = ruleset
                    action_args["source_rule_name"] = rule
                    result = await self.pa_runner.add_playbook(
                        action, action_args
                    )
                else:
                    await builtin_actions[action](
                        event_log=self.event_log,
                        inventory=inventory,
                        hosts=hosts,
                        variables=variables_copy,
                        facts=facts,
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
            except ShutdownException:
                await self.ruleset_queue_plan.source_queue.put(Shutdown())
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


class PlaybookActionRunner:
    """Run playbook like actions in background. Queue such actions
    and run them in sequential order.
    These actions are defined in ANSIBLE_ACTIONS including
    run_playbook, run_module, and run_job_template.
    """

    def __init__(self):
        self.actions = asyncio.Queue()
        self.result = None
        self.stopped = True

    async def start(self, name: str):
        if not self.stopped:
            return

        logger.info("Start a playbook action runner for %s", name)
        self.stopped = False
        while not self.stopped:
            action_args = await self.actions.get()
            if isinstance(action_args, Shutdown):
                break
            # TODO: consider uncomment the following but it will fail some
            # spec tests because Shutdown is issued immediately after the last
            # event. Spec tests assume everything is processed with lossing
            # if self.stopped:
            #    break
            await self.execute(action_args)

        logger.info("Playbook action runner %s exits", name)

    def stop(self):
        self.stopped = True
        # helps to break waiting on actions.get when the queue is empty
        try:
            self.actions.put_nowait(Shutdown())
        except asyncio.QueueFull:
            pass

    async def execute(self, action_args: Dict):
        action_method = action_args.pop("_action_method")

        try:
            await action_method(**action_args)
        except Exception as e:
            logger.exception("Error calling %s", action_method.__name__)
            result = dict(error=e)
            await self.event_log.put(
                dict(
                    type="Action",
                    action=action_method.__name__,
                    activation_id=settings.identifier,
                    playbook_name=action_args.get("name"),
                    status="failed",
                    run_at=str(datetime.utcnow()),
                    reason=result,
                )
            )

    async def add_playbook(self, action: str, action_args: Dict):
        name = {action_args["name"]}
        logger.info(
            "Queue playbook/module/job template %s for running later", name
        )

        action_args["_action_method"] = builtin_actions[action]
        await self.actions.put(action_args)


def prime_facts(name: str, hosts_facts: List[Dict], variables: Dict):
    for data in hosts_facts:
        try:
            lang.assert_fact(name, data)
        except MessageNotHandledException:
            pass

    if variables:
        try:
            lang.assert_fact(name, variables)
        except MessageNotHandledException:
            pass
