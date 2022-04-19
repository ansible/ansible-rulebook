from durable.lang import m, c, assert_fact, ruleset, rule, when_all, post
from durable.lang import statechart, state, to
import durable
from ansible_events.rule_generator import generate_statecharts
from ansible_events.rules_parser import parse_state_machines
import pytest
import os
import yaml
import multiprocessing as mp
import asyncio

HERE = os.path.dirname(os.path.abspath(__file__))


def test_statemachine():

    statemachine = statechart('hello')

    assert statemachine
    assert durable.lang._rulesets
    assert durable.lang._rulesets["hello"] == statemachine

    with statemachine:
        a_state = state('initial')

    assert statemachine.define() == ('hello$state', {'initial': {}})


def test_states():

    some_states = statechart("test_states1")

    assert some_states
    assert durable.lang._rulesets
    assert durable.lang._rulesets["test_states1"] == some_states

    assert len(durable.lang._ruleset_stack) == 0

    with some_states:
        assert durable.lang._ruleset_stack[-1] == some_states

        a_state = state('initial')

        with a_state:
            #@to('end_state')
            #@when_all(m.x == 5)
            def x(c):
                print("c")
            # when_all(m.x == 5)(x)
            #rule("all", True, m.x == 5)(to('end_state',x))
            to('end_state')(rule("all", True, m.x == 5)(x))

        state('end_state')

    assert len(durable.lang._ruleset_stack) == 0

    print(some_states.define())
    assert some_states.define() == (
        "test_states1$state", {'end_state': {},
            'initial': {'t_0': {'all': [{'m': {'x': 5}}], 'run': x, 'to': 'end_state'}}},
    )
    post("test_states1", {"x": 5})

def no_test_assert_facts():

    some_rules = ruleset("test_assert_facts")

    with some_rules:

        @when_all(+m.subject.x)
        def output(c):
            print("Fact: {0} {1} {2}".format(c.m.subject.x, c.m.predicate, c.m.object))

    assert_fact(
        "test_assert_facts",
        {"subject": {"x": "Kermit"}, "predicate": "eats", "object": "flies"},
    )


def no_test_parse_rules():
    os.chdir(HERE)
    with open("rules.yml") as f:
        data = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)


@pytest.mark.asyncio
async def test_generate_statecharts():
    os.chdir(HERE)
    with open("test_states2.yml") as f:
        data = yaml.safe_load(f.read())
    with open("inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    state_machines = parse_state_machines(data)
    print(state_machines)
    state_machine_queue_plans = [
        (state_machine, mp.Queue(), asyncio.Queue()) for state_machine in state_machines
    ]
    durable_statecharts = generate_statecharts(state_machine_queue_plans, dict(), inventory)

    print(durable_statecharts[0][0].define())

    assert_fact("Test state machines2", {"payload": {"text": "hello"}})
    assert_fact("Test state machines2", {"payload": {"text": "goodbye"}})

    assert state_machine_queue_plans[0][2].get_nowait()[1] == "debug"
    assert state_machine_queue_plans[0][2].get_nowait()[1] == "debug"


def test_experimental():
    assert False, "experimental code do not merge"
