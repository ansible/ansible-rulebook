import os

from ansible_events.condition_parser import parse_condition
from ansible_events.json_generator import generate_condition

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
        "GreaterThanExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"Integer": 1}}
    } == generate_condition(parse_condition("fact.range.i > 1"), {})
    assert {
        "LessThanExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"Integer": 1}}
    } == generate_condition(parse_condition("fact.range.i < 1"), {})
    assert {
        "LessThanOrEqualToExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"Integer": 1}}
    } == generate_condition(parse_condition("fact.range.i <= 1"), {})
    assert {
        "GreaterThanOrEqualToExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"Integer": 1}}
    } == generate_condition(parse_condition("fact.range.i >= 1"), {})
    assert {
        "EqualsExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"String": "Hello"}}
    } == generate_condition(parse_condition("fact.range.i == 'Hello'"), {})
    assert {
        "AssignmentExpression": { "lhs": {"Events": "first"}, "rhs": {"EqualsExpression": {"lhs": {"Fact": "range.i"}, "rhs": {"String": "Hello"}}}}
    } == generate_condition(parse_condition("events.first << fact.range.i == 'Hello'"), {})
    assert {
        "IsDefinedExpression": {"Fact": "range.i"}
    } == generate_condition(parse_condition("fact.range.i is defined"), {})
    assert {
        "IsNotDefinedExpression": {"Fact": "range.i"}
    } == generate_condition(parse_condition("fact.range.i is not defined"), {})
