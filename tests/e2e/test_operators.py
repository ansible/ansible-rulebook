"""
Module with tests for operators
"""
import logging
import subprocess

import pytest
from pytest_check import check

from ansible_rulebook import terminal

from . import utils
from .settings import SETTINGS

LOGGER = logging.getLogger(__name__)
DEFAULT_CMD_TIMEOUT = SETTINGS["cmd_timeout"]
DEFAULT_SHUTDOWN_AFTER = SETTINGS["operators_shutdown_after"]


@pytest.mark.e2e
def test_relational_operators(update_environment):
    """
    Run a rulebook with several rules to test relational operators
    """
    env = update_environment(
        {"DEFAULT_SHUTDOWN_AFTER": str(DEFAULT_SHUTDOWN_AFTER)}
    )
    rulebook = (
        utils.BASE_DATA_PATH
        / "rulebooks/operators/test_relational_operators.yml"
    )
    vars_file = utils.BASE_DATA_PATH / "extra_vars/operator_variables.yml"
    cmd = utils.Command(
        rulebook=rulebook,
        vars_file=vars_file,
        envvars="DEFAULT_SHUTDOWN_AFTER",
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

    assert result.returncode == 0
    assert not result.stderr

    with check:
        assert "Output for testcase #01" in result.stdout, "testcase #1 failed"

    with check:
        assert "Output for testcase #02" in result.stdout, "testcase #2 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #03" in line
                ]
            )
            == 1
        ), "testcase #3 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #04" in line
                ]
            )
            == 2
        ), "testcase #4 failed"

    with check:
        assert "Output for testcase #05" in result.stdout, "testcase #5 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #06" in line
                ]
            )
            == 1
        ), "testcase #6 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #07" in line
                ]
            )
            == 1
        ), "testcase #7 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #08" in line
                ]
            )
            == 1
        ), "testcase #8 failed"

    with check:
        assert "Output for testcase #09" in result.stdout, "testcase #9 failed"

    with check:
        assert (
            "Output for testcase #10" in result.stdout
        ), "testcase #10 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #11" in line
                ]
            )
            == 1
        ), "testcase #11 failed"

    with check:
        assert (
            "Output for testcase #12" in result.stdout
        ), "testcase #12 failed"

    with check:
        assert (
            "Output for testcase #13" in result.stdout
        ), "testcase #13 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #14" in line
                ]
            )
            == 1
        ), "Testcase #14 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #15" in line
                ]
            )
            == 1
        ), "testcase #15 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #16" in line
                ]
            )
            == 3
        ), "testcase #16, failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #17" in line
                ]
            )
            == 1
        ), "testcase #17 failed"

    with check:
        assert (
            "Output for testcase #18" in result.stdout
        ), "testcase #18 failed"

    with check:
        assert (
            "Output for testcase #19" not in result.stdout
        ), "testcase #19 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #20" in line
                ]
            )
            == 1
        ), "testcase #20 failed"

    with check:
        assert (
            "Output for testcase #21" in result.stdout
        ), "testcase #21 failed"

    with check:
        assert (
            "Output for testcase #22" in result.stdout
        ), "testcase #22 failed"

    with check:
        banners = terminal.Display.get_banners("ruleset", result.stdout)
        banners = [
            banner
            for banner in banners
            if "Test relational operators rule: Finish"
            " - test shutdown msg has initiated shutdown" in banner
        ]
        assert banners, "Shutdown message failed"

    assert len(result.stdout.splitlines()) == 100, "Unexpected output"


@pytest.mark.e2e
def test_membership_operators(update_environment):
    """
    Run a rulebook with several rules to test membership operators
    """
    env = update_environment(
        {"DEFAULT_SHUTDOWN_AFTER": str(DEFAULT_SHUTDOWN_AFTER)}
    )
    rulebook = (
        utils.BASE_DATA_PATH
        / "rulebooks/operators/test_membership_operators.yml"
    )
    vars_file = utils.BASE_DATA_PATH / "extra_vars/operator_variables.yml"
    cmd = utils.Command(
        rulebook=rulebook,
        vars_file=vars_file,
        envvars="DEFAULT_SHUTDOWN_AFTER",
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

    assert result.returncode == 0
    assert not result.stderr

    with check:
        assert "Output for Testcase #01" in result.stdout, "Testcase #1 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for Testcase #02" in line
                ]
            )
            == 2
        ), "Testcase #2 failed"

    with check:
        assert "Output for Testcase #03" in result.stdout, "Testcase #3"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for Testcase #04" in line
                ]
            )
            == 1
        ), "Testcase #4 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for Testcase #05" in line
                ]
            )
            == 1
        ), "Testcase #5 failed"

    with check:
        assert "Winter is missing" not in result.stdout, "Testcase #6 failed"

    with check:
        assert "Output for Testcase #07" in result.stdout, "Testcase #7 failed"

    with check:
        assert "Output for Testcase #08" in result.stdout, "Testcase #8 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for Testcase #09" in line
                ]
            )
            == 1
        ), "Testcase #9"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for Testcase #10" in line
                ]
            )
            == 4
        ), "Testcase #10 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for Testcase #11" in line
                ]
            )
            == 5
        ), "Testcase #11 failed"

    with check:
        assert (
            "Output for Testcase #12" in result.stdout
        ), "Testcase #12 failed"

    assert len(result.stdout.splitlines()) == 76, "Unexpected output"


@pytest.mark.e2e
def test_logical_operators(update_environment):
    """
    Run a rulebook with several rules to test logical operators
    """
    env = update_environment(
        {"DEFAULT_SHUTDOWN_AFTER": str(DEFAULT_SHUTDOWN_AFTER)}
    )
    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/operators/test_logical_operators.yml"
    )
    vars_file = utils.BASE_DATA_PATH / "extra_vars/operator_variables.yml"
    cmd = utils.Command(
        rulebook=rulebook,
        vars_file=vars_file,
        envvars="DEFAULT_SHUTDOWN_AFTER",
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

    assert result.returncode == 0
    assert not result.stderr

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Testcase #01" in line
                ]
            )
            == 1
        ), "Testcase #1 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Testcase #02" in line
                ]
            )
            == 3
        ), "Testcase #2 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Testcase #03 passes" in line
                ]
            )
            == 1
        ), "Testcase #3 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Testcase #04 passes" in line
                ]
            )
            == 2
        ), "Testcase #4 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Testcase #05 passes" in line
                ]
            )
            == 2
        ), "Testcase #5 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Testcase #06 passes" in line
                ]
            )
            == 4
        ), "Testcase #6 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Testcase #07 passes" in line
                ]
            )
            == 1
        ), "Testcase #7 failed"

    with check:
        assert "Testcase #08 passes" in result.stdout, "Testcase #8 failed"

    with check:
        assert (
            "Testcase #09 passes, "
            "output: Status: new york down, addis ababa down" in result.stdout
        ), "Testcase #9 failed"

    with check:
        assert (
            "Testcase #10 passes, output: IDS state: None" in result.stdout
        ), "Testcase #10 failed"

    with check:
        assert "Testcase #11 passes" in result.stdout, "Testcase #11 failed"

    with check:
        assert "Testcase #12 passes" in result.stdout, "Testcase #12 failed"


@pytest.mark.e2e
def test_string_match():
    """
    Execute a rulebook that performs match operations on a string
    """

    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/operators/test_string_match.yml"
    )
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )

    with check:
        assert "Output for testcase #01" in result.stdout, "testcase #1 failed"

    with check:
        assert "Output for testcase #02" in result.stdout, "testcase #2 failed"

    with check:
        assert "Output for testcase #03" in result.stdout, "testcase #3 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #04" in line
                ]
            )
            == 2
        ), "testcase #4 failed"

    with check:
        assert "Output for testcase #05" in result.stdout, "testcase #5 failed"

    with check:
        assert "Output for testcase #06" in result.stdout, "testcase #6 failed"

    with check:
        assert "Output for testcase #07" in result.stdout, "testcase #7 failed"


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook",
    [
        pytest.param(
            "test_string_search_search.yml",
            id="string_search_search",
        ),
        pytest.param(
            "test_string_search_regex.yml",
            id="string_search_regex",
        ),
    ],
)
def test_string_search(rulebook):
    """
    Execute a rulebook that performs search and regex operations on a string
    """

    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )

    with check:
        assert "Output for testcase #01" in result.stdout, "testcase #1 failed"

    with check:
        assert "Output for testcase #02" in result.stdout, "testcase #2 failed"

    with check:
        assert "Output for testcase #03" in result.stdout, "testcase #3 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #04" in line
                ]
            )
            == 2
        ), "testcase #4 failed"

    with check:
        assert "Output for testcase #05" in result.stdout, "testcase #5 failed"

    with check:
        assert "Output for testcase #06" in result.stdout, "testcase #6 failed"

    with check:
        assert "Output for testcase #07" in result.stdout, "testcase #7 failed"


@pytest.mark.e2e
def test_select_operator():
    """
    Run a rulebook with several rules to test the select operator
    """
    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/operators/test_select_operator.yml"
    )
    vars_file = utils.BASE_DATA_PATH / "extra_vars/operator_variables.yml"
    cmd = utils.Command(rulebook=rulebook, vars_file=vars_file)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )

    assert result.returncode == 0
    assert not result.stderr

    with check:
        assert (
            "Negative testcase (should not fire)" not in result.stdout
        ), "negative testcase fired unexpectedly"

    with check:
        assert (
            "Output for testcase #01" in result.stdout
        ), "testcase #01 failed"

    with check:
        assert (
            "Output for testcase #02" in result.stdout
        ), "testcase #02 failed"

    with check:
        assert (
            "Output for testcase #03" in result.stdout
        ), "testcase #03 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #04" in line
                ]
            )
            == 2
        ), "testcase #04 failed"

    with check:
        assert (
            "Output for testcase #05" in result.stdout
        ), "testcase #05 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #06" in line
                ]
            )
            == 2
        ), "testcase #06 failed"


@pytest.mark.e2e
def test_selectattr_operator():
    """
    Run a rulebook with several rules to test the selectattr operator
    """
    rulebook = (
        utils.BASE_DATA_PATH
        / "rulebooks/operators/test_selectattr_operator.yml"
    )
    vars_file = utils.BASE_DATA_PATH / "extra_vars/operator_variables.yml"
    cmd = utils.Command(rulebook=rulebook, vars_file=vars_file)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )

    assert result.returncode == 0
    assert not result.stderr

    with check:
        assert (
            "Negative testcase (should not fire)" not in result.stdout
        ), "negative testcase fired unexpectedly"

    with check:
        assert (
            "Output for testcase #01" in result.stdout
        ), "testcase #01 failed"

    with check:
        assert (
            "Output for testcase #02" in result.stdout
        ), "testcase #02 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #03" in line
                ]
            )
            == 2
        ), "testcase #03 failed"

    with check:
        assert (
            "Output for testcase #04" in result.stdout
        ), "testcase #04 failed"

    with check:
        assert (
            "Output for testcase #05" in result.stdout
        ), "testcase #05 failed"

    with check:
        assert (
            "Output for testcase #06" in result.stdout
        ), "testcase #06 failed"

    with check:
        assert (
            "Output for testcase #07" in result.stdout
        ), "testcase #07 failed"

    with check:
        assert (
            "Output for testcase #08" in result.stdout
        ), "testcase #08 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #09" in line
                ]
            )
            == 2
        ), "testcase #09 failed"

    with check:
        assert (
            "Output for testcase #10" in result.stdout
        ), "testcase #10 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #11" in line
                ]
            )
            == 1
        ), "testcase #11 failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Output for testcase #12" in line
                ]
            )
            == 1
        ), "testcase #12 failed"
