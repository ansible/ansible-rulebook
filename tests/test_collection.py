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

import textwrap

import pytest

import ansible_rulebook.collection as collection_module
from ansible_rulebook.collection import (
    find_collection,
    find_playbook,
    find_source,
    has_playbook,
    has_rulebook,
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


def test_event_source_deprecation_and_redirect(monkeypatch, tmp_path):
    collection_module._displayed_plugin_warnings.clear()
    collection_module._load_collection_runtime.cache_clear()

    collection_name = "testns.testcol"
    collection_root = tmp_path / "testns" / "testcol"
    plugin_dir = (
        collection_root
        / "extensions"
        / "eda"
        / "plugins"
        / "event_source"
    )
    plugin_dir.mkdir(parents=True)
    new_plugin = plugin_dir / "new_plugin.py"
    new_plugin.write_text("# test plugin\n", encoding="utf-8")

    runtime_dir = collection_root / "meta"
    runtime_dir.mkdir(parents=True)
    runtime_dir.joinpath("runtime.yml").write_text(
        textwrap.dedent(
            """
            plugin_routing:
              event_source:
                old_plugin:
                  redirect: testns.testcol.new_plugin
                  deprecation:
                    removal_version: 2.0.0
                    warning_text: Use testns.testcol.new_plugin instead.
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    def fake_find_collection(name):
        if name == collection_name:
            return str(collection_root)
        return None

    monkeypatch.setattr(
        collection_module, "find_collection", fake_find_collection
    )

    display = collection_module.terminal.Display.instance()
    captured = []

    def fake_banner(*args, **kwargs):
        captured.append((args, kwargs))

    monkeypatch.setattr(display, "banner", fake_banner)

    assert collection_module.has_source(collection_name, "old_plugin")
    resolved_path = collection_module.find_source(
        collection_name, "old_plugin"
    )
    assert resolved_path == str(new_plugin)

    assert captured, "Expected a deprecation banner to be emitted"
    banner_args, banner_kwargs = captured[0]
    assert banner_args[0] == "deprecation"
    assert "Use testns.testcol.new_plugin instead." in banner_args[1]
    assert "Redirects to 'testns.testcol.new_plugin'." in banner_args[1]


def test_event_filter_deprecation_without_redirect(monkeypatch, tmp_path):
    collection_module._displayed_plugin_warnings.clear()
    collection_module._load_collection_runtime.cache_clear()

    collection_name = "testns.filters"
    collection_root = tmp_path / "testns" / "filters"
    plugin_dir = (
        collection_root
        / "extensions"
        / "eda"
        / "plugins"
        / "event_filter"
    )
    plugin_dir.mkdir(parents=True)
    filter_plugin = plugin_dir / "keeping_filter.py"
    filter_plugin.write_text("# filter plugin\n", encoding="utf-8")

    runtime_dir = collection_root / "meta"
    runtime_dir.mkdir(parents=True)
    runtime_dir.joinpath("runtime.yml").write_text(
        textwrap.dedent(
            """
            plugin_routing:
              event_filter:
                keeping_filter:
                  deprecation:
                    removal_date: 2025-01-01
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    def fake_find_collection(name):
        if name == collection_name:
            return str(collection_root)
        return None

    monkeypatch.setattr(
        collection_module, "find_collection", fake_find_collection
    )

    display = collection_module.terminal.Display.instance()
    captured = []

    def fake_banner(*args, **kwargs):
        captured.append((args, kwargs))

    monkeypatch.setattr(display, "banner", fake_banner)

    assert collection_module.has_source_filter(
        collection_name, "keeping_filter"
    )
    resolved_path = collection_module.find_source_filter(
        collection_name, "keeping_filter"
    )
    assert resolved_path == str(filter_plugin)

    assert captured, "Expected a deprecation banner to be emitted"
    banner_args, _ = captured[0]
    assert banner_args[0] == "deprecation"
    assert "removal date 2025-01-01" in banner_args[1]
