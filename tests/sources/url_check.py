#  Copyright 2022 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import time

import requests
from requests.exceptions import ConnectionError, ReadTimeout


def main(queue, args):

    urls = args.get("urls", [])
    delay = args.get("delay", 1)

    if not urls:
        return

    while True:

        for url in urls:
            try:
                response = requests.get(url, timeout=10, verify=False)
                queue.put(
                    dict(
                        url_check=dict(
                            url=url,
                            status="up"
                            if response.status_code == 200
                            else "down",
                            status_code=response.status_code,
                        ),
                        meta=dict(time=time.time()),
                    )
                )

            except (ConnectionError, ReadTimeout):
                queue.put(
                    dict(
                        url_check=dict(
                            url=url, status="down", status_code=None
                        ),
                        meta=dict(time=time.time()),
                    )
                )

        time.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        def put(self, event):
            print(event)

    main(MockQueue(), {"urls": ["http://redhat.com"]})
