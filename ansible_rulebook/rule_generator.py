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

import asyncio
import json
import logging
from typing import Any, Callable, Dict, List

from drools.rule import Rule as DroolsRule
from drools.ruleset import Ruleset as DroolsRuleset

from ansible_rulebook.json_generator import visit_ruleset
from ansible_rulebook.rule_types import (
    Action,
    ActionContext,
    EngineRuleSetQueuePlan,
    Plan,
    RuleSetQueue,
)

logger = logging.getLogger(__name__)


def add_to_plan(
    ruleset: str,
    ruleset_uuid: str,
    rule: str,
    rule_uuid: str,
    actions: List[Action],
    variables: Dict,
    inventory: str,
    hosts: List,
    plan: Plan,
    rule_engine_results: Any,
) -> None:
    plan.queue.put_nowait(
        ActionContext(
            ruleset,
            ruleset_uuid,
            rule,
            rule_uuid,
            actions,
            variables,
            inventory,
            hosts,
            rule_engine_results,
        )
    )


def make_fn(
    ruleset,
    ruleset_uuid,
    ansible_rule,
    variables: Dict,
    inventory: str,
    hosts: List,
    plan: Plan,
) -> Callable:
    def fn(rule_engine_results):
        logger.debug("callback calling %s", ansible_rule.name)
        add_to_plan(
            ruleset,
            ruleset_uuid,
            ansible_rule.name,
            ansible_rule.uuid,
            ansible_rule.actions,
            variables,
            inventory,
            hosts,
            plan,
            rule_engine_results,
        )

    return fn


def generate_rulesets(
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: str,
) -> List[EngineRuleSetQueuePlan]:

    rulesets = []

    for ansible_ruleset, source_queue in ruleset_queues:
        ruleset_ast = visit_ruleset(ansible_ruleset, variables)
        drools_ruleset = DroolsRuleset(
            name=ansible_ruleset.name,
            serialized_ruleset=json.dumps(ruleset_ast["RuleSet"]),
        )
        plan = Plan(queue=asyncio.Queue())
        for ansible_rule in ansible_ruleset.rules:
            if ansible_rule.enabled:
                fn = make_fn(
                    ansible_ruleset.name,
                    ansible_ruleset.uuid,
                    ansible_rule,
                    variables,
                    inventory,
                    ansible_ruleset.hosts,
                    plan,
                )
                drools_ruleset.add_rule(
                    DroolsRule(name=ansible_rule.name, callback=fn)
                )

        rulesets.append(
            EngineRuleSetQueuePlan(drools_ruleset, source_queue, plan)
        )
    return rulesets
