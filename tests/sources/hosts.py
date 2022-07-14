import asyncio
from typing import Any, Dict


async def main(queue: asyncio.Queue, args: Dict[str, Any]):

    for i in range(int(args["limit"])):
        await queue.put(dict(i=i, meta=dict(hosts="localhost")))


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), dict(limit=5)))
