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
import tempfile
from asyncio.exceptions import CancelledError

import websockets
import yaml

from ansible_rulebook import rules_parser as rules_parser
from ansible_rulebook.job_template_runner import job_template_runner
from ansible_rulebook.key import install_private_key

logger = logging.getLogger(__name__)


async def request_workload(activation_id, websocket_address):
    logger.info("websocket %s connecting", websocket_address)
    async with websockets.connect(websocket_address) as websocket:
        try:
            logger.info("websocket %s connected", websocket_address)
            await websocket.send(
                json.dumps(dict(type="Worker", activation_id=activation_id))
            )
            inventory = None
            rulebook = None
            extra_vars = None
            private_key = None
            project_data_fh, project_data_file = tempfile.mkstemp()
            while (
                inventory is None
                or rulebook is None
                or extra_vars is None
                or private_key is None
            ):
                msg = await websocket.recv()
                data = json.loads(msg)
                if data.get("type") == "ProjectData":
                    if data.get("data") and data.get("more"):
                        os.write(
                            project_data_fh, base64.b64decode(data.get("data"))
                        )
                    if not data.get("data") and not data.get("more"):
                        os.close(project_data_fh)
                        logger.debug("wrote %s", project_data_file)
                if data.get("type") == "Rulebook":
                    rulebook = rules_parser.parse_rule_sets(
                        yaml.safe_load(base64.b64decode(data.get("data")))
                    )
                if data.get("type") == "Inventory":
                    inventory = yaml.safe_load(
                        base64.b64decode(data.get("data"))
                    )
                if data.get("type") == "ExtraVars":
                    extra_vars = yaml.safe_load(
                        base64.b64decode(data.get("data"))
                    )
                if data.get("type") == "SSHPrivateKey":
                    private_key = True
                    await install_private_key(
                        base64.b64decode(data.get("data")).decode()
                    )
                if data.get("type") == "ControllerUrl":
                    job_template_runner.host = data.get("data")
                if data.get("type") == "ControllerToken":
                    job_template_runner.token = data.get("data")
            return inventory, extra_vars, rulebook, project_data_file
        except CancelledError:
            logger.info("closing websocket due to task cancelled")
            return
        except websockets.exceptions.ConnectionClosed:
            logger.info("websocket %s closed", websocket_address)
            return


async def send_event_log_to_websocket(event_log, websocket_address):
    logger.info("websocket %s connecting", websocket_address)
    async for websocket in websockets.connect(
        websocket_address, logger=logger
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
