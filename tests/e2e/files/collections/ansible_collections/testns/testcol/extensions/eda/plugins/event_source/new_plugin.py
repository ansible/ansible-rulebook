import asyncio
from typing import Any, Dict


async def main(queue: asyncio.Queue, args: Dict[str, Any]) -> None:
    """
    Simple event source used for deprecation/redirect testing.
    """
    message = args.get("message", "redirected plugin executed")
    await queue.put({"message": message})
