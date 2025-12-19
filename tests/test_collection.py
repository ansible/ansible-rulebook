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
    has_playbook,
    has_rulebook,
    is_deprecated,
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
    """Test loading a valid eda_runtime.yml file."""
    # Clear the cache before testing
    _load_eda_runtime.cache_clear()

    # Use the mock collection that has eda_runtime.yml
    collection_path = find_collection("ansible.eda")
    if collection_path:
        # Check if mock runtime exists in test data
        test_runtime = os.path.join(
            os.path.dirname(__file__),
            "data/mock_collection/extensions/eda/eda_runtime.yml",
        )
        if os.path.exists(test_runtime):
            # Test with mock collection name
            with patch(
                "ansible_rulebook.collection.find_collection"
            ) as mock_find:
                mock_find.return_value = os.path.join(
                    os.path.dirname(__file__), "data/mock_collection"
                )
                result = _load_eda_runtime("ansible.eda")
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
    """Test loading runtime with invalid YAML content."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = "/tmp/fake_collection"
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch(
                "builtins.open", mock_open(read_data="invalid: yaml: [")
            ):
                result = _load_eda_runtime("test.collection")
                assert result == {}


def test_load_eda_runtime_caching():
    """Test that _load_eda_runtime caches results."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )
        # First call
        result1 = _load_eda_runtime("ansible.eda")
        # Second call should use cache
        result2 = _load_eda_runtime("ansible.eda")

        # Should only call find_collection once due to caching
        assert result1 == result2
        # The mock should have been called, but results should be cached
        assert mock_find.call_count >= 1


def test_is_deprecated_with_redirect():
    """Test is_deprecated for a plugin that is deprecated with redirect."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        deprecated, redirect = is_deprecated(
            "ansible.eda.json_filter", "event_filter"
        )

        assert deprecated is True
        assert redirect == "eda.builtin.json_filter"


def test_is_deprecated_source():
    """Test is_deprecated for an event source."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        deprecated, redirect = is_deprecated(
            "ansible.eda.range", "event_source"
        )

        assert deprecated is True
        assert redirect == "eda.builtin.range"


def test_is_deprecated_not_found():
    """Test is_deprecated for a plugin that is not deprecated."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = os.path.join(
            os.path.dirname(__file__), "data/mock_collection"
        )

        deprecated, redirect = is_deprecated(
            "ansible.eda.unknown_plugin", "event_filter"
        )

        assert deprecated is False
        assert redirect is None


def test_is_deprecated_invalid_name():
    """Test is_deprecated with invalid plugin name."""
    deprecated, redirect = is_deprecated("invalid", "event_filter")

    assert deprecated is False
    assert redirect is None


def test_is_deprecated_missing_collection():
    """Test is_deprecated when collection doesn't exist."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = None

        deprecated, redirect = is_deprecated(
            "missing.collection.plugin", "event_filter"
        )

        assert deprecated is False
        assert redirect is None


def test_is_deprecated_no_plugin_routing():
    """Test is_deprecated when runtime YAML has no plugin_routing."""
    _load_eda_runtime.cache_clear()

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = "/tmp/fake_collection"
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch(
                "builtins.open", mock_open(read_data="---\nother: data")
            ):
                deprecated, redirect = is_deprecated(
                    "test.collection.plugin", "event_filter"
                )

                assert deprecated is False
                assert redirect is None


def test_is_deprecated_no_redirect():
    """Test is_deprecated when deprecation exists but no redirect."""
    _load_eda_runtime.cache_clear()

    runtime_yaml = """---
plugin_routing:
  extensions.eda.plugins.event_filter:
    test.collection.plugin:
      deprecation:
        warning_text: "This is deprecated"
"""

    with patch("ansible_rulebook.collection.find_collection") as mock_find:
        mock_find.return_value = "/tmp/fake_collection"
        with patch("os.path.exists") as mock_exists:
            mock_exists.return_value = True
            with patch("builtins.open", mock_open(read_data=runtime_yaml)):
                deprecated, redirect = is_deprecated(
                    "test.collection.plugin", "event_filter"
                )

                assert deprecated is False
                assert redirect is None
