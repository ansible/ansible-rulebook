from durable.lang import *
import durable.lang
import yaml
import os
import asyncio
import multiprocessing as mp

from pprint import pprint

from ansible_events.rules_parser import parse_rule_sets
from ansible_events.engine import run_rulesets, start_sources
from ansible_events.messages import Shutdown
from ansible_events.rule_types import EventSource

HERE = os.path.dirname(os.path.abspath(__file__))


def test_start_sources():
    os.chdir(HERE)

    queue = mp.Queue()
    start_sources(
        [EventSource("range", "range", dict(limit=1), None)],
        ["sources"],
        dict(limit=1),
        queue,
    )
    assert queue.get() == dict(i=0)


def test_run_rulesets():
    os.chdir(HERE)
    with open("test_rules.yml") as f:
        data = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    pprint(rulesets)

    ruleset_queues = [(ruleset, mp.Queue()) for ruleset in rulesets]

    event_log = mp.Queue()

    queue = ruleset_queues[0][1]
    queue.put(dict())
    queue.put(dict(i=1))
    queue.put(dict(i=2))
    queue.put(dict(i=3))
    queue.put(dict(i=4))
    queue.put(dict(i=5))
    queue.put(Shutdown())

    redis_host_name = None
    redis_port = None
    # redis_host_name='localhost'
    # redis_port=6379

    run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
        redis_host_name=redis_host_name,
        redis_port=redis_port,
    )

    assert event_log.get()['type'] == 'EmptyEvent', '0'
    assert event_log.get()['type'] == 'ProcessedEvent', '1'
    assert event_log.get()['type'] == 'ProcessedEvent', '2'
    assert event_log.get()['type'] == 'ProcessedEvent', '3'
    assert event_log.get()['type'] == 'ProcessedEvent', '4'
    assert event_log.get()['type'] == 'MessageNotHandled', '5'
    assert event_log.get()['type'] == 'ProcessedEvent', '6'
    assert event_log.get()['type'] == 'Shutdown', '7'
    assert event_log.empty()
