"""
Module with tests for general CLI runtime
"""
import logging
import subprocess
import time
from pathlib import Path

import pytest
from pytest_check import check

from . import utils
from .settings import SETTINGS

LOGGER = logging.getLogger(__name__)
DEFAULT_CMD_TIMEOUT = SETTINGS["cmd_timeout"]
DEFAULT_STARTUP_DELAY = SETTINGS["default_startup_delay"]
DISABLED_RULES_EVENT_DELAY = SETTINGS["disabled_rules_event_delay"]


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
            "actions/test_run_playbook.yml",
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
        timeout=DEFAULT_CMD_TIMEOUT,
        cwd=utils.BASE_DATA_PATH,
        env=env,
    )

    assert result.returncode == expected_rc


@pytest.mark.e2e
def test_disabled_rules(update_environment):
    """
    Execute a rulebook that has disabled rules and
    ensure they do not execute
    """

    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_disabled_rules.yml"
    env = update_environment(
        {
            "DEFAULT_STARTUP_DELAY": str(DEFAULT_STARTUP_DELAY),
            "DISABLED_RULES_EVENT_DELAY": str(DISABLED_RULES_EVENT_DELAY),
        }
    )

    cmd = utils.Command(
        rulebook=rulebook,
        envvars="DEFAULT_STARTUP_DELAY,DISABLED_RULES_EVENT_DELAY",
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
            "Enabled rule fired correctly" in result.stdout
        ), "Enabled rule failed to fire"

    with check:
        assert (
            "Disabled rule should not have fired" not in result.stdout
        ), "A disabled rule fired unexpectedly"


@pytest.mark.e2e
@pytest.mark.parametrize(
    "shutdown_delay",
    [
        pytest.param(
            None,
            id="default_timeout",
        ),
        pytest.param(
            5,
            id="custom_timeout",
        ),
    ],
)
def test_terminate_process_source_end(update_environment, shutdown_delay):
    """
    Execute a rulebook and ensure ansible-rulebook terminates correctly
    after an event source plugin ends
    """

    if shutdown_delay:
        env = update_environment({"EDA_SHUTDOWN_DELAY": str(shutdown_delay)})

    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_process_source_end.yml"
    cmd = utils.Command(rulebook=rulebook, execution_strategy="parallel")

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
        env=env if shutdown_delay else None,
    )

    assert result.returncode == 0
    assert not result.stderr

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if '"msg": "Sleeping..."' in line
                ]
            )
            == 1
        ), "long-running playbook failed to fire"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if "Parallel action triggered successfully" in line
                ]
            )
            == 3
        ), "a parallel action failed to fire"

    with check:
        assert (
            len(
                [
                    line
                    for line in result.stdout.splitlines()
                    if '"msg": "Rise and shine..."' in line
                ]
            )
            == 1
        ), "long-running playbook failed to finish"


@pytest.mark.e2e
def test_terminate_process_sigint():
    """
    Execute a rulebook and ensure ansible-rulebook terminates correctly
    after a SIGINT is issued
    """

    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_process_sigint.yml"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")

    process = subprocess.Popen(
        cmd,
        cwd=utils.BASE_DATA_PATH,
        text=True,
        stdout=subprocess.PIPE,
    )

    start = time.time()
    while line := process.stdout.readline():
        if "'action': 'long_loop'" in line:
            process.send_signal(subprocess.signal.SIGINT)
            process.wait()
            break
        time.sleep(0.1)
        if time.time() - start > DEFAULT_CMD_TIMEOUT:
            process.kill()

    assert process.returncode == 130


@pytest.mark.e2e
def test_hot_reload():
    """
    Execute a rulebook with hot-reload option,
    check for first action being triggered,
    then modify the content of the rulebook,
    check for the other action being triggered.
    """

    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_hot_reload.yml"
    cmd = utils.Command(rulebook=rulebook, hot_reload=True)

    LOGGER.info(f"Running command: {cmd}")

    process = subprocess.Popen(
        cmd,
        cwd=utils.BASE_DATA_PATH,
        text=True,
        stdout=subprocess.PIPE,
    )

    with open(rulebook, "rt") as file:
        original_data = file.read()
    found_rule_1_in_out = False
    found_rule_2_in_out = False

    start = time.time()
    while line := process.stdout.readline():
        if "Rule 1: I matched for value_a" in line:
            found_rule_1_in_out = True
            break
        time.sleep(0.1)
        if time.time() - start > DEFAULT_CMD_TIMEOUT:
            process.kill()

    assert found_rule_1_in_out

    data = original_data.replace('- action: "value_a"', '- action: "value_b"')
    with open(rulebook, "wt") as file:
        file.write(data)

    start = time.time()
    while line := process.stdout.readline():
        if "Rule 2: I have now matched for value_b" in line:
            found_rule_2_in_out = True
            break
        time.sleep(0.1)
        if time.time() - start > DEFAULT_CMD_TIMEOUT:
            process.kill()

    with open(rulebook, "wt") as file:
        file.write(original_data)

    assert found_rule_2_in_out
