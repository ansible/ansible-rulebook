from durable.lang import ruleset, rule, m, c
import asyncio
import multiprocessing as mp
from ansible_events.condition_types import (
    Identifier,
    String,
    OperatorExpression,
    Integer,
    Condition,
    ConditionTypes,
    ExistsExpression,
)

from ansible_events.rule_types import RuleSetQueuePlan, ActionContext
from ansible_events.rule_types import Condition as RuleCondition
from ansible_events.inventory import matching_hosts
from ansible_events.util import substitute_variables


from typing import Dict, List, Callable


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
    plan.put_nowait(ActionContext(ruleset, action, action_args, variables, inventory, hosts, facts, c))


def visit_condition(parsed_condition: ConditionTypes, variables: Dict):
    if isinstance(parsed_condition, list):
        return [visit_condition(c, variables) for c in parsed_condition]
    elif isinstance(parsed_condition, Condition):
        return visit_condition(parsed_condition.value, variables)
    elif isinstance(parsed_condition, Identifier):
        if parsed_condition.value.startswith('fact.'):
            return m.__getattr__(parsed_condition.value[5:])
        elif parsed_condition.value.startswith('event.'):
            return m.__getattr__(parsed_condition.value[6:])
        elif parsed_condition.value.startswith('events.'):
            return c.__getattr__(parsed_condition.value[7:])
        elif parsed_condition.value.startswith('facts.'):
            return c.__getattr__(parsed_condition.value[6:])
        else:
            raise Exception(f'Unhandled identifier {parsed_condition.value}')
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
        elif parsed_condition.operator == "is":
            if isinstance(parsed_condition.right, Identifier):
                if parsed_condition.right.value == 'defined':
                    return visit_condition(parsed_condition.left, variables).__pos__()
        elif parsed_condition.operator == "<<":
            return visit_condition(parsed_condition.left, variables).__lshift__(
                visit_condition(parsed_condition.right, variables)
            )
        else:
            raise Exception(f"Unhandled token {parsed_condition}")
    elif isinstance(parsed_condition, ExistsExpression):
        return visit_condition(parsed_condition.value, variables).__pos__()
    else:
        raise Exception(f"Unhandled token {parsed_condition}")


def generate_condition(ansible_condition: RuleCondition, variables: Dict):
    condition =  visit_condition(ansible_condition.value, variables)
    logger = mp.get_logger()
    for i in condition:
        logger.debug(f"{i.define()}")
    return condition


def make_fn(
    ruleset, ansible_rule, variables: Dict, inventory: Dict, hosts: List, facts: Dict, plan: asyncio.Queue
) -> Callable:
    def fn(c):
        logger = mp.get_logger()
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


def generate_host_rulesets(
    ansible_ruleset_queue_plans: List[RuleSetQueuePlan], variables: Dict, inventory: Dict
):

    logger = mp.get_logger()
    rulesets = []

    for ansible_ruleset, queue, plan in ansible_ruleset_queue_plans:
        host_rulesets = []
        a_ruleset = ruleset(ansible_ruleset.name)
        with a_ruleset:
            for ansible_rule in ansible_ruleset.rules:
                if ansible_rule.enabled:
                    fn = make_fn(a_ruleset.name, ansible_rule, variables, inventory, [], {}, plan)
                    r = rule(ansible_rule.condition.when, True, *generate_condition(ansible_rule.condition, variables))(fn)
                    logger.info(r.define())
        for host in matching_hosts(inventory, ansible_ruleset.hosts):
            host_ruleset = ruleset(f'{ansible_ruleset.name}_{host}')
            with host_ruleset:
                for ansible_rule in ansible_ruleset.host_rules:
                    if ansible_rule.enabled:
                        fn = make_fn(host_ruleset.name, ansible_rule, variables, inventory, [host], {}, plan)
                        r = rule(ansible_rule.condition.when, True, *generate_condition(ansible_rule.condition, variables))(fn)
                        logger.info(r.define())
            host_rulesets.append(host_ruleset)
        rulesets.append((a_ruleset, host_rulesets, queue, plan))

    return rulesets
