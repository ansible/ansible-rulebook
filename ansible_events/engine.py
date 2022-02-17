import os
import multiprocessing as mp
import runpy
import asyncio
import durable.lang
import select

import ansible_events.rule_generator as rule_generator
from ansible_events.durability import provide_durability
from ansible_events.messages import Shutdown
from ansible_events.util import substitute_variables
from ansible_events.builtin import actions as builtin_actions
from ansible_events.rule_types import (
    EventSource,
    RuleSetQueue,
    RuleSetQueuePlan,
    RuleSetPlan,
    ActionContext,
)

from typing import Optional, Dict, List, cast


def start_sources(sources: List[EventSource], source_dirs: List[str], variables: Dict, queue: mp.Queue) -> None:

    logger = mp.get_logger()

    logger.info("start_sources")

    try:

        for source in sources:
            module = runpy.run_path(os.path.join(source_dirs[0], source.source_name + ".py"))

            args = {
                k: substitute_variables(v, variables) for k, v in source.source_args.items()
            }
            module["main"](queue, args)
    finally:
        queue.put(Shutdown())


async def call_action(
    action: str,
    action_args: Dict,
    variables: Dict,
    inventory: Dict,
    c,
) -> Dict:

    logger = mp.get_logger()

    if action in builtin_actions:
        try:
            variables_copy = variables.copy()
            variables_copy["event"] = c.m._d
            action_args = {
                k: substitute_variables(v, variables_copy)
                for k, v in action_args.items()
            }
            logger.info(action_args)
            result = builtin_actions[action](**action_args)
        except Exception as e:
            logger.error(e)
            result = dict(error=e)
    else:
        raise Exception(f'Action {action} not supported')

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

    ruleset_queue_plans = [
        RuleSetQueuePlan(ruleset, queue, asyncio.Queue())
        for ruleset, queue in ruleset_queues
    ]
    ruleset_plans = [
        RuleSetPlan(ruleset, plan) for ruleset, _, plan in ruleset_queue_plans
    ]
    rulesets = [ruleset for ruleset, _, _ in ruleset_queue_plans]

    logger.info(str([rulesets]))
    durable_rulesets = rule_generator.generate_rulesets(
        ruleset_plans, variables, inventory
    )
    print(str([x.define() for x in durable_rulesets]))
    logger.info(str([x.define() for x in durable_rulesets]))

    asyncio.run(_run_rulesets_async(event_log, ruleset_queue_plans))


async def _run_rulesets_async(
    event_log: mp.Queue,
    ruleset_queue_plans: List[RuleSetQueuePlan],
):

    logger = mp.get_logger()

    gate_cache: Dict = dict()

    rulesets = [ruleset for ruleset, _, _ in ruleset_queue_plans]

    queue_readers = {i[1]._reader: i for i in ruleset_queue_plans}  # type: ignore

    while True:
        logger.info("Waiting for event")
        read_ready, _, _ = select.select(queue_readers.keys(), [], [])
        for queue_reader in read_ready:
            ruleset, queue, plan = queue_readers[queue_reader]
            data = queue.get()
            if isinstance(data, Shutdown):
                event_log.put(dict(type='Shutdown'))
                return
            logger.info(str(data))
            if not data:
                event_log.put(dict(type='EmptyEvent'))
                continue
            logger.info(str(data))
            logger.info(str(ruleset.name))
            try:
                logger.info("Asserting event")
                durable.lang.assert_fact(ruleset.name, data)
                while not plan.empty():
                    item = cast(ActionContext, await plan.get())
                    logger.info(item)
                    result = await call_action(
                        *item,
                    )

                logger.info("Retracting event")
                durable.lang.retract_fact(ruleset.name, data)
                event_log.put(dict(type='ProcessedEvent', result=result))
            except durable.engine.MessageNotHandledException:
                logger.error(f"MessageNotHandledException: {data}")
                event_log.put(dict(type='MessageNotHandled'))
