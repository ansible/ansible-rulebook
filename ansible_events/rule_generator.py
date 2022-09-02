import asyncio
import logging
import os
from typing import Callable, Dict, List

if os.environ.get("RULES_ENGINE", "durable_rules") == "drools":
    from drools.vendor.lang import c, m, none, rule, ruleset
else:
    from durable.lang import c, m, none, rule, ruleset

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
from ansible_events.rule_types import (
    ActionContext,
    Condition as RuleCondition,
    RuleSetQueuePlan,
)
from ansible_events.util import substitute_variables


def add_to_plan(
    ruleset: str,
    action: str,
    action_args: Dict,
    variables: Dict,
    inventory: Dict,
    hosts: List,
    facts: Dict,
    plan: asyncio.Queue,
    c,
) -> None:
    plan.put_nowait(
        ActionContext(
            ruleset, action, action_args, variables, inventory, hosts, facts, c
        )
    )


def dotted_getattr(o, value):
    parts = value.split(".")
    current = o
    for part in parts:
        current = current.__getattr__(part)
    return current


def visit_condition(parsed_condition: ConditionTypes, variables: Dict):
    if isinstance(parsed_condition, list):
        return [visit_condition(c, variables) for c in parsed_condition]
    elif isinstance(parsed_condition, Condition):
        return visit_condition(parsed_condition.value, variables)
    elif isinstance(parsed_condition, Boolean):
        return True if parsed_condition.value == "true" else False
    elif isinstance(parsed_condition, Identifier):
        if parsed_condition.value.startswith("fact."):
            return dotted_getattr(m, parsed_condition.value[5:])
        elif parsed_condition.value.startswith("event."):
            return dotted_getattr(m, parsed_condition.value[6:])
        elif parsed_condition.value.startswith("events."):
            return dotted_getattr(c, parsed_condition.value[7:])
        elif parsed_condition.value.startswith("facts."):
            return dotted_getattr(c, parsed_condition.value[6:])
        else:
            raise Exception(f"Unhandled identifier {parsed_condition.value}")
    elif isinstance(parsed_condition, String):
        return substitute_variables(parsed_condition.value, variables)
    elif isinstance(parsed_condition, Integer):
        return parsed_condition.value
    elif isinstance(parsed_condition, OperatorExpression):
        if parsed_condition.operator == "!=":
            return visit_condition(parsed_condition.left, variables).__ne__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "==":
            return visit_condition(parsed_condition.left, variables).__eq__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "and":
            return visit_condition(parsed_condition.left, variables).__and__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "or":
            return visit_condition(parsed_condition.left, variables).__or__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == ">":
            return visit_condition(parsed_condition.left, variables).__gt__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "<":
            return visit_condition(parsed_condition.left, variables).__lt__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == ">=":
            return visit_condition(parsed_condition.left, variables).__ge__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "<=":
            return visit_condition(parsed_condition.left, variables).__le__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "+":
            return visit_condition(parsed_condition.left, variables).__add__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "-":
            return visit_condition(parsed_condition.left, variables).__sub__(
                visit_condition(parsed_condition.right, variables)
            )
        elif parsed_condition.operator == "is":
            if isinstance(parsed_condition.right, Identifier):
                if parsed_condition.right.value == "defined":
                    return visit_condition(
                        parsed_condition.left, variables
                    ).__pos__()
        elif parsed_condition.operator == "is not":
            if isinstance(parsed_condition.right, Identifier):
                if parsed_condition.right.value == "defined":
                    return none(
                        visit_condition(
                            parsed_condition.left, variables
                        ).__pos__()
                    )
        elif parsed_condition.operator == "<<":
            return visit_condition(
                parsed_condition.left, variables
            ).__lshift__(visit_condition(parsed_condition.right, variables))
        else:
            raise Exception(f"Unhandled token {parsed_condition}")
    elif isinstance(parsed_condition, ExistsExpression):
        if parsed_condition.operator == "+":
            raise Exception("Please use is defined instead of +")

        return visit_condition(parsed_condition.value, variables).__pos__()
    else:
        raise Exception(f"Unhandled token {parsed_condition}")


def generate_condition(ansible_condition: RuleCondition, variables: Dict):
    condition = visit_condition(ansible_condition.value, variables)
    logger = logging.getLogger()
    for i in condition:
        if i:
            logger.debug(f"{i.define()}")
        else:
            logger.debug("None")
    return condition


def make_fn(
    ruleset,
    ansible_rule,
    variables: Dict,
    inventory: Dict,
    hosts: List,
    facts: Dict,
    plan: asyncio.Queue,
) -> Callable:
    def fn(c):
        logger = logging.getLogger()
        logger.info(f"calling {ansible_rule.name}")
        add_to_plan(
            ruleset,
            ansible_rule.action.action,
            ansible_rule.action.action_args,
            variables,
            inventory,
            hosts,
            facts,
            plan,
            c,
        )

    return fn


def generate_rulesets(
    ansible_ruleset_queue_plans: List[RuleSetQueuePlan],
    variables: Dict,
    inventory: Dict,
):

    logger = logging.getLogger()
    rulesets = []

    for ansible_ruleset, queue, plan in ansible_ruleset_queue_plans:
        a_ruleset = ruleset(ansible_ruleset.name)
        with a_ruleset:
            for ansible_rule in ansible_ruleset.rules:
                if ansible_rule.enabled:
                    fn = make_fn(
                        a_ruleset.name,
                        ansible_rule,
                        variables,
                        inventory,
                        ansible_ruleset.hosts,
                        {},
                        plan,
                    )
                    r = rule(
                        ansible_rule.condition.when,
                        True,
                        *generate_condition(ansible_rule.condition, variables),
                    )(fn)
                    logger.info(r.define())
        rulesets.append((a_ruleset, [], queue, plan))

    return rulesets
