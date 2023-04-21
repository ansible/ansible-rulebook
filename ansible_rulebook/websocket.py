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

import base64
import json
import logging
import os
import ssl
import tempfile
from asyncio.exceptions import CancelledError

import websockets
import yaml

from ansible_rulebook import rules_parser as rules_parser
from ansible_rulebook.common import StartupArgs

logger = logging.getLogger(__name__)


async def request_workload(
    activation_id: str, websocket_address: str, websocket_ssl_verify: str
) -> StartupArgs:
    logger.info("websocket %s connecting", websocket_address)
    async with websockets.connect(
        websocket_address,
        ssl=_sslcontext(websocket_address, websocket_ssl_verify),
    ) as websocket:
        try:
            logger.info("websocket %s connected", websocket_address)
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
                        os.write(
                            project_data_fh, base64.b64decode(data.get("data"))
                        )
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
                    response.controller_verify_ssl = data.get("ssl_verify")
            return response
        except CancelledError:
            logger.info("closing websocket due to task cancelled")
            return
        except websockets.exceptions.ConnectionClosed:
            logger.info("websocket %s closed", websocket_address)
            return


async def send_event_log_to_websocket(
    event_log, websocket_address, websocket_ssl_verify
):
    logger.info("websocket %s connecting", websocket_address)
    async for websocket in websockets.connect(
        websocket_address,
        logger=logger,
        ssl=_sslcontext(websocket_address, websocket_ssl_verify),
    ):
        logger.info("websocket %s connected", websocket_address)
        event = None
        try:
            while True:
                event = await event_log.get()
                await websocket.send(json.dumps(event))
                if event == dict(type="Shutdown"):
                    return
        except websockets.ConnectionClosed:
            logger.warning("websocket %s connection closed", websocket_address)
        except CancelledError:
            logger.info("closing websocket due to task cancelled")
            return
        except BaseException:
            logger.exception("websocket error on %s", event)


def _sslcontext(url, ssl_verify) -> ssl.SSLContext:
    if url.startswith("wss"):
        if ssl_verify.lower() == "yes":
            return ssl.create_default_context()
        elif ssl_verify.lower() == "no":
            return ssl._create_unverified_context()
        return ssl.create_default_context(cafile=ssl_verify)
    return None
