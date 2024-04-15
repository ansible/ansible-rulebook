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

from ansible_rulebook import terminal
from ansible_rulebook.action.control import Control
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.action.run_job_template import RunJobTemplate
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    ControllerApiException,
    JobTemplateNotFoundException,
)


def _validate(queue, success, reason=None):
    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "Action":
            action = event

    assert action["action"] == "run_job_template"
    if reason:
        assert action["reason"] == reason

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
        "job_template_name",
        "matching_events",
        "url",
        "organization",
        "job_id",
    }

    if not success:
        required_keys.add("message")

    x = set(action.keys()).difference(required_keys)
    assert len(x) == 0
    return action


JOB_TEMPLATE_ERRORS = [
    ("api error", ControllerApiException("api error")),
    ("jt does not exist", JobTemplateNotFoundException("jt does not exist")),
]


@pytest.mark.parametrize("err_msg,err", JOB_TEMPLATE_ERRORS)
@pytest.mark.asyncio
async def test_run_job_template_exception(err_msg, err):
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"a": 1},
        project_data_file="",
    )
    action_args = {
        "name": "fred",
        "set_facts": True,
        "organization": "Default",
        "retries": 0,
        "retry": True,
        "delay": 0,
    }
    with patch(
        "ansible_rulebook.action.run_job_template."
        "job_template_runner.run_job_template",
        side_effect=err,
    ):
        await RunJobTemplate(metadata, control, **action_args)()
        _validate(queue, False, {"error": err_msg})


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
async def test_run_job_template(drools_call, additional_args, capsys):
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"a": 1},
        project_data_file="",
    )
    action_args = {
        "name": "fred",
        "organization": "Default",
        "retries": 0,
        "retry": True,
        "delay": 0,
    }
    action_args.update(additional_args)
    controller_job = {
        "status": "failed",
        "rc": 0,
        "artifacts": dict(b=1),
        "created": "abc",
        "id": 10,
    }
    with patch(
        "ansible_rulebook.action.run_job_template."
        "job_template_runner.run_job_template",
        return_value=controller_job,
    ):
        with patch(drools_call) as drools_mock:
            old_setting = settings.print_events
            settings.print_events = True
            try:
                await RunJobTemplate(metadata, control, **action_args)()
            finally:
                settings.print_events = old_setting
            captured = capsys.readouterr()
            drools_mock.assert_called_once()

        _validate(queue, True)
        assert terminal.Display.get_banners("job: set-facts", captured.out)


URL_PARAMETERS = [
    (None,),
    (10,),
]


@pytest.mark.parametrize("job_id", URL_PARAMETERS)
@pytest.mark.asyncio
async def test_run_job_template_url(job_id):
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"a": 1},
        project_data_file="",
    )
    action_args = {
        "name": "fred",
        "organization": "Default",
        "retries": 0,
        "retry": True,
        "delay": 0,
    }
    controller_job = {
        "status": "success",
        "rc": 0,
        "artifacts": dict(b=1),
        "created": "abc",
    }
    if job_id is not None:
        controller_job["id"] = job_id

    with patch(
        "ansible_rulebook.action.run_job_template."
        "job_template_runner.run_job_template",
        return_value=controller_job,
    ):
        await RunJobTemplate(metadata, control, **action_args)()

        action = _validate(queue, True)

        assert ((not job_id) and (action["url"] == "")) or (
            job_id and (action["url"] != "")
        )


@pytest.mark.asyncio
async def test_run_job_template_retries():
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"a": 1},
        project_data_file="",
    )
    action_args = {
        "name": "fred",
        "organization": "Default",
        "retries": 1,
        "retry": True,
        "delay": 1,
        "set_facts": True,
    }
    controller_job = [
        {
            "status": "failed",
            "rc": 0,
            "artifacts": dict(b=1),
            "created": "abc",
            "id": 10,
        },
        {
            "status": "success",
            "rc": 0,
            "artifacts": dict(b=1),
            "created": "abc",
            "id": 10,
        },
    ]

    with patch(
        "ansible_rulebook.action.run_job_template."
        "job_template_runner.run_job_template",
        side_effect=controller_job,
    ):
        with patch(
            "ansible_rulebook.action.run_job_template.lang.assert_fact"
        ) as drools_mock:
            await RunJobTemplate(metadata, control, **action_args)()
            drools_mock.assert_called_once()

        _validate(queue, True)
