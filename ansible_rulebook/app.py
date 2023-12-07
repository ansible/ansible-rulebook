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
from typing import Any, Dict, List, Optional, Tuple

import yaml

from ansible_rulebook import rules_parser as rules_parser
from ansible_rulebook.collection import (
    has_rulebook,
    load_rulebook as collection_load_rulebook,
    split_collection_name,
)
from ansible_rulebook.common import StartupArgs
from ansible_rulebook.conf import settings
from ansible_rulebook.engine import run_rulesets, start_source
from ansible_rulebook.job_template_runner import job_template_runner
from ansible_rulebook.rule_types import RuleSet, RuleSetQueue
from ansible_rulebook.validators import Validate
from ansible_rulebook.websocket import (
    request_workload,
    send_event_log_to_websocket,
)

from .exception import (
    ControllerNeededException,
    InventoryNeededException,
    InventoryNotFound,
    RulebookNotFoundException,
    WebSocketExchangeException,
)


class NullQueue:
    async def put(self, _data):
        pass

    def qsize(self):
        return 0


logger = logging.getLogger(__name__)
INVENTORY_ACTIONS = ("run_playbook", "run_module")
CONTROLLER_ACTIONS = ("run_job_template", "run_workflow_template")


# FIXME(cutwater): Replace parsed_args with clear interface
async def run(parsed_args: argparse.Namespace) -> None:
    file_monitor = None

    if parsed_args.worker and parsed_args.websocket_url and parsed_args.id:
        logger.info("Starting worker mode")
        startup_args = await request_workload(parsed_args.id)
        if not startup_args:
            logger.error("Error communicating with web socket server")
            raise WebSocketExchangeException(
                "Error communicating with web socket server"
            )
    else:
        startup_args = StartupArgs()
        startup_args.variables = load_vars(parsed_args)
        startup_args.rulesets = load_rulebook(
            parsed_args, startup_args.variables
        )
        if parsed_args.hot_reload is True and os.path.exists(
            parsed_args.rulebook
        ):
            logger.critical(
                "HOT-RELOAD: Hot-reload was requested, "
                + "will monitor for rulebook file changes"
            )
            file_monitor = parsed_args.rulebook
        if parsed_args.inventory:
            startup_args.inventory = parsed_args.inventory
        startup_args.project_data_file = parsed_args.project_tarball
        startup_args.controller_url = parsed_args.controller_url
        startup_args.controller_token = parsed_args.controller_token
        startup_args.controller_ssl_verify = parsed_args.controller_ssl_verify

    validate_actions(startup_args)

    if startup_args.check_controller_connection:
        await validate_controller_params(startup_args)

    if parsed_args.websocket_url:
        event_log = asyncio.Queue()
    else:
        event_log = NullQueue()

    logger.info("Starting sources")
    tasks, ruleset_queues = spawn_sources(
        startup_args.rulesets,
        startup_args.variables,
        [parsed_args.source_dir],
        parsed_args.shutdown_delay,
    )

    logger.info("Starting rules")

    feedback_task = None
    if parsed_args.websocket_url:
        feedback_task = asyncio.create_task(
            send_event_log_to_websocket(event_log=event_log)
        )
        tasks.append(feedback_task)

    should_reload = await run_rulesets(
        event_log,
        ruleset_queues,
        startup_args.variables,
        startup_args.inventory,
        parsed_args,
        startup_args.project_data_file,
        file_monitor,
    )

    await event_log.put(dict(type="Exit"))
    if feedback_task:
        await asyncio.wait(
            [feedback_task], timeout=settings.max_feedback_timeout
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
    await job_template_runner.close_session()
    if error_found:
        raise Exception("One of the source plugins failed")
    elif should_reload is True:
        logger.critical("HOT-RELOAD! rules file changed, now restarting")
        await run(parsed_args)


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
def load_rulebook(
    parsed_args: argparse.Namespace, variables: Optional[Dict] = None
) -> List[RuleSet]:
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
            if variables is None:
                variables = {}
            rulesets = rules_parser.parse_rule_sets(data, variables)
    elif has_rulebook(*split_collection_name(parsed_args.rulebook)):
        logger.debug(
            "Loading rules from a collection %s", parsed_args.rulebook
        )
        rulesets = rules_parser.parse_rule_sets(
            collection_load_rulebook(
                *split_collection_name(parsed_args.rulebook)
            )
        )
    else:
        raise RulebookNotFoundException(
            f"Could not find rulebook {parsed_args.rulebook}"
        )

    return rulesets


def spawn_sources(
    rulesets: List[RuleSet],
    variables: Dict[str, Any],
    source_dirs: List[str],
    shutdown_delay: float,
) -> Tuple[List[asyncio.Task], List[RuleSetQueue]]:
    tasks = []
    ruleset_queues = []
    for ruleset in rulesets:
        source_queue = asyncio.Queue(1)
        for source in ruleset.sources:
            task = asyncio.create_task(
                start_source(
                    source,
                    source_dirs,
                    variables,
                    source_queue,
                    shutdown_delay,
                )
            )
            tasks.append(task)
        ruleset_queues.append(RuleSetQueue(ruleset, source_queue))
    return tasks, ruleset_queues


def validate_actions(startup_args: StartupArgs) -> None:
    for ruleset in startup_args.rulesets:
        for rule in ruleset.rules:
            for action in rule.actions:
                if action.action in CONTROLLER_ACTIONS:
                    startup_args.check_controller_connection = True
                if (
                    action.action in INVENTORY_ACTIONS
                    and not startup_args.inventory
                ):
                    raise InventoryNeededException(
                        f"Rule {rule.name} has an action {action.action} "
                        "which needs inventory to be defined"
                    )

                if action.action in INVENTORY_ACTIONS and not os.path.exists(
                    startup_args.inventory
                ):
                    raise InventoryNotFound(
                        f"Inventory {startup_args.inventory} not found"
                    )
                if (
                    action.action in CONTROLLER_ACTIONS
                    and not startup_args.controller_url
                    and not startup_args.controller_token
                ):
                    raise ControllerNeededException(
                        f"Rule {rule.name} has an action {action.action} "
                        "which needs controller url and token to be defined"
                    )


async def validate_controller_params(startup_args: StartupArgs) -> None:
    if startup_args.controller_url:
        job_template_runner.host = startup_args.controller_url
        job_template_runner.token = startup_args.controller_token
        if startup_args.controller_ssl_verify:
            job_template_runner.verify_ssl = startup_args.controller_ssl_verify

        data = await job_template_runner.get_config()
        logger.info("AAP Version %s", data["version"])
