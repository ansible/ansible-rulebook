"""
Module with tests for general CLI runtime
"""
import logging
import subprocess
from pathlib import Path

import pytest

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook, inventory, event_delay, expected_rc",
    [
        pytest.param(
            "hello_events_with_var.yml",
            utils.DEFAULT_INVENTORY,
            "0.1",
            0,
            id="successful_rc",
        ),
        pytest.param(
            "hello_events_with_var.yml",
            Path("nonexistent.yml"),
            "0.1",
            1,
            id="failed_rc_wrong_inventory",
        ),
        pytest.param(
            "hello_events_with_var.yml",
            utils.DEFAULT_INVENTORY,
            "notafloat",
            1,
            id="failed_rc_bad_src_config",
        ),
        pytest.param(
            "malformed_rulebook.yml",
            utils.DEFAULT_INVENTORY,
            "0.1",
            1,
            id="failed_rc_rulebook_validation",
        ),
    ],
)
def test_program_return_code(
    update_environment, rulebook, inventory, event_delay, expected_rc
):
    """
    Execute a rulebook with various potential failure
    scenarios and validate that the return code is correct
    """
    env = update_environment({"EVENT_DELAY": event_delay})

    rulebook = utils.BASE_DATA_PATH / f"rulebooks/{rulebook}"
    cmd = utils.Command(
        rulebook=rulebook, envvars="EVENT_DELAY", inventory=inventory
    )

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        cwd=utils.BASE_DATA_PATH,
        env=env,
    )

    assert result.returncode == expected_rc
