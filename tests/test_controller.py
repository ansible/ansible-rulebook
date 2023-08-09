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
import json

import pytest
from aiohttp import ClientError
from aioresponses import aioresponses

from ansible_rulebook.exception import (
    ControllerApiException,
    JobTemplateNotFoundException,
    WorkflowJobTemplateNotFoundException,
)

from .data.awx_test_data import (
    JOB_1_RUNNING,
    JOB_1_SLUG,
    JOB_1_SUCCESSFUL,
    JOB_TEMPLATE_1_LAUNCH_SLUG,
    JOB_TEMPLATE_2_LAUNCH_SLUG,
    JOB_TEMPLATE_NAME_1,
    JOB_TEMPLATE_POST_RESPONSE,
    NO_JOB_TEMPLATE_PAGE1_RESPONSE,
    ORGANIZATION_NAME,
    UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
    UNIFIED_JOB_TEMPLATE_PAGE1_SLUG,
    UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
    UNIFIED_JOB_TEMPLATE_PAGE2_SLUG,
)

CONFIG_SLUG = "/api/v2/config/"


@pytest.fixture
def mocked_job_template_runner():
    from ansible_rulebook.job_template_runner import job_template_runner

    job_template_runner.host = "https://example.com"
    job_template_runner.token = "DUMMY"
    job_template_runner.refresh_delay = 0.05
    return job_template_runner


@pytest.mark.asyncio
async def test_job_template_get_config(mocked_job_template_runner):
    text = json.dumps(dict(version="4.4.1"))
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}{CONFIG_SLUG}",
            status=200,
            body=text,
        )
        data = await mocked_job_template_runner.get_config()
        assert data["version"] == "4.4.1"


@pytest.mark.asyncio
async def test_job_template_get_config_error(mocked_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}{CONFIG_SLUG}",
            exception=ClientError,
        )
        with pytest.raises(ControllerApiException):
            await mocked_job_template_runner.get_config()


@pytest.mark.asyncio
async def test_job_template_get_config_auth_error(mocked_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}{CONFIG_SLUG}", status=401
        )
        with pytest.raises(ControllerApiException):
            await mocked_job_template_runner.get_config()


@pytest.mark.asyncio
async def test_run_job_template(mocked_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE),
        )
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE2_SLUG}",
            status=200,
            body=json.dumps(UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE),
        )
        mocked.post(
            f"{mocked_job_template_runner.host}"
            f"{JOB_TEMPLATE_1_LAUNCH_SLUG}",
            status=200,
            body=json.dumps(JOB_TEMPLATE_POST_RESPONSE),
        )
        mocked.get(
            f"{mocked_job_template_runner.host}{JOB_1_SLUG}",
            status=200,
            body=json.dumps(JOB_1_RUNNING),
        )
        mocked.get(
            f"{mocked_job_template_runner.host}{JOB_1_SLUG}",
            status=200,
            body=json.dumps(JOB_1_SUCCESSFUL),
        )
        data = await mocked_job_template_runner.run_job_template(
            JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}
        )
        assert data["status"] == "successful"
        assert data["artifacts"] == {"fred": 45, "barney": 90}


@pytest.mark.asyncio
async def test_run_workflow_template(mocked_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE),
        )
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE2_SLUG}",
            status=200,
            body=json.dumps(UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE),
        )
        mocked.post(
            f"{mocked_job_template_runner.host}"
            f"{JOB_TEMPLATE_2_LAUNCH_SLUG}",
            status=200,
            body=json.dumps(JOB_TEMPLATE_POST_RESPONSE),
        )
        mocked.get(
            f"{mocked_job_template_runner.host}{JOB_1_SLUG}",
            status=200,
            body=json.dumps(JOB_1_RUNNING),
        )
        mocked.get(
            f"{mocked_job_template_runner.host}{JOB_1_SLUG}",
            status=200,
            body=json.dumps(JOB_1_SUCCESSFUL),
        )

        data = await mocked_job_template_runner.run_workflow_job_template(
            JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1, "limit": "all"}
        )
        assert data["status"] == "successful"
        assert data["artifacts"] == {"fred": 45, "barney": 90}


@pytest.mark.asyncio
async def test_missing_job_template(mocked_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(NO_JOB_TEMPLATE_PAGE1_RESPONSE),
        )
        with pytest.raises(JobTemplateNotFoundException):
            await mocked_job_template_runner.run_job_template(
                JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}
            )


@pytest.mark.asyncio
async def test_missing_workflow_template(mocked_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(NO_JOB_TEMPLATE_PAGE1_RESPONSE),
        )
        with pytest.raises(WorkflowJobTemplateNotFoundException):
            await mocked_job_template_runner.run_workflow_job_template(
                JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}
            )


@pytest.mark.asyncio
async def test_run_workflow_template_fail(mocked_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE),
        )
        mocked.get(
            f"{mocked_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE2_SLUG}",
            status=200,
            body=json.dumps(UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE),
        )
        mocked.post(
            f"{mocked_job_template_runner.host}"
            f"{JOB_TEMPLATE_2_LAUNCH_SLUG}",
            status=400,
            body=json.dumps({"msg": "Custom error message"}),
        )

        with pytest.raises(ControllerApiException):
            await mocked_job_template_runner.run_workflow_job_template(
                JOB_TEMPLATE_NAME_1,
                ORGANIZATION_NAME,
                {"a": 1, "limit": "all"},
            )
