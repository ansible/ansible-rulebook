
from durable.lang import *
import durable.lang
import yaml
import os
import asyncio
import pytest
import multiprocessing as mp

from ansible_events.rules_parser import parse_rule_sets
from ansible_events.rule_generator import generate_host_rulesets

HERE = os.path.dirname(os.path.abspath(__file__))

def test_m():
    assert m
    assert m.x
    assert m.x.define() == {'$m': 'x'}
    assert m.x > m.y
    assert (m.x > m.y).define() == {'$gt': {'x': {'$m': 'y'}}}
    assert m.x == m.y
    assert (m.x == m.y).define() ==  {'x': {'$m': 'y'}}
    assert m.x < m.y
    assert (m.x < m.y).define() ==  {'$lt': {'x': {'$m': 'y'}}}
    assert (+m.x).define() == {'$ex': {'x': 1}}
    assert (-m.x).define() == {'$nex': {'x': 1}}
    assert (m.x.y.z == 'foo').define() ==  {'x.y.z': 'foo'}

def test_ruleset():

    some_rules = ruleset('test_rules')

    assert some_rules
    assert durable.lang._rulesets
    assert durable.lang._rulesets['test_rules'] == some_rules

    assert len(durable.lang._ruleset_stack) == 0

    with some_rules:
        assert durable.lang._ruleset_stack[-1] == some_rules

    assert len(durable.lang._ruleset_stack) == 0

    assert some_rules.define() == ('test_rules', {})


def test_rules():

    some_rules = ruleset('test_rules1')

    assert some_rules
    assert durable.lang._rulesets
    assert durable.lang._rulesets['test_rules1'] == some_rules

    assert len(durable.lang._ruleset_stack) == 0

    with some_rules:
        assert durable.lang._ruleset_stack[-1] == some_rules

        def x(c):
            print('c')

        #when_all(m.x == 5)(x)
        rule('all', True, m.x == 5)(x)

    assert len(durable.lang._ruleset_stack) == 0

    assert some_rules.define() == ('test_rules1', {'r_0': {'all': [{'m': {'x': 5}}],
                                                           'run': x}})
    post('test_rules1', {'x': 5})



def test_assert_facts():

    some_rules = ruleset('test_assert_facts')

    with some_rules:
        @when_all(+m.subject.x)
        def output(c):
            print('Fact: {0} {1} {2}'.format(c.m.subject.x, c.m.predicate, c.m.object))

    assert_fact('test_assert_facts',  { 'subject': {'x': 'Kermit'}, 'predicate': 'eats', 'object': 'flies' })



def test_parse_rules():
    os.chdir(HERE)
    with open('rules.yml') as f:
        data = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)

@pytest.mark.asyncio
async def test_generate_rules():
    os.chdir(HERE)
    with open('rules.yml') as f:
        data = yaml.safe_load(f.read())
    with open('inventory.yml') as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queue_plans = [ (ruleset, mp.Queue(), asyncio.Queue()) for ruleset in rulesets ]
    durable_rulesets = generate_host_rulesets(ruleset_queue_plans, dict(), inventory)

    print(durable_rulesets[0][0].define())
    print(durable_rulesets[0][1][0].define())

    assert_fact('Demo rules_localhost',  {'payload': {'text': 'hello'}})

    assert ruleset_queue_plans[0][2].get_nowait()[1] == 'slack'
    assert ruleset_queue_plans[0][2].get_nowait()[1] == 'assert_fact'
    assert ruleset_queue_plans[0][2].get_nowait()[1] == 'log'
