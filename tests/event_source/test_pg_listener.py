"""Tests for pg_listener source plugin"""

import asyncio
import json
import uuid
from typing import Any, Type
from unittest.mock import AsyncMock, MagicMock, patch

import psycopg
import psycopg.errors
import pytest
import xxhash

from ansible_rulebook.event_source.pg_listener import (
    MESSAGE_CHUNK,
    MESSAGE_CHUNK_COUNT,
    MESSAGE_CHUNK_SEQUENCE,
    MESSAGE_CHUNKED_UUID,
    MESSAGE_LENGTH,
    MESSAGE_XX_HASH,
    PG_KEEPALIVE_DEFAULTS,
    MissingRequiredArgumentError,
    _build_connect_params,
    _validate_args,
    main as pg_listener_main,
)

MAX_LENGTH = 7 * 1024


class _MockQueue(asyncio.Queue[Any]):
    def __init__(self) -> None:
        self.queue: list[Any] = []

    async def put(self, event: Any) -> None:
        """Put an event into the queue"""
        self.queue.append(event)


class _AsyncIterator:
    def __init__(self, data: Any) -> None:
        self.count = 0
        self.data = data

    def __aiter__(self) -> "_AsyncIterator":
        return _AsyncIterator(self.data)

    async def __aenter__(self) -> "_AsyncIterator":
        return self

    async def __anext__(self) -> MagicMock:
        if self.count >= len(self.data):
            raise StopAsyncIteration

        mock = MagicMock()
        mock.payload = self.data[self.count]
        self.count += 1
        return mock


class _FailingIterator(_AsyncIterator):
    """Yields events then raises an exception to simulate a drop."""

    def __init__(self, data: Any, error: Exception) -> None:
        super().__init__(data)
        self.error = error

    def __aiter__(self) -> "_FailingIterator":
        return _FailingIterator(self.data, self.error)

    async def __anext__(self) -> MagicMock:
        if self.count >= len(self.data):
            raise self.error
        return await super().__anext__()


def _to_chunks(payload: str, result: list[str]) -> None:
    message_length = len(payload)
    if message_length >= MAX_LENGTH:
        xx_hash = xxhash.xxh32(payload.encode("utf-8")).hexdigest()
        message_uuid = str(uuid.uuid4())
        number_of_chunks = int(message_length / MAX_LENGTH) + 1
        chunked = {
            MESSAGE_CHUNKED_UUID: message_uuid,
            MESSAGE_CHUNK_COUNT: number_of_chunks,
            MESSAGE_LENGTH: message_length,
            MESSAGE_XX_HASH: xx_hash,
        }
        sequence = 1
        for i in range(0, message_length, MAX_LENGTH):
            chunked[MESSAGE_CHUNK] = payload[i : i + MAX_LENGTH]
            chunked[MESSAGE_CHUNK_SEQUENCE] = sequence
            sequence += 1
            result.append(json.dumps(chunked))
    else:
        result.append(payload)


TEST_PAYLOADS = [
    [{"a": 1, "b": 2}, {"name": "Fred", "kids": ["Pebbles"]}],
    [{"blob": "x" * 9000, "huge": "h" * 9000}],
    [{"a": 1, "x": 2}, {"x": "y" * 20000, "fail": False, "pi": 3.14159}],
]


@pytest.mark.parametrize("events", TEST_PAYLOADS)
def test_receive_from_pg_listener(events: list[dict[str, Any]]) -> None:
    """Test receiving different payloads from pg notify."""
    notify_payload: list[str] = []
    myqueue = _MockQueue()
    for event in events:
        _to_chunks(json.dumps(event), notify_payload)

    def my_iterator() -> _AsyncIterator:
        return _AsyncIterator(notify_payload)

    with patch(
        "ansible_rulebook.event_source.pg_listener.AsyncConnection.connect"
    ) as conn:
        mock_object = AsyncMock()
        conn.return_value = mock_object
        mock_object.closed = False
        mock_object.cursor = AsyncMock
        mock_object.notifies = my_iterator

        asyncio.run(
            pg_listener_main(
                myqueue,
                {
                    "dsn": (
                        "host=localhost dbname=mydb user=postgres "
                        "password=password"
                    ),
                    "channels": ["test"],
                },
            )
        )

        assert len(myqueue.queue) == len(events)
        index = 0
        for event in events:
            assert myqueue.queue[index] == event
            index += 1


def test_decoding_error() -> None:
    """Test json parsing error"""
    notify_payload: list[str] = ['{"a"; "b"}']
    myqueue = _MockQueue()

    def my_iterator() -> _AsyncIterator:
        return _AsyncIterator(notify_payload)

    with patch(
        "ansible_rulebook.event_source.pg_listener.AsyncConnection.connect"
    ) as conn:
        mock_object = AsyncMock()
        conn.return_value = mock_object
        mock_object.closed = False
        mock_object.cursor = AsyncMock
        mock_object.notifies = my_iterator

        with pytest.raises(json.decoder.JSONDecodeError):
            asyncio.run(
                pg_listener_main(
                    myqueue,
                    {
                        "dsn": (
                            "host=localhost dbname=mydb "
                            "user=postgres password=password"
                        ),
                        "channels": ["test"],
                    },
                )
            )


def test_operational_error_retries_then_succeeds() -> None:
    """Test that OperationalError triggers retry and recovers."""
    notify_payload: list[str] = ['{"a": "b"}']
    myqueue = _MockQueue()

    def my_iterator() -> _AsyncIterator:
        return _AsyncIterator(notify_payload)

    with patch(
        "ansible_rulebook.event_source.pg_listener.AsyncConnection.connect"
    ) as conn:
        mock_object = AsyncMock()
        mock_object.closed = False
        mock_object.cursor = AsyncMock
        mock_object.notifies = my_iterator
        conn.side_effect = [
            psycopg.OperationalError("Kaboom"),
            mock_object,
        ]

        asyncio.run(
            pg_listener_main(
                myqueue,
                {
                    "dsn": (
                        "host=localhost dbname=mydb "
                        "user=postgres password=password"
                    ),
                    "channels": ["test"],
                    "retry_max_timeout": 0,
                },
            )
        )

        assert len(myqueue.queue) == 1
        assert myqueue.queue[0] == {"a": "b"}


def test_invalid_password_is_not_retried() -> None:
    """Test that InvalidPassword raises immediately without retry."""
    myqueue = _MockQueue()

    with patch(
        "ansible_rulebook.event_source.pg_listener.AsyncConnection.connect"
    ) as conn:
        conn.side_effect = psycopg.errors.InvalidPassword(
            "password authentication failed"
        )

        with pytest.raises(psycopg.errors.InvalidPassword):
            asyncio.run(
                pg_listener_main(
                    myqueue,
                    {
                        "dsn": (
                            "host=localhost dbname=mydb "
                            "user=postgres password=wrong"
                        ),
                        "channels": ["test"],
                    },
                )
            )


def test_build_connect_params_uses_keepalive_defaults() -> None:
    """Keepalive defaults are applied when not in DSN or plugin args."""
    args = {"dsn": "host=localhost", "channels": ["test"]}
    params = _build_connect_params(args)
    for key, value in PG_KEEPALIVE_DEFAULTS.items():
        assert params[key] == value


def test_build_connect_params_user_overrides_keepalives() -> None:
    """Plugin args override defaults; unset keys still get defaults."""
    args = {
        "dsn": "host=localhost",
        "channels": ["test"],
        "keepalives_idle": 30,
        "keepalives_count": 5,
    }
    params = _build_connect_params(args)
    assert params["keepalives_idle"] == "30"
    assert params["keepalives_count"] == "5"
    assert params["keepalives"] == PG_KEEPALIVE_DEFAULTS["keepalives"]
    assert (
        params["keepalives_interval"]
        == PG_KEEPALIVE_DEFAULTS["keepalives_interval"]
    )


def test_build_connect_params_postgres_params_override_all() -> None:
    """postgres_params take highest precedence over defaults and args."""
    args = {
        "dsn": "host=localhost",
        "channels": ["test"],
        "keepalives_idle": 30,
        "postgres_params": {"keepalives_idle": "60", "dbname": "mydb"},
    }
    params = _build_connect_params(args)
    assert params["keepalives_idle"] == "60"
    assert params["dbname"] == "mydb"


def test_build_connect_params_dsn_keepalives_not_overridden() -> None:
    """Keepalive values already in the DSN are not overridden by defaults."""
    args = {
        "dsn": "host=localhost keepalives_idle=30 keepalives_count=6",
        "channels": ["test"],
    }
    params = _build_connect_params(args)
    assert "keepalives_idle" not in params
    assert "keepalives_count" not in params
    assert params["keepalives"] == PG_KEEPALIVE_DEFAULTS["keepalives"]
    assert (
        params["keepalives_interval"]
        == PG_KEEPALIVE_DEFAULTS["keepalives_interval"]
    )


def test_backoff_resets_between_failovers(capfd) -> None:
    """Each failover gets a fresh backoff starting at min, not escalating."""
    notify_payload: list[str] = ['{"a": "b"}']
    myqueue = _MockQueue()

    def my_iterator() -> _AsyncIterator:
        return _AsyncIterator(notify_payload)

    call_count = 0

    def connect_side_effect(*_args, **_kwargs):
        nonlocal call_count
        call_count += 1
        if call_count in (1, 2):
            raise psycopg.OperationalError("Outage 1")
        if call_count in (4, 5):
            raise psycopg.OperationalError("Outage 2")
        mock = AsyncMock()
        mock.closed = False
        mock.cursor = AsyncMock
        if call_count == 3:
            mock.notifies = lambda: _FailingIterator(
                notify_payload, psycopg.OperationalError("drop")
            )
        else:
            mock.notifies = my_iterator
        return mock

    with patch(
        "ansible_rulebook.event_source.pg_listener.AsyncConnection.connect",
        side_effect=connect_side_effect,
    ):
        import logging

        pg_logger = logging.getLogger(
            "ansible_rulebook.event_source.pg_listener"
        )
        log_records = []
        handler = logging.Handler()
        handler.emit = lambda record: log_records.append(record)
        pg_logger.addHandler(handler)
        try:
            asyncio.run(
                pg_listener_main(
                    myqueue,
                    {
                        "dsn": "host=localhost dbname=mydb",
                        "channels": ["test"],
                        "retry_max_timeout": 0,
                    },
                )
            )
        finally:
            pg_logger.removeHandler(handler)

        retry_msgs = [
            r for r in log_records if "reconnecting in" in r.getMessage()
        ]
        # 2 failed connect attempts per outage, 2 outages = 4 retries
        assert len(retry_msgs) == 4
        for msg in retry_msgs:
            assert "2 seconds" in msg.getMessage()


def test_validate_args_with_missing_keys() -> None:
    """Test missing required arguments."""
    args: dict[str, str] = {}
    with pytest.raises(MissingRequiredArgumentError) as exc:
        _validate_args(args)
    assert str(exc.value) == "Missing required arguments: channels"


def test_validate_args_with_missing_dsn_and_postgres_params() -> None:
    """Test missing dsn and postgres_params."""
    args = {"channels": ["test"]}
    with pytest.raises(MissingRequiredArgumentError) as exc:
        _validate_args(args)
    assert str(exc.value) == (
        "Missing dsn or postgres_params, at least one is required"
    )


def test_validate_args_with_missing_dsn() -> None:
    """Test missing dsn."""
    args = {
        "postgres_params": {"user": "postgres", "password": "password"},
        "channels": ["test"],
    }
    with (
        patch(
            "ansible_rulebook.event_source.pg_listener.REQUIRED_KEYS",
            ["dsn"],
        ),
        pytest.raises(MissingRequiredArgumentError) as exc,
    ):
        _validate_args(args)
    assert str(exc.value) == "Missing required arguments: dsn"


def test_validate_args_with_missing_postgres_params() -> None:
    """Test missing postgres_params."""
    args = {
        "dsn": "host=localhost dbname=mydb user=postgres password=password",
        "channels": ["test"],
    }
    with (
        patch(
            "ansible_rulebook.event_source.pg_listener.REQUIRED_KEYS",
            ["postgres_params"],
        ),
        pytest.raises(MissingRequiredArgumentError) as exc,
    ):
        _validate_args(args)
    assert str(exc.value) == "Missing required arguments: postgres_params"


def test_validate_args_with_valid_args() -> None:
    """Test valid arguments."""
    args = {
        "dsn": "host=localhost dbname=mydb user=postgres password=password",
        "channels": ["test"],
    }
    _validate_args(args)  # No exception should be raised


@pytest.mark.parametrize(
    "args, expected_exception, expected_message",
    [
        # Valid channels
        ({"channels": ["channel1", "channel2"], "dsn": "dummy"}, None, None),
        # Empty channels
        (
            {"channels": [], "dsn": "dummy"},
            ValueError,
            "Channels must be a list and not empty",
        ),
        # Non-list channels
        (
            {"channels": "channel1", "dsn": "dummy"},
            ValueError,
            "Channels must be a list and not empty",
        ),
        # Valid dsn
        (
            {
                "channels": ["channel1"],
                "dsn": "postgres://user:password@host:port/database",
            },
            None,
            None,
        ),
        # Invalid dsn
        (
            {"channels": ["channel1"], "dsn": 123},
            ValueError,
            "DSN must be a string",
        ),
        # Valid postgres params
        (
            {
                "channels": ["channel1"],
                "postgres_params": {"host": "localhost", "port": 5432},
            },
            None,
            None,
        ),
        # Invalid postgres params
        (
            {"channels": ["channel1"], "postgres_params": "invalid_params"},
            ValueError,
            "Postgres params must be a dictionary",
        ),
        # Invalid postgres params
        (
            {
                "channels": ["channel1"],
                "postgres_params": [{"host": "localhost"}, {"port": "5432"}],
            },
            ValueError,
            "Postgres params must be a dictionary",
        ),
    ],
)
def test_validate_args_type_checks(
    args: dict[str, Any],
    expected_exception: Type[Exception],
    expected_message: str,
) -> None:
    """Test _validate_args type checks."""
    if expected_exception is None:
        _validate_args(args)
    else:
        with pytest.raises(expected_exception, match=expected_message):
            _validate_args(args)
