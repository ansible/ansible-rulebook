"""
Module with tests for operators
"""
import logging
import pprint
import subprocess

import jinja2
import pytest
from pytest_check import check

from . import utils
from .settings import SETTINGS

LOGGER = logging.getLogger(__name__)
DEFAULT_CMD_TIMEOUT = SETTINGS["cmd_timeout"]
DEFAULT_SHUTDOWN_AFTER = SETTINGS["default_shutdown_after"]
DEFAULT_EVENT_DELAY = SETTINGS["default_event_delay"]
DEFAULT_STARTUP_DELAY = SETTINGS["default_startup_delay"]


@pytest.mark.e2e
def test_actions_sanity(update_environment):
    """
    A rulebook that contains multiple rules with the following list of actions:
        * run_playbook
        * run_module
        * print_event
        * debug
        * post_event
        * set_fact
        * retract_fact
    Each rule has specific logic to be executed only one time
    and each action produces a specific output to be verified.
    """
    env = update_environment(
        {
            "DEFAULT_SHUTDOWN_AFTER": str(DEFAULT_SHUTDOWN_AFTER),
            "DEFAULT_EVENT_DELAY": str(DEFAULT_EVENT_DELAY),
        }
    )

    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/actions/test_actions_sanity.yml"
    )
    inventory = utils.BASE_DATA_PATH / "inventories/default_inventory.ini"
    cmd = utils.Command(
        rulebook=rulebook,
        inventory=inventory,
        envvars="DEFAULT_SHUTDOWN_AFTER,DEFAULT_EVENT_DELAY",
    )

    with open(inventory) as f:
        inventory_data = pprint.pformat(f.read())

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
    event_debug_expected_output_tpl = """kwargs:
{'hosts': ['all'],
 'inventory': {{INVENTORY_DATA}},
 'project_data_file': None,
 'ruleset': 'Test actions sanity',
 'source_rule_name': 'debug',
 'source_ruleset_name': 'Test actions sanity',
 'variables': {'DEFAULT_EVENT_DELAY': '{{DEFAULT_EVENT_DELAY}}',
               'DEFAULT_SHUTDOWN_AFTER': '{{DEFAULT_SHUTDOWN_AFTER}}',
               'event': {'action': 'debug'}}}"""  # noqa: E501

    event_debug_expected_output = jinja2.Template(
        event_debug_expected_output_tpl
    ).render(
        DEFAULT_SHUTDOWN_AFTER=DEFAULT_SHUTDOWN_AFTER,
        DEFAULT_EVENT_DELAY=DEFAULT_EVENT_DELAY,
        INVENTORY_DATA=inventory_data,
    )

    # assert each expected output per action tested
    with check:
        assert (
            "Event matched: {'action': 'run_playbook'}" in result.stdout
        ), "run_playbook action failed"

    with check:
        assert (
            "Event matched: {'action': 'run_module'}" in result.stdout
        ), "run_module action failed"

    with check:
        assert (
            "{'action': 'print_event'}" in result.stdout
        ), "print_event action with single event failed"

    with check:
        assert (
            "{'m_1': {'action': 'print_event_multi_2'}, 'm_0': "
            "{'action': 'print_event_multi_1'}}" in result.stdout
        ), "print_event action with multiple events failed"

    with check:
        assert (
            event_debug_expected_output in result.stdout
        ), "debug action failed"

    with check:
        assert (
            "Event matched in same ruleset: sent" in result.stdout
        ), "post_event action failed"

    with check:
        assert (
            "Event matched in different ruleset: sent" in result.stdout
        ), "post_event action across rulesets failed"

    with check:
        assert (
            "Fact matched in same ruleset: sent" in result.stdout
        ), "set_fact action failed"

    with check:
        assert (
            "Fact matched in different ruleset: sent" in result.stdout
        ), "set_fact action across rulesets failed"

    with check:
        assert (
            "Retracted fact in same ruleset, this should not be printed"
            not in result.stdout
        ), "retract_fact action failed"

    multiple_actions_expected_output = (
        "{'action': 'multiple_actions'}\n"
        "Ruleset: Test actions sanity rule: Test multiple actions in "
        "sequential order has initiated shutdown of type: graceful. "
        "Delay: 0.000 seconds, Message: Sequential action #2: shutdown\n"
        "Sequential action #3: debug"
    )

    with check:
        assert (
            multiple_actions_expected_output in result.stdout
        ), "multiple sequential actions failed"

    assert (
        len(result.stdout.splitlines()) == 48
    ), "unexpected output from the rulebook"


@pytest.mark.e2e
def test_run_playbook(update_environment):
    """
    Execute a rulebook that contains multiple run_playbook actions
    to validate all params that are available with the action.
    """

    rulebook = utils.BASE_DATA_PATH / "rulebooks/actions/test_run_playbook.yml"
    env = update_environment(
        {"DEFAULT_SHUTDOWN_AFTER": str(DEFAULT_SHUTDOWN_AFTER)}
    )

    cmd = utils.Command(rulebook=rulebook, envvars="DEFAULT_SHUTDOWN_AFTER")

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

    retry_attempts = result.stdout.count(
        '"msg": "Remediation failed on simba"'
    )

    with check:
        assert (
            "Post-processing complete on nala" in result.stdout
        ), "run_playbook set_facts to secondary ruleset failed"

    with check:
        assert (
            retry_attempts == 1
        ), "run_playbook retry attempt failed or did not match"

    with check:
        assert (
            "Remediation successful" in result.stdout
        ), "run_playbook post_events failed"

    with check:
        assert (
            "verbosity: 4" in result.stdout
        ), "run_playbook verbosity setting failed"

    with check:
        assert (
            "Post-processing complete on simba" in result.stdout
        ), "run_playbook set_facts to same ruleset failed"


@pytest.mark.e2e
def test_shutdown_action_graceful(update_environment):
    """
    Execute a rulebook to validate the shutdown action with kind graceful
    """

    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/actions/test_shutdown_graceful.yml"
    )
    env = update_environment({"DEFAULT_EVENT_DELAY": str(DEFAULT_EVENT_DELAY)})

    cmd = utils.Command(rulebook=rulebook, envvars="DEFAULT_EVENT_DELAY")

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
                    if '"msg": "Sleeping..."' in line
                ]
            )
            == 1
        ), "long-running playbook failed to fire"

    with check:
        assert (
            "Sequential action triggered successfully" in result.stdout
        ), "a sequential action failed to fire"

    with check:
        assert (
            "Shutdown gracefully has initiated shutdown "
            "of type: graceful." in result.stdout
        ), "graceful shutdown failed to initiate"

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

    with check:
        assert (
            "This condition should not fire" not in result.stdout
        ), "a post-shutdown condition fired when it should not have"


@pytest.mark.e2e
def test_shutdown_action_now(update_environment):
    """
    Execute a rulebook to validate the shutdown action with kind now
    """

    rulebook = utils.BASE_DATA_PATH / "rulebooks/actions/test_shutdown_now.yml"
    env = update_environment(
        {"DEFAULT_STARTUP_DELAY": str(DEFAULT_STARTUP_DELAY)}
    )

    cmd = utils.Command(rulebook=rulebook, envvars="DEFAULT_STARTUP_DELAY")

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
            "Sequential action triggered successfully" in result.stdout
        ), "a sequential action failed to fire"

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
            "Shutdown has initiated shutdown of type: now" in result.stdout
        ), "shutdown now failed to initiate"

    with check:
        assert (
            '"msg": "Rise and shine..."' not in result.stdout
        ), "long-running playbook should not have finished executing"

    with check:
        assert (
            "This condition should not fire" not in result.stdout
        ), "a post-shutdown condition fired when it should not have"
