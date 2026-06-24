#  Copyright 2026 Red Hat, Inc.
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

"""Tests for SharedJobMonitor - centralized batch job monitoring."""

import asyncio
import json
import re

import pytest
import pytest_asyncio
from aioresponses import aioresponses

from .data.awx_test_data import JOB_1_RUNNING, JOB_1_SLUG, JOB_1_SUCCESSFUL

POLL_INTERVAL = 0.01
POLL_TIMEOUT = 5.0


async def _wait_for(predicate, timeout=POLL_TIMEOUT):
    """Poll predicate until truthy or timeout."""

    async def _poll():
        while not predicate():
            await asyncio.sleep(POLL_INTERVAL)

    await asyncio.wait_for(_poll(), timeout=timeout)


def batch_url(host, path="api/v2/jobs/"):
    """Regex pattern matching a batch polling URL with id__in param."""
    base = re.escape(f"{host}{path}")
    return re.compile(base + r"\?.*\bid__in=")


@pytest_asyncio.fixture
async def new_job_template_runner(monkeypatch):
    from ansible_rulebook.conf import settings
    from ansible_rulebook.job_template_runner import JobTemplateRunner

    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    obj = JobTemplateRunner(
        host="https://example.com",
        token="DUMMY",
    )
    obj.refresh_delay = 0.0
    yield obj
    await obj.close_session()


@pytest.mark.asyncio
async def test_shared_monitor_single_job(new_job_template_runner):
    """Test that shared monitor works for a single job."""
    with aioresponses() as mocked:
        # Job is running initially
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_RUNNING]}),
        )
        # Job completes
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_SUCCESSFUL]}),
        )

        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "successful"


@pytest.mark.asyncio
async def test_shared_monitor_multiple_jobs_concurrently(
    new_job_template_runner,
):
    """Test shared monitor with multiple concurrent jobs."""
    job_2_slug = "api/v2/jobs/124/"
    job_3_slug = "api/v2/jobs/125/"

    with aioresponses() as mocked:
        # First batch poll: all running
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps(
                {
                    "count": 3,
                    "results": [
                        {**JOB_1_RUNNING, "id": 909},
                        {**JOB_1_RUNNING, "id": 124},
                        {**JOB_1_RUNNING, "id": 125},
                    ],
                }
            ),
        )
        # Second batch poll: all successful
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps(
                {
                    "count": 3,
                    "results": [
                        {**JOB_1_SUCCESSFUL, "id": 909},
                        {**JOB_1_SUCCESSFUL, "id": 124},
                        {**JOB_1_SUCCESSFUL, "id": 125},
                    ],
                }
            ),
        )

        results = await asyncio.gather(
            new_job_template_runner.monitor_job(JOB_1_SLUG),
            new_job_template_runner.monitor_job(job_2_slug),
            new_job_template_runner.monitor_job(job_3_slug),
        )

        assert all(r["status"] == "successful" for r in results)
        assert results[0]["id"] == 909
        assert results[1]["id"] == 124
        assert results[2]["id"] == 125

        # Verify all jobs were cleaned up from monitor
        assert (
            new_job_template_runner._job_monitor.get_monitored_job_count() == 0
        )


@pytest.mark.asyncio
async def test_shared_monitor_handles_duplicate_registration(
    new_job_template_runner,
):
    """Test that registering the same job twice returns the same future."""
    monitor = new_job_template_runner._job_monitor

    with aioresponses() as mocked:
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_SUCCESSFUL]}),
        )

        # Register the same job twice
        future1 = await monitor.register_job(JOB_1_SLUG)
        future2 = await monitor.register_job(JOB_1_SLUG)

        # Should be the same future
        assert future1 is future2

        # Both should resolve to the same result
        result = await future1
        assert result["status"] == "successful"


@pytest.mark.asyncio
async def test_shared_monitor_batch_polling(new_job_template_runner):
    """Test that batch polling uses correct API path for multiple jobs."""

    job_2_slug = "api/v2/jobs/124/"
    job_3_slug = "api/v2/jobs/125/"

    # Expected batch API response
    batch_response = {
        "count": 3,
        "results": [
            {**JOB_1_RUNNING, "id": 909},
            {**JOB_1_RUNNING, "id": 124},
            {**JOB_1_SUCCESSFUL, "id": 125},
        ],
    }

    with aioresponses() as mocked:
        # Mock batch polling endpoint
        # Should use api/v2/jobs/ with id__in parameter
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps(batch_response),
        )

        # Second poll - remaining jobs
        batch_response_2 = {
            "count": 2,
            "results": [
                {**JOB_1_SUCCESSFUL, "id": 909},
                {**JOB_1_SUCCESSFUL, "id": 124},
            ],
        }
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps(batch_response_2),
        )

        # Monitor all 3 jobs concurrently
        results = await asyncio.gather(
            new_job_template_runner.monitor_job(JOB_1_SLUG),
            new_job_template_runner.monitor_job(job_2_slug),
            new_job_template_runner.monitor_job(job_3_slug),
        )

        assert all(r["status"] == "successful" for r in results)
        assert results[0]["id"] == 909
        assert results[1]["id"] == 124
        assert results[2]["id"] == 125


@pytest.mark.asyncio
async def test_shared_monitor_batch_polling_gateway_path(
    new_job_template_runner,
):
    """Test that batch polling works with gateway URL format."""

    # Simulate gateway setup
    new_job_template_runner.host = "https://example.com/api/controller/"
    job_1_slug = "v2/jobs/123/"
    job_2_slug = "v2/jobs/124/"

    batch_response = {
        "count": 2,
        "results": [
            {**JOB_1_SUCCESSFUL, "id": 123, "url": job_1_slug},
            {**JOB_1_SUCCESSFUL, "id": 124, "url": job_2_slug},
        ],
    }

    with aioresponses() as mocked:
        # Should use v2/jobs/ (not api/v2/jobs/) for gateway
        mocked.get(
            batch_url(new_job_template_runner.host, "v2/jobs/"),
            status=200,
            body=json.dumps(batch_response),
        )

        # Monitor both jobs
        results = await asyncio.gather(
            new_job_template_runner.monitor_job(job_1_slug),
            new_job_template_runner.monitor_job(job_2_slug),
        )

        assert all(r["status"] == "successful" for r in results)
        assert results[0]["id"] == 123
        assert results[1]["id"] == 124


@pytest.mark.asyncio
async def test_shared_monitor_stats(new_job_template_runner):
    """Test that SharedJobMonitor.get_stats() returns accurate statistics."""

    with aioresponses() as mocked:
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_SUCCESSFUL]}),
        )

        # Get initial stats
        initial_stats = new_job_template_runner._job_monitor.get_stats()

        # Register and monitor a job
        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "successful"

        # Check final stats
        final_stats = new_job_template_runner._job_monitor.get_stats()
        assert final_stats["active_jobs"] == 0  # Job completed
        assert (
            final_stats["total_jobs_monitored"]
            >= initial_stats["total_jobs_monitored"]
        )
        assert final_stats["monitor_cycles"] >= initial_stats["monitor_cycles"]


@pytest.mark.asyncio
async def test_shared_monitor_get_monitored_job_count(new_job_template_runner):
    """Test that get_monitored_job_count returns correct count."""

    job_2_slug = "api/v2/jobs/124/"

    with aioresponses() as mocked:
        # Jobs that stay running for this test
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps(
                {
                    "count": 2,
                    "results": [
                        {**JOB_1_RUNNING, "id": 909},
                        {**JOB_1_RUNNING, "id": 124},
                    ],
                }
            ),
            repeat=True,
        )

        # Start monitoring (don't await - let them run in background)
        task1 = asyncio.create_task(
            new_job_template_runner.monitor_job(JOB_1_SLUG)
        )
        task2 = asyncio.create_task(
            new_job_template_runner.monitor_job(job_2_slug)
        )

        # Wait for monitor to register both jobs
        monitor = new_job_template_runner._job_monitor
        await _wait_for(lambda: monitor.get_monitored_job_count() >= 2)
        assert monitor.get_monitored_job_count() == 2

        # Cancel tasks to cleanup
        task1.cancel()
        task2.cancel()
        try:
            await task1
        except asyncio.CancelledError:
            pass
        try:
            await task2
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_shared_monitor_unregister_job(new_job_template_runner):
    """Test manual unregistration of a job."""

    with aioresponses() as mocked:
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_RUNNING]}),
            repeat=True,
        )

        # Register job
        monitor = new_job_template_runner._job_monitor
        await monitor.register_job(JOB_1_SLUG)
        assert monitor.get_monitored_job_count() == 1

        # Unregister job
        await monitor.unregister_job(JOB_1_SLUG)
        assert monitor.get_monitored_job_count() == 0


@pytest.mark.asyncio
async def test_shared_monitor_is_healthy(new_job_template_runner):
    """Test health check in various states."""

    # Initially healthy (no jobs, no monitor)
    assert new_job_template_runner._job_monitor.is_healthy()

    with aioresponses() as mocked:
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_SUCCESSFUL]}),
        )

        # Monitor a job
        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "successful"

        # Still healthy after job completes
        assert new_job_template_runner._job_monitor.is_healthy()


@pytest.mark.asyncio
async def test_shared_monitor_cleanup_cancelled_jobs(new_job_template_runner):
    """Test that cancelled futures are cleaned up properly."""

    with aioresponses() as mocked:
        # Job stays running
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_RUNNING]}),
            repeat=True,
        )

        # Start monitoring but cancel immediately
        task = asyncio.create_task(
            new_job_template_runner.monitor_job(JOB_1_SLUG)
        )
        monitor = new_job_template_runner._job_monitor
        await _wait_for(lambda: monitor.get_monitored_job_count() >= 1)
        initial_count = monitor.get_monitored_job_count()
        assert initial_count >= 1

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        # Wait for cleanup to run
        await _wait_for(
            lambda: monitor.get_monitored_job_count() < initial_count
        )
        assert (
            new_job_template_runner._job_monitor.get_monitored_job_count()
            < initial_count
        )


@pytest.mark.asyncio
async def test_shared_monitor_batch_polling_mixed_job_types(
    new_job_template_runner,
):
    """Test batch polling with both regular jobs and workflow jobs."""
    regular_job_slug = "api/v2/jobs/123/"
    workflow_job_slug = "api/v2/workflow_jobs/456/"

    workflow_job_successful = {
        "id": 456,
        "status": "successful",
        "url": workflow_job_slug,
        "artifacts": {"result": "ok"},
    }

    with aioresponses() as mocked:
        # Batch response for regular jobs
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps(
                {"count": 1, "results": [{**JOB_1_SUCCESSFUL, "id": 123}]}
            ),
        )

        # Batch response for workflow jobs
        mocked.get(
            batch_url(new_job_template_runner.host, "api/v2/workflow_jobs/"),
            status=200,
            body=json.dumps(
                {"count": 1, "results": [workflow_job_successful]}
            ),
        )

        # Monitor both types concurrently
        results = await asyncio.gather(
            new_job_template_runner.monitor_job(regular_job_slug),
            new_job_template_runner.monitor_job(workflow_job_slug),
        )

        assert results[0]["id"] == 123
        assert results[0]["status"] == "successful"
        assert results[1]["id"] == 456
        assert results[1]["status"] == "successful"


@pytest.mark.asyncio
async def test_shared_monitor_batch_polling_retries_on_error(
    new_job_template_runner,
):
    """Test that batch polling retries via the monitor loop on error."""
    with aioresponses() as mocked:
        # First batch poll fails (transient error)
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=500,
            body="Internal Server Error",
        )

        # Second batch poll succeeds
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_SUCCESSFUL]}),
        )

        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "successful"


@pytest.mark.asyncio
async def test_shared_monitor_empty_batch_results(new_job_template_runner):
    """Test handling of empty batch results (jobs not in response)."""
    with aioresponses() as mocked:
        # First poll: empty results
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 0, "results": []}),
        )

        # Second poll: job appears and completes
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [JOB_1_SUCCESSFUL]}),
        )

        # Should eventually complete
        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "successful"


@pytest.mark.asyncio
async def test_monitor_job_with_failed_status_logged(
    new_job_template_runner, caplog
):
    """Test that failed jobs are properly logged at ERROR level."""
    job_failed = {
        "id": 909,
        "status": "failed",
        "url": JOB_1_SLUG,
        "artifacts": {},
        "created": "2024-01-01T00:00:00Z",
    }

    with aioresponses() as mocked:
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [job_failed]}),
        )

        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "failed"

    error_msgs = [
        r
        for r in caplog.records
        if r.levelname == "ERROR" and "failed" in r.message
    ]
    assert len(error_msgs) >= 1


@pytest.mark.asyncio
async def test_monitor_job_with_canceled_status_logged(
    new_job_template_runner, caplog
):
    """Test that canceled jobs are properly logged at WARNING level."""
    job_canceled = {
        "id": 909,
        "status": "canceled",
        "url": JOB_1_SLUG,
        "artifacts": {},
        "created": "2024-01-01T00:00:00Z",
    }

    with aioresponses() as mocked:
        mocked.get(
            batch_url(new_job_template_runner.host),
            status=200,
            body=json.dumps({"count": 1, "results": [job_canceled]}),
        )

        result = await new_job_template_runner.monitor_job(JOB_1_SLUG)
        assert result["status"] == "canceled"

    warning_msgs = [
        r
        for r in caplog.records
        if r.levelname == "WARNING" and "canceled" in r.message
    ]
    assert len(warning_msgs) >= 1


@pytest.mark.asyncio
async def test_shared_monitor_chunked_batch_polling(new_job_template_runner):
    """Test that batch polling chunks jobs by max_batch_job_polling_size.

    With 4 jobs and a batch size of 2, the monitor should make 2 API calls
    per poll cycle, each with 2 job IDs in the id__in parameter.
    """
    from unittest.mock import patch

    job_slugs = [f"api/v2/jobs/{i}/" for i in range(123, 127)]

    with patch(
        "ansible_rulebook.shared_job_monitor.settings"
    ) as mock_settings:
        mock_settings.max_batch_job_polling_size = 2

        with aioresponses() as mocked:
            # Chunk 1: jobs 123, 124
            mocked.get(
                batch_url(new_job_template_runner.host),
                status=200,
                body=json.dumps(
                    {
                        "count": 2,
                        "results": [
                            {**JOB_1_SUCCESSFUL, "id": 123},
                            {**JOB_1_SUCCESSFUL, "id": 124},
                        ],
                    }
                ),
            )
            # Chunk 2: jobs 125, 126
            mocked.get(
                batch_url(new_job_template_runner.host),
                status=200,
                body=json.dumps(
                    {
                        "count": 2,
                        "results": [
                            {**JOB_1_SUCCESSFUL, "id": 125},
                            {**JOB_1_SUCCESSFUL, "id": 126},
                        ],
                    }
                ),
            )

            results = await asyncio.gather(
                *[
                    new_job_template_runner.monitor_job(slug)
                    for slug in job_slugs
                ]
            )

            assert len(results) == 4
            assert all(r["status"] == "successful" for r in results)
            for i, result in enumerate(results):
                assert result["id"] == 123 + i


@pytest.mark.asyncio
async def test_batch_poll_includes_page_size(new_job_template_runner):
    """Test that batch polling includes page_size parameter."""
    # Create a mock monitor
    monitor = new_job_template_runner._job_monitor

    # Mock the _get_page_no_retry to capture params
    captured_params = []

    original_get_page = new_job_template_runner._get_page_no_retry

    async def mock_get_page(href_slug, params):
        captured_params.append(params)
        return {"count": 0, "results": []}

    new_job_template_runner._get_page_no_retry = mock_get_page

    try:
        # Create fake jobs
        jobs = {
            f"jobs/{i}": {
                "url": f"https://example.com/api/v2/jobs/{i}/",  # noqa
                "numeric_id": str(i),
                "future": asyncio.Future(),
            }
            for i in range(10, 15)  # 5 jobs
        }

        # Call _poll_job_chunk
        await monitor._poll_job_chunk(jobs, "api/v2/jobs/", "jobs")

        # Verify page_size was included in params
        assert len(captured_params) == 1
        params = captured_params[0]

        assert "page_size" in params
        assert params["page_size"] == 5  # Same as number of jobs
        assert "id__in" in params

    finally:
        new_job_template_runner._get_page_no_retry = original_get_page


@pytest.mark.asyncio
async def test_batch_poll_page_size_matches_chunk_size(
    new_job_template_runner,
):
    """Test that page_size matches the number of IDs being queried."""
    monitor = new_job_template_runner._job_monitor

    captured_params = []

    async def mock_get_page(href_slug, params):
        captured_params.append(params)
        return {"count": 0, "results": []}

    new_job_template_runner._get_page_no_retry = mock_get_page

    try:
        # Test with different chunk sizes
        for num_jobs in [1, 5, 25, 50]:
            captured_params.clear()

            jobs = {
                f"jobs/{i}": {
                    "url": f"https://example.com/api/v2/jobs/{i}/",  # noqa
                    "numeric_id": str(i),
                    "future": asyncio.Future(),
                }
                for i in range(num_jobs)
            }

            await monitor._poll_job_chunk(jobs, "api/v2/jobs/", "jobs")

            # Verify page_size matches number of jobs
            assert len(captured_params) == 1
            params = captured_params[0]
            assert params["page_size"] == num_jobs

            # Verify id__in contains correct number of IDs
            id_list = params["id__in"].split(",")
            assert len(id_list) == num_jobs

    finally:
        # Clean up futures
        for jobs_dict in [jobs]:
            for job_info in jobs_dict.values():
                if not job_info["future"].done():
                    job_info["future"].cancel()
