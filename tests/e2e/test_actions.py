"""
Module with tests for operators
"""
import logging
import subprocess

import pytest

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


@pytest.mark.e2e
def test_actions_sanity():
    """
    A rulebook that contains multiple rules with the following list of actions:
        * run_playbook
        * run_module
        * print_event
        * debug
        * post_event
        * set_fact
        * retract_fact
        * echo
    Each rule has specific logic to be executed only one time
    and each action produces a specific output to be verified.
    """
    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/actions/test_actions_sanity.yml"
    )
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )

    assert result.returncode == 0
    assert not result.stderr

    # assert each expected output per action tested
    assert (
        "Event matched: {'action': 'run_playbook'}" in result.stdout
    ), "run_playbook action failed"

    assert (
        "Event matched: {'action': 'run_module'}" in result.stdout
    ), "run_module action failed"

    assert (
        "{'action': 'print_event'}" in result.stdout
    ), "print_event action failed"

    event_debug_expected_output = """{'facts': {},
 'hosts': ['all'],
 'inventory': {'all': {'hosts': {'localhost': {'ansible_connection': 'local'}}}},
 'project_data_file': None,
 'ruleset': 'Test actions sanity',
 'source_rule_name': 'debug',
 'source_ruleset_name': 'Test actions sanity',
 'variables': {'ansible_eda': {'event': {'action': 'debug'},
                               'fact': {'action': 'debug'}}}}"""  # noqa: E501

    assert event_debug_expected_output in result.stdout, "debug action failed"

    assert (
        "Event matched in same ruleset: sent" in result.stdout
    ), "post_event action failed"

    assert (
        "Event matched in different ruleset: sent" in result.stdout
    ), "post_event action across rulesets failed"

    assert (
        "Fact matched in same ruleset: sent" in result.stdout
    ), "set_fact action failed"

    assert (
        "Fact matched in different ruleset: sent" in result.stdout
    ), "set_fact action across rulesets failed"

    assert (
        "Retracted fact in same ruleset, this should not be printed"
        not in result.stdout
    ), "retract_fact action failed"

    assert "Echo action executed" in result.stdout

    assert (
        len(result.stdout.splitlines()) == 45
    ), "unexpected output from the rulebook"
