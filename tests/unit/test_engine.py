#  Copyright 2023 Red Hat, Inc.
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
import os
from unittest.mock import AsyncMock, Mock, patch

import pytest
from anyio import NamedTemporaryFile
from freezegun import freeze_time

from ansible_rulebook.engine import (
    FilteredQueue,
    RulebookFileChangeHandler,
    all_source_queues,
    broadcast,
    heartbeat_task,
    meta_info_filter,
    monitor_rulebook,
    run_rulesets,
    start_source,
)
from ansible_rulebook.exception import (
    HotReloadException,
    SourceFilterNotFoundException,
    SourcePluginMainMissingException,
    SourcePluginNotAsyncioCompatibleException,
    SourcePluginNotFoundException,
)
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import (
    EventSource,
    EventSourceFilter,
    ExecutionStrategy,
    RuleSet,
    RuleSetQueue,
)


class TestFilteredQueue:
    """Test the FilteredQueue class."""

    @pytest.mark.asyncio
    async def test_filtered_queue_single_item(self):
        """Test FilteredQueue with a single data item."""
        queue = asyncio.Queue()

        # Mock filter function that doubles the value
        mock_filter = Mock(return_value={"value": 20})
        filters = [(mock_filter, {"multiplier": 2})]

        filtered_queue = FilteredQueue(filters, queue)
        await filtered_queue.put({"value": 10})

        # Verify filter was called
        mock_filter.assert_called_once_with({"value": 10}, multiplier=2)

        # Verify result was put in queue
        result = await queue.get()
        assert result == {"value": 20}

    @pytest.mark.asyncio
    async def test_filtered_queue_list_input(self):
        """Test FilteredQueue with list input."""
        queue = asyncio.Queue()

        # Mock filter that adds a processed flag
        mock_filter = Mock(
            side_effect=lambda x, **kwargs: {**x, "processed": True}
        )
        filters = [(mock_filter, None)]

        filtered_queue = FilteredQueue(filters, queue)
        data = [{"id": 1}, {"id": 2}]
        await filtered_queue.put(data)

        # Should have called filter twice
        assert mock_filter.call_count == 2

        # Should have two items in queue
        results = []
        for _ in range(2):
            results.append(await queue.get())

        assert results == [
            {"id": 1, "processed": True},
            {"id": 2, "processed": True},
        ]

    @pytest.mark.asyncio
    async def test_filtered_queue_filter_returns_list(self):
        """Test FilteredQueue when filter returns a list."""
        queue = asyncio.Queue()

        # Mock filter that splits data into multiple items
        mock_filter = Mock(return_value=[{"split": 1}, {"split": 2}])
        filters = [(mock_filter, {})]

        filtered_queue = FilteredQueue(filters, queue)
        await filtered_queue.put({"original": "data"})

        # Should have two items in queue
        results = []
        for _ in range(2):
            results.append(await queue.get())

        assert results == [{"split": 1}, {"split": 2}]

    @pytest.mark.asyncio
    async def test_filtered_queue_multiple_filters(self):
        """Test FilteredQueue with multiple filters."""
        queue = asyncio.Queue()

        # Chain of filters
        filter1 = Mock(return_value={"value": 20})  # doubles value
        filter2 = Mock(return_value={"value": 25})  # adds 5
        filters = [(filter1, {}), (filter2, {})]

        filtered_queue = FilteredQueue(filters, queue)
        await filtered_queue.put({"value": 10})

        # Verify filters were called in order
        filter1.assert_called_once_with({"value": 10})
        filter2.assert_called_once_with({"value": 20})

        result = await queue.get()
        assert result == {"value": 25}

    @pytest.mark.asyncio
    async def test_filtered_queue_put_nowait(self):
        """Test FilteredQueue put_nowait method."""
        queue = asyncio.Queue()

        mock_filter = Mock(return_value={"processed": True})
        filters = [(mock_filter, {"test": "arg"})]

        filtered_queue = FilteredQueue(filters, queue)
        filtered_queue.put_nowait({"original": "data"})

        mock_filter.assert_called_once_with({"original": "data"}, test="arg")

        result = queue.get_nowait()
        assert result == {"processed": True}


class TestBroadcast:
    """Test the broadcast function."""

    @pytest.mark.asyncio
    async def test_broadcast_empty_queues(self):
        """Test broadcast with no queues."""
        # Clear global queues list
        all_source_queues.clear()

        shutdown = Shutdown(message="test shutdown", delay=30.0)
        await broadcast(shutdown)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_broadcast_multiple_queues(self):
        """Test broadcast with multiple queues."""
        # Clear and setup queues
        all_source_queues.clear()

        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        all_source_queues.extend([queue1, queue2])

        shutdown = Shutdown(message="test shutdown", delay=30.0)
        await broadcast(shutdown)

        # Verify shutdown was sent to both queues
        result1 = await queue1.get()
        result2 = await queue2.get()

        assert result1 == shutdown
        assert result2 == shutdown

        # Cleanup
        all_source_queues.clear()


class TestHeartbeatTask:
    """Test the heartbeat_task function."""

    @pytest.mark.asyncio
    async def test_heartbeat_task(self):
        """Test heartbeat task sends stats periodically."""
        event_log = asyncio.Queue()
        rule_set_names = ["ruleset1", "ruleset2"]
        interval = 1  # Short interval for testing

        with patch(
            "ansible_rulebook.engine.send_session_stats"
        ) as mock_send_stats:
            with patch(
                "ansible_rulebook.engine.session_stats"
            ) as mock_session_stats:
                mock_session_stats.return_value = {"stats": "data"}

                # Start heartbeat task
                task = asyncio.create_task(
                    heartbeat_task(event_log, rule_set_names, interval)
                )

                # Let it run for a short time
                await asyncio.sleep(0.25)
                task.cancel()

                # Verify stats were sent for both rulesets
                assert mock_send_stats.call_count >= 2  # At least one cycle
                mock_session_stats.assert_called()

    @pytest.mark.asyncio
    async def test_heartbeat_task_cancellation(self):
        """Test heartbeat task handles cancellation gracefully."""
        event_log = asyncio.Queue()
        rule_set_names = ["ruleset1"]

        task = asyncio.create_task(
            heartbeat_task(event_log, rule_set_names, 1)
        )

        # Cancel immediately
        task.cancel()

        with pytest.raises(asyncio.CancelledError):
            await task


class TestMetaInfoFilter:
    """Test the meta_info_filter function."""

    def test_meta_info_filter_creation(self):
        """Test meta_info_filter creates correct filter."""
        source = EventSource(
            name="test_source",
            source_name="kafka",
            source_args={"topic": "events"},
            source_filters=[],
        )

        result = meta_info_filter(source)

        assert result.filter_name == "eda.builtin.insert_meta_info"
        assert result.filter_args == {
            "source_name": "test_source",
            "source_type": "kafka",
        }


class TestRulebookFileChangeHandler:
    """Test the RulebookFileChangeHandler class."""

    def test_handler_initial_state(self):
        """Test handler initial state."""
        handler = RulebookFileChangeHandler()
        assert not handler.is_modified()

    def test_handler_on_modified(self):
        """Test handler detects file modifications."""
        handler = RulebookFileChangeHandler()

        # Mock file system event
        mock_event = Mock()
        mock_event.src_path = "/path/to/rulebook.yml"

        handler.on_modified(mock_event)
        assert handler.is_modified()


class TestMonitorRulebook:
    """Test the monitor_rulebook function."""

    @pytest.mark.asyncio
    @patch("ansible_rulebook.engine.Observer")
    async def test_monitor_rulebook_file_changed(self, mock_observer_class):
        """Test monitor_rulebook raises HotReloadException
        when file changes."""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        # Create a handler that reports modification
        handler = RulebookFileChangeHandler()
        handler.modified = True

        with patch(
            "ansible_rulebook.engine.RulebookFileChangeHandler",
            return_value=handler,
        ):
            with pytest.raises(HotReloadException):
                await monitor_rulebook("/fake/path/rulebook.yml")

        mock_observer.start.assert_called_once()
        mock_observer.stop.assert_called_once()
        mock_observer.join.assert_called_once()

    @pytest.mark.asyncio
    @patch("ansible_rulebook.engine.Observer")
    async def test_monitor_rulebook_no_changes(self, mock_observer_class):
        """Test monitor_rulebook handles no file changes."""
        mock_observer = Mock()
        mock_observer_class.return_value = mock_observer

        handler = RulebookFileChangeHandler()
        # Don't set modified to True

        with patch(
            "ansible_rulebook.engine.RulebookFileChangeHandler",
            return_value=handler,
        ):
            # This will run until cancelled
            task = asyncio.create_task(
                monitor_rulebook("/fake/path/rulebook.yml")
            )
            await asyncio.sleep(0.1)  # Let it start
            task.cancel()

            with pytest.raises(asyncio.CancelledError):
                await task

        mock_observer.start.assert_called_once()


class TestStartSource:
    """Test the start_source function."""

    def setup_method(self):
        """Clear global queues before each test."""
        all_source_queues.clear()

    def teardown_method(self):
        """Clear global queues after each test."""
        all_source_queues.clear()

    @pytest.mark.asyncio
    async def test_start_source_local_file(self):
        """Test start_source with local source file."""
        source = EventSource(
            name="test_source",
            source_name="mock_source",
            source_args={"arg1": "value1"},
            source_filters=[],
        )

        queue = asyncio.Queue()
        variables = {"var1": "test"}

        # Mock source execution to avoid actual file execution
        async def mock_source_main(queue, args):
            await queue.put({"test": "event"})

        # Mock the meta info filter
        def mock_meta_filter(event, **kwargs):
            return {**event, "meta": {"filtered": True}}

        # Mock all the dependencies
        with patch("os.path.exists", return_value=True):
            with patch(
                "ansible_rulebook.engine.has_builtin_filter", return_value=True
            ):
                with patch(
                    "ansible_rulebook.engine.find_builtin_filter",
                    return_value="/fake/filter.py",
                ):
                    with patch(
                        "ansible_rulebook.engine.runpy.run_path"
                    ) as mock_run_path:

                        def run_path_side_effect(path):
                            if "mock_source.py" in path:
                                return {"main": mock_source_main}
                            else:
                                return {"main": mock_meta_filter}

                        mock_run_path.side_effect = run_path_side_effect

                        # Run start_source
                        await start_source(
                            source, ["/fake/source/dir"], variables, queue
                        )

        # Verify queue was added to global list
        assert queue in all_source_queues

        # Verify event was put in queue (should have meta info added)
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert "test" in event
        assert event["test"] == "event"
        assert "meta" in event

    @pytest.mark.asyncio
    async def test_start_source_plugin_not_found(self):
        """Test start_source with non-existent source plugin."""
        source = EventSource(
            name="test_source",
            source_name="nonexistent_source",
            source_args={},
            source_filters=[],
        )

        queue = asyncio.Queue()

        with patch("ansible_rulebook.engine.has_source", return_value=False):
            with pytest.raises(SourcePluginNotFoundException):
                await start_source(source, [], {}, queue)

    @pytest.mark.asyncio
    async def test_start_source_missing_main(self):
        """Test start_source with source missing main function."""
        async with NamedTemporaryFile(
            mode="w+", suffix=".py", delete=False
        ) as f:
            await f.write("# No main function")
            temp_path = f.name

        try:
            source_dir = os.path.dirname(temp_path)
            source_name = os.path.basename(temp_path)[:-3]

            source = EventSource(
                name="test_source",
                source_name=source_name,
                source_args={},
                source_filters=[],
            )

            queue = asyncio.Queue()

            with pytest.raises(SourcePluginMainMissingException):
                await start_source(source, [source_dir], {}, queue)

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_start_source_not_async(self):
        """Test start_source with non-async main function."""
        async with NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            await f.write(
                """
def main(queue, args):
    pass  # Not async
"""
            )
            temp_path = f.name

        try:
            source_dir = os.path.dirname(temp_path)
            source_name = os.path.basename(temp_path)[:-3]

            source = EventSource(
                name="test_source",
                source_name=source_name,
                source_args={},
                source_filters=[],
            )

            queue = asyncio.Queue()

            with pytest.raises(SourcePluginNotAsyncioCompatibleException):
                await start_source(source, [source_dir], {}, queue)

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_start_source_with_filters(self):
        """Test start_source with source filters."""
        # Mock filter
        mock_filter = EventSourceFilter("test_filter", {"arg": "value"})

        source = EventSource(
            name="test_source",
            source_name="mock_source",
            source_args={},
            source_filters=[mock_filter],
        )

        queue = asyncio.Queue()

        # Mock source execution
        async def mock_source_main(queue, args):
            await queue.put({"original": "data"})

        # Mock filter functions
        def mock_custom_filter(data, **kwargs):
            return {**data, "custom_filtered": True}

        def mock_meta_filter(data, **kwargs):
            return {**data, "meta": {"filtered": True}}

        # Mock all the dependencies
        with patch("os.path.exists", return_value=True):
            with patch(
                "ansible_rulebook.engine.has_builtin_filter"
            ) as mock_has_builtin:
                with patch(
                    "ansible_rulebook.engine.find_builtin_filter",
                    return_value="/fake/filter.py",
                ):
                    with patch(
                        "ansible_rulebook.engine.runpy.run_path"
                    ) as mock_run_path:
                        # Configure has_builtin_filter to return True
                        # for both filters
                        def has_builtin_side_effect(filter_name):
                            return filter_name in [
                                "test_filter",
                                "eda.builtin.insert_meta_info",
                            ]

                        mock_has_builtin.side_effect = has_builtin_side_effect

                        def run_path_side_effect(path):
                            if "mock_source.py" in path:
                                return {"main": mock_source_main}
                            elif "test_filter" in path:
                                return {"main": mock_custom_filter}
                            else:
                                return {"main": mock_meta_filter}

                        mock_run_path.side_effect = run_path_side_effect

                        await start_source(
                            source, ["/fake/source/dir"], {}, queue
                        )

    @pytest.mark.asyncio
    async def test_start_source_filter_not_found(self):
        """Test start_source with non-existent filter."""
        async with NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            await f.write(
                """
async def main(queue, args):
    pass
"""
            )
            temp_path = f.name

        try:
            source_dir = os.path.dirname(temp_path)
            source_name = os.path.basename(temp_path)[:-3]

            mock_filter = EventSourceFilter("nonexistent_filter", {})

            source = EventSource(
                name="test_source",
                source_name=source_name,
                source_args={},
                source_filters=[mock_filter],
            )

            queue = asyncio.Queue()

            with patch(
                "ansible_rulebook.engine.has_source_filter", return_value=False
            ):
                with patch(
                    "ansible_rulebook.engine.has_builtin_filter",
                    return_value=False,
                ):
                    with pytest.raises(SourceFilterNotFoundException):
                        await start_source(source, [source_dir], {}, queue)

        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    @freeze_time("2023-06-11 12:13:14")
    async def test_start_source_keyboard_interrupt(self):
        """Test start_source handles KeyboardInterrupt."""
        async with NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            await f.write(
                """
async def main(queue, args):
    raise KeyboardInterrupt()
"""
            )
            temp_path = f.name

        try:
            source_dir = os.path.dirname(temp_path)
            source_name = os.path.basename(temp_path)[:-3]

            source = EventSource(
                name="test_source",
                source_name=source_name,
                source_args={},
                source_filters=[],
            )

            queue = asyncio.Queue()

            with patch("ansible_rulebook.engine.broadcast") as mock_broadcast:
                await start_source(source, [source_dir], {}, queue)

                # Verify broadcast was called with appropriate shutdown message
                mock_broadcast.assert_called_once()
                shutdown_arg = mock_broadcast.call_args[0][0]
                assert "keyboard interrupt" in shutdown_arg.message
                assert shutdown_arg.source_plugin == source_name

        finally:
            os.unlink(temp_path)


class TestRunRulesets:
    """Test the run_rulesets function."""

    @pytest.mark.asyncio
    async def test_run_rulesets_empty_plans(self):
        """Test run_rulesets with empty ruleset plans."""
        event_log = asyncio.Queue()
        ruleset_queues = []
        variables = {}

        with patch(
            "ansible_rulebook.engine.rule_generator.generate_rulesets",
            return_value=[],
        ):
            result = await run_rulesets(event_log, ruleset_queues, variables)
            assert result is None

    @pytest.mark.asyncio
    async def test_run_rulesets_basic_execution(self):
        """Test basic run_rulesets execution."""
        event_log = asyncio.Queue()

        # Create mock ruleset
        mock_ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        source_queue = asyncio.Queue()
        ruleset_queues = [RuleSetQueue(mock_ruleset, source_queue)]
        variables = {"test": "value"}

        # Mock dependencies
        with patch(
            "ansible_rulebook.engine.rule_generator.generate_rulesets"
        ) as mock_generate:
            with patch(
                "ansible_rulebook.engine.establish_async_channel"
            ) as mock_channel:
                with patch(
                    "ansible_rulebook.engine.handle_async_messages"
                ) as mock_handle:
                    with patch(
                        "ansible_rulebook.engine.RuleSetRunner"
                    ) as mock_runner_class:
                        # Create mock drools ruleset with define method
                        mock_drools_ruleset = Mock()
                        mock_drools_ruleset.define.return_value = (
                            "mocked ruleset definition"
                        )
                        mock_drools_ruleset.name = (
                            "test_ruleset"  # Set the name property
                        )

                        # Setup mocks
                        mock_plan = Mock()
                        mock_plan.ruleset = mock_drools_ruleset
                        mock_generate.return_value = [mock_plan]
                        mock_channel.return_value = (Mock(), Mock())
                        mock_handle.return_value = AsyncMock()

                        mock_runner = Mock()
                        mock_runner.run_ruleset = AsyncMock()
                        mock_runner_class.return_value = mock_runner

                        # Run test
                        result = await run_rulesets(
                            event_log, ruleset_queues, variables
                        )

                        # Verify setup
                        mock_generate.assert_called_once()
                        mock_runner_class.assert_called_once()
                        assert result is False  # No hot reload

    @pytest.mark.asyncio
    async def test_run_rulesets_with_heartbeat(self):
        """Test run_rulesets with heartbeat enabled."""
        event_log = asyncio.Queue()

        mock_ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        source_queue = asyncio.Queue()
        ruleset_queues = [RuleSetQueue(mock_ruleset, source_queue)]
        variables = {}

        # Mock parsed_args with heartbeat
        parsed_args = argparse.Namespace()
        parsed_args.heartbeat = 30

        with patch(
            "ansible_rulebook.engine.rule_generator.generate_rulesets"
        ) as mock_generate:
            with patch(
                "ansible_rulebook.engine.establish_async_channel"
            ) as mock_channel:
                with patch(
                    "ansible_rulebook.engine.handle_async_messages"
                ) as mock_handle:
                    with patch(
                        "ansible_rulebook.engine.RuleSetRunner"
                    ) as mock_runner_class:
                        with patch(
                            "ansible_rulebook.engine.heartbeat_task"
                        ) as mock_heartbeat:
                            # Create mock drools ruleset with define method
                            mock_drools_ruleset = Mock()
                            mock_drools_ruleset.define.return_value = (
                                "mocked ruleset definition"
                            )
                            mock_drools_ruleset.name = (
                                "test_ruleset"  # Set the name property
                            )

                            # Setup mocks
                            mock_plan = Mock()
                            mock_plan.ruleset = mock_drools_ruleset
                            mock_generate.return_value = [mock_plan]
                            mock_channel.return_value = (Mock(), Mock())
                            mock_handle.return_value = AsyncMock()
                            mock_heartbeat.return_value = AsyncMock()

                            mock_runner = Mock()
                            mock_runner.run_ruleset = AsyncMock()
                            mock_runner_class.return_value = mock_runner

                            # Run test
                            await run_rulesets(
                                event_log,
                                ruleset_queues,
                                variables,
                                parsed_args=parsed_args,
                            )

                            # Verify heartbeat task was created
                            mock_heartbeat.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_rulesets_with_file_monitor(self):
        """Test run_rulesets with file monitoring enabled."""
        event_log = asyncio.Queue()

        mock_ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=False,
        )

        source_queue = asyncio.Queue()
        ruleset_queues = [RuleSetQueue(mock_ruleset, source_queue)]
        variables = {}

        with patch(
            "ansible_rulebook.engine.rule_generator.generate_rulesets"
        ) as mock_generate:
            with patch(
                "ansible_rulebook.engine.establish_async_channel"
            ) as mock_channel:
                with patch(
                    "ansible_rulebook.engine.handle_async_messages"
                ) as mock_handle:
                    with patch(
                        "ansible_rulebook.engine.RuleSetRunner"
                    ) as mock_runner_class:
                        with patch(
                            "ansible_rulebook.engine.monitor_rulebook"
                        ) as mock_monitor:
                            # Create mock drools ruleset with define method
                            mock_drools_ruleset = Mock()
                            mock_drools_ruleset.define.return_value = (
                                "mocked ruleset definition"
                            )
                            mock_drools_ruleset.name = (
                                "test_ruleset"  # Set the name property
                            )

                            # Setup mocks
                            mock_plan = Mock()
                            mock_plan.ruleset = mock_drools_ruleset
                            mock_generate.return_value = [mock_plan]
                            mock_channel.return_value = (Mock(), Mock())
                            mock_handle.return_value = AsyncMock()

                            mock_runner = Mock()
                            mock_runner.run_ruleset = AsyncMock()
                            mock_runner_class.return_value = mock_runner

                            # Just test that monitor_rulebook is called when
                            #  file_monitor is provided
                            # Don't test the complex hot reload logic due to
                            #  asyncio mocking complexity
                            result = await run_rulesets(
                                event_log,
                                ruleset_queues,
                                variables,
                                file_monitor="/path/to/rulebook.yml",
                            )

                            # Verify monitor_rulebook was called
                            mock_monitor.assert_called_once_with(
                                "/path/to/rulebook.yml"
                            )
                            # Should return False (no hot reload detected
                            #  in this simple test)
                            assert result is False

    @pytest.mark.asyncio
    async def test_run_rulesets_gather_facts(self):
        """Test run_rulesets with gather_facts enabled."""
        event_log = asyncio.Queue()

        mock_ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=True,  # Enable gather_facts
        )

        source_queue = asyncio.Queue()
        ruleset_queues = [RuleSetQueue(mock_ruleset, source_queue)]
        variables = {}
        inventory = "/path/to/inventory"

        with patch(
            "ansible_rulebook.engine.rule_generator.generate_rulesets"
        ) as mock_generate:
            with patch(
                "ansible_rulebook.engine.establish_async_channel"
            ) as mock_channel:
                with patch(
                    "ansible_rulebook.engine.handle_async_messages"
                ) as mock_handle:
                    with patch(
                        "ansible_rulebook.engine.RuleSetRunner"
                    ) as mock_runner_class:
                        with patch(
                            "ansible_rulebook.engine.collect_ansible_facts"
                        ) as mock_collect_facts:
                            # Create mock drools ruleset with define method
                            mock_drools_ruleset = Mock()
                            mock_drools_ruleset.define.return_value = (
                                "mocked ruleset definition"
                            )
                            mock_drools_ruleset.name = (
                                "test_ruleset"  # Set the name property
                            )

                            # Setup mocks
                            mock_plan = Mock()
                            mock_plan.ruleset = mock_drools_ruleset
                            mock_generate.return_value = [mock_plan]
                            mock_channel.return_value = (Mock(), Mock())
                            mock_handle.return_value = AsyncMock()
                            mock_collect_facts.return_value = {
                                "host1": {"fact": "value"}
                            }

                            mock_runner = Mock()
                            mock_runner.run_ruleset = AsyncMock()
                            mock_runner_class.return_value = mock_runner

                            # Run test
                            await run_rulesets(
                                event_log, ruleset_queues, variables, inventory
                            )

                            # Verify facts were collected
                            mock_collect_facts.assert_called_once_with(
                                inventory
                            )

    @pytest.mark.asyncio
    async def test_run_rulesets_gather_facts_no_inventory(self):
        """Test run_rulesets with gather_facts but no inventory."""
        event_log = asyncio.Queue()

        mock_ruleset = RuleSet(
            name="test_ruleset",
            hosts=["localhost"],
            sources=[],
            rules=[],
            execution_strategy=ExecutionStrategy.SEQUENTIAL,
            gather_facts=True,
        )

        source_queue = asyncio.Queue()
        ruleset_queues = [RuleSetQueue(mock_ruleset, source_queue)]
        variables = {}

        with patch(
            "ansible_rulebook.engine.rule_generator.generate_rulesets"
        ) as mock_generate:
            with patch(
                "ansible_rulebook.engine.establish_async_channel"
            ) as mock_channel:
                with patch(
                    "ansible_rulebook.engine.handle_async_messages"
                ) as mock_handle:
                    with patch(
                        "ansible_rulebook.engine.RuleSetRunner"
                    ) as mock_runner_class:
                        with patch(
                            "ansible_rulebook.engine.collect_ansible_facts"
                        ) as mock_collect_facts:
                            # Create mock drools ruleset with define method
                            mock_drools_ruleset = Mock()
                            mock_drools_ruleset.define.return_value = (
                                "mocked ruleset definition"
                            )
                            mock_drools_ruleset.name = (
                                "test_ruleset"  # Set the name property
                            )

                            # Setup mocks
                            mock_plan = Mock()
                            mock_plan.ruleset = mock_drools_ruleset
                            mock_generate.return_value = [mock_plan]
                            mock_channel.return_value = (Mock(), Mock())
                            mock_handle.return_value = AsyncMock()

                            mock_runner = Mock()
                            mock_runner.run_ruleset = AsyncMock()
                            mock_runner_class.return_value = mock_runner

                            # Run test with no inventory
                            await run_rulesets(
                                event_log, ruleset_queues, variables
                            )

                            # Facts should not be collected
                            mock_collect_facts.assert_not_called()
