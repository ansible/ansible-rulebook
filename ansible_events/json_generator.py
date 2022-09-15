"""Generate condition AST from Ansible condition."""
from typing import Dict

from ansible_events.condition_types import (
    Boolean,
    Condition,
    ConditionTypes,
    ExistsExpression,
    Identifier,
    Integer,
    OperatorExpression,
    String,
)
from ansible_events.rule_types import Condition as RuleCondition
from ansible_events.util import substitute_variables


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
        else:
            raise Exception(f"Unhandled identifier {parsed_condition.value}")
    elif isinstance(parsed_condition, String):
        return {
            "String": substitute_variables(parsed_condition.value, variables)
        }
    elif isinstance(parsed_condition, Integer):
        return {"Integer": parsed_condition.value}
    elif isinstance(parsed_condition, OperatorExpression):
        if parsed_condition.operator == "!=":
            return {
                "NotEqualsExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == "==":
            return {
                "EqualsExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == "and":
            return {
                "AndExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == "or":
            return {
                "OrExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == ">":
            return {
                "GreaterThanExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == "<":
            return {
                "LessThanExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == ">=":
            return {
                "GreaterThanOrEqualToExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == "<=":
            return {
                "LessThanOrEqualToExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == "+":
            return {
                "AdditionExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
        elif parsed_condition.operator == "-":
            return {
                "SubtractionExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": visit_condition(parsed_condition.right, variables),
                }
            }
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
        elif parsed_condition.operator == "<<":
            return {
                "AssignmentExpression": {
                    "lhs": visit_condition(parsed_condition.left, variables),
                    "rhs": (
                        visit_condition(parsed_condition.right, variables)
                    ),
                }
            }
        else:
            raise Exception(f"Unhandled token {parsed_condition}")
    elif isinstance(parsed_condition, ExistsExpression):
        if parsed_condition.operator == "+":
            raise Exception("Please use 'is defined' instead of +")

        return visit_condition(parsed_condition.value, variables).__pos__()
    else:
        raise Exception(f"Unhandled token {parsed_condition}")


def generate_condition(ansible_condition: RuleCondition, variables: Dict):
    """Generate the condition AST."""
    condition = visit_condition(ansible_condition.value, variables)
    return condition
