import asyncio
import logging
import os
import shutil
import stat
import tempfile

logger = logging.getLogger()

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
