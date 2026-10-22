#  Copyright 2024 Red Hat, Inc.
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
import time
from functools import cached_property
from http import HTTPStatus
from typing import Optional, Union
from urllib.parse import urljoin

import aiohttp
from aiohttp_retry import ExponentialRetry, RetryClient

from ansible_rulebook import util
from ansible_rulebook.conf import settings

logger = logging.getLogger(__name__)


CLIENT_CONNECT_ERROR_STRING = "Error connecting to Automation Orchestrator: %s"
CLIENT_INVALID_JSON_STRING = (
    "Invalid JSON response from Automation Orchestrator at %s: %s"
)


class AOWorkflowRunnerException(Exception):
    """Base exception for AO Workflow Runner errors."""

    pass


class AOAuthenticationException(AOWorkflowRunnerException):
    """Exception raised when authentication to AO fails."""

    pass


class AOWorkflowNotFoundException(AOWorkflowRunnerException):
    """Exception raised when a workflow cannot be found."""

    pass


class AOExecutionTimeoutException(AOWorkflowRunnerException):
    """Exception raised when workflow execution times out."""

    pass


class AOExecutionFailedException(AOWorkflowRunnerException):
    """Exception raised when workflow execution fails."""

    pass


class AOWorkflowRunner:
    """Client for interacting with Automation Orchestrator (AO) API.

    This singleton class manages authentication and API interactions with
    Automation Orchestrator, including triggering workflows via webhooks and
    monitoring their execution status.
    """

    WORKFLOWS_SLUG = "api/v1/workflows"
    WEBHOOKS_SLUG = "api/v1/webhooks"  # Workflow webhook triggers (not /eda/)
    EXECUTIONS_SLUG = "api/v1/executions"
    AUTH_SLUG = "api/v1/auth/login"
    AUTH_TOKEN_SLUG = "api/v1/auth/token"

    # Terminal execution statuses
    COMPLETED_STATUSES = [
        "completed",
        "completed_with_errors",
        "failed",
        "cancelled",
    ]
    SUCCESS_STATUSES = ["completed"]
    PARTIAL_SUCCESS_STATUSES = ["completed_with_errors"]
    FAILURE_STATUSES = ["failed", "cancelled"]

    def __init__(
        self,
        host: str = "",
        token: str = "",
        username: str = "",
        password: str = "",
        client_id: str = "",
        client_secret: str = "",
        verify_ssl: str = "yes",
    ):
        """Initialize the AO Workflow Runner.

        Args:
            host: AO base URL (e.g., https://ao-host:8080)
            token: Bearer token for authentication
            username: Username for authentication (if token not provided)
            password: Password for authentication (if token not provided)
            client_id: OAuth2 client ID for authentication
            client_secret: OAuth2 client secret for authentication
            verify_ssl: SSL verification setting (yes/no/<path to CA bundle>)

        Note:
            If arguments are not provided, will check environment variables:
            - EDA_AO_URL
            - EDA_AO_TOKEN
            - EDA_AO_CLIENT_ID
            - EDA_AO_CLIENT_SECRET
            - EDA_AO_USERNAME
            - EDA_AO_PASSWORD
            - EDA_AO_SSL_VERIFY
        """
        # Use environment variables as fallback if arguments not provided
        # Prioritize OAuth2 client credentials (recommended for AO service accounts)
        self.token = token
        self._host = ""
        self.host = host or os.environ.get("EDA_AO_URL", "")
        self.client_id = client_id or os.environ.get("EDA_AO_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get(
            "EDA_AO_CLIENT_SECRET", ""
        )
        # Username/password kept for backwards compatibility but not recommended
        self.username = username
        self.password = password
        # For verify_ssl, only use default if no arg and no env var
        if verify_ssl == "yes" and "EDA_AO_SSL_VERIFY" in os.environ:
            self.verify_ssl = os.environ["EDA_AO_SSL_VERIFY"]
        else:
            self.verify_ssl = verify_ssl
        self._session = None
        self._raw_session = None
        self._access_token = None

    @property
    def host(self):
        return self._host

    @host.setter
    def host(self, value: str):
        self._host = util.ensure_trailing_slash(value)

    async def close_session(self):
        """Close the aiohttp session."""
        if self._session:
            await self._session.close()
            self._session = None
        if self._raw_session:
            await self._raw_session.close()
            self._raw_session = None
        self._access_token = None

    def _create_session(self):
        """Create aiohttp session with retry logic."""
        if self._session is None:
            client_session = aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(limit=30),
            )
            self._raw_session = client_session
            retry_options = ExponentialRetry(
                attempts=settings.controller_retry_attempts,
                start_timeout=2.0,
                max_timeout=settings.controller_retry_max_timeout,
                factor=2.0,
                statuses={429, 500, 502, 503, 504},
                retry_all_server_errors=False,
                exceptions={aiohttp.ClientConnectorError},
                methods={"GET", "POST"},
            )
            self._session = RetryClient(
                client_session=client_session,
                retry_options=retry_options,
                raise_for_status=True,
            )

    @cached_property
    def _sslcontext(self) -> Union[bool, ssl.SSLContext]:
        """Get SSL context for HTTPS connections."""
        if self.host.startswith("https"):
            if self.verify_ssl.lower() in ["yes", "true"]:
                return True
            if self.verify_ssl.lower() not in ["no", "false"]:
                return ssl.create_default_context(cafile=self.verify_ssl)
        return False

    def _load_from_environment(self):
        """Load credentials from environment variables if not already set.

        This is called lazily to ensure environment variables set by AAP EDA
        credentials are available before we try to use them.
        """
        # Check for empty or default host (empty string becomes "/" via setter)
        if not self.host or self.host == "/":
            env_host = os.environ.get("EDA_AO_URL", "")
            if env_host:
                self.host = env_host
                logger.debug("Loaded AO URL from environment: %s", env_host)

        if not self.token:
            self.token = os.environ.get("EDA_AO_TOKEN", "")
            if self.token:
                logger.debug("Loaded AO token from environment")

        if not self.client_id:
            self.client_id = os.environ.get("EDA_AO_CLIENT_ID", "")
            if self.client_id:
                logger.debug(
                    "Loaded AO client_id from environment: %s", self.client_id
                )

        if not self.client_secret:
            self.client_secret = os.environ.get("EDA_AO_CLIENT_SECRET", "")
            if self.client_secret:
                logger.debug(
                    "Loaded AO client_secret from environment (length: %d)",
                    len(self.client_secret),
                )

        if self.verify_ssl == "yes" and "EDA_AO_SSL_VERIFY" in os.environ:
            self.verify_ssl = os.environ["EDA_AO_SSL_VERIFY"]
            logger.debug(
                "Loaded AO SSL verify from environment: %s", self.verify_ssl
            )

        # Log what we have after loading
        logger.debug(
            "AO credentials after env load: host=%s, has_token=%s, has_client_id=%s, has_client_secret=%s",
            bool(self.host and self.host != "/"),
            bool(self.token),
            bool(self.client_id),
            bool(self.client_secret),
        )

    async def _get_access_token(self) -> str:
        """Authenticate and get access token.

        Returns:
            str: Bearer token for API requests

        Raises:
            AOAuthenticationException: If authentication fails
        """
        # Load from environment if needed (lazy loading for AAP EDA)
        self._load_from_environment()

        # Direct token takes precedence
        if self.token:
            return self.token

        # OAuth2 client_credentials flow (always fetch fresh token)
        if self.client_id and self.client_secret:
            return await self._get_oauth2_token()

        # Cached token from username/password auth
        if self._access_token:
            return self._access_token

        # Username/password auth
        if self.username and self.password:
            return await self._get_username_password_token()

        raise AOAuthenticationException(
            "Either token, client_id/client_secret, or username/password "
            "must be provided"
        )

    async def _get_oauth2_token(self) -> str:
        """Get OAuth2 token using client_credentials grant.

        Returns:
            str: Bearer token for API requests

        Raises:
            AOAuthenticationException: If authentication fails
        """
        url = urljoin(self.host, self.AUTH_TOKEN_SLUG)
        auth_data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }

        try:
            self._create_session()
            async with self._raw_session.post(
                url, data=auth_data, ssl=self._sslcontext
            ) as response:
                response.raise_for_status()
                response_text = await response.text()
                if not response_text:
                    raise AOAuthenticationException(
                        "Empty OAuth2 token response"
                    )
                result = json.loads(response_text)
                access_token = result.get("access_token")
                if not access_token:
                    raise AOAuthenticationException(
                        "No access_token in OAuth2 response"
                    )
                logger.debug("Successfully obtained OAuth2 access token")
                return access_token
        except aiohttp.ClientResponseError as e:
            logger.error("OAuth2 authentication failed: %s", e)
            raise AOAuthenticationException(
                f"OAuth2 authentication failed: {e}"
            )
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error("OAuth2 authentication error: %s", e)
            raise AOAuthenticationException(
                f"OAuth2 authentication error: {e}"
            )

    async def _get_username_password_token(self) -> str:
        """Get token using username/password authentication.

        Returns:
            str: Bearer token for API requests

        Raises:
            AOAuthenticationException: If authentication fails
        """
        url = urljoin(self.host, self.AUTH_SLUG)
        auth_data = {
            "username": self.username,
            "password": self.password,
        }

        try:
            self._create_session()
            async with self._raw_session.post(
                url, json=auth_data, ssl=self._sslcontext
            ) as response:
                response.raise_for_status()
                response_text = await response.text()
                if not response_text:
                    raise AOAuthenticationException(
                        "Empty authentication response"
                    )
                result = json.loads(response_text)
                self._access_token = result.get("access_token")
                if not self._access_token:
                    raise AOAuthenticationException(
                        "No access_token in authentication response"
                    )
                return self._access_token
        except aiohttp.ClientResponseError as e:
            logger.error("Authentication failed: %s", e)
            raise AOAuthenticationException(f"Authentication failed: {e}")
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error("Authentication error: %s", e)
            raise AOAuthenticationException(f"Authentication error: {e}")

    async def _api_request(self, method: str, path: str, **kwargs) -> dict:
        """Make authenticated API request to AO.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (will be joined with host)
            **kwargs: Additional arguments for aiohttp request

        Returns:
            dict: JSON response from API

        Raises:
            AOWorkflowRunnerException: If request fails
        """
        access_token = await self._get_access_token()
        url = urljoin(self.host, path)

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"

        try:
            self._create_session()
            async with self._session.request(
                method, url, headers=headers, ssl=self._sslcontext, **kwargs
            ) as response:
                response_text = await response.text()
                if not response_text:
                    return {}
                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(CLIENT_INVALID_JSON_STRING, url, str(e))
                    raise AOWorkflowRunnerException(
                        f"Invalid JSON response from AO: {e}"
                    )
        except aiohttp.ClientError as e:
            logger.error(CLIENT_CONNECT_ERROR_STRING, str(e))
            raise AOWorkflowRunnerException(f"AO API request failed: {e}")

    async def lookup_webhook_path(
        self, workflow_name: str, project: Optional[str] = None
    ) -> str:
        """Look up webhook path for a workflow by name.

        Args:
            workflow_name: Name of the workflow
            project: Optional project name to narrow search

        Returns:
            str: Webhook path for the workflow

        Raises:
            AOWorkflowNotFoundException: If workflow not found
        """
        params = {"name": workflow_name}
        if project:
            params["project"] = project

        result = await self._api_request(
            "GET", self.WORKFLOWS_SLUG, params=params
        )

        workflows = result.get("results", [])
        if not workflows:
            raise AOWorkflowNotFoundException(
                f"Workflow '{workflow_name}' not found"
                + (f" in project '{project}'" if project else "")
            )

        workflow = workflows[0]
        webhook_path = workflow.get("webhook_path")
        if not webhook_path:
            raise AOWorkflowNotFoundException(
                f"Workflow '{workflow_name}' has no webhook_path configured"
            )

        return webhook_path

    async def trigger_workflow(
        self, webhook_path: str, payload: Optional[dict] = None
    ) -> str:
        """Trigger a workflow via EDA webhook.

        Args:
            webhook_path: Webhook UUID or path (e.g., "755d5f81-a574-4ea3-8461-1934cb4a5c51")
            payload: Optional payload data to send

        Returns:
            str: Execution ID

        Raises:
            AOWorkflowRunnerException: If trigger fails
        """
        path = f"{self.WEBHOOKS_SLUG}/{webhook_path}"
        result = await self._api_request("POST", path, json=payload or {})

        execution_id = result.get("execution_id")
        if not execution_id:
            raise AOWorkflowRunnerException(
                "No execution_id in webhook trigger response"
            )

        logger.info(
            "Triggered workflow via webhook '%s', execution_id: %s",
            webhook_path,
            execution_id,
        )
        return execution_id

    async def get_execution_status(self, execution_id: str) -> dict:
        """Get execution status.

        Args:
            execution_id: Execution ID to check

        Returns:
            dict: Execution status information
        """
        path = f"{self.EXECUTIONS_SLUG}/{execution_id}"
        return await self._api_request("GET", path)

    async def wait_for_execution(
        self,
        execution_id: str,
        timeout: int = 600,
        poll_interval: int = 5,
    ) -> dict:
        """Wait for execution to complete.

        Args:
            execution_id: Execution ID to monitor
            timeout: Maximum time to wait in seconds
            poll_interval: Seconds between status checks

        Returns:
            dict: Final execution status

        Raises:
            AOExecutionTimeoutException: If execution times out
        """
        start_time = time.time()
        logger.info(
            "Waiting for execution %s (timeout: %ds, poll: %ds)",
            execution_id,
            timeout,
            poll_interval,
        )

        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise AOExecutionTimeoutException(
                    f"Execution {execution_id} timed out after {timeout}s"
                )

            try:
                execution = await self.get_execution_status(execution_id)
                status = execution.get("status")

                logger.debug(
                    "Execution %s status: %s (elapsed: %.1fs)",
                    execution_id,
                    status,
                    elapsed,
                )

                if status in self.COMPLETED_STATUSES:
                    logger.info(
                        "Execution %s completed with status: %s",
                        execution_id,
                        status,
                    )
                    return execution

                await asyncio.sleep(poll_interval)

            except AOWorkflowRunnerException as e:
                logger.warning(
                    "Error checking execution status, will retry: %s", e
                )
                await asyncio.sleep(poll_interval)

    def is_execution_successful(
        self, execution: dict, treat_errors_as_failure: bool = True
    ) -> bool:
        """Check if execution was successful.

        Args:
            execution: Execution dict from API
            treat_errors_as_failure: Treat completed_with_errors as failure

        Returns:
            bool: True if successful
        """
        status = execution.get("status")

        if status in self.SUCCESS_STATUSES:
            return True

        if status in self.PARTIAL_SUCCESS_STATUSES:
            return not treat_errors_as_failure

        return False


# Singleton instance
ao_workflow_runner = AOWorkflowRunner()
