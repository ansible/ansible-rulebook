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
from asyncio.exceptions import CancelledError
from typing import Any, Dict, List, Tuple

import yaml

from ansible_rulebook import rules_parser as rules_parser
from ansible_rulebook.collection import (
    has_rulebook,
    load_rulebook as collection_load_rulebook,
    split_collection_name,
)
from ansible_rulebook.engine import run_rulesets, start_source
from ansible_rulebook.rule_types import RuleSet, RuleSetQueue
from ansible_rulebook.util import load_inventory
from ansible_rulebook.validators import Validate
from ansible_rulebook.websocket import (
    request_workload,
    send_event_log_to_websocket,
)


class NullQueue:
    async def put(self, _data):
        pass


logger = logging.getLogger(__name__)


# FIXME(cutwater): Replace parsed_args with clear interface
async def run(parsed_args: argparse.ArgumentParser) -> None:

    if parsed_args.worker and parsed_args.websocket_address and parsed_args.id:
        logger.info("Starting worker mode")

        (
            inventory,
            variables,
            rulesets,
            project_data_file,
        ) = await request_workload(
            int(parsed_args.id), parsed_args.websocket_address
        )
    else:
        inventory = {}
        variables = load_vars(parsed_args)
        rulesets = load_rulebook(parsed_args)
        if parsed_args.inventory:
            inventory = load_inventory(parsed_args.inventory)
        project_data_file = parsed_args.project_tarball

    if parsed_args.websocket_address:
        event_log = asyncio.Queue()
    else:
        event_log = NullQueue()

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
        parsed_args,
        project_data_file,
    )

    logger.info("Cancelling event source tasks")
    for task in tasks:
        task.cancel()

    error_found = False
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        if isinstance(result, Exception) and not isinstance(
            result, CancelledError
        ):
            logger.error(result)
            error_found = True

    logger.info("Main complete")
    await event_log.put(dict(type="Exit"))
    if error_found:
        raise Exception("One of the source plugins failed")


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
                    f"Could not find environment variable {env_var!r}"
                )
            variables[env_var] = os.environ[env_var]

    return variables


# TODO(cutwater): Maybe move to util.py
def load_rulebook(parsed_args) -> List[RuleSet]:
    if not parsed_args.rulebook:
        logger.debug("Loading no rules")
        return []
    elif os.path.exists(parsed_args.rulebook):
        logger.debug(
            "Loading rules from the file system %s", parsed_args.rulebook
        )
        with open(parsed_args.rulebook) as f:
            data = yaml.safe_load(f.read())
            Validate.rulebook(data)
            return rules_parser.parse_rule_sets(data)
    elif has_rulebook(*split_collection_name(parsed_args.rulebook)):
        logger.debug(
            "Loading rules from a collection %s", parsed_args.rulebook
        )
        return rules_parser.parse_rule_sets(
            collection_load_rulebook(
                *split_collection_name(parsed_args.rulebook)
            )
        )
    else:
        raise Exception(f"Could not find ruleset {parsed_args.rulebook}")


def spawn_sources(
    rulesets: List[RuleSet],
    variables: Dict[str, Any],
    source_dirs: List[str],
) -> Tuple[List[asyncio.Task], List[RuleSetQueue]]:
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
