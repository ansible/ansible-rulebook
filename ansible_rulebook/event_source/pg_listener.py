import asyncio
import json
import logging
from typing import Any

import xxhash
from psycopg import AsyncConnection, OperationalError, sql
from psycopg.conninfo import conninfo_to_dict
from psycopg.errors import InvalidAuthorizationSpecification, InvalidPassword
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

DOCUMENTATION = r"""
---
short_description: Read events from pg_pub_sub.
description:
  - An ansible-rulebook event source plugin for reading events from pg_pub_sub.
options:
  dsn:
    description:
      - The connection string/dsn for Postgres as supported by psycopg/libpq.
        Refer to https://www.postgresql.org/docs/current/libpq-connect.html#
        LIBPQ-CONNSTRING-KEYWORD-VALUE.
        Either dsn or postgres_params is required.
    type: str
  postgres_params:
    description:
      - The parameters for the pg connection as they are supported
        by psycopg/libpq.
        Refer to https://www.postgresql.org/docs/current/libpq-connect.html#
        LIBPQ-PARAMKEYWORDS
        If the param is already in the dsn, it will be overridden by the
        value in postgres_params.
        Either dsn or postgres_params is required.
    type: dict
  channels:
    description:
      - The list of channels to listen
    type: list
    elements: str
    required: true
  retry_max_timeout:
    description:
      - Maximum backoff time in seconds when retrying after a
        transient PostgreSQL connection loss. Default is 60.
    type: float
    default: 60
  retry_attempts:
    description:
      - Maximum number of retry attempts when reconnecting after a
        transient PostgreSQL connection loss. Default is 10.
    type: int
    default: 10
  keepalives:
    description:
      - Enable TCP keepalives on the PostgreSQL connection.
        Default is 1 (enabled). Set to 0 to disable.
    type: int
    default: 1
  keepalives_idle:
    description:
      - Seconds of inactivity before sending a TCP keepalive probe.
        Default is 10. Controls how quickly a dead connection is detected
        after a database failover.
    type: int
    default: 10
  keepalives_interval:
    description:
      - Seconds between TCP keepalive probes once the idle threshold
        is reached. Default is 10.
    type: int
    default: 10
  keepalives_count:
    description:
      - Number of TCP keepalive probes before declaring the connection
        dead. Default is 3. With the defaults the connection will be
        detected as dead within ~40 seconds (10 + 10*3).
    type: int
    default: 3
notes:
  - Chunking - this is just informational, a user doesn't have to do anything
    special to enable chunking. The sender, which is the pg_notify
    action from ansible-rulebook, will decide if chunking needs to
    happen based on the size of the payload.
  - |
    If the messages are over 7KB the sender will chunk the messages
    into separate payloads with each payload having the following
    keys:
    * _message_chunked_uuid   The unique message uuid
    * _message_chunk_count    The number of chunks for the message
    * _message_chunk_sequence The sequence of the current chunk
    * _chunk                  The actual chunk
    * _message_length         The total length of the message
    * _message_xx_hash        A hash for the entire message
  - The pg_listener source will assemble the chunks and once all the
    chunks have been received it will deliver the entire payload to the
    rulebook engine. Before the payload is delivered we validated
    that the entire message has been received by validating its computed hash.
"""

EXAMPLES = r"""
- eda.builtin.pg_listener:
    dsn: "host=localhost port=5432 dbname=mydb"
    channels:
      - my_events
      - my_alerts

- eda.builtin.pg_listener:
    postgres_params:
      host: localhost
      port: 5432
      dbname: mydb
    channels:
      - my_events
      - my_alerts

- eda.builtin.pg_listener:
    dsn: "host=localhost port=5432 dbname=mydb"
    channels:
      - my_events
    keepalives_idle: 5
    keepalives_interval: 5
    keepalives_count: 2
"""

LOGGER = logging.getLogger(__name__)

MESSAGE_CHUNKED_UUID = "_message_chunked_uuid"
MESSAGE_CHUNK_COUNT = "_message_chunk_count"
MESSAGE_CHUNK_SEQUENCE = "_message_chunk_sequence"
MESSAGE_CHUNK = "_chunk"
MESSAGE_LENGTH = "_message_length"
MESSAGE_XX_HASH = "_message_xx_hash"
REQUIRED_KEYS = ["channels"]

REQUIRED_CHUNK_KEYS = (
    MESSAGE_CHUNK_COUNT,
    MESSAGE_CHUNK_SEQUENCE,
    MESSAGE_CHUNK,
    MESSAGE_LENGTH,
    MESSAGE_XX_HASH,
)


class MissingRequiredArgumentError(Exception):
    """Exception class for missing arguments."""


class MissingChunkKeyError(Exception):
    """Exception class for missing chunking keys."""

    def __init__(self: "MissingChunkKeyError", key: str) -> None:
        """Class constructor with the missing key."""
        super().__init__(f"Chunked payload is missing required {key}")


def _validate_chunked_payload(payload: dict[str, Any]) -> None:
    for key in REQUIRED_CHUNK_KEYS:
        if key not in payload:
            raise MissingChunkKeyError(key)


def _validate_args(args: dict[str, Any]) -> None:
    """Validate the arguments and raise exception accordingly."""
    missing_keys = [key for key in REQUIRED_KEYS if key not in args]
    if missing_keys:
        msg = f"Missing required arguments: {', '.join(missing_keys)}"
        raise MissingRequiredArgumentError(msg)
    if args.get("dsn") is None and args.get("postgres_params") is None:
        msg = "Missing dsn or postgres_params, at least one is required"
        raise MissingRequiredArgumentError(msg)

    # Type checking
    # TODO(alejandro): We should implement a standard way to  # NOSONAR
    # validate the schema, # noqa: TD003, FIX002
    # of the arguments for all the plugins
    err_msg = None
    if not isinstance(args["channels"], list) or not args["channels"]:
        err_msg = "Channels must be a list and not empty"
    elif args.get("dsn") is not None and not isinstance(args["dsn"], str):
        err_msg = "DSN must be a string"
    elif args.get("postgres_params") is not None and not isinstance(
        args["postgres_params"],
        dict,
    ):
        err_msg = "Postgres params must be a dictionary"
    if err_msg:
        raise ValueError(err_msg)


PG_RETRY_MAX_TIMEOUT_DEFAULT = 60
PG_RETRY_ATTEMPTS_DEFAULT = 10

PG_KEEPALIVE_DEFAULTS = {
    "keepalives": "1",
    "keepalives_idle": "10",
    "keepalives_interval": "10",
    "keepalives_count": "3",
}


async def main(queue: asyncio.Queue[Any], args: dict[str, Any]) -> None:
    """Listen for events from a channel."""
    _validate_args(args)

    max_timeout = float(
        args.get("retry_max_timeout", PG_RETRY_MAX_TIMEOUT_DEFAULT)
    )
    if max_timeout < 2.0:
        LOGGER.warning(
            "retry_max_timeout=%.1f is below minimum backoff (2s), "
            "retries will have minimal delay. Resetting to 2 seconds.",
            max_timeout,
        )
        max_timeout = 2.0

    max_attempts = int(args.get("retry_attempts", PG_RETRY_ATTEMPTS_DEFAULT))
    reconnecting = False

    # Each outage gets a fresh AsyncRetrying budget.  The retry
    # only wraps connection + LISTEN setup (a short-lived operation).
    # Once connected, _process_notifications() blocks on
    # conn.notifies() outside the retry scope.  When that connection
    # drops, the outer loop catches it and starts a new retry
    # sequence with a fresh budget.
    while True:
        conn = None
        connected = False
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(_is_retryable_pg_error),
                wait=wait_exponential(multiplier=1, min=2, max=max_timeout),
                stop=stop_after_attempt(max_attempts),
                before_sleep=_log_pg_retry,
                reraise=True,
            ):
                with attempt:
                    conn = await _connect_and_subscribe(args, reconnecting)
            connected = True
            await _process_notifications(conn, queue)
            return
        except asyncio.CancelledError:
            LOGGER.info("pg_listener shutdown requested")
            raise
        except OperationalError as e:
            if not connected or not _is_retryable_pg_error(e):
                raise
            LOGGER.warning(
                "PostgreSQL connection lost (%s); "
                "any in-progress messages were discarded",
                e,
            )
            reconnecting = True
        finally:
            if conn and not conn.closed:
                await conn.close()


def _is_retryable_pg_error(exc: BaseException) -> bool:
    """Retry on transient OperationalErrors but not on auth failures."""
    return isinstance(exc, OperationalError) and not isinstance(
        exc, (InvalidPassword, InvalidAuthorizationSpecification)
    )


def _log_pg_retry(retry_state) -> None:
    exc = retry_state.outcome.exception()
    wait = retry_state.next_action.sleep
    LOGGER.warning(
        "PostgreSQL connection lost (%s), reconnecting in %.0f seconds",
        exc,
        wait,
    )


def _build_connect_params(args: dict[str, Any]) -> dict[str, Any]:
    """Build connection params, applying keepalive defaults only for
    keys not already present in the DSN or plugin args.
    """
    dsn_keys = conninfo_to_dict(args.get("dsn", ""))
    keepalive_params = {}
    for key, default in PG_KEEPALIVE_DEFAULTS.items():
        if key in args:
            keepalive_params[key] = str(args[key])
        elif key not in dsn_keys:
            keepalive_params[key] = default
    user_params = args.get("postgres_params", {})
    return {**keepalive_params, **user_params}


async def _connect_and_subscribe(
    args: dict[str, Any],
    reconnecting: bool,
) -> AsyncConnection:
    """Connect to PostgreSQL and subscribe to channels.

    This is the short-lived operation wrapped by AsyncRetrying.
    Returns the open connection for the caller to listen on.
    """
    conn = await AsyncConnection.connect(
        conninfo=args.get("dsn", ""),
        autocommit=True,
        **_build_connect_params(args),
    )
    if reconnecting:
        LOGGER.warning("PostgreSQL connection re-established")
    cursor = conn.cursor()
    for channel in args["channels"]:
        # Compose the query safely using psycopg v3's sql module
        query = sql.SQL("LISTEN {};").format(sql.Identifier(channel))
        await cursor.execute(query)
        LOGGER.debug("Waiting for notifications on channel %s", channel)
    return conn


async def _process_notifications(
    conn: AsyncConnection,
    queue: asyncio.Queue[Any],
) -> None:
    """Block on conn.notifies() and forward events to the queue.

    Runs outside the retry scope.  Any OperationalError from a
    dropped connection propagates to the caller.
    """
    chunked_cache: dict[str, Any] = {}
    try:
        async for event in conn.notifies():
            data = json.loads(event.payload)
            if MESSAGE_CHUNKED_UUID in data:
                _validate_chunked_payload(data)
                await _handle_chunked_message(data, chunked_cache, queue)
            else:
                await queue.put(data)
    except json.decoder.JSONDecodeError:
        LOGGER.exception("Error decoding data")
        raise


async def _handle_chunked_message(
    data: dict[str, Any],
    chunked_cache: dict[str, Any],
    queue: asyncio.Queue[Any],
) -> None:
    message_uuid = data[MESSAGE_CHUNKED_UUID]
    number_of_chunks = data[MESSAGE_CHUNK_COUNT]
    message_length = data[MESSAGE_LENGTH]
    LOGGER.debug(
        "Received chunked message %s total chunks %d message length %d",
        message_uuid,
        number_of_chunks,
        message_length,
    )
    if message_uuid in chunked_cache:
        chunked_cache[message_uuid].append(data)
    else:
        chunked_cache[message_uuid] = [data]
    if (
        len(chunked_cache[message_uuid])
        == chunked_cache[message_uuid][0][MESSAGE_CHUNK_COUNT]
    ):
        LOGGER.debug(
            "Received all chunks for message %s",
            message_uuid,
        )
        all_data = ""
        for chunk in chunked_cache[message_uuid]:
            all_data += chunk[MESSAGE_CHUNK]
        chunks = chunked_cache.pop(message_uuid)
        xx_hash = xxhash.xxh32(all_data.encode("utf-8")).hexdigest()
        LOGGER.debug("Computed XX Hash is %s", xx_hash)
        LOGGER.debug(
            "XX Hash expected %s",
            chunks[0][MESSAGE_XX_HASH],
        )
        if xx_hash == chunks[0][MESSAGE_XX_HASH]:
            data = json.loads(all_data)
            await queue.put(data)
        else:
            LOGGER.error("XX Hash of chunked payload doesn't match")
    else:
        LOGGER.debug(
            "Received %d chunks for message %s",
            len(chunked_cache[message_uuid]),
            message_uuid,
        )


if __name__ == "__main__":
    # MockQueue if running directly

    class MockQueue(asyncio.Queue[Any]):
        """A fake queue."""

        async def put(self: "MockQueue", event: dict[str, Any]) -> None:
            """Print the event."""
            print(event)  # noqa: T201

    asyncio.run(
        main(
            MockQueue(),
            {
                "dsn": "host=localhost port=5432 dbname=eda user=postgres",
                "channels": ["my_channel"],
            },
        ),
    )
