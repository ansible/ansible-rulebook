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

import uuid
from typing import Any, Dict, List, Optional

import ansible_rulebook.rule_types as rt
from ansible_rulebook.condition_parser import (
    parse_condition as parse_condition_value,
)
from ansible_rulebook.conf import settings
from ansible_rulebook.util import substitute_variables

from .exception import (
    RulenameDuplicateException,
    RulenameEmptyException,
    RulesetNameDuplicateException,
    RulesetNameEmptyException,
)


def parse_hosts(hosts):
    if isinstance(hosts, str):
        return [hosts]
    elif isinstance(hosts, list):
        return hosts
    else:
        raise Exception(f"Unsupported hosts value {hosts}")


def parse_rule_sets(
    rule_sets: Dict, variables: Optional[Dict] = None
) -> List[rt.RuleSet]:
    rule_set_list = []
    ruleset_names = []
    for rule_set in rule_sets:
        name = rule_set.get("name")
        if name is None:
            raise RulesetNameEmptyException("Ruleset name not provided")

        name = name.strip()
        if name == "":
            raise RulesetNameEmptyException(
                "Ruleset name cannot be an empty string"
            )

        if name in ruleset_names:
            raise RulesetNameDuplicateException(
                f"Ruleset with name: {name} defined multiple times"
            )

        ruleset_names.append(name)

        if variables is None:
            variables = {}

        strategy = rule_set.get(
            "execution_strategy", settings.default_execution_strategy
        )
        if strategy == "sequential":
            execution_strategy = rt.ExecutionStrategy.SEQUENTIAL
        elif strategy == "parallel":
            execution_strategy = rt.ExecutionStrategy.PARALLEL

        rule_set_list.append(
            rt.RuleSet(
                name=name,
                hosts=parse_hosts(rule_set["hosts"]),
                sources=parse_event_sources(rule_set["sources"]),
                rules=parse_rules(rule_set.get("rules", {}), variables),
                execution_strategy=execution_strategy,
                gather_facts=rule_set.get("gather_facts", False),
                uuid=str(uuid.uuid4()),
                default_events_ttl=rule_set.get("default_events_ttl", None),
                match_multiple_rules=rule_set.get(
                    "match_multiple_rules", False
                ),
            )
        )
    return rule_set_list


def parse_event_sources(sources: Dict) -> List[rt.EventSource]:
    source_list = []
    for source in sources:
        name = source.pop("name", "")
        source_filters = []
        for source_filter in source.pop("filters", []):
            source_filters.append(parse_source_filter(source_filter))
        source_name = list(source.keys())[0]
        if source[source_name]:
            source_args = {k: v for k, v in source[source_name].items()}
        else:
            source_args = {}
        source_list.append(
            rt.EventSource(
                name=name or source_name,
                source_name=source_name,
                source_args=source_args,
                source_filters=source_filters,
            )
        )

    return source_list


def parse_source_filter(source_filter: Dict) -> rt.EventSourceFilter:

    source_filter_name = list(source_filter.keys())[0]
    source_filter_args = source_filter[source_filter_name]

    return rt.EventSourceFilter(source_filter_name, source_filter_args)


def parse_rules(rules: Dict, variables: Dict) -> List[rt.Rule]:
    rule_list = []
    rule_names = []
    if variables is None:
        variables = {}
    for rule in rules:
        name = rule.get("name")
        if name is None:
            raise RulenameEmptyException("Rule name not provided")

        name = substitute_variables(name, variables)
        if name == "":
            raise RulenameEmptyException("Rule name cannot be an empty string")

        if name in rule_names:
            raise RulenameDuplicateException(
                f"Rule with name {name} defined multiple times"
            )

        rule_names.append(name)
        if "throttle" in rule:
            throttle = rt.Throttle(
                once_within=rule["throttle"].get("once_within", None),
                once_after=rule["throttle"].get("once_after", None),
                group_by_attributes=rule["throttle"]["group_by_attributes"],
            )
        else:
            throttle = None

        rule = rt.Rule(
            name=name,
            condition=parse_condition(rule["condition"]),
            actions=parse_actions(rule),
            enabled=rule.get("enabled", True),
            throttle=throttle,
            uuid=str(uuid.uuid4()),
        )
        if rule.enabled:
            rule_list.append(rule)

    return rule_list


def parse_actions(rule: Dict) -> List[rt.Action]:
    actions = []
    if "actions" in rule:
        for action in rule["actions"]:
            actions.append(parse_action(action))
    elif "action" in rule:
        actions.append(parse_action(rule["action"]))

    return actions


def parse_action(action: Dict) -> rt.Action:
    action_name = list(action.keys())[0]
    if action[action_name]:
        action_args = {k: v for k, v in action[action_name].items()}
    else:
        action_args = {}
    return rt.Action(action=action_name, action_args=action_args)


def parse_condition(condition: Any) -> rt.Condition:
    if isinstance(condition, str):
        return rt.Condition("all", [parse_condition_value(condition)])
    elif isinstance(condition, bool):
        return rt.Condition("all", [parse_condition_value(str(condition))])
    elif isinstance(condition, dict):
        timeout = condition.pop("timeout", None)
        keys = list(condition.keys())
        if len(condition) == 1 and keys[0] in ["any", "all", "not_all"]:
            when = keys[0]
            return rt.Condition(
                when,
                [parse_condition_value(str(c)) for c in condition[when]],
                timeout,
            )
        else:
            raise Exception(
                f"Condition should have one of any, all, not_all: {condition}"
            )

    else:
        raise Exception(f"Unsupported condition {condition}")
