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

"""Generate condition AST from Ansible condition."""
from typing import Dict, List

import dpath

from ansible_rulebook.condition_types import (
    Boolean,
    Condition,
    ConditionTypes,
    Float,
    Identifier,
    Integer,
    KeywordValue,
    NegateExpression,
    Null,
    OperatorExpression,
    SearchType,
    SelectattrType,
    SelectType,
    String,
    to_condition_type,
)
from ansible_rulebook.exception import (
    InvalidAssignmentException,
    InvalidIdentifierException,
    VarsKeyMissingException,
)
from ansible_rulebook.rule_types import (
    Action,
    Condition as RuleCondition,
    EventSource,
    EventSourceFilter,
    Rule,
    RuleSet,
    Throttle,
)
from ansible_rulebook.util import substitute_variables

OPERATOR_MNEMONIC = {
    "!=": "NotEqualsExpression",
    "==": "EqualsExpression",
    "and": "AndExpression",
    "or": "OrExpression",
    ">": "GreaterThanExpression",
    "<": "LessThanExpression",
    ">=": "GreaterThanOrEqualToExpression",
    "<=": "LessThanOrEqualToExpression",
    "+": "AdditionExpression",
    "-": "SubtractionExpression",
    "<<": "AssignmentExpression",
    "in": "ItemInListExpression",
    "not in": "ItemNotInListExpression",
    "contains": "ListContainsItemExpression",
    "not contains": "ListNotContainsItemExpression",
}


def visit_condition(parsed_condition: ConditionTypes, variables: Dict):
    """Visit the condition and generate the AST."""
    if isinstance(parsed_condition, list):
        return [visit_condition(c, variables) for c in parsed_condition]
    elif isinstance(parsed_condition, Condition):
        return visit_condition(parsed_condition.value, variables)
    elif isinstance(parsed_condition, Boolean):
        return (
            {"Boolean": True}
            if parsed_condition.value == "true"
            else {"Boolean": False}
        )
    elif isinstance(parsed_condition, Identifier):
        if parsed_condition.value.startswith("fact."):
            return {"Fact": parsed_condition.value[5:]}
        elif parsed_condition.value.startswith("fact["):
            return {"Fact": parsed_condition.value[4:]}
        elif parsed_condition.value.startswith("event."):
            return {"Event": parsed_condition.value[6:]}
        elif parsed_condition.value.startswith("event["):
            return {"Event": parsed_condition.value[5:]}
        elif parsed_condition.value.startswith("events."):
            return {"Events": parsed_condition.value[7:]}
        elif parsed_condition.value.startswith("facts."):
            return {"Facts": parsed_condition.value[6:]}
        elif parsed_condition.value.startswith("vars."):
            key = parsed_condition.value[5:]
            return process_vars(variables, key)
        else:
            msg = (
                f"Invalid identifier : {parsed_condition.value} "
                + "Should start with event., events.,fact., facts. or vars."
            )
            raise InvalidIdentifierException(msg)

    elif isinstance(parsed_condition, String):
        return {
            "String": substitute_variables(parsed_condition.value, variables)
        }
    elif isinstance(parsed_condition, Null):
        return {"NullType": None}
    elif isinstance(parsed_condition, Integer):
        return {"Integer": parsed_condition.value}
    elif isinstance(parsed_condition, Float):
        return {"Float": parsed_condition.value}
    elif isinstance(parsed_condition, SearchType):
        data = dict(
            kind=visit_condition(parsed_condition.kind, variables),
            pattern=visit_condition(parsed_condition.pattern, variables),
        )
        if parsed_condition.options:
            data["options"] = [
                visit_condition(v, variables) for v in parsed_condition.options
            ]
        return {"SearchType": data}
    elif isinstance(parsed_condition, SelectattrType):
        return dict(
            key=visit_condition(parsed_condition.key, variables),
            operator=visit_condition(parsed_condition.operator, variables),
            value=visit_condition(parsed_condition.value, variables),
        )
    elif isinstance(parsed_condition, SelectType):
        return dict(
            operator=visit_condition(parsed_condition.operator, variables),
            value=visit_condition(parsed_condition.value, variables),
        )
    elif isinstance(parsed_condition, KeywordValue):
        return dict(
            name=visit_condition(parsed_condition.name, variables),
            value=visit_condition(parsed_condition.value, variables),
        )
    elif isinstance(parsed_condition, OperatorExpression):
        if parsed_condition.operator == "<<":
            validate_assignment_expression(parsed_condition.left.value)

        if parsed_condition.operator in OPERATOR_MNEMONIC:
            return create_binary_node(
                OPERATOR_MNEMONIC[parsed_condition.operator],
                parsed_condition,
                variables,
            )
        elif parsed_condition.operator == "is":
            if isinstance(parsed_condition.right, String):
                if parsed_condition.right.value == "defined":
                    return {
                        "IsDefinedExpression": visit_condition(
                            parsed_condition.left, variables
                        )
                    }
            elif isinstance(parsed_condition.right, SearchType):
                return create_binary_node(
                    "SearchMatchesExpression", parsed_condition, variables
                )
            elif isinstance(parsed_condition.right, SelectattrType):
                return create_binary_node(
                    "SelectAttrExpression", parsed_condition, variables
                )
            elif isinstance(parsed_condition.right, SelectType):
                return create_binary_node(
                    "SelectExpression", parsed_condition, variables
                )
        elif parsed_condition.operator == "is not":
            if isinstance(parsed_condition.right, String):
                if parsed_condition.right.value == "defined":
                    return {
                        "IsNotDefinedExpression": visit_condition(
                            parsed_condition.left, variables
                        )
                    }
            elif isinstance(parsed_condition.right, SearchType):
                return create_binary_node(
                    "SearchNotMatchesExpression", parsed_condition, variables
                )
            elif isinstance(parsed_condition.right, SelectattrType):
                return create_binary_node(
                    "SelectAttrNotExpression", parsed_condition, variables
                )
            elif isinstance(parsed_condition.right, SelectType):
                return create_binary_node(
                    "SelectNotExpression", parsed_condition, variables
                )
        else:
            raise Exception(f"Unhandled token {parsed_condition}")
    elif isinstance(parsed_condition, NegateExpression):
        return {
            "NegateExpression": visit_condition(
                parsed_condition.value, variables
            )
        }
    else:
        raise Exception(f"Unhandled token {parsed_condition}")


def create_binary_node(name, parsed_condition, variables):
    return {
        name: {
            "lhs": visit_condition(parsed_condition.left, variables),
            "rhs": visit_condition(parsed_condition.right, variables),
        }
    }


def visit_rule(parsed_rule: Rule, variables: Dict):
    data = {
        "name": parsed_rule.name,
        "condition": generate_condition(parsed_rule.condition, variables),
        "actions": visit_actions(parsed_rule.actions, variables),
        "enabled": parsed_rule.enabled,
    }

    if parsed_rule.throttle:
        data.update(visit_throttle(parsed_rule.throttle, variables))

    return {"Rule": data}


def visit_actions(actions: List[Action], variables: Dict):
    return [visit_action(a, variables) for a in actions]


def visit_action(parsed_action: Action, variables: Dict):
    return {
        "Action": {
            "action": parsed_action.action,
            "action_args": parsed_action.action_args,
        }
    }


def visit_throttle(parsed_throttle: Throttle, variables: Dict):
    throttle = {"group_by_attributes": parsed_throttle.group_by_attributes}
    if parsed_throttle.once_within:
        throttle["once_within"] = parsed_throttle.once_within
    elif parsed_throttle.once_after:
        throttle["once_after"] = parsed_throttle.once_after

    return {"throttle": throttle}


def visit_source(parsed_source: EventSource, variables: Dict):
    return {
        "EventSource": {
            "name": parsed_source.name,
            "source_name": parsed_source.source_name,
            "source_args": parsed_source.source_args,
            "source_filters": [
                visit_source_filter(f, variables)
                for f in parsed_source.source_filters
            ],
        }
    }


def visit_source_filter(parsed_source: EventSourceFilter, variables: Dict):
    return {
        "EventSourceFilter": {
            "filter_name": parsed_source.filter_name,
            "filter_args": parsed_source.filter_args,
        }
    }


def generate_condition(ansible_condition: RuleCondition, variables: Dict):
    """Generate the condition AST."""
    condition = visit_condition(ansible_condition.value, variables)
    if ansible_condition.when == "any":
        data = {"AnyCondition": condition}
    elif ansible_condition.when == "all":
        data = {"AllCondition": condition}
    elif ansible_condition.when == "not_all":
        data = {"NotAllCondition": condition}
    else:
        data = {"AllCondition": condition}

    if ansible_condition.timeout:
        data["timeout"] = ansible_condition.timeout

    return data


def visit_ruleset(ruleset: RuleSet, variables: Dict):
    """Generate JSON compatible rules."""
    data = {
        "name": ruleset.name,
        "hosts": ruleset.hosts,
        "sources": [
            visit_source(source, variables) for source in ruleset.sources
        ],
        "rules": [visit_rule(rule, variables) for rule in ruleset.rules],
    }

    if ruleset.default_events_ttl:
        data["default_events_ttl"] = ruleset.default_events_ttl

    if ruleset.match_multiple_rules:
        data["match_multiple_rules"] = ruleset.match_multiple_rules

    return {"RuleSet": data}


def generate_dict_rulesets(ruleset: List[RuleSet], variables: Dict):
    """Generate JSON compatible rulesets."""
    return [visit_ruleset(ruleset, variables) for ruleset in ruleset]


def validate_assignment_expression(value):
    tokens = value.split(".")
    if len(tokens) != 2:
        msg = (
            f"Assignment variable: {value} is invalid."
            + "Valid values start with events or facts. e.g events.var1 "
            + "or facts.var1 "
            + "Where var1 can only contain alpha numeric and _ charachters"
        )
        raise InvalidAssignmentException(msg)

    if tokens[0] not in ["events", "facts"]:
        msg = (
            "Only events and facts can be used in assignment. "
            + f"{value} is invalid."
        )
        raise InvalidAssignmentException(msg)


def process_vars(variables, key):
    try:
        return visit_condition(
            to_condition_type(dpath.get(variables, key, separator=".")),
            variables,
        )
    except KeyError:
        raise VarsKeyMissingException(f"vars does not contain key: {key}")
