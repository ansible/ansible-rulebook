import asyncio
from typing import Any, Dict


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    delay = args.get("delay", 0)

    for j in range(int(args["i_limit"])):
        for i in range(int(args["j_limit"])):
            await queue.put(dict(nested=dict(i=i, j=j)))
            await asyncio.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), dict(i_limit=5, j_limit=5)))
