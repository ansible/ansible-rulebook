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

"""Unit tests for ansible_rulebook.ao_workflow_runner module."""

import time
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest
import pytest_asyncio
from aioresponses import aioresponses
from yarl import URL

from ansible_rulebook.ao_workflow_runner import (
    AOAuthenticationException,
    AOExecutionTimeoutException,
    AOWorkflowNotFoundException,
    AOWorkflowRunner,
    AOWorkflowRunnerException,
)
from ansible_rulebook.conf import settings

AO_HOST = "https://ao.example.com"
WEBHOOK_URL = f"{AO_HOST}/api/v1/webhooks/disk-cleanup"
EXECUTION_URL = f"{AO_HOST}/api/v1/executions/exec-1"
TOKEN_URL = f"{AO_HOST}/api/v1/auth/token"


def _calls(mocked, method, url):
    """Number of requests that aioresponses received for method and url."""
    return len(mocked.requests.get((method, URL(url)), []))


@pytest_asyncio.fixture
async def token_runner(monkeypatch):
    """Runner with a static token and retries without delay."""
    monkeypatch.setattr(settings, "controller_retry_attempts", 3)
    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    runner = AOWorkflowRunner(host=AO_HOST, token="static-token")
    yield runner
    await runner.close_session()


class TestAOWorkflowRunnerInit:
    """Tests for AOWorkflowRunner initialization."""

    def test_init_with_token(self):
        """Test initialization with bearer token."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        assert runner.host == "https://ao.example.com/"
        assert runner.token == "test-token"
        assert runner._session is None
        assert runner._access_token is None

    def test_init_with_username_password(self):
        """Test initialization with username/password."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            username="user",
            password="pass",
        )

        assert runner.username == "user"
        assert runner.password == "pass"
        assert runner.token == ""

    def test_init_from_environment_variables(self):
        """Test initialization from environment variables."""
        import os

        # Set environment variables
        os.environ["EDA_AO_URL"] = "https://ao-env.example.com"
        os.environ["EDA_AO_CLIENT_ID"] = "env-client-id"
        os.environ["EDA_AO_CLIENT_SECRET"] = "env-client-secret"
        os.environ["EDA_AO_SSL_VERIFY"] = "no"

        try:
            # Initialize without arguments - should read from env
            runner = AOWorkflowRunner()

            assert runner.host == "https://ao-env.example.com/"
            assert runner.client_id == "env-client-id"
            assert runner.client_secret == "env-client-secret"
            assert runner.verify_ssl == "no"
        finally:
            # Clean up environment variables
            del os.environ["EDA_AO_URL"]
            del os.environ["EDA_AO_CLIENT_ID"]
            del os.environ["EDA_AO_CLIENT_SECRET"]
            del os.environ["EDA_AO_SSL_VERIFY"]

    def test_init_args_override_environment(self):
        """Test that explicit arguments override environment variables."""
        import os

        os.environ["EDA_AO_URL"] = "https://ao-env.example.com"
        os.environ["EDA_AO_CLIENT_ID"] = "env-client-id"

        try:
            # Explicit arguments should take precedence
            runner = AOWorkflowRunner(
                host="https://ao-arg.example.com",
                client_id="arg-client-id",
            )

            assert runner.host == "https://ao-arg.example.com/"
            assert runner.client_id == "arg-client-id"
        finally:
            del os.environ["EDA_AO_URL"]
            del os.environ["EDA_AO_CLIENT_ID"]

    @pytest.mark.asyncio
    async def test_lazy_loading_from_environment(self):
        """Test that environment variables are loaded lazily when needed."""
        import os

        # Create runner with empty values
        runner = AOWorkflowRunner()

        # Set environment variables AFTER initialization
        os.environ["EDA_AO_URL"] = "https://ao-lazy.example.com"
        os.environ["EDA_AO_CLIENT_ID"] = "lazy-client-id"
        os.environ["EDA_AO_CLIENT_SECRET"] = "lazy-client-secret"

        try:
            # Call _load_from_environment manually to simulate what happens
            # in _get_access_token
            runner._load_from_environment()

            # Should have picked up the environment variables
            assert runner.host == "https://ao-lazy.example.com/"
            assert runner.client_id == "lazy-client-id"
            assert runner.client_secret == "lazy-client-secret"
        finally:
            del os.environ["EDA_AO_URL"]
            del os.environ["EDA_AO_CLIENT_ID"]
            del os.environ["EDA_AO_CLIENT_SECRET"]


class TestAOWorkflowRunnerSessions:
    """Tests for session management."""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test session creation."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        try:
            runner._create_session()

            assert runner._session is not None
            assert runner._raw_session is not None
            assert isinstance(runner._raw_session, aiohttp.ClientSession)
        finally:
            await runner.close_session()

    @pytest.mark.asyncio
    async def test_close_session(self):
        """Test session cleanup."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        runner._create_session()
        assert runner._session is not None

        await runner.close_session()

        assert runner._session is None
        assert runner._raw_session is None
        assert runner._access_token is None


class TestAOWorkflowRunnerAuthentication:
    """Tests for authentication methods."""

    @pytest.mark.asyncio
    async def test_get_access_token_with_token(self):
        """Test using provided bearer token."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        token = await runner._get_access_token()
        assert token == "test-token"

    @pytest.mark.asyncio
    async def test_get_access_token_no_credentials(self):
        """Test authentication failure with no credentials."""
        runner = AOWorkflowRunner(host="https://ao.example.com")

        with pytest.raises(AOAuthenticationException):
            await runner._get_access_token()

    @pytest.mark.asyncio
    async def test_get_access_token_with_username_password(self):
        """Test authentication with username/password."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            username="user",
            password="pass",
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value='{"access_token": "auth-token-123"}'
        )
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        try:
            runner._create_session()
            runner._raw_session.post = Mock(return_value=mock_response)

            token = await runner._get_access_token()

            assert token == "auth-token-123"
            assert runner._access_token == "auth-token-123"
            runner._raw_session.post.assert_called_once()
        finally:
            await runner.close_session()

    @pytest.mark.asyncio
    async def test_get_access_token_auth_failure(self):
        """Test authentication failure handling."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            username="user",
            password="wrong",
        )

        # Create error to raise
        auth_error = aiohttp.ClientResponseError(
            request_info=Mock(),
            history=(),
            status=401,
            message="Unauthorized",
        )

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.raise_for_status = Mock(side_effect=auth_error)
        mock_response.text = AsyncMock(
            return_value='{"error": "Unauthorized"}'
        )
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        try:
            runner._create_session()
            runner._raw_session.post = Mock(return_value=mock_response)

            with pytest.raises(AOAuthenticationException):
                await runner._get_access_token()
        finally:
            await runner.close_session()

    @pytest.mark.asyncio
    async def test_get_access_token_with_oauth2(self):
        """Test OAuth2 client_credentials authentication."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value='{"access_token": "oauth2-token-456"}'
        )
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        try:
            runner._create_session()
            runner._raw_session.post = Mock(return_value=mock_response)

            token = await runner._get_access_token()

            assert token == "oauth2-token-456"
            # OAuth2 tokens are not cached
            assert runner._access_token is None
            runner._raw_session.post.assert_called_once()

            # Verify it was called with form data
            call_args = runner._raw_session.post.call_args
            assert "data" in call_args[1]
            assert call_args[1]["data"]["grant_type"] == "client_credentials"
            assert call_args[1]["data"]["client_id"] == "test-client-id"
            assert (
                call_args[1]["data"]["client_secret"] == "test-client-secret"
            )
        finally:
            await runner.close_session()

    @pytest.mark.asyncio
    async def test_get_access_token_oauth2_always_fresh(self):
        """Test that OAuth2 tokens are fetched fresh each time."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            client_id="test-client-id",
            client_secret="test-client-secret",
        )

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(
            return_value='{"access_token": "fresh-token"}'
        )
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock()

        try:
            runner._create_session()
            runner._raw_session.post = Mock(return_value=mock_response)

            # Get token twice
            token1 = await runner._get_access_token()
            token2 = await runner._get_access_token()

            assert token1 == "fresh-token"
            assert token2 == "fresh-token"

            # Should be called twice (no caching)
            assert runner._raw_session.post.call_count == 2
        finally:
            await runner.close_session()

    @pytest.mark.asyncio
    async def test_init_with_client_credentials(self):
        """Test initialization with OAuth2 client credentials."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            client_id="client-123",
            client_secret="secret-456",
        )

        assert runner.client_id == "client-123"
        assert runner.client_secret == "secret-456"
        assert runner.token == ""


class TestAOWorkflowRunnerWorkflowLookup:
    """Tests for workflow lookup methods."""

    @pytest.mark.asyncio
    async def test_lookup_webhook_path_success(self):
        """Test successful webhook path lookup."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "results": [
                    {
                        "name": "Test Workflow",
                        "webhook_path": "ops/test-workflow",
                    }
                ]
            }

            path = await runner.lookup_webhook_path("Test Workflow")

            assert path == "ops/test-workflow"
            mock_request.assert_called_once_with(
                "GET",
                runner.WORKFLOWS_SLUG,
                params={"name": "Test Workflow"},
            )

    @pytest.mark.asyncio
    async def test_lookup_webhook_path_with_project(self):
        """Test webhook path lookup with project filter."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "results": [
                    {
                        "name": "Test Workflow",
                        "webhook_path": "ops/test-workflow",
                    }
                ]
            }

            path = await runner.lookup_webhook_path(
                "Test Workflow", project="Operations"
            )

            assert path == "ops/test-workflow"
            mock_request.assert_called_once_with(
                "GET",
                runner.WORKFLOWS_SLUG,
                params={"name": "Test Workflow", "project": "Operations"},
            )

    @pytest.mark.asyncio
    async def test_lookup_webhook_path_not_found(self):
        """Test workflow not found error."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"results": []}

            with pytest.raises(AOWorkflowNotFoundException):
                await runner.lookup_webhook_path("Nonexistent Workflow")

    @pytest.mark.asyncio
    async def test_lookup_webhook_path_no_webhook_configured(self):
        """Test workflow with no webhook path configured."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "results": [{"name": "Test Workflow"}]
            }

            with pytest.raises(AOWorkflowNotFoundException):
                await runner.lookup_webhook_path("Test Workflow")


class TestAOWorkflowRunnerTrigger:
    """Tests for workflow trigger methods."""

    @pytest.mark.asyncio
    async def test_trigger_workflow_success(self):
        """Test successful workflow trigger."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"execution_id": "exec-123"}

            execution_id = await runner.trigger_workflow(
                "ops/test", {"key": "value"}
            )

            assert execution_id == "exec-123"
            mock_request.assert_called_once_with(
                "POST",
                "api/v1/webhooks/ops/test",
                json={"key": "value"},
            )

    @pytest.mark.asyncio
    async def test_trigger_workflow_empty_payload(self):
        """Test workflow trigger with no payload."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"execution_id": "exec-456"}

            execution_id = await runner.trigger_workflow("ops/test")

            assert execution_id == "exec-456"
            mock_request.assert_called_once_with(
                "POST", "api/v1/webhooks/ops/test", json={}
            )


class TestAOWorkflowRunnerExecution:
    """Tests for execution monitoring methods."""

    @pytest.mark.asyncio
    async def test_get_execution_status(self):
        """Test getting execution status."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "_api_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "id": "exec-123",
                "status": "running",
            }

            status = await runner.get_execution_status("exec-123")

            assert status["id"] == "exec-123"
            assert status["status"] == "running"

    @pytest.mark.asyncio
    async def test_wait_for_execution_success(self):
        """Test waiting for successful execution."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "get_execution_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.side_effect = [
                {"id": "exec-123", "status": "running"},
                {"id": "exec-123", "status": "completed"},
            ]

            execution = await runner.wait_for_execution(
                "exec-123", timeout=10, poll_interval=1
            )

            assert execution["status"] == "completed"
            assert mock_status.call_count == 2

    @pytest.mark.asyncio
    async def test_wait_for_execution_timeout(self):
        """Test execution timeout."""
        runner = AOWorkflowRunner(
            host="https://ao.example.com",
            token="test-token",
        )

        with patch.object(
            runner, "get_execution_status", new_callable=AsyncMock
        ) as mock_status:
            mock_status.return_value = {"id": "exec-123", "status": "running"}

            with pytest.raises(AOExecutionTimeoutException):
                await runner.wait_for_execution(
                    "exec-123", timeout=1, poll_interval=1
                )

    @pytest.mark.asyncio
    async def test_is_execution_successful_completed(self):
        """Test successful execution check."""
        runner = AOWorkflowRunner()

        execution = {"status": "completed"}
        assert runner.is_execution_successful(execution) is True

    @pytest.mark.asyncio
    async def test_is_execution_successful_with_errors_treat_as_failure(self):
        """Test completed_with_errors treated as failure."""
        runner = AOWorkflowRunner()

        execution = {"status": "completed_with_errors"}
        assert (
            runner.is_execution_successful(
                execution, treat_errors_as_failure=True
            )
            is False
        )

    @pytest.mark.asyncio
    async def test_is_execution_successful_with_errors_treat_as_success(self):
        """Test completed_with_errors treated as success."""
        runner = AOWorkflowRunner()

        execution = {"status": "completed_with_errors"}
        assert (
            runner.is_execution_successful(
                execution, treat_errors_as_failure=False
            )
            is True
        )

    @pytest.mark.asyncio
    async def test_is_execution_successful_failed(self):
        """Test failed execution check."""
        runner = AOWorkflowRunner()

        execution = {"status": "failed"}
        assert runner.is_execution_successful(execution) is False


class TestAOWorkflowRunnerOverrides:
    """Tests for per-action connection settings."""

    def test_with_overrides_returns_separate_runner(self):
        """The shared runner keeps its settings when an action overrides."""
        shared = AOWorkflowRunner(
            host="https://ao.example.com",
            client_id="shared-id",
            client_secret="shared-secret",
        )
        shared.verify_ssl = "yes"

        own = shared.with_overrides(
            host="https://other-ao.example.com",
            client_id="own-id",
            client_secret="own-secret",
            verify_ssl="no",
        )

        assert own is not shared
        assert own.host == "https://other-ao.example.com/"
        assert own.client_id == "own-id"
        assert own.client_secret == "own-secret"
        assert own.verify_ssl == "no"

        assert shared.host == "https://ao.example.com/"
        assert shared.client_id == "shared-id"
        assert shared.client_secret == "shared-secret"
        assert shared.verify_ssl == "yes"

    def test_with_overrides_inherits_missing_settings(self):
        """Settings that the action does not pass come from the runner."""
        shared = AOWorkflowRunner(
            host="https://ao.example.com",
            client_id="shared-id",
            client_secret="shared-secret",
        )
        shared.verify_ssl = "/etc/pki/ca.pem"

        own = shared.with_overrides(host="https://other-ao.example.com")

        assert own.host == "https://other-ao.example.com/"
        assert own.client_id == "shared-id"
        assert own.client_secret == "shared-secret"
        assert own.verify_ssl == "/etc/pki/ca.pem"

    def test_with_overrides_client_credentials_replace_token(self):
        """Client credentials of the action win over a global token."""
        shared = AOWorkflowRunner(
            host="https://ao.example.com",
            token="global-token",
            username="user",
            password="pass",
        )

        own = shared.with_overrides(
            client_id="own-id", client_secret="own-secret"
        )

        assert own.token == ""
        assert own.username == ""
        assert own.password == ""
        assert own.client_id == "own-id"

    def test_with_overrides_keeps_explicit_verify_ssl(self):
        """An explicit "yes" is not replaced by EDA_AO_SSL_VERIFY."""
        import os

        shared = AOWorkflowRunner(host="https://ao.example.com")
        os.environ["EDA_AO_SSL_VERIFY"] = "no"
        try:
            own = shared.with_overrides(verify_ssl="yes")
            own._load_from_environment()

            assert own.verify_ssl == "yes"
            assert own._sslcontext is True
        finally:
            del os.environ["EDA_AO_SSL_VERIFY"]

    def test_sslcontext_follows_verify_ssl(self):
        """Changing verify_ssl is honored on the next request."""
        runner = AOWorkflowRunner(host="https://ao.example.com")

        runner.verify_ssl = "no"
        assert runner._sslcontext is False

        runner.verify_ssl = "yes"
        assert runner._sslcontext is True

        runner.verify_ssl = "no"
        assert runner._sslcontext is False

    def test_sslcontext_follows_host(self):
        """Changing the host scheme is honored on the next request."""
        runner = AOWorkflowRunner(host="https://ao.example.com")
        runner.verify_ssl = "yes"
        assert runner._sslcontext is True

        runner.host = "http://ao.example.com"
        assert runner._sslcontext is False


@pytest_asyncio.fixture
async def oauth_runner(monkeypatch):
    """Runner with client credentials and retries without delay."""
    monkeypatch.setattr(settings, "controller_retry_attempts", 3)
    monkeypatch.setattr(settings, "controller_retry_max_timeout", 0.0)
    runner = AOWorkflowRunner(
        host=AO_HOST, client_id="client-id", client_secret="client-secret"
    )
    yield runner
    await runner.close_session()


def _token(value, expires_in=900):
    """Body of a token response."""
    body = {"access_token": value, "token_type": "Bearer"}
    if expires_in is not None:
        body["expires_in"] = expires_in
    return body


class TestAOWorkflowRunnerTokenCache:
    """Tests for the reuse of OAuth2 access tokens."""

    @pytest.mark.asyncio
    async def test_token_reused_while_valid(self, oauth_runner):
        """One token request serves the calls made within its lifetime."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1"), repeat=True)
            mocked.get(
                EXECUTION_URL, payload={"status": "running"}, repeat=True
            )

            for _ in range(5):
                await oauth_runner.get_execution_status("exec-1")

            assert _calls(mocked, "POST", TOKEN_URL) == 1
            assert _calls(mocked, "GET", EXECUTION_URL) == 5

    @pytest.mark.asyncio
    async def test_trigger_and_wait_use_one_token(self, oauth_runner):
        """Triggering a workflow and waiting for it needs a single token."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1"), repeat=True)
            mocked.post(
                WEBHOOK_URL, status=202, payload={"execution_id": "exec-1"}
            )
            mocked.get(EXECUTION_URL, payload={"status": "pending"})
            mocked.get(EXECUTION_URL, payload={"status": "running"})
            mocked.get(EXECUTION_URL, payload={"status": "completed"})

            execution_id = await oauth_runner.trigger_workflow(
                "disk-cleanup", {}
            )
            execution = await oauth_runner.wait_for_execution(
                execution_id, timeout=30, poll_interval=0
            )

            assert execution["status"] == "completed"
            assert _calls(mocked, "POST", TOKEN_URL) == 1

    @pytest.mark.asyncio
    async def test_token_renewed_after_expiry(self, oauth_runner):
        """An expired token is not sent again."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1"))
            mocked.post(TOKEN_URL, payload=_token("t2"))
            mocked.get(
                EXECUTION_URL, payload={"status": "running"}, repeat=True
            )

            await oauth_runner.get_execution_status("exec-1")
            oauth_runner._access_token_expires_at = time.monotonic() - 1
            await oauth_runner.get_execution_status("exec-1")

            assert _calls(mocked, "POST", TOKEN_URL) == 2
            last_call = mocked.requests[("GET", URL(EXECUTION_URL))][-1]
            assert last_call.kwargs["headers"]["Authorization"] == "Bearer t2"

    @pytest.mark.asyncio
    async def test_token_expiry_uses_margin(self, oauth_runner):
        """A token is renewed TOKEN_EXPIRY_MARGIN seconds before expiry."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1", expires_in=900))

            before = time.monotonic()
            await oauth_runner._get_access_token()
            after = time.monotonic()

            margin = AOWorkflowRunner.TOKEN_EXPIRY_MARGIN
            assert (
                before + 900 - margin
                <= oauth_runner._access_token_expires_at
                <= after + 900 - margin
            )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("expires_in", [None, 0, 30, "not-a-number"])
    async def test_token_not_cached_without_usable_lifetime(
        self, oauth_runner, expires_in
    ):
        """Without a lifetime longer than the margin every call asks anew."""
        with aioresponses() as mocked:
            mocked.post(
                TOKEN_URL, payload=_token("t1", expires_in), repeat=True
            )
            mocked.get(
                EXECUTION_URL, payload={"status": "running"}, repeat=True
            )

            await oauth_runner.get_execution_status("exec-1")
            await oauth_runner.get_execution_status("exec-1")

            assert _calls(mocked, "POST", TOKEN_URL) == 2
            assert oauth_runner._access_token is None

    @pytest.mark.asyncio
    async def test_rejected_cached_token_is_renewed_once(self, oauth_runner):
        """A 401 on a cached token gets one retry with a new token."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1"))
            mocked.post(TOKEN_URL, payload=_token("t2"))
            mocked.get(EXECUTION_URL, payload={"status": "running"})
            mocked.get(EXECUTION_URL, status=401)
            mocked.get(EXECUTION_URL, payload={"status": "completed"})

            await oauth_runner.get_execution_status("exec-1")
            execution = await oauth_runner.get_execution_status("exec-1")

            assert execution["status"] == "completed"
            assert _calls(mocked, "POST", TOKEN_URL) == 2
            last_call = mocked.requests[("GET", URL(EXECUTION_URL))][-1]
            assert last_call.kwargs["headers"]["Authorization"] == "Bearer t2"

    @pytest.mark.asyncio
    async def test_rejected_new_token_is_not_retried(self, oauth_runner):
        """A 401 on a token that was just issued is an error."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1"), repeat=True)
            mocked.get(EXECUTION_URL, status=401, repeat=True)

            with pytest.raises(AOWorkflowRunnerException):
                await oauth_runner.get_execution_status("exec-1")

            assert _calls(mocked, "GET", EXECUTION_URL) == 1
            assert _calls(mocked, "POST", TOKEN_URL) == 1

    @pytest.mark.asyncio
    async def test_token_not_reused_for_other_credentials(self, oauth_runner):
        """A cached token belongs to the credentials it was issued for."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1"))
            mocked.post(TOKEN_URL, payload=_token("t2"))

            assert await oauth_runner._get_access_token() == "t1"
            assert await oauth_runner._get_access_token() == "t1"

            oauth_runner.client_secret = "another-secret"

            assert await oauth_runner._get_access_token() == "t2"
            assert _calls(mocked, "POST", TOKEN_URL) == 2

    @pytest.mark.asyncio
    async def test_close_session_forgets_token(self, oauth_runner):
        """Closing the session drops the cached token."""
        with aioresponses() as mocked:
            mocked.post(TOKEN_URL, payload=_token("t1"))

            await oauth_runner._get_access_token()
            assert oauth_runner._access_token == "t1"

            await oauth_runner.close_session()
            assert oauth_runner._access_token is None
            assert oauth_runner._access_token_expires_at is None


class TestAOWorkflowRunnerRetries:
    """Tests for the retry policy of GET and POST requests."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [500, 504])
    async def test_trigger_not_retried_on_500_and_504(
        self, token_runner, status
    ):
        """A POST answered with 500 or 504 may have started the workflow."""
        with aioresponses() as mocked:
            mocked.post(WEBHOOK_URL, status=status)
            mocked.post(
                WEBHOOK_URL, status=202, payload={"execution_id": "exec-2"}
            )

            with pytest.raises(AOWorkflowRunnerException):
                await token_runner.trigger_workflow("disk-cleanup", {})

            assert _calls(mocked, "POST", WEBHOOK_URL) == 1

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [429, 502, 503])
    async def test_trigger_retried_on_429_502_503(self, token_runner, status):
        """POST retries follow the policy used by job_template_runner."""
        with aioresponses() as mocked:
            mocked.post(WEBHOOK_URL, status=status)
            mocked.post(
                WEBHOOK_URL, status=202, payload={"execution_id": "exec-1"}
            )

            execution_id = await token_runner.trigger_workflow(
                "disk-cleanup", {}
            )

            assert execution_id == "exec-1"
            assert _calls(mocked, "POST", WEBHOOK_URL) == 2

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
    async def test_status_check_retried_on_server_errors(
        self, token_runner, status
    ):
        """GET requests are safe to repeat on every transient error."""
        with aioresponses() as mocked:
            mocked.get(EXECUTION_URL, status=status)
            mocked.get(
                EXECUTION_URL, status=200, payload={"status": "running"}
            )

            execution = await token_runner.get_execution_status("exec-1")

            assert execution["status"] == "running"
            assert _calls(mocked, "GET", EXECUTION_URL) == 2

    @pytest.mark.asyncio
    async def test_trigger_not_retried_on_client_error(self, token_runner):
        """A 4xx answer is final."""
        with aioresponses() as mocked:
            mocked.post(WEBHOOK_URL, status=403)
            mocked.post(
                WEBHOOK_URL, status=202, payload={"execution_id": "exec-2"}
            )

            with pytest.raises(AOWorkflowRunnerException):
                await token_runner.trigger_workflow("disk-cleanup", {})

            assert _calls(mocked, "POST", WEBHOOK_URL) == 1
