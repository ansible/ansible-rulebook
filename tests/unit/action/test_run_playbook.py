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
import os
from unittest.mock import patch

import pytest
from freezegun import freeze_time

from ansible_rulebook import terminal
from ansible_rulebook.action.control import Control
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.action.run_playbook import RunPlaybook
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import PlaybookNotFoundException

DUMMY_UUID = "eb7de03f-6f8f-4943-b69e-3c90db346edf"
RULE_UUID = "abcdef3f-6f8f-4943-b69e-3c90db346edf"
RULE_SET_UUID = "00aabbcc-1111-2222-b69e-3c90db346edf"
RULE_RUN_AT = "2023-06-11T12:13:10Z"
ACTION_RUN_AT = "2023-06-11T12:13:14Z"
HERE = os.path.dirname(os.path.abspath(__file__))
INVENTORY_FILE = os.path.join(HERE, "../../playbooks/inventory.yml")


def _validate(queue, metadata, status, rc):
    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "Action":
            action = event

    required_keys = {
        "action",
        "action_uuid",
        "activation_id",
        "activation_instance_id",
        "ansible_rulebook_id",
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
        "job_id",
        "playbook_name",
        "rc",
    }
    assert action["action"] == "run_playbook"
    assert action["action_uuid"] == DUMMY_UUID
    assert action["activation_instance_id"] == settings.identifier
    assert action["run_at"] == ACTION_RUN_AT
    assert action["rule_run_at"] == metadata.rule_run_at
    assert action["rule"] == metadata.rule
    assert action["ruleset"] == metadata.rule_set
    assert action["rule_uuid"] == metadata.rule_uuid
    assert action["ruleset_uuid"] == metadata.rule_set_uuid
    assert action["status"] == status
    assert action["rc"] == rc
    assert action["type"] == "Action"
    assert action["matching_events"] == {"m": {"a": 1}}

    assert len(set(action.keys()).difference(required_keys)) == 0


HERE = os.path.dirname(os.path.abspath(__file__))

DROOLS_CALLS = [
    (
        "ansible_rulebook.action.run_job_template.lang.assert_fact",
        dict(set_facts=True),
    ),
    (
        "ansible_rulebook.action.run_job_template.lang.post",
        dict(post_events=True),
    ),
]


@pytest.mark.parametrize("drools_call,additional_args", DROOLS_CALLS)
@pytest.mark.asyncio
@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
async def test_run_playbook(drools_call, additional_args, capsys):
    os.chdir(HERE)
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
        inventory=INVENTORY_FILE,
        hosts=["all"],
        variables={"event": {"a": 1}},
        project_data_file="",
    )
    action_args = {
        "ruleset": metadata.rule_set,
        "name": "./playbooks/rule_name.yml",
    }
    action_args.update(additional_args)

    set_fact_args = {
        "results": {
            "my_rule_name": metadata.rule,
            "my_rule_set_name": metadata.rule_set,
        },
        "meta": {
            "source": {"name": "run_playbook", "type": "internal"},
            "received_at": ACTION_RUN_AT,
            "uuid": DUMMY_UUID,
        },
    }

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        with patch(drools_call) as drools_mock:
            old_setting = settings.print_events
            settings.print_events = True
            try:
                await RunPlaybook(metadata, control, **action_args)()
            finally:
                settings.print_events = old_setting
            captured = capsys.readouterr()
            drools_mock.assert_called_once_with(
                action_args["ruleset"], set_fact_args
            )

    _validate(queue, metadata, "successful", 0)
    assert terminal.Display.get_banners("playbook: set-facts", captured.out)


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
async def test_run_playbook_missing():
    os.chdir(HERE)
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
        inventory=INVENTORY_FILE,
        hosts=["all"],
        variables={"event": {"a": 1}},
        project_data_file="",
    )
    action_args = {
        "ruleset": metadata.rule_set,
        "name": "./playbooks/does_not_exist.yml",
        "set_facts": True,
    }

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        with pytest.raises(PlaybookNotFoundException):
            await RunPlaybook(metadata, control, **action_args)()


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
async def test_run_playbook_fail():
    os.chdir(HERE)
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
        inventory=INVENTORY_FILE,
        hosts=["all"],
        variables={"event": {"a": 1}},
        project_data_file="",
    )
    action_args = {
        "ruleset": metadata.rule_set,
        "name": "./playbooks/fail.yml",
        "set_facts": True,
    }

    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        await RunPlaybook(metadata, control, **action_args)()

    _validate(queue, metadata, "failed", 2)
