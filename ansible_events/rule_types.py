from __future__ import annotations

from typing import NamedTuple, Union, List, Any, Dict
import ansible_events.condition_types as ct

import asyncio
import multiprocessing as mp


class EventSource(NamedTuple):
    name: str
    source_name: str
    source_args: dict
    transform: Union[str, None]


class Action(NamedTuple):
    action: str
    action_args: dict


class Condition(NamedTuple):
    value: ct.Condition


class Rule(NamedTuple):
    name: str
    condition: Condition
    action: Action


class RuleSet(NamedTuple):
    name: str
    hosts: Union[str, List[str]]
    sources: List[EventSource]
    rules: List[Rule]
    host_rules: List[Rule]


class HostRuleSet(NamedTuple):
    name: str
    host: str
    ruleset: RuleSet


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
    queue: mp.Queue

class RuleSetQueuePlan(NamedTuple):
    ruleset: RuleSet
    queue: mp.Queue
    plan: asyncio.Queue

