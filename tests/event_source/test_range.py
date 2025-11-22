"""Tests for range source plugin"""

import asyncio
from typing import Any

import pytest

from ansible_rulebook.event_source.range import main as range_main


class _MockQueue(asyncio.Queue[Any]):
    def __init__(self) -> None:
        self.queue: list[Any] = []

    async def put(self, item: Any) -> None:
        """Put an event into the queue"""
        self.queue.append(item)


def test_range_basic() -> None:
    """Test basic range functionality with limit."""
    myqueue = _MockQueue()
    limit = 5

    asyncio.run(
        range_main(
            myqueue,
            {"limit": limit},
        )
    )

    assert len(myqueue.queue) == limit
    for i in range(limit):
        assert myqueue.queue[i] == {"i": i}


def test_range_zero_limit() -> None:
    """Test range with zero limit produces no events."""
    myqueue = _MockQueue()

    asyncio.run(
        range_main(
            myqueue,
            {"limit": 0},
        )
    )

    assert len(myqueue.queue) == 0


def test_range_single_event() -> None:
    """Test range with limit of 1."""
    myqueue = _MockQueue()

    asyncio.run(
        range_main(
            myqueue,
            {"limit": 1},
        )
    )

    assert len(myqueue.queue) == 1
    assert myqueue.queue[0] == {"i": 0}


def test_range_large_limit() -> None:
    """Test range with larger limit."""
    myqueue = _MockQueue()
    limit = 100

    asyncio.run(
        range_main(
            myqueue,
            {"limit": limit},
        )
    )

    assert len(myqueue.queue) == limit
    # Verify first, middle, and last events
    assert myqueue.queue[0] == {"i": 0}
    assert myqueue.queue[50] == {"i": 50}
    assert myqueue.queue[99] == {"i": 99}


def test_range_with_delay() -> None:
    """Test range with delay parameter."""
    myqueue = _MockQueue()
    limit = 3
    delay = 0.001  # Very small delay for testing

    asyncio.run(
        range_main(
            myqueue,
            {"limit": limit, "delay": delay},
        )
    )

    assert len(myqueue.queue) == limit
    for i in range(limit):
        assert myqueue.queue[i] == {"i": i}


def test_range_string_limit() -> None:
    """Test range with limit as string (should be converted to int)."""
    myqueue = _MockQueue()
    limit = "10"

    asyncio.run(
        range_main(
            myqueue,
            {"limit": limit},
        )
    )

    assert len(myqueue.queue) == 10
    for i in range(10):
        assert myqueue.queue[i] == {"i": i}


@pytest.mark.parametrize("limit", [5, 10, 15, 20])
def test_range_parametrized_limits(limit: int) -> None:
    """Test range with various limit values."""
    myqueue = _MockQueue()

    asyncio.run(
        range_main(
            myqueue,
            {"limit": limit},
        )
    )

    assert len(myqueue.queue) == limit
    for i in range(limit):
        assert myqueue.queue[i] == {"i": i}


def test_range_event_structure() -> None:
    """Test that each event has the correct structure."""
    myqueue = _MockQueue()
    limit = 5

    asyncio.run(
        range_main(
            myqueue,
            {"limit": limit},
        )
    )

    for event in myqueue.queue:
        assert isinstance(event, dict)
        assert "i" in event
        assert isinstance(event["i"], int)
        assert len(event) == 1  # Only 'i' key should be present


def test_range_sequential_values() -> None:
    """Test that index values are sequential starting from 0."""
    myqueue = _MockQueue()
    limit = 20

    asyncio.run(
        range_main(
            myqueue,
            {"limit": limit},
        )
    )

    for idx, event in enumerate(myqueue.queue):
        assert event["i"] == idx
        if idx > 0:
            # Verify each value is exactly 1 more than the previous
            assert event["i"] == myqueue.queue[idx - 1]["i"] + 1
