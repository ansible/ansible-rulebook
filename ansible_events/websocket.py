import base64
import json
import logging
from asyncio.exceptions import CancelledError

import websockets
import yaml

from ansible_events import rules_parser as rules_parser
from ansible_events.key import install_private_key

logger = logging.getLogger("ansible_events.websocket")


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
            while (
                inventory is None
                or rulebook is None
                or extra_vars is None
                or private_key is None
            ):
                msg = await websocket.recv()
                data = json.loads(msg)
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
            return inventory, extra_vars, rulebook
        except CancelledError:
            logger.info("closing websocket due to task cancelled")
            return
        except websockets.exceptions.ConnectionClosed:
            logger.info("websocket %s closed", websocket_address)
            return


async def send_event_log_to_websocket(event_log, websocket_address):
    logger.info("websocket %s connecting", websocket_address)
    async for websocket in websockets.connect(websocket_address):
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
        except BaseException as e:
            logger.error(f"websocket error {type(e)} {e} on {event}")
