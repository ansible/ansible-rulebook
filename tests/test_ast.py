#  Copyright 2022 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

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
    assert {"Float": 3.1415} == visit_condition(parse_condition("3.1415"), {})
    assert {"String": "Hello"} == visit_condition(
        parse_condition("'Hello'"), {}
    )
    assert {
        "EqualsExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"Integer": 1}}
    } == visit_condition(parse_condition("fact.range.i == 1"), {})
    assert {
        "EqualsExpression": {
            "lhs": {"Fact": "range.pi"},
            "rhs": {"Float": 3.1415},
        }
    } == visit_condition(parse_condition("fact.range.pi == 3.1415"), {})
    assert {
        "GreaterThanExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.range.i > 1"), {})

    assert {
        "NegateExpression": {
            "Event": "enabled",
        }
    } == visit_condition(parse_condition("not event.enabled"), {})

    assert {
        "NegateExpression": {
            "LessThanExpression": {
                "lhs": {"Fact": "range.i"},
                "rhs": {"Integer": 1},
            }
        }
    } == visit_condition(parse_condition("not (fact.range.i < 1)"), {})

    assert {
        "LessThanExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.range.i < 1"), {})

    assert {
        "NegateExpression": {
            "Event": "enabled",
        }
    } == visit_condition(parse_condition("not event.enabled"), {})

    assert {
        "NegateExpression": {
            "LessThanExpression": {
                "lhs": {"Fact": "range.i"},
                "rhs": {"Integer": 1},
            }
        }
    } == visit_condition(parse_condition("not (fact.range.i < 1)"), {})
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

    assert {
        "ItemInListExpression": {
            "lhs": {"Fact": "i"},
            "rhs": [{"Integer": 1}, {"Integer": 2}, {"Integer": 3}],
        }
    } == visit_condition(parse_condition("fact.i in [1,2,3]"), {})

    assert {
        "ItemInListExpression": {
            "lhs": {"Fact": "name"},
            "rhs": [
                {"String": "fred"},
                {"String": "barney"},
                {"String": "wilma"},
            ],
        }
    } == visit_condition(
        parse_condition("fact.name in ['fred','barney','wilma']"), {}
    )

    assert {
        "ItemNotInListExpression": {
            "lhs": {"Fact": "i"},
            "rhs": [{"Integer": 1}, {"Integer": 2}, {"Integer": 3}],
        }
    } == visit_condition(parse_condition("fact.i not in [1,2,3]"), {})

    assert {
        "ItemNotInListExpression": {
            "lhs": {"Fact": "name"},
            "rhs": [
                {"String": "fred"},
                {"String": "barney"},
                {"String": "wilma"},
            ],
        }
    } == visit_condition(
        parse_condition("fact.name not in ['fred','barney','wilma']"), {}
    )
    assert {
        "ItemNotInListExpression": {
            "lhs": {"Fact": "radius"},
            "rhs": [
                {"Float": 1079.6234},
                {"Float": 3985.8},
                {"Float": 2106.1234},
            ],
        }
    } == visit_condition(
        parse_condition("fact.radius not in [1079.6234,3985.8,2106.1234]"), {}
    )
    assert {
        "ListContainsItemExpression": {
            "lhs": {"Fact": "mylist"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.mylist contains 1"), {})

    assert {
        "ListContainsItemExpression": {
            "lhs": {"Fact": "friends"},
            "rhs": {"String": "fred"},
        }
    } == visit_condition(parse_condition("fact.friends contains 'fred'"), {})

    assert {
        "ListNotContainsItemExpression": {
            "lhs": {"Fact": "mylist"},
            "rhs": {"Integer": 1},
        }
    } == visit_condition(parse_condition("fact.mylist not contains 1"), {})

    assert {
        "ListNotContainsItemExpression": {
            "lhs": {"Fact": "friends"},
            "rhs": {"String": "fred"},
        }
    } == visit_condition(
        parse_condition("fact.friends not contains 'fred'"), {}
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
