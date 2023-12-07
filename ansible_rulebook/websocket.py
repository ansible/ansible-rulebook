#  Copyright 2022 Red Hat, Inc.
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
import base64
import json
import logging
import os
import random
import ssl
import tempfile
import typing as tp
from dataclasses import dataclass, field

import websockets
import yaml
from websockets.client import WebSocketClientProtocol

from ansible_rulebook import rules_parser as rules_parser
from ansible_rulebook.common import StartupArgs
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import ShutdownException
from ansible_rulebook.token import renew_token

logger = logging.getLogger(__name__)


BACKOFF_MIN = 1.92
BACKOFF_MAX = 60.0
BACKOFF_FACTOR = 1.618
BACKOFF_INITIAL = 5


async def _connect_websocket(
    handler: tp.Callable[[WebSocketClientProtocol], tp.Awaitable],
    retry: bool,
    **kwargs: list,
) -> tp.Any:
    logger.info("websocket %s connecting", settings.websocket_url)
    if settings.websocket_access_token:
        extra_headers = {
            "Authorization": f"Bearer {settings.websocket_access_token}"
        }
    else:
        extra_headers = {}

    result = None
    refresh = True

    while True:
        backoff_delay = BACKOFF_MIN
        try:
            async with websockets.connect(
                settings.websocket_url,
                ssl=_sslcontext(),
                extra_headers=extra_headers,
            ) as websocket:
                result = await handler(websocket, **kwargs)
                if not retry:
                    break
        except asyncio.CancelledError:  # pragma: no cover
            raise
        except ShutdownException:
            break
        except Exception as e:
            status403_legacy = (
                isinstance(e, websockets.exceptions.InvalidStatusCode)
                and e.status_code == 403
            )
            status403 = (
                isinstance(e, websockets.exceptions.InvalidStatus)
                and e.response.status_code == 403
            )
            if status403_legacy or status403:
                if refresh and settings.websocket_refresh_token:
                    new_token = await renew_token()
                    extra_headers["Authorization"] = f"Bearer {new_token}"
                    # Only attempt to refresh token once. If a new token cannot
                    # establish the connection, something else must cause 403
                    refresh = False
                else:
                    raise
            elif isinstance(e, OSError) and "[Errno 61]" in str(e):
                # Sleep and retry implemention duplicated from
                # websockets.lagacy.client.Client

                # Add a random initial delay between 0 and 5 seconds.
                # See 7.2.3. Recovering from Abnormal Closure in RFC 6544.
                if backoff_delay == BACKOFF_MIN:
                    initial_delay = random.random() * BACKOFF_INITIAL
                    logger.info(
                        "! connect failed; reconnecting in %.1f seconds",
                        initial_delay,
                        exc_info=True,
                    )
                    await asyncio.sleep(initial_delay)
                else:
                    logger.info(
                        "! connect failed again; retrying in %d seconds",
                        int(backoff_delay),
                        exc_info=True,
                    )
                    await asyncio.sleep(int(backoff_delay))
                # Increase delay with truncated exponential backoff.
                backoff_delay = backoff_delay * BACKOFF_FACTOR
                backoff_delay = min(backoff_delay, BACKOFF_MAX)
                continue
        else:
            # Connection succeeded - reset backoff delay
            backoff_delay = BACKOFF_MIN
            refresh = True

    return result


async def request_workload(activation_id: str) -> StartupArgs:
    return await _connect_websocket(
        handler=_handle_request_workload,
        retry=False,
        activation_id=activation_id,
    )


async def _handle_request_workload(
    websocket: WebSocketClientProtocol,
    activation_id: str,
) -> StartupArgs:
    logger.info("workload websocket connected")
    await websocket.send(
        json.dumps(dict(type="Worker", activation_id=activation_id))
    )

    project_data_fh = None
    response = StartupArgs()
    while True:
        msg = await websocket.recv()
        data = json.loads(msg)
        if data.get("type") == "EndOfResponse":
            break
        if data.get("type") == "ProjectData":
            if not project_data_fh:
                (
                    project_data_fh,
                    response.project_data_file,
                ) = tempfile.mkstemp()

            if data.get("data") and data.get("more"):
                os.write(project_data_fh, base64.b64decode(data.get("data")))
            if not data.get("data") and not data.get("more"):
                os.close(project_data_fh)
                logger.debug("wrote %s", response.project_data_file)
        if data.get("type") == "Rulebook":
            response.rulesets = rules_parser.parse_rule_sets(
                yaml.safe_load(base64.b64decode(data.get("data")))
            )
        if data.get("type") == "ExtraVars":
            response.variables = yaml.safe_load(
                base64.b64decode(data.get("data"))
            )
        if data.get("type") == "ControllerInfo":
            response.controller_url = data.get("url")
            response.controller_token = data.get("token")
            response.controller_ssl_verify = data.get("ssl_verify")
    return response


@dataclass
class EventLogQueue:
    queue: asyncio.Queue = field(default=None)
    event: dict = field(default=None)


async def send_event_log_to_websocket(event_log: asyncio.Queue):
    logs = EventLogQueue()
    logs.queue = event_log

    return await _connect_websocket(
        handler=_handle_send_event_log,
        retry=True,
        logs=logs,
    )


async def _handle_send_event_log(
    websocket: WebSocketClientProtocol,
    logs: EventLogQueue,
):
    logger.info("feedback websocket connected")

    if logs.event:
        logger.info("Resending last event...")
        await websocket.send(json.dumps(logs.event))
        logs.event = None

    while True:
        event = await logs.queue.get()
        logger.debug(f"Event received, {event}")

        if event == dict(type="Exit"):
            logger.info("Exiting feedback websocket task")
            raise ShutdownException(shutdown=None)

        logs.event = event
        await websocket.send(json.dumps(event))
        logs.event = None


def _sslcontext() -> tp.Optional[ssl.SSLContext]:
    if settings.websocket_url.startswith("wss"):
        ssl_verify = settings.websocket_ssl_verify.lower()
        if ssl_verify in ["yes", "true"]:
            return ssl.create_default_context()
        if ssl_verify in ["no", "false"]:
            return ssl._create_unverified_context()
        return ssl.create_default_context(cafile=ssl_verify)
    return None
