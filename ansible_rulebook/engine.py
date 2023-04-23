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
import runpy
from datetime import datetime
from typing import Any, Dict, List, Optional

from drools.dispatch import establish_async_channel, handle_async_messages

import ansible_rulebook.rule_generator as rule_generator
from ansible_rulebook.collection import (
    find_source,
    find_source_filter,
    has_source,
    has_source_filter,
    split_collection_name,
)
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_set_runner import RuleSetRunner
from ansible_rulebook.rule_types import (
    EventSource,
    EventSourceFilter,
    RuleSetQueue,
)
from ansible_rulebook.util import (
    collect_ansible_facts,
    find_builtin_filter,
    has_builtin_filter,
    substitute_variables,
)

from .exception import (
    SourceFilterNotFoundException,
    SourcePluginMainMissingException,
    SourcePluginNotAsyncioCompatibleException,
    SourcePluginNotFoundException,
)

logger = logging.getLogger(__name__)


all_source_queues = []


async def broadcast(shutdown: Shutdown):
    logger.info(f"Broadcast to queues: {all_source_queues}")
    logger.info(f"Broadcasting shutdown: {shutdown}")
    for queue in all_source_queues:
        await queue.put(shutdown)


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
    shutdown_delay: float = 60.0,
) -> None:

    all_source_queues.append(queue)
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
            raise SourcePluginNotFoundException(
                f"Could not find source plugin for {source.source_name}"
            )

        source_filters = []

        logger.info("load source filters")

        source.source_filters.append(meta_info_filter(source))

        for source_filter in source.source_filters:
            logger.info("loading %s", source_filter.filter_name)
            if os.path.exists(
                os.path.join("event_filter", source_filter.filter_name + ".py")
            ):
                source_filter_module = runpy.run_path(
                    os.path.join(
                        "event_filter", source_filter.filter_name + ".py"
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
            elif has_builtin_filter(source_filter.filter_name):
                source_filter_module = runpy.run_path(
                    find_builtin_filter(source_filter.filter_name)
                )
            else:
                raise SourceFilterNotFoundException(
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
            raise SourcePluginMainMissingException(
                "Entrypoint missing. Source module must have function 'main'."
            )

        # NOTE(cutwater): This check may be unnecessary.
        if not asyncio.iscoroutinefunction(entrypoint):
            raise SourcePluginNotAsyncioCompatibleException(
                "Entrypoint is not a coroutine function."
            )

        await entrypoint(fqueue, args)
        shutdown_msg = (
            f"Source {source.source_name} initiated shutdown at "
            f"{str(datetime.now())}"
        )

    except KeyboardInterrupt:
        shutdown_msg = (
            f"Source {source.source_name} keyboard interrupt, "
            + f"initiated shutdown at {str(datetime.now())}"
        )
        pass
    except asyncio.CancelledError:
        shutdown_msg = (
            f"Source {source.source_name} task cancelled, "
            + f"initiated shutdown at {str(datetime.now())}"
        )
        logger.info("Task cancelled " + shutdown_msg)
    except BaseException as e:
        logger.exception("Source error")
        shutdown_msg = (
            f"Shutting down source: {source.source_name} error : {e}"
        )
        logger.error(shutdown_msg)
        raise
    finally:
        logger.info("Broadcast shutdown to all source plugins")
        asyncio.create_task(
            broadcast(
                Shutdown(
                    message=shutdown_msg,
                    source_plugin=source.source_name,
                    delay=shutdown_delay,
                ),
            )
        )


async def run_rulesets(
    event_log: asyncio.Queue,
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: str = "",
    parsed_args: argparse.ArgumentParser = None,
    project_data_file: Optional[str] = None,
):

    logger.info("run_ruleset")
    rulesets_queue_plans = rule_generator.generate_rulesets(
        ruleset_queues, variables, inventory
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
    reader, writer = await establish_async_channel()
    async_task = asyncio.create_task(
        handle_async_messages(reader, writer), name="drools_async_task"
    )

    for ruleset_queue_plan in rulesets_queue_plans:
        ruleset_runner = RuleSetRunner(
            event_log=event_log,
            ruleset_queue_plan=ruleset_queue_plan,
            hosts_facts=hosts_facts,
            variables=variables,
            project_data_file=project_data_file,
            parsed_args=parsed_args,
            broadcast_method=broadcast,
        )
        task_name = f"main_ruleset :: {ruleset_queue_plan.ruleset.name}"
        ruleset_task = asyncio.create_task(
            ruleset_runner.run_ruleset(), name=task_name
        )
        ruleset_tasks.append(ruleset_task)

    logger.info("Waiting for all ruleset tasks to end")
    await asyncio.wait(ruleset_tasks, return_when=asyncio.FIRST_EXCEPTION)
    async_task.cancel()
    logger.info("Cancelling all ruleset tasks")
    for task in ruleset_tasks:
        if not task.done():
            logger.info("Cancelling " + task.get_name())
            task.cancel()

    logger.info("Waiting on gather")
    asyncio.gather(*ruleset_tasks)
    logger.info("Returning from run_rulesets")


def meta_info_filter(source: EventSource) -> EventSourceFilter:
    source_filter_name = "eda.builtin.insert_meta_info"
    source_filter_args = dict(
        source_name=source.name, source_type=source.source_name
    )
    return EventSourceFilter(source_filter_name, source_filter_args)
