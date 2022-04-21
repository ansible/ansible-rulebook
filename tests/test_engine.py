from durable.lang import *
import durable.lang
import yaml
import os
import asyncio
import multiprocessing as mp
import pytest

from pprint import pprint

from ansible_events.rules_parser import parse_rule_sets
from ansible_events.engine import run_rulesets, start_source
from ansible_events.messages import Shutdown
from ansible_events.rule_types import EventSource, EventSourceFilter
from ansible_events.util import load_inventory

HERE = os.path.dirname(os.path.abspath(__file__))


def test_start_source():
    os.chdir(HERE)

    queue = mp.Queue()
    start_source(
        EventSource("range", "range", dict(limit=1), [EventSourceFilter('noop', {})]),
        ["sources"],
        dict(limit=1),
        queue,
    )
    assert queue.get() == dict(i=0)


@pytest.fixture
def new_event_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    return loop



def load_rules(rules_file):
    os.chdir(HERE)
    with open(rules_file) as f:
        data = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    pprint(rulesets)

    ruleset_queues = [(ruleset, mp.Queue()) for ruleset in rulesets]

    event_log = mp.Queue()

    queue = ruleset_queues[0][1]

    return ruleset_queues, queue, event_log


def test_run_rulesets(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("test_rules.yml")

    queue.put(dict())
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get()['type'] == 'EmptyEvent', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    assert event_log.get()['type'] == 'ProcessedEvent', '3'
    assert event_log.get()['type'] == 'ProcessedEvent', '4'
    #assert event_log.get()['type'] == 'MessageNotHandled', '5'
    assert event_log.get()['type'] == 'ProcessedEvent', '6'
    assert event_log.get()['type'] == 'Shutdown', '7'
    assert event_log.empty()


def test_run_rules_with_assignment(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("rules_with_assignment.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get()['type'] == 'ProcessedEvent', '0'
    #assert event_log.get()['type'] == 'MessageNotHandled', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    assert event_log.get()['type'] == 'Shutdown', '3'
    assert event_log.empty()

def test_run_rules_with_assignment2(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("rules_with_assignment2.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get()['type'] == 'ProcessedEvent', '0'
    #assert event_log.get()['type'] == 'MessageNotHandled', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    assert event_log.get()['type'] == 'Shutdown', '3'
    assert event_log.empty()

def test_run_rules_simple(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("test_simple.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get()['type'] == 'ProcessedEvent', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    assert event_log.get()['type'] == 'Shutdown', '3'
    assert event_log.empty()


def test_run_multiple_hosts(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("test_rules_multiple_hosts.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory('inventory1.yml'),
    )

    #assert event_log.get()['type'] == 'MessageNotHandled', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '1.1'
    assert event_log.get()['type'] == 'ProcessedEvent', '1.2'
    assert event_log.get()['type'] == 'ProcessedEvent', '1.3'
    assert event_log.get()['type'] == 'ProcessedEvent', '1.4'
    #assert event_log.get()['type'] == 'MessageNotHandled', '2'
    assert event_log.get()['type'] == 'ProcessedEvent', '3'
    assert event_log.get()['type'] == 'Shutdown', '4'
    assert event_log.empty()


def test_run_multiple_hosts2(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("test_rules_multiple_hosts2.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory('inventory1.yml'),
    )

    #assert event_log.get()['type'] == 'MessageNotHandled', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    #assert event_log.get()['type'] == 'MessageNotHandled', '2.5'
    assert event_log.get()['type'] == 'ProcessedEvent', '3'
    #assert event_log.get()['type'] == 'MessageNotHandled', '4'
    assert event_log.get()['type'] == 'ProcessedEvent', '5'
    #assert event_log.get()['type'] == 'MessageNotHandled', '6'
    assert event_log.get()['type'] == 'ProcessedEvent', '7'
    #assert event_log.get()['type'] == 'MessageNotHandled', '8'
    assert event_log.get()['type'] == 'ProcessedEvent', '9'
    assert event_log.get()['type'] == 'Shutdown', '10'
    assert event_log.empty()


def test_run_multiple_hosts3(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("test_rules_multiple_hosts3.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory('inventory.yml'),
    )

    #assert event_log.get()['type'] == 'MessageNotHandled', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    #assert event_log.get()['type'] == 'MessageNotHandled', '2'
    assert event_log.get()['type'] == 'ProcessedEvent', '3'
    #assert event_log.get()['type'] == 'MessageNotHandled', '4'
    assert event_log.get()['type'] == 'ProcessedEvent', '5'
    #assert event_log.get()['type'] == 'MessageNotHandled', '6'
    assert event_log.get()['type'] == 'ProcessedEvent', '7'
    #assert event_log.get()['type'] == 'MessageNotHandled', '8'
    assert event_log.get()['type'] == 'ProcessedEvent', '9'
    #assert event_log.get()['type'] == 'MessageNotHandled', '10'
    assert event_log.get()['type'] == 'ProcessedEvent', '11'
    assert event_log.get()['type'] == 'Shutdown', '12'
    assert event_log.empty()

def test_filters(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("test_filters.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get()['type'] == 'ProcessedEvent', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    assert event_log.get()['type'] == 'Shutdown', '3'
    assert event_log.empty()

def test_run_rulesets_on_hosts(new_event_loop):

    ruleset_queues, queue, event_log = load_rules("test_host_rules.yml")

    queue.put(dict())
    queue.put(dict(i=1, meta=dict(hosts='localhost0')))
    queue.put(dict(i=2, meta=dict(hosts='localhost0')))
    queue.put(dict(i=3, meta=dict(hosts='localhost0')))
    queue.put(dict(i=4, meta=dict(hosts='localhost0')))
    queue.put(dict(i=5, meta=dict(hosts='localhost0')))
    queue.put(Shutdown())

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get()['type'] == 'EmptyEvent', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    assert event_log.get()['type'] == 'ProcessedEvent', '3'
    assert event_log.get()['type'] == 'ProcessedEvent', '4'
    #assert event_log.get()['type'] == 'MessageNotHandled', '5'
    assert event_log.get()['type'] == 'ProcessedEvent', '6'
    assert event_log.get()['type'] == 'Shutdown', '7'
    assert event_log.empty()
