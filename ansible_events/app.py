import asyncio
import logging
import os
from asyncio.exceptions import CancelledError
from typing import Any, Dict, List, Tuple

import yaml

from ansible_events import rules_parser as rules_parser
from ansible_events.collection import (
    has_rules,
    load_rules as collection_load_rules,
    split_collection_name,
)
from ansible_events.engine import run_rulesets, start_source
from ansible_events.rule_types import RuleSet, RuleSetQueue
from ansible_events.util import load_inventory
from ansible_events.websocket import (
    request_workload,
    send_event_log_to_websocket,
)

logger = logging.getLogger("ansible_events")


# FIXME(cutwater): Replace parsed_args with clear interface
async def run(parsed_args) -> None:

    if parsed_args.worker and parsed_args.websocket_address and parsed_args.id:
        logger.info("Starting worker mode")

        inventory, variables, rulesets = await request_workload(
            int(parsed_args.id), parsed_args.websocket_address
        )
    else:
        inventory = {}
        variables = load_vars(parsed_args)
        rulesets = load_rules(parsed_args)
        if parsed_args.inventory:
            inventory = load_inventory(parsed_args.inventory)

    event_log = asyncio.Queue()

    logger.info("Starting sources")
    tasks, ruleset_queues = spawn_sources(
        rulesets, variables, [parsed_args.source_dir]
    )

    logger.info("Starting rules")

    if parsed_args.websocket_address:
        tasks.append(
            asyncio.create_task(
                send_event_log_to_websocket(
                    event_log, parsed_args.websocket_address
                )
            )
        )

    await run_rulesets(
        event_log,
        ruleset_queues,
        variables,
        inventory,
        parsed_args.redis_host_name,
        parsed_args.redis_port,
    )

    logger.info("Cancelling event source tasks")
    for task in tasks:
        task.cancel()
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception) and not isinstance(
            result, CancelledError
        ):
            logger.error(result)

    logger.info("Main complete")
    await event_log.put(dict(type="Exit"))


# TODO(cutwater): Maybe move to util.py
def load_vars(parsed_args) -> Dict[str, str]:
    variables = dict()
    if parsed_args.vars:
        with open(parsed_args.vars) as f:
            variables.update(yaml.safe_load(f.read()))

    if parsed_args.env_vars:
        for env_var in parsed_args.env_vars.split(","):
            env_var = env_var.strip()
            if env_var not in os.environ:
                raise KeyError(
                    f'Could not find environment variable "{env_var}"'
                )
            variables[env_var] = os.environ[env_var]

    return variables


# TODO(cutwater): Maybe move to util.py
def load_rules(parsed_args) -> List[RuleSet]:
    if not parsed_args.rules:
        logger.debug("Loading no rules")
        return []
    elif os.path.exists(parsed_args.rules):
        logger.debug(f"Loading rules from the file system {parsed_args.rules}")
        with open(parsed_args.rules) as f:
            return rules_parser.parse_rule_sets(yaml.safe_load(f.read()))
    elif has_rules(*split_collection_name(parsed_args.rules)):
        logger.debug(f"Loading rules from a collection {parsed_args.rules}")
        return rules_parser.parse_rule_sets(
            collection_load_rules(*split_collection_name(parsed_args.rules))
        )
    else:
        raise Exception(f"Could not find ruleset {parsed_args.rules}")


def spawn_sources(
    rulesets: List[RuleSet],
    variables: Dict[str, Any],
    source_dirs: List[str],
) -> Tuple[List[asyncio.Task], List[RuleSetQueue]]:
    logger.info("Starting sources")
    tasks = []
    ruleset_queues = []
    for ruleset in rulesets:
        source_queue = asyncio.Queue()
        for source in ruleset.sources:
            task = asyncio.create_task(
                start_source(
                    source,
                    source_dirs,
                    variables,
                    source_queue,
                )
            )
            tasks.append(task)
        ruleset_queues.append(RuleSetQueue(ruleset, source_queue))
    return tasks, ruleset_queues
