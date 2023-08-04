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

from ansible_rulebook.exception import (
    ControllerApiException,
    JobTemplateNotFoundException,
)

logger = logging.getLogger(__name__)


class JobTemplateRunner:
    JOB_TEMPLATE_SLUG = "/api/v2/job_templates"
    CONFIG_SLUG = "/api/v2/config"
    JOB_COMPLETION_STATUSES = ["successful", "failed", "error", "canceled"]

    def __init__(
        self, host: str = "", token: str = "", verify_ssl: str = "yes"
    ):
        self.token = token
        self.host = host
        self.verify_ssl = verify_ssl
        self.refresh_delay = int(
            os.environ.get("EDA_JOB_TEMPLATE_REFRESH_DELAY", 10)
        )
        self._session = None

    async def close_session(self):
        if self._session and not self._session.closed:
            await self._session.close()

    def _create_session(self):
        if self._session is None:
            limit = int(os.getenv("EDA_CONTROLLER_CONNECTION_LIMIT", "30"))
            self._session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=limit),
                headers=self._auth_headers(),
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
        return dict(Authorization=f"Bearer {self.token}")

    @cached_property
    def _sslcontext(self) -> Union[bool, ssl.SSLContext]:
        if self.host.startswith("https"):
            if self.verify_ssl.lower() == "yes":
                return True
            elif not self.verify_ssl.lower() == "no":
                return ssl.create_default_context(cafile=self.verify_ssl)
        return False

    async def _get_job_template_id(self, name: str, organization: str) -> int:
        slug = f"{self.JOB_TEMPLATE_SLUG}/"
        params = {"name": name}

        while True:
            json_body = await self._get_page(slug, params)
            for jt in json_body["results"]:
                if (
                    jt["name"] == name
                    and dpath.get(jt, "summary_fields.organization.name", ".")
                    == organization
                ):
                    return jt["id"]

            if json_body.get("next", None):
                params["page"] = params.get("page", 1) + 1
            else:
                break

        raise JobTemplateNotFoundException(
            (
                f"Job template {name} in organization "
                f"{organization} does not exist"
            )
        )

    async def run_job_template(
        self,
        name: str,
        organization: str,
        job_params: dict,
    ) -> dict:
        job = await self.launch(name, organization, job_params)

        url = job["url"]
        params = {}

        while True:
            # fetch and process job status
            json_body = await self._get_page(url, params)
            job_status = json_body["status"]
            if job_status in self.JOB_COMPLETION_STATUSES:
                return json_body

            await asyncio.sleep(self.refresh_delay)

    async def launch(
        self, name: str, organization: str, job_params: dict
    ) -> dict:
        jt_id = await self._get_job_template_id(name, organization)
        url = urljoin(self.host, f"{self.JOB_TEMPLATE_SLUG}/{jt_id}/launch/")

        try:
            async with self._session.post(
                url, json=job_params, ssl=self._sslcontext
            ) as post_response:
                return json.loads(await post_response.text())
        except aiohttp.ClientError as e:
            logger.error("Error connecting to controller %s", str(e))
            raise ControllerApiException(str(e))


job_template_runner = JobTemplateRunner()
