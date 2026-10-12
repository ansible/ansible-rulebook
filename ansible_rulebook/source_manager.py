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
Source Manager for ansible-rulebook.

This module provides a singleton SourceManager class that handles the
lifecycle of event sources.

The manager uses a two-phase initialization:
1. initialize() - Creates queues and prepares infrastructure (happens
   immediately)
2. start_sources() - Spawns source tasks (happens after rulesets are ready)

This allows the rule engine and heartbeats to start before sources are
active.
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import EventSource, RuleSet, RuleSetQueue
from ansible_rulebook.source_loader import broadcast, start_source

logger = logging.getLogger(__name__)

# Background tasks set to prevent tasks from being garbage collected
_background_tasks = set()


class SourceManager:
    """
    Singleton manager for event source lifecycle.

    Handles initialization, starting, and stopping of event sources.

    Two-Phase Lifecycle:
    1. Initialize phase - Sets up queues, feedback queues, and infrastructure
    2. Execution phase - Starts/stops source tasks

    Usage:
        # Get singleton instance
        manager = SourceManager.get_instance()

        # Phase 1: Initialize (creates queues, prepares rulesets)
        ruleset_queues = manager.initialize(
            rulesets=rulesets,
            variables=variables,
            source_dirs=[source_dir],
            shutdown_delay=60.0,
            filter_dirs=[filter_dir]
        )

        # Phase 2a: Start sources (after rulesets are ready)
        await manager.start_sources()

        # Phase 2b: Stop sources
        await manager.stop_sources()

    The manager is a singleton to ensure consistent state across the
    application.
    """

    _instance: Optional["SourceManager"] = None
    _lock = asyncio.Lock()

    def __init__(self):
        """
        Private constructor - use get_instance() instead.
        """
        if SourceManager._instance is not None:
            raise RuntimeError(
                "SourceManager is a singleton. Use get_instance() instead."
            )

        # Configuration
        self._rulesets: List[RuleSet] = []
        self._variables: Dict[str, Any] = {}
        self._source_dirs: List[str] = []
        self._shutdown_delay: float = 60.0
        self._filter_dirs: List[str] = []
        self._event_log = None

        # Infrastructure (created during initialize)
        self._ruleset_queues: List[RuleSetQueue] = []
        self._source_queue_map: Dict[str, asyncio.Queue] = {}
        self._feedback_queue_map: Dict[str, Dict[str, asyncio.Queue]] = {}

        # Execution state (managed during start/stop)
        self._source_tasks: List[asyncio.Task] = []
        self._initialized = False
        self._sources_running = False

        # Coordination event for ruleset initialization
        self._rulesets_ready_event = asyncio.Event()

    @classmethod
    def get_instance(cls) -> "SourceManager":
        """
        Get the singleton instance of SourceManager.

        Returns:
            The singleton SourceManager instance.
        """
        if cls._instance is None:
            cls._instance = SourceManager()
        return cls._instance

    @classmethod
    async def get_instance_async(cls) -> "SourceManager":
        """
        Get the singleton instance of SourceManager (async-safe).

        This is the async-safe version that uses a lock to prevent race
        conditions.

        Returns:
            The singleton SourceManager instance.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = SourceManager()
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """
        Reset the singleton instance (primarily for testing).

        Warning: This should only be used in tests or when completely
        reinitializing the application.
        """
        cls._instance = None

    def initialize(
        self,
        rulesets: List[RuleSet],
        variables: Dict[str, Any],
        source_dirs: List[str],
        shutdown_delay: float,
        filter_dirs: List[str],
        event_log=None,
    ) -> List[RuleSetQueue]:
        """
        Phase 1: Initialize the source manager.

        This creates all the queues and prepares the infrastructure needed
        for sources and rulesets. This phase does NOT start the sources
        yet.

        This allows the rule engine to start before sources are running.

        Args:
            rulesets: List of rulesets to manage
            variables: Variables to pass to sources
            source_dirs: Directories to search for source plugins
            shutdown_delay: Delay before shutdown (seconds)
            filter_dirs: Directories to search for filter plugins
            event_log: Optional the WebSocket Eventlog to send feedback

        Returns:
            List of RuleSetQueue objects that can be passed to run_rulesets()

        Raises:
            RuntimeError: If already initialized
        """
        if self._initialized:
            raise RuntimeError(
                "SourceManager already initialized. "
                "Call reset_instance() first if reinitializing."
            )

        logger.info("Initializing SourceManager")

        # Store configuration
        self._rulesets = rulesets
        self._variables = variables
        self._source_dirs = source_dirs
        self._shutdown_delay = shutdown_delay
        self._filter_dirs = filter_dirs
        self._event_log = event_log

        # Create queues and feedback infrastructure for each ruleset
        self._ruleset_queues = []

        for ruleset in rulesets:
            # Create source queue for this ruleset
            source_queue = asyncio.Queue(1)
            source_feedback_queues = {}
            source_names = []

            # Process each source in the ruleset
            for source in ruleset.sources:
                # Check if this source needs a feedback queue
                feedback_queue = self._get_feedback_queue(
                    source, source_names, source_feedback_queues
                )
                if feedback_queue:
                    source_feedback_queues[source.name] = feedback_queue

                source_names.append(source.name)

                # Map source to its queue for later reference
                source_key = f"{ruleset.name}" + "::" + f"{source.name}"
                self._source_queue_map[source_key] = source_queue

            # Store feedback queues for this ruleset
            self._feedback_queue_map[ruleset.name] = source_feedback_queues

            # Create RuleSetQueue
            ruleset_queue = RuleSetQueue(
                ruleset, source_queue, source_feedback_queues
            )
            self._ruleset_queues.append(ruleset_queue)

        self._initialized = True
        logger.info(
            f"SourceManager initialized: {len(self._ruleset_queues)} "
            f"rulesets, {len(self._source_queue_map)} sources prepared"
        )

        return self._ruleset_queues

    async def start_sources(self) -> List[asyncio.Task]:
        """
        Phase 2: Start all event sources.

        Waits for rulesets to be ready, then starts all sources.
        If persistence is enabled, enables leader mode in drools.

        Returns:
            List of asyncio tasks for the sources

        Raises:
            RuntimeError: If not initialized or sources already running
        """
        if not self._initialized:
            raise RuntimeError(
                "SourceManager not initialized. Call initialize() first."
            )

        if self._sources_running:
            logger.warning(
                "Sources already running. Call stop_sources() first "
                "before starting again."
            )
            return self._source_tasks

        # Wait for rulesets to be ready before starting sources
        # Add timeout to prevent hanging if rulesets fail to initialize
        logger.info("Waiting for rulesets to be ready...")
        try:
            await asyncio.wait_for(
                self._rulesets_ready_event.wait(), timeout=60.0
            )
            logger.info("Rulesets ready - starting sources")
        except asyncio.TimeoutError:
            logger.error(  # NOSONAR
                "Timeout waiting for rulesets to be ready. "
                "Rulesets may have failed to initialize."
            )
            raise RuntimeError(
                "Timeout waiting for rulesets to be ready after 60 seconds"
            )

        logger.info("Starting sources")

        self._source_tasks = []

        for ruleset in self._rulesets:
            # Get the source queue for this ruleset
            for source in ruleset.sources:
                source_key = f"{ruleset.name}" + "::" + f"{source.name}"
                source_queue = self._source_queue_map[source_key]

                # Get feedback queue if exists
                feedback_queues = self._feedback_queue_map.get(
                    ruleset.name, {}
                )
                feedback_queue = feedback_queues.get(source.name)

                # Create and start the source task
                logger.info(
                    f"Starting source: {source.name} "
                    f"(ruleset: {ruleset.name})"
                )
                task = asyncio.create_task(
                    start_source(
                        source,
                        self._source_dirs,
                        self._variables,
                        source_queue,
                        self._shutdown_delay,
                        self._filter_dirs,
                        feedback_queue,
                        broadcast_callback=self._broadcast_shutdown,
                    ),
                    name=f"source_{ruleset.name}_{source.name}",
                )
                self._source_tasks.append(task)

        self._sources_running = True
        logger.info(f"Started {len(self._source_tasks)} source tasks")

        return self._source_tasks

    async def _broadcast_shutdown(self, shutdown: Shutdown) -> None:
        """
        Internal method to broadcast shutdown to all source queues.

        Args:
            shutdown: Shutdown message to broadcast
        """
        # Get unique queues by id (multiple sources may share same queue)
        seen_queue_ids = set()
        source_queues = []
        for queue in self._source_queue_map.values():
            queue_id = id(queue)
            if queue_id not in seen_queue_ids:
                seen_queue_ids.add(queue_id)
                source_queues.append(queue)
        await broadcast(source_queues, shutdown)

    async def stop_sources(
        self, reason: str = "Shutdown requested", broadcast: bool = True
    ) -> None:
        """
        Stop all running sources.

        This optionally broadcasts a shutdown message to all sources and
        cancels their tasks.

        Args:
            reason: Reason for stopping (used in shutdown message)
            broadcast: Whether to broadcast shutdown message (default True)
        """
        if not self._sources_running:
            logger.info("No sources running, nothing to stop")
            return

        logger.info(f"Stopping sources: {reason}")

        # Broadcast shutdown to all sources if requested
        if broadcast:
            try:
                await self._broadcast_shutdown(
                    Shutdown(
                        message=reason,
                        delay=0,  # Immediate shutdown
                        kind="graceful",
                    )
                )
            except Exception as e:
                logger.error(f"Error broadcasting shutdown: {e}")  # NOSONAR

        # Cancel all source tasks
        cancelled_count = 0
        for task in self._source_tasks:
            if not task.done():
                task.cancel()
                cancelled_count += 1

        logger.info(f"Cancelled {cancelled_count} source tasks")

        # Wait for all tasks to complete (with timeout)
        try:
            await asyncio.wait_for(
                asyncio.gather(*self._source_tasks, return_exceptions=True),
                timeout=self._shutdown_delay,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Source shutdown timed out after {self._shutdown_delay}s"
            )

        # Clear the task list
        self._source_tasks = []
        self._sources_running = False

        logger.info("All sources stopped")

    def _get_feedback_queue(
        self,
        source: EventSource,
        source_names: List[str],
        source_feedback_queues: Dict[str, asyncio.Queue],
    ) -> Optional[asyncio.Queue]:
        """
        Determine if a source needs a feedback queue and create it if needed.

        This is a helper method that replicates the logic from app.py.

        Args:
            source: The event source
            source_names: List of source names already processed
            source_feedback_queues: Dict of existing feedback queues

        Returns:
            A feedback queue if needed, None otherwise
        """
        if not source.source_args:
            return None

        if not source.source_args.get("feedback", False):
            return None

        # Check for duplicate source names (same logic as app.py)
        from ansible_rulebook.conf import settings
        from ansible_rulebook.exception import (
            DuplicateSourceNamesException,
            SourcePluginFeedbackMisconfiguredException,
        )

        # Check if persistence is enabled (required for feedback)
        if settings.persistence_id is None:
            raise SourcePluginFeedbackMisconfiguredException(
                source_name=source.name
            )

        # Check for duplicate source names
        if (
            source.name in source_feedback_queues
            or source.name in source_names
        ):
            raise DuplicateSourceNamesException(source_name=source.name)

        # Create feedback queue
        return asyncio.Queue(1)

    def get_ruleset_queues(self) -> List[RuleSetQueue]:
        """
        Get the list of RuleSetQueue objects.

        Returns:
            List of RuleSetQueue objects created during initialization

        Raises:
            RuntimeError: If not initialized
        """
        if not self._initialized:
            raise RuntimeError(
                "SourceManager not initialized. Call initialize() first."
            )
        return self._ruleset_queues

    def is_initialized(self) -> bool:
        """Check if the manager is initialized."""
        return self._initialized

    def is_running(self) -> bool:
        """Check if sources are currently running."""
        return self._sources_running

    def signal_rulesets_ready(self) -> None:
        """
        Signal that rulesets are fully initialized and ready.

        This should be called by the engine after:
        1. All rulesets have been defined in Drools
        2. RuleSetRunner tasks have been created and started
        3. Event processing loops are ready

        This allows start_sources() to proceed when the system is fully
        ready to process events.
        """
        logger.info("Signaling that rulesets are ready")
        self._rulesets_ready_event.set()

    def get_source_tasks(self) -> List[asyncio.Task]:
        """
        Get the list of source tasks.

        Returns:
            List of asyncio tasks for running sources
        """
        return self._source_tasks

    async def cleanup(self) -> None:
        """
        Clean up the source manager.

        Stops all sources and resets the state. Use this for graceful shutdown.
        Clears all stored configuration including variables and event logs
        to prevent retention of sensitive runtime data.
        """
        if self._sources_running:
            await self.stop_sources("Manager cleanup")

        self._initialized = False
        self._ruleset_queues = []
        self._source_queue_map = {}
        self._feedback_queue_map = {}
        self._source_tasks = []
        # Reset the ready event for next initialization
        self._rulesets_ready_event = asyncio.Event()

        # Clear stored configuration to prevent retention of runtime data
        self._rulesets = []
        self._variables = {}
        self._source_dirs = []
        self._filter_dirs = []
        self._event_log = None

        logger.info("SourceManager cleaned up")
