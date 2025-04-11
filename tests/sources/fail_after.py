"""fail_after.py.

An ansible-rulebook event source plugin for generating events with an
increasing index i. It raises an exception when it reaches the value
of fail_after (4 by default) and sleeps every delay (0 by default)

Arguments:
---------
    limit: The upper limit of the range of the index.
    delay: The number of seconds to sleep between events
    after: Fail after we have reached the prescribed amount

Example:
-------
    - fail_after:
        limit: 5
        delay: 0
        after: 4

"""

import asyncio
import secrets
from typing import Any


async def main(queue: asyncio.Queue[Any], args: dict[str, Any]) -> None:
    """Generate events with an increasing index i with a limit."""
    password = secrets.token_hex()
    after = int(args.get("after", "4"))
    delay = int(args.get("delay", "0"))

    for i in range(int(args["limit"])):
        await queue.put({"i": i})
        if i == after:
            i.something_that_does_not_exist(password)
        await asyncio.sleep(delay)


if __name__ == "__main__":
    # MockQueue if running directly

    class MockQueue(asyncio.Queue[Any]):
        """A fake queue."""

        async def put(self: "MockQueue", event: dict[str, Any]) -> None:
            """Print the event."""
            print(event)  # noqa: T201

    asyncio.run(main(MockQueue(), {"limit": 5}))
