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

from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from ansible_rulebook.ao_workflow_runner import (
    AOAuthenticationException,
    AOExecutionTimeoutException,
    AOWorkflowNotFoundException,
    AOWorkflowRunner,
)


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
        mock_response.text = AsyncMock(return_value='{"error": "Unauthorized"}')
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        try:
            runner._create_session()
            runner._raw_session.post = Mock(return_value=mock_response)

            with pytest.raises(AOAuthenticationException):
                await runner._get_access_token()
        finally:
            await runner.close_session()


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
            runner.is_execution_successful(execution, treat_errors_as_failure=True)
            is False
        )

    @pytest.mark.asyncio
    async def test_is_execution_successful_with_errors_treat_as_success(self):
        """Test completed_with_errors treated as success."""
        runner = AOWorkflowRunner()

        execution = {"status": "completed_with_errors"}
        assert (
            runner.is_execution_successful(execution, treat_errors_as_failure=False)
            is True
        )

    @pytest.mark.asyncio
    async def test_is_execution_successful_failed(self):
        """Test failed execution check."""
        runner = AOWorkflowRunner()

        execution = {"status": "failed"}
        assert runner.is_execution_successful(execution) is False
