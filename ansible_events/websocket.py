

import asyncio
import websockets
import json
import logging


async def send_event_log_to_websocket(event_log, websocket_address):
    logger = logging.getLogger()
    async for websocket in websockets.connect(websocket_address):
        event = None
        try:
            while True:
                event = await event_log.get()
                await websocket.send(json.dumps(event))
        except websockets.ConnectionClosed:
            logger.warning(f'websocket {websocket_address} connection closed')
            continue
        except BaseException as e:
            logger.error(f'websocket error {e} on {event}')
            continue
