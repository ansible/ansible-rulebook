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
import logging
import os
import shutil
import stat
import tempfile

logger = logging.getLogger(__name__)

ssh_add = shutil.which("ssh-add")


async def install_private_key(private_key):

    """
    Install a private key into the ssh-agent.
    """

    with tempfile.TemporaryDirectory() as local_working_directory:
        # Create a file for write with mode 0600
        key_file_fd = os.open(
            os.path.join(local_working_directory, "key"),
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            mode=stat.S_IRUSR | stat.S_IWUSR,
        )
        with os.fdopen(key_file_fd, "w") as f:
            f.write(private_key)

        cmd_args = [os.path.join(local_working_directory, "key")]
        logger.debug(ssh_add)
        logger.debug(cmd_args)

        proc = await asyncio.create_subprocess_exec(
            ssh_add,
            *cmd_args,
            cwd=local_working_directory,
        )

        await proc.wait()
