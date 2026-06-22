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

import os
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
    async def test_syntax_check_missing_inventory_action(self, capsys):
        """Test syntax-check allows inventory actions without inventory (syntax-only validation)."""
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

            # Should PASS - syntax is valid, runtime config not checked
            await run(args)

            # Verify output
            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

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

    @pytest.mark.asyncio
    async def test_syntax_check_multiple_rulesets(self, capsys):
        """Test syntax-check with multiple rulesets in one file."""
        # Create a rulebook with multiple rulesets
        rulebook_content = [
            {
                "name": "First Ruleset",
                "hosts": "all",
                "sources": [{"name": "range", "range": {"limit": 5}}],
                "rules": [
                    {
                        "name": "rule_1",
                        "condition": "event.i == 1",
                        "action": {"debug": {}},
                    }
                ],
            },
            {
                "name": "Second Ruleset",
                "hosts": "localhost",
                "sources": [{"name": "range", "range": {"limit": 3}}],
                "rules": [
                    {
                        "name": "rule_2",
                        "condition": "event.i == 2",
                        "action": {"print_event": {}},
                    }
                ],
            },
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yml", delete=False
        ) as f:
            yaml.dump(rulebook_content, f)
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

            await run(args)

            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_with_gather_facts(self, capsys):
        """Test syntax-check with gather_facts enabled."""
        rulebook_content = {
            "name": "Gather Facts Rulebook",
            "hosts": "all",
            "gather_facts": True,
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

            await run(args)

            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_multiple_sources(self, capsys):
        """Test syntax-check with multiple event sources."""
        rulebook_content = {
            "name": "Multiple Sources Rulebook",
            "hosts": "all",
            "sources": [
                {"name": "range1", "range": {"limit": 5}},
                {"name": "range2", "range": {"limit": 3}},
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

            await run(args)

            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_complex_conditions(self, capsys):
        """Test syntax-check with complex rule conditions."""
        rulebook_content = {
            "name": "Complex Conditions Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 10}}],
            "rules": [
                {
                    "name": "complex_all",
                    "condition": {
                        "all": [
                            "event.i > 0",
                            "event.i < 10",
                        ]
                    },
                    "action": {"debug": {}},
                },
                {
                    "name": "complex_any",
                    "condition": {
                        "any": [
                            "event.i == 1",
                            "event.i == 5",
                        ]
                    },
                    "action": {"print_event": {}},
                },
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

            await run(args)

            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_with_environment_variables(self, capsys):
        """Test syntax-check with environment variable usage."""
        rulebook_content = {
            "name": "Environment Variables Rulebook",
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

        # Set environment variable for test
        os.environ["TEST_SYNTAX_VAR"] = "test_value"

        try:
            args = Namespace(
                rulebook=rulebook_path,
                syntax_check=True,
                worker=False,
                vars=None,
                env_vars="TEST_SYNTAX_VAR",
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

            await run(args)

            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()
            # Clean up environment variable
            if "TEST_SYNTAX_VAR" in os.environ:
                del os.environ["TEST_SYNTAX_VAR"]

    @pytest.mark.asyncio
    async def test_syntax_check_real_example_rulebook(self, capsys):
        """Test syntax-check with actual example from the repository."""
        # Use the 02_debug.yml example from tests/examples
        example_path = (
            "/Users/bgrimmet/Nextcloud/Projects/Ansible/"
            "ansible-rulebook/tests/examples/02_debug.yml"
        )

        if not Path(example_path).exists():
            pytest.skip("Example rulebook not found")

        args = Namespace(
            rulebook=example_path,
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

        await run(args)

        captured = capsys.readouterr()
        assert "No issues encountered" in captured.out

    @pytest.mark.asyncio
    async def test_syntax_check_execution_strategy(self, capsys):
        """Test syntax-check with execution_strategy specified."""
        rulebook_content = {
            "name": "Parallel Execution Rulebook",
            "hosts": "all",
            "execution_strategy": "parallel",
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

            await run(args)

            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_missing_sources(self):
        """Test syntax-check with missing required sources field."""
        rulebook_content = {
            "name": "Missing Sources Rulebook",
            "hosts": "all",
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

            # Should raise validation error for missing sources
            with pytest.raises(Exception):
                await run(args)

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_missing_rules(self):
        """Test syntax-check with missing required rules field."""
        rulebook_content = {
            "name": "Missing Rules Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
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

            # Should raise validation error for missing rules
            with pytest.raises(Exception):
                await run(args)

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_controller_action_without_config(self, capsys):
        """Test syntax-check allows controller actions without controller config (syntax-only validation)."""
        rulebook_content = {
            "name": "Controller Action Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {
                        "run_job_template": {
                            "name": "Demo Job Template",
                            "organization": "Default"
                        }
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

            # Should PASS - syntax is valid, runtime config not checked
            await run(args)

            # Verify output
            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_workflow_template_action_without_config(self, capsys):
        """Test syntax-check allows workflow template actions without controller config (syntax-only validation)."""
        rulebook_content = {
            "name": "Workflow Template Action Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {
                        "run_workflow_template": {
                            "name": "Demo Workflow Template",
                            "organization": "Default"
                        }
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

            # Should PASS - syntax is valid, runtime config not checked
            await run(args)

            # Verify output
            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()

    @pytest.mark.asyncio
    async def test_syntax_check_run_module_action_without_inventory(self, capsys):
        """Test syntax-check allows run_module actions without inventory (syntax-only validation)."""
        rulebook_content = {
            "name": "Run Module Action Rulebook",
            "hosts": "all",
            "sources": [{"name": "range", "range": {"limit": 5}}],
            "rules": [
                {
                    "name": "test_rule",
                    "condition": "event.i == 1",
                    "action": {
                        "run_module": {
                            "name": "ansible.builtin.debug",
                            "module_args": {"msg": "test"}
                        }
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

            # Should PASS - syntax is valid, runtime config not checked
            await run(args)

            # Verify output
            captured = capsys.readouterr()
            assert "No issues encountered" in captured.out

        finally:
            Path(rulebook_path).unlink()
