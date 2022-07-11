import asyncio


async def main(queue: asyncio.Queue, args):
    delay = args.get("delay", 0)

    for i in range(int(args["limit"])):
        await queue.put(dict(i=i))
        await asyncio.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), dict(limit=5)))
