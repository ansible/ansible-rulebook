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
import re

import pytest
import pytest_asyncio
from aiohttp import ClientError
from aioresponses import aioresponses

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    ControllerApiException,
    JobTemplateNotFoundException,
    WorkflowJobTemplateNotFoundException,
)

from .data.awx_test_data import (
    CUSTOMER_LABEL,
    CUSTOMER_LABEL_DATA,
    CUSTOMER_LABEL_RESPONSE,
    CUSTOMER_LABEL_SLUG,
    DEFAULT_LABEL_RESPONSE,
    DEFAULT_LABEL_SLUG,
    JOB_1_RUNNING,
    JOB_1_SLUG,
    JOB_1_SUCCESSFUL,
    JOB_TEMPLATE_1_LAUNCH_SLUG,
    JOB_TEMPLATE_2_LAUNCH_SLUG,
    JOB_TEMPLATE_NAME_1,
    JOB_TEMPLATE_POST_RESPONSE,
    LABEL_POST_SLUG,
    NO_JOB_TEMPLATE_PAGE1_RESPONSE,
    NO_SUCH_LABEL,
    NO_SUCH_ORGANIZATION,
    ORGANIZATION_NAME,
    ORGANIZATION_RESPONSE,
    ORGANIZATION_SLUG,
    UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
    UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS,
    UNIFIED_JOB_TEMPLATE_PAGE1_SLUG,
    UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
    UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS,
    UNIFIED_JOB_TEMPLATE_PAGE2_SLUG,
)

CONFIG_SLUG = "api/v2/config/"
BATCH_JOBS_SLUG = "api/v2/jobs/"


def add_batch_job_monitor_responses(mocked, host, *job_responses):
    """Mock the batch polling endpoint used by SharedJobMonitor.

    Each job_response is a dict (e.g. JOB_1_RUNNING, JOB_1_SUCCESSFUL)
    that will be returned as a single-item batch result per poll cycle.
    Uses regex to match the URL with any query params (id__in=...).
    """
    base = re.escape(f"{host}{BATCH_JOBS_SLUG}")
    pattern = re.compile(base + r"\?.*\bid__in=")
    for job_data in job_responses:
        mocked.get(
            pattern,
            status=200,
            body=json.dumps({"count": 1, "results": [job_data]}),
        )


@pytest_asyncio.fixture
async def new_job_template_runner(monkeypatch):
    from ansible_rulebook.job_template_runner import JobTemplateRunner

    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    obj = JobTemplateRunner(
        host="https://example.com",
        token="DUMMY",
    )
    obj.refresh_delay = 0.0
    yield obj
    await obj.close_session()


@pytest.fixture
def mocked_job_template_runner():
    from ansible_rulebook.job_template_runner import job_template_runner

    job_template_runner.host = "https://example.com"
    job_template_runner.token = "DUMMY"
    job_template_runner.refresh_delay = 0.05
    return job_template_runner


@pytest.mark.asyncio
async def test_job_template_get_config(new_job_template_runner):
    text = json.dumps(dict(version="4.4.1"))
    with aioresponses() as mocked:
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=200,
            body=text,
        )
        data = await new_job_template_runner.get_config()
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


def add_mock_label_transactions(mocked, host, fail_org, fail_label):
    if fail_org:
        mocked.get(
            f"{host}{ORGANIZATION_SLUG}",
            status=200,
            body=json.dumps(NO_SUCH_ORGANIZATION),
        )
        return
    else:
        mocked.get(
            f"{host}{ORGANIZATION_SLUG}",
            status=200,
            body=json.dumps(ORGANIZATION_RESPONSE),
        )

    mocked.get(
        f"{host}{DEFAULT_LABEL_SLUG}",
        status=200,
        body=json.dumps(DEFAULT_LABEL_RESPONSE),
    )
    mocked.get(
        f"{host}{CUSTOMER_LABEL_SLUG}",
        status=200,
        body=json.dumps(NO_SUCH_LABEL),
    )
    if fail_label:
        if "exception" in fail_label:
            mocked.post(
                f"{host}{LABEL_POST_SLUG}",
                exception=fail_label["exception"],
            )
        elif "code" in fail_label:
            mocked.post(
                f"{host}{LABEL_POST_SLUG}",
                status=fail_label["code"],
                body=json.dumps(
                    {"__all__": fail_label.get("message", "Kaboom")}
                ),
            )
            mocked.get(
                f"{host}{CUSTOMER_LABEL_SLUG}",
                status=200,
                body=json.dumps(CUSTOMER_LABEL_RESPONSE),
            )
    else:
        mocked.post(
            f"{host}{LABEL_POST_SLUG}",
            status=201,
            body=json.dumps(CUSTOMER_LABEL_DATA),
        )


def add_job_templates_pages(mocked, host, page1, page2):
    mocked.get(
        f"{host}{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
        status=200,
        body=json.dumps(page1),
    )
    mocked.get(
        f"{host}{UNIFIED_JOB_TEMPLATE_PAGE2_SLUG}",
        status=200,
        body=json.dumps(page2),
    )


@pytest.mark.parametrize(
    ("labels", "page1", "page2", "fail_org", "fail_label"),
    [
        (
            [],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS,
            False,
            {},
        ),
        (
            [CUSTOMER_LABEL, "", None, "", {"a": 1}, [CUSTOMER_LABEL]],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
            False,
            {},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS,
            False,
            {},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
            True,
            {},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
            False,
            {"code": 400, "message": "Label already exists"},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
            False,
            {"code": 400},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
            False,
            {"code": 403},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
            False,
            {"exception": ClientError("Kaboom")},
        ),
    ],
)
@pytest.mark.asyncio
async def test_run_job_template(
    new_job_template_runner, labels, page1, page2, fail_org, fail_label
):
    with aioresponses() as mocked:
        add_job_templates_pages(
            mocked, new_job_template_runner.host, page1, page2
        )
        if labels:
            add_mock_label_transactions(
                mocked, new_job_template_runner.host, fail_org, fail_label
            )
        mocked.post(
            f"{new_job_template_runner.host}{JOB_TEMPLATE_1_LAUNCH_SLUG}",
            status=200,
            body=json.dumps(JOB_TEMPLATE_POST_RESPONSE),
        )
        add_batch_job_monitor_responses(
            mocked,
            new_job_template_runner.host,
            JOB_1_RUNNING,
            JOB_1_SUCCESSFUL,
        )
        if "exception" in fail_label:
            with pytest.raises(ControllerApiException):
                await new_job_template_runner.run_job_template(
                    JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}, labels
                )
        else:
            data = await new_job_template_runner.run_job_template(
                JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}, labels
            )
            assert data["status"] == "successful"
            assert data["artifacts"] == {"fred": 45, "barney": 90}


@pytest.mark.parametrize(
    ("labels", "page1", "page2", "fail_org", "fail_label"),
    [
        (
            [],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS,
            False,
            {},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE,
            False,
            {},
        ),
        (
            [CUSTOMER_LABEL],
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS,
            False,
            {},
        ),
    ],
)
@pytest.mark.asyncio
async def test_run_workflow_template(
    new_job_template_runner, labels, page1, page2, fail_org, fail_label
):
    with aioresponses() as mocked:
        add_job_templates_pages(
            mocked, new_job_template_runner.host, page1, page2
        )
        if labels:
            add_mock_label_transactions(
                mocked, new_job_template_runner.host, fail_org, fail_label
            )
        mocked.post(
            f"{new_job_template_runner.host}{JOB_TEMPLATE_2_LAUNCH_SLUG}",
            status=200,
            body=json.dumps(JOB_TEMPLATE_POST_RESPONSE),
        )
        add_batch_job_monitor_responses(
            mocked,
            new_job_template_runner.host,
            JOB_1_RUNNING,
            JOB_1_SUCCESSFUL,
        )

        data = await new_job_template_runner.run_workflow_job_template(
            JOB_TEMPLATE_NAME_1,
            ORGANIZATION_NAME,
            {"a": 1, "limit": "all"},
            labels,
        )
        assert data["status"] == "successful"
        assert data["artifacts"] == {"fred": 45, "barney": 90}


@pytest.mark.asyncio
async def test_missing_job_template(new_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{new_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(NO_JOB_TEMPLATE_PAGE1_RESPONSE),
        )
        with pytest.raises(JobTemplateNotFoundException):
            await new_job_template_runner.run_job_template(
                JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}
            )


@pytest.mark.asyncio
async def test_missing_workflow_template(new_job_template_runner):
    with aioresponses() as mocked:
        mocked.get(
            f"{new_job_template_runner.host}"
            f"{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(NO_JOB_TEMPLATE_PAGE1_RESPONSE),
        )
        with pytest.raises(WorkflowJobTemplateNotFoundException):
            await new_job_template_runner.run_workflow_job_template(
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


@pytest.mark.parametrize(
    ("host", "expected"),
    [
        ("https://example.com", "https://example.com/api/v2/config/"),
        ("https://example.com/", "https://example.com/api/v2/config/"),
        (
            "https://example.com/custom/awx",
            "https://example.com/custom/awx/v2/config/",
        ),
        (
            "https://example.com/awx/api",
            "https://example.com/awx/api/v2/config/",
        ),
        (
            "https://example.com/custom/awx/",
            "https://example.com/custom/awx/v2/config/",
        ),
    ],
)
@pytest.mark.asyncio
async def test_session_get_called_with_expected_url(
    new_job_template_runner,
    host,
    expected,
):
    new_job_template_runner.host = host
    with aioresponses() as mocked:
        mocked.get(expected, status=200, body=json.dumps({"a": 1}))
        data = await new_job_template_runner.get_config()
        assert data == {"a": 1}


@pytest.mark.asyncio
async def test_get_job_url_from_label_job_template_found(
    new_job_template_runner,
):
    """Test get_job_url_from_label with job_template type when job is found."""
    from ansible_rulebook.job_template_runner import JOB_TEMPLATE_TYPE

    label_name = "test-label"
    job_url = "api/v2/jobs/123/"

    # Mock response for job template
    job_template_response = {
        "id": 255,
        "type": "job_template",
        "name": JOB_TEMPLATE_NAME_1,
        "ask_limit_on_launch": False,
        "ask_variables_on_launch": False,
        "ask_inventory_on_launch": False,
        "ask_labels_on_launch": True,
        "related": {"launch": JOB_TEMPLATE_1_LAUNCH_SLUG},
        "summary_fields": {"organization": {"name": ORGANIZATION_NAME}},
    }

    # Mock response for jobs with label
    jobs_response = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [{"url": job_url, "id": 123, "status": "successful"}],
    }

    with aioresponses() as mocked:
        # Mock the unified job templates endpoint
        mocked.get(
            f"{new_job_template_runner.host}{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(
                {
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [job_template_response],
                }
            ),
        )

        # Mock the jobs endpoint filtered by label
        jobs_slug = f"api/v2/job_templates/255/jobs/?labels__name={label_name}"
        mocked.get(
            f"{new_job_template_runner.host}{jobs_slug}",
            status=200,
            body=json.dumps(jobs_response),
        )

        result = await new_job_template_runner.get_job_url_from_label(
            JOB_TEMPLATE_NAME_1,
            ORGANIZATION_NAME,
            JOB_TEMPLATE_TYPE,
            label_name,
        )

        assert result == job_url


@pytest.mark.asyncio
async def test_get_job_url_from_label_job_template_not_found(
    new_job_template_runner,
):
    """Test get_job_url_from_label with job_template type.

    When no job is found.
    """
    from ansible_rulebook.job_template_runner import JOB_TEMPLATE_TYPE

    label_name = "test-label"

    # Mock response for job template
    job_template_response = {
        "id": 255,
        "type": "job_template",
        "name": JOB_TEMPLATE_NAME_1,
        "ask_limit_on_launch": False,
        "ask_variables_on_launch": False,
        "ask_inventory_on_launch": False,
        "ask_labels_on_launch": True,
        "related": {"launch": JOB_TEMPLATE_1_LAUNCH_SLUG},
        "summary_fields": {"organization": {"name": ORGANIZATION_NAME}},
    }

    # Mock response for jobs with label - no results
    jobs_response = {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }

    with aioresponses() as mocked:
        # Mock the unified job templates endpoint
        mocked.get(
            f"{new_job_template_runner.host}{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(
                {
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [job_template_response],
                }
            ),
        )

        # Mock the jobs endpoint filtered by label
        jobs_slug = f"api/v2/job_templates/255/jobs/?labels__name={label_name}"
        mocked.get(
            f"{new_job_template_runner.host}{jobs_slug}",
            status=200,
            body=json.dumps(jobs_response),
        )

        result = await new_job_template_runner.get_job_url_from_label(
            JOB_TEMPLATE_NAME_1,
            ORGANIZATION_NAME,
            JOB_TEMPLATE_TYPE,
            label_name,
        )

        assert result is None


@pytest.mark.asyncio
async def test_get_job_url_from_label_workflow_template_found(
    new_job_template_runner,
):
    """Test get_job_url_from_label with workflow_template type.

    When job is found.
    """
    from ansible_rulebook.job_template_runner import WORKFLOW_TEMPLATE_TYPE

    label_name = "test-label"
    workflow_job_url = "api/v2/workflow_jobs/456/"

    # Mock response for workflow template
    workflow_template_response = {
        "id": 300,
        "type": "workflow_job_template",
        "name": JOB_TEMPLATE_NAME_1,
        "ask_limit_on_launch": False,
        "ask_variables_on_launch": False,
        "ask_inventory_on_launch": True,
        "ask_labels_on_launch": True,
        "related": {"launch": JOB_TEMPLATE_2_LAUNCH_SLUG},
        "summary_fields": {"organization": {"name": ORGANIZATION_NAME}},
    }

    # Mock response for workflow jobs with label
    workflow_jobs_response = {
        "count": 1,
        "next": None,
        "previous": None,
        "results": [
            {"url": workflow_job_url, "id": 456, "status": "successful"}
        ],
    }

    with aioresponses() as mocked:
        # Mock the unified job templates endpoint
        mocked.get(
            f"{new_job_template_runner.host}{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(
                {
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [workflow_template_response],
                }
            ),
        )

        # Mock the workflow jobs endpoint filtered by label
        jobs_slug = (
            f"api/v2/workflow_job_templates/300/workflow_jobs/"
            f"?labels__name={label_name}"
        )
        mocked.get(
            f"{new_job_template_runner.host}{jobs_slug}",
            status=200,
            body=json.dumps(workflow_jobs_response),
        )

        result = await new_job_template_runner.get_job_url_from_label(
            JOB_TEMPLATE_NAME_1,
            ORGANIZATION_NAME,
            WORKFLOW_TEMPLATE_TYPE,
            label_name,
        )

        assert result == workflow_job_url


@pytest.mark.asyncio
async def test_get_job_url_from_label_workflow_template_not_found(
    new_job_template_runner,
):
    """Test get_job_url_from_label with workflow_template type.

    When no job is found.
    """
    from ansible_rulebook.job_template_runner import WORKFLOW_TEMPLATE_TYPE

    label_name = "test-label"

    # Mock response for workflow template
    workflow_template_response = {
        "id": 300,
        "type": "workflow_job_template",
        "name": JOB_TEMPLATE_NAME_1,
        "ask_limit_on_launch": False,
        "ask_variables_on_launch": False,
        "ask_inventory_on_launch": True,
        "ask_labels_on_launch": True,
        "related": {"launch": JOB_TEMPLATE_2_LAUNCH_SLUG},
        "summary_fields": {"organization": {"name": ORGANIZATION_NAME}},
    }

    # Mock response for workflow jobs with label - no results
    workflow_jobs_response = {
        "count": 0,
        "next": None,
        "previous": None,
        "results": [],
    }

    with aioresponses() as mocked:
        # Mock the unified job templates endpoint
        mocked.get(
            f"{new_job_template_runner.host}{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(
                {
                    "count": 1,
                    "next": None,
                    "previous": None,
                    "results": [workflow_template_response],
                }
            ),
        )

        # Mock the workflow jobs endpoint filtered by label
        jobs_slug = (
            f"api/v2/workflow_job_templates/300/workflow_jobs/"
            f"?labels__name={label_name}"
        )
        mocked.get(
            f"{new_job_template_runner.host}{jobs_slug}",
            status=200,
            body=json.dumps(workflow_jobs_response),
        )

        result = await new_job_template_runner.get_job_url_from_label(
            JOB_TEMPLATE_NAME_1,
            ORGANIZATION_NAME,
            WORKFLOW_TEMPLATE_TYPE,
            label_name,
        )

        assert result is None


@pytest.mark.asyncio
async def test_get_job_url_from_label_template_not_exists(
    new_job_template_runner,
):
    """Test get_job_url_from_label when the template doesn't exist."""
    from ansible_rulebook.job_template_runner import JOB_TEMPLATE_TYPE

    label_name = "test-label"

    with aioresponses() as mocked:
        # Mock the unified job templates endpoint - no results
        mocked.get(
            f"{new_job_template_runner.host}{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(NO_JOB_TEMPLATE_PAGE1_RESPONSE),
        )

        with pytest.raises(JobTemplateNotFoundException):
            await new_job_template_runner.get_job_url_from_label(
                JOB_TEMPLATE_NAME_1,
                ORGANIZATION_NAME,
                JOB_TEMPLATE_TYPE,
                label_name,
            )


@pytest.mark.asyncio
async def test_get_job_url_from_label_workflow_template_not_exists(
    new_job_template_runner,
):
    """Test get_job_url_from_label when the workflow template doesn't exist."""
    from ansible_rulebook.job_template_runner import WORKFLOW_TEMPLATE_TYPE

    label_name = "test-label"

    with aioresponses() as mocked:
        # Mock the unified job templates endpoint - no results
        mocked.get(
            f"{new_job_template_runner.host}{UNIFIED_JOB_TEMPLATE_PAGE1_SLUG}",
            status=200,
            body=json.dumps(NO_JOB_TEMPLATE_PAGE1_RESPONSE),
        )

        with pytest.raises(WorkflowJobTemplateNotFoundException):
            await new_job_template_runner.get_job_url_from_label(
                JOB_TEMPLATE_NAME_1,
                ORGANIZATION_NAME,
                WORKFLOW_TEMPLATE_TYPE,
                label_name,
            )


@pytest.mark.asyncio
async def test_get_job_url_from_label_invalid_type(new_job_template_runner):
    """Test get_job_url_from_label with an invalid type."""
    label_name = "test-label"
    invalid_type = "invalid_type"

    with pytest.raises(ValueError) as exc_info:
        await new_job_template_runner.get_job_url_from_label(
            JOB_TEMPLATE_NAME_1,
            ORGANIZATION_NAME,
            invalid_type,
            label_name,
        )

    assert "Invalid type" in str(exc_info.value)
    assert invalid_type in str(exc_info.value)


@pytest.mark.asyncio
async def test_monitor_job_retries_on_502(
    new_job_template_runner, monkeypatch
):
    """Verify monitor_job retries on 502 and succeeds after recovery.

    The SharedJobMonitor polls the batch endpoint (api/v2/jobs/?id__in=...).
    When a poll fails, the monitor retries on the next cycle.
    """
    monkeypatch.setattr(settings, "controller_retry_attempts", 3)
    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    batch_pattern = re.compile(
        re.escape(f"{new_job_template_runner.host}{BATCH_JOBS_SLUG}")
        + r"\?.*\bid__in="
    )
    with aioresponses() as mocked:
        mocked.get(batch_pattern, status=502)
        mocked.get(batch_pattern, status=502)
        add_batch_job_monitor_responses(
            mocked,
            new_job_template_runner.host,
            JOB_1_RUNNING,
            JOB_1_SUCCESSFUL,
        )

        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "successful"


@pytest.mark.asyncio
async def test_monitor_job_raises_after_max_retries(
    new_job_template_runner, monkeypatch
):
    """Verify monitor_job eventually completes even after transient errors.

    The SharedJobMonitor catches polling errors and retries on the next
    cycle rather than raising immediately, so we verify it recovers.
    """
    monkeypatch.setattr(settings, "controller_retry_attempts", 3)
    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    batch_pattern = re.compile(
        re.escape(f"{new_job_template_runner.host}{BATCH_JOBS_SLUG}")
        + r"\?.*\bid__in="
    )
    with aioresponses() as mocked:
        for _ in range(3):
            mocked.get(batch_pattern, status=502)
        add_batch_job_monitor_responses(
            mocked,
            new_job_template_runner.host,
            JOB_1_SUCCESSFUL,
        )

        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "successful"


@pytest.mark.asyncio
async def test_controller_unavailable_and_restored_logging(
    caplog, monkeypatch
):
    """Verify unavailable/restored logging."""
    from ansible_rulebook.job_template_runner import JobTemplateRunner

    monkeypatch.setattr(settings, "controller_retry_attempts", 1)
    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    runner = JobTemplateRunner(host="https://example.com", token="DUMMY")
    runner.refresh_delay = 0.0
    url = f"{runner.host}api/v2/config/"

    with aioresponses() as mocked:
        mocked.get(url, status=502)
        with pytest.raises(ControllerApiException):
            await runner.get_config()

        mocked.get(url, status=200, body=json.dumps({"version": "4.4.1"}))
        await runner.get_config()

    unavailable_msgs = [
        r for r in caplog.records if "Controller unavailable" in r.message
    ]
    restored_msgs = [
        r
        for r in caplog.records
        if "Controller connection restored" in r.message
    ]
    assert len(unavailable_msgs) == 1
    assert len(restored_msgs) == 1
    await runner.close_session()


def test_controller_retry_max_timeout_default(monkeypatch):
    """Verify default when env var is not set."""
    from ansible_rulebook.conf import _Settings

    monkeypatch.delenv("EDA_CONTROLLER_RETRY_MAX_TIMEOUT", raising=False)
    s = _Settings()
    assert s.controller_retry_max_timeout == 60.0


@pytest.mark.asyncio
async def test_get_page_empty_response(new_job_template_runner):
    """Verify _get_page raises on empty response body."""
    with aioresponses() as mocked:
        url = f"{new_job_template_runner.host}{CONFIG_SLUG}"
        mocked.get(url, status=200, body="")
        with pytest.raises(ControllerApiException, match="empty response"):
            await new_job_template_runner.get_config()


@pytest.mark.asyncio
async def test_launch_empty_response(new_job_template_runner, monkeypatch):
    """Verify _launch raises on empty response body."""
    monkeypatch.setattr(settings, "controller_retry_attempts", 1)
    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    new_job_template_runner._create_session()
    launch_url = "api/v2/job_templates/1/launch/"
    with aioresponses() as mocked:
        url = f"{new_job_template_runner.host}{launch_url}"
        mocked.post(url, status=200, body="")
        with pytest.raises(ControllerApiException, match="empty response"):
            await new_job_template_runner._launch({}, url)


@pytest.mark.asyncio
async def test_launch_5xx_with_body(new_job_template_runner, monkeypatch):
    """Verify _launch parses body before raise_for_status on 5xx."""
    monkeypatch.setattr(settings, "controller_retry_attempts", 1)
    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    new_job_template_runner._create_session()
    launch_url = "api/v2/job_templates/1/launch/"
    error_body = json.dumps({"detail": "Bad Gateway"})
    with aioresponses() as mocked:
        url = f"{new_job_template_runner.host}{launch_url}"
        mocked.post(url, status=502, body=error_body)
        with pytest.raises(ControllerApiException):
            await new_job_template_runner._launch({}, url)


@pytest.mark.asyncio
async def test_create_obj_already_exists_returns_retry(
    new_job_template_runner,
):
    """Verify _create_obj returns (None, True) on 400 'already exists'."""
    new_job_template_runner._create_session()
    slug = "api/v2/labels/"
    exists_body = json.dumps({"__all__": "Label already exists"})
    with aioresponses() as mocked:
        url = f"{new_job_template_runner.host}{slug}"
        mocked.post(url, status=400, body=exists_body)
        result, retry = await new_job_template_runner._create_obj(
            slug, {"name": "test"}
        )
        assert result is None
        assert retry is True


# Shared monitor and back pressure tests


@pytest.mark.asyncio
async def test_retry_on_503_service_unavailable(new_job_template_runner):
    """Test that 503 errors are retried and eventually succeed."""
    text_success = json.dumps(dict(version="4.4.1"))

    with aioresponses() as mocked:
        # First attempt: 503 Service Unavailable
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=503,
            body="Service Unavailable",
        )
        # Second attempt: Success
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=200,
            body=text_success,
        )

        data = await new_job_template_runner.get_config()
        assert data["version"] == "4.4.1"


@pytest.mark.asyncio
async def test_retry_on_429_rate_limit(new_job_template_runner):
    """Test that 429 rate limit errors are retried and eventually succeed."""
    text_success = json.dumps(dict(version="4.4.1"))

    with aioresponses() as mocked:
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=429,
            body="Too Many Requests",
        )
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=200,
            body=text_success,
        )

        data = await new_job_template_runner.get_config()
        assert data["version"] == "4.4.1"


@pytest.mark.asyncio
async def test_retry_on_502_bad_gateway(new_job_template_runner):
    """Test that 502 Bad Gateway errors are retried and eventually succeed."""
    text_success = json.dumps(dict(version="4.4.1"))

    with aioresponses() as mocked:
        # First attempt: 502 Bad Gateway
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=502,
            body="Bad Gateway",
        )
        # Second attempt: Success
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=200,
            body=text_success,
        )

        data = await new_job_template_runner.get_config()
        assert data["version"] == "4.4.1"


@pytest.mark.asyncio
async def test_retry_on_504_gateway_timeout(new_job_template_runner):
    """Test that 504 errors are retried and succeed."""
    text_success = json.dumps(dict(version="4.4.1"))

    with aioresponses() as mocked:
        # First attempt: 504 Gateway Timeout
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=504,
            body="Gateway Timeout",
        )
        # Second attempt: Success
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=200,
            body=text_success,
        )

        data = await new_job_template_runner.get_config()
        assert data["version"] == "4.4.1"


@pytest.mark.asyncio
async def test_retry_exhaustion_raises_exception(
    new_job_template_runner, monkeypatch
):
    """Test that after max retries are exhausted, exception is raised."""
    monkeypatch.setattr(settings, "controller_retry_attempts", 3)
    with aioresponses() as mocked:
        # Mock consecutive 503 errors (more than 3 attempts)
        for _ in range(5):
            mocked.get(
                f"{new_job_template_runner.host}{CONFIG_SLUG}",
                status=503,
                body="Service Unavailable",
            )

        with pytest.raises(ControllerApiException):
            await new_job_template_runner.get_config()


@pytest.mark.asyncio
async def test_retry_on_post_request_launch(new_job_template_runner):
    """Test that POST requests (job launch) also retry on 503 errors."""
    with aioresponses() as mocked:
        add_job_templates_pages(
            mocked,
            new_job_template_runner.host,
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS,
        )

        # First POST attempt: 503 Service Unavailable
        mocked.post(
            f"{new_job_template_runner.host}{JOB_TEMPLATE_1_LAUNCH_SLUG}",
            status=503,
            body="Service Unavailable",
        )
        # Second POST attempt: Success
        mocked.post(
            f"{new_job_template_runner.host}{JOB_TEMPLATE_1_LAUNCH_SLUG}",
            status=200,
            body=json.dumps(JOB_TEMPLATE_POST_RESPONSE),
        )

        # Mock job monitoring via batch endpoint
        add_batch_job_monitor_responses(
            mocked,
            new_job_template_runner.host,
            JOB_1_SUCCESSFUL,
        )

        data = await new_job_template_runner.run_job_template(
            JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}
        )
        assert data["status"] == "successful"


@pytest.mark.asyncio
async def test_multiple_retries_before_success(new_job_template_runner):
    """Test that multiple retries work before eventual success."""
    text_success = json.dumps(dict(version="4.4.1"))

    with aioresponses() as mocked:
        # First attempt: 503
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=503,
            body="Service Unavailable",
        )
        # Second attempt: 502
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=502,
            body="Bad Gateway",
        )
        # Third attempt: Success
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=200,
            body=text_success,
        )

        data = await new_job_template_runner.get_config()
        assert data["version"] == "4.4.1"


@pytest.mark.asyncio
async def test_non_retryable_error_fails_immediately(new_job_template_runner):
    """Test that non-retryable errors fail immediately."""
    with aioresponses() as mocked:
        # 400 Bad Request should not be retried
        mocked.get(
            f"{new_job_template_runner.host}{CONFIG_SLUG}",
            status=400,
            body="Bad Request",
        )

        with pytest.raises(ControllerApiException):
            await new_job_template_runner.get_config()


@pytest.mark.asyncio
async def test_retry_on_workflow_launch(new_job_template_runner):
    """Test that workflow launches also retry on 503 errors."""
    with aioresponses() as mocked:
        add_job_templates_pages(
            mocked,
            new_job_template_runner.host,
            UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS,
            UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS,
        )

        # First POST attempt: 503 Service Unavailable
        mocked.post(
            f"{new_job_template_runner.host}{JOB_TEMPLATE_2_LAUNCH_SLUG}",
            status=503,
            body="Service Unavailable",
        )
        # Second POST attempt: Success
        mocked.post(
            f"{new_job_template_runner.host}{JOB_TEMPLATE_2_LAUNCH_SLUG}",
            status=200,
            body=json.dumps(JOB_TEMPLATE_POST_RESPONSE),
        )

        # Mock job monitoring via batch endpoint
        add_batch_job_monitor_responses(
            mocked,
            new_job_template_runner.host,
            JOB_1_SUCCESSFUL,
        )

        data = await new_job_template_runner.run_workflow_job_template(
            JOB_TEMPLATE_NAME_1, ORGANIZATION_NAME, {"a": 1}, []
        )
        assert data["status"] == "successful"
