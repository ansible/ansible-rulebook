import ansible_events.rule_types as rt
import ansible_events.condition_types as ct

from ansible_events.condition_parser import parse_condition as parse_condition_value

from typing import Dict, List, Any


def parse_hosts(hosts):
    if isinstance(hosts, str):
        return [hosts]
    elif isinstance(hosts, list):
        return hosts
    else:
        raise Exception(f'Unsupported hosts value {hosts}')


def parse_rule_sets(rule_sets: Dict) -> List[rt.RuleSet]:
    rule_set_list = []
    for rule_set in rule_sets:
        rule_set_list.append(
            rt.RuleSet(
                name=rule_set["name"],
                hosts=parse_hosts(rule_set["hosts"]),
                sources=parse_event_sources(rule_set["sources"]),
                rules=parse_rules(rule_set.get("rules", {})),
            )
        )
    return rule_set_list


def parse_event_sources(sources: Dict) -> List[rt.EventSource]:
    source_list = []
    for source in sources:
        name = source.pop("name", '')
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

    return rt.EventSourceFilter(source_filter_name,
                             source_filter_args)


def parse_rules(rules: Dict) -> List[rt.Rule]:
    rule_list = []
    for rule in rules:
        name = rule.get("name")
        rule_list.append(
            rt.Rule(
                name=name,
                condition=parse_condition(rule["condition"]),
                action=parse_action(rule["action"]),
                enabled=rule.get('enabled', True)
            )
        )

    return rule_list


def parse_action(action: Dict) -> rt.Action:
    action_name = list(action.keys())[0]
    if action[action_name]:
        action_args = {k: v for k, v in action[action_name].items()}
    else:
        action_args = {}
    return rt.Action(action=action_name, action_args=action_args)


def parse_condition(condition: Any) -> rt.Condition:
    if isinstance(condition, str):
        return rt.Condition('all', [parse_condition_value(condition)])
    elif isinstance(condition, dict):
        keys = list(condition.keys())
        if len(condition) == 1 and keys[0] in ['any', 'all']:
            when = keys[0]
            return rt.Condition(when, [parse_condition_value(c) for c in condition[when]])
        else:
            raise Exception(f'Condition should have one of any or all: {condition}')

    else:
        raise Exception(f'Unsupported condition {condition}')
