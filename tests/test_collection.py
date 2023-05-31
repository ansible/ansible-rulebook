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

import pytest

from ansible_rulebook.collection import (
    find_collection,
    find_playbook,
    find_source,
    has_playbook,
    has_rulebook,
    load_rulebook,
    split_collection_name,
)


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
    assert not load_rulebook(
        *split_collection_name("missing.eda.hello_events")
    )


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
