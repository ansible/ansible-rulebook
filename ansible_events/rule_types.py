from __future__ import annotations

import asyncio
from queue import Queue
from typing import Any, Dict, List, NamedTuple, Union

import ansible_events.condition_types as ct


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


class ActionContext(NamedTuple):
    ruleset: str
    action: str
    actions_args: Dict
    variables: Dict
    inventory: Dict
    hosts: List[str]
    facts: Dict
    c: Any


class RuleSetPlan(NamedTuple):
    ruleset: RuleSet
    plan: asyncio.Queue


class RuleSetQueue(NamedTuple):
    ruleset: RuleSet
    queue: Queue


class RuleSetQueuePlan(NamedTuple):
    ruleset: RuleSet
    queue: Queue
    plan: asyncio.Queue
