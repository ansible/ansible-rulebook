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

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional, Union

from drools.ruleset import Ruleset as EngineRuleSet

import ansible_rulebook.condition_types as ct


class ExecutionStrategy(Enum):
    SEQUENTIAL = 1
    PARALLEL = 2


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
    uuid: Optional[str] = None


class Condition(NamedTuple):
    when: str
    value: List[ct.Condition]
    timeout: Optional[str] = None


class Throttle(NamedTuple):
    group_by_attributes: List[str]
    once_within: Optional[str] = None
    once_after: Optional[str] = None


class Rule(NamedTuple):
    name: str
    condition: Condition
    actions: List[Action]
    enabled: bool
    throttle: Optional[Throttle] = None
    uuid: Optional[str] = None


class RuleSet(NamedTuple):
    name: str
    hosts: Union[str, List[str]]
    sources: List[EventSource]
    rules: List[Rule]
    execution_strategy: ExecutionStrategy
    gather_facts: bool
    uuid: Optional[str] = None
    default_events_ttl: Optional[str] = None
    match_multiple_rules: bool = False


class ActionContext(NamedTuple):
    ruleset: str
    ruleset_uuid: str
    rule: str
    rule_uuid: str
    actions: List[Action]
    variables: Dict
    inventory: str
    hosts: List[str]
    rule_engine_results: Any


class RuleSetQueue(NamedTuple):
    ruleset: RuleSet
    source_queue: asyncio.Queue


@dataclass
class Plan:
    queue: asyncio.Queue


class EngineRuleSetQueuePlan(NamedTuple):
    ruleset: EngineRuleSet
    source_queue: asyncio.Queue
    plan: Plan
