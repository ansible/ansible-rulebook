"""
Module with tests for the use of variables
"""
import logging
import subprocess

import pytest
from pytest_check import check

from . import utils
from .settings import SETTINGS

LOGGER = logging.getLogger(__name__)
DEFAULT_CMD_TIMEOUT = SETTINGS["cmd_timeout"]
DEFAULT_EVENT_DELAY = SETTINGS["default_event_delay"]


@pytest.mark.e2e
def test_variables_sanity(update_environment):
    """
    Execute a rulebook that requires multiple variables to be defined
    at runtime. Variable values are supplied through environment variables
    and file variables.
    """

    env = update_environment(
        {
            "DEFAULT_EVENT_DELAY": str(DEFAULT_EVENT_DELAY),
            "E2E_AGENT_ID": "86",
            "E2E_AGENT_NAME": "Maxwell Smart",
        }
    )

    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/variables/test_variables_sanity.yml"
    )
    vars_file = (
        utils.BASE_DATA_PATH / "extra_vars/test_variables_extra_vars.yml"
    )
    cmd = utils.Command(
        rulebook=rulebook,
        envvars="DEFAULT_EVENT_DELAY,E2E_AGENT_ID,E2E_AGENT_NAME",
        vars_file=vars_file,
    )

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
        env=env,
    )

    with check:
        assert (
            "Intruder detected in hobart" in result.stdout
        ), "Failure parsing string variables from file"

    with check:
        assert (
            "Rule name: Intruder detected in hobart" in result.stdout
        ), "Failure parsing variable in rule name"

    with check:
        assert (
            "Notifying agent Maxwell Smart, ID 86" in result.stdout
        ), "Failure parsing environment variables"

    with check:
        assert (
            "Notifying law enforcement" in result.stdout
        ), "Failure parsing single condition variable from file"

    with check:
        assert (
            "Lockdown level 9.0 initiated" in result.stdout
        ), "Failure parsing multi-condition variables from file"

    with check:
        assert (
            "Intruder neutralized" in result.stdout
        ), "Failure parsing null value from variables file"
