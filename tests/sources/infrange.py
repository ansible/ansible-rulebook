"""
infrange produces a regular range in an endless loop.
Mainly for testing and debugging purposes.
"""


import asyncio
from itertools import cycle
from typing import Any, Dict


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    delay = args.get("delay", 0)

    for i in cycle(range(int(args["limit"]))):
        await queue.put(dict(i=i))
        await asyncio.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), dict(limit=5)))
