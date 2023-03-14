import asyncio
from typing import Any, Dict


def main(queue: asyncio.Queue, args: Dict[str, Any]):
    print("Not asyncio should fail")
