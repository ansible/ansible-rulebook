from durable.lang import *
import durable.lang
import yaml
import os
import asyncio
import janus
import pytest
from queue import Queue

from pprint import pprint

from ansible_events.rules_parser import parse_rule_sets
from ansible_events.engine import run_rulesets, start_source
from ansible_events.messages import Shutdown
from ansible_events.rule_types import EventSource, EventSourceFilter
from ansible_events.util import load_inventory

HERE = os.path.dirname(os.path.abspath(__file__))


def test_start_source():
    os.chdir(HERE)

    queue = Queue()
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

    queue = janus.Queue()

    ruleset_queues = [(ruleset, queue.async_q) for ruleset in rulesets]

    event_log = asyncio.Queue()

    return ruleset_queues, queue.sync_q, queue.async_q, event_log


@pytest.mark.asyncio
async def test_run_rulesets(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("test_rules.yml")

    queue.put(dict())
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()['type'] == 'EmptyEvent', '0'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1'
    assert event_log.get_nowait()['type'] == 'Job', '1.0'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.2'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.3'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.4'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '2'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '3'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '4'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '5'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '6'
    assert event_log.get_nowait()['type'] == 'Shutdown', '7'
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rules_with_assignment(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("rules_with_assignment.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '0'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '1'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '2'
    assert event_log.get_nowait()['type'] == 'Shutdown', '3'
    assert event_log.empty()

@pytest.mark.asyncio
async def test_run_rules_with_assignment2(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("rules_with_assignment2.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '0'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '1'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '2'
    assert event_log.get_nowait()['type'] == 'Shutdown', '3'
    assert event_log.empty()

@pytest.mark.asyncio
async def test_run_rules_simple(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("test_simple.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '0'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1'
    assert event_log.get_nowait()['type'] == 'Job', '1.0'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.2'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.3'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.4'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '2'
    assert event_log.get_nowait()['type'] == 'Shutdown', '3'
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("test_rules_multiple_hosts.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory('inventory1.yml'),
    )

    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '0'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1.1'
    assert event_log.get_nowait()['type'] == 'Job', '1.1.0'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.1'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.2'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.3'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.4'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.5'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.6'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.7'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.8'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.9'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.10'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.11'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.12'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1.13'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1.2'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1.3'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1.4'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '2'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '3'
    assert event_log.get_nowait()['type'] == 'Shutdown', '4'
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts2(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("test_rules_multiple_hosts2.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory('inventory1.yml'),
    )

    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '0'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '2'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '2.5'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '3'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '4'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '5'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '6'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '7'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '8'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '9'
    assert event_log.get_nowait()['type'] == 'Shutdown', '10'
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts3(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("test_rules_multiple_hosts3.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory('inventory.yml'),
    )

    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '0'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '2'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '3'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '4'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '5'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '6'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '7'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '8'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '9'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '10'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '11'
    assert event_log.get_nowait()['type'] == 'Shutdown', '12'
    assert event_log.empty()

@pytest.mark.asyncio
async def test_filters(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("test_filters.yml")

    queue.put(dict(i=0))
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '0'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1'
    assert event_log.get_nowait()['type'] == 'Job', '1.0'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.2'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.3'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.4'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '2'
    assert event_log.get_nowait()['type'] == 'Shutdown', '3'
    assert event_log.empty()

@pytest.mark.asyncio
async def test_run_rulesets_on_hosts(new_event_loop):

    ruleset_queues, queue, aqueue, event_log = load_rules("test_host_rules.yml")

    queue.put(dict())
    queue.put(dict(i=1, meta=dict(hosts='localhost0')))
    queue.put(dict(i=2, meta=dict(hosts='localhost0')))
    queue.put(dict(i=3, meta=dict(hosts='localhost0')))
    queue.put(dict(i=4, meta=dict(hosts='localhost0')))
    queue.put(dict(i=5, meta=dict(hosts='localhost0')))
    queue.put(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()['type'] == 'EmptyEvent', '0'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '1'
    assert event_log.get_nowait()['type'] == 'Job', '1.0'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.1'
    assert event_log.get_nowait()['type'] == 'AnsibleEvent', '1.2'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '2'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '3'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '4'
    #assert event_log.get_nowait()['type'] == 'MessageNotHandled', '5'
    assert event_log.get_nowait()['type'] == 'ProcessedEvent', '6'
    assert event_log.get_nowait()['type'] == 'Shutdown', '7'
    assert event_log.empty()
