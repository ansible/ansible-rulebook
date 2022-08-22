import json
import logging
from asyncio.exceptions import CancelledError

import websockets

logger = logging.getLogger("ansible_events.websocket")


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
            logger.warning("closing websocket due to task cancelled")
            return
        except BaseException as e:
            logger.error(f"websocket error {type(e)} {e} on {event}")
