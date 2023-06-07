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
from pathlib import Path

import pytest
from aiohttp import ClientError
from aioresponses import aioresponses

from ansible_rulebook.exception import (
    ControllerApiException,
    JobTemplateNotFoundException,
)
from ansible_rulebook.job_template_runner import job_template_runner


@pytest.fixture(scope="module")
def vcr_config():
    return {"filter_headers": [("authorization", "Bearer DUMMY")]}


@pytest.fixture(scope="module")
def vcr_cassette_dir(request):
    return str(Path(f"{__file__}").parent / "cassettes")


@pytest.mark.vcr()
@pytest.mark.asyncio
async def test_job_template():
    job_template_runner.host = "https://examples.com"
    job_template_runner.token = "DUMMY"
    job_template_runner.refresh_delay = 0.01
    job = await job_template_runner.run_job_template(
        "Hello World", "Default", {"secret": "secret"}
    )
    assert job["name"] == "Hello World"
    assert job["status"] == "successful"


@pytest.mark.vcr()
@pytest.mark.asyncio
async def test_job_template_not_exist():
    job_template_runner.host = "https://examples.com"
    job_template_runner.token = "DUMMY"
    with pytest.raises(JobTemplateNotFoundException):
        await job_template_runner.run_job_template("Hello World", "no-org", {})


@pytest.mark.asyncio
async def test_job_template_get_config():
    text = json.dumps(dict(version="4.4.1"))
    with aioresponses() as mocked:
        job_template_runner.host = "https://example.com"
        job_template_runner.token = "DUMMY"
        mocked.get("https://example.com/api/v2/config", status=200, body=text)
        data = await job_template_runner.get_config()
        assert data["version"] == "4.4.1"


@pytest.mark.asyncio
async def test_job_template_get_config_error():
    with aioresponses() as mocked:
        job_template_runner.host = "https://example.com"
        job_template_runner.token = "DUMMY"
        mocked.get("https://example.com/api/v2/config", exception=ClientError)
        with pytest.raises(ControllerApiException):
            await job_template_runner.get_config()


@pytest.mark.asyncio
async def test_job_template_get_config_auth_error():
    with aioresponses() as mocked:
        job_template_runner.host = "https://example.com"
        job_template_runner.token = "DUMMY"
        mocked.get("https://example.com/api/v2/config", status=401)
        with pytest.raises(ControllerApiException):
            await job_template_runner.get_config()
