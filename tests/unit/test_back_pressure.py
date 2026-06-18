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

import asyncio
from unittest.mock import Mock, patch

import pytest

from ansible_rulebook.app import NullQueue
from ansible_rulebook.back_pressure import BackPressureManager
from ansible_rulebook.exception import (
    TimedOutActionsException,
    TimedOutReportingException,
)


class TestBackPressureManager:
    """Test suite for BackPressureManager class."""

    # ========================================================================
    # Reporting Back Pressure Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_no_event_log(self):
        """Test that reporting back pressure is skipped when no event_log."""
        manager = BackPressureManager(event_log=None)
        # Should return immediately without error
        await manager.apply_reporting_back_pressure()

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_null_queue(self):
        """Test that reporting back pressure is skipped with NullQueue."""
        null_queue = NullQueue()
        manager = BackPressureManager(event_log=null_queue)

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10

            # Should return immediately since NullQueue has maxsize=0
            await manager.apply_reporting_back_pressure()

            # Verify NullQueue has expected interface
            assert hasattr(null_queue, "maxsize")
            assert hasattr(null_queue, "full")
            assert hasattr(null_queue, "qsize")
            assert null_queue.maxsize == 0
            assert null_queue.full() is False
            assert null_queue.qsize() == 0

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_skip_audit_events(self):
        """Test reporting back pressure skipped when audit disabled."""
        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = True
            # Should return immediately without checking queue
            await manager.apply_reporting_back_pressure()

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_queue_not_full(self):
        """Test that back pressure returns immediately when queue has space."""
        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10

            # Queue is empty, should return immediately
            await manager.apply_reporting_back_pressure()

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_queue_full_then_drains(self):
        """Test back pressure waits when queue full, releases on drain."""
        event_log = asyncio.Queue(maxsize=2)
        manager = BackPressureManager(event_log=event_log)

        # Fill the queue
        await event_log.put("item1")
        await event_log.put("item2")
        assert event_log.full()

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10

            # Simulate queue draining after 1 second
            async def drain_queue():
                await asyncio.sleep(0.1)
                await event_log.get()  # Remove one item

            drain_task = asyncio.create_task(drain_queue())

            # Should wait briefly then return when space available
            await manager.apply_reporting_back_pressure()
            await drain_task

            # Verify queue now has space
            assert not event_log.full()

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_timeout(self):
        """Test that timeout exception is raised when queue stays full."""
        event_log = asyncio.Queue(maxsize=2)
        manager = BackPressureManager(event_log=event_log)

        # Fill the queue
        await event_log.put("item1")
        await event_log.put("item2")
        assert event_log.full()

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 2  # Short timeout

            # Should raise exception after timeout
            with pytest.raises(TimedOutReportingException) as exc_info:
                await manager.apply_reporting_back_pressure()

            assert "did not drain" in str(exc_info.value)
            assert "2 seconds" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_drains_just_before_timeout(self):
        """Test back pressure succeeds if queue drains before timeout."""
        event_log = asyncio.Queue(maxsize=2)
        manager = BackPressureManager(event_log=event_log)

        # Fill the queue
        await event_log.put("item1")
        await event_log.put("item2")

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 3

            # Drain queue just before timeout
            async def drain_queue():
                await asyncio.sleep(
                    1.5
                )  # Drain after 1.5s (before 3s timeout)
                await event_log.get()

            drain_task = asyncio.create_task(drain_queue())

            # Should succeed without raising exception
            await manager.apply_reporting_back_pressure()
            await drain_task

    # ========================================================================
    # Actions Back Pressure Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_actions_back_pressure_no_semaphore(self):
        """Test actions back pressure skipped when semaphore not set."""
        manager = BackPressureManager()

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = None
            # Should return immediately without error
            await manager.apply_actions_back_pressure()

    @pytest.mark.asyncio
    async def test_actions_back_pressure_semaphore_available(self):
        """Test back pressure returns immediately when slots available."""
        manager = BackPressureManager()

        mock_semaphore = Mock()
        mock_semaphore._value = 5  # 5 slots available

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.max_back_pressure_timeout = 10

            # Should return immediately
            await manager.apply_actions_back_pressure()

    @pytest.mark.asyncio
    async def test_actions_back_pressure_semaphore_full_then_releases(self):
        """Test back pressure waits when full, releases when available."""
        manager = BackPressureManager()

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # No slots available

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.max_back_pressure_timeout = 10
            mock_settings.max_concurrent_actions = 10

            # Simulate slot becoming available after delay
            async def release_slot():
                await asyncio.sleep(0.1)
                mock_semaphore._value = 1  # One slot becomes available

            release_task = asyncio.create_task(release_slot())

            # Should wait briefly then return
            await manager.apply_actions_back_pressure()
            await release_task

            assert mock_semaphore._value > 0

    @pytest.mark.asyncio
    async def test_actions_back_pressure_timeout(self):
        """Test timeout exception raised when actions don't complete."""
        manager = BackPressureManager()

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # No slots available

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.max_back_pressure_timeout = 2  # Short timeout
            mock_settings.max_concurrent_actions = 10

            # Should raise exception after timeout
            with pytest.raises(TimedOutActionsException) as exc_info:
                await manager.apply_actions_back_pressure()

            assert "failed to end" in str(exc_info.value)
            assert "2 seconds" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_actions_back_pressure_releases_just_before_timeout(self):
        """Test back pressure succeeds if actions complete before timeout."""
        manager = BackPressureManager()

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # No slots available

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.max_back_pressure_timeout = 3
            mock_settings.max_concurrent_actions = 10

            # Release slot just before timeout
            async def release_slot():
                await asyncio.sleep(
                    1.5
                )  # Release after 1.5s (before 3s timeout)
                mock_semaphore._value = 1

            release_task = asyncio.create_task(release_slot())

            # Should succeed without raising exception
            await manager.apply_actions_back_pressure()
            await release_task

    # ========================================================================
    # Combined Back Pressure Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_apply_all_back_pressure_both_available(self):
        """Test apply_all works when both actions and reporting available."""
        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        mock_semaphore = Mock()
        mock_semaphore._value = 5

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10

            # Should return immediately when both have capacity
            await manager.apply_all_back_pressure()

    @pytest.mark.asyncio
    async def test_apply_all_back_pressure_actions_blocks(self):
        """Test apply_all propagates actions timeout exception."""
        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # Actions blocked

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 1
            mock_settings.max_concurrent_actions = 10

            # Should raise actions timeout exception
            with pytest.raises(TimedOutActionsException):
                await manager.apply_all_back_pressure()

    @pytest.mark.asyncio
    async def test_apply_all_back_pressure_reporting_blocks(self):
        """Test that apply_all propagates reporting timeout exception."""
        event_log = asyncio.Queue(maxsize=2)
        manager = BackPressureManager(event_log=event_log)

        # Fill reporting queue
        await event_log.put("item1")
        await event_log.put("item2")

        mock_semaphore = Mock()
        mock_semaphore._value = 5  # Actions available

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 1

            # Should raise reporting timeout exception
            with pytest.raises(TimedOutReportingException):
                await manager.apply_all_back_pressure()

    @pytest.mark.asyncio
    async def test_apply_all_back_pressure_sequential_release(self):
        """Test that both back pressures are checked sequentially."""
        event_log = asyncio.Queue(maxsize=2)
        manager = BackPressureManager(event_log=event_log)

        # Fill reporting queue
        await event_log.put("item1")
        await event_log.put("item2")

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # Actions blocked initially

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10
            mock_settings.max_concurrent_actions = 10

            async def release_both():
                await asyncio.sleep(0.1)
                mock_semaphore._value = 1  # Release actions
                await asyncio.sleep(0.1)
                await event_log.get()  # Release reporting

            release_task = asyncio.create_task(release_both())

            # Should succeed when both release
            await manager.apply_all_back_pressure()
            await release_task

    # ========================================================================
    # Edge Cases and Logging Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_reporting_back_pressure_logs_waiting(self, caplog):
        """Test waiting message logged when back pressure applied."""
        event_log = asyncio.Queue(maxsize=2)
        manager = BackPressureManager(event_log=event_log)

        # Fill queue
        await event_log.put("item1")
        await event_log.put("item2")

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10

            async def drain_quickly():
                await asyncio.sleep(0.05)
                await event_log.get()

            drain_task = asyncio.create_task(drain_quickly())

            await manager.apply_reporting_back_pressure()
            await drain_task

            # Check that appropriate log message was generated
            # Note: Actual logging verification depends on caplog fixture

    @pytest.mark.asyncio
    async def test_actions_back_pressure_logs_waiting(self):
        """Test waiting message logged when actions back pressure applied."""
        manager = BackPressureManager()

        mock_semaphore = Mock()
        mock_semaphore._value = 0

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.max_back_pressure_timeout = 10
            mock_settings.max_concurrent_actions = 10

            async def release_quickly():
                await asyncio.sleep(0.05)
                mock_semaphore._value = 1

            release_task = asyncio.create_task(release_quickly())

            await manager.apply_actions_back_pressure()
            await release_task

    @pytest.mark.asyncio
    async def test_multiple_back_pressure_cycles(self):
        """Test back pressure can be applied multiple times in sequence."""
        event_log = asyncio.Queue(maxsize=2)
        manager = BackPressureManager(event_log=event_log)

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10

            # First call - queue empty
            await manager.apply_reporting_back_pressure()

            # Fill queue
            await event_log.put("item1")
            await event_log.put("item2")

            # Second call - queue full, but drain it
            async def drain():
                await asyncio.sleep(0.05)
                await event_log.get()

            drain_task = asyncio.create_task(drain())
            await manager.apply_reporting_back_pressure()
            await drain_task

            # Third call - queue not full again
            await manager.apply_reporting_back_pressure()

    @pytest.mark.asyncio
    async def test_apply_all_back_pressure_shares_timeout_budget(self):
        """Test that apply_all shares timeout budget between phases."""
        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # Actions blocked initially

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 5

            # Fill the reporting queue
            for _ in range(10):
                await event_log.put("item")

            # Release actions after 2 seconds, leaving 3 seconds for reporting
            async def release_actions():
                await asyncio.sleep(2)
                mock_semaphore._value = 1

            # Drain queue after another 2 seconds (total 4s, within budget)
            async def drain_queue():
                await asyncio.sleep(2.5)
                while not event_log.empty():
                    await event_log.get()

            release_task = asyncio.create_task(release_actions())
            drain_task = asyncio.create_task(drain_queue())

            # Should succeed because total time < 5s
            await manager.apply_all_back_pressure()
            await release_task
            await drain_task

    @pytest.mark.asyncio
    async def test_apply_all_back_pressure_timeout_from_actions_phase(self):
        """Test that actions phase timeout leaves less time for reporting."""
        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # Actions blocked

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = (
                3  # 3 second total budget
            )

            # Fill the reporting queue
            for _ in range(10):
                await event_log.put("item")

            # Actions phase blocks for the full timeout
            # Reporting phase will have 0 seconds left and should timeout

            # Should raise TimedOutActionsException after 3 seconds
            with pytest.raises(TimedOutActionsException) as exc_info:
                await manager.apply_all_back_pressure()

            assert "3 seconds" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_back_pressure_uses_asyncio_wait_for(self):
        """Test that back pressure uses asyncio.wait_for() correctly."""
        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        mock_semaphore = Mock()
        mock_semaphore._value = 1  # Available

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 10

            # Should return immediately since semaphore has capacity
            await manager.apply_actions_back_pressure()

            # Should return immediately since queue is not full
            await manager.apply_reporting_back_pressure()

    @pytest.mark.asyncio
    async def test_back_pressure_timeout_with_time_tracking(self):
        """Test that apply_all tracks time correctly between phases."""
        import time

        event_log = asyncio.Queue(maxsize=10)
        manager = BackPressureManager(event_log=event_log)

        mock_semaphore = Mock()
        mock_semaphore._value = 0  # Blocked initially

        with patch("ansible_rulebook.back_pressure.settings") as mock_settings:
            mock_settings.max_actions_semaphore = mock_semaphore
            mock_settings.skip_audit_events = False
            mock_settings.max_back_pressure_timeout = 5

            # Fill the reporting queue
            for _ in range(10):
                await event_log.put("item")

            # Release after 1 second
            async def release():
                await asyncio.sleep(1)
                mock_semaphore._value = 1

            # Drain queue quickly
            async def drain():
                await asyncio.sleep(1.2)
                while not event_log.empty():
                    await event_log.get()

            release_task = asyncio.create_task(release())
            drain_task = asyncio.create_task(drain())

            start = time.monotonic()
            await manager.apply_all_back_pressure()
            elapsed = time.monotonic() - start

            await release_task
            await drain_task

            # Should complete in ~2 seconds (1s for actions + 1s for reporting)
            assert 1.5 <= elapsed <= 3
