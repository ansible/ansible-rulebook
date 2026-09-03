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
from unittest.mock import AsyncMock, patch

import pytest

from ansible_rulebook.exception import (
    DuplicateSourceNamesException,
    SourcePluginFeedbackMisconfiguredException,
)
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import EventSource, ExecutionStrategy, RuleSet
from ansible_rulebook.source_manager import SourceManager


class TestSourceManagerSingleton:
    """Test SourceManager singleton pattern."""

    def teardown_method(self):
        """Reset singleton after each test."""
        SourceManager.reset_instance()

    @pytest.mark.asyncio
    async def test_get_instance(self):
        """Test get_instance returns singleton."""
        manager1 = SourceManager.get_instance()
        manager2 = SourceManager.get_instance()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_get_instance_async(self):
        """Test async get_instance returns singleton."""
        manager1 = await SourceManager.get_instance_async()
        manager2 = await SourceManager.get_instance_async()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_reset_instance(self):
        """Test reset_instance clears singleton."""
        manager1 = SourceManager.get_instance()
        SourceManager.reset_instance()
        manager2 = SourceManager.get_instance()
        assert manager1 is not manager2

    @pytest.mark.asyncio
    async def test_direct_instantiation_raises_error(self):
        """Test direct instantiation raises RuntimeError."""
        SourceManager.get_instance()  # Create singleton
        with pytest.raises(RuntimeError, match="singleton"):
            SourceManager()


class TestSourceManagerInitialization:
    """Test SourceManager initialization phase."""

    def setup_method(self):
        """Reset singleton before each test."""
        SourceManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        SourceManager.reset_instance()

    @pytest.mark.asyncio
    async def test_initialize_single_ruleset(self):
        """Test initialization with single ruleset."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={"limit": 5},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        ruleset_queues = manager.initialize(
            rulesets=[ruleset],
            variables={"var1": "value1"},
            source_dirs=["/fake/dir"],
            shutdown_delay=60.0,
            filter_dirs=[],
        )

        assert len(ruleset_queues) == 1
        assert manager.is_initialized()
        assert not manager.is_running()
        assert ruleset_queues[0].ruleset == ruleset

    @pytest.mark.asyncio
    async def test_initialize_multiple_rulesets(self):
        """Test initialization with multiple rulesets."""
        manager = SourceManager.get_instance()

        source1 = EventSource(
            name="source1",
            source_name="range",
            source_args={"limit": 5},
            source_filters=[],
        )
        source2 = EventSource(
            name="source2",
            source_name="generic",
            source_args={},
            source_filters=[],
        )

        ruleset1 = RuleSet(
            name="ruleset1",
            hosts=["localhost"],
            sources=[source1],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )
        ruleset2 = RuleSet(
            name="ruleset2",
            hosts=["localhost"],
            sources=[source2],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        ruleset_queues = manager.initialize(
            rulesets=[ruleset1, ruleset2],
            variables={},
            source_dirs=[],
            shutdown_delay=30.0,
            filter_dirs=[],
        )

        assert len(ruleset_queues) == 2
        assert manager.is_initialized()

    @pytest.mark.asyncio
    async def test_initialize_twice_raises_error(self):
        """Test initializing twice raises RuntimeError."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=[],
            shutdown_delay=60.0,
            filter_dirs=[],
        )

        with pytest.raises(RuntimeError, match="already initialized"):
            manager.initialize(
                rulesets=[ruleset],
                variables={},
                source_dirs=[],
                shutdown_delay=60.0,
                filter_dirs=[],
            )

    @pytest.mark.asyncio
    async def test_get_ruleset_queues_before_init_raises_error(self):
        """Test get_ruleset_queues before init raises error."""
        manager = SourceManager.get_instance()
        with pytest.raises(RuntimeError, match="not initialized"):
            manager.get_ruleset_queues()


class TestSourceManagerFeedbackQueues:
    """Test feedback queue creation and validation."""

    def setup_method(self):
        """Reset singleton before each test."""
        SourceManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        SourceManager.reset_instance()

    @pytest.mark.asyncio
    async def test_feedback_queue_requires_persistence(self):
        """Test feedback queue creation requires persistence_id."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="feedback_source",
            source_name="range",
            source_args={"feedback": True},  # Request feedback
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        # Explicitly patch persistence_id to None to isolate this test
        with patch("ansible_rulebook.conf.settings.persistence_id", None):
            # Should raise error when persistence_id is None
            with pytest.raises(SourcePluginFeedbackMisconfiguredException):
                manager.initialize(
                    rulesets=[ruleset],
                    variables={},
                    source_dirs=[],
                    shutdown_delay=60.0,
                    filter_dirs=[],
                )

    @pytest.mark.asyncio
    async def test_feedback_queue_with_persistence(self):
        """Test feedback queue creation with persistence enabled."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="feedback_source",
            source_name="range",
            source_args={"feedback": True},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        # Mock conf.settings where it's imported in _get_feedback_queue
        with patch("ansible_rulebook.conf.settings") as mock_settings:
            mock_settings.persistence_id = "test-persistence-id"

            ruleset_queues = manager.initialize(
                rulesets=[ruleset],
                variables={},
                source_dirs=[],
                shutdown_delay=60.0,
                filter_dirs=[],
            )

            # Should create feedback queue
            assert len(ruleset_queues) == 1
            assert (
                "feedback_source" in ruleset_queues[0].source_feedback_queues
            )

    @pytest.mark.asyncio
    async def test_duplicate_source_names_raises_error(self):
        """Test duplicate source names raise error."""
        manager = SourceManager.get_instance()

        # Two sources with same name but both requesting feedback
        source1 = EventSource(
            name="duplicate",
            source_name="range",
            source_args={"feedback": True},
            source_filters=[],
        )
        source2 = EventSource(
            name="duplicate",  # Same name
            source_name="generic",
            source_args={"feedback": True},
            source_filters=[],
        )

        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source1, source2],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        with patch("ansible_rulebook.conf.settings") as mock_settings:
            mock_settings.persistence_id = "test-persistence-id"

            with pytest.raises(DuplicateSourceNamesException):
                manager.initialize(
                    rulesets=[ruleset],
                    variables={},
                    source_dirs=[],
                    shutdown_delay=60.0,
                    filter_dirs=[],
                )


class TestSourceManagerExecution:
    """Test SourceManager source execution phase."""

    def setup_method(self):
        """Reset singleton before each test."""
        SourceManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        SourceManager.reset_instance()

    @pytest.mark.asyncio
    async def test_start_sources_before_init_raises_error(self):
        """Test starting sources before init raises error."""
        manager = SourceManager.get_instance()
        with pytest.raises(RuntimeError, match="not initialized"):
            await manager.start_sources()

    @pytest.mark.asyncio
    async def test_start_sources_waits_for_rulesets_ready(self):
        """Test start_sources waits for rulesets_ready signal."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={"limit": 5},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=["/fake/dir"],
            shutdown_delay=60.0,
            filter_dirs=[],
        )

        with patch(
            "ansible_rulebook.source_manager.start_source"
        ) as mock_start_source:
            mock_start_source.return_value = AsyncMock()

            # Start sources in background (it will wait for signal)
            start_task = asyncio.create_task(manager.start_sources())

            # Give it a moment to start waiting
            await asyncio.sleep(0.1)

            # Should still be waiting
            assert not start_task.done()

            # Signal that rulesets are ready
            manager.signal_rulesets_ready()

            # Now it should complete
            await asyncio.wait_for(start_task, timeout=1.0)

            # Should have started the source
            assert manager.is_running()
            mock_start_source.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_sources_timeout_raises_error(self):
        """Test start_sources raises RuntimeError on timeout."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={"limit": 5},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=["/fake/dir"],
            shutdown_delay=60.0,
            filter_dirs=[],
        )

        # Patch wait_for to simulate timeout immediately
        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = asyncio.TimeoutError()

            # Should raise RuntimeError due to timeout
            with pytest.raises(
                RuntimeError,
                match="Timeout waiting for rulesets to be ready",
            ):
                await manager.start_sources()

    @pytest.mark.asyncio
    async def test_signal_rulesets_ready(self):
        """Test signaling rulesets ready."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=[],
            shutdown_delay=60.0,
            filter_dirs=[],
        )

        # Signal before starting
        manager.signal_rulesets_ready()

        # Should be able to start immediately now
        with patch(
            "ansible_rulebook.source_manager.start_source"
        ) as mock_start_source:
            mock_start_source.return_value = AsyncMock()

            await asyncio.wait_for(manager.start_sources(), timeout=1.0)
            assert manager.is_running()

    @pytest.mark.asyncio
    async def test_stop_sources(self):
        """Test stopping sources."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=[],
            shutdown_delay=0.1,
            filter_dirs=[],
        )

        # Create a long-running async function for mocking
        async def mock_source_func():
            await asyncio.sleep(10000)  # Will be cancelled

        with patch(
            "ansible_rulebook.source_manager.start_source",
            side_effect=lambda *args, **kwargs: mock_source_func(),
        ):
            manager.signal_rulesets_ready()
            await manager.start_sources()

            assert manager.is_running()
            assert len(manager.get_source_tasks()) == 1

            # Stop sources
            await manager.stop_sources(reason="Test shutdown")

            assert not manager.is_running()
            assert len(manager.get_source_tasks()) == 0

    @pytest.mark.asyncio
    async def test_broadcast_shutdown(self):
        """Test broadcast_shutdown sends to all queues."""
        manager = SourceManager.get_instance()

        source1 = EventSource(
            name="source1",
            source_name="range",
            source_args={},
            source_filters=[],
        )
        source2 = EventSource(
            name="source2",
            source_name="generic",
            source_args={},
            source_filters=[],
        )

        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source1, source2],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=[],
            shutdown_delay=60.0,
            filter_dirs=[],
        )

        # Get the queue for verification
        ruleset_queues = manager.get_ruleset_queues()
        source_queue = ruleset_queues[0].source_queue

        # Broadcast shutdown
        shutdown = Shutdown(message="Test shutdown", delay=0)
        await manager._broadcast_shutdown(shutdown)

        # Should have put shutdown in queue
        result = await asyncio.wait_for(source_queue.get(), timeout=1.0)
        assert result == shutdown


class TestSourceManagerCleanup:
    """Test SourceManager cleanup and reset."""

    def setup_method(self):
        """Reset singleton before each test."""
        SourceManager.reset_instance()

    def teardown_method(self):
        """Reset singleton after each test."""
        SourceManager.reset_instance()

    @pytest.mark.asyncio
    async def test_cleanup(self):
        """Test cleanup resets state."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=[],
            shutdown_delay=0.1,
            filter_dirs=[],
        )

        with patch(
            "ansible_rulebook.source_manager.start_source"
        ) as mock_start_source:
            mock_start_source.return_value = AsyncMock()

            manager.signal_rulesets_ready()
            await manager.start_sources()

            assert manager.is_initialized()
            assert manager.is_running()

            # Cleanup
            await manager.cleanup()

            # Should reset state
            assert not manager.is_initialized()
            assert not manager.is_running()

    @pytest.mark.asyncio
    async def test_cleanup_stops_running_sources(self):
        """Test cleanup stops running sources."""
        manager = SourceManager.get_instance()

        source = EventSource(
            name="test_source",
            source_name="range",
            source_args={},
            source_filters=[],
        )
        ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[source],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        manager.initialize(
            rulesets=[ruleset],
            variables={},
            source_dirs=[],
            shutdown_delay=0.1,
            filter_dirs=[],
        )

        # Create a long-running async function for mocking
        async def mock_source_func():
            await asyncio.sleep(10000)  # Will be cancelled

        with patch(
            "ansible_rulebook.source_manager.start_source",
            side_effect=lambda *args, **kwargs: mock_source_func(),
        ):
            manager.signal_rulesets_ready()
            await manager.start_sources()

            assert manager.is_running()

            # Cleanup should stop sources
            await manager.cleanup()

            # Should reset state
            assert not manager.is_running()
            assert not manager.is_initialized()
