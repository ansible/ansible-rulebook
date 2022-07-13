import asyncio


async def main(queue, args):
    delay = args.get("delay", 0)

    for i in range(int(args["limit"])):
        await queue.put(dict(range2=dict(i=i)))
        await asyncio.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), dict(limit=5)))
