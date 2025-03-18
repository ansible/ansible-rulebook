"""
Module with tests for source failures
"""
import logging
import subprocess

import pytest

from . import utils
from .settings import SETTINGS

LOGGER = logging.getLogger(__name__)
DEFAULT_CMD_TIMEOUT = SETTINGS["cmd_timeout"]


@pytest.mark.e2e
@pytest.mark.parametrize(
    "limit, trace_present",
    [
        pytest.param("2", False),
        pytest.param("10", True),
    ],
)
def test_source_stacktrace(update_environment, limit, trace_present):
    """
    Execute a rulebook that has source that fails with
    exception in certain conditions, we should see the
    stack trace with the file and line number in specific cases
    """

    env = update_environment({"LIMIT": limit})
    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_source_stacktrace.yml"
    vars_file = (
        utils.BASE_DATA_PATH / "extra_vars/test_variables_extra_vars.yml"
    )

    cmd = utils.Command(
        rulebook=rulebook,
        envvars="LIMIT",
        vars_file=vars_file,
    )

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        env=env,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )

    found = "sources/fail_after.py:36" in result.stderr
    assert found == trace_present
