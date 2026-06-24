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
"""Back pressure management for ansible-rulebook.

This module provides back pressure mechanisms to prevent system overload
when actions or reporting queues reach capacity.
"""

import asyncio
import logging
import time
from typing import Optional

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    TimedOutActionsException,
    TimedOutReportingException,
)

logger = logging.getLogger(__name__)


class BackPressureManager:
    """Manages back pressure for actions and reporting queues.

    This class implements back pressure mechanisms to prevent the system
    from being overwhelmed when:
    - Too many actions are running concurrently
    - The reporting queue is full and cannot drain to EDA Server

    Attributes:
        event_log: AsyncIO Queue for reporting/audit events
    """

    def __init__(self, event_log: Optional[asyncio.Queue] = None):
        """Initialize the BackPressureManager.

        Args:
            event_log: Optional asyncio.Queue for reporting events.
                      If None, reporting back pressure is skipped.
        """
        self.event_log = event_log

    async def _wait_for_reporting_capacity(self) -> None:
        """Wait until reporting queue has capacity."""
        blocked = False
        once = False

        while self.event_log.full():
            if not once:
                logger.info(
                    "Waiting on %d reporting objects to flush, queue "
                    "capacity %d. back pressure applied",
                    self.event_log.qsize(),
                    self.event_log.maxsize,
                )
                once = True
            blocked = True
            await asyncio.sleep(1)

        if blocked:
            logger.info(
                "Back pressure due to reporting released. Free slots %d "
                "Queue capacity %d",
                self.event_log.maxsize - self.event_log.qsize(),
                self.event_log.maxsize,
            )

    def _should_skip_reporting_back_pressure(self) -> bool:
        """Check if reporting back pressure should be skipped."""
        if settings.skip_audit_events or self.event_log is None:
            return True

        # Skip if queue has no size limit (unbounded or NullQueue)
        if (
            not hasattr(self.event_log, "maxsize")
            or self.event_log.maxsize == 0
        ):
            return True

        return False

    async def apply_reporting_back_pressure(self) -> None:
        """Apply back pressure based on reporting queue capacity.

        Blocks event processing if the reporting queue is full, waiting
        for audit events to drain to the EDA Server before allowing
        new events to be processed.

        Uses asyncio.wait_for() with timeout from settings.

        Raises:
            TimedOutReportingException: If queue doesn't drain within timeout
        """
        if self._should_skip_reporting_back_pressure():
            return

        if not self.event_log.full():
            return

        try:
            await asyncio.wait_for(
                self._wait_for_reporting_capacity(),
                timeout=settings.max_back_pressure_timeout,
            )
        except asyncio.TimeoutError:
            raise TimedOutReportingException(
                "Reporting objects did not drain in "
                f"{settings.max_back_pressure_timeout} seconds hence aborting"
            )

    async def _wait_for_action_capacity(self) -> None:
        """Wait until action semaphore has capacity."""
        blocked = False
        once = False

        while settings.max_actions_semaphore._value <= 0:
            if not once:
                logger.info(
                    "Waiting on %d actions to finish, "
                    "back pressure applied",
                    settings.max_concurrent_actions,
                )
                once = True
            blocked = True
            await asyncio.sleep(1)

        if blocked:
            logger.info(
                "Back pressure released. Free slots %d",
                settings.max_actions_semaphore._value,
            )

    async def apply_actions_back_pressure(self) -> None:
        """Apply back pressure based on concurrent action capacity.

        Blocks event processing if max concurrent actions limit is reached,
        waiting for running actions to complete before allowing new events
        to be processed.

        Uses asyncio.wait_for() with timeout from settings.

        Raises:
            TimedOutActionsException: If actions don't complete within timeout
        """
        if settings.max_actions_semaphore is None:
            return

        if settings.max_actions_semaphore._value > 0:
            return

        try:
            await asyncio.wait_for(
                self._wait_for_action_capacity(),
                timeout=settings.max_back_pressure_timeout,
            )
        except asyncio.TimeoutError:
            raise TimedOutActionsException(
                "Actions failed to end in "
                f"{settings.max_back_pressure_timeout} seconds hence aborting"
            )

    def _check_timeout_budget_exhausted(
        self, remaining_timeout: float, actions_elapsed: float
    ) -> None:
        """Check if timeout budget is exhausted and raise if needed."""
        if remaining_timeout <= 0 and self.event_log and self.event_log.full():
            raise TimedOutReportingException(
                f"Timeout budget exhausted after actions phase "
                f"({actions_elapsed: .1f}s). No time remaining for "
                f"reporting back pressure."
            )

    async def _apply_reporting_with_remaining_timeout(
        self,
        remaining_timeout: float,
        start_time: float,
        actions_elapsed: float,
    ) -> None:
        """Apply reporting back pressure with remaining timeout budget."""
        if self._should_skip_reporting_back_pressure():
            return

        if not self.event_log.full():
            return

        try:
            await asyncio.wait_for(
                self._wait_for_reporting_capacity(),
                timeout=remaining_timeout,
            )
        except asyncio.TimeoutError:
            total_elapsed = time.monotonic() - start_time
            raise TimedOutReportingException(
                f"Reporting objects did not drain within remaining timeout "
                f"({remaining_timeout: .1f}s of "
                f"{settings.max_back_pressure_timeout}s total). "
                f"Actions phase took {actions_elapsed: .1f}s, "
                f"total elapsed {total_elapsed: .1f}s"
            )

    async def apply_all_back_pressure(self) -> None:
        """Apply both actions and reporting back pressure.

        Checks both back pressure mechanisms sequentially before
        allowing event processing to continue. The timeout budget is
        shared between both phases.

        Raises:
            TimedOutActionsException: If actions don't complete within timeout
            TimedOutReportingException: If reporting queue doesn't drain
        """
        start_time = time.monotonic()

        # Apply actions back pressure with full timeout
        await self.apply_actions_back_pressure()

        actions_elapsed = time.monotonic() - start_time
        remaining_timeout = max(
            0, settings.max_back_pressure_timeout - actions_elapsed
        )

        self._check_timeout_budget_exhausted(
            remaining_timeout, actions_elapsed
        )

        # Apply reporting back pressure with remaining timeout
        await self._apply_reporting_with_remaining_timeout(
            remaining_timeout, start_time, actions_elapsed
        )
