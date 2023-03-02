from contextlib import nullcontext as does_not_raise

import pytest

from ansible_rulebook.app import validate_actions
from ansible_rulebook.cli import get_parser
from ansible_rulebook.exception import InventoryNeededException

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
