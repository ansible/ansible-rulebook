import itertools
import time


def main(queue, args):

    for i in itertools.count(start=1):
        queue.put(dict(time=dict(tick=i)))
        time.sleep(1)


if __name__ == "__main__":

    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), dict(limit=5))
