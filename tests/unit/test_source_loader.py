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
import os
from unittest.mock import Mock, patch

import pytest
from anyio import NamedTemporaryFile

from ansible_rulebook.exception import (
    SourceFilterNotFoundException,
    SourcePluginMainMissingException,
    SourcePluginNotAsyncioCompatibleException,
    SourcePluginNotFoundException,
)
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import EventSource, EventSourceFilter
from ansible_rulebook.source_loader import (
    FilteredQueue,
    broadcast,
    meta_info_filter,
    start_source,
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
        """Test FilteredQueue put_nowait method with single item."""
        queue = asyncio.Queue()

        mock_filter = Mock(return_value={"processed": True})
        filters = [(mock_filter, {"test": "arg"})]

        filtered_queue = FilteredQueue(filters, queue)
        filtered_queue.put_nowait({"original": "data"})

        mock_filter.assert_called_once_with({"original": "data"}, test="arg")

        result = queue.get_nowait()
        assert result == {"processed": True}

    @pytest.mark.asyncio
    async def test_filtered_queue_put_nowait_with_list(self):
        """Test FilteredQueue put_nowait with list input."""
        queue = asyncio.Queue()

        # Mock filter that adds a processed flag
        mock_filter = Mock(
            side_effect=lambda x, **kwargs: {**x, "processed": True}
        )
        filters = [(mock_filter, None)]

        filtered_queue = FilteredQueue(filters, queue)
        data = [{"id": 1}, {"id": 2}]
        filtered_queue.put_nowait(data)

        # Should have called filter twice
        assert mock_filter.call_count == 2

        # Should have two items in queue
        results = []
        results.append(queue.get_nowait())
        results.append(queue.get_nowait())

        assert results == [
            {"id": 1, "processed": True},
            {"id": 2, "processed": True},
        ]

    @pytest.mark.asyncio
    async def test_filtered_queue_put_nowait_filter_returns_list(self):
        """Test FilteredQueue put_nowait when filter returns a list."""
        queue = asyncio.Queue()

        # Mock filter that splits data into multiple items
        mock_filter = Mock(return_value=[{"split": 1}, {"split": 2}])
        filters = [(mock_filter, {})]

        filtered_queue = FilteredQueue(filters, queue)
        filtered_queue.put_nowait({"original": "data"})

        # Should have two items in queue
        results = []
        results.append(queue.get_nowait())
        results.append(queue.get_nowait())

        assert results == [{"split": 1}, {"split": 2}]

    @pytest.mark.asyncio
    async def test_filtered_queue_put_nowait_multiple_filters(self):
        """Test FilteredQueue put_nowait with multiple filters."""
        queue = asyncio.Queue()

        # Chain of filters
        filter1 = Mock(return_value={"value": 20})  # doubles value
        filter2 = Mock(return_value={"value": 25})  # adds 5
        filters = [(filter1, {}), (filter2, {})]

        filtered_queue = FilteredQueue(filters, queue)
        filtered_queue.put_nowait({"value": 10})

        # Verify filters were called in order
        filter1.assert_called_once_with({"value": 10})
        filter2.assert_called_once_with({"value": 20})

        result = queue.get_nowait()
        assert result == {"value": 25}

    @pytest.mark.asyncio
    async def test_filtered_queue_no_filters(self):
        """Test FilteredQueue with no filters."""
        queue = asyncio.Queue()

        filtered_queue = FilteredQueue([], queue)
        await filtered_queue.put({"value": 10})

        # Data should pass through unchanged
        result = await queue.get()
        assert result == {"value": 10}


class TestBroadcast:
    """Test the broadcast function."""

    @pytest.mark.asyncio
    async def test_broadcast_empty_queues(self):
        """Test broadcast with no queues."""
        shutdown = Shutdown(message="test shutdown", delay=30.0)
        await broadcast([], shutdown)
        # Should not raise any exceptions

    @pytest.mark.asyncio
    async def test_broadcast_single_queue(self):
        """Test broadcast with single queue."""
        queue = asyncio.Queue()

        shutdown = Shutdown(message="test shutdown", delay=30.0)
        await broadcast([queue], shutdown)

        # Verify shutdown was sent to queue
        result = await queue.get()
        assert result == shutdown

    @pytest.mark.asyncio
    async def test_broadcast_multiple_queues(self):
        """Test broadcast with multiple queues."""
        queue1 = asyncio.Queue()
        queue2 = asyncio.Queue()
        queue3 = asyncio.Queue()

        shutdown = Shutdown(message="test shutdown", delay=30.0)
        await broadcast([queue1, queue2, queue3], shutdown)

        # Verify shutdown was sent to all queues
        result1 = await queue1.get()
        result2 = await queue2.get()
        result3 = await queue3.get()

        assert result1 == shutdown
        assert result2 == shutdown
        assert result3 == shutdown


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

    def test_meta_info_filter_different_source(self):
        """Test meta_info_filter with different source."""
        source = EventSource(
            name="my_webhook",
            source_name="ansible.eda.webhook",
            source_args={"port": 5000},
            source_filters=[],
        )

        result = meta_info_filter(source)

        assert result.filter_name == "eda.builtin.insert_meta_info"
        assert result.filter_args == {
            "source_name": "my_webhook",
            "source_type": "ansible.eda.webhook",
        }


class TestStartSourceExceptions:
    """Test start_source exception handling."""

    @pytest.mark.asyncio
    async def test_source_plugin_not_found(self):
        """Test SourcePluginNotFoundException is raised."""
        source = EventSource(
            name="test_source",
            source_name="nonexistent_source",
            source_args={},
            source_filters=[],
        )

        queue = asyncio.Queue()

        with patch(
            "ansible_rulebook.source_loader.has_source", return_value=False
        ):
            with pytest.raises(SourcePluginNotFoundException):
                await start_source(source, [], {}, queue)

    @pytest.mark.asyncio
    async def test_source_plugin_missing_main(self):
        """Test SourcePluginMainMissingException is raised."""
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
    async def test_source_plugin_not_async(self):
        """Test SourcePluginNotAsyncioCompatibleException is raised."""
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
    async def test_filter_not_found(self):
        """Test SourceFilterNotFoundException is raised."""
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
                "ansible_rulebook.source_loader.has_source_filter",
                return_value=False,
            ):
                with patch(
                    "ansible_rulebook.source_loader.has_builtin_filter",
                    return_value=False,
                ):
                    with pytest.raises(SourceFilterNotFoundException):
                        await start_source(source, [source_dir], {}, queue)

        finally:
            os.unlink(temp_path)


class TestStartSourceWithBroadcast:
    """Test start_source with broadcast callback."""

    @pytest.mark.asyncio
    async def test_start_source_with_broadcast_callback(self):
        """Test start_source calls broadcast_callback on shutdown."""
        source = EventSource(
            name="test_source",
            source_name="mock_source",
            source_args={},
            source_filters=[],
        )

        queue = asyncio.Queue()

        # Mock source execution
        async def mock_source_main(queue, args):
            await queue.put({"test": "event"})

        # Mock meta info filter
        def mock_meta_filter(event, **kwargs):
            return {**event, "meta": {"filtered": True}}

        # Track broadcast calls
        broadcast_calls = []

        async def mock_broadcast_callback(shutdown):
            broadcast_calls.append(shutdown)

        with patch("os.path.exists", return_value=True):
            with patch(
                "ansible_rulebook.source_loader.has_builtin_filter",
                return_value=True,
            ):
                with patch(
                    "ansible_rulebook.source_loader.find_builtin_filter",
                    return_value="/fake/filter.py",
                ):
                    with patch(
                        "ansible_rulebook.source_loader.runpy.run_path"
                    ) as mock_run_path:

                        def run_path_side_effect(path):
                            if "mock_source.py" in path:
                                return {"main": mock_source_main}
                            else:
                                return {"main": mock_meta_filter}

                        mock_run_path.side_effect = run_path_side_effect

                        # Run start_source with broadcast callback
                        await start_source(
                            source,
                            ["/fake/source/dir"],
                            {},
                            queue,
                            broadcast_callback=mock_broadcast_callback,
                        )

        # Verify event was processed
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert "test" in event

        # Give background task time to complete
        await asyncio.sleep(0.1)

        # Verify broadcast was called
        assert len(broadcast_calls) > 0
        assert isinstance(broadcast_calls[0], Shutdown)

    @pytest.mark.asyncio
    async def test_start_source_without_broadcast_callback(self):
        """Test start_source puts shutdown to queue without callback."""
        source = EventSource(
            name="test_source",
            source_name="mock_source",
            source_args={},
            source_filters=[],
        )

        queue = asyncio.Queue()

        # Mock source execution
        async def mock_source_main(queue, args):
            await queue.put({"test": "event"})

        # Mock meta info filter
        def mock_meta_filter(event, **kwargs):
            return {**event, "meta": {"filtered": True}}

        with patch("os.path.exists", return_value=True):
            with patch(
                "ansible_rulebook.source_loader.has_builtin_filter",
                return_value=True,
            ):
                with patch(
                    "ansible_rulebook.source_loader.find_builtin_filter",
                    return_value="/fake/filter.py",
                ):
                    with patch(
                        "ansible_rulebook.source_loader.runpy.run_path"
                    ) as mock_run_path:

                        def run_path_side_effect(path):
                            if "mock_source.py" in path:
                                return {"main": mock_source_main}
                            else:
                                return {"main": mock_meta_filter}

                        mock_run_path.side_effect = run_path_side_effect

                        # Run start_source WITHOUT broadcast callback
                        await start_source(
                            source,
                            ["/fake/source/dir"],
                            {},
                            queue,
                        )

        # Verify event was processed
        event = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert "test" in event

        # Verify shutdown was put directly to queue
        shutdown = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert isinstance(shutdown, Shutdown)
        assert "mock_source" in shutdown.message


class TestStartSourceCancellation:
    """Test start_source cancellation handling."""

    @pytest.mark.asyncio
    async def test_start_source_cancelled_error(self):
        """Test start_source handles CancelledError."""
        source = EventSource(
            name="test_source",
            source_name="mock_source",
            source_args={},
            source_filters=[],
        )

        queue = asyncio.Queue()

        # Mock source that waits indefinitely
        async def mock_source_main(queue, args):
            await asyncio.sleep(10000)  # Long sleep

        def mock_meta_filter(event, **kwargs):
            return {**event, "meta": {"filtered": True}}

        with patch("os.path.exists", return_value=True):
            with patch(
                "ansible_rulebook.source_loader.has_builtin_filter",
                return_value=True,
            ):
                with patch(
                    "ansible_rulebook.source_loader.find_builtin_filter",
                    return_value="/fake/filter.py",
                ):
                    with patch(
                        "ansible_rulebook.source_loader.runpy.run_path"
                    ) as mock_run_path:

                        def run_path_side_effect(path):
                            if "mock_source.py" in path:
                                return {"main": mock_source_main}
                            else:
                                return {"main": mock_meta_filter}

                        mock_run_path.side_effect = run_path_side_effect

                        # Start source and cancel it
                        task = asyncio.create_task(
                            start_source(
                                source, ["/fake/source/dir"], {}, queue
                            )
                        )

                        await asyncio.sleep(0.1)
                        task.cancel()

                        # Should handle cancellation and put shutdown
                        try:
                            await task
                        except asyncio.CancelledError:
                            pass

        # Should have shutdown message in queue
        shutdown = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert isinstance(shutdown, Shutdown)
        assert "task cancelled" in shutdown.message.lower()
