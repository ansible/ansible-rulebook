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
import json

import pytest

from ansible_rulebook.engine import run_rulesets, start_source
from ansible_rulebook.exception import VarsKeyMissingException
from ansible_rulebook.messages import Shutdown
from ansible_rulebook.util import load_inventory

from .test_engine import get_queue_item, load_rulebook, validate_events


class SourceTask:
    def __init__(self, source, source_dir, variables, queue):
        self.source = source
        self.source_dir = source_dir
        self.variables = variables
        self.queue = queue

    def __enter__(self):
        self.task = asyncio.create_task(
            start_source(
                self.source, [self.source_dir], self.variables, self.queue
            )
        )
        return self.task

    def __exit__(self, *args):
        self.task.cancel()


@pytest.mark.asyncio
async def test_01_noop():
    ruleset_queues, event_log = load_rulebook("examples/01_noop.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "noop", "2"
    assert event["matching_events"] == {"m": {"i": 1}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_02_debug():
    ruleset_queues, event_log = load_rulebook("examples/02_debug.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"i": 1}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_03_print_event():
    ruleset_queues, event_log = load_rulebook("examples/03_print_event.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "print_event", "2"
    assert event["matching_events"] == {"m": {"i": 1}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_04_set_fact():
    ruleset_queues, event_log = load_rulebook("examples/04_set_fact.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "set_fact", "2"
    assert event["matching_events"] == {"m": {"i": 1}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "print_event", "4"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "6"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_05_post_event():
    ruleset_queues, event_log = load_rulebook("examples/05_post_event.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "post_event", "2"
    assert event["matching_events"] == {"m": {"i": 1}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "print_event", "4"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "6"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_06_retract_fact():
    ruleset_queues, event_log = load_rulebook("examples/06_retract_fact.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "set_fact", "2"
    assert event["matching_events"] == {"m": {"i": 1}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "retract_fact", "4"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "4"
    assert event["action"] == "debug", "5"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_07_and():
    ruleset_queues, event_log = load_rulebook("examples/07_and.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(nested=dict(i=1, j=1)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"nested": {"i": 1, "j": 1}}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_08_or():
    ruleset_queues, event_log = load_rulebook("examples/08_or.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(nested=dict(i=1, j=1)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"nested": {"i": 1, "j": 1}}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_09_gt():
    ruleset_queues, event_log = load_rulebook("examples/09_gt.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=3))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"i": 3}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_10_lt():
    ruleset_queues, event_log = load_rulebook("examples/10_lt.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"i": 1}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_11_le():
    ruleset_queues, event_log = load_rulebook("examples/11_le.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=2))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"i": 2}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_12_ge():
    ruleset_queues, event_log = load_rulebook("examples/12_ge.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=2))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"i": 2}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_13_add():
    ruleset_queues, event_log = load_rulebook("examples/13_add.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(nested=dict(i=2, j=1)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"nested": {"i": 2, "j": 1}}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_14_sub():
    ruleset_queues, event_log = load_rulebook("examples/14_sub.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(nested=dict(i=1, j=2)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m": {"nested": {"i": 1, "j": 2}}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_15_multiple_events_all():
    ruleset_queues, event_log = load_rulebook(
        "examples/15_multiple_events_all.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(nested=dict(i=1, j=0)))
    queue.put_nowait(dict(nested=dict(i=0, j=1)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {
        "m_0": {"nested": {"i": 1, "j": 0}},
        "m_1": {"nested": {"i": 0, "j": 1}},
    }, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_16_multiple_events_any():
    ruleset_queues, event_log = load_rulebook(
        "examples/16_multiple_events_any.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(nested=dict(i=1, j=0)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m_0": {"nested": {"i": 1, "j": 0}}}
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_17_multiple_sources_any():
    ruleset_queues, event_log = load_rulebook(
        "examples/17_multiple_sources_any.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(range2=dict(i=1)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {"m_0": {"i": 1}}
    event = event_log.get_nowait()
    assert event["type"] == "Action", "4"
    assert event["action"] == "debug", "5"
    assert event["matching_events"] == {"m_1": {"range2": {"i": 1}}}, "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_18_multiple_sources_all():
    ruleset_queues, event_log = load_rulebook(
        "examples/18_multiple_sources_all.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(range2=dict(i=1)))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {
        "m_0": {"i": 1},
        "m_1": {"range2": {"i": 1}},
    }, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "5"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_19_is_defined():
    ruleset_queues, event_log = load_rulebook("examples/19_is_defined.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(payload=dict(key1="value1", key2=dict(name="fred"))))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "set_fact", "2"
    assert event["matching_events"] == {"m": {"i": 1}}
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] in ["debug", "print_event"], "4"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "6"
    assert event["action"] in ["print_event", "debug"], "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "6"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_20_is_not_defined():
    ruleset_queues, event_log = load_rulebook("examples/20_is_not_defined.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "set_fact", "2"
    assert event["matching_events"] == {"m": {"i": 1}}
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "retract_fact", "4"
    assert event["matching_events"] == {"m": {"msg": "hello"}}
    event = event_log.get_nowait()
    assert event["type"] == "Action", "5"
    assert event["action"] == "debug", "6"
    assert event["matching_events"] == {"m": {"msg": "hello"}}
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


PLAYBOOK_RULES = [
    ("examples/21_run_playbook.yml", 12),
    ("examples/33_run_playbook_retry.yml", 33),
    ("examples/34_run_playbook_retries.yml", 33),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("rule, ansible_events", PLAYBOOK_RULES)
async def test_21_run_playbook(rule, ansible_events):
    ruleset_queues, event_log = load_rulebook(rule)

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory("playbooks/inventory.yml"),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Job", "0"
    ansible_event_count = 0
    while True:
        event = event_log.get_nowait()
        if event["type"] == "AnsibleEvent":
            ansible_event_count += 1
        else:
            break

    assert ansible_event_count == ansible_events
    assert event["type"] == "Action", "1"
    assert event["action"] == "run_playbook", "2"
    assert event["matching_events"] == {"m": {"i": 1}}
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_23_nested_data():
    ruleset_queues, event_log = load_rulebook("examples/23_nested_data.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(root=dict(nested=dict(i=0))))
    queue.put_nowait(dict(root=dict(nested=dict(i=1))))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["matching_events"] == {"m": {"root": {"nested": {"i": 1}}}}
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "2"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_24_max_attributes():
    ruleset_queues, event_log = load_rulebook("examples/24_max_attributes.yml")

    with open("examples/replays/24_max_attributes/00.json") as f:
        data = json.loads(f.read())

    queue = ruleset_queues[0][1]
    queue.put_nowait(data)
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "2"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_25_max_attributes_nested():
    ruleset_queues, event_log = load_rulebook(
        "examples/25_max_attributes_nested.yml"
    )

    with open("examples/replays/25_max_attributes_nested/00.json") as f:
        data = json.loads(f.read())

    queue = ruleset_queues[0][1]
    queue.put_nowait(data)
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "2"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_26_print_events():
    ruleset_queues, event_log = load_rulebook("examples/26_print_events.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(dict(i=2))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "print_event", "2"
    assert event["matching_events"] == {"m_0": {"i": 1}, "m_1": {"i": 2}}, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_27_var_root():
    ruleset_queues, event_log = load_rulebook("examples/27_var_root.yml")
    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        event = event_log.get_nowait()
        assert event["type"] == "Action", "1"
        assert event["action"] == "print_event", "2"
        assert event["matching_events"] == {
            "webhook": {"url": "http://www.example.com", "action": "merge"},
            "kafka": {"topic": "testing", "channel": "red"},
        }
        event = event_log.get_nowait()
        assert event["type"] == "Shutdown", "7"
        assert event_log.empty()


@pytest.mark.asyncio
async def test_28_right_side_condition_template():
    ruleset_queues, event_log = load_rulebook(
        "examples/28_right_side_condition_template.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait({"i": 1})
    queue.put_nowait({"i": 2})
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        {"custom": {"expected_index": 2}},
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    assert event["matching_events"] == {
        "m": {"i": 2},
    }, "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "4"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_29_run_module():
    ruleset_queues, event_log = load_rulebook("examples/29_run_module.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Job", "0"
    for i in range(4):
        assert event_log.get_nowait()["type"] == "AnsibleEvent", f"0.{i}"

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "run_module", "2"
    assert event["matching_events"] == {
        "m": {"i": 1, "meta": {"hosts": "localhost"}}
    }
    assert event["rc"] == 0, "2.1"
    assert event["status"] == "successful", "2.2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_30_run_module_missing():
    ruleset_queues, event_log = load_rulebook(
        "examples/30_run_module_missing.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Job", "0"
    for i in range(4):
        assert event_log.get_nowait()["type"] == "AnsibleEvent", f"0.{i}"

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "run_module", "2"

    assert event["rc"] == 2, "2.1"
    assert event["status"] == "failed", "2.2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_31_run_module_missing_args():
    ruleset_queues, event_log = load_rulebook(
        "examples/31_run_module_missing_args.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Job", "0"
    for i in range(4):
        assert event_log.get_nowait()["type"] == "AnsibleEvent", f"0.{i}"

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "run_module", "2"

    assert event["rc"] == 2, "2.1"
    assert event["status"] == "failed", "2.2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_32_run_module_fail():
    ruleset_queues, event_log = load_rulebook(
        "examples/32_run_module_fail.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Job", "0"
    for i in range(8):
        assert event_log.get_nowait()["type"] == "AnsibleEvent", f"0.{i}"

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "run_module", "2"

    assert event["rc"] == 2, "2.1"
    assert event["status"] == "failed", "2.2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_35_multiple_rulesets_1_fired():
    ruleset_queues, event_log = load_rulebook(
        "examples/35_multiple_rulesets_1_fired.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))

    queue = ruleset_queues[1][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))

    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    checks = {
        "max_events": 3,
        "shutdown_events": 1,
        "actions": [
            "35 multiple rulesets 1::r1::set_fact",
            "35 multiple rulesets 1::r2::noop",
        ],
    }
    validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_36_multiple_rulesets_both_fired():
    ruleset_queues, event_log = load_rulebook(
        "examples/36_multiple_rulesets_both_fired.yml"
    )

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))
    queue.put_nowait(dict(i=2, meta=dict(hosts="localhost")))

    queue = ruleset_queues[1][1]
    queue.put_nowait(dict(i=1, meta=dict(hosts="localhost")))

    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )
    checks = {
        "max_events": 3,
        "shutdown_events": 1,
        "actions": [
            "36 multiple rulesets 1::r1::set_fact",
            "36 multiple rulesets 2::r1::debug",
        ],
    }
    validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_37_hosts_facts():
    ruleset_queues, event_log = load_rulebook("examples/37_hosts_facts.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory("playbooks/inventory.yml"),
    )

    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_38_shutdown_action():
    ruleset_queues, event_log = load_rulebook("examples/38_shutdown.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(dict(i=1))

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        load_inventory("playbooks/inventory.yml"),
    )
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "shutdown", "1"
    assert event["message"] == "My rule has triggered a shutdown"
    assert event["delay"] == 1.1845
    assert event["ruleset"] == "Test shutdown action"
    assert event["rule"] == "Host 1 rule"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "2"


@pytest.mark.asyncio
async def test_40_in():
    ruleset_queues, event_log = load_rulebook("examples/40_in.yml")
    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "40 in::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_41_not_in():
    ruleset_queues, event_log = load_rulebook("examples/41_not_in.yml")
    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "41 not in::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_42_contains():
    ruleset_queues, event_log = load_rulebook("examples/42_contains.yml")
    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "42 contains::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_43_not_contains():
    ruleset_queues, event_log = load_rulebook("examples/43_not_contains.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "43 not contains::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_44_in_and():
    ruleset_queues, event_log = load_rulebook("examples/44_in_and.yml")
    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "44 in and::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_45_in_or():
    ruleset_queues, event_log = load_rulebook("examples/45_in_or.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 5,
            "shutdown_events": 1,
            "actions": [
                "45 in or::r1::debug",
                "45 in or::r1::debug",
                "45 in or::r1::debug",
                "45 in or::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_47_generic_plugin():
    ruleset_queues, event_log = load_rulebook("examples/47_generic_plugin.yml")
    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 3,
            "shutdown_events": 1,
            "actions": [
                "47 Generic Plugin::r1::print_event",
                "47 Generic Plugin::r2::print_event",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_48_echo():
    ruleset_queues, event_log = load_rulebook("examples/48_echo.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "48 echo::r1::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_49_float():
    ruleset_queues, event_log = load_rulebook("examples/49_float.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        event = event_log.get_nowait()
        assert event["type"] == "Action", "1"
        assert event["action"] == "debug", "1"
        assert event["matching_events"] == {"m": {"pi": 3.14159}}, "3"
        event = event_log.get_nowait()
        assert event["type"] == "Action", "3"
        assert event["action"] == "debug", "4"
        assert event["matching_events"] == {"m": {"mass": 5.97219}}, "5"
        event = event_log.get_nowait()
        assert event["type"] == "Shutdown", "7"


@pytest.mark.asyncio
async def test_50_negation():
    ruleset_queues, event_log = load_rulebook("examples/50_negation.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        event = event_log.get_nowait()
        assert event["type"] == "Action", "1"
        assert event["action"] == "print_event", "1"
        assert event["matching_events"] == {"m": {"b": False}}, "1"
        event = event_log.get_nowait()
        assert event["type"] == "Action", "3"
        assert event["action"] == "print_event", "3"
        assert event["matching_events"] == {"m": {"bt": True}}, "3"
        event = event_log.get_nowait()
        assert event["type"] == "Action", "5"
        assert event["action"] == "print_event", "5"
        assert event["matching_events"] == {"m": {"i": 10}}, "5"
        event = event_log.get_nowait()
        assert event["type"] == "Action", "6"
        assert event["action"] == "print_event", "6"
        assert event["matching_events"] == {"m": {"msg": "Fred"}}, "6"
        event = event_log.get_nowait()
        assert event["type"] == "Action", "7"
        assert event["action"] == "print_event", "7"
        assert event["matching_events"] == {"m": {"j": 9}}, "7"
        event = event_log.get_nowait()
        assert event["type"] == "Shutdown", "8"


@pytest.mark.asyncio
async def test_51_vars_namespace():
    ruleset_queues, event_log = load_rulebook("examples/51_vars_namespace.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        years = [2001, 2002, 2003, 2004]
        address = dict(
            street="123 Any Street",
            city="Bedrock",
            state="NJ",
            years_active=years,
        )
        person = dict(
            person=dict(
                age=45,
                name="Fred Flintstone",
                active=True,
                reliability=86.9,
                address=address,
            )
        )

        await run_rulesets(
            event_log,
            ruleset_queues,
            person,
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 6,
            "shutdown_events": 1,
            "actions": [
                "51 vars namespace::str_test::echo",
                "51 vars namespace::list_test::echo",
                "51 vars namespace::bool_test::echo",
                "51 vars namespace::int_test::echo",
                "51 vars namespace::float_test::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_51_vars_namespace_missing_key():
    ruleset_queues, event_log = load_rulebook("examples/51_vars_namespace.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        years = [2001, 2002, 2003, 2004]
        address = dict(
            street="123 Any Street",
            city="Bedrock",
            state="NJ",
            years_active=years,
        )
        person = dict(
            person=dict(
                name="Fred Flintstone",
                active=True,
                reliability=86.9,
                address=address,
            )
        )

        with pytest.raises(VarsKeyMissingException) as exc_info:
            await run_rulesets(
                event_log,
                ruleset_queues,
                person,
                load_inventory("playbooks/inventory.yml"),
            )
        assert str(exc_info.value) == "vars does not contain key: person.age"


@pytest.mark.asyncio
async def test_52_once_within():
    ruleset_queues, event_log = load_rulebook("examples/52_once_within.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 3,
            "shutdown_events": 1,
            "actions": [
                "52 once within::r1::debug",
                "52 once within::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_53_once_within_multiple_hosts():
    ruleset_queues, event_log = load_rulebook(
        "examples/53_once_within_multiple_hosts.yml"
    )

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 3,
            "shutdown_events": 1,
            "actions": [
                "53 once within multiple hosts::r1::debug",
                "53 once within multiple hosts::r1::debug",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
@pytest.mark.temporal
@pytest.mark.long_run
async def test_54_time_window():
    ruleset_queues, event_log = load_rulebook("examples/54_time_window.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        event = await get_queue_item(event_log, 10, 2)
        assert event["type"] == "Action", "1"
        assert event["action"] == "print_event", "1"
        assert event["matching_events"] == {
            "m_1": {
                "alert": {"code": 1002, "message": "Restarted"},
                "event_index": 1,
            },
            "m_0": {
                "alert": {"code": 1001, "message": "Applying maintenance"},
                "event_index": 0,
            },
        }
        event = event_log.get_nowait()
        assert event["type"] == "Shutdown", "6"


@pytest.mark.asyncio
@pytest.mark.temporal
@pytest.mark.long_run
async def test_55_not_all():
    ruleset_queues, event_log = load_rulebook("examples/55_not_all.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 3,
            "shutdown_events": 1,
            "actions": [
                "55 not all::maint failed::echo",
                "55 not all::maint failed::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
@pytest.mark.temporal
@pytest.mark.long_run
async def test_56_once_after():
    ruleset_queues, event_log = load_rulebook("examples/56_once_after.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "56 once after::r1::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
@pytest.mark.temporal
@pytest.mark.long_run
async def test_57_once_after_multiple():
    ruleset_queues, event_log = load_rulebook(
        "examples/57_once_after_multi.yml"
    )

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 7,
            "shutdown_events": 1,
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_58_string_search():
    ruleset_queues, event_log = load_rulebook("examples/58_string_search.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 7,
            "shutdown_events": 1,
            "actions": [
                "58 String search::match::echo",
                "58 String search::search::echo",
                "58 String search::regex::echo",
                "58 String search::not match::echo",
                "58 String search::not search::echo",
                "58 String search::not regex::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_59_multiple_actions():
    ruleset_queues, event_log = load_rulebook(
        "examples/59_multiple_actions.yml"
    )

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )
        checks = {
            "max_events": 6,
            "shutdown_events": 1,
            "actions": [
                "59 Multiple Actions::r1::debug",
                "59 Multiple Actions::r1::print_event",
                "59 Multiple Actions::r1::echo",
                "59 Multiple Actions::r1::echo",
                "59 Multiple Actions::r2::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_60_json_filter():
    ruleset_queues, event_log = load_rulebook("examples/60_json_filter.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "60 json filter::r1::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_61_select_1():
    ruleset_queues, event_log = load_rulebook("examples/61_select_1.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "61 select 1::r1::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_62_select_2():
    ruleset_queues, event_log = load_rulebook("examples/62_select_2.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 4,
            "shutdown_events": 1,
            "actions": [
                "62 select 2::r1::echo",
                "62 select 2::r2::echo",
                "62 select 2::r1::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_63_selectattr_1():
    ruleset_queues, event_log = load_rulebook("examples/63_selectattr_1.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 3,
            "shutdown_events": 1,
            "actions": [
                "63 selectattr 1::r1::echo",
                "63 selectattr 1::r2::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_64_selectattr_2():
    ruleset_queues, event_log = load_rulebook("examples/64_selectattr_2.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "64 selectattr 2::r1::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_65_selectattr_3():
    ruleset_queues, event_log = load_rulebook("examples/65_selectattr_3.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "65 selectattr 3::r1::echo",
            ],
        }
        validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_68_disabled_rule():
    ruleset_queues, event_log = load_rulebook("examples/68_disabled_rule.yml")

    queue = ruleset_queues[0][1]
    rs = ruleset_queues[0][0]
    with SourceTask(rs.sources[0], "sources", {}, queue):
        await run_rulesets(
            event_log,
            ruleset_queues,
            dict(),
            load_inventory("playbooks/inventory.yml"),
        )

        checks = {
            "max_events": 2,
            "shutdown_events": 1,
            "actions": [
                "68 disabled rule::r1::echo",
            ],
        }
        validate_events(event_log, **checks)
