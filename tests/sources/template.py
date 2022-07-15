"""
template.py

An ansible-events event source plugin template.

Arguments:
    - delay: seconds to wait between events

Examples:
    - template:

"""
import asyncio
from typing import Any, Dict


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    delay = args.get("delay", 0)

    while True:
        await queue.put(dict(template=dict(msg="hello world")))
        await asyncio.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    mock_arguments = dict()
    asyncio.run(main(MockQueue(), mock_arguments))
