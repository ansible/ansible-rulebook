import asyncio
import os
from queue import Queue

import pytest
import yaml

from ansible_events.condition_parser import parse_condition
from ansible_events.json_generator import generate_condition
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
