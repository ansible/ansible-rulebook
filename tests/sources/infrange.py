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

"""
Infrange produces a regular range in an endless loop.
Mainly for testing and debugging purposes.
args:
  delay: Optional, interval of seconds between events. Default: 0
  data_size: Optional, size in bytes of randomized data. Default: 0
  limit: Optional, number of events per loop iteration: Default: 5
"""


import asyncio
from itertools import cycle
from random import choice
from string import ascii_letters
from typing import Any, Dict


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    delay = float(args.get("delay", 0))
    limit = int(args.get("limit", 5))
    data_size = int(args.get("data_size", 0))

    for i in cycle(range(limit)):
        payload = {
            "i": i,
            "data": "".join(choice(ascii_letters) for n in range(data_size)),
        }
        await queue.put(payload)
        await asyncio.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), dict(delay=1)))
