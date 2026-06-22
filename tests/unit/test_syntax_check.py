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

"""Tests for --syntax-check functionality."""

import tempfile
from argparse import Namespace
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import yaml

from ansible_rulebook.app import run


class TestSyntaxCheckIntegration:
    """Integration tests for syntax-check mode."""

    @pytest.mark.asyncio
    async def test_syntax_check_valid_rulebook(self, capsys):
        """Test syntax-check with valid rulebook returns success."""
        # Create a valid rulebook
        rulebook_content = {
            "name": "Test Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {"debug": {}},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            yaml.dump([rulebook_content], f)
            rulebook_path = f.name

        try:
            args = Namespace(
                rulebook=rulebook_path,
                syntax_check=True,
                worker=False,
                vars=None,
                env_vars=None,
                inventory=None,
                hot_reload=False,
                project_tarball=None,
                controller_url=None,
                controller_token=None,
                controller_ssl_verify=None,
                controller_username=None,
                controller_password=None,
                websocket_url=None,
                source_dir=None,
                filter_dir=None,
                shutdown_delay=60,
            )

            # Run syntax check
            await run(args)

            # Verify output
            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_invalid_yaml(self):
        """Test syntax-check with invalid YAML reports error."""
        # Create a file with invalid YAML
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            f.write("---\n- name: Test\n  invalid: [\n")
            rulebook_path = f.name

        try:
            args = Namespace(
                rulebook=rulebook_path,
                syntax_check=True,
                worker=False,
                vars=None,
                env_vars=None,
                inventory=None,
                hot_reload=False,
                project_tarball=None,
                controller_url=None,
                controller_token=None,
                controller_ssl_verify=None,
                controller_username=None,
                controller_password=None,
                websocket_url=None,
                source_dir=None,
                filter_dir=None,
                shutdown_delay=60,
            )

            # Should raise YAML parsing error
            with pytest.raises(Exception):
                await run(args)

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_schema_violation(self):
        """Test syntax-check with schema violations reports error."""
        # Create a rulebook that violates the schema (missing required 'name')
        rulebook_content = {
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {"debug": {}},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            yaml.dump([rulebook_content], f)
            rulebook_path = f.name

        try:
            args = Namespace(
                rulebook=rulebook_path,
                syntax_check=True,
                worker=False,
                vars=None,
                env_vars=None,
                inventory=None,
                hot_reload=False,
                project_tarball=None,
                controller_url=None,
                controller_token=None,
                controller_ssl_verify=None,
                controller_username=None,
                controller_password=None,
                websocket_url=None,
                source_dir=None,
                filter_dir=None,
                shutdown_delay=60,
            )

            # Should raise validation error
            with pytest.raises(Exception):
                await run(args)

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_missing_inventory_action(self):
        """Test syntax-check with action requiring inventory."""
        # Create rulebook with run_playbook action but no inventory
        rulebook_content = {
            "name": "Test Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {
                        "run_playbook": {"name": "test.yml"}
                    },
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            yaml.dump([rulebook_content], f)
            rulebook_path = f.name

        try:
            args = Namespace(
                rulebook=rulebook_path,
                syntax_check=True,
                worker=False,
                vars=None,
                env_vars=None,
                inventory=None,
                hot_reload=False,
                project_tarball=None,
                controller_url=None,
                controller_token=None,
                controller_ssl_verify=None,
                controller_username=None,
                controller_password=None,
                websocket_url=None,
                source_dir=None,
                filter_dir=None,
                shutdown_delay=60,
            )

            # Should raise InventoryNeededException
            with pytest.raises(Exception) as exc_info:
                await run(args)
            assert "inventory" in str(exc_info.value).lower()

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_does_not_spawn_sources(self):
        """Test that syntax-check does not actually spawn event sources."""
        rulebook_content = {
            "name": "Test Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {"debug": {}},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            yaml.dump([rulebook_content], f)
            rulebook_path = f.name

        try:
            args = Namespace(
                rulebook=rulebook_path,
                syntax_check=True,
                worker=False,
                vars=None,
                env_vars=None,
                inventory=None,
                hot_reload=False,
                project_tarball=None,
                controller_url=None,
                controller_token=None,
                controller_ssl_verify=None,
                controller_username=None,
                controller_password=None,
                websocket_url=None,
                source_dir=None,
                filter_dir=None,
                shutdown_delay=60,
            )

            # Mock spawn_sources to ensure it's not called
            with patch(
                "ansible_rulebook.app.spawn_sources"
            ) as mock_spawn_sources:
                await run(args)
                # spawn_sources should NOT be called in syntax-check mode
                mock_spawn_sources.assert_not_called()

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_with_variables(self, capsys):
        """Test syntax-check with variable substitution."""
        # Create a variables file
        vars_content = {"test_limit": 10}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            yaml.dump(vars_content, f)
            vars_path = f.name

        # Create a rulebook using variables
        rulebook_content = {
            "name": "Test Rulebook",
            "hosts": "all",
            "sources": [
                {"name": "range", "range": {"limit": "{{ test_limit }}"}}
            ],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {"debug": {}},
                }
            ],
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            yaml.dump([rulebook_content], f)
            rulebook_path = f.name

        try:
            args = Namespace(
                rulebook=rulebook_path,
                syntax_check=True,
                worker=False,
                vars=vars_path,
                env_vars=None,
                inventory=None,
                hot_reload=False,
                project_tarball=None,
                controller_url=None,
                controller_token=None,
                controller_ssl_verify=None,
                controller_username=None,
                controller_password=None,
                websocket_url=None,
                source_dir=None,
                filter_dir=None,
                shutdown_delay=60,
            )

            # Run syntax check
            await run(args)

            # Verify output
            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()
            Path(vars_path).unlink()
