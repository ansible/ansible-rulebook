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
from typing import Any, Dict, List, NamedTuple, Union

from drools.ruleset import Ruleset as EngineRuleSet

import ansible_rulebook.condition_types as ct


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
    source_queue: asyncio.Queue


@dataclass
class Plan:
    queue: asyncio.Queue


class EngineRuleSetQueuePlan(NamedTuple):
    ruleset: EngineRuleSet
    source_queue: asyncio.Queue
    plan: Plan
