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
    ActionContext,
)

from typing import Optional, Dict, List, cast


def start_sources(
    sources: List[EventSource], source_dirs: List[str], variables: Dict, queue: mp.Queue
) -> None:

    logger = mp.get_logger()

    logger.info("start_sources")

    try:

        for source in sources:
            module = runpy.run_path(
                os.path.join(source_dirs[0], source.source_name + ".py")
            )

            args = {
                k: substitute_variables(v, variables)
                for k, v in source.source_args.items()
            }
            module["main"](queue, args)
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
            variables_copy["event"] = c.m._d  # event data is stored in c.m._d
            logger.info(f"substitute_variables {action_args} {variables_copy}")
            action_args = {
                k: substitute_variables(v, variables_copy)
                for k, v in action_args.items()
            }
            logger.info(action_args)
            if facts is None:
                facts = durable.lang.get_facts(ruleset)
            logger.info(f"facts: {durable.lang.get_facts(ruleset)}")
            if 'ruleset' not in action_args:
                action_args['ruleset'] = ruleset
            result = builtin_actions[action](
                inventory=inventory,
                hosts=hosts,
                variables=variables_copy,
                facts=facts,
                **action_args,
            )
        except durable.engine.MessageNotHandledException as e:
            logger.error(f"MessageNotHandledException: {action_args}")
            result = dict(error=e)
        except durable.engine.MessageObservedException as e:
            logger.info(f"MessageObservedException: {action_args}")
            result = dict(error=e)
        except Exception as e:
            logger.error(f"Error calling {action}: {e}")
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

    host_rulesets_queue_plans = rule_generator.generate_host_rulesets(
        ansible_ruleset_queue_plans, variables, inventory
    )
    for host_rulesets_list in host_rulesets_queue_plans:
        for host_rulesets in host_rulesets_list[1]:
            logger.debug(host_rulesets.define())

    asyncio.run(_run_rulesets_async(event_log, host_rulesets_queue_plans, inventory))


async def _run_rulesets_async(
    event_log: mp.Queue, host_rulesets_queue_plans, inventory
):

    logger = mp.get_logger()

    queue_readers = {i[2]._reader: i for i in host_rulesets_queue_plans}  # type: ignore

    while True:
        logger.info("Waiting for event")
        read_ready, _, _ = select.select(queue_readers.keys(), [], [])
        for queue_reader in read_ready:
            global_ruleset, host_rulesets, queue, plan = queue_readers[queue_reader]
            data = queue.get()
            if isinstance(data, Shutdown):
                event_log.put(dict(type="Shutdown"))
                return
            logger.info(str(data))
            if not data:
                event_log.put(dict(type="EmptyEvent"))
                continue
            logger.info(str(data))
            logger.info(str([ruleset.name for ruleset in host_rulesets]))
            results = []
            try:
                logger.info("Asserting event")
                handled = False
                try:
                    logger.debug(data)
                    durable.lang.assert_fact(global_ruleset.name, data)
                    handled = True
                except durable.engine.MessageNotHandledException:
                    logger.debug(f"MessageNotHandledException: {data}")
                for ruleset in host_rulesets:
                    try:
                        durable.lang.assert_fact(ruleset.name, data)
                        handled = True
                    except durable.engine.MessageNotHandledException:
                        logger.debug(f"MessageNotHandledException: {data}")
                if not handled:
                    event_log.put(dict(type="MessageNotHandled"))
                while not plan.empty():
                    run_last_item = True
                    item = cast(ActionContext, await plan.get())
                    logger.debug(item)
                    # Combine run_playbook actions into one action with multiple hosts
                    if item.action == "run_playbook":
                        new_item = item._replace(hosts=[], facts={})
                        logger.debug(f"Extending hosts")
                        while item.action == "run_playbook":
                            logger.debug(f"Adding hosts {item.hosts}")
                            new_item.hosts.extend(item.hosts)
                            if item.hosts:
                                logger.debug('Adding host facts')
                                logger.debug(f'host {item.hosts[0]} = {durable.lang.get_facts(item.ruleset)}')
                                new_item.facts[item.hosts[0]] = durable.lang.get_facts(item.ruleset)
                                logger.debug(f'facts {new_item.facts}')
                            else:
                                logger.debug('Adding facts')
                                new_item.facts['global'] = durable.lang.get_facts(item.ruleset)
                            if plan.empty():
                                run_last_item = False
                                break
                            item = cast(ActionContext, await plan.get())
                        result = await call_action(*new_item)
                        results.append(result)
                        if run_last_item:
                            result = await call_action(*item)
                            results.append(result)

                    # Run all other actions individually
                    else:
                        result = await call_action(*item)
                        results.append(result)

                logger.info("Retracting event")
                durable.lang.retract_fact(global_ruleset.name, data)
                for ruleset in host_rulesets:
                    durable.lang.retract_fact(ruleset.name, data)
                event_log.put(dict(type="ProcessedEvent", results=results))
            except durable.engine.MessageNotHandledException:
                logger.info(f"MessageNotHandledException: {data}")
                event_log.put(dict(type="MessageNotHandled"))
