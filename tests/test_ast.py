import os

import yaml

from ansible_events.condition_parser import parse_condition
from ansible_events.json_generator import (
    generate_condition,
    generate_dict_rulesets,
)
from ansible_events.rules_parser import parse_rule_sets

HERE = os.path.dirname(os.path.abspath(__file__))


def test_parse_condition():
    assert {"Fact": "range.i"} == generate_condition(
        parse_condition("fact.range.i"), {}
    )
    assert {"Boolean": True} == generate_condition(parse_condition("True"), {})
    assert {"Boolean": False} == generate_condition(
        parse_condition("False"), {}
    )
    assert {"Integer": 42} == generate_condition(parse_condition("42"), {})
    assert {"String": "Hello"} == generate_condition(
        parse_condition("'Hello'"), {}
    )
    assert {
        "EqualsExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"Integer": 1}}
    } == generate_condition(parse_condition("fact.range.i == 1"), {})
    assert {
        "GreaterThanExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == generate_condition(parse_condition("fact.range.i > 1"), {})
    assert {
        "LessThanExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == generate_condition(parse_condition("fact.range.i < 1"), {})
    assert {
        "LessThanOrEqualToExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == generate_condition(parse_condition("fact.range.i <= 1"), {})
    assert {
        "GreaterThanOrEqualToExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"Integer": 1},
        }
    } == generate_condition(parse_condition("fact.range.i >= 1"), {})
    assert {
        "EqualsExpression": {
            "lhs": {"Fact": "range.i"},
            "rhs": {"String": "Hello"},
        }
    } == generate_condition(parse_condition("fact.range.i == 'Hello'"), {})
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
    } == generate_condition(
        parse_condition("events.first << fact.range.i == 'Hello'"), {}
    )
    assert {"IsDefinedExpression": {"Fact": "range.i"}} == generate_condition(
        parse_condition("fact.range.i is defined"), {}
    )
    assert {
        "IsNotDefinedExpression": {"Fact": "range.i"}
    } == generate_condition(parse_condition("fact.range.i is not defined"), {})

    assert {
        "IsNotDefinedExpression": {"Fact": "range.i"}
    } == generate_condition(
        parse_condition("(fact.range.i is not defined)"), {}
    )

    assert {
        "IsNotDefinedExpression": {"Fact": "range.i"}
    } == generate_condition(
        parse_condition("(((fact.range.i is not defined)))"), {}
    )
    assert {
        "OrExpression": {
            "lhs": {"IsNotDefinedExpression": {"Fact": "range.i"}},
            "rhs": {"IsDefinedExpression": {"Fact": "range.i"}},
        }
    } == generate_condition(
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
    } == generate_condition(
        parse_condition(
            "(fact.range.i is not defined) and (fact.range.i is defined)"
        ),
        {},
    )
    print(
        generate_condition(
            parse_condition(
                "(fact.range.i is not defined) and (fact.range.i is defined) and (fact.range.i == 1)"
            ),
            {},
        )
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
    } == generate_condition(
        parse_condition(
            "(fact.range.i is not defined) and (fact.range.i is defined) and (fact.range.i == 1)"
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
    } == generate_condition(
        parse_condition(
            "(fact.range.i is not defined) and (fact.range.i is defined) or (fact.range.i == 1)"
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
    } == generate_condition(
        parse_condition(
            "(fact.range.i is not defined) and ((fact.range.i is defined) or (fact.range.i == 1))"
        ),
        {},
    )


def test_generate_dict_ruleset():

    os.chdir(HERE)
    with open("rules/rules.yml") as f:
        data = yaml.safe_load(f.read())

    print(parse_rule_sets(data))
    ruleset = generate_dict_rulesets(parse_rule_sets(data), {})
    assert ruleset == [
        {
            "RuleSet": {
                "hosts": ["localhost"],
                "name": "Demo rules",
                "rules": [
                    {
                        "Rule": {
                            "action": {
                                "Action": {
                                    "action": "slack",
                                    "action_args": {
                                        "color": "good",
                                        "msg": "Deployment "
                                        "success "
                                        "at "
                                        "{{event.payload.eventTime}}: "
                                        "{{management_url}}"
                                        "{{event.payload.applicationId}}",
                                        "token": "{{token}}",
                                    },
                                }
                            },
                            "condition": [
                                {
                                    "EqualsExpression": {
                                        "lhs": {
                                            "Event": "payload.provisioningState"
                                        },
                                        "rhs": {"String": "Succeeded"},
                                    }
                                }
                            ],
                            "enabled": True,
                            "name": "send to slack3",
                        }
                    },
                    {
                        "Rule": {
                            "action": {
                                "Action": {
                                    "action": "slack",
                                    "action_args": {
                                        "color": "warning",
                                        "msg": "Deployment "
                                        "deleted "
                                        "at "
                                        "{{event.payload.eventTime}}: "
                                        "{{management_url}}"
                                        "{{event.payload.applicationId}}",
                                        "token": "{{token}}",
                                    },
                                }
                            },
                            "condition": [
                                {
                                    "EqualsExpression": {
                                        "lhs": {
                                            "Event": "payload.provisioningState"
                                        },
                                        "rhs": {"String": "Deleted"},
                                    }
                                }
                            ],
                            "enabled": True,
                            "name": "send to slack4",
                        }
                    },
                    {
                        "Rule": {
                            "action": {
                                "Action": {
                                    "action": "slack",
                                    "action_args": {
                                        "msg": "{{event}}",
                                        "token": "{{token}}",
                                    },
                                }
                            },
                            "condition": [
                                {
                                    "NotEqualsExpression": {
                                        "lhs": {"Event": "payload.eventType"},
                                        "rhs": {"String": "GET"},
                                    }
                                }
                            ],
                            "enabled": True,
                            "name": "send to slack5",
                        }
                    },
                    {
                        "Rule": {
                            "action": {
                                "Action": {
                                    "action": "slack",
                                    "action_args": {
                                        "msg": "{{event}}",
                                        "token": "{{token}}",
                                    },
                                }
                            },
                            "condition": [
                                {
                                    "NotEqualsExpression": {
                                        "lhs": {"Event": "payload.text"},
                                        "rhs": {"String": ""},
                                    }
                                }
                            ],
                            "enabled": True,
                            "name": "send to slack6",
                        }
                    },
                    {
                        "Rule": {
                            "action": {
                                "Action": {
                                    "action": "assert_fact",
                                    "action_args": {
                                        "fact": {"received_greeting": True},
                                        "ruleset": "Demo " "rules",
                                    },
                                }
                            },
                            "condition": [
                                {
                                    "NotEqualsExpression": {
                                        "lhs": {"Event": "payload.text"},
                                        "rhs": {"String": ""},
                                    }
                                }
                            ],
                            "enabled": True,
                            "name": "assert fact",
                        }
                    },
                    {
                        "Rule": {
                            "action": {
                                "Action": {"action": "log", "action_args": {}}
                            },
                            "condition": [
                                {
                                    "NotEqualsExpression": {
                                        "lhs": {"Event": "payload.text"},
                                        "rhs": {"String": ""},
                                    }
                                }
                            ],
                            "enabled": True,
                            "name": "log event",
                        }
                    },
                ],
                "sources": [
                    {
                        "EventSource": {
                            "name": "azure_service_bus",
                            "source_args": {
                                "conn_str": "{{connection_str}}",
                                "queue_name": "{{queue_name}}",
                            },
                            "source_filters": [],
                        }
                    },
                    {
                        "EventSource": {
                            "name": "local_events",
                            "source_args": {},
                            "source_filters": [],
                        }
                    },
                ],
            }
        }
    ]
