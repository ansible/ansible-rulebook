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
from unittest.mock import patch

import pytest

from ansible_rulebook.collection import (
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

# Path to test data directory and mock collection
TEST_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MOCK_COLLECTION_PATH = os.path.join(TEST_DATA_DIR, "mock_collection")


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


# Tests for is_deprecated function
@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_event_filter(mock_find_collection):
    """Test that deprecated event filters are correctly identified."""
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated("ansible.eda.json_filter", "event_filter")
    assert is_dep is True
    assert redirect == "eda.builtin.json_filter"


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_event_filter_normalize_keys(mock_find_collection):
    """Test another deprecated event filter."""
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated(
        "ansible.eda.normalize_keys", "event_filter"
    )
    assert is_dep is True
    assert redirect == "eda.builtin.normalize_keys"


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_event_filter_dashes_to_underscores(
    mock_find_collection,
):
    """Test dashes_to_underscores event filter deprecation."""
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated(
        "ansible.eda.dashes_to_underscores", "event_filter"
    )
    assert is_dep is True
    assert redirect == "eda.builtin.dashes_to_underscores"


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_event_source(mock_find_collection):
    """Test that deprecated event sources are correctly identified."""
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated("ansible.eda.pg_listener", "event_source")
    assert is_dep is True
    assert redirect == "eda.builtin.pg_listener"


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_event_source_generic(mock_find_collection):
    """Test generic event source deprecation."""
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated("ansible.eda.generic", "event_source")
    assert is_dep is True
    assert redirect == "eda.builtin.generic"


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_event_source_range(mock_find_collection):
    """Test range event source deprecation."""
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated("ansible.eda.range", "event_source")
    assert is_dep is True
    assert redirect == "eda.builtin.range"


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_not_deprecated_plugin(mock_find_collection):
    """Test that non-deprecated plugins return False."""
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated(
        "ansible.eda.alertmanager", "event_source"
    )
    assert is_dep is False
    assert redirect is None


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_missing_collection(mock_find_collection):
    """Test behavior when collection doesn't exist."""
    mock_find_collection.return_value = None
    is_dep, redirect = is_deprecated(
        "missing.collection.plugin", "event_source"
    )
    assert is_dep is False
    assert redirect is None


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_invalid_name_format(mock_find_collection):
    """Test behavior when plugin name doesn't have proper format."""
    # Should not even call find_collection since name is invalid
    is_dep, redirect = is_deprecated("invalid_name", "event_source")
    assert is_dep is False
    assert redirect is None
    mock_find_collection.assert_not_called()


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_wrong_object_type(mock_find_collection):
    """Test checking wrong object type doesn't find deprecation."""
    # This tests that if we look for event_source but the deprecation
    # is only defined for event_filter, we won't find it
    mock_find_collection.return_value = MOCK_COLLECTION_PATH
    is_dep, redirect = is_deprecated("ansible.eda.json_filter", "event_source")
    assert is_dep is False
    assert redirect is None


@patch("ansible_rulebook.collection.find_collection")
def test_is_deprecated_collection_without_runtime_yml(mock_find_collection):
    """Test behavior when collection exists but has no runtime.yml."""
    # Point to a directory without runtime.yml
    mock_find_collection.return_value = TEST_DATA_DIR
    is_dep, redirect = is_deprecated("some.collection.plugin", "event_source")
    assert is_dep is False
    assert redirect is None
