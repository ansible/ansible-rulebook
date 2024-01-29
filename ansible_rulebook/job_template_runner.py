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

import asyncio
import json
import logging
import os
import ssl
from functools import cached_property
from typing import Union
from urllib.parse import urljoin

import aiohttp
import dpath

from ansible_rulebook import util
from ansible_rulebook.exception import (
    ControllerApiException,
    JobTemplateNotFoundException,
    WorkflowJobTemplateNotFoundException,
)

logger = logging.getLogger(__name__)


class JobTemplateRunner:
    UNIFIED_TEMPLATE_SLUG = "api/v2/unified_job_templates/"
    CONFIG_SLUG = "api/v2/config/"
    JOB_COMPLETION_STATUSES = ["successful", "failed", "error", "canceled"]

    def __init__(
        self,
        host: str = "",
        token: str = "",
        username: str = "",
        password: str = "",
        verify_ssl: str = "yes",
    ):
        self.token = token
        self._host = ""
        self.host = host
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.refresh_delay = float(
            os.environ.get("EDA_JOB_TEMPLATE_REFRESH_DELAY", 10.0)
        )
        self._session = None

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = util.ensure_trailing_slash(value)

    async def close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _create_session(self):
        if self._session is None:
            limit = int(os.getenv("EDA_CONTROLLER_CONNECTION_LIMIT", "30"))
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=limit),
                headers=self._auth_headers(),
                auth=self._basic_auth(),
                raise_for_status=True,
            )

    async def _get_page(self, href_slug: str, params: dict) -> dict:
        try:
            url = urljoin(self.host, href_slug)
            self._create_session()
            async with self._session.get(
                url, params=params, ssl=self._sslcontext
            ) as response:
                return json.loads(await response.text())
        except aiohttp.ClientError as e:
            logger.error("Error connecting to controller %s", str(e))
            raise ControllerApiException(str(e))

    async def get_config(self) -> dict:
        logger.info("Attempting to connect to Controller %s", self.host)
        return await self._get_page(self.CONFIG_SLUG, {})

    def _auth_headers(self) -> dict:
        if self.token:
            return dict(Authorization=f"Bearer {self.token}")

    def _basic_auth(self) -> aiohttp.BasicAuth:
        if self.username and self.password:
            return aiohttp.BasicAuth(
                login=self.username, password=self.password
            )

    @cached_property
    def _sslcontext(self) -> Union[bool, ssl.SSLContext]:
        if self.host.startswith("https"):
            if self.verify_ssl.lower() in ["yes", "true"]:
                return True
            if self.verify_ssl.lower() not in ["no", "false"]:
                return ssl.create_default_context(cafile=self.verify_ssl)
        return False

    async def _get_template_obj(
        self, name: str, organization: str, unified_type: str
    ) -> dict:
        params = {"name": name}

        while True:
            json_body = await self._get_page(
                self.UNIFIED_TEMPLATE_SLUG, params
            )
            for jt in json_body["results"]:
                if (
                    jt["type"] == unified_type
                    and jt["name"] == name
                    and dpath.get(
                        jt,
                        "summary_fields.organization.name",
                        ".",
                        organization,
                    )
                    == organization
                ):
                    return {
                        "launch": dpath.get(jt, "related.launch", ".", None),
                        "ask_limit_on_launch": jt["ask_limit_on_launch"],
                        "ask_inventory_on_launch": jt[
                            "ask_inventory_on_launch"
                        ],
                        "ask_variables_on_launch": jt[
                            "ask_variables_on_launch"
                        ],
                    }

            if json_body.get("next", None):
                params["page"] = params.get("page", 1) + 1
            else:
                break

    async def run_job_template(
        self,
        name: str,
        organization: str,
        job_params: dict,
    ) -> dict:
        obj = await self._get_template_obj(name, organization, "job_template")
        if not obj:
            raise JobTemplateNotFoundException(
                (
                    f"Job template {name} in organization "
                    f"{organization} does not exist"
                )
            )
        url = urljoin(self.host, obj["launch"])
        job = await self._launch(job_params, url)
        return await self._monitor_job(job["url"])

    async def run_workflow_job_template(
        self,
        name: str,
        organization: str,
        job_params: dict,
    ) -> dict:
        obj = await self._get_template_obj(
            name, organization, "workflow_job_template"
        )
        if not obj:
            raise WorkflowJobTemplateNotFoundException(
                (
                    f"Workflow template {name} in organization "
                    f"{organization} does not exist"
                )
            )
        url = urljoin(self.host, obj["launch"])
        if not obj["ask_limit_on_launch"] and "limit" in job_params:
            logger.warning(
                "Workflow template %s does not accept limit, removing it", name
            )
            job_params.pop("limit")
        if not obj["ask_variables_on_launch"] and "extra_vars" in job_params:
            logger.warning(
                "Workflow template %s does not accept extra vars, "
                "removing it",
                name,
            )
            job_params.pop("extra_vars")
        job = await self._launch(job_params, url)
        return await self._monitor_job(job["url"])

    async def _monitor_job(self, url) -> dict:
        while True:
            # fetch and process job status
            json_body = await self._get_page(url, {})
            if json_body["status"] in self.JOB_COMPLETION_STATUSES:
                return json_body

            await asyncio.sleep(self.refresh_delay)

    async def _launch(self, job_params: dict, url: str) -> dict:
        body = None
        try:
            async with self._session.post(
                url,
                json=job_params,
                ssl=self._sslcontext,
                raise_for_status=False,
            ) as post_response:
                body = json.loads(await post_response.text())
                post_response.raise_for_status()
                return body
        except aiohttp.ClientError as e:
            logger.error("Error connecting to controller %s", str(e))
            if body:
                logger.error("Error %s", body)
            raise ControllerApiException(str(e))


job_template_runner = JobTemplateRunner()
