"""
Usage:
    ansible-events [options]

Options:
    -h, --help                  Show this page
    -v, --vars=<v>              Variables file
    -i, --inventory=<i>         Inventory
    --rules=<r>                 The rules file or rules from a collection
    -S=<S>, --source_dir=<S>    Source dir
    --vars=<v>                  A vars file
    --env-vars=<e>              Comma separated list of variables to import
                                from the environment
    --redis_host_name=<h>       Redis host name
    --redis_port=<p>            Redis port
    --debug                     Show debug logging
    --verbose                   Show verbose logging
    --version                   Show the version and exit
    --websocket-address=<w>     Connect the event log to a websocket
    --id=<i>                    Identifier
"""
import argparse
import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Tuple

import yaml

import ansible_events
import ansible_events.rules_parser as rules_parser
from ansible_events.collection import (
    has_rules,
    load_rules as collection_load_rules,
    split_collection_name,
)
from ansible_events.conf import settings
from ansible_events.engine import run_rulesets, start_source
from ansible_events.rule_types import RuleSet, RuleSetQueue
from ansible_events.util import load_inventory
from ansible_events.websocket import send_event_log_to_websocket

logger = logging.getLogger("ansible_events")


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


def get_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rules")
    parser.add_argument("--vars")
    parser.add_argument("--env-vars")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("--redis-host-name")
    parser.add_argument("--redis-port")
    parser.add_argument("-S", "--source-dir")
    parser.add_argument("-i", "--inventory")
    parser.add_argument("--websocket-address")
    parser.add_argument("--id")
    return parser


async def main(args):
    """Console script for ansible_events."""
    parser = get_parser()
    parsed_args = parser.parse_args(args)
    if parsed_args.id:
        settings.identifier = parsed_args.id
    if parsed_args.version:
        print(ansible_events.__version__)
        print(settings.identifier)
        return 0
    if parsed_args.debug:
        logging.basicConfig(level=logging.DEBUG)
    elif parsed_args.verbose:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)
    variables = load_vars(parsed_args)
    rulesets = load_rules(parsed_args)
    if parsed_args.inventory:
        inventory = load_inventory(parsed_args.inventory)
    else:
        inventory = {}

    event_log: asyncio.Queue = asyncio.Queue()

    logger.info("Starting sources")
    tasks, ruleset_queues = spawn_sources(
        rulesets, variables, [parsed_args.source_dir]
    )
    num_sources = len(tasks)

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
        num_sources,
        variables,
        inventory,
        parsed_args.redis_host_name,
        parsed_args.redis_port,
    )

    logger.info("Cancelling event source tasks")
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks)

    logger.info("Main complete")
    await event_log.put(dict(type="Exit"))

    return 0


def entry_point() -> None:
    asyncio.run(main(sys.argv[1:]))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))  # pragma: no cover
