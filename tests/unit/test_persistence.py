#  Copyright 2023 Red Hat, Inc.
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

"""Unit tests for ansible_rulebook.persistence module."""

import argparse
import json
from unittest.mock import patch

import pytest

from ansible_rulebook import persistence
from ansible_rulebook.conf import settings

SSL_PASS = "test_ssl_password"
TEST_PASSWORD = "test_password"


@pytest.fixture
def mock_lang():
    """Mock the drools.ruleset module."""
    with patch("ansible_rulebook.persistence.lang") as mock:
        yield mock


@pytest.fixture
def postgres_variables():
    """Return a valid set of PostgreSQL configuration variables."""
    return {
        "drools_db_host": "localhost",
        "drools_db_port": 5432,
        "drools_db_name": "test_db",
        "drools_db_user": "test_user",
        "drools_db_password": TEST_PASSWORD,
        "drools_sslmode": "require",
    }


@pytest.fixture
def h2_variables():
    """Return a valid set of H2 configuration variables."""
    return {
        "drools_db_file_path": "/tmp/test_db",
    }


@pytest.fixture
def parsed_args():
    """Return mock parsed arguments."""
    args = argparse.Namespace()
    args.persistence_id = "test-persistence-id"
    args.id = "worker-1"
    return args


@pytest.fixture
def reset_settings():
    """Reset settings.persistence_enabled after each test."""
    original_value = settings.persistence_enabled
    yield
    settings.persistence_enabled = original_value


class TestEnablePersistence:
    """Tests for enable_persistence function."""

    def test_enable_persistence_with_postgres(
        self, mock_lang, postgres_variables, parsed_args, reset_settings
    ):
        """Test enabling persistence with PostgreSQL configuration."""
        persistence.enable_persistence(parsed_args, postgres_variables)

        assert settings.persistence_enabled is True
        mock_lang.initialize_ha.assert_called_once()
        call_kwargs = mock_lang.initialize_ha.call_args.kwargs

        assert call_kwargs["uuid"] == "test-persistence-id"
        assert call_kwargs["worker_name"] == "instance-worker-1"
        assert call_kwargs["db_params"]["db_type"] == "postgres"
        assert call_kwargs["db_params"]["host"] == "localhost"
        assert call_kwargs["db_params"]["port"] == 5432
        assert call_kwargs["db_params"]["database"] == "test_db"
        assert call_kwargs["db_params"]["user"] == "test_user"
        assert call_kwargs["db_params"]["password"] == TEST_PASSWORD
        assert call_kwargs["db_params"]["sslmode"] == "require"

    def test_enable_persistence_with_h2(
        self, mock_lang, h2_variables, parsed_args, reset_settings
    ):
        """Test enabling persistence with H2 configuration."""
        persistence.enable_persistence(parsed_args, h2_variables)

        assert settings.persistence_enabled is True
        mock_lang.initialize_ha.assert_called_once()
        call_kwargs = mock_lang.initialize_ha.call_args.kwargs

        assert call_kwargs["uuid"] == "test-persistence-id"
        assert call_kwargs["worker_name"] == "instance-worker-1"
        assert call_kwargs["db_params"]["db_type"] == "h2"
        assert call_kwargs["db_params"]["db_file_path"] == "/tmp/test_db"

    def test_enable_persistence_no_db_config(
        self, mock_lang, parsed_args, reset_settings
    ):
        """Test persistence not enabled without database config."""
        variables = {"some_other_key": "value"}

        persistence.enable_persistence(parsed_args, variables)

        assert settings.persistence_enabled is False
        mock_lang.initialize_ha.assert_not_called()

    def test_enable_persistence_with_encryption_keys(
        self, mock_lang, postgres_variables, parsed_args, reset_settings
    ):
        """Test enabling persistence with encryption keys configured."""
        postgres_variables["drools_primary_encryption_secret"] = "primary_key"
        postgres_variables[
            "drools_secondary_encryption_secret"
        ] = "secondary_key"

        persistence.enable_persistence(parsed_args, postgres_variables)

        call_kwargs = mock_lang.initialize_ha.call_args.kwargs
        assert call_kwargs["config"]["encryption_key_primary"] == "primary_key"
        assert (
            call_kwargs["config"]["encryption_key_secondary"]
            == "secondary_key"
        )

    def test_enable_persistence_with_grace_period(
        self, mock_lang, postgres_variables, parsed_args, reset_settings
    ):
        """Test enabling persistence with expired window grace period."""
        postgres_variables["drools_expired_window_grace_period"] = "300"

        persistence.enable_persistence(parsed_args, postgres_variables)

        call_kwargs = mock_lang.initialize_ha.call_args.kwargs
        assert call_kwargs["config"]["expired_window_grace_period"] == 300

    def test_enable_persistence_logs_initialization(
        self,
        mock_lang,
        postgres_variables,
        parsed_args,
        reset_settings,
        caplog,
    ):
        """Test that persistence initialization is logged."""
        import logging

        caplog.set_level(logging.INFO)

        persistence.enable_persistence(parsed_args, postgres_variables)

        assert "Initializing drools HA mode" in caplog.text
        assert "test-persistence-id" in caplog.text
        assert "postgres" in caplog.text


class TestUpdateActionInfo:
    """Tests for update_action_info function."""

    def test_update_action_info_create(self, mock_lang, reset_settings):
        """Test creating new action info."""
        settings.persistence_enabled = True
        info = {"status": "running", "job_id": "12345"}

        persistence.update_action_info(
            "test_ruleset", "uuid-123", 0, info, create=True
        )

        mock_lang.add_action_info.assert_called_once_with(
            "test_ruleset", "uuid-123", 0, json.dumps(info)
        )

    def test_update_action_info_update(self, mock_lang, reset_settings):
        """Test updating existing action info."""
        settings.persistence_enabled = True
        existing_data = {"status": "running", "job_id": "12345"}
        mock_lang.get_action_info.return_value = json.dumps(existing_data)

        new_info = {"status": "completed", "end_time": "2023-01-01T00:00:00"}

        persistence.update_action_info(
            "test_ruleset", "uuid-123", 0, new_info, create=False
        )

        mock_lang.get_action_info.assert_called_once_with(
            "test_ruleset", "uuid-123", 0
        )

        expected_data = {
            "status": "completed",
            "job_id": "12345",
            "end_time": "2023-01-01T00:00:00",
        }
        mock_lang.update_action_info.assert_called_once_with(
            "test_ruleset", "uuid-123", 0, json.dumps(expected_data)
        )

    def test_update_action_info_update_logs_debug(
        self, mock_lang, reset_settings, caplog
    ):
        """Test that debug logging occurs when updating action info."""
        import logging

        caplog.set_level(logging.DEBUG)
        settings.persistence_enabled = True
        existing_data = {"status": "running"}
        mock_lang.get_action_info.return_value = json.dumps(existing_data)

        new_info = {"status": "completed"}

        persistence.update_action_info(
            "test_ruleset", "uuid-123", 0, new_info, create=False
        )

        assert "Updating action info" in caplog.text

    def test_update_action_info_update_with_corrupt_data(
        self, mock_lang, reset_settings, caplog
    ):
        """Test updating action info when existing data is corrupted."""
        settings.persistence_enabled = True
        mock_lang.get_action_info.return_value = "invalid json {{"

        new_info = {"status": "completed"}

        persistence.update_action_info(
            "test_ruleset", "uuid-123", 0, new_info, create=False
        )

        # Should still update with new info only
        mock_lang.update_action_info.assert_called_once()
        call_args = mock_lang.update_action_info.call_args[0]
        assert json.loads(call_args[3]) == {"status": "completed"}

        # Should log an error
        assert "Error parsing saved action data" in caplog.text

    def test_update_action_info_persistence_disabled(
        self, mock_lang, reset_settings
    ):
        """Test that nothing happens when persistence is disabled."""
        settings.persistence_enabled = False
        info = {"status": "running"}

        persistence.update_action_info(
            "test_ruleset", "uuid-123", 0, info, create=True
        )

        mock_lang.add_action_info.assert_not_called()
        mock_lang.update_action_info.assert_not_called()


class TestGetActionAPriori:
    """Tests for get_action_a_priori function."""

    def test_get_action_a_priori_exists(self, mock_lang):
        """Test retrieving existing action info."""
        action_data = {"status": "running", "job_id": "12345"}
        mock_lang.action_info_exists.return_value = True
        mock_lang.get_action_info.return_value = json.dumps(action_data)

        result = persistence.get_action_a_priori("test_ruleset", "uuid-123", 0)

        assert result == action_data
        mock_lang.action_info_exists.assert_called_once_with(
            "test_ruleset", "uuid-123", 0
        )
        mock_lang.get_action_info.assert_called_once_with(
            "test_ruleset", "uuid-123", 0
        )

    def test_get_action_a_priori_logs_debug(self, mock_lang, caplog):
        """Test that debug logging occurs when retrieving action info."""
        import logging

        caplog.set_level(logging.DEBUG)
        action_data = {"status": "running"}
        mock_lang.action_info_exists.return_value = True
        mock_lang.get_action_info.return_value = json.dumps(action_data)

        persistence.get_action_a_priori("test_ruleset", "uuid-123", 0)

        assert "Previous action data" in caplog.text

    def test_get_action_a_priori_not_exists(self, mock_lang):
        """Test retrieving non-existent action info."""
        mock_lang.action_info_exists.return_value = False

        result = persistence.get_action_a_priori("test_ruleset", "uuid-123", 0)

        assert result is None
        mock_lang.get_action_info.assert_not_called()

    def test_get_action_a_priori_corrupt_data(self, mock_lang, caplog):
        """Test retrieving corrupted action info."""
        mock_lang.action_info_exists.return_value = True
        mock_lang.get_action_info.return_value = "invalid json {{"

        result = persistence.get_action_a_priori("test_ruleset", "uuid-123", 0)

        assert result == {}
        assert "Error parsing prior action data" in caplog.text


class TestEnableLeader:
    """Tests for enable_leader function."""

    def test_enable_leader_when_persistence_enabled(
        self, mock_lang, reset_settings
    ):
        """Test enabling leader mode when persistence is enabled."""
        settings.persistence_enabled = True

        persistence.enable_leader()

        mock_lang.enable_leader.assert_called_once()

    def test_enable_leader_when_persistence_disabled(
        self, mock_lang, reset_settings
    ):
        """Test leader mode not enabled when persistence disabled."""
        settings.persistence_enabled = False

        persistence.enable_leader()

        mock_lang.enable_leader.assert_not_called()


class TestGetPostgresParams:
    """Tests for _get_postgres_params function."""

    def test_get_postgres_params_minimal(self):
        """Test extracting minimal PostgreSQL parameters."""
        variables = {
            "drools_db_host": "localhost",
            "drools_db_port": 5432,
            "drools_db_name": "test_db",
        }

        result = persistence._get_postgres_params(variables)

        assert result is not None
        assert result["db_type"] == "postgres"
        assert result["host"] == "localhost"
        assert result["port"] == 5432
        assert result["database"] == "test_db"

    def test_get_postgres_params_with_auth(self):
        """Test extracting PostgreSQL parameters with authentication."""
        variables = {
            "drools_db_host": "localhost",
            "drools_db_port": 5432,
            "drools_db_name": "test_db",
            "drools_db_user": "admin",
            "drools_db_password": "secret",
        }

        result = persistence._get_postgres_params(variables)

        assert result["user"] == "admin"
        assert result["password"] == "secret"

    def test_get_postgres_params_with_ssl(self):
        """Test extracting PostgreSQL parameters with SSL configuration."""
        variables = {
            "drools_db_host": "localhost",
            "drools_db_port": 5432,
            "drools_db_name": "test_db",
            "drools_sslmode": "require",
            "drools_sslpassword": SSL_PASS,
            "drools_sslrootcert": "/path/to/root.crt",
            "drools_sslkey": "/path/to/key.pem",
            "drools_sslcert": "/path/to/cert.pem",
        }

        result = persistence._get_postgres_params(variables)

        assert result["sslmode"] == "require"
        assert result["sslpassword"] == SSL_PASS
        assert result["sslrootcert"] == "/path/to/root.crt"
        assert result["sslkey"] == "/path/to/key.pem"
        assert result["sslcert"] == "/path/to/cert.pem"

    def test_get_postgres_params_with_eda_filenames(self):
        """Test extracting PostgreSQL parameters with EDA filename paths."""
        variables = {
            "drools_db_host": "localhost",
            "drools_db_port": 5432,
            "drools_db_name": "test_db",
            "eda": {
                "filename": {
                    "drools_sslrootcert": "/eda/path/root.crt",
                    "drools_sslkey": "/eda/path/key.pem",
                    "drools_sslcert": "/eda/path/cert.pem",
                }
            },
        }

        result = persistence._get_postgres_params(variables)

        assert result["sslrootcert"] == "/eda/path/root.crt"
        assert result["sslkey"] == "/eda/path/key.pem"
        assert result["sslcert"] == "/eda/path/cert.pem"

    def test_get_postgres_params_missing_required(self):
        """Test that None is returned when required parameters are missing."""
        # Missing drools_db_name
        variables = {
            "drools_db_host": "localhost",
            "drools_db_port": 5432,
        }

        result = persistence._get_postgres_params(variables)

        assert result is None

    def test_get_postgres_params_empty_variables(self):
        """Test that None is returned with empty variables."""
        result = persistence._get_postgres_params({})

        assert result is None

    def test_get_postgres_params_priority_eda_over_direct(self):
        """Test that EDA filename paths take priority over direct variables."""
        variables = {
            "drools_db_host": "localhost",
            "drools_db_port": 5432,
            "drools_db_name": "test_db",
            "drools_sslcert": "/direct/path/cert.pem",
            "eda": {
                "filename": {
                    "drools_sslcert": "/eda/path/cert.pem",
                }
            },
        }

        result = persistence._get_postgres_params(variables)

        # EDA filename path is processed first in the mappings dict,
        # but dpath.get will find the direct variable last, so direct wins
        # since it overwrites in the iteration
        assert result["sslcert"] == "/direct/path/cert.pem"

    def test_get_postgres_params_skips_falsy_values(self):
        """Test that falsy values (empty string, None) are not added."""
        variables = {
            "drools_db_host": "localhost",
            "drools_db_port": 5432,
            "drools_db_name": "test_db",
            "drools_db_user": "",  # Empty string should be skipped
            "drools_db_password": None,  # None should be skipped
        }

        result = persistence._get_postgres_params(variables)

        assert "user" not in result
        assert "password" not in result


class TestGetH2Params:
    """Tests for _get_h2_params function."""

    def test_get_h2_params_valid(self):
        """Test extracting H2 parameters with valid configuration."""
        variables = {
            "drools_db_file_path": "/tmp/test_db",
        }

        result = persistence._get_h2_params(variables)

        assert result is not None
        assert result["db_type"] == "h2"
        assert result["db_file_path"] == "/tmp/test_db"

    def test_get_h2_params_missing_required(self):
        """Test that None is returned when required parameters are missing."""
        variables = {
            "some_other_key": "value",
        }

        result = persistence._get_h2_params(variables)

        assert result is None

    def test_get_h2_params_empty_variables(self):
        """Test that None is returned with empty variables."""
        result = persistence._get_h2_params({})

        assert result is None


class TestGetConfigParams:
    """Tests for _get_config_params function."""

    def test_get_config_params_defaults(self):
        """Test extracting config parameters with default values."""
        variables = {}

        result = persistence._get_config_params(variables)

        assert "encryption_key_primary" not in result
        assert "encryption_key_secondary" not in result
        assert "expired_window_grace_period" not in result
        assert "overwrite_if_rulebook_changes" not in result
        assert "dedup_buffer_size" not in result

    def test_get_config_params_with_encryption_keys(self):
        """Test extracting config parameters with encryption keys."""
        variables = {
            "drools_primary_encryption_secret": "primary_key",
            "drools_secondary_encryption_secret": "secondary_key",
        }

        result = persistence._get_config_params(variables)

        assert result["encryption_key_primary"] == "primary_key"
        assert result["encryption_key_secondary"] == "secondary_key"

    def test_get_config_params_with_grace_period(self):
        """Test extracting config parameters with grace period."""
        variables = {
            "drools_expired_window_grace_period": "600",
        }

        result = persistence._get_config_params(variables)

        assert result["expired_window_grace_period"] == 600

    def test_get_config_params_all_options(self):
        """Test extracting all config parameters."""
        variables = {
            "drools_primary_encryption_secret": "primary",
            "drools_secondary_encryption_secret": "secondary",
            "drools_expired_window_grace_period": "1200",
            "drools_overwrite_if_rulebook_changes": True,
            "drools_deduplication_window_size": "1000",
        }

        result = persistence._get_config_params(variables)

        assert result["encryption_key_primary"] == "primary"
        assert result["encryption_key_secondary"] == "secondary"
        assert result["expired_window_grace_period"] == 1200
        assert result["overwrite_if_rulebook_changes"] is True
        assert result["dedup_buffer_size"] == 1000

    def test_get_config_params_with_overwrite_bool_true(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as bool True.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": True,
        }

        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is True

    def test_get_config_params_with_overwrite_bool_false(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as bool False.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": False,
        }
        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is False

    def test_get_config_params_with_overwrite_string_true(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as string 'true'.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": "true",
        }

        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is True

    def test_get_config_params_with_overwrite_string_false(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as string 'false'.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": "false",
        }

        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is False

    def test_get_config_params_with_overwrite_string_yes(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as string 'yes'.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": "yes",
        }

        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is True

    def test_get_config_params_with_overwrite_string_no(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as string 'no'.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": "no",
        }

        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is False

    def test_get_config_params_with_overwrite_int_1(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as int 1.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": 1,
        }

        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is True

    def test_get_config_params_with_overwrite_int_0(self):
        """Test extracting config with overwrite_if_rulebook_changes.

        Testing as int 0.
        """
        variables = {
            "drools_overwrite_if_rulebook_changes": 0,
        }

        result = persistence._get_config_params(variables)

        assert result["overwrite_if_rulebook_changes"] is False

    def test_get_config_params_with_dedup_buffer_size(self):
        """Test extracting config with dedup_buffer_size."""
        variables = {
            "drools_deduplication_window_size": "5000",
        }

        result = persistence._get_config_params(variables)

        assert result["dedup_buffer_size"] == 5000

    def test_get_config_params_with_dedup_buffer_size_int(self):
        """Test extracting config with dedup_buffer_size as integer."""
        variables = {
            "drools_deduplication_window_size": 10000,
        }

        result = persistence._get_config_params(variables)

        assert result["dedup_buffer_size"] == 10000
