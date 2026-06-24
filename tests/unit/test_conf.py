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

"""Unit tests for ansible_rulebook.conf module."""

import uuid
from unittest.mock import patch

from ansible_rulebook.conf import (
    DEFAULT_EDA_LABEL,
    DEFAULT_MAX_CONCURRENT_ACTIONS,
    _Settings,
    settings,
)


class TestSettings:
    """Tests for _Settings class."""

    def test_settings_initialization(self):
        """Test that _Settings initializes with correct default values."""
        test_settings = _Settings()

        # UUID should be generated
        assert isinstance(uuid.UUID(test_settings.identifier), uuid.UUID)

        # Check default values
        assert test_settings.gc_after == 1000
        assert test_settings.default_execution_strategy == "sequential"
        assert test_settings.max_feedback_timeout == 5
        assert test_settings.print_events is False
        assert test_settings.websocket_url is None
        assert test_settings.websocket_ssl_verify == "yes"
        assert test_settings.websocket_token_url is None
        assert test_settings.websocket_access_token is None
        assert test_settings.websocket_refresh_token is None
        assert test_settings.skip_audit_events is False
        assert test_settings.vault is not None
        assert test_settings.eda_labels == [DEFAULT_EDA_LABEL]
        assert test_settings.persistence_enabled is False

    def test_settings_ansible_galaxy_path(self):
        """Test that ansible-galaxy path is set if available."""
        with patch("shutil.which", return_value="/usr/bin/ansible-galaxy"):
            test_settings = _Settings()
            assert (
                test_settings.ansible_galaxy_path == "/usr/bin/ansible-galaxy"
            )

    def test_settings_ansible_galaxy_path_not_found(self):
        """Test that ansible-galaxy path is None if not found."""
        with patch("shutil.which", return_value=None):
            test_settings = _Settings()
            assert test_settings.ansible_galaxy_path is None

    def test_settings_unique_identifier(self):
        """Test that each _Settings instance gets a unique identifier."""
        settings1 = _Settings()
        settings2 = _Settings()

        assert settings1.identifier != settings2.identifier

    def test_settings_vault_initialization(self):
        """Test that Vault instance is created."""
        test_settings = _Settings()
        from ansible_rulebook.vault import Vault

        assert isinstance(test_settings.vault, Vault)

    def test_settings_modification(self):
        """Test that settings values can be modified."""
        test_settings = _Settings()

        # Modify values
        test_settings.print_events = True
        test_settings.skip_audit_events = True
        test_settings.persistence_enabled = True
        test_settings.gc_after = 2000
        test_settings.default_execution_strategy = "parallel"

        # Verify modifications
        assert test_settings.print_events is True
        assert test_settings.skip_audit_events is True
        assert test_settings.persistence_enabled is True
        assert test_settings.gc_after == 2000
        assert test_settings.default_execution_strategy == "parallel"

    def test_settings_websocket_configuration(self):
        """Test setting websocket configuration."""
        test_settings = _Settings()

        test_settings.websocket_url = "wss://example.com"
        test_settings.websocket_ssl_verify = "no"
        test_settings.websocket_token_url = "https://example.com/token"
        test_settings.websocket_access_token = "access_token_123"
        test_settings.websocket_refresh_token = "refresh_token_456"

        assert test_settings.websocket_url == "wss://example.com"
        assert test_settings.websocket_ssl_verify == "no"
        assert test_settings.websocket_token_url == "https://example.com/token"
        assert test_settings.websocket_access_token == "access_token_123"
        assert test_settings.websocket_refresh_token == "refresh_token_456"

    def test_settings_eda_labels_default(self):
        """Test that eda_labels contains default label."""
        test_settings = _Settings()

        assert DEFAULT_EDA_LABEL in test_settings.eda_labels
        assert len(test_settings.eda_labels) == 1

    def test_settings_eda_labels_modification(self):
        """Test modifying eda_labels list."""
        test_settings = _Settings()

        test_settings.eda_labels.append("custom_label")

        assert DEFAULT_EDA_LABEL in test_settings.eda_labels
        assert "custom_label" in test_settings.eda_labels
        assert len(test_settings.eda_labels) == 2

    def test_settings_new_attributes(self):
        """Test concurrency and timeout attributes."""
        test_settings = _Settings()

        assert test_settings.max_concurrent_actions == 0
        assert test_settings.max_actions_semaphore is None
        assert test_settings.max_actions_timeout == 3600
        assert test_settings.max_batch_job_polling_size == 25


class TestConvertType:
    """Tests for _Settings._convert_type static method."""

    def test_convert_type_bool_from_string_true(self):
        """Test converting various true string values to bool."""
        assert _Settings._convert_type("true", bool) is True
        assert _Settings._convert_type("True", bool) is True
        assert _Settings._convert_type("TRUE", bool) is True
        assert _Settings._convert_type("1", bool) is True
        assert _Settings._convert_type("yes", bool) is True
        assert _Settings._convert_type("YES", bool) is True
        assert _Settings._convert_type("on", bool) is True
        assert _Settings._convert_type("ON", bool) is True

    def test_convert_type_bool_from_string_false(self):
        """Test converting various false string values to bool."""
        assert _Settings._convert_type("false", bool) is False
        assert _Settings._convert_type("False", bool) is False
        assert _Settings._convert_type("FALSE", bool) is False
        assert _Settings._convert_type("0", bool) is False
        assert _Settings._convert_type("no", bool) is False
        assert _Settings._convert_type("NO", bool) is False
        assert _Settings._convert_type("off", bool) is False
        assert _Settings._convert_type("", bool) is False

    def test_convert_type_bool_already_bool(self):
        """Test that bool values are returned as-is."""
        assert _Settings._convert_type(True, bool) is True
        assert _Settings._convert_type(False, bool) is False

    def test_convert_type_int_from_string(self):
        """Test converting string to int."""
        assert _Settings._convert_type("42", int) == 42
        assert _Settings._convert_type("0", int) == 0
        assert _Settings._convert_type("-10", int) == -10

    def test_convert_type_int_already_int(self):
        """Test that int values are returned as-is."""
        assert _Settings._convert_type(42, int) == 42
        assert _Settings._convert_type(0, int) == 0

    def test_convert_type_str_from_various(self):
        """Test converting various types to string."""
        assert _Settings._convert_type("hello", str) == "hello"
        assert _Settings._convert_type(42, str) == "42"
        assert _Settings._convert_type(True, str) == "True"

    def test_convert_type_str_already_str(self):
        """Test that string values are returned as-is."""
        assert _Settings._convert_type("hello", str) == "hello"

    def test_convert_type_list_from_json_string(self):
        """Test converting JSON string to list."""
        assert _Settings._convert_type('["a", "b", "c"]', list) == [
            "a",
            "b",
            "c",
        ]
        assert _Settings._convert_type("[1, 2, 3]", list) == [1, 2, 3]
        assert _Settings._convert_type("[]", list) == []

    def test_convert_type_list_from_non_json_string(self):
        """Test converting non-JSON string to list."""
        result = _Settings._convert_type("simple_string", list)
        assert result == ["simple_string"]

    def test_convert_type_list_already_list(self):
        """Test that list values are returned as-is."""
        test_list = ["a", "b", "c"]
        assert _Settings._convert_type(test_list, list) == test_list

    def test_convert_type_list_from_non_list_non_string(self):
        """Test converting non-list, non-string to list."""
        assert _Settings._convert_type(42, list) == [42]


class TestUpdateFromEnv:
    """Tests for _Settings.update_from_env method."""

    def test_update_from_env_int_values(self, monkeypatch):
        """Test updating int settings from environment variables."""
        monkeypatch.setenv("EDA_GC_AFTER", "2000")
        monkeypatch.setenv("EDA_MAX_FEEDBACK_TIMEOUT", "10")
        monkeypatch.setenv("EDA_MAX_CONCURRENT_ACTIONS", "5")
        monkeypatch.setenv("EDA_MAX_ACTIONS_TIMEOUT", "7200")

        test_settings = _Settings()

        assert test_settings.gc_after == 2000
        assert test_settings.max_feedback_timeout == 10
        assert test_settings.max_concurrent_actions == 5
        assert test_settings.max_actions_timeout == 7200

    def test_update_from_env_batch_polling_size(self, monkeypatch):
        """Test updating max_batch_job_polling_size from env var."""
        monkeypatch.setenv("EDA_MAX_BATCH_JOB_POLLING_SIZE", "50")

        test_settings = _Settings()

        assert test_settings.max_batch_job_polling_size == 50

    def test_update_from_env_bool_values(self, monkeypatch):
        """Test updating bool settings from environment variables."""
        monkeypatch.setenv("EDA_PRINT_EVENTS", "true")
        monkeypatch.setenv("EDA_SKIP_AUDIT_EVENTS", "1")
        monkeypatch.setenv("EDA_PERSISTENCE_ENABLED", "yes")

        test_settings = _Settings()

        assert test_settings.print_events is True
        assert test_settings.skip_audit_events is True
        assert test_settings.persistence_enabled is True

    def test_update_from_env_bool_false_values(self, monkeypatch):
        """Test updating bool settings with false values from env."""
        monkeypatch.setenv("EDA_PRINT_EVENTS", "false")
        monkeypatch.setenv("EDA_SKIP_AUDIT_EVENTS", "0")

        test_settings = _Settings()

        assert test_settings.print_events is False
        assert test_settings.skip_audit_events is False

    def test_update_from_env_string_values(self, monkeypatch):
        """Test updating string settings from environment variables."""
        monkeypatch.setenv("EDA_EXECUTION_STRATEGY", "parallel")
        monkeypatch.setenv("EDA_WEBSOCKET_URL", "wss://example.com")
        monkeypatch.setenv("EDA_WEBSOCKET_SSL_VERIFY", "no")
        monkeypatch.setenv(
            "EDA_WEBSOCKET_TOKEN_URL", "https://example.com/token"
        )
        monkeypatch.setenv("EDA_WEBSOCKET_ACCESS_TOKEN", "token123")
        monkeypatch.setenv("EDA_WEBSOCKET_REFRESH_TOKEN", "refresh123")
        monkeypatch.setenv("EDA_PERSISTENCE_ID", "unique-id-123")

        test_settings = _Settings()

        assert test_settings.default_execution_strategy == "parallel"
        assert test_settings.websocket_url == "wss://example.com"
        assert test_settings.websocket_ssl_verify == "no"
        assert test_settings.websocket_token_url == "https://example.com/token"
        assert test_settings.websocket_access_token == "token123"
        assert test_settings.websocket_refresh_token == "refresh123"
        assert test_settings.persistence_id == "unique-id-123"

    def test_update_from_env_list_values_json(self, monkeypatch):
        """Test updating list settings from JSON environment variable."""
        monkeypatch.setenv("EDA_LABELS", '["label1", "label2", "label3"]')

        test_settings = _Settings()

        assert test_settings.eda_labels == ["label1", "label2", "label3"]

    def test_update_from_env_list_values_non_json(self, monkeypatch):
        """Test updating list settings from non-JSON string."""
        monkeypatch.setenv("EDA_LABELS", "single_label")

        test_settings = _Settings()

        assert test_settings.eda_labels == ["single_label"]

    def test_update_from_env_no_env_vars(self, monkeypatch):
        """Test that defaults are used when no env vars are set."""
        # Clear any existing env vars
        for env_key in [
            "EDA_GC_AFTER",
            "EDA_EXECUTION_STRATEGY",
            "EDA_MAX_FEEDBACK_TIMEOUT",
            "EDA_PRINT_EVENTS",
        ]:
            monkeypatch.delenv(env_key, raising=False)

        test_settings = _Settings()

        # Should use defaults
        assert test_settings.gc_after == 1000
        assert test_settings.default_execution_strategy == "sequential"
        assert test_settings.max_feedback_timeout == 5
        assert test_settings.print_events is False

    def test_update_from_env_invalid_int(self, monkeypatch, caplog):
        """Test handling of invalid int value in env var."""
        monkeypatch.setenv("EDA_GC_AFTER", "not_a_number")

        test_settings = _Settings()

        # Should keep default value and log warning
        assert test_settings.gc_after == 1000
        assert "Failed to convert env var EDA_GC_AFTER" in caplog.text

    def test_update_from_env_invalid_json_list(self, monkeypatch, caplog):
        """Test handling of invalid JSON in list env var."""
        monkeypatch.setenv("EDA_LABELS", '["unclosed array')

        test_settings = _Settings()

        # Should fall back to treating it as a single-item list
        assert test_settings.eda_labels == ['["unclosed array']

    def test_update_from_env_called_multiple_times(self, monkeypatch):
        """Test that update_from_env can be called multiple times."""
        monkeypatch.setenv("EDA_GC_AFTER", "1500")

        test_settings = _Settings()
        assert test_settings.gc_after == 1500

        # Update env var and call update_from_env again
        monkeypatch.setenv("EDA_GC_AFTER", "2500")
        test_settings.update_from_env()

        assert test_settings.gc_after == 2500

    def test_update_from_env_partial_update(self, monkeypatch):
        """Test that only env vars that are set get updated."""
        # Set only some env vars
        monkeypatch.setenv("EDA_GC_AFTER", "3000")
        monkeypatch.setenv("EDA_PRINT_EVENTS", "true")

        test_settings = _Settings()

        # Updated values
        assert test_settings.gc_after == 3000
        assert test_settings.print_events is True

        # Default values for others
        assert test_settings.default_execution_strategy == "sequential"
        assert test_settings.max_feedback_timeout == 5

    def test_env_map_completeness(self):
        """Test that ENV_MAP is properly defined."""
        assert hasattr(_Settings, "ENV_MAP")
        assert isinstance(_Settings.ENV_MAP, dict)

        # Check that all expected keys are present
        expected_keys = {
            "gc_after",
            "default_execution_strategy",
            "max_feedback_timeout",
            "print_events",
            "websocket_url",
            "websocket_ssl_verify",
            "websocket_token_url",
            "websocket_access_token",
            "websocket_refresh_token",
            "skip_audit_events",
            "persistence_enabled",
            "persistence_id",
            "max_concurrent_actions",
            "max_actions_timeout",
            "max_back_pressure_timeout",
            "max_reporting_queue_size",
            "max_batch_job_polling_size",
            "eda_labels",
        }

        assert set(_Settings.ENV_MAP.keys()) == expected_keys

        # Check that each value is a tuple of (env_var_name, type)
        for _key, value in _Settings.ENV_MAP.items():
            assert isinstance(value, tuple)
            assert len(value) == 2
            assert isinstance(value[0], str)
            assert isinstance(value[1], type)


class TestGlobalSettings:
    """Tests for the global settings instance."""

    def test_global_settings_instance(self):
        """Test that global settings instance exists."""
        assert settings is not None
        assert isinstance(settings, _Settings)

    def test_default_eda_label_constant(self):
        """Test DEFAULT_EDA_LABEL constant value."""
        assert DEFAULT_EDA_LABEL == "Activated by Event-Driven Ansible"

    def test_default_max_concurrent_actions_constant(self):
        """Test DEFAULT_MAX_CONCURRENT_ACTIONS constant value."""
        assert DEFAULT_MAX_CONCURRENT_ACTIONS == 25


class TestMaxConcurrentActionsValidation:
    """Tests for max_concurrent_actions special validation."""

    def test_max_concurrent_actions_accepts_zero(self):
        """Test that max_concurrent_actions accepts 0 as sentinel value."""
        with patch.dict("os.environ", {"EDA_MAX_CONCURRENT_ACTIONS": "0"}):
            test_settings = _Settings()
            # 0 should be accepted (sentinel for "use default")
            assert test_settings.max_concurrent_actions == 0

    def test_max_concurrent_actions_accepts_positive(self):
        """Test that max_concurrent_actions accepts positive values."""
        with patch.dict("os.environ", {"EDA_MAX_CONCURRENT_ACTIONS": "50"}):
            test_settings = _Settings()
            assert test_settings.max_concurrent_actions == 50

    def test_max_concurrent_actions_rejects_negative(self):
        """Test that negative max_concurrent_actions is rejected."""
        with patch.dict("os.environ", {"EDA_MAX_CONCURRENT_ACTIONS": "-5"}):
            test_settings = _Settings()
            # Negative should be rejected, falls back to default 0
            assert test_settings.max_concurrent_actions == 0

    def test_max_concurrent_actions_not_in_positive_int_settings(self):
        """Test that max_concurrent_actions is not in POSITIVE_INT_SETTINGS."""
        # max_concurrent_actions should NOT be in POSITIVE_INT_SETTINGS
        # because 0 is a valid sentinel value
        assert "max_concurrent_actions" not in _Settings.POSITIVE_INT_SETTINGS

    def test_positive_int_settings_still_reject_zero(self):
        """Test that other POSITIVE_INT_SETTINGS still reject 0."""
        # Test that other settings in POSITIVE_INT_SETTINGS still reject 0
        with patch.dict("os.environ", {"EDA_MAX_ACTIONS_TIMEOUT": "0"}):
            test_settings = _Settings()
            # Should reject 0 and use default
            assert test_settings.max_actions_timeout == 3600  # default

        with patch.dict("os.environ", {"EDA_MAX_BACK_PRESSURE_TIMEOUT": "0"}):
            test_settings = _Settings()
            # Should reject 0 and use default
            assert test_settings.max_back_pressure_timeout == 3600  # default

    def test_max_concurrent_actions_default_is_zero(self):
        """Test that default max_concurrent_actions is 0 (sentinel)."""
        test_settings = _Settings()
        assert test_settings.max_concurrent_actions == 0
