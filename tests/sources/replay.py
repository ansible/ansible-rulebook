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
import glob
import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    delay = args.get("delay", 0)
    directory = args.get("directory", None)
    if not directory:
        logger.error("No replay directory")
        return
    if not os.path.exists(directory):
        logger.error("Could not find replay directory %s", directory)
        return

    replays = sorted(glob.glob(os.path.join(directory, "*.json")))

    if not replays:
        logger.error("Could not find any replays in directory %s", directory)
        return

    for replay_file in replays:
        with open(replay_file) as f:
            await queue.put(json.loads(f.read()))
            await asyncio.sleep(delay)


if __name__ == "__main__":

    class MockQueue:
        async def put(self, event):
            print(event)

    asyncio.run(main(MockQueue(), dict(directory="replays")))
