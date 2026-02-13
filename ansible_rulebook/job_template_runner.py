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
from http import HTTPStatus
from typing import Optional, Union
from urllib.parse import urljoin, urlparse

import aiohttp
import dpath

from ansible_rulebook import util
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    ControllerApiException,
    ControllerObjectCreateException,
    JobTemplateNotFoundException,
    WorkflowJobTemplateNotFoundException,
)

logger = logging.getLogger(__name__)


CLIENT_CONNECT_ERROR_STRING = "Error connecting to controller: %s"
JOB_TEMPLATE_TYPE = "job_template"
WORKFLOW_TEMPLATE_TYPE = "workflow_template"


class JobTemplateRunner:
    LEGACY_UNIFIED_TEMPLATE_SLUG = "api/v2/unified_job_templates/"
    LEGACY_CONFIG_SLUG = "api/v2/config/"
    LEGACY_LABELS_SLUG = "api/v2/labels/"
    LEGACY_ORGANIZATION_SLUG = "api/v2/organizations/"
    GATEWAY_UNIFIED_TEMPLATE_SLUG = "v2/unified_job_templates/"
    GATEWAY_CONFIG_SLUG = "v2/config/"
    GATEWAY_LABELS_SLUG = "v2/labels/"
    GATEWAY_ORGANIZATION_SLUG = "v2/organizations/"
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
        self._config_slug = self.LEGACY_CONFIG_SLUG
        self._unified_job_template_slug = self.LEGACY_UNIFIED_TEMPLATE_SLUG
        self._labels_slug = self.LEGACY_LABELS_SLUG
        self._organization_slug = self.LEGACY_ORGANIZATION_SLUG

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = util.ensure_trailing_slash(value)
        self._set_slugs(value)

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

    def _set_slugs(self, url):
        urlparts = urlparse(url)
        if urlparts.path and urlparts.path != "/":
            self._config_slug = self.GATEWAY_CONFIG_SLUG
            self._labels_slug = self.GATEWAY_LABELS_SLUG
            self._organization_slug = self.GATEWAY_ORGANIZATION_SLUG
            self._unified_job_template_slug = (
                self.GATEWAY_UNIFIED_TEMPLATE_SLUG
            )
            logger.debug(f"Switched config slug {self._config_slug}")
            logger.debug(
                f"Switched job template slug {self._unified_job_template_slug}"
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
            logger.error(CLIENT_CONNECT_ERROR_STRING, str(e))
            raise ControllerApiException(str(e))

    async def get_config(self) -> dict:
        logger.info("Attempting to connect to Controller %s", self.host)
        return await self._get_page(self._config_slug, {})

    def _auth_headers(self) -> Optional[dict]:
        if self.token:
            return dict(Authorization=f"Bearer {self.token}")
        return None

    def _basic_auth(self) -> Optional[aiohttp.BasicAuth]:
        if self.username and self.password:
            return aiohttp.BasicAuth(
                login=self.username, password=self.password
            )
        return None

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
    ) -> Optional[dict]:
        params = {"name": name}

        while True:
            json_body = await self._get_page(
                self._unified_job_template_slug, params
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
                        "id": jt["id"],
                        "launch": dpath.get(jt, "related.launch", ".", None),
                        "ask_limit_on_launch": jt["ask_limit_on_launch"],
                        "ask_labels_on_launch": jt["ask_labels_on_launch"],
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

        return None

    async def launch_job_template(
        self,
        name: str,
        organization: str,
        job_params: dict,
        labels: Optional[list[str]] = None,
    ) -> str:
        """Launch a job template and return the job URL immediately.

        This method initiates a job template execution on the controller
        and returns immediately with the job URL without waiting for
        completion. This enables asynchronous job monitoring.

        Args:
            name: Name of the job template to launch
            organization: Organization name containing the job template
            job_params: Dictionary of parameters to pass to the job (e.g.,
                extra_vars, inventory, limit)
            labels: Optional list of label names to attach to the job

        Returns:
            str: The job URL for monitoring

        Raises:
            JobTemplateNotFoundException: If the specified job template
                does not exist in the organization
        """
        obj = await self._get_template_obj(name, organization, "job_template")
        if not obj:
            raise JobTemplateNotFoundException(
                (
                    f"Job template {name} in organization "
                    f"{organization} does not exist"
                )
            )

        label_ids = await self._get_labels_for_job(
            name,
            "Job Template",
            organization,
            obj["ask_labels_on_launch"],
            labels,
        )

        if label_ids:
            job_params["labels"] = label_ids

        url = urljoin(self.host, obj["launch"])
        job = await self._launch(job_params, url)
        return job["url"]

    async def run_job_template(
        self,
        name: str,
        organization: str,
        job_params: dict,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """Launch a job template and wait for it to complete.

        This method combines launching a job template with monitoring its
        execution until completion. It's a convenience wrapper around
        launch_job_template() and monitor_job().

        Args:
            name: Name of the job template to run
            organization: Organization name containing the job template
            job_params: Dictionary of parameters to pass to the job
            labels: Optional list of label names to attach to the job

        Returns:
            dict: The final job status information including status, artifacts,
                and other job metadata

        Raises:
            JobTemplateNotFoundException: If the specified job template
                does not exist in the organization
        """
        job_url = await self.launch_job_template(
            name, organization, job_params, labels
        )
        return await self.monitor_job(job_url)

    async def launch_workflow_job_template(
        self,
        name: str,
        organization: str,
        job_params: dict,
        labels: Optional[list[str]] = None,
    ) -> str:
        """Launch a workflow job template and return the job URL immediately.

        This method initiates a workflow job template execution on the
        controller and returns immediately with the job URL without waiting
        for completion. Workflows may not support all parameters that regular
        job templates do (e.g., limit parameter).

        Args:
            name: Name of the workflow job template to launch
            organization: Organization name containing the workflow template
            job_params: Dictionary of parameters to pass to the workflow
                (e.g., extra_vars, inventory). Note: 'limit' is removed if
                the workflow template doesn't accept it.
            labels: Optional list of label names to attach to the workflow job

        Returns:
            str: The workflow job URL for monitoring

        Raises:
            WorkflowJobTemplateNotFoundException: If the specified workflow
                template does not exist in the organization
        """
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

        label_ids = await self._get_labels_for_job(
            name,
            "Workflow Job Template",
            organization,
            obj["ask_labels_on_launch"],
            labels,
        )

        if label_ids:
            job_params["labels"] = label_ids

        url = urljoin(self.host, obj["launch"])
        if not obj["ask_limit_on_launch"] and "limit" in job_params:
            logger.warning(
                "Workflow template %s does not accept limit, removing it", name
            )
            job_params.pop("limit")
        job = await self._launch(job_params, url)
        return job["url"]

    async def run_workflow_job_template(
        self,
        name: str,
        organization: str,
        job_params: dict,
        labels: Optional[list[str]] = None,
    ) -> dict:
        """Launch a workflow job template and wait for it to complete.

        This method combines launching a workflow job template with monitoring
        its execution until completion. It's a convenience wrapper around
        launch_workflow_job_template() and monitor_job().

        Args:
            name: Name of the workflow job template to run
            organization: Organization name containing the workflow template
            job_params: Dictionary of parameters to pass to the workflow
            labels: Optional list of label names to attach to the workflow job

        Returns:
            dict: The final workflow job status information including status,
                artifacts, and other job metadata

        Raises:
            WorkflowJobTemplateNotFoundException: If the specified workflow
                template does not exist in the organization
        """
        job_url = await self.launch_workflow_job_template(
            name, organization, job_params, labels
        )
        return await self.monitor_job(job_url)

    async def monitor_job(self, url) -> dict:
        """Monitor a running job until it reaches a completion status.

        This method polls the controller for job status updates at regular
        intervals until the job reaches a terminal state (successful, failed,
        error, or canceled).

        Args:
            url: The job URL to monitor (can be a regular job or workflow job)

        Returns:
            dict: The final job status information when the job completes,
                including status, artifacts, and other job metadata
        """
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
            logger.error(CLIENT_CONNECT_ERROR_STRING, str(e))
            if body:
                logger.error("Error: %s", body)
            raise ControllerApiException(str(e))

    async def _get_obj_by_name(
        self, href_slug: str, name: str
    ) -> Optional[dict]:
        params = {"name": name}
        result = await self._get_page(href_slug, params)
        if result["count"] == 0:
            return None
        elif result["count"] == 1:
            return result["results"][0]

    async def _create_obj(
        self, href_slug: str, params: dict
    ) -> tuple[Optional[dict], bool]:
        body = None
        try:
            url = urljoin(self.host, href_slug)
            self._create_session()
            async with self._session.post(
                url,
                json=params,
                ssl=self._sslcontext,
                raise_for_status=False,
            ) as post_response:
                body = json.loads(await post_response.text())
                post_response.raise_for_status()
                return body, False
        except aiohttp.ClientResponseError as e:
            # If the object got created by another process, do a retry
            if e.status == HTTPStatus.BAD_REQUEST and "already exists" in str(
                body
            ):
                return None, True
            logger.error(
                f"Client Response Error {e.status} message {e.message}"
            )
            raise ControllerObjectCreateException(str(e))
        except aiohttp.ClientError as e:
            logger.error(CLIENT_CONNECT_ERROR_STRING, str(e))
            raise ControllerApiException(str(e))

    async def _get_or_create_label(
        self, label: str, organization_obj: dict
    ) -> dict:
        obj = await self._get_obj_by_name(self._labels_slug, label)
        if obj:
            return obj

        params = {"name": label, "organization": organization_obj["id"]}
        try:
            obj, retry = await self._create_obj(self._labels_slug, params)
        except ControllerObjectCreateException:
            return {}

        if retry:
            return await self._get_obj_by_name(self._labels_slug, label)
        return obj

    async def _get_label_ids_from_names(
        self, organization: str, labels: Optional[list[str]]
    ) -> list[int]:
        result = []
        organization_obj = await self._get_obj_by_name(
            self._organization_slug, organization
        )
        if not organization_obj:
            logger.warning(
                f"Organization {organization} not found "
                "all labels will be ignored"
            )
            return result

        all_labels = settings.eda_labels
        if labels:
            # Drop any empty strings or non str objects
            all_labels = settings.eda_labels + list(
                filter(lambda s: isinstance(s, str) and s != "", labels)
            )

        # Drop duplicates if any from the label list
        for label in set(all_labels):
            label_obj = await self._get_or_create_label(
                label, organization_obj
            )
            if label_obj:
                result.append(label_obj["id"])
            else:
                logger.warning(
                    f"Could not create label {label} in organization "
                    f"{organization} ignored"
                )
        return result

    async def _get_labels_for_job(
        self,
        name: str,
        obj_type: str,
        organization: str,
        ask_labels_on_launch: bool,
        labels: Optional[list[str]],
    ) -> list[int]:
        if ask_labels_on_launch:
            return await self._get_label_ids_from_names(organization, labels)

        if labels:
            logger.warning(
                (
                    "%s: %s does not accept labels, please "
                    "enable Prompt on launch for Labels. "
                    "Ignoring all labels for now"
                ),
                obj_type,
                name,
            )
        return []

    def _api_slug_prefix(self) -> str:
        return self._unified_job_template_slug.split("unified_job_templates/")[
            0
        ]

    async def get_job_url_from_label(
        self, name: str, organization: str, obj_type: str, label: str
    ) -> Optional[str]:
        """Retrieve a job URL by searching for a job with a specific label.

        This method searches for jobs or workflow jobs associated with a
        template that have been tagged with a specific label. This is useful
        in HA/persistence scenarios where a job was launched in a previous
        execution and needs to be found and monitored.

        Args:
            name: Name of the job or workflow template
            organization: Organization name containing the template
            obj_type: Type of template ("job_template" or
                "workflow_template")
            label: Label name to search for (e.g., "eda-event-uuid-{uuid}")

        Returns:
            Optional[str]: The job URL if a job with the label is found,
                None if no matching job exists

        Raises:
            JobTemplateNotFoundException: If obj_type is "job_template"
                and the template doesn't exist
            WorkflowJobTemplateNotFoundException: If obj_type is
                "workflow_template" and the template doesn't exist
            ValueError: If obj_type is neither "job_template" nor
                "workflow_template"
        """
        if obj_type == JOB_TEMPLATE_TYPE:
            obj = await self._get_template_obj(
                name, organization, "job_template"
            )
            if not obj:
                raise JobTemplateNotFoundException(
                    (
                        f"Job template {name} in organization "
                        f"{organization} does not exist"
                    )
                )
            job_slug = (
                f"{self._api_slug_prefix()}job_templates/{obj['id']}/jobs/"
            )
        elif obj_type == WORKFLOW_TEMPLATE_TYPE:
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
            job_slug = (
                f"{self._api_slug_prefix()}"
                f"workflow_job_templates/{obj['id']}/workflow_jobs/"
            )
        else:
            raise ValueError(
                f"Invalid type {obj_type} passed into job_url_from_label"
            )

        params = {"labels__name": label}
        result = await self._get_page(job_slug, params)
        if result["count"] >= 1:
            return result["results"][0]["url"]

        return None


job_template_runner = JobTemplateRunner()
