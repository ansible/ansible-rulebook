

import asyncio
import websockets
import json


async def send_event_log_to_websocket(event_log, websocket_address):
    async for websocket in websockets.connect(websocket_address):
        try:
            while True:
                event = await event_log.get()
                await websocket.send(json.dumps(event))
        except websockets.ConnectionClosed:
            continue
