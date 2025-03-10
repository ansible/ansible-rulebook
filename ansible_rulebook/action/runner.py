#  Copyright 2023 Red Hat, Inc.
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
import concurrent.futures
import logging
from asyncio.exceptions import CancelledError
from functools import partial

import ansible_runner
import janus

from ansible_rulebook.conf import settings

logger = logging.getLogger(__name__)


class Runner:
    """calls ansible-runner to launch either playbooks/modules
    ansible-runner
    """

    def __init__(
        self,
        data_dir,
        host_limit,
        verbosity,
        job_id,
        json_mode,
        helper,
        runner_args,
    ):
        self.private_data_dir = data_dir
        self.host_limit = host_limit
        self.verbosity = verbosity
        self.job_id = job_id
        self.helper = helper
        self.runner_args = runner_args
        self.json_mode = json_mode

    async def __call__(self):
        shutdown = False

        loop = asyncio.get_running_loop()

        queue = janus.Queue()

        # The event_callback is called from the ansible-runner thread
        # It needs a thread-safe synchronous queue.
        # Janus provides a sync queue connected to an async queue
        # Here we push the event into the sync side of janus
        def event_callback(event, *_args, **_kwargs):
            event["job_id"] = self.job_id
            event["ansible_rulebook_id"] = settings.identifier
            queue.sync_q.put({"type": "AnsibleEvent", "event": event})

        # Here we read the async side and push it into the event queue
        # which is also async.
        # We do this until cancelled at the end of the ansible runner call.
        # We might need to drain the queue here before ending.
        async def read_queue():
            try:
                while True:
                    val = await queue.async_q.get()
                    event_data = val.get("event", {})
                    val["run_at"] = event_data.get("created")
                    await self.helper.send_status(val)
            except CancelledError:
                logger.info("Ansible runner Queue task cancelled")

        def cancel_callback():
            return shutdown

        tasks = []

        tasks.append(asyncio.create_task(read_queue()))

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as task_pool:
            try:
                await loop.run_in_executor(
                    task_pool,
                    partial(
                        ansible_runner.run,
                        private_data_dir=self.private_data_dir,
                        limit=self.host_limit,
                        verbosity=self.verbosity,
                        event_handler=event_callback,
                        cancel_callback=cancel_callback,
                        json_mode=self.json_mode,
                        **self.runner_args,
                    ),
                )
            except CancelledError:
                logger.debug(
                    "Ansible Runner Thread Pool executor task cancelled"
                )
                shutdown = True
                raise
            finally:
                # Cancel the queue reading task
                for task in tasks:
                    if not task.done():
                        logger.debug("Cancel Queue reading task")
                        task.cancel()

                await asyncio.gather(*tasks)
