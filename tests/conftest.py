import pytest

from ansible_rulebook.condition_types import Condition as Conditions
from ansible_rulebook.rule_types import (
    Action,
    Condition,
    EventSource,
    EventSourceFilter,
    ExecutionStrategy,
    Rule,
    RuleSet,
)


@pytest.fixture
def create_conditions(**kwargs):
    def _conditions(**kwargs):
        return Conditions(kwargs.pop("value", "2 > 1"))

    return _conditions


@pytest.fixture
def create_condition(create_conditions, **kwargs):
    def _condition(**kwargs):
        when = kwargs.pop("when", "all")
        value = kwargs.pop("value", [create_conditions()])
        return Condition(when, value)

    return _condition


@pytest.fixture
def create_event_source_filter(**kwargs):
    def _event_source_filter(**kwargs):
        filter_name = kwargs.pop("filter_name", "test")
        filter_args = kwargs.pop("filter_args", dict(arg1=1))
        return EventSourceFilter(filter_name, filter_args)

    return _event_source_filter


@pytest.fixture
def create_event_source(create_event_source_filter, **kwargs):
    def _event_source(**kwargs):
        name = kwargs.pop("name", "es")
        source_name = kwargs.pop("source_name", "sample_source_name")
        source_args = kwargs.pop("source_args", dict(arg1=1))
        source_filters = kwargs.pop(
            "source_filters", [create_event_source_filter()]
        )
        return EventSource(name, source_name, source_args, source_filters)

    return _event_source


@pytest.fixture
def create_action(**kwargs):
    def _action(**kwargs):
        action = kwargs.pop("action", "debug")
        action_args = kwargs.pop("action_args", dict(msg="Hello World"))
        return Action(action, action_args)

    return _action


@pytest.fixture
def create_rule(create_condition, create_action, **kwargs):
    def _rule(**kwargs):
        name = kwargs.pop("name", "r1")
        cond = kwargs.pop("condition", create_condition())
        actions = kwargs.pop("actions", [create_action()])
        enabled = kwargs.pop("enabled", True)
        throttle = kwargs.pop("throttle", None)
        return Rule(name, cond, actions, enabled, throttle)

    return _rule


@pytest.fixture
def create_ruleset(create_event_source, create_rule, **kwargs):
    def _ruleset(**kwargs):
        name = kwargs.pop("name", "ruleset1")
        hosts = kwargs.pop("hosts", ["host1"])
        event_sources = kwargs.pop("event_sources", [create_event_source()])
        rules = kwargs.pop("rules", [create_rule()])
        gather_facts = kwargs.pop("gather_facts", False)
        return RuleSet(
            name,
            hosts,
            event_sources,
            rules,
            ExecutionStrategy.SEQUENTIAL,
            gather_facts,
        )

    return _ruleset
