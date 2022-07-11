import time
from datetime import datetime


def main(queue, args):

    while True:
        queue.put(
            dict(
                timestamp=dict(
                    unix_timestamp=time.mktime(datetime.now().timetuple())
                )
            )
        )
        time.sleep(1)


if __name__ == "__main__":

    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), dict(limit=5))
