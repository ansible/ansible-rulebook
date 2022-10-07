import json
import os

import pytest

from ansible_events.engine import run_rulesets
from ansible_events.messages import Shutdown
from ansible_events.util import load_inventory

from .test_engine import load_rules


@pytest.mark.asyncio
async def test_01_noop():
    ruleset_queues, event_log = load_rules("examples/01_noop.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "1"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_02_debug():
    ruleset_queues, event_log = load_rules("examples/02_debug.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "1"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_03_print_event():
    ruleset_queues, event_log = load_rules("examples/03_print_event.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "1"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_04_assert_fact():
    ruleset_queues, event_log = load_rules("examples/04_assert_fact.yml")

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
    assert event["action"] == "assert_fact", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "print_event", "4"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "5"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "6"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_05_post_event():
    ruleset_queues, event_log = load_rules("examples/05_post_event.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "print_event", "4"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "5"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "6"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_06_retract_fact():
    ruleset_queues, event_log = load_rules("examples/06_retract_fact.yml")

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
    assert event["action"] == "assert_fact", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "retract_fact", "4"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "4"
    assert event["action"] == "debug", "5"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_07_and():
    ruleset_queues, event_log = load_rules("examples/07_and.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_08_or():
    ruleset_queues, event_log = load_rules("examples/08_or.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_09_gt():
    ruleset_queues, event_log = load_rules("examples/09_gt.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_10_lt():
    ruleset_queues, event_log = load_rules("examples/10_lt.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_11_le():
    ruleset_queues, event_log = load_rules("examples/11_le.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_12_ge():
    ruleset_queues, event_log = load_rules("examples/12_ge.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_13_add():
    ruleset_queues, event_log = load_rules("examples/13_add.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_14_sub():
    ruleset_queues, event_log = load_rules("examples/14_sub.yml")

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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_15_multiple_events_all():
    ruleset_queues, event_log = load_rules(
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
    assert event["type"] == "ProcessedEvent", "0"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_16_multiple_events_any():
    ruleset_queues, event_log = load_rules(
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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_17_multiple_sources_any():
    ruleset_queues, event_log = load_rules(
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
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "3"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "4"
    assert event["action"] == "debug", "5"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_18_multiple_sources_all():
    ruleset_queues, event_log = load_rules(
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
    assert event["type"] == "ProcessedEvent", "0"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "3"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_19_is_defined():
    ruleset_queues, event_log = load_rules("examples/19_is_defined.yml")

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
    assert event["action"] == "assert_fact", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "debug", "4"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "5"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "6"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_20_is_not_defined():
    ruleset_queues, event_log = load_rules("examples/20_is_not_defined.yml")

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
    assert event["action"] == "assert_fact", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "3"
    assert event["action"] == "retract_fact", "4"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "5"
    assert event["action"] == "debug", "6"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


PLAYBOOK_RULES = [
    "examples/21_run_playbook.yml",
    "examples/33_run_playbook_retry.yml",
    "examples/34_run_playbook_retries.yml",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("rule", PLAYBOOK_RULES)
async def test_21_run_playbook(rule):
    ruleset_queues, event_log = load_rules(rule)

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
    assert event["type"] == "Job", "0"
    for i in range(4):
        assert event_log.get_nowait()["type"] == "AnsibleEvent", f"0.{i}"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "run_playbook", "2"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_23_nested_data():
    ruleset_queues, event_log = load_rules("examples/23_nested_data.yml")

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
    assert event["type"] == "ProcessedEvent", "0"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "2"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_24_max_attributes():
    ruleset_queues, event_log = load_rules("examples/24_max_attributes.yml")

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
    assert event["type"] == "ProcessedEvent", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "2"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_25_max_attributes_nested():
    ruleset_queues, event_log = load_rules(
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
    assert event["type"] == "ProcessedEvent", "2"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "2"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_26_print_events():
    ruleset_queues, event_log = load_rules("examples/26_print_events.yml")

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

    event_log.get_nowait()
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "print_event", "2"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "1"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_27_var_root():
    ruleset_queues, event_log = load_rules("examples/27_var_root.yml")

    queue = ruleset_queues[0][1]
    queue.put_nowait(
        dict(
            webhook=dict(
                payload=dict(url="http://www.example.com", action="merge")
            )
        )
    )
    queue.put_nowait(
        dict(kafka=dict(message=dict(topic="testing", channel="red")))
    )
    queue.put_nowait(Shutdown())

    await run_rulesets(
        event_log,
        ruleset_queues,
        dict(),
        dict(),
    )

    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "0"
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "print_event", "2"

    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "6"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.skipif(
    os.environ.get("RULES_ENGINE", "drools") == "drools",
    reason="durable rules only test, issues with jinja substitution",
)
@pytest.mark.asyncio
async def test_28_right_side_condition_template():
    ruleset_queues, event_log = load_rules(
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

    event_log.get_nowait()
    event = event_log.get_nowait()
    assert event["type"] == "Action", "1"
    assert event["action"] == "debug", "2"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "1"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "7"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_29_run_module():
    ruleset_queues, event_log = load_rules("examples/29_run_module.yml")

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

    assert event["rc"] == 0, "2.1"
    assert event["status"] == "successful", "2.2"
    event = event_log.get_nowait()
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_30_run_module_missing():
    ruleset_queues, event_log = load_rules(
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
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_31_run_module_missing_args():
    ruleset_queues, event_log = load_rules(
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
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_32_run_module_fail():
    ruleset_queues, event_log = load_rules("examples/32_run_module_fail.yml")

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
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()


@pytest.mark.asyncio
async def test_35_multiple_rulesets_1_fired():
    ruleset_queues, event_log = load_rules(
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
        "max_events": 5,
        "processed_events": 2,
        "shutdown_events": 1,
        "actions": ["assert_fact", "noop"],
    }
    validate_events(event_log, **checks)


@pytest.mark.asyncio
async def test_36_multiple_rulesets_both_fired():
    ruleset_queues, event_log = load_rules(
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
        "max_events": 6,
        "processed_events": 3,
        "shutdown_events": 1,
        "actions": ["assert_fact", "debug"],
    }
    validate_events(event_log, **checks)


def validate_events(event_log, **kwargs):
    processed_events = 0
    shutdown_events = 0
    actions = []

    for _ in range(kwargs["max_events"]):
        event = event_log.get_nowait()
        print(event)
        if event["type"] == "ProcessedEvent":
            processed_events += 1
        elif event["type"] == "Action":
            actions.append(event["action"])
        elif event["type"] == "Shutdown":
            shutdown_events += 1

    assert event_log.empty()
    if "actions" in kwargs:
        assert kwargs["actions"] == actions
    if "processed_events" in kwargs:
        assert kwargs["processed_events"] == processed_events
    if "shutdown_events" in kwargs:
        assert kwargs["shutdown_events"] == shutdown_events


@pytest.mark.skipif(
    os.environ.get("RULES_ENGINE", "durable_rules") == "durable_rules",
    reason="durable rules does not support more than 255 keys in facts",
)
@pytest.mark.asyncio
async def test_37_hosts_facts():
    ruleset_queues, event_log = load_rules("examples/37_hosts_facts.yml")

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
    assert event["type"] == "ProcessedEvent", "7"
    event = event_log.get_nowait()
    assert event["type"] == "Shutdown", "8"
    assert event_log.empty()
