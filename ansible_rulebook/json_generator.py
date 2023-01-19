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
    ExistsExpression,
    Float,
    Identifier,
    Integer,
    NegateExpression,
    OperatorExpression,
    String,
)
from ansible_rulebook.exception import VarsKeyMissingException
from ansible_rulebook.rule_types import (
    Action,
    Condition as RuleCondition,
    EventSource,
    EventSourceFilter,
    Rule,
    RuleSet,
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
        elif parsed_condition.value.startswith("event."):
            return {"Event": parsed_condition.value[6:]}
        elif parsed_condition.value.startswith("events."):
            return {"Events": parsed_condition.value[7:]}
        elif parsed_condition.value.startswith("facts."):
            return {"Facts": parsed_condition.value[6:]}
        elif parsed_condition.value.startswith("vars."):
            key = parsed_condition.value[5:]
            try:
                return visit_condition(
                    convert_to_type(dpath.get(variables, key, separator=".")),
                    variables,
                )
            except KeyError:
                raise VarsKeyMissingException(
                    f"vars does not contain key: {key}"
                )
        else:
            raise Exception(f"Unhandled identifier {parsed_condition.value}")
    elif isinstance(parsed_condition, String):
        return {
            "String": substitute_variables(parsed_condition.value, variables)
        }
    elif isinstance(parsed_condition, Integer):
        return {"Integer": parsed_condition.value}
    elif isinstance(parsed_condition, Float):
        return {"Float": parsed_condition.value}
    elif isinstance(parsed_condition, OperatorExpression):
        if parsed_condition.operator in OPERATOR_MNEMONIC:
            return create_binary_node(
                OPERATOR_MNEMONIC[parsed_condition.operator],
                parsed_condition,
                variables,
            )
        elif parsed_condition.operator == "is":
            if isinstance(parsed_condition.right, Identifier):
                if parsed_condition.right.value == "defined":
                    return {
                        "IsDefinedExpression": visit_condition(
                            parsed_condition.left, variables
                        )
                    }
        elif parsed_condition.operator == "is not":
            if isinstance(parsed_condition.right, Identifier):
                if parsed_condition.right.value == "defined":
                    return {
                        "IsNotDefinedExpression": visit_condition(
                            parsed_condition.left, variables
                        )
                    }
        else:
            raise Exception(f"Unhandled token {parsed_condition}")
    elif isinstance(parsed_condition, ExistsExpression):
        if parsed_condition.operator == "+":
            raise Exception("Please use 'is defined' instead of +")

        return visit_condition(parsed_condition.value, variables).__pos__()
    elif isinstance(parsed_condition, NegateExpression):
        return {
            "NegateExpression": visit_condition(
                parsed_condition.value, variables
            )
        }
    else:
        raise Exception(f"Unhandled token {parsed_condition}")


def convert_to_type(value):
    if isinstance(value, int):
        return Integer(value)
    elif isinstance(value, bool):
        return Boolean(value)
    elif isinstance(value, str):
        return String(value)
    elif isinstance(value, float):
        return Float(value)
    elif isinstance(value, list):
        return [convert_to_type(v) for v in value]
    else:
        raise Exception(f"Invalid type for {value}")


def create_binary_node(name, parsed_condition, variables):
    return {
        name: {
            "lhs": visit_condition(parsed_condition.left, variables),
            "rhs": visit_condition(parsed_condition.right, variables),
        }
    }


def visit_rule(parsed_rule: Rule, variables: Dict):
    return {
        "Rule": {
            "name": parsed_rule.name,
            "condition": generate_condition(parsed_rule.condition, variables),
            "action": visit_action(parsed_rule.action, variables),
            "enabled": parsed_rule.enabled,
        }
    }


def visit_action(parsed_action: Action, variables: Dict):
    return {
        "Action": {
            "action": parsed_action.action,
            "action_args": parsed_action.action_args,
        }
    }


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
    pass


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
        return {"AnyCondition": condition}
    elif ansible_condition.when == "all":
        return {"AllCondition": condition}
    else:
        return {"AllCondition": condition}


def visit_ruleset(ruleset: RuleSet, variables: Dict):
    """Generate JSON compatible rules."""
    return {
        "RuleSet": {
            "name": ruleset.name,
            "hosts": ruleset.hosts,
            "sources": [
                visit_source(source, variables) for source in ruleset.sources
            ],
            "rules": [visit_rule(rule, variables) for rule in ruleset.rules],
        }
    }


def generate_dict_rulesets(ruleset: List[RuleSet], variables: Dict):
    """Generate JSON compatible rulesets."""
    return [visit_ruleset(ruleset, variables) for ruleset in ruleset]
