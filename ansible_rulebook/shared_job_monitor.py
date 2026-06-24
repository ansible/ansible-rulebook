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

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import ControllerApiException

if TYPE_CHECKING:
    from ansible_rulebook.job_template_runner import JobTemplateRunner

logger = logging.getLogger(__name__)


class SharedJobMonitor:
    """Shared monitor that polls multiple jobs in batches.

    Created as an instance variable on JobTemplateRunner so its lifecycle
    is tied to the runner.  All calls to monitor_job on the same runner
    share one polling loop, reducing API calls to the controller.

    Benefits:
    - Centralized polling logic
    - Batch API support via id__in
    - Better error handling across all jobs
    - Reduced overhead from multiple asyncio tasks
    - Natural cleanup when the runner is destroyed
    """

    def __init__(self, runner: "JobTemplateRunner"):
        self._runner = runner
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._monitor_task = None
        self._jobs_lock = asyncio.Lock()
        self._total_jobs_monitored = 0
        self._monitor_start_count = 0

    @staticmethod
    def _job_key(job_url: str) -> str:
        """Derive a unique key from a job URL.

        Uses the last two path segments (e.g. "jobs/123") so that
        /jobs/123 and /workflow_jobs/123 are tracked separately.
        """
        parts = job_url.rstrip("/").split("/")
        return "/".join(parts[-2:])

    async def register_job(self, job_url: str) -> asyncio.Future:
        """Register a job for monitoring and return a future.

        Args:
            job_url: The job URL to monitor

        Returns:
            asyncio.Future that resolves to the final job status dict
        """
        key = self._job_key(job_url)

        async with self._jobs_lock:
            if key in self._jobs:
                logger.debug("Job %s already registered, reusing future", key)
                return self._jobs[key]["future"]

            future = asyncio.Future()
            numeric_id = job_url.rstrip("/").split("/")[-1]
            self._jobs[key] = {
                "url": job_url,
                "numeric_id": numeric_id,
                "future": future,
            }
            self._total_jobs_monitored += 1

            monitor_was_stopped = (
                self._monitor_task is None or self._monitor_task.done()
            )
            if monitor_was_stopped:
                self._monitor_start_count += 1
                self._monitor_task = asyncio.create_task(self._monitor_loop())
                logger.info(
                    "Started shared job monitor loop (cycle #%d) - "
                    "monitoring %d job(s)",
                    self._monitor_start_count,
                    len(self._jobs),
                )
            else:
                logger.debug(
                    "Registered job %s for batch monitoring (%d active jobs)",
                    key,
                    len(self._jobs),
                )

        return future

    async def _monitor_loop(self):
        """Main monitoring loop that polls all registered jobs."""
        logger.info("Starting shared job monitor loop")

        while True:
            try:
                await self._cleanup_stale_jobs()

                async with self._jobs_lock:
                    if not self._jobs:
                        logger.info(
                            "No more jobs to monitor, "
                            "stopping monitor loop. "
                            "Total monitored this cycle: %d",
                            self._total_jobs_monitored,
                        )
                        self._monitor_task = None
                        break

                    jobs_to_check = list(self._jobs.items())

                await self._poll_all_jobs(jobs_to_check)

                if jobs_to_check:
                    await asyncio.sleep(self._runner.refresh_delay)

            except (
                ControllerApiException,
                OSError,
                asyncio.TimeoutError,
            ) as e:
                logger.error(  # NOSONAR
                    "Transient error in shared job monitor loop: %s",
                    str(e),
                )
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(  # NOSONAR
                    "Non-transient error in shared job monitor loop: %s",
                    str(e),
                )
                await self._fail_all_jobs(e)
                break

    async def _poll_all_jobs(
        self, jobs_to_check: List[Tuple[str, Dict[str, Any]]]
    ):
        """Group jobs by type and poll each group."""
        regular_jobs = {}
        workflow_jobs = {}

        for job_id, job_info in jobs_to_check:
            if job_info["future"].done():
                continue
            if "workflow_jobs" in job_info["url"]:
                workflow_jobs[job_id] = job_info
            else:
                regular_jobs[job_id] = job_info

        api_prefix = self._runner._api_slug_prefix()

        if regular_jobs:
            await self._batch_poll_jobs(
                regular_jobs, f"{api_prefix}jobs/", "jobs"
            )

        if workflow_jobs:
            await self._batch_poll_jobs(
                workflow_jobs,
                f"{api_prefix}workflow_jobs/",
                "workflow_jobs",
            )

    async def _batch_poll_jobs(
        self, jobs: Dict[str, Dict[str, Any]], api_path: str, job_type: str
    ):
        """Poll multiple jobs in chunked batch API calls."""
        if not jobs:
            return

        job_ids = list(jobs.keys())
        chunk_size = settings.max_batch_job_polling_size
        chunks = [
            job_ids[i : i + chunk_size]
            for i in range(0, len(job_ids), chunk_size)
        ]

        logger.debug(
            "Batch polling %d %s in %d chunk(s) of up to %d",
            len(job_ids),
            job_type,
            len(chunks),
            chunk_size,
        )

        for chunk in chunks:
            chunk_jobs = {jid: jobs[jid] for jid in chunk}
            await self._poll_job_chunk(chunk_jobs, api_path, job_type)

    async def _poll_job_chunk(
        self, jobs: Dict[str, Dict[str, Any]], api_path: str, job_type: str
    ):
        """Poll a single chunk of jobs with one API call."""
        numeric_ids = []
        id_to_key = {}
        for key, info in jobs.items():
            nid = info["numeric_id"]
            numeric_ids.append(nid)
            id_to_key[nid] = key

        # Include page_size to ensure all results come back in one page
        # and avoid silent truncation if controller's default page size
        # is smaller than our chunk size
        params = {
            "id__in": ",".join(numeric_ids),
            "page_size": len(numeric_ids),
        }
        result = await self._runner._get_page_no_retry(api_path, params)

        processed = 0
        for job_data in result.get("results", []):
            nid = str(job_data["id"])
            key = id_to_key.get(nid)
            if key and key in jobs:
                processed += await self._process_poll_result(
                    key, jobs[key], job_data
                )

        logger.debug(
            "Batch poll chunk processed %d/%d %s",
            processed,
            len(numeric_ids),
            job_type,
        )

    async def _process_poll_result(
        self,
        key: str,
        job_info: Dict[str, Any],
        job_data: dict,
    ) -> int:
        """Process a single job result from a poll response.

        Returns 1 if the job was processed, 0 otherwise.
        """
        nid = str(job_data["id"])
        status = job_data["status"]

        if status not in self._runner.JOB_COMPLETION_STATUSES:
            logger.debug("Job %s still running (status: %s)", nid, status)
            return 1

        async with self._jobs_lock:
            if key in self._jobs and not job_info["future"].done():
                job_info["future"].set_result(job_data)
                del self._jobs[key]
                self._log_completion(nid, status)
                return 1
        return 0

    def _log_completion(self, job_id: str, status: str) -> None:
        """Log job completion at the appropriate level."""
        remaining = len(self._jobs)
        if status == "successful":
            logger.debug(
                "Job %s completed successfully (%d jobs remaining)",
                job_id,
                remaining,
            )
        elif status in ["failed", "error"]:
            logger.error(
                "Job %s completed with status: %s (%d jobs remaining)",
                job_id,
                status,
                remaining,
            )
        elif status == "canceled":
            logger.warning(
                "Job %s was canceled (%d jobs remaining)",
                job_id,
                remaining,
            )

    async def _cleanup_stale_jobs(self):
        """Remove jobs with cancelled or errored futures."""
        async with self._jobs_lock:
            stale_jobs = [
                job_id
                for job_id, job_info in self._jobs.items()
                if job_info["future"].done()
                and (
                    job_info["future"].cancelled()
                    or job_info["future"].exception() is not None
                )
            ]

            for job_id in stale_jobs:
                job_info = self._jobs[job_id]
                if job_info["future"].cancelled():
                    logger.debug(
                        "Removing cancelled job %s from monitor", job_id
                    )
                else:
                    logger.warning(
                        "Removing job %s with error from monitor: %s",
                        job_id,
                        job_info["future"].exception(),
                    )
                del self._jobs[job_id]

    async def _fail_all_jobs(self, exc: Exception):
        """Resolve all pending job futures with the exception."""
        async with self._jobs_lock:
            for _key, job_info in self._jobs.items():
                if not job_info["future"].done():
                    job_info["future"].set_exception(
                        ControllerApiException(str(exc))
                    )
            self._jobs.clear()
            self._monitor_task = None

    async def unregister_job(self, job_url: str):
        """Manually unregister a job (e.g., if cancelled)."""
        key = self._job_key(job_url)
        async with self._jobs_lock:
            if key in self._jobs:
                del self._jobs[key]
                logger.debug(
                    "Unregistered job %s (%d jobs remaining)",
                    key,
                    len(self._jobs),
                )

    def get_monitored_job_count(self) -> int:
        return len(self._jobs)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_jobs": len(self._jobs),
            "total_jobs_monitored": self._total_jobs_monitored,
            "monitor_cycles": self._monitor_start_count,
            "monitor_running": self._monitor_task is not None
            and not self._monitor_task.done(),
        }

    def is_healthy(self) -> bool:
        has_jobs = len(self._jobs) > 0
        monitor_running = (
            self._monitor_task is not None and not self._monitor_task.done()
        )

        if has_jobs and not monitor_running:
            logger.error(
                "Monitor unhealthy: %d jobs registered "
                "but monitor not running",
                len(self._jobs),
            )
            return False

        return True
