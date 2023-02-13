"""
Module with tests for operators
"""
import logging
import subprocess

import pytest
from pytest_check import check

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
        assert (
            "Negation round 1 passed" in result.stdout
        ), "not operator failed"

    with check:
        assert (
            "Negation round 2 passed" in result.stdout
        ), "not operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "not-equal #1 passed" in line
                ]
            )
            == 1
        ), "not-equal operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "not-equal #2 passed" in line
                ]
            )
            == 2
        ), "not-equal operator failed"

    with check:
        assert (
            "not-equal #3 passed" in result.stdout
        ), "not-equal operator failed, booleans"

    # TODO: Compare between floats and ints
    # Ref: https://issues.redhat.com/browse/AAP-9095
    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "less-than #1 passed" in line
                ]
            )
            == 1
        ), "less-than operator failed, floats"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "less-than #2 passed" in line
                ]
            )
            == 1
        ), "less-than operator failed, ints"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "less-equal #1 passed" in line
                ]
            )
            == 1
        ), "less-equal operator failed, ints"

    with check:
        assert (
            "less-equal #2 passed" in result.stdout
        ), "less-equal operator failed, floats"

    # FAIL: Compare between floats and ints
    # Ref: https://issues.redhat.com/browse/AAP-9282
    with check:
        assert (
            "test equal #1 passed" in result.stdout
        ), "equal operator failed, floats and ints"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test equal #2 passed" in line
                ]
            )
            == 1
        ), "equal operator failed, strings"

    with check:
        assert (
            "test equal #3 passed" in result.stdout
        ), "equal operator failed, ints"

    with check:
        assert (
            "test equal #4 passed" in result.stdout
        ), "equal operator failed, booleans"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test greater than #1 passed" in line
                ]
            )
            == 1
        ), "greater than operator failed, ints"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test greater than #2 passed" in line
                ]
            )
            == 1
        ), "greater than operator failed, floats"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test greater-equal #2 passed" in line
                ]
            )
            == 2
        ), "greater-equal operator failed, floats"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test plain boolean #1 passed" in line
                ]
            )
            == 1
        ), "plain boolean operator failed"

    with check:
        assert (
            "test null boolean #1 passed" in result.stdout
        ), "null boolean failed"

    with check:
        assert (
            "null equal false should not be printed" not in result.stdout
        ), "null equal false failed"

    with check:
        assert (
            "Ruleset: Test relational operators rule: Finish"
            " - test shutdown msg has initiated shutdown" in result.stdout
        ), "Shutdown message failed"

    assert len(result.stdout.splitlines()) == 21, "Unexpected output"


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
        assert (
            "Event matched: {'id': 'test_contains_1'" in result.stdout
        ), "contains operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "not-in #1 passed" in line
                ]
            )
            == 2
        ), "not-in operator failed hardcoded list"

    with check:
        assert (
            "not-in #2 passed" in result.stdout
        ), "not-in operator failed, string"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "not-in #3 passed" in line
                ]
            )
            == 1
        ), "not-in operator failed, integer"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "not-in #4 passed" in line
                ]
            )
            == 1
        ), "not-in operator failed, mixed types"

    with check:
        assert (
            "Winter is missing" not in result.stdout
        ), "not-cointains operator failed, output found"

    with check:
        assert (
            "not-contains #2 passed" in result.stdout
        ), "not-contains operator failed"

    with check:
        assert (
            "not-contains #3 passed" in result.stdout
        ), "not-contains operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test in operator #1 passed" in line
                ]
            )
            == 1
        ), "in operator failed, string hardcoded list"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test in operator #2 passed" in line
                ]
            )
            == 4
        ), "in operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "test contains operator #1 passed" in line
                ]
            )
            == 2
        ), "contains operator failed"
    assert len(result.stdout.splitlines()) == 27, "Unexpected output"


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
                    if "Test and operator #1 passes" in line
                ]
            )
            == 1
        ), "logical and operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Test or operator #1 passes" in line
                ]
            )
            == 3
        ), "logical or operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Test and-or operator #1 passes" in line
                ]
            )
            == 1
        ), "logical and-or operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Test and-or operator #3 passes" in line
                ]
            )
            == 2
        ), "logical and-or operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Test and-or operator #4 passes" in line
                ]
            )
            == 2
        ), "logical and-or operator failed"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Test and-or operator #5 passes" in line
                ]
            )
            == 4
        ), "logical and-or operator failed"
