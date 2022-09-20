import asyncio
import logging
import os
import runpy
import traceback
from collections import OrderedDict
from datetime import datetime
from pprint import pformat
from typing import Any, Dict, List, Optional, cast

if os.environ.get("RULES_ENGINE", "durable_rules") == "drools":
    from drools.vendor import engine, lang
else:
    from durable import engine, lang

import ansible_events.rule_generator as rule_generator
from ansible_events.builtin import actions as builtin_actions, run_playbook
from ansible_events.collection import (
    find_source,
    find_source_filter,
    has_source,
    has_source_filter,
    split_collection_name,
)
from ansible_events.conf import settings
from ansible_events.durability import provide_durability
from ansible_events.exception import ShutdownException
from ansible_events.messages import Shutdown
from ansible_events.rule_types import (
    ActionContext,
    EngineRuleSetQueuePlan,
    EventSource,
    RuleSetQueue,
)
from ansible_events.rules_parser import parse_hosts
from ansible_events.util import json_count, substitute_variables

logger = logging.getLogger()


class FilteredQueue:
    def __init__(self, filters, queue: asyncio.Queue):
        self.filters = filters
        self.queue = queue

    async def put(self, data):
        for f, kwargs in self.filters:
            kwargs = kwargs or {}
            data = f(data, **kwargs)
        await self.queue.put(data)


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
            logger.info(f"loading {source_filter.filter_name}")
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
        logger.info(f"Calling main in {source.source_name}")

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
    except BaseException as e:
        logger.error(f"Source error {e}")
    finally:
        await queue.put(Shutdown())


async def run_rulesets(
    event_log: asyncio.Queue,
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: Dict,
    redis_host_name: Optional[str] = None,
    redis_port: Optional[int] = None,
):

    logger.info("run_ruleset")
    if redis_host_name and redis_port:
        provide_durability(lang.get_host(), redis_host_name, redis_port)

    rulesets_queue_plans = rule_generator.generate_rulesets(
        ruleset_queues, variables, inventory
    )

    if not rulesets_queue_plans:
        return

    for ruleset_queue_plan in rulesets_queue_plans:
        logger.info("ruleset define: %s", ruleset_queue_plan.ruleset.define())

    ruleset_tasks = []
    for ruleset_queue_plan in rulesets_queue_plans:
        ruleset_runner = RuleSetRunner(event_log, ruleset_queue_plan)
        ruleset_task = asyncio.create_task(ruleset_runner.run_ruleset())
        ruleset_tasks.append(ruleset_task)

    await asyncio.wait(ruleset_tasks, return_when=asyncio.FIRST_COMPLETED)


class RuleSetRunner:
    def __init__(
        self,
        event_log: asyncio.Queue,
        ruleset_queue_plan: EngineRuleSetQueuePlan,
    ):
        self.pa_runner = PlaybookActionRunner()
        self.playbook_actions_task = None
        self.action_tasks = []
        self.event_log = event_log
        self.ruleset_queue_plan = ruleset_queue_plan

    async def run_ruleset(self):
        name = self.ruleset_queue_plan.ruleset.name
        self.playbook_actions_task = asyncio.create_task(
            self.pa_runner.start(name), name=name
        )
        logger.info(f"Waiting for event from {name}")
        while True:
            data = await self.ruleset_queue_plan.queue.get()
            self.ruleset_queue_plan.plan.queue = asyncio.Queue()
            json_count(data)
            if isinstance(data, Shutdown):
                await asyncio.wait(self.action_tasks)
                self.pa_runner.stop()
                await self.playbook_actions_task
                await self.event_log.put(dict(type="Shutdown"))
                return
            if not data:
                await self.event_log.put(dict(type="EmptyEvent"))
                continue

            logger.debug(str(data))
            self.action_tasks.append(
                asyncio.create_task(
                    self.run_actions(data, self.ruleset_queue_plan.plan.queue)
                )
            )

    async def run_actions(self, data: Dict, plan_queue: asyncio.Queue):
        results = []
        try:
            name = self.ruleset_queue_plan.ruleset.name
            try:
                lang.post(name, data)
            except engine.MessageObservedException:
                logger.debug(f"MessageObservedException: {data}")
            except engine.MessageNotHandledException:
                logger.debug(f"MessageNotHandledException: {data}")
            finally:
                logger.debug(lang.get_pending_events(name))

            while not plan_queue.empty():
                item = cast(ActionContext, await plan_queue.get())
                result = await self.call_action(*item)
                results.append(result)

            await self.event_log.put(
                dict(type="ProcessedEvent", results=results)
            )
        except engine.MessageNotHandledException:
            logger.info(f"MessageNotHandledException: {data}")
            await self.event_log.put(dict(type="MessageNotHandled"))
        except ShutdownException:
            await self.ruleset_queue_plan.queue.put(Shutdown())
        except Exception as e:
            logger.error(
                f"Error calling {data}: {e}\n {traceback.format_exc()}"
            )

    async def call_action(
        self,
        ruleset: str,
        action: str,
        action_args: Dict,
        variables: Dict,
        inventory: Dict,
        hosts: List,
        facts: Dict,
        c,
    ) -> Dict:

        logger.info(f"call_action {action}")

        if action in builtin_actions:
            try:
                variables_copy = variables.copy()
                if c.m is not None:
                    variables_copy[
                        "event"
                    ] = c.m._d  # event data is stored in c.m._d
                    variables_copy[
                        "fact"
                    ] = c.m._d  # event data is stored in c.m._d
                    event = c.m._d  # event data is stored in c.m._d
                    if "meta" in event:
                        if "hosts" in event["meta"]:
                            hosts = parse_hosts(event["meta"]["hosts"])
                else:
                    variables_copy["events"] = c._m
                    variables_copy["facts"] = c._m
                    new_hosts = []
                    for event in variables_copy["events"]:
                        if "meta" in event:
                            if "hosts" in event["meta"]:
                                new_hosts.append(
                                    parse_hosts(event["meta"]["hosts"])
                                )
                    if new_hosts:
                        hosts = new_hosts

                logger.info(
                    f"substitute_variables [{action_args}] [{variables_copy}]"
                )
                action_args = {
                    k: substitute_variables(v, variables_copy)
                    for k, v in action_args.items()
                }
                logger.info(action_args)

                if facts is None:
                    facts = lang.get_facts(ruleset)
                    logger.info(f"facts: {facts}")

                if "ruleset" not in action_args:
                    action_args["ruleset"] = ruleset

                if action == "run_playbook":
                    action_args["event_log"] = self.event_log
                    action_args["inventory"] = inventory
                    action_args["hosts"] = hosts
                    action_args["variables"] = variables_copy
                    action_args["facts"] = facts
                    return await self.pa_runner.wait_for_playbook(action_args)
                else:
                    return await builtin_actions[action](
                        event_log=self.event_log,
                        inventory=inventory,
                        hosts=hosts,
                        variables=variables_copy,
                        facts=facts,
                        **action_args,
                    )
            except KeyError as e:
                logger.error(f"{e}\n{pformat(variables_copy)}")
                result = dict(error=e)
            except engine.MessageNotHandledException as e:
                logger.error(f"MessageNotHandledException: {action_args}")
                result = dict(error=e)
            except engine.MessageObservedException as e:
                logger.info(f"MessageObservedException: {action_args}")
                result = dict(error=e)
            except ShutdownException:
                raise
            except Exception as e:
                logger.error(
                    f"Error calling {action}: {e}\n {traceback.format_exc()}"
                )
                result = dict(error=e)
        else:
            logger.error(f"Action {action} not supported")
            result = dict(error=f"Action {action} not supported")

        await self.event_log.put(
            dict(
                type="Action",
                action=action,
                activation_id=settings.identifier,
                playbook_name=action_args.get("name"),
                status="failed",
                run_at=str(datetime.utcnow()),
            )
        )

        return result


class PlaybookActionRunner:
    def __init__(self):
        self.actions = OrderedDict()
        self.result = None
        self.stopped = True
        self.delay = int(os.environ.get("RUN_PLAYBOOK_DELAY", 0))

    async def start(self, name: str):
        if not self.stopped:
            return

        logger.info(f"Start a playbook action runner for {name}")
        self.stopped = False
        while not self.stopped:
            await asyncio.sleep(self.delay)
            await self.execute()
        logger.info(f"Playbook action runner {name} exists")

    def stop(self):
        self.stopped = True

    async def execute(self):
        for key in list(self.actions.keys()):
            action_args = self.actions[key]
            del self.actions[key]
            async_condition = action_args.pop("async_condition")

            try:
                result = await run_playbook(**action_args)
            except Exception as e:
                action = "run_playbook"
                logger.error(
                    f"Error calling {action}: {e}\n {traceback.format_exc()}"
                )
                result = dict(error=e)

            async with async_condition:
                self.result = result
                async_condition.notify_all()

    async def wait_for_playbook(self, action_args: Dict):
        name = action_args["name"]
        logger.info(f"Queue playbook {name} for running later")

        if name in self.actions:
            for host in action_args["hosts"]:
                logger.info(f"Combine host {host} to playbook {name}")
                self.actions[name]["hosts"].add(host)
            async_condition = self.actions[name]["async_condition"]
        else:
            async_condition = asyncio.Condition()
            action_args["async_condition"] = async_condition
            action_args["hosts"] = set(action_args["hosts"])
            self.actions[name] = action_args

        result = None
        async with async_condition:
            await async_condition.wait()
            result = self.result
        return result
