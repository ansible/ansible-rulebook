import asyncio
import os
from pprint import pprint

import pytest
import yaml

from ansible_events.engine import run_rulesets, start_source
from ansible_events.messages import Shutdown
from ansible_events.rule_types import EventSource, EventSourceFilter
from ansible_events.rules_parser import parse_rule_sets
from ansible_events.util import load_inventory

HERE = os.path.dirname(os.path.abspath(__file__))


def load_rules(rules_file):
    os.chdir(HERE)
    with open(rules_file) as f:
        data = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    pprint(rulesets)

    queue = asyncio.Queue()

    ruleset_queues = [(ruleset, queue) for ruleset in rulesets]

    event_log = asyncio.Queue()

    return ruleset_queues, queue, event_log


@pytest.mark.asyncio
async def test_start_source():
    os.chdir(HERE)

    queue = asyncio.Queue()
    await start_source(
        EventSource(
            "range", "range", dict(limit=1), [EventSourceFilter("noop", {})]
        ),
        ["sources"],
        dict(limit=1),
        queue,
    )
    assert queue.get_nowait() == dict(i=0)


@pytest.mark.asyncio
async def test_run_rulesets():

    ruleset_queues, queue, event_log = load_rules("test_rules.yml")

    queue.put_nowait(dict())
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(dict(i=3))
    queue.put_nowait(dict(i=4))
    queue.put_nowait(dict(i=5))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "EmptyEvent", "0"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.4"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "3"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "4"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '5'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "6"
    assert event_log.get_nowait()["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rules_with_assignment():
    ruleset_queues, queue, event_log = load_rules("rules_with_assignment.yml")

    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "ProcessedEvent", "0"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '1'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rules_with_assignment2():
    ruleset_queues, queue, event_log = load_rules("rules_with_assignment2.yml")

    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "ProcessedEvent", "0"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '1'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rules_simple():
    ruleset_queues, queue, event_log = load_rules("test_simple.yml")

    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "ProcessedEvent", "0"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.4"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts():
    ruleset_queues, queue, event_log = load_rules(
        "test_rules_multiple_hosts.yml"
    )

    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(dict(i=3))
    queue.put_nowait(dict(i=4))
    queue.put_nowait(dict(i=5))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        load_inventory("inventory1.yml"),
    )

    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '0'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1.1"
    assert event_log.get_nowait()["type"] == "Job", "1.1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.4"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.5"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.6"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.7"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.8"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.9"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.10"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.11"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.12"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1.13"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1.2"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1.3"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1.4"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '2'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "3"
    assert event_log.get_nowait()["type"] == "Shutdown", "4"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts2():
    ruleset_queues, queue, event_log = load_rules(
        "test_rules_multiple_hosts2.yml"
    )

    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(dict(i=3))
    queue.put_nowait(dict(i=4))
    queue.put_nowait(dict(i=5))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        load_inventory("inventory1.yml"),
    )

    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '0'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '2.5'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "3"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '4'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "5"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '6'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "7"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '8'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "9"
    assert event_log.get_nowait()["type"] == "Shutdown", "10"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts3():
    ruleset_queues, queue, event_log = load_rules(
        "test_rules_multiple_hosts3.yml"
    )

    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(dict(i=3))
    queue.put_nowait(dict(i=4))
    queue.put_nowait(dict(i=5))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        load_inventory("inventory.yml"),
    )

    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '0'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '2'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "3"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '4'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "5"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '6'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "7"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '8'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "9"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '10'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "11"
    assert event_log.get_nowait()["type"] == "Shutdown", "12"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_filters():
    ruleset_queues, queue, event_log = load_rules("test_filters.yml")

    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "ProcessedEvent", "0"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.4"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rulesets_on_hosts():
    ruleset_queues, queue, event_log = load_rules("test_host_rules.yml")

    queue.put_nowait(dict())
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost0")))
    queue.put_nowait(dict(i=2, meta=dict(hosts="localhost0")))
    queue.put_nowait(dict(i=3, meta=dict(hosts="localhost0")))
    queue.put_nowait(dict(i=4, meta=dict(hosts="localhost0")))
    queue.put_nowait(dict(i=5, meta=dict(hosts="localhost0")))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        1,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "EmptyEvent", "0"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "3"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "4"
    # assert event_log.get_nowait()['type'] == 'MessageNotHandled', '5'
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "6"
    assert event_log.get_nowait()["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rules_with_multiple_sources():

    ruleset_queues, queue, event_log = load_rules("test_multiple_sources.yml")

    queue.put_nowait(dict(range2=dict(i=0)))
    queue.put_nowait(dict(range2=dict(i=1)))
    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(range2=dict(i=2)))
    queue.put_nowait(dict(range2=dict(i=3)))
    queue.put_nowait(dict(range2=dict(i=4)))
    queue.put_nowait(Shutdown())
    queue.put_nowait(dict(i=2))
    queue.put_nowait(dict(i=3))
    queue.put_nowait(dict(i=4))
    queue.put_nowait(dict(i=5))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        2,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "ProcessedEvent", "0"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "1"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "2"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "3"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "4"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "5"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "6"
    assert event_log.get_nowait()["type"] == "EmptyEvent", "7"
    assert event_log.get_nowait()["type"] == "Job", "8"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "9"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "10"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "11"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "12"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "13"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "14"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "15"
    assert event_log.get_nowait()["type"] == "ProcessedEvent", "16"
    assert event_log.get_nowait()["type"] == "Shutdown", "17"
    assert event_log.empty()
