import os
from contextlib import nullcontext as does_not_raise
from unittest import mock

import pytest

from ansible_rulebook.app import (
    load_rulebook,
    load_vars,
    run,
    spawn_sources,
    validate_actions,
)
from ansible_rulebook.cli import get_parser
from ansible_rulebook.exception import (
    InventoryNeededException,
    RulebookNotFoundException,
)

HERE = os.path.dirname(os.path.abspath(__file__))
TEST_ACTIONS = [
    ("debug", does_not_raise()),
    ("print_event", does_not_raise()),
    ("set_fact", does_not_raise()),
    ("post_event", does_not_raise()),
    ("run_playbook", pytest.raises(InventoryNeededException)),
    ("run_module", pytest.raises(InventoryNeededException)),
]


@pytest.mark.parametrize("action,expectation", TEST_ACTIONS)
def test_validate_action(
    create_ruleset, create_action, create_rule, action, expectation
):
    actions = [create_action(**dict(action=action))]
    rules = [create_rule(**dict(actions=actions))]
    rulesets = [create_ruleset(**dict(rules=rules))]
    parser = get_parser()
    cmdline_args = parser.parse_args(["-r", "dummy.yml"])
    with expectation:
        validate_actions(rulesets, cmdline_args)


def test_load_vars():
    os.chdir(HERE)
    parser = get_parser()
    cmdline_args = parser.parse_args(
        ["-e", "./data/test_vars.yml", "-E", "TEST_ABC,TEST_XYZ"]
    )
    try:
        os.environ["TEST_ABC"] = "Barney"
        os.environ["TEST_XYZ"] = "42"
        result = load_vars(cmdline_args)
        assert (result["person"]["name"]) == "Fred"
        assert (result["person"]["age"]) == 42
        assert result["person"]["employed"]
        assert (result["TEST_ABC"]) == "Barney"
        assert (result["TEST_XYZ"]) == "42"
    finally:
        del os.environ["TEST_ABC"]
        del os.environ["TEST_XYZ"]


def test_load_vars_missing_key():
    parser = get_parser()
    cmdline_args = parser.parse_args(["-E", "TEST_ABC,TEST_XYZ"])
    with pytest.raises(KeyError):
        load_vars(cmdline_args)


def test_load_rulebook():
    os.chdir(HERE)
    parser = get_parser()
    cmdline_args = parser.parse_args(["-r", "./data/rulebook.yml"])
    ruleset = load_rulebook(cmdline_args)[0]
    assert ruleset.name == "Sample Rulebook"
    assert ruleset.rules[0].name == "r1"
    assert ruleset.rules[0].actions[0].action == "debug"


def test_load_rulebook_via_collection():
    parser = get_parser()
    cmdline_args = parser.parse_args(
        ["-r", "ansible.eda.hello_events", "-i", "inventory.yml"]
    )
    ruleset = load_rulebook(cmdline_args)[0]
    assert ruleset.name == "Hello Events"
    assert ruleset.rules[0].name == "Say Hello"
    assert ruleset.rules[0].actions[0].action == "run_playbook"


def test_load_rulebook_empty():
    parser = get_parser()
    cmdline_args = parser.parse_args(["-E", "TEST"])
    assert (len(load_rulebook(cmdline_args))) == 0


def test_load_rulebook_missing():
    parser = get_parser()
    cmdline_args = parser.parse_args(["-r", "missing.yml"])
    with pytest.raises(RulebookNotFoundException):
        load_rulebook(cmdline_args)


@pytest.mark.asyncio
async def test_spawn_sources(create_ruleset):
    with mock.patch("ansible_rulebook.app.start_source") as mock_start_source:
        tasks, ruleset_queues = spawn_sources(
            [create_ruleset()], dict(), ["."], 0.0
        )
        for task in tasks:
            task.cancel()
        assert mock_start_source.call_count == 1


@pytest.mark.asyncio
async def test_run(create_ruleset):
    os.chdir(HERE)
    parser = get_parser()
    cmdline_args = parser.parse_args(
        ["-r", "./data/rulebook.yml", "-i", "./playbooks/inventory.yml"]
    )

    with mock.patch("ansible_rulebook.app.start_source") as mock_start_source:
        with mock.patch(
            "ansible_rulebook.app.run_rulesets"
        ) as mock_run_rulesets:
            await run(cmdline_args)
            assert mock_start_source.call_count == 1
            assert mock_run_rulesets.call_count == 1


@pytest.mark.asyncio
async def test_run_with_websocket(create_ruleset):
    os.chdir(HERE)
    rulesets = [create_ruleset()]
    parser = get_parser()
    cmdline_args = parser.parse_args(
        ["-r", "./data/rulebook.yml", "-W", "fake", "--id", "1", "-w"]
    )

    with mock.patch("ansible_rulebook.app.start_source") as mock_start_source:
        with mock.patch(
            "ansible_rulebook.app.run_rulesets"
        ) as mock_run_rulesets:
            with mock.patch(
                "ansible_rulebook.app.request_workload"
            ) as mock_request_workload:
                mock_request_workload.return_value = ("a", "b", rulesets, "d")

                await run(cmdline_args)

                assert mock_start_source.call_count == 1
                assert mock_run_rulesets.call_count == 1
                assert mock_request_workload.call_count == 1
