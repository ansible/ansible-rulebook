import ansible_events.rule_types as rt
import ansible_events.condition_types as ct

from ansible_events.condition_parser import parse_condition as parse_condition_value

from typing import Dict, List


def parse_rule_sets(rule_sets: Dict) -> List[rt.RuleSet]:
    rule_set_list = []
    for rule_set in rule_sets:
        rule_set_list.append(
            rt.RuleSet(
                name=rule_set["name"],
                hosts=rule_set["hosts"],
                sources=parse_event_sources(rule_set["sources"]),
                rules=parse_rules(rule_set.get("rules", {})),
                host_rules=parse_rules(rule_set.get("host_rules", {})),
            )
        )
    return rule_set_list


def parse_event_sources(sources: Dict) -> List[rt.EventSource]:
    source_list = []
    for source in sources:
        name = source["name"]
        del source["name"]
        transform = source.pop("transform", None)
        source_name = list(source.keys())[0]
        if source[source_name]:
            source_args = {k: v for k, v in source[source_name].items()}
        else:
            source_args = {}
        source_list.append(
            rt.EventSource(
                name=name,
                source_name=source_name,
                source_args=source_args,
                transform=transform,
            )
        )

    return source_list


def parse_rules(rules: Dict) -> List[rt.Rule]:
    rule_list = []
    for rule in rules:
        name = rule.get("name")
        rule_list.append(
            rt.Rule(
                name=name,
                condition=parse_condition(parse_condition_value(rule["condition"])),
                action=parse_action(rule["action"]),
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


def parse_condition(condition: ct.Condition) -> rt.Condition:
    return rt.Condition(condition)
