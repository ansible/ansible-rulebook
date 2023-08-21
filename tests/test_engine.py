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
import tempfile
from pprint import pprint
from unittest.mock import patch

import pytest
import yaml
from freezegun import freeze_time
from jsonschema.exceptions import ValidationError

from ansible_rulebook.engine import run_rulesets, start_source
from ansible_rulebook.exception import (
    RulenameDuplicateException,
    SourceFilterNotFoundException,
    SourcePluginMainMissingException,
    SourcePluginNotAsyncioCompatibleException,
    SourcePluginNotFoundException,
)
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.rule_types import EventSource, EventSourceFilter
from ansible_rulebook.rules_parser import parse_rule_sets
from ansible_rulebook.validators import Validate


class TimedOutException(Exception):
    pass


HERE = os.path.dirname(os.path.abspath(__file__))


DUMMY_UUID = "eb7de03f-6f8f-4943-b69e-3c90db346edf"


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


async def get_queue_item(queue, timeout=0.5, times=1):
    for _ in range(times):
        try:
            item = queue.get_nowait()
        except asyncio.QueueEmpty:
            await asyncio.sleep(timeout)
            continue
        if item:
            return item
    return None


async def validate_events(event_log, **kwargs):
    shutdown_events = 0
    job_events = 0
    ansible_events = 0
    action_events = 0
    actions = []
    max_events = 0

    while True:
        if event_log.empty() and kwargs.get("drain_event_log", False):
            break
        if "max_events" in kwargs and kwargs["max_events"] == max_events:
            break
        if "timeout" in kwargs:
            event = await get_queue_item(event_log, kwargs["timeout"])
            if not event:
                raise TimedOutException(
                    "Validate events, failed no event received"
                )
        else:
            event = event_log.get_nowait()

        max_events += 1
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


test_data = [
    ("range", "noop", "Source range initiated shutdown at"),
    (
        "ansible.eda.range",
        "ansible.eda.noop",
        "Source ansible.eda.range initiated shutdown at",
    ),
]


@freeze_time("2023-03-23 11:11:11")
@pytest.mark.parametrize(
    "source_name,filter_name, shutdown_message", test_data
)
@pytest.mark.asyncio
async def test_start_source(source_name, filter_name, shutdown_message):
    os.chdir(HERE)
    meta = {
        "source": {"name": source_name, "type": source_name},
        "received_at": "2023-03-23T11:11:11Z",
        "uuid": DUMMY_UUID,
    }
    queue = asyncio.Queue()
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        await start_source(
            EventSource(
                source_name,
                source_name,
                dict(limit=1),
                [EventSourceFilter(filter_name, {})],
            ),
            ["sources"],
            dict(limit=1),
            queue,
        )
        assert queue.get_nowait() == dict(i=0, meta=meta)
        last = await queue.get()
        assert shutdown_message in last.message


test_data = [
    ("missing", "noop", "sources", SourcePluginNotFoundException),
    ("range", "missing", "sources", SourceFilterNotFoundException),
    ("bad_source", "noop", "data", SourcePluginMainMissingException),
    ("not_asyncio", "noop", "data", SourcePluginNotAsyncioCompatibleException),
]


@pytest.mark.parametrize("source_name,filter_name,source_dir,ex", test_data)
@pytest.mark.asyncio
async def test_start_source_exceptions(
    source_name, filter_name, source_dir, ex
):
    os.chdir(HERE)

    queue = asyncio.Queue()
    with pytest.raises(ex):
        await start_source(
            EventSource(
                source_name,
                source_name,
                dict(limit=1),
                [EventSourceFilter(filter_name, {})],
            ),
            [source_dir],
            dict(limit=1),
            queue,
        )


source_args = dict(
    loop_count=-1, event_delay=1, startup_delay=30, payload=dict(i=1)
)
test_data = [
    ("generic", "noop", "sources", source_args),
]


@pytest.mark.parametrize("source_name,filter_name,source_dir,args", test_data)
@pytest.mark.asyncio
async def test_start_source_with_args(
    source_name, filter_name, source_dir, args
):
    os.chdir(HERE)

    queue = asyncio.Queue()
    task = asyncio.create_task(
        start_source(
            EventSource(
                source_name,
                source_name,
                args,
                [EventSourceFilter(filter_name, {})],
            ),
            [source_dir],
            args,
            queue,
        )
    )
    await asyncio.sleep(0.02)
    task.cancel()
    last = await queue.get()
    assert (
        f"Source {source_name} task cancelled, initiated shutdown at"
        in last.message
    )


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
        "playbooks/inventory.yml",
    )

    checks = {
        "max_events": 18,
        "shutdown_events": 1,
        "job_events": 1,
        "ansible_events": 9,
        "action_events": 6,
    }
    await validate_events(event_log, **checks)


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
        event_log, ruleset_queues, dict(), "playbooks/inventory.yml"
    )

    assert event_log.get_nowait()["type"] == "Action", "0"
    assert event_log.get_nowait()["type"] == "Action", "0.2"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.4"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.5"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.6"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.7"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.8"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.9"
    assert event_log.get_nowait()["type"] == "Action", "2.0"
    assert event_log.get_nowait()["type"] == "Action", "2.1"
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
        "playbooks/inventory1.yml",
    )

    checks = {
        "max_events": 21,
        "shutdown_events": 1,
        "job_events": 1,
        "ansible_events": 13,
        "action_events": 6,
    }
    await validate_events(event_log, **checks)


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
        "playbooks/inventory1.yml",
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
        "playbooks/inventory.yml",
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
        event_log, ruleset_queues, dict(), "playbooks/inventory.yml"
    )

    assert event_log.get_nowait()["type"] == "Action", "0"
    assert event_log.get_nowait()["type"] == "Action", "0.2"
    assert event_log.get_nowait()["type"] == "Job", "1.0"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.1"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.2"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.3"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.4"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.5"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.6"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.7"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.8"
    assert event_log.get_nowait()["type"] == "AnsibleEvent", "1.9"
    assert event_log.get_nowait()["type"] == "Action", "2.0"
    assert event_log.get_nowait()["type"] == "Action", "2.1"
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
        "playbooks/inventory1.yml",
    )

    checks = {
        "max_events": 18,
        "shutdown_events": 1,
        "job_events": 1,
        "ansible_events": 9,
        "action_events": 6,
    }
    await validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_run_assert_facts():
    ruleset_queues, event_log = load_rulebook("rules/test_set_facts.yml")
    inventory = dict(
        all=dict(hosts=dict(localhost=dict(ansible_connection="local")))
    )
    with tempfile.NamedTemporaryFile(mode="w+") as temp:
        temp.write(yaml.dump(inventory))
        temp.flush()
        queue = ruleset_queues[0][1]
        queue.put_nowait(dict())
        queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))
        queue.put_nowait(Shutdown())
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(Naboo="naboo"),
            temp.name,
        )

        assert event_log.get_nowait()["type"] == "EmptyEvent", "0"
        assert event_log.get_nowait()["type"] == "Action", "0.1"
        assert event_log.get_nowait()["type"] == "Job", "1.0"
        for i in range(47):
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
