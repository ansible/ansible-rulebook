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
from urllib.parse import urljoin

from drools import ruleset as lang

from ansible_rulebook import terminal
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    ControllerApiException,
    WorkflowJobTemplateNotFoundException,
)
from ansible_rulebook.job_template_runner import job_template_runner
from ansible_rulebook.util import process_controller_host_limit, run_at

from .control import Control
from .helper import Helper
from .metadata import Metadata

logger = logging.getLogger(__name__)


class RunWorkflowTemplate:
    """run_workflow_template action launches a specified workflow template on
    the controller. It waits for the job to be complete.
    """

    def __init__(
        self,
        metadata: Metadata,
        control: Control,
        **action_args,
    ):
        self.helper = Helper(metadata, control, "run_workflow_template")
        self.action_args = action_args
        self.name = self.action_args["name"]
        self.organization = self.action_args["organization"]
        self.job_id = str(uuid.uuid4())
        self.job_args = self.action_args.get("job_args", {})
        self.job_args["limit"] = process_controller_host_limit(
            self.job_args,
            self.helper.control.hosts,
        )
        self.controller_job = {}
        self.display = terminal.Display()

    async def __call__(self):
        logger.info(
            "running workflow template: %s, organization: %s",
            self.name,
            self.organization,
        )
        logger.debug(
            "ruleset: %s, rule %s",
            self.helper.metadata.rule_set,
            self.helper.metadata.rule,
        )

        self.job_args["extra_vars"] = self.helper.collect_extra_vars(
            self.job_args.get("extra_vars", {})
        )
        await self._job_start_event()
        await self._run()

    async def _run(self):
        retries = self.action_args.get("retries", 0)
        if self.action_args.get("retry", False):
            retries = max(self.action_args.get("retries", 0), 1)
        delay = self.action_args.get("delay", 0)

        try:
            for i in range(retries + 1):
                if i > 0:
                    if delay > 0:
                        await asyncio.sleep(delay)
                    logger.info(
                        "Previous run_workflow_template failed. "
                        "Retry %d of %d",
                        i,
                        retries,
                    )
                controller_job = (
                    await job_template_runner.run_workflow_job_template(
                        self.name,
                        self.organization,
                        self.job_args,
                    )
                )
                if controller_job["status"] != "failed":
                    break
        except (
            ControllerApiException,
            WorkflowJobTemplateNotFoundException,
        ) as ex:
            logger.error(ex)
            controller_job = {}
            controller_job["status"] = "failed"
            controller_job["created"] = run_at()
            controller_job["error"] = str(ex)

        self.controller_job = controller_job
        await self._post_process()

    async def _post_process(self) -> None:
        a_log = {
            "name": self.name,
            "organization": self.organization,
            "job_id": self.job_id,
            "status": self.controller_job["status"],
            "run_at": self.controller_job["created"],
            "url": self._controller_job_url(),
            "matching_events": self.helper.get_events(),
        }
        if "error" in self.controller_job:
            a_log["message"] = self.controller_job["error"]
            a_log["reason"] = {"error": self.controller_job["error"]}
        else:
            logger.info(f"job results url: {a_log['url']}")

        await self.helper.send_status(a_log)
        set_facts = self.action_args.get("set_facts", False)
        post_events = self.action_args.get("post_events", False)

        if set_facts or post_events:
            # Default to output events at debug level.
            level = logging.DEBUG

            # If we are printing events adjust the level to the display's
            # current level to guarantee output.
            if settings.print_events:
                level = self.display.level

            ruleset = self.action_args.get(
                "ruleset", self.helper.metadata.rule_set
            )
            self.display.banner("workflow: set-facts", level=level)
            facts = self.controller_job.get("artifacts", {})
            if facts:
                facts = self.helper.embellish_internal_event(facts)
                self.display.output(facts, level=level, pretty=True)
                if set_facts:
                    lang.assert_fact(ruleset, facts)
                if post_events:
                    lang.post(ruleset, facts)
            else:
                self.display.output("Empty facts are not set", level=level)
            self.display.banner(level=level)

    async def _job_start_event(self):
        await self.helper.send_status(
            {
                "run_at": run_at(),
                "matching_events": self.helper.get_events(),
                "action": self.helper.action,
                "hosts": ",".join(self.helper.control.hosts),
                "name": self.name,
                "job_id": self.job_id,
                "ansible_rulebook_id": settings.identifier,
            },
            obj_type="Job",
        )

    def _controller_job_url(self) -> str:
        if "id" in self.controller_job:
            return urljoin(
                job_template_runner.host,
                "/#/jobs/workflow/" f"{self.controller_job['id']}/" "details",
            )
        return ""
