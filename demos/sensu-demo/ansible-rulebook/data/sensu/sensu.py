"""
sensu.py

An ansible-rulebook event source module for receiving events via Sensu.

Arguments:
    host: The hostname to listen to. Set to 0.0.0.0 to listen on all
          interfaces. Defaults to 127.0.0.1
    port: The TCP port to listen to.  Defaults to 5000

"""

import asyncio
# import socket
# import json
from typing import Any, Dict

from aiohttp import web

routes = web.RouteTableDef()


# async def handle_client(queue: asyncio.Queue, client):
#     loop = asyncio.get_event_loop()
#     request = None
#     while request != '':
#         # raw_req = (await loop.sock_recv(client, 255))
#         # print(raw_req)
#         # print(type(raw_req))

#         request = (await loop.sock_recv(client, 255)).decode('utf8')
#         req_body = {"request": request}

#         # figure out what the body needs to be for the event queue
#         await queue.put(req_body)
#         print(f"\nReceived the following request: {request}")
#         response = bytes(request, 'utf8')
#         print(f"\nclient: {client}")

#         # if I take out the sendall it will never move on to the next message (but the broken pipe errors stop)
#         await loop.sock_sendall(client, response)
#     client.close()

# async def main(queue: asyncio.Queue, args: Dict[str, Any]):
#     server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server.bind((args.get("host") or "localhost", args.get("port") or 5001))
#     server.listen(8)
#     server.setblocking(False)

#     loop = asyncio.get_event_loop()

#     while True:
#         client, _ = await loop.sock_accept(server)
#         loop.create_task(handle_client(queue, client))


@routes.post("/{endpoint}")
async def webhook(request: web.Request):
    # debugging what sensu is sending
    print(f"\nrequest: {request}")
    print(dir(request))
    print(f"\nrequest url: {request.url}")
    text = await request.text()
    print(f"\nrequest text: {text}")
    print(f"\nrequest values: {request.values()}")
    print(f"\nrequest content type: {request.content_type}")
    print(f"\nrequest content dict: {request._content_dict}")
    print(f"\nrequest payload: {request._payload}")
    print(f"\nrequest headers: {request._headers}")
    print(f"\nrequest raw headers: {request.raw_headers}")
    content = await request.content.read()
    decoded = content.decode('utf8')
    print(f"\nrequest content decoded: {decoded}")
    payload = {"Test": decoded}
    try:
        payload = await request.json()
    except Exception as e:
        print(e)
    print(f"\npayload: {payload}")
    endpoint = request.match_info["endpoint"]
    data = {
        "payload": payload,
        "meta": {"endpoint": endpoint, "headers": dict(request.headers)},
    }
    print(f"\ndata: {data}")
    await request.app["queue"].put(data)
    return web.Response(text=endpoint)


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    app = web.Application()
    app["queue"] = queue

    app.add_routes(routes)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(
        runner, args.get("host") or "localhost", args.get("port") or 5001
    )
    await site.start()

    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        print("Plugin Task Cancelled")
    finally:
        await runner.cleanup()

if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), {}))
