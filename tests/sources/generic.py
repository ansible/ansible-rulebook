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

import asyncio
import random
from typing import Any, Dict


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    payload = args.get("payload")
    randomize = args.get("randomize", False)
    create_index = args.get("create_index", None)
    delay = int(args.get("delay", 0))
    loop_count = int(args.get("loop_count", 1))  # -1 infinite
    loop_delay = int(args.get("loop_delay", 0))

    if not isinstance(payload, list):
        payload = [payload]

    iteration = 0
    index = 0
    while iteration != loop_count:
        if loop_delay > 0 and iteration > 0:
            await asyncio.sleep(loop_delay)
        if randomize:
            random.shuffle(payload)
        for event in payload:
            if create_index:
                event.update({f"{create_index}": index})
            await queue.put(event)
            await asyncio.sleep(delay)
            index += 1
        iteration += 1


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(
        main(
            MockQueue(),
            dict(
                randomize=True,
                create_index="my_index",
                loop_count=2,
                payload=[dict(i=1), dict(f=3.14159), dict(b=False)],
            ),
        )
    )
