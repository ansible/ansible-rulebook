import asyncio
import logging
import os
import runpy
from datetime import datetime
from pprint import pformat
from typing import Any, Dict, List, Optional, cast

if os.environ.get("RULES_ENGINE", "drools") == "drools":
    from drools import ruleset as lang
    from drools.exceptions import (
        MessageNotHandledException,
        MessageObservedException,
    )
else:
    from durable import lang
    from durable.engine import (
        MessageObservedException,
        MessageNotHandledException,
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
    RuleSetQueuePlan,
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
    finally:
        await queue.put(Shutdown())


async def call_action(
    ruleset: str,
    rule: str,
    action: str,
    action_args: Dict,
    variables: Dict,
    inventory: Dict,
    hosts: List,
    facts: Dict,
    rules_engine_result,
    event_log,
    project_data_file: Optional[str] = None,
) -> Dict:

    logger.info("call_action %s", action)

    if action in builtin_actions:
        try:
            single_match = None
            if os.environ.get("RULES_ENGINE", "drools") == "drools":
                keys = list(rules_engine_result.data.keys())
                if len(keys) == 1:
                    single_match = rules_engine_result.data[keys[0]]
                else:
                    multi_match = rules_engine_result.data
            else:
                if rules_engine_result.m is not None:
                    single_match = rules_engine_result.m._d
                else:
                    multi_match = rules_engine_result._m
            variables_copy = variables.copy()
            if single_match:
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
                "substitute_variables [%s] [%s]", action_args, variables_copy
            )
            action_args = {
                k: substitute_variables(v, variables_copy)
                for k, v in action_args.items()
            }
            logger.info("action args: %s", action_args)

            if "ruleset" not in action_args:
                action_args["ruleset"] = ruleset

            return await builtin_actions[action](
                event_log=event_log,
                inventory=inventory,
                hosts=hosts,
                variables=variables_copy,
                facts=facts,
                project_data_file=project_data_file,
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
            logger.info(e.message)
            result = dict(error=e.message)
        except MessageObservedException as e:
            logger.info(e.message)
            result = dict(error=e.message)
        except ShutdownException:
            raise
        except Exception as e:
            logger.exception("Error calling %s", action)
            result = dict(error=str(e))
    else:
        logger.error("Action %s not supported", action)
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
    project_data_file: Optional[str] = None,
):

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
        ruleset_task = asyncio.create_task(
            run_ruleset(
                event_log,
                ruleset_queue_plan,
                hosts_facts,
                variables,
                project_data_file,
            )
        )
        ruleset_tasks.append(ruleset_task)

    await asyncio.wait(ruleset_tasks, return_when=asyncio.FIRST_COMPLETED)
    logger.info("Canceling all ruleset tasks")
    for task in ruleset_tasks:
        task.cancel()


async def run_ruleset(
    event_log: asyncio.Queue,
    ruleset_queue_plan: EngineRuleSetQueuePlan,
    hosts_facts: List[Dict],
    variables: Dict,
    project_data_file: Optional[str] = None,
):

    name = ruleset_queue_plan.ruleset.name

    prime_facts(name, hosts_facts, variables)

    logger.info("Waiting for event from %s", name)
    while True:
        data = await ruleset_queue_plan.queue.get()
        json_count(data)
        if isinstance(data, Shutdown):
            await event_log.put(dict(type="Shutdown"))
            if os.environ.get("RULES_ENGINE", "drools") == "drools":
                lang.end_session(name)
            return
        if not data:
            await event_log.put(dict(type="EmptyEvent"))
            continue
        results = []
        try:
            try:
                lang.post(name, data)
            except MessageObservedException:
                logger.debug("MessageObservedException: %s", data)
            except MessageNotHandledException:
                logger.debug("MessageNotHandledException: %s", data)
            finally:
                logger.debug(lang.get_pending_events(name))

            while not ruleset_queue_plan.plan.empty():
                item = cast(ActionContext, await ruleset_queue_plan.plan.get())
                result = await call_action(
                    *item,
                    event_log=event_log,
                    project_data_file=project_data_file,
                )
                results.append(result)

            await event_log.put(dict(type="ProcessedEvent", results=results))
        except MessageNotHandledException:
            logger.info("MessageNotHandledException: %s", data)
            await event_log.put(dict(type="MessageNotHandled"))
        except ShutdownException:
            await event_log.put(dict(type="Shutdown"))
            if os.environ.get("RULES_ENGINE", "drools") == "drools":
                lang.end_session(name)
            return
        except Exception:
            logger.exception("Error calling %s", data)


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
