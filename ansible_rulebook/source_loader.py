#  Copyright 2026 Red Hat, Inc.
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
"""
Source Loader for ansible-rulebook.

This module provides low-level functionality for loading and running event
sources. It handles:
- Loading source plugins from disk, collections, or built-ins
- Applying filters to source events
- Running source entry points
- Error handling and cleanup

This module is used by SourceManager for orchestrating source lifecycle.
"""

import asyncio
import logging
import os
import runpy
from datetime import datetime
from typing import Any, Dict, List, Optional

from drools.ruleset import shutdown as drools_shutdown

from ansible_rulebook.collection import (
    find_source,
    find_source_filter,
    has_source,
    has_source_filter,
    split_collection_name,
)
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import EventSource
from ansible_rulebook.util import (
    find_builtin_filter,
    find_builtin_source,
    has_builtin_filter,
    has_builtin_source,
    substitute_variables,
)

from .exception import (
    SourceFilterNotFoundException,
    SourcePluginMainMissingException,
    SourcePluginNotAsyncioCompatibleException,
    SourcePluginNotFoundException,
)

logger = logging.getLogger(__name__)

# Background tasks set to prevent tasks from being garbage collected
_background_tasks = set()


class FilteredQueue:
    """Queue that applies filters to data before putting it in the queue."""

    def __init__(self, filters, queue: asyncio.Queue):
        self.filters = filters
        self.queue = queue

    def _apply_filters(self, data):
        """Apply all filters to data and return filtered results."""
        if not isinstance(data, list):
            data = [data]

        for f, kwargs in self.filters:
            kwargs = kwargs or {}
            flat_list = []
            for e in data:
                result = f(e, **kwargs)
                if not isinstance(result, list):
                    result = [result]
                for r in result:
                    flat_list.append(r)

            data = flat_list

        return data

    async def put(self, data):
        filtered_data = self._apply_filters(data)
        for e in filtered_data:
            await self.queue.put(e)

    def put_nowait(self, data):
        filtered_data = self._apply_filters(data)
        for e in filtered_data:
            self.queue.put_nowait(e)


async def broadcast(source_queues: List[asyncio.Queue], shutdown: Shutdown):
    """Broadcast shutdown message to all source queues."""
    logger.info(f"Broadcasting shutdown to {len(source_queues)} queues")
    logger.info(f"Shutdown message: {shutdown}")
    for queue in source_queues:
        await queue.put(shutdown)


def meta_info_filter(source: EventSource):
    """Create a meta info filter for a source."""
    from ansible_rulebook.rule_types import EventSourceFilter

    source_filter_name = "eda.builtin.insert_meta_info"
    source_filter_args = {
        "source_name": source.name,
        "source_type": source.source_name,
    }
    return EventSourceFilter(source_filter_name, source_filter_args)


def _load_source_module(source: EventSource, source_dirs: List[str]) -> dict:
    """Load the source module from available locations."""
    # Search all configured source directories
    if source_dirs:
        for source_dir in source_dirs:
            if source_dir and os.path.exists(
                os.path.join(source_dir, source.source_name + ".py")
            ):
                return runpy.run_path(
                    os.path.join(source_dir, source.source_name + ".py")
                )

    # Fall back to built-in sources
    if has_builtin_source(source.source_name):
        return runpy.run_path(find_builtin_source(source.source_name))
    elif has_source(*split_collection_name(source.source_name)):
        return runpy.run_path(
            find_source(*split_collection_name(source.source_name))
        )
    else:
        raise SourcePluginNotFoundException(source_name=source.source_name)


def _load_filter_module(filter_name: str, filter_dirs: Optional[list[str]]):
    """Load a filter module from available locations."""
    # Search all configured filter directories
    if filter_dirs:
        for filter_dir in filter_dirs:
            if filter_dir and os.path.exists(
                os.path.join(filter_dir, filter_name + ".py")
            ):
                return runpy.run_path(
                    os.path.join(filter_dir, filter_name + ".py")
                )

    # Check event_filter directory
    if os.path.exists(os.path.join("event_filter", filter_name + ".py")):
        return runpy.run_path(
            os.path.join("event_filter", filter_name + ".py")
        )

    # Fall back to collection and built-in filters
    if has_source_filter(*split_collection_name(filter_name)):
        return runpy.run_path(
            find_source_filter(*split_collection_name(filter_name))
        )
    elif has_builtin_filter(filter_name):
        return runpy.run_path(find_builtin_filter(filter_name))
    else:
        raise SourceFilterNotFoundException(source_filter_name=filter_name)


def _load_source_filters(
    source: EventSource, filter_dirs: Optional[list[str]]
) -> List:
    """Load all filters for a source."""
    # Build a local combined list to avoid mutating source.source_filters
    # which would accumulate duplicates on reuse/restart
    all_filters = list(source.source_filters) + [meta_info_filter(source)]

    source_filters = []
    for source_filter in all_filters:
        logger.info("loading source filter %s", source_filter.filter_name)
        source_filter_module = _load_filter_module(
            source_filter.filter_name, filter_dirs
        )
        source_filters.append(
            (source_filter_module["main"], source_filter.filter_args)
        )
    return source_filters


def _create_shutdown_message(source_name: str, reason: str = None) -> str:
    """Create a shutdown message for a source."""
    timestamp = str(datetime.now())
    if reason:
        return (
            f"Source {source_name} {reason}, initiated shutdown at {timestamp}"
        )
    return f"Source {source_name} initiated shutdown at {timestamp}"


async def _broadcast_shutdown(
    shutdown: Shutdown,
    broadcast_callback,
    queue: asyncio.Queue,
):
    """Broadcast shutdown message using callback or direct queue put."""
    if broadcast_callback:
        try:
            task = asyncio.create_task(broadcast_callback(shutdown))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
        except Exception as e:
            logger.warning(f"Could not broadcast shutdown: {e}")
    else:
        # Fallback for direct usage without SourceManager
        await queue.put(shutdown)


async def start_source(
    source: EventSource,
    source_dirs: List[str],
    variables: Dict[str, Any],
    queue: asyncio.Queue,
    shutdown_delay: float = 60.0,
    filter_dirs: Optional[list[str]] = None,
    source_feedback_queue: asyncio.Queue = None,
    broadcast_callback=None,
) -> None:
    """
    Start a single event source.

    This function loads a source plugin, applies filters, and runs it until
    completion or error. On shutdown, it broadcasts a shutdown message.

    Args:
        source: EventSource configuration
        source_dirs: Directories to search for source plugins
        variables: Variables to substitute in source args
        queue: Queue to send events to
        shutdown_delay: Delay before shutdown (seconds)
        filter_dirs: Directories to search for filter plugins
        source_feedback_queue: Optional feedback queue for source
        broadcast_callback: Optional callback to broadcast shutdown
    """
    shutdown_msg = ""
    try:
        logger.info("load source %s", source.source_name)
        module = _load_source_module(source, source_dirs)
        source_filters = _load_source_filters(source, filter_dirs)

        args = {
            k: substitute_variables(v, variables)
            for k, v in source.source_args.items()
        }
        fqueue = FilteredQueue(source_filters, queue)
        logger.debug("Calling main in %s", source.source_name)

        try:
            entrypoint = module["main"]
        except KeyError:
            raise SourcePluginMainMissingException(
                source_name=source.source_name
            )

        # NOTE(cutwater): This check may be unnecessary.
        if not asyncio.iscoroutinefunction(entrypoint):
            raise SourcePluginNotAsyncioCompatibleException(
                source_name=source.source_name
            )

        if source_feedback_queue:
            args["eda_feedback_queue"] = source_feedback_queue
        await entrypoint(fqueue, args)
        shutdown_msg = _create_shutdown_message(source.source_name)

    except KeyboardInterrupt:
        shutdown_msg = _create_shutdown_message(
            source.source_name, "keyboard interrupt"
        )
        drools_shutdown()
    except asyncio.CancelledError:
        shutdown_msg = _create_shutdown_message(
            source.source_name, "task cancelled"
        )
        logger.debug("Task cancelled: %s", shutdown_msg)
        raise
    except BaseException as e:
        error_msg = str(e)
        error_type = str(type(e)).split(".")[-1].replace("'>", "")
        if not error_msg:
            user_msg = (
                f"Unknown error {error_type}: "
                "source plugin failed with no error message."
            )
        else:
            user_msg = (
                f"{error_type}: Source plugin failed with error message: "
                f"'{error_msg}'"
            )
        logger.error("Source error: %s", user_msg)
        shutdown_msg = f"Shutting down source: {source.source_name}"
        logger.error(shutdown_msg)
        raise
    finally:
        logger.debug("Broadcast shutdown to all source plugins")
        shutdown = Shutdown(
            message=shutdown_msg,
            source_plugin=source.source_name,
            delay=shutdown_delay,
        )
        await _broadcast_shutdown(shutdown, broadcast_callback, queue)
