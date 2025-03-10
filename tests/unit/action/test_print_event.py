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
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from ansible_rulebook.action.control import Control
from ansible_rulebook.action.helper import INTERNAL_ACTION_STATUS
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.action.print_event import PrintEvent
from ansible_rulebook.conf import settings

DUMMY_UUID = "eb7de03f-6f8f-4943-b69e-3c90db346edf"
RULE_UUID = "abcdef3f-6f8f-4943-b69e-3c90db346edf"
RULE_SET_UUID = "00aabbcc-1111-2222-b69e-3c90db346edf"
RULE_RUN_AT = "2023-06-11T12:13:10Z"
ACTION_RUN_AT = "2023-06-11T12:13:14Z"


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
async def test_print_event():
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": {"a": 1}},
        project_data_file="",
    )
    action_args = dict(pretty=True)

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        await PrintEvent(metadata, control, **action_args)()

    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "Action":
            action = event

    required_keys = {
        "action",
        "action_uuid",
        "activation_id",
        "activation_instance_id",
        "reason",
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
    assert action["action"] == "print_event"
    assert action["action_uuid"] == DUMMY_UUID
    assert action["activation_id"] == settings.identifier
    assert action["activation_instance_id"] == settings.identifier
    assert action["run_at"] == ACTION_RUN_AT
    assert action["rule_run_at"] == metadata.rule_run_at
    assert action["rule"] == metadata.rule
    assert action["ruleset"] == metadata.rule_set
    assert action["rule_uuid"] == metadata.rule_uuid
    assert action["ruleset_uuid"] == metadata.rule_set_uuid
    assert action["status"] == INTERNAL_ACTION_STATUS
    assert action["type"] == "Action"
    assert action["matching_events"] == {"m": {"a": 1}}

    assert len(set(action.keys()).difference(required_keys)) == 0


@freeze_time("2023-11-30 14:51:30")
@pytest.mark.asyncio
async def test_pretty_print_event(capsys):
    # Use a large payload so pretty printing will produce multiline output.
    payload = {
        "aaaaaaaaaaaaaaaaaaaa": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "bbbbbbbbbbbbbbbbbbbb": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "cccccccccccccccccccc": "cccccccccccccccccccccccccccccccccccccccc",
        "dddddddddddddddddddd": "dddddddddddddddddddddddddddddddddddddddd",
        "eeeeeeeeeeeeeeeeeeee": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
    }
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": payload},
        project_data_file="",
    )

    # The not pretty-printed event.
    action_args = dict(pretty=False)

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        await PrintEvent(metadata, control, **action_args)()

    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "Action":
            unpretty_action = event

    unpretty = capsys.readouterr()
    # Three lines as a result of displaying in a banner.
    assert len(unpretty.out.strip().splitlines()) == 3

    # The pretty-printed event.
    action_args = dict(pretty=True)

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        await PrintEvent(metadata, control, **action_args)()

    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "Action":
            pretty_action = event

    pretty = capsys.readouterr()
    assert len(pretty.out.strip().splitlines()) > 3

    # Assert there was no difference in content.
    assert pretty_action == unpretty_action
