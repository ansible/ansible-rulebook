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
import json
from unittest.mock import MagicMock, patch

import pytest
from freezegun import freeze_time
from psycopg import OperationalError

from ansible_rulebook.action.control import Control
from ansible_rulebook.action.helper import FAILED_STATUS, SUCCESSFUL_STATUS
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.action.pg_notify import (
    MESSAGE_CHUNK,
    MESSAGE_CHUNK_COUNT,
    MESSAGE_CHUNKED_UUID,
    PGNotify,
)
from ansible_rulebook.conf import settings

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


class AsyncContextManager:
    async def __aenter__(self):
        return self

    async def __aexit__(self):
        pass


def _validate(queue, metadata, status, event, message=None):
    while not queue.empty():
        data = queue.get_nowait()
        if data["type"] == "Action":
            action = data

    assert action["action"] == "pg_notify"
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
    ({"abc": "def", "simple": True, "pi": 3.14259}, {"notifies": 1}),
    (
        {"abc": "def", "simple": True, "pi": 3.14259, "meta": {"uuid": 1}},
        {"notifies": 1},
    ),
    (
        {"a": 1, "blob": "x" * 9000, "y": 365, "phased": True},
        {"notifies": 2, "number_of_chunks": 2},
    ),
]


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
@pytest.mark.parametrize("event,result", TEST_PAYLOADS)
async def test_pg_notify(event, result):
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )
    channel_name = "my_chanel"
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": event},
        project_data_file="",
    )

    dsn = "host=localhost port=5432 dbname=mydb connect_timeout=10"
    action_args = {
        "dsn": dsn,
        "event": event,
        "channel": channel_name,
    }
    notifies = 0
    if "meta" in event:
        action_args["remove_meta"] = True
        compared_event = event.copy()
        compared_event.pop("meta")
    else:
        compared_event = event

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        with patch(
            "ansible_rulebook.action.pg_notify." "AsyncConnection.connect",
            return_value=MagicMock(AsyncContextManager()),
        ) as conn:
            if "exception" in result:
                conn.side_effect = result["exception"]
            with patch(
                "ansible_rulebook.action.pg_notify.AsyncClientCursor",
                new=MagicMock(AsyncContextManager()),
            ) as cursor:
                await PGNotify(metadata, control, **action_args)()
                conn.assert_called_once_with(conninfo=dsn, autocommit=True)
                conn.assert_called_once()
                assert len(cursor.mock_calls) == 3 + result["notifies"]
                entire_msg = ""
                for c in cursor.mock_calls:
                    if len(c.args) == 1 and type(c.args[0]) == str:
                        notifies += 1
                        parts = c.args[0].split(" ", 2)
                        assert len(parts) == 3
                        assert parts[0] == "NOTIFY"
                        assert parts[1].strip(",") == channel_name
                        payload = json.loads(parts[2][1:-2])
                        if MESSAGE_CHUNKED_UUID in payload:
                            assert (
                                payload[MESSAGE_CHUNK_COUNT]
                                == result["number_of_chunks"]
                            )
                            entire_msg += payload[MESSAGE_CHUNK]
                        else:
                            entire_msg = parts[2][1:-2]

                assert notifies == result["notifies"]
                assert json.loads(entire_msg) == compared_event
                _validate(queue, metadata, SUCCESSFUL_STATUS, {"m": event})


EXCEPTIONAL_PAYLOADS = [
    (
        {"abc": "will fail"},
        {"message": "Kaboom", "exception": OperationalError("Kaboom")},
    ),
]


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
@pytest.mark.parametrize("event,result", EXCEPTIONAL_PAYLOADS)
async def test_pg_notify_with_exception(event, result):
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )
    channel_name = "my_chanel"
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": event},
        project_data_file="",
    )

    dsn = "host=localhost port=5432 dbname=mydb connect_timeout=10"
    action_args = {
        "dsn": dsn,
        "event": event,
        "channel": channel_name,
    }

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        with pytest.raises(OperationalError):
            with patch(
                "ansible_rulebook.action.pg_notify." "AsyncConnection.connect",
                return_value=MagicMock(AsyncContextManager()),
            ) as conn:
                conn.side_effect = result["exception"]
                await PGNotify(metadata, control, **action_args)()

    _validate(queue, metadata, FAILED_STATUS, {"m": event}, result["message"])


@pytest.mark.asyncio
async def test_pg_notify_with_no_event():
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )
    channel_name = "my_chanel"
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": {}},
        project_data_file="",
    )

    dsn = "host=localhost port=5432 dbname=mydb connect_timeout=10"
    action_args = {
        "dsn": dsn,
        "event": {},
        "channel": channel_name,
    }

    await PGNotify(metadata, control, **action_args)()
    assert queue.empty()
