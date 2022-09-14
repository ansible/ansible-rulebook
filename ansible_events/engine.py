import asyncio
import logging
import os
import runpy
import traceback
from datetime import datetime
from pprint import pformat
from typing import Any, Dict, List, Optional, cast

if os.environ.get("RULES_ENGINE", "durable_rules") == "drools":
    from drools.vendor import engine, lang
else:
    from durable import engine, lang

import ansible_events.rule_generator as rule_generator
from ansible_events.builtin import actions as builtin_actions
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
    EventSource,
    RuleSetQueue,
    RuleSetQueuePlan,
)
from ansible_events.rules_parser import parse_hosts
from ansible_events.util import json_count, substitute_variables


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

    logger = logging.getLogger()

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


async def call_action(
    ruleset: str,
    action: str,
    action_args: Dict,
    variables: Dict,
    inventory: Dict,
    hosts: List,
    facts: Dict,
    c,
    event_log,
) -> Dict:

    logger = logging.getLogger()
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
            logger.info(f"action args: {action_args}")

            if facts is None:
                facts = lang.get_facts(ruleset)
                logger.info(f"facts: {facts}")

            if "ruleset" not in action_args:
                action_args["ruleset"] = ruleset

            return await builtin_actions[action](
                event_log=event_log,
                inventory=inventory,
                hosts=hosts,
                variables=variables_copy,
                facts=facts,
                **action_args,
            )
        except KeyError as e:
            logger.error(f"KeyError: {e}\n{pformat(variables_copy)}")
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

    await event_log.put(
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


async def run_rulesets(
    event_log: asyncio.Queue,
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: Dict,
    redis_host_name: Optional[str] = None,
    redis_port: Optional[int] = None,
):

    logger = logging.getLogger()

    logger.info("run_ruleset")
    if redis_host_name and redis_port:
        provide_durability(lang.get_host(), redis_host_name, redis_port)

    ansible_ruleset_queue_plans = [
        RuleSetQueuePlan(ruleset, queue, asyncio.Queue())
        for ruleset, queue in ruleset_queues
    ]

    rulesets_queue_plans = rule_generator.generate_rulesets(
        ansible_ruleset_queue_plans, variables, inventory
    )
    for rulesets_list in rulesets_queue_plans:
        for rulesets in rulesets_list[1]:
            logger.info("rulesets define: %s", rulesets.define())

    if not rulesets_queue_plans:
        return

    while True:
        logger.info("Waiting for event")
        queue_tasks = {
            asyncio.create_task(rqp[2].get()): rqp
            for rqp in rulesets_queue_plans
        }
        done, pending = await asyncio.wait(
            list(queue_tasks.keys()), return_when=asyncio.FIRST_COMPLETED
        )
        for queue_reader in done:
            ruleset, _, queue, plan = queue_tasks[queue_reader]
            data = queue_reader.result()
            json_count(data)
            if isinstance(data, Shutdown):
                await event_log.put(dict(type="Shutdown"))
                return
            if not data:
                await event_log.put(dict(type="EmptyEvent"))
                continue
            results = []
            try:
                try:
                    lang.post(ruleset.name, data)
                except engine.MessageObservedException:
                    logger.debug(f"MessageObservedException: {data}")
                except engine.MessageNotHandledException:
                    logger.debug(f"MessageNotHandledException: {data}")
                finally:
                    logger.debug(lang.get_pending_events(ruleset.name))

                while not plan.empty():
                    item = cast(ActionContext, await plan.get())
                    logger.debug(f"item: {item}")
                    result = await call_action(*item, event_log=event_log)
                    logger.debug(f"call_action result: {result}")
                    results.append(result)

                await event_log.put(
                    dict(type="ProcessedEvent", results=results)
                )
            except engine.MessageNotHandledException:
                logger.info(f"MessageNotHandledException: {data}")
                await event_log.put(dict(type="MessageNotHandled"))
            except ShutdownException:
                await event_log.put(dict(type="Shutdown"))
            except Exception as e:
                logger.error(
                    f"Error calling {data}: {e}\n {traceback.format_exc()}"
                )
