#  Copyright 2023 Red Hat, Inc.
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
from unittest.mock import AsyncMock, patch

import pytest
from aiokafka.errors import KafkaError
from freezegun import freeze_time

from ansible_rulebook.action.control import Control
from ansible_rulebook.action.kafka_notify import KafkaNotify
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.conf import settings

SUCCESSFUL_STATUS = "successful"
FAILED_STATUS = "failed"

DUMMY_UUID = "eb7de03f-6f8f-4943-b69e-3c90db346edf"
RULE_UUID = "abcdef3f-6f8f-4943-b69e-3c90db346edf"
RULE_SET_UUID = "00aabbcc-1111-2222-b69e-3c90db346edf"
RULE_RUN_AT = "2023-06-11T12:13:10Z"
ACTION_RUN_AT = "2023-06-11T12:13:14Z"
REQUIRED_KEYS = {
    "action",
    "action_uuid",
    "activation_id",
    "activation_instance_id",
    "message",
    "rule_run_at",
    "run_at",
    "rule",
    "ruleset",
    "rule_uuid",
    "ruleset_uuid",
    "status",
    "type",
    "matching_events",
}


def _validate(queue, metadata, status, event, message=None):
    while not queue.empty():
        data = queue.get_nowait()
        if data["type"] == "Action":
            action = data

    assert action["action"] == "kafka_notify"
    assert action["action_uuid"] == DUMMY_UUID
    assert action["activation_id"] == settings.identifier
    assert action["rule_run_at"] == metadata.rule_run_at
    assert action["rule"] == metadata.rule
    assert action["ruleset"] == metadata.rule_set
    assert action["rule_uuid"] == metadata.rule_uuid
    assert action["ruleset_uuid"] == metadata.rule_set_uuid
    assert action["status"] == status
    assert action["type"] == "Action"
    if action["status"] == SUCCESSFUL_STATUS:
        assert action["run_at"] == ACTION_RUN_AT
        assert action["matching_events"] == event
    assert action.get("message", None) == message
    assert len(set(action.keys()).difference(REQUIRED_KEYS)) == 0


TEST_PAYLOADS = [
    ({"abc": "def", "simple": True, "pi": 3.14259}),
    ({"abc": "def", "simple": True, "pi": 3.14259, "meta": {"uuid": 1}},),
    ({"a": 1, "blob": "x" * 9000, "y": 365, "phased": True},),
]


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
@pytest.mark.parametrize("event", TEST_PAYLOADS)
async def test_kafka_notify(event):
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )
    topic = "my_chanel"
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": event},
        project_data_file="",
    )

    connection = {"bootstrap_servers": "localhost:9002"}
    action_args = {
        "connection": connection,
        "event": event,
        "topic": topic,
    }
    if "meta" in event:
        action_args["remove_meta"] = True
        compared_event = event.copy()
        compared_event.pop("meta")
    else:
        compared_event = event

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        with patch(
            "ansible_rulebook.action.kafka_notify.AIOKafkaProducer",
            return_value=AsyncMock(),
        ):
            await KafkaNotify(metadata, control, **action_args)()
            _validate(queue, metadata, "successful", {"m": event})


EXCEPTIONAL_PAYLOADS = [
    (
        {"abc": "will fail"},
        {"message": "KafkaError: Kaboom", "exception": KafkaError("Kaboom")},
    ),
]


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
@pytest.mark.parametrize("event,result", EXCEPTIONAL_PAYLOADS)
async def test_kafka_notify_with_exception(event, result):
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )
    topic = "my_chanel"
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": event},
        project_data_file="",
    )

    connection = {"bootstrap_servers": "localhost:9002"}
    action_args = {
        "connection": connection,
        "event": event,
        "topic": topic,
    }

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        with pytest.raises(KafkaError):
            with patch(
                "ansible_rulebook.action.kafka_notify.AIOKafkaProducer",
                return_value=AsyncMock(),
            ) as producer:
                producer.side_effect = result["exception"]
                await KafkaNotify(metadata, control, **action_args)()

    _validate(queue, metadata, "failed", {"m": event}, result["message"])
