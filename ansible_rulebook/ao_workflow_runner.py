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
    PROJECTS_SLUG = "api/v1/projects"
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
    # Seconds before its reported expiry at which a cached access token is
    # no longer used
    TOKEN_EXPIRY_MARGIN = 60
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
        # Prioritize OAuth2 client credentials (recommended for AO service
        # accounts)
        self.token = token
        self._host = ""
        self.host = host or os.environ.get("EDA_AO_URL", "")
        self.client_id = client_id or os.environ.get("EDA_AO_CLIENT_ID", "")
        self.client_secret = client_secret or os.environ.get(
            "EDA_AO_CLIENT_SECRET", ""
        )
        # Username/password kept for backwards compatibility but not
        # recommended
        self.username = username
        self.password = password
        # For verify_ssl, only use default if no arg and no env var
        if verify_ssl == "yes" and "EDA_AO_SSL_VERIFY" in os.environ:
            self.verify_ssl = os.environ["EDA_AO_SSL_VERIFY"]
        else:
            self.verify_ssl = verify_ssl
        self._session = None
        self._raw_session = None
        self._post_retry_options = None
        self._access_token = None
        self._access_token_expires_at = None
        self._access_token_key = None
        self._sslcontext_key = None
        self._sslcontext_value = False
        # A runner created by with_overrides() already carries the settings
        # resolved from the environment and must not read them again.
        self._use_environment = True

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
        self._invalidate_access_token()

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
                methods={"GET"},
            )
            # POST retries are limited to 429/502/503, as in
            # job_template_runner. A webhook POST starts a workflow
            # execution and AO provides no idempotency for it, so a POST
            # answered with 500 or 504 is not sent again: the gateway may
            # return them after AO accepted the request, and a second
            # POST would start the workflow twice.
            self._post_retry_options = ExponentialRetry(
                attempts=settings.controller_retry_attempts,
                start_timeout=2.0,
                max_timeout=settings.controller_retry_max_timeout,
                factor=2.0,
                statuses={429, 502, 503},
                retry_all_server_errors=False,
                exceptions={aiohttp.ClientConnectorError},
                methods={"POST"},
            )
            self._session = RetryClient(
                client_session=client_session,
                retry_options=retry_options,
                raise_for_status=True,
            )

    @property
    def _sslcontext(self) -> Union[bool, ssl.SSLContext]:
        """Get SSL context for HTTPS connections.

        The context is rebuilt whenever the host or the verify_ssl setting
        changes, so a new setting is never ignored in favor of an old one.
        """
        key = (self.host, self.verify_ssl)
        if self._sslcontext_key != key:
            self._sslcontext_value = self._build_sslcontext()
            self._sslcontext_key = key
        return self._sslcontext_value

    def _build_sslcontext(self) -> Union[bool, ssl.SSLContext]:
        """Translate verify_ssl (yes/no/<CA bundle>) into an aiohttp value."""
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
        if not self._use_environment:
            return

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
            "AO credentials after env load: host=%s, has_token=%s, "
            "has_client_id=%s, has_client_secret=%s",
            bool(self.host and self.host != "/"),
            bool(self.token),
            bool(self.client_id),
            bool(self.client_secret),
        )

    def with_overrides(
        self,
        host: str = "",
        client_id: str = "",
        client_secret: str = "",
        verify_ssl: str = "",
    ) -> "AOWorkflowRunner":
        """Create a runner for one action with its own connection settings.

        The new runner starts from the settings of this runner and replaces
        the ones given. This runner is left untouched, so the settings that
        one action passes never reach another action.

        Args:
            host: AO base URL to use instead of the configured one
            client_id: OAuth2 client ID to use instead of the configured one
            client_secret: OAuth2 client secret to use instead of the
                configured one
            verify_ssl: SSL verification setting (yes/no/<path to CA bundle>)
                to use instead of the configured one

        Returns:
            AOWorkflowRunner: A new runner; the caller must close its session
        """
        self._load_from_environment()
        # Client credentials given to the action take precedence over a
        # token or a username/password configured globally.
        own_credentials = bool(client_id or client_secret)
        runner = AOWorkflowRunner(
            host=host or self.host,
            token="" if own_credentials else self.token,
            username="" if own_credentials else self.username,
            password="" if own_credentials else self.password,
            client_id=client_id or self.client_id,
            client_secret=client_secret or self.client_secret,
        )
        # Set after the constructor: an explicit "yes" must not be replaced
        # by EDA_AO_SSL_VERIFY, which the constructor does for the default.
        runner.verify_ssl = verify_ssl or self.verify_ssl
        runner._use_environment = False
        return runner

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

        # Token obtained earlier with the current settings and still valid
        cached_token = self._cached_access_token()
        if cached_token:
            return cached_token

        # OAuth2 client_credentials flow
        if self.client_id and self.client_secret:
            return await self._get_oauth2_token()

        # Username/password auth
        if self.username and self.password:
            return await self._get_username_password_token()

        raise AOAuthenticationException(
            "Either token, client_id/client_secret, or username/password "
            "must be provided"
        )

    def _credentials_key(self) -> tuple:
        """Settings an access token was issued for."""
        return (
            self.host,
            self.client_id,
            self.client_secret,
            self.username,
            self.password,
        )

    def _cached_access_token(self) -> Optional[str]:
        """Return the cached access token while it can still be used.

        A token is reused only for the settings it was issued for and until
        TOKEN_EXPIRY_MARGIN seconds before the expiry reported by AO.
        """
        if not self._access_token:
            return None
        if self._access_token_key != self._credentials_key():
            return None
        if (
            self._access_token_expires_at is not None
            and time.monotonic() >= self._access_token_expires_at
        ):
            return None
        return self._access_token

    def _invalidate_access_token(self) -> None:
        """Forget the cached access token."""
        self._access_token = None
        self._access_token_expires_at = None
        self._access_token_key = None

    def _store_access_token(
        self, access_token: str, expires_in, always: bool
    ) -> None:
        """Cache an access token until shortly before it expires.

        Args:
            access_token: Token returned by AO
            expires_in: Lifetime in seconds reported by AO, if any
            always: Cache the token even when AO reports no lifetime
        """
        try:
            lifetime = float(expires_in)
        except (TypeError, ValueError):
            lifetime = None

        if lifetime is None:
            if not always:
                return
            expires_at = None
        elif lifetime <= self.TOKEN_EXPIRY_MARGIN:
            return
        else:
            expires_at = time.monotonic() + lifetime - self.TOKEN_EXPIRY_MARGIN

        self._access_token = access_token
        self._access_token_expires_at = expires_at
        self._access_token_key = self._credentials_key()

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
                # Reused until shortly before the expiry reported by AO.
                # Without expires_in a new token is requested every time.
                self._store_access_token(
                    access_token, result.get("expires_in"), always=False
                )
                return access_token
        except aiohttp.ClientResponseError as e:
            logger.error("OAuth2 authentication failed: %s", e)
            raise AOAuthenticationException(
                f"OAuth2 authentication failed: {e}"
            ) from e
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error("OAuth2 authentication error: %s", e)
            raise AOAuthenticationException(
                f"OAuth2 authentication error: {e}"
            ) from e

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
                access_token = result.get("access_token")
                if not access_token:
                    raise AOAuthenticationException(
                        "No access_token in authentication response"
                    )
                self._store_access_token(
                    access_token, result.get("expires_in"), always=True
                )
                return access_token
        except aiohttp.ClientResponseError as e:
            logger.error("Authentication failed: %s", e)
            raise AOAuthenticationException(
                f"Authentication failed: {e}"
            ) from e
        except (aiohttp.ClientError, json.JSONDecodeError) as e:
            logger.error("Authentication error: %s", e)
            raise AOAuthenticationException(
                f"Authentication error: {e}"
            ) from e

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
        base_headers = kwargs.pop("headers", {})

        for attempt in (1, 2):
            # Load the settings first: the cache is checked against them
            self._load_from_environment()
            from_cache = self._cached_access_token() is not None
            access_token = await self._get_access_token()
            url = urljoin(self.host, path)

            headers = dict(base_headers)
            headers["Authorization"] = f"Bearer {access_token}"

            try:
                self._create_session()
                if method.upper() == "POST":
                    kwargs["retry_options"] = self._post_retry_options
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    ssl=self._sslcontext,
                    **kwargs,
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
                        ) from e
            except aiohttp.ClientError as e:
                rejected_cached_token = (
                    isinstance(e, aiohttp.ClientResponseError)
                    and e.status == 401
                    and from_cache
                    and attempt == 1
                )
                if rejected_cached_token:
                    # The token was revoked or expired earlier than reported
                    logger.debug(
                        "AO rejected the cached access token, "
                        "requesting a new one"
                    )
                    self._invalidate_access_token()
                    continue
                logger.error(CLIENT_CONNECT_ERROR_STRING, str(e))
                raise AOWorkflowRunnerException(
                    f"AO API request failed: {e}"
                ) from e

    async def _lookup_project_id(self, project: str) -> str:
        """Look up the ID of a project by its name.

        Args:
            project: Name of the project

        Returns:
            str: ID of the project

        Raises:
            AOWorkflowNotFoundException: If the project is not found
        """
        result = await self._api_request(
            "GET", self.PROJECTS_SLUG, params={"name": project}
        )
        for candidate in result.get("resources", []):
            if candidate.get("name") == project:
                return candidate["id"]

        raise AOWorkflowNotFoundException(f"Project '{project}' not found")

    async def lookup_webhook_path(
        self, workflow_name: str, project: Optional[str] = None
    ) -> str:
        """Look up the webhook path of a workflow by the workflow name.

        The webhook path is not part of the workflow itself. It is a
        parameter of the webhook trigger in the published version of the
        workflow, so the lookup takes up to three requests: project (when
        given), workflow and published version.

        Args:
            workflow_name: Name of the workflow
            project: Optional project name, needed when workflows in
                different projects have the same name

        Returns:
            str: Webhook path for the workflow

        Raises:
            AOWorkflowNotFoundException: If the project or the workflow is
                not found, the name is ambiguous, the workflow is not
                published, or it does not have exactly one webhook trigger
        """
        where = f" in project '{project}'" if project else ""
        params = {"name": workflow_name}
        if project:
            params["project_id"] = await self._lookup_project_id(project)

        result = await self._api_request(
            "GET", self.WORKFLOWS_SLUG, params=params
        )
        workflows = [
            workflow
            for workflow in result.get("resources", [])
            if workflow.get("name") == workflow_name
        ]
        if not workflows:
            raise AOWorkflowNotFoundException(
                f"Workflow '{workflow_name}' not found{where}"
            )
        if len(workflows) > 1:
            raise AOWorkflowNotFoundException(
                f"More than one workflow named '{workflow_name}' "
                f"found{where}, set 'project' or use 'webhook_path'"
            )

        workflow = workflows[0]
        version = workflow.get("published_version_number")
        if not version:
            raise AOWorkflowNotFoundException(
                f"Workflow '{workflow_name}' has no published version"
            )

        published = await self._api_request(
            "GET", f"{self.WORKFLOWS_SLUG}/{workflow['id']}/versions/{version}"
        )
        definition = published.get("workflow_definition") or {}
        webhook_paths = [
            trigger["parameters"]["webhook_path"]
            for trigger in definition.get("triggers") or []
            if trigger.get("type") == "webhook_trigger"
            and (trigger.get("parameters") or {}).get("webhook_path")
        ]
        if not webhook_paths:
            raise AOWorkflowNotFoundException(
                f"Workflow '{workflow_name}' has no webhook trigger in its "
                f"published version"
            )
        if len(webhook_paths) > 1:
            raise AOWorkflowNotFoundException(
                f"Workflow '{workflow_name}' has more than one webhook "
                f"trigger ({', '.join(webhook_paths)}), use 'webhook_path'"
            )

        return webhook_paths[0]

    async def trigger_workflow(
        self, webhook_path: str, payload: Optional[dict] = None
    ) -> str:
        """Trigger a workflow via EDA webhook.

        Args:
            webhook_path: Webhook UUID or path
                (e.g., "755d5f81-a574-4ea3-8461-1934cb4a5c51")
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

            except AOAuthenticationException:
                # Authentication errors won't fix themselves, fail fast
                logger.error(
                    "Authentication failed while checking execution %s",
                    execution_id,
                )
                raise
            except AOWorkflowRunnerException as e:
                # Check if this wraps a 4xx client error - those won't fix
                # themselves
                # Exception: 429 (rate limit) is transient, keep polling
                if e.__cause__ and isinstance(
                    e.__cause__, aiohttp.ClientResponseError
                ):
                    status = e.__cause__.status
                    if status == 403:
                        # Being authorized on the webhook trigger allows the
                        # trigger only, reading the execution needs a role.
                        raise AOWorkflowRunnerException(
                            f"Not allowed to read execution {execution_id}. "
                            "The workflow was triggered, but its status "
                            "cannot be checked: the service account needs a "
                            "role that can read executions in the project "
                            "of the workflow, for example project-auditor"
                        ) from e.__cause__
                    if 400 <= status < 500 and status != 429:
                        logger.error(
                            "Client error for execution %s (status %d), "
                            "failing immediately: %s",
                            execution_id,
                            status,
                            e,
                        )
                        raise
                # Retry transient errors (network issues, 5xx server errors,
                # rate limits)
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
