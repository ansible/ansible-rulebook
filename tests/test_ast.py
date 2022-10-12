import os

import pytest
import yaml

from ansible_rulebook.condition_parser import parse_condition
from ansible_rulebook.json_generator import (
    generate_dict_rulesets,
    visit_condition,
)
from ansible_rulebook.rules_parser import parse_rule_sets

HERE = os.path.dirname(os.path.abspath(__file__))


def test_parse_condition():
    assert {"Fact": "range.i"} == visit_condition(
        parse_condition("fact.range.i"), {}
    )
    assert {"Boolean": True} == visit_condition(parse_condition("True"), {})
    assert {"Boolean": False} == visit_condition(parse_condition("False"), {})
    assert {"Integer": 42} == visit_condition(parse_condition("42"), {})
    assert {"String": "Hello"} == visit_condition(
        parse_condition("'Hello'"), {}
    )
    assert {
        "EqualsExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"Integer": 1}}
    } == visit_condition(parse_condition("fact.range.i == 1"), {})
    assert {
        "GreaterThanExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.range.i > 1"), {})
    assert {
        "LessThanExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.range.i < 1"), {})
    assert {
        "LessThanOrEqualToExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.range.i <= 1"), {})
    assert {
        "GreaterThanOrEqualToExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.range.i >= 1"), {})
    assert {
        "EqualsExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"String": "Hello"},
        }
    } == visit_condition(parse_condition("fact.range.i == 'Hello'"), {})
    assert {
        "AssignmentExpression": {
            "lhs": {"Events": "first"},
            "rhs": {
                "EqualsExpression": {
                    "lhs": {"Fact": "range.i"},
                    "rhs": {"String": "Hello"},
                }
            },
        }
    } == visit_condition(
        parse_condition("events.first << fact.range.i == 'Hello'"), {}
    )
    assert {"IsDefinedExpression": {"Fact": "range.i"}} == visit_condition(
        parse_condition("fact.range.i is defined"), {}
    )
    assert {"IsNotDefinedExpression": {"Fact": "range.i"}} == visit_condition(
        parse_condition("fact.range.i is not defined"), {}
    )

    assert {"IsNotDefinedExpression": {"Fact": "range.i"}} == visit_condition(
        parse_condition("(fact.range.i is not defined)"), {}
    )

    assert {"IsNotDefinedExpression": {"Fact": "range.i"}} == visit_condition(
        parse_condition("(((fact.range.i is not defined)))"), {}
    )
    assert {
        "OrExpression": {
            "lhs": {"IsNotDefinedExpression": {"Fact": "range.i"}},
            "rhs": {"IsDefinedExpression": {"Fact": "range.i"}},
        }
    } == visit_condition(
        parse_condition(
            "(fact.range.i is not defined) or (fact.range.i is defined)"
        ),
        {},
    )
    assert {
        "AndExpression": {
            "lhs": {"IsNotDefinedExpression": {"Fact": "range.i"}},
            "rhs": {"IsDefinedExpression": {"Fact": "range.i"}},
        }
    } == visit_condition(
        parse_condition(
            "(fact.range.i is not defined) and (fact.range.i is defined)"
        ),
        {},
    )
    assert {
        "AndExpression": {
            "lhs": {
                "AndExpression": {
                    "lhs": {"IsNotDefinedExpression": {"Fact": "range.i"}},
                    "rhs": {"IsDefinedExpression": {"Fact": "range.i"}},
                }
            },
            "rhs": {
                "EqualsExpression": {
                    "lhs": {"Fact": "range.i"},
                    "rhs": {"Integer": 1},
                }
            },
        }
    } == visit_condition(
        parse_condition(
            "(fact.range.i is not defined) and (fact.range.i is defined) "
            "and (fact.range.i == 1)"
        ),
        {},
    )
    assert {
        "OrExpression": {
            "lhs": {
                "AndExpression": {
                    "lhs": {"IsNotDefinedExpression": {"Fact": "range.i"}},
                    "rhs": {"IsDefinedExpression": {"Fact": "range.i"}},
                }
            },
            "rhs": {
                "EqualsExpression": {
                    "lhs": {"Fact": "range.i"},
                    "rhs": {"Integer": 1},
                }
            },
        }
    } == visit_condition(
        parse_condition(
            "(fact.range.i is not defined) and (fact.range.i is defined) "
            "or (fact.range.i == 1)"
        ),
        {},
    )

    assert {
        "AndExpression": {
            "lhs": {"IsNotDefinedExpression": {"Fact": "range.i"}},
            "rhs": {
                "OrExpression": {
                    "lhs": {"IsDefinedExpression": {"Fact": "range.i"}},
                    "rhs": {
                        "EqualsExpression": {
                            "lhs": {"Fact": "range.i"},
                            "rhs": {"Integer": 1},
                        }
                    },
                }
            },
        }
    } == visit_condition(
        parse_condition(
            "(fact.range.i is not defined) and "
            "((fact.range.i is defined) or (fact.range.i == 1))"
        ),
        {},
    )


@pytest.mark.parametrize(
    "rulebook",
    [
        "rules.yml",
        "rules_with_assignment.yml",
        "rules_with_assignment2.yml",
        "rules_with_multiple_conditions.yml",
        "rules_with_multiple_conditions2.yml",
        "rules_with_multiple_conditions3.yml",
        "rules_with_time.yml",
        "rules_with_timestamp.yml",
        "rules_with_vars.yml",
        "rules_without_assignment.yml",
        "test_set_facts.yml",
        "test_filters.yml",
        "test_host_rules.yml",
        "test_rules.yml",
        "test_rules_multiple_hosts.yml",
        "test_rules_multiple_hosts2.yml",
        "test_rules_multiple_hosts3.yml",
        "test_simple.yml",
    ],
)
def test_generate_dict_ruleset(rulebook):

    os.chdir(HERE)
    with open(os.path.join("rules", rulebook)) as f:
        data = yaml.safe_load(f.read())

    ruleset = generate_dict_rulesets(parse_rule_sets(data), {})
    print(yaml.dump(ruleset))

    with open(os.path.join("asts", rulebook)) as f:
        ast = yaml.safe_load(f.read())

    assert ruleset == ast
