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
from typing import Dict, List, Optional

from drools.dispatch import establish_async_channel, handle_async_messages
from drools.ruleset import session_stats
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

import ansible_rulebook.rule_generator as rule_generator
from ansible_rulebook.persistence import enable_persistence
from ansible_rulebook.rule_set_runner import RuleSetRunner
from ansible_rulebook.rule_types import RuleSetQueue
from ansible_rulebook.source_manager import SourceManager
from ansible_rulebook.util import collect_ansible_facts, send_session_stats

from .exception import HotReloadException

logger = logging.getLogger(__name__)


async def heartbeat_task(
    event_log: asyncio.Queue, rule_set_names: List[str], interval: int
):
    while True:
        for name in rule_set_names:
            await send_session_stats(event_log, session_stats(name))
        await asyncio.sleep(interval)


class RulebookFileChangeHandler(FileSystemEventHandler):
    modified = False

    def on_modified(self, event):
        logger.debug(f"Rulebook file {event.src_path} has been modified")
        self.modified = True

    def is_modified(self):
        return self.modified


async def monitor_rulebook(rulebook_file):
    event_handler = RulebookFileChangeHandler()
    to_observe = os.path.abspath(rulebook_file)
    observer = Observer()
    observer.schedule(event_handler, to_observe, recursive=True)
    observer.start()
    try:
        while not event_handler.is_modified():
            await asyncio.sleep(1)
    finally:
        observer.stop()
        observer.join()
        # we need to check if the try-clause completed because
        # while-loop terminated successfully, in such case we
        # follow on the hot-reload use case, or if we got into
        # this finally-clause because of other errors.
        if event_handler.is_modified():
            raise HotReloadException(
                "Rulebook file changed, "
                + "raising exception so to asyncio.FIRST_EXCEPTION "
                + "in order to reload"
            )


async def run_rulesets(
    event_log: asyncio.Queue,
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: str = "",
    parsed_args: argparse.Namespace = None,
    project_data_file: Optional[str] = None,
    file_monitor: str = None,
) -> bool:
    logger.debug("run_ruleset")
    reader, writer = await establish_async_channel()
    async_task = asyncio.create_task(
        handle_async_messages(reader, writer), name="drools_async_task"
    )

    enable_persistence(parsed_args, variables)
    rulesets_queue_plans = rule_generator.generate_rulesets(
        ruleset_queues, variables, inventory
    )

    if not rulesets_queue_plans:
        return

    for ruleset_queue_plan in rulesets_queue_plans:
        logger.debug("ruleset define: %s", ruleset_queue_plan.ruleset.define())

    # Enable leader mode before starting rulesets (needed for Drools
    # initialization)
    from ansible_rulebook.persistence import enable_leader

    enable_leader()

    hosts_facts = []
    ruleset_names = []
    rulesets = {}
    for ruleset, _, _ in ruleset_queues:
        if ruleset.gather_facts and not hosts_facts:
            if inventory:
                hosts_facts = collect_ansible_facts(inventory)
            else:
                logger.warning(
                    "Ignoring gather_facts, since it requires inventory"
                )

        ruleset_names.append(ruleset.name)
        rulesets[ruleset.name] = ruleset

    ruleset_tasks = []
    send_heartbeat_task = None
    if parsed_args and parsed_args.heartbeat > 0 and event_log:
        send_heartbeat_task = asyncio.create_task(
            heartbeat_task(event_log, ruleset_names, parsed_args.heartbeat),
            name="heartbeat_task",
        )

    # Get SourceManager's broadcast method for shutdown handling
    source_manager = SourceManager.get_instance()

    for ruleset_queue_plan in rulesets_queue_plans:
        ruleset_runner = RuleSetRunner(
            event_log=event_log,
            ruleset_queue_plan=ruleset_queue_plan,
            hosts_facts=hosts_facts,
            variables=variables,
            rule_set=rulesets[ruleset_queue_plan.ruleset.name],
            project_data_file=project_data_file,
            parsed_args=parsed_args,
            broadcast_method=source_manager._broadcast_shutdown,
        )
        task_name = "main_ruleset::" + f"{ruleset_queue_plan.ruleset.name}"
        ruleset_task = asyncio.create_task(
            ruleset_runner.run_ruleset(), name=task_name
        )
        ruleset_tasks.append(ruleset_task)

    # Yield control briefly to allow ruleset tasks to initialize
    # This ensures prime_facts() and event loops are ready
    await asyncio.sleep(0)

    # Signal to SourceManager that rulesets are fully initialized
    # This allows start_sources() to proceed when ready
    try:
        source_manager.signal_rulesets_ready()
        logger.info(
            "Signaled to SourceManager that %d rulesets are ready",
            len(ruleset_tasks),
        )
    except Exception as e:
        logger.warning(
            "Could not signal rulesets ready to SourceManager: %s", e
        )

    monitor_task = None
    if file_monitor:
        monitor_task = asyncio.create_task(monitor_rulebook(file_monitor))
        ruleset_tasks.append(monitor_task)

    logger.info("Waiting for all ruleset tasks to end")
    await asyncio.wait(ruleset_tasks, return_when=asyncio.FIRST_EXCEPTION)
    async_task.cancel()
    logger.info("Cancelling all ruleset tasks")
    for task in ruleset_tasks:
        if not task.done():
            logger.info("Cancelling %s", task.get_name())
            task.cancel()

    should_reload = False
    if monitor_task and isinstance(
        monitor_task.exception(), HotReloadException
    ):
        logger.debug("Hot-reload, setting should_reload")
        should_reload = True

    logger.debug("Waiting on gather")
    asyncio.gather(*ruleset_tasks, return_exceptions=True)
    logger.debug("Returning from run_rulesets")
    if send_heartbeat_task:
        send_heartbeat_task.cancel()

    return should_reload
