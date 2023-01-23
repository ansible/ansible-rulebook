"""
Module with tests for general CLI runtime
"""
import logging
import os
import subprocess
from pathlib import Path

import pytest

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook, inventory, range_limit, expected_rc",
    [
        pytest.param(
            "hello_events_with_var.yml",
            utils.DEFAULT_INVENTORY,
            "5",
            0,
            id="successful_rc",
        ),
        pytest.param(
            "test_check_rc.yml",
            Path("nonexistent.yml"),
            "5",
            1,
            id="failed_rc_wrong_inventory",
        ),
        pytest.param(
            "test_check_rc.yml",
            utils.DEFAULT_INVENTORY,
            "notanint",
            1,
            id="failed_rc_bad_var",
        ),
        pytest.param(
            "malformed_rulebook.yml",
            utils.DEFAULT_INVENTORY,
            "5",
            1,
            id="failed_rc_rulebook_validation",
        ),
    ],
)
def test_program_return_code(rulebook, inventory, range_limit, expected_rc):
    """
    GIVEN a valid or invalid rulebook
        and a valid or invalid environment variable
        and a valid or invalid inventory
    WHEN the program is executed
    THEN the program must exit with the correct return code
    """
    os.environ["RANGE_LIMIT"] = range_limit

    rulebook = utils.BASE_DATA_PATH / f"rulebooks/{rulebook}"
    cmd = utils.Command(
        rulebook=rulebook, envvars="RANGE_LIMIT", inventory=inventory
    )

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        cwd=utils.BASE_DATA_PATH,
    )

    assert result.returncode == expected_rc
