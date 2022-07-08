import os
import runpy
import asyncio
import durable.lang
import traceback
import logging
from queue import Queue


from pprint import pformat

import ansible_events.rule_generator as rule_generator
from ansible_events.durability import provide_durability
from ansible_events.messages import Shutdown
from ansible_events.util import substitute_variables, json_count
from ansible_events.builtin import actions as builtin_actions
from ansible_events.rule_types import (
    EventSource,
    RuleSetQueue,
    RuleSetQueuePlan,
    ActionContext,
)
from ansible_events.rules_parser import parse_hosts
from ansible_events.exception import ShutdownException
from ansible_events.collection import (
    has_source,
    split_collection_name,
    find_source,
    has_source_filter,
    find_source_filter,
)

from typing import Optional, Dict, List, cast


class FilteredQueue:
    def __init__(self, filters, queue):
        self.filters = filters
        self.queue = queue

    def put(self, data):
        for f, kwargs in self.filters:
            kwargs = kwargs or {}
            data = f(data, **kwargs)
        self.queue.put(data)


def start_source(
    source: EventSource,
    source_dirs: List[str],
    variables: Dict,
    queue: Queue,
) -> None:

    logger = logging.getLogger()

    logger.info("start_source")

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
        logger.info(f"calling main in {source.source_name}")
        module["main"](fqueue, args)
    except KeyboardInterrupt:
        pass
    except BaseException as e:
        logger.error(f"Source error {e}")
    finally:
        queue.put(Shutdown())


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
                event = c.m._d  # event data is stored in c.m._d
                if "meta" in event:
                    if "hosts" in event["meta"]:
                        hosts = parse_hosts(event["meta"]["hosts"])
            else:
                variables_copy["events"] = c._m
                new_hosts = []
                for event in variables_copy["events"]:
                    if "meta" in event:
                        if "hosts" in event["meta"]:
                            new_hosts.append(
                                parse_hosts(event["meta"]["hosts"])
                            )
                if new_hosts:
                    hosts = new_hosts
            logger.info(f"substitute_variables {action_args} {variables_copy}")
            action_args = {
                k: substitute_variables(v, variables_copy)
                for k, v in action_args.items()
            }
            logger.info(action_args)
            if facts is None:
                facts = durable.lang.get_facts(ruleset)
            logger.info(f"facts: {durable.lang.get_facts(ruleset)}")
            if "ruleset" not in action_args:
                action_args["ruleset"] = ruleset
            result = await builtin_actions[action](
                event_log=event_log,
                inventory=inventory,
                hosts=hosts,
                variables=variables_copy,
                facts=facts,
                **action_args,
            )
        except KeyError as e:
            logger.error(f"{e}\n{pformat(variables_copy)}")
            raise
        except durable.engine.MessageNotHandledException as e:
            logger.error(f"MessageNotHandledException: {action_args}")
            result = dict(error=e)
        except durable.engine.MessageObservedException as e:
            logger.info(f"MessageObservedException: {action_args}")
            result = dict(error=e)
        except ShutdownException as e:
            raise
        except Exception as e:
            logger.error(
                f"Error calling {action}: {e}\n {traceback.format_exc()}"
            )
            result = dict(error=e)
    else:
        raise Exception(f"Action {action} not supported")

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
        provide_durability(
            durable.lang.get_host(), redis_host_name, redis_port
        )

    ansible_ruleset_queue_plans = [
        RuleSetQueuePlan(ruleset, queue, asyncio.Queue())
        for ruleset, queue in ruleset_queues
    ]

    rulesets_queue_plans = rule_generator.generate_rulesets(
        ansible_ruleset_queue_plans, variables, inventory
    )
    for rulesets_list in rulesets_queue_plans:
        for rulesets in rulesets_list[1]:
            logger.debug(rulesets.define())

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
            logger.info(str(data))
            if not data:
                await event_log.put(dict(type="EmptyEvent"))
                continue
            logger.info(str(data))
            results = []
            try:
                logger.info("Asserting event")
                try:
                    logger.debug(data)
                    durable.lang.post(ruleset.name, data)
                except durable.engine.MessageObservedException:
                    logger.debug(f"MessageObservedException: {data}")
                except durable.engine.MessageNotHandledException:
                    logger.debug(f"MessageNotHandledException: {data}")
                finally:
                    logger.debug(durable.lang.get_pending_events(ruleset.name))
                while not plan.empty():
                    item = cast(ActionContext, await plan.get())
                    logger.debug(item)
                    result = await call_action(*item, event_log=event_log)
                    results.append(result)

                await event_log.put(
                    dict(type="ProcessedEvent", results=results)
                )
            except durable.engine.MessageNotHandledException:
                logger.info(f"MessageNotHandledException: {data}")
                await event_log.put(dict(type="MessageNotHandled"))
            except ShutdownException:
                await event_log.put(dict(type="Shutdown"))
                return
