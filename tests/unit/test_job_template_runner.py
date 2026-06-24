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

"""Unit tests for ansible_rulebook.job_template_runner module."""

from unittest.mock import AsyncMock, Mock

import aiohttp
import pytest

from ansible_rulebook.job_template_runner import JobTemplateRunner


class TestJobTemplateRunnerSessions:
    """Tests for JobTemplateRunner session management."""

    @pytest.mark.asyncio
    async def test_init_creates_no_sessions(self):
        """Test that __init__ doesn't create sessions immediately."""
        runner = JobTemplateRunner(
            host="https://controller.example.com",
            token="test-token",
        )

        assert runner._session is None
        assert runner._raw_session is None

    @pytest.mark.asyncio
    async def test_create_session_stores_both_sessions(self):
        """Test that _create_session stores both raw and retry sessions."""
        runner = JobTemplateRunner(
            host="https://controller.example.com",
            token="test-token",
        )

        try:
            runner._create_session()

            # Both sessions should be created
            assert runner._session is not None
            assert runner._raw_session is not None

            # _session should be a RetryClient
            from aiohttp_retry import RetryClient

            assert isinstance(runner._session, RetryClient)

            # _raw_session should be the underlying aiohttp.ClientSession
            assert isinstance(runner._raw_session, aiohttp.ClientSession)
        finally:
            # Clean up
            await runner.close_session()

    @pytest.mark.asyncio
    async def test_close_session_closes_both(self):
        """Test that close_session closes both sessions."""
        runner = JobTemplateRunner(
            host="https://controller.example.com",
            token="test-token",
        )

        runner._create_session()

        # Store references to verify they exist before closing
        assert runner._session is not None
        assert runner._raw_session is not None

        # Close both sessions
        await runner.close_session()

        # Both should be set to None
        assert runner._session is None
        assert runner._raw_session is None

    @pytest.mark.asyncio
    async def test_get_page_no_retry_uses_raw_session(self):
        """Test that _get_page_no_retry uses raw session directly."""
        runner = JobTemplateRunner(
            host="https://controller.example.com",
            token="test-token",
        )

        try:
            runner._create_session()

            # Mock the raw session's get method
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(
                return_value='{"result": "success"}'
            )
            mock_response.raise_for_status = Mock()
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock()

            runner._raw_session.get = Mock(return_value=mock_response)

            # Call _get_page_no_retry
            result = await runner._get_page_no_retry("api/v2/jobs/", {})

            # Verify raw session was used (not RetryClient)
            runner._raw_session.get.assert_called_once()
            assert result == {"result": "success"}
        finally:
            # Clean up
            await runner.close_session()

    @pytest.mark.asyncio
    async def test_raw_session_no_internal_attribute_access(self):
        """Test that we don't access RetryClient internal attributes."""
        runner = JobTemplateRunner(
            host="https://controller.example.com",
            token="test-token",
        )

        try:
            runner._create_session()

            # Verify we can access _raw_session without accessing
            # _session._client
            assert hasattr(runner, "_raw_session")
            assert runner._raw_session is not None

            # The _raw_session should be the same object that
            # RetryClient wraps
            # But we're accessing it directly, not via RetryClient._client
            assert isinstance(runner._raw_session, aiohttp.ClientSession)

            # Verify we're NOT accessing internal _client attribute
            # This test passes if _raw_session exists and we can use it
            # without needing _session._client
            assert runner._raw_session is not None
        finally:
            # Clean up
            await runner.close_session()
