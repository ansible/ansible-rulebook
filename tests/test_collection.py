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

import os
from unittest.mock import mock_open, patch

import pytest

from ansible_rulebook.collection import (
    _load_eda_runtime,
    find_collection,
    find_playbook,
    find_source,
    get_deprecation_info,
    get_redirect_info,
    get_tombstone_info,
    has_playbook,
    has_rulebook,
    load_plugin_routing,
    load_rulebook,
    split_collection_name,
)
from ansible_rulebook.exception import RulebookNotFoundException


def test_find_collection():
    location = find_collection("community.general")
    assert location is not None


def test_find_collection_missing():
    assert find_collection("community.missing") is None


def test_find_collection_eda():
    location = find_collection("ansible.eda")
    assert location is not None


def test_find_source():
    location = find_source(*split_collection_name("ansible.eda.range"))
    assert location is not None


def test_load_rulebook():
    rules = load_rulebook(*split_collection_name("ansible.eda.hello_events"))
    assert rules is not None


def test_load_rulebook_missing():
    with pytest.raises(RulebookNotFoundException):
        load_rulebook(*split_collection_name("missing.eda.hello_events"))


def test_has_rulebook():
    assert has_rulebook(*split_collection_name("ansible.eda.hello_events"))


def test_find_playbook():
    assert (
        find_playbook(*split_collection_name("ansible.eda.hello")) is not None
    )


def test_find_playbook_missing():
    with pytest.raises(FileNotFoundError):
        find_playbook(*split_collection_name("ansible.eda.missing"))


def test_has_playbook():
    assert has_playbook(*split_collection_name("ansible.eda.hello"))


def test_has_playbook_missing():
    assert not has_playbook(*split_collection_name("ansible.eda.missing"))


def test_has_playbook_missing_collection():
    assert not has_playbook(*split_collection_name("missing.eda.missing"))


def test_load_eda_runtime_success():
    """Test loading a valid eda_runtime.yml file from mock collection."""
    _load_eda_runtime.cache_clear()

    # Mock find_collection to return our test data directory
    # When _load_eda_runtime calls find_collection("test.mock"),
    # it will get back the path to our mock_collection test fixture
    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        # Call with any collection name - it will use our mocked path
        result = _load_eda_runtime("test.mock")

        assert isinstance(result, dict)
        assert "plugin_routing" in result


def test_load_eda_runtime_missing_collection():
    """Test loading runtime for a non-existent collection."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = None
        result = _load_eda_runtime("missing.collection")
        assert result == {}


def test_load_eda_runtime_missing_file():
    """Test loading runtime when eda_runtime.yml doesn't exist."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = "/tmp/fake_collection"
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = False
            result = _load_eda_runtime("test.collection")
            assert result == {}


def test_load_eda_runtime_invalid_yaml():
    """Test loading runtime with invalid YAML content raises ValueError."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = "/tmp/fake_collection"
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch(
                "builtins.open", mock_open(read_data="invalid: yaml: [")
            ):
                with pytest.raises(
                    ValueError, match="error parsing eda collection metadata"
                ):
                    _load_eda_runtime("test.collection")


def test_get_deprecation_info_with_redirect():
    """Test deprecated plugin with redirect."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        routing = load_plugin_routing("ansible.eda.deprecated_custom_source")
        deprecation = get_deprecation_info(
            routing, "event_source", "deprecated_custom_source"
        )
        redirect = get_redirect_info(
            routing, "event_source", "deprecated_custom_source"
        )

        assert deprecation is not None
        assert deprecation["removal_version"] == "3.1.0"
        assert redirect == "eda.builtin.new_custom_source"


def test_get_deprecation_info_without_redirect():
    """Test deprecated plugin without redirect."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        routing = load_plugin_routing("ansible.eda.old_custom_filter")
        deprecation = get_deprecation_info(
            routing, "event_filter", "old_custom_filter"
        )
        redirect = get_redirect_info(
            routing, "event_filter", "old_custom_filter"
        )

        assert deprecation is not None
        assert deprecation["removal_version"] == "3.0.0"
        assert redirect is None


def test_get_redirect_info_without_deprecation():
    """Test redirect only (no deprecation)."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        routing = load_plugin_routing("ansible.eda.silent_redirect_source")
        deprecation = get_deprecation_info(
            routing, "event_source", "silent_redirect_source"
        )
        redirect = get_redirect_info(
            routing, "event_source", "silent_redirect_source"
        )

        assert deprecation is None
        assert redirect == "eda.builtin.better_source"


def test_get_tombstone_info():
    """Test tombstoned plugin."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        routing = load_plugin_routing("ansible.eda.removed_filter")
        tombstone = get_tombstone_info(
            routing, "event_filter", "removed_filter"
        )

        assert tombstone is not None
        assert tombstone["removal_version"] == "2.5.0"
        assert "warning_text" in tombstone


def test_load_eda_runtime_non_dict_data():
    """Test that non-dict YAML data raises ValueError."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = "/tmp/fake_collection"
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            # YAML that parses to a list instead of dict
            with patch(
                "builtins.open", mock_open(read_data="- item1\n- item2")
            ):
                with pytest.raises(
                    ValueError, match="Expected dict, got list"
                ):
                    _load_eda_runtime("test.collection")


def test_load_plugin_routing_non_dict_plugin_routing():
    """Test that non-dict plugin_routing raises ValueError."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = "/tmp/fake_collection"
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            # YAML with plugin_routing as a list instead of dict
            yaml_content = "plugin_routing:\n  - invalid"
            with patch("builtins.open", mock_open(read_data=yaml_content)):
                with pytest.raises(
                    ValueError, match="expected plugin_routing as dict"
                ):
                    load_plugin_routing("test.collection.plugin")


def test_get_redirect_info_non_dict_type_section():
    """Test that non-dict type section raises ValueError."""
    plugin_routing = {"event_source": ["not", "a", "dict"]}

    with pytest.raises(ValueError, match="expected dict, got list"):
        get_redirect_info(plugin_routing, "event_source", "test_plugin")


def test_get_redirect_info_non_dict_plugin_data():
    """Test that non-dict plugin data raises ValueError."""
    plugin_routing = {"event_source": {"test_plugin": "not_a_dict"}}

    with pytest.raises(ValueError, match="expected dict, got str"):
        get_redirect_info(plugin_routing, "event_source", "test_plugin")


def test_get_deprecation_info_non_dict_type_section():
    """Test that non-dict type section raises ValueError."""
    plugin_routing = {"event_filter": ["not", "a", "dict"]}

    with pytest.raises(ValueError, match="expected dict, got list"):
        get_deprecation_info(plugin_routing, "event_filter", "test_plugin")


def test_get_deprecation_info_non_dict_plugin_data():
    """Test that non-dict plugin data raises ValueError."""
    plugin_routing = {"event_filter": {"test_plugin": "not_a_dict"}}

    with pytest.raises(ValueError, match="expected dict, got str"):
        get_deprecation_info(plugin_routing, "event_filter", "test_plugin")


def test_get_tombstone_info_non_dict_type_section():
    """Test that non-dict type section raises ValueError."""
    plugin_routing = {"event_source": ["not", "a", "dict"]}

    with pytest.raises(ValueError, match="expected dict, got list"):
        get_tombstone_info(plugin_routing, "event_source", "test_plugin")


def test_get_tombstone_info_non_dict_plugin_data():
    """Test that non-dict plugin data raises ValueError."""
    plugin_routing = {"event_source": {"test_plugin": "not_a_dict"}}

    with pytest.raises(ValueError, match="expected dict, got str"):
        get_tombstone_info(plugin_routing, "event_source", "test_plugin")
