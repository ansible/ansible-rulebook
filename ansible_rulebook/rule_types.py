from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, NamedTuple, Union

import ansible_rulebook.condition_types as ct

if os.environ.get("RULES_ENGINE", "drools") == "drools":
    from drools.ruleset import Ruleset as EngineRuleSet
else:
    from durable.lang import ruleset as EngineRuleSet


class EventSourceFilter(NamedTuple):

    filter_name: str
    filter_args: dict


class EventSource(NamedTuple):
    name: str
    source_name: str
    source_args: dict
    source_filters: List[EventSourceFilter]


class Action(NamedTuple):
    action: str
    action_args: dict


class Condition(NamedTuple):
    when: str
    value: List[ct.Condition]


class Rule(NamedTuple):
    name: str
    condition: Condition
    action: Action
    enabled: bool


class RuleSet(NamedTuple):
    name: str
    hosts: Union[str, List[str]]
    sources: List[EventSource]
    rules: List[Rule]
    gather_facts: bool


class ActionContext(NamedTuple):
    ruleset: str
    rule: str
    action: str
    actions_args: Dict
    variables: Dict
    inventory: Dict
    hosts: List[str]
    facts: Dict
    c: Any


class RuleSetQueue(NamedTuple):
    ruleset: RuleSet
    queue: asyncio.Queue


class RuleSetQueuePlan(NamedTuple):
    ruleset: RuleSet
    queue: asyncio.Queue
    plan: asyncio.Queue


class EngineRuleSetQueuePlan(NamedTuple):
    ruleset: EngineRuleSet
    queue: asyncio.Queue
    plan: asyncio.Queue
