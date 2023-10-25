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
import logging
import uuid
from typing import Callable
from urllib.parse import urljoin

import drools

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import ControllerApiException
from ansible_rulebook.job_template_runner import job_template_runner
from ansible_rulebook.util import run_at

from .control import Control
from .helper import Helper
from .metadata import Metadata

logger = logging.getLogger(__name__)


class RunBase:
    """Common superclass for "run" actions."""

    @property
    def _job_data(self) -> dict:
        data = {
            "run_at": run_at(),
            "matching_events": self.helper.get_events(),
            "action": self.helper.action,
            "name": self.name,
            "job_id": self.job_id,
            "ansible_rulebook_id": settings.identifier,
        }
        return data

    @property
    def _action_name(self) -> str:
        raise NotImplementedError

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        self.helper = Helper(metadata, control, self._action_name)
        self.action_args = action_args
        self.job_id = str(uuid.uuid4())
        self.name = self.action_args["name"]

    async def __call__(self):
        await self._pre_process()
        await self._job_start_event()
        await self._run()
        await self._post_process()

    async def _do_run(self) -> bool:
        raise NotImplementedError

    async def _run(self):
        retries = self.action_args.get("retries", 0)
        if self.action_args.get("retry", False):
            retries = max(self.action_args.get("retries", 0), 1)
        delay = self.action_args.get("delay", 0)

        for i in range(retries + 1):
            if i > 0:
                if delay > 0:
                    await asyncio.sleep(delay)
                logger.info(
                    "Previous %s failed. Retry %d of %d",
                    self._action_name,
                    i,
                    retries,
                )

            retry = await self._do_run()
            if not retry:
                break

    async def _pre_process(self) -> None:
        pass

    async def _post_process(self) -> None:
        pass

    async def _job_start_event(self):
        await self.helper.send_status(
            self._job_data,
            obj_type="Job",
        )


class RunTemplate(RunBase):
    """Superclass for template-based run actions.  Launches the appropriate
    specified template on the controller. It waits for the job to be complete.
    """

    @property
    def _exceptions(self) -> tuple:
        return (ControllerApiException,)

    @property
    def _job_data(self) -> dict:
        data = super()._job_data
        data["hosts"] = ",".join(self.helper.control.hosts)
        return data

    @property
    def _run_job(self) -> Callable:
        raise NotImplementedError

    @property
    def _template_name(self) -> str:
        raise NotImplementedError

    @property
    def _url_path(self) -> str:
        return self._url_prefix + f"{self.controller_job['id']}/" + "details"

    @property
    def _url_prefix(self) -> str:
        return "/#/"

    def _make_log(self) -> dict:
        log = {
            "organization": self.organization,
            "job_id": self.job_id,
            "status": self.controller_job["status"],
            "run_at": self.controller_job["created"],
            "url": self._controller_job_url(),
            "matching_events": self.helper.get_events(),
        }
        if "error" in self.controller_job:
            log["message"] = self.controller_job["error"]
            log["reason"] = {"error": self.controller_job["error"]}
        return log

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        super().__init__(metadata, control, **action_args)
        self.organization = self.action_args["organization"]
        self.job_args = self.action_args.get("job_args", {})
        self.job_args["limit"] = ",".join(self.helper.control.hosts)
        self.controller_job = {}

    async def __call__(self):
        logger.info(
            "running %s: %s, organization: %s",
            self._template_name,
            self.name,
            self.organization,
        )
        logger.info(
            "ruleset: %s, rule %s",
            self.helper.metadata.rule_set,
            self.helper.metadata.rule,
        )

        self.job_args["extra_vars"] = self.helper.collect_extra_vars(
            self.job_args.get("extra_vars", {})
        )
        await super().__call__()

    async def _do_run(self) -> bool:
        exception = False
        try:
            controller_job = await self._run_job(
                self.name,
                self.organization,
                self.job_args,
            )
        except self._exceptions as ex:
            exception = True
            logger.error(ex)
            controller_job = {}
            controller_job["status"] = "failed"
            controller_job["created"] = run_at()
            controller_job["error"] = str(ex)

        self.controller_job = controller_job

        return (not exception) and (self.controller_job["status"] == "failed")

    async def _post_process(self) -> None:
        a_log = self._make_log()

        await self.helper.send_status(a_log)
        set_facts = self.action_args.get("set_facts", False)
        post_events = self.action_args.get("post_events", False)

        if set_facts or post_events:
            ruleset = self.action_args.get(
                "ruleset", self.helper.metadata.rule_set
            )
            logger.debug("set_facts")
            facts = self.controller_job.get("artifacts", {})
            if facts:
                facts = self.helper.embellish_internal_event(facts)
                logger.debug("facts %s", facts)
                if set_facts:
                    drools.ruleset.assert_fact(ruleset, facts)
                if post_events:
                    drools.ruleset.post(ruleset, facts)
            else:
                logger.debug("Empty facts are not set")

        await super()._post_process()

    def _controller_job_url(self) -> str:
        if "id" in self.controller_job:
            return urljoin(
                job_template_runner.host,
                self._url_path,
            )
        return ""
