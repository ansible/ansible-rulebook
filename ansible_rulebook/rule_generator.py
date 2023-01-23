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
from typing import Callable, Dict, List

from drools.rule import Rule as DroolsRule
from drools.ruleset import Ruleset as DroolsRuleset

from ansible_rulebook.json_generator import visit_ruleset
from ansible_rulebook.rule_types import (
    ActionContext,
    EngineRuleSetQueuePlan,
    Plan,
    RuleSetQueue,
)

logger = logging.getLogger(__name__)


def add_to_plan(
    ruleset: str,
    rule: str,
    action: str,
    action_args: Dict,
    variables: Dict,
    inventory: Dict,
    hosts: List,
    facts: Dict,
    plan: Plan,
    c,
) -> None:
    plan.queue.put_nowait(
        ActionContext(
            ruleset,
            rule,
            action,
            action_args,
            variables,
            inventory,
            hosts,
            facts,
            c,
        )
    )


def make_fn(
    ruleset,
    ansible_rule,
    variables: Dict,
    inventory: Dict,
    hosts: List,
    facts: Dict,
    plan: Plan,
) -> Callable:
    def fn(c):
        logger.info("calling %s", ansible_rule.name)
        add_to_plan(
            ruleset,
            ansible_rule.name,
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
    ruleset_queues: List[RuleSetQueue],
    variables: Dict,
    inventory: Dict,
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
                    ansible_rule,
                    variables,
                    inventory,
                    ansible_ruleset.hosts,
                    {},
                    plan,
                )
                drools_ruleset.add_rule(
                    DroolsRule(name=ansible_rule.name, callback=fn)
                )

        rulesets.append(
            EngineRuleSetQueuePlan(drools_ruleset, source_queue, plan)
        )
    return rulesets
