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

import asyncio
import os
from pprint import pprint

import pytest
import yaml
from jsonschema.exceptions import ValidationError

from ansible_rulebook.engine import run_rulesets, start_source
from ansible_rulebook.exception import RulenameDuplicateException
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import EventSource, EventSourceFilter
from ansible_rulebook.rules_parser import parse_rule_sets
from ansible_rulebook.util import load_inventory
from ansible_rulebook.validators import Validate

HERE = os.path.dirname(os.path.abspath(__file__))


def load_rulebook(rules_file):
    os.chdir(HERE)
    with open(rules_file) as f:
        data = yaml.safe_load(f.read())

    Validate.rulebook(data)
    rulesets = parse_rule_sets(data)
    pprint(rulesets)

    ruleset_queues = [(ruleset, asyncio.Queue()) for ruleset in rulesets]

    event_log = asyncio.Queue()

    return ruleset_queues, event_log


def validate_events(event_log, **kwargs):
    shutdown_events = 0
    job_events = 0
    ansible_events = 0
    action_events = 0
    actions = []

    for _ in range(kwargs["max_events"]):
        event = event_log.get_nowait()
        print(event)
        if event["type"] == "Action":
            action_events += 1
            actions.append(
                f"{event['ruleset']}::{event['rule']}::{event['action']}"
            )
        elif event["type"] == "Shutdown":
            shutdown_events += 1
        elif event["type"] == "Job":
            job_events += 1
        elif event["type"] == "AnsibleEvent":
            ansible_events += 1

    assert event_log.empty()
    if "actions" in kwargs:
        assert kwargs["actions"] == actions
    if "shutdown_events" in kwargs:
        assert kwargs["shutdown_events"] == shutdown_events
    if "job_events" in kwargs:
        assert kwargs["job_events"] == job_events
    if "ansible_events" in kwargs:
        assert kwargs["ansible_events"] == ansible_events
    if "action_events" in kwargs:
        assert kwargs["action_events"] == action_events


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

    ruleset_queues, event_log = load_rulebook("rules/test_rules.yml")

    queue = ruleset_queues[0][1]
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
        dict(),
        load_inventory("playbooks/inventory.yml"),
    )

    checks = {
        "max_events": 18,
        "shutdown_events": 1,
        "job_events": 1,
        "ansible_events": 9,
        "action_events": 6,
    }
    validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_run_rules_with_assignment():
    ruleset_queues, event_log = load_rulebook(
        "rules/rules_with_assignment.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "Action", "0"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rules_with_assignment2():
    ruleset_queues, event_log = load_rulebook(
        "rules/rules_with_assignment2.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "Action", "0"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rules_simple():
    ruleset_queues, event_log = load_rulebook("rules/test_simple.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "Action", "0"
    assert event_log.get_nowait()["type"] == "Action", "0.2"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.4"
    assert event_log.get_nowait()["type"] == "Action", "1.5"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts():
    ruleset_queues, event_log = load_rulebook(
        "rules/test_rules_multiple_hosts.yml"
    )

    queue = ruleset_queues[0][1]
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
        dict(),
        load_inventory("playbooks/inventory1.yml"),
    )

    checks = {
        "max_events": 21,
        "shutdown_events": 1,
        "job_events": 1,
        "ansible_events": 13,
        "action_events": 6,
    }
    validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_run_multiple_hosts2():
    ruleset_queues, event_log = load_rulebook(
        "rules/test_rules_multiple_hosts2.yml"
    )

    queue = ruleset_queues[0][1]
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
        dict(),
        load_inventory("playbooks/inventory1.yml"),
    )

    assert event_log.get_nowait()["type"] == "Action", "1"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_multiple_hosts3():
    ruleset_queues, event_log = load_rulebook(
        "rules/test_rules_multiple_hosts3.yml"
    )

    queue = ruleset_queues[0][1]
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
        dict(),
        load_inventory("playbooks/inventory.yml"),
    )

    assert event_log.get_nowait()["type"] == "Action", "1"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_filters():
    ruleset_queues, event_log = load_rulebook("rules/test_filters.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=0))
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    assert event_log.get_nowait()["type"] == "Action", "0"
    assert event_log.get_nowait()["type"] == "Action", "0.2"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.4"
    assert event_log.get_nowait()["type"] == "Action", "1.5"
    assert event_log.get_nowait()["type"] == "Shutdown", "3"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_run_rulesets_on_hosts():
    ruleset_queues, event_log = load_rulebook("rules/test_host_rules.yml")

    queue = ruleset_queues[0][1]
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
        dict(),
        load_inventory("playbooks/inventory1.yml"),
    )

    checks = {
        "max_events": 18,
        "shutdown_events": 1,
        "job_events": 1,
        "ansible_events": 9,
        "action_events": 6,
    }
    validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_run_assert_facts():
    ruleset_queues, event_log = load_rulebook("rules/test_set_facts.yml")
    inventory = dict(
        all=dict(hosts=dict(localhost=dict(ansible_connection="local")))
    )
    queue = ruleset_queues[0][1]
    queue.put_nowait(dict())
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))
    queue.put_nowait(Shutdown())
    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        inventory,
    )

    assert event_log.get_nowait()["type"] == "EmptyEvent", "0"
    assert event_log.get_nowait()["type"] == "Action", "0.1"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    for i in range(41):
        assert event_log.get_nowait()["type"] == "AnsibleEvent", f"1.{i}"

    event = event_log.get_nowait()
    assert event["type"] == "Action", "2.1"
    assert event["action"] == "run_playbook", "2.2"
    assert event["rc"] == 0, "2.3"
    assert event["status"] == "successful", "2.4"
    assert event_log.get_nowait()["type"] == "Shutdown", "4"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_duplicate_rule_names():
    with pytest.raises(RulenameDuplicateException):
        load_rulebook("rules/test_duplicate_rule_names.yml")


@pytest.mark.asyncio
async def test_empty_rule_names():
    with pytest.raises(ValidationError):
        load_rulebook("rules/test_empty_rule_names.yml")


@pytest.mark.asyncio
async def test_missing_rule_names():
    with pytest.raises(ValidationError):
        load_rulebook("rules/test_missing_rule_names.yml")


@pytest.mark.asyncio
async def test_blank_rule_names():
    with pytest.raises(ValidationError):
        load_rulebook("rules/test_blank_rule_name.yml")
