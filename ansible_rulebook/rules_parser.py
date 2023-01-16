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

from typing import Any, Dict, List

import ansible_rulebook.rule_types as rt
from ansible_rulebook.condition_parser import (
    parse_condition as parse_condition_value,
)
from ansible_rulebook.job_template_runner import job_template_runner

from .exception import RulenameDuplicateException, RulenameEmptyException


def parse_hosts(hosts):
    if isinstance(hosts, str):
        return [hosts]
    elif isinstance(hosts, list):
        return hosts
    else:
        raise Exception(f"Unsupported hosts value {hosts}")


def parse_rule_sets(rule_sets: Dict) -> List[rt.RuleSet]:
    rule_set_list = []
    for rule_set in rule_sets:
        rule_set_list.append(
            rt.RuleSet(
                name=rule_set["name"],
                hosts=parse_hosts(rule_set["hosts"]),
                sources=parse_event_sources(rule_set["sources"]),
                rules=parse_rules(rule_set.get("rules", {})),
                gather_facts=rule_set.get("gather_facts", False),
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


def parse_rules(rules: Dict) -> List[rt.Rule]:
    rule_list = []
    rule_names = []
    for rule in rules:
        name = rule.get("name")
        if name is None:
            raise RulenameEmptyException("Rule name not provided")

        if name == "":
            raise RulenameEmptyException("Rule name cannot be an empty string")

        if name in rule_names:
            raise RulenameDuplicateException(
                f"Rule with name {name} defined multiple times"
            )

        rule_names.append(name)
        rule_list.append(
            rt.Rule(
                name=name,
                condition=parse_condition(rule["condition"]),
                action=parse_action(rule["action"]),
                enabled=rule.get("enabled", True),
            )
        )

    return rule_list


def parse_action(action: Dict) -> rt.Action:
    action_name = list(action.keys())[0]
    if action_name == "run_job_template":
        if not job_template_runner.host or not job_template_runner.token:
            raise Exception("No controller is configured to run job templates")

    if action[action_name]:
        action_args = {k: v for k, v in action[action_name].items()}
    else:
        action_args = {}
    return rt.Action(action=action_name, action_args=action_args)


def parse_condition(condition: Any) -> rt.Condition:
    if isinstance(condition, str):
        return rt.Condition("all", [parse_condition_value(condition)])
    elif isinstance(condition, dict):
        keys = list(condition.keys())
        if len(condition) == 1 and keys[0] in ["any", "all"]:
            when = keys[0]
            return rt.Condition(
                when, [parse_condition_value(c) for c in condition[when]]
            )
        else:
            raise Exception(
                f"Condition should have one of any or all: {condition}"
            )

    else:
        raise Exception(f"Unsupported condition {condition}")
