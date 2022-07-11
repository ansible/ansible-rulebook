import time


def main(queue, args):

    delay = args.get("delay", 0)

    for i in range(int(args["limit"])):
        queue.put(dict(i=i))
        time.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), dict(limit=5))
