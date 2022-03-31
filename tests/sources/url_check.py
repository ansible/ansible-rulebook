

import requests
import time


def main(queue, args):

    urls = args.get('urls', [])
    delay = args.get('delay', 1)

    if not urls:
        return

    while True:

        for url in urls:
            response = requests.get(url)
            queue.put(dict(url_check=dict(url=url,
                                          status='up' if response.status_code == 200 else 'down',
                                          status_code=response.status_code)))

        time.sleep(delay)




if __name__ == "__main__":
    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), {'urls': ['http://redhat.com']})


