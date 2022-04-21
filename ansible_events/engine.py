import os
import multiprocessing as mp
import runpy
import asyncio
import durable.lang
import select
import traceback

from pprint import pprint, pformat

import ansible_events.rule_generator as rule_generator
from ansible_events.durability import provide_durability
from ansible_events.messages import Shutdown
from ansible_events.util import substitute_variables
from ansible_events.builtin import actions as builtin_actions
from ansible_events.rule_types import (
    EventSource,
    RuleSetQueue,
    RuleSetQueuePlan,
    ActionContext,
)
from ansible_events.rules_parser import parse_hosts

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
    queue: mp.Queue,
) -> None:

    logger = mp.get_logger()

    logger.info("start_source")

    try:
        logger.info("load source")
        module = runpy.run_path(
            os.path.join(source_dirs[0], source.source_name + ".py")
        )

        source_filters = []

        logger.info("load source filters")
        for source_filter in source.source_filters:
            logger.info(f"loading {source_filter.filter_name}")
            source_filter_module = runpy.run_path(
                os.path.join("event_filters", source_filter.filter_name + ".py")
            )
            source_filters.append(
                (source_filter_module["main"], source_filter.filter_args)
            )

        args = {
            k: substitute_variables(v, variables) for k, v in source.source_args.items()
        }
        fqueue = FilteredQueue(source_filters, queue)
        logger.info(f"calling main in {source.source_name}")
        module["main"](fqueue, args)
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
) -> Dict:

    logger = mp.get_logger()
    logger.info(f"call_action {action}")

    if action in builtin_actions:
        try:
            variables_copy = variables.copy()
            if c.m is not None:
                variables_copy["event"] = c.m._d  # event data is stored in c.m._d
                event = c.m._d  # event data is stored in c.m._d
                if 'meta' in event:
                    if 'hosts' in event['meta']:
                        hosts = parse_hosts(event['meta']['hosts'])
            else:
                variables_copy["events"] = c._m
                new_hosts = []
                for event in variables_copy["events"]:
                    if 'meta' in event:
                        if 'hosts' in event['meta']:
                            new_hosts.append(parse_hosts(event['meta']['hosts']))
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
            result = builtin_actions[action](
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
        except Exception as e:
            logger.error(f"Error calling {action}: {e}\n {traceback.format_exc()}")
            result = dict(error=e)
    else:
        raise Exception(f"Action {action} not supported")

    return result


def run_rulesets(
    event_log: mp.Queue,
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: Dict,
    redis_host_name: Optional[str] = None,
    redis_port: Optional[int] = None,
):

    logger = mp.get_logger()

    logger.info("run_ruleset")

    if redis_host_name and redis_port:
        provide_durability(durable.lang.get_host(), redis_host_name, redis_port)

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

    asyncio.run(_run_rulesets_async(event_log, rulesets_queue_plans, inventory))


def json_count(data):
    s = 0
    q = []
    q.append(data)
    while q:
        o = q.pop()
        if isinstance(o, dict):
            s += len(o)
            if len(o) > 255:
                pprint(data)
                raise Exception(
                    f"Only 255 values supported per dictionary found {len(o)}"
                )
            if s > 255:
                pprint(data)
                raise Exception(f"Only 255 values supported per dictionary found {s}")
            for i in o.values():
                q.append(i)


async def _run_rulesets_async(event_log: mp.Queue, rulesets_queue_plans, inventory):

    logger = mp.get_logger()

    queue_readers = {i[2]._reader: i for i in rulesets_queue_plans}  # type: ignore

    while True:
        logger.info("Waiting for event")
        read_ready, _, _ = select.select(queue_readers.keys(), [], [])
        for queue_reader in read_ready:
            ruleset, _, queue, plan = queue_readers[queue_reader]
            data = queue.get()
            json_count(data)
            if isinstance(data, Shutdown):
                event_log.put(dict(type="Shutdown"))
                return
            logger.info(str(data))
            if not data:
                event_log.put(dict(type="EmptyEvent"))
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
                    result = await call_action(*item)
                    results.append(result)

                event_log.put(dict(type="ProcessedEvent", results=results))
            except durable.engine.MessageNotHandledException:
                logger.info(f"MessageNotHandledException: {data}")
                event_log.put(dict(type="MessageNotHandled"))
