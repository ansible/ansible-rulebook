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

import asyncio
import os
from queue import Queue
from unittest.mock import patch

import pytest
import yaml
from drools.ruleset import assert_fact as set_fact, post
from jinja2.exceptions import UndefinedError

from ansible_rulebook.collection import (
    LEGACY_FILTER_MAPPING,
    LEGACY_SOURCE_MAPPING,
    apply_plugin_routing,
)
from ansible_rulebook.exception import (
    RulenameDuplicateException,
    RulenameEmptyException,
    RulesetNameDuplicateException,
    RulesetNameEmptyException,
    SourceFilterNotFoundException,
    SourcePluginNotFoundException,
)
from ansible_rulebook.rule_generator import generate_rulesets
from ansible_rulebook.rules_parser import (
    parse_event_sources,
    parse_rule_sets,
    parse_source_filter,
)

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.asyncio
async def test_generate_rules():
    os.chdir(HERE)
    with open("rules/rules.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue(), Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())
    set_fact("Demo rules", {"payload": {"text": "hello"}})

    assert (
        durable_rulesets[0].plan.queue.get_nowait().actions[0].action
        == "slack"
    )
    assert durable_rulesets[0].plan.queue.get_nowait().rule == "assert fact"
    assert durable_rulesets[0].plan.queue.get_nowait().ruleset == "Demo rules"


@pytest.mark.asyncio
async def test_generate_rules_multiple_conditions_any():
    os.chdir(HERE)
    with open("rules/rules_with_multiple_conditions.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue(), Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())

    post("Demo rules multiple conditions any", {"i": 0})
    assert (
        durable_rulesets[0].plan.queue.get_nowait().actions[0].action
        == "debug"
    )
    post("Demo rules multiple conditions any", {"i": 1})
    assert (
        durable_rulesets[0].plan.queue.get_nowait().actions[0].action
        == "debug"
    )


@pytest.mark.asyncio
async def test_generate_rules_multiple_conditions_all():
    os.chdir(HERE)
    with open("rules/rules_with_multiple_conditions2.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue(), Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())

    post("Demo rules multiple conditions all", {"i": 0})
    assert durable_rulesets[0].plan.queue.qsize() == 0
    post("Demo rules multiple conditions all", {"i": 1})
    assert durable_rulesets[0].plan.queue.qsize() == 1
    assert (
        durable_rulesets[0].plan.queue.get_nowait().actions[0].action
        == "debug"
    )


@pytest.mark.asyncio
async def test_generate_rules_multiple_conditions_all_3():
    os.chdir(HERE)
    with open("rules/rules_with_multiple_conditions3.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue(), Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())

    post("Demo rules multiple conditions reference assignment", {"i": 0})
    assert durable_rulesets[0].plan.queue.qsize() == 0
    post("Demo rules multiple conditions reference assignment", {"i": 1})
    assert durable_rulesets[0].plan.queue.qsize() == 0
    post("Demo rules multiple conditions reference assignment", {"i": 2})
    assert durable_rulesets[0].plan.queue.qsize() == 1
    assert (
        durable_rulesets[0].plan.queue.get_nowait().actions[0].action
        == "debug"
    )


@pytest.mark.asyncio
async def test_duplicate_ruleset_names():
    os.chdir(HERE)
    with open("rules/test_duplicate_ruleset_names.yml") as f:
        data = yaml.safe_load(f.read())

    with pytest.raises(RulesetNameDuplicateException) as exc_info:
        parse_rule_sets(data)

    assert (
        str(exc_info.value)
        == "Ruleset with name: ruleset1 defined multiple times"
    )


@pytest.mark.asyncio
async def test_blank_ruleset_names():
    os.chdir(HERE)
    with open("rules/test_blank_ruleset_name.yml") as f:
        data = yaml.safe_load(f.read())

    with pytest.raises(RulesetNameEmptyException) as exc_info:
        parse_rule_sets(data)

    assert str(exc_info.value) == "Ruleset name cannot be an empty string"


@pytest.mark.asyncio
async def test_missing_ruleset_names():
    os.chdir(HERE)
    with open("rules/test_missing_ruleset_name.yml") as f:
        data = yaml.safe_load(f.read())

    with pytest.raises(RulesetNameEmptyException) as exc_info:
        parse_rule_sets(data)

    assert str(exc_info.value) == "Ruleset name not provided"


@pytest.mark.asyncio
async def test_rule_name_substitution_duplicates():
    os.chdir(HERE)
    variables = {"custom": {"name1": "fred", "name2": "fred"}}
    with open("rules/rule_names_with_substitution.yml") as f:
        data = yaml.safe_load(f.read())

    with pytest.raises(RulenameDuplicateException):
        parse_rule_sets(data, variables)


@pytest.mark.asyncio
async def test_rule_name_substitution_empty():
    os.chdir(HERE)
    variables = {"custom": {"name1": "", "name2": "fred"}}
    with open("rules/rule_names_with_substitution.yml") as f:
        data = yaml.safe_load(f.read())

    with pytest.raises(RulenameEmptyException):
        parse_rule_sets(data, variables)


@pytest.mark.asyncio
async def test_rule_name_substitution_missing():
    os.chdir(HERE)
    variables = {"custom": {"name2": "fred"}}
    with open("rules/rule_names_with_substitution.yml") as f:
        data = yaml.safe_load(f.read())

    with pytest.raises(UndefinedError):
        parse_rule_sets(data, variables)


@pytest.mark.asyncio
async def test_rule_name_substitution():
    os.chdir(HERE)
    variables = {"custom": {"name1": "barney", "name2": "fred"}}
    with open("rules/rule_names_with_substitution.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data, variables)
    ruleset_queues = [(ruleset, Queue(), Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)
    ruleset_name = durable_rulesets[0].ruleset.name

    durable_rulesets[0].plan.queue = asyncio.Queue()
    post(ruleset_name, {"i": 1})
    assert durable_rulesets[0].plan.queue.qsize() == 1
    event = durable_rulesets[0].plan.queue.get_nowait()
    assert event.rule == "barney"
    assert event.actions[0].action == "debug"
    post(ruleset_name, {"i": 2})
    assert durable_rulesets[0].plan.queue.qsize() == 1
    event = durable_rulesets[0].plan.queue.get_nowait()
    assert event.rule == "fred"
    assert event.actions[0].action == "debug"


@pytest.mark.parametrize(
    "plugin_name,plugin_type,args,expected_name",
    [
        ("ansible.eda.range", "source", {"limit": 5}, "eda.builtin.range"),
        (
            "ansible.eda.json_filter",
            "filter",
            {"exclude_keys": ["key1"]},
            "eda.builtin.json_filter",
        ),
    ],
)
def test_parse_with_legacy_mapping(
    plugin_name, plugin_type, args, expected_name
):
    """Test that legacy mappings are applied correctly."""
    if plugin_type == "source":
        sources = [{plugin_name: args}]
        result = parse_event_sources(sources)
        assert len(result) == 1
        assert result[0].source_name == expected_name
        assert result[0].source_args == args
    else:
        source_filter = {plugin_name: args}
        result = parse_source_filter(source_filter)
        assert result.filter_name == expected_name
        assert result.filter_args == args


@pytest.mark.parametrize(
    "plugin_name,plugin_type,args",
    [
        ("eda.builtin.range", "source", {"limit": 10}),
        ("eda.builtin.json_filter", "filter", {"include_keys": ["key1"]}),
    ],
)
def test_parse_no_deprecation(plugin_name, plugin_type, args):
    """Test plugins that are not deprecated."""
    if plugin_type == "source":
        sources = [{plugin_name: args}]
        result = parse_event_sources(sources)
        assert len(result) == 1
        assert result[0].source_name == plugin_name
    else:
        source_filter = {plugin_name: args}
        result = parse_source_filter(source_filter)
        assert result.filter_name == plugin_name


def test_all_legacy_source_mappings():
    """Test all entries in LEGACY_SOURCE_MAPPING."""
    for old_name, new_name in LEGACY_SOURCE_MAPPING.items():
        sources = [{old_name: {}}]
        result = parse_event_sources(sources)

        assert len(result) == 1
        assert (
            result[0].source_name == new_name
        ), f"Failed for {old_name} -> {new_name}"


def test_all_legacy_filter_mappings():
    """Test all entries in LEGACY_FILTER_MAPPING."""
    for old_name, new_name in LEGACY_FILTER_MAPPING.items():
        source_filter = {old_name: {}}
        result = parse_source_filter(source_filter)

        assert (
            result.filter_name == new_name
        ), f"Failed for {old_name} -> {new_name}"


@pytest.mark.parametrize(
    "plugin_name,plugin_type,exception_type",
    [
        (
            "ansible.eda.removed_source",
            "source",
            SourcePluginNotFoundException,
        ),
        (
            "ansible.eda.removed_filter",
            "filter",
            SourceFilterNotFoundException,
        ),
    ],
)
def test_tombstone_raises_exception(plugin_name, plugin_type, exception_type):
    """Test tombstoned plugins raise appropriate exceptions."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        if plugin_type == "source":
            sources = [{plugin_name: {}}]
            with pytest.raises(exception_type) as exc_info:
                parse_event_sources(sources)
        else:
            source_filter = {plugin_name: {}}
            with pytest.raises(exception_type) as exc_info:
                parse_source_filter(source_filter)

        assert "has been removed" in str(exc_info.value)


@pytest.mark.parametrize(
    "plugin_name,plugin_type,expected_result",
    [
        (
            "ansible.eda.deprecated_custom_source",
            "source",
            "eda.builtin.new_custom_source",
        ),
        (
            "ansible.eda.deprecated_custom_filter",
            "filter",
            "eda.builtin.new_custom_filter",
        ),
    ],
)
def test_deprecated_with_redirect(plugin_name, plugin_type, expected_result):
    """Test deprecated plugins with redirect."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        if plugin_type == "source":
            sources = [{plugin_name: {}}]
            result = parse_event_sources(sources)
            assert len(result) == 1
            assert result[0].source_name == expected_result
        else:
            source_filter = {plugin_name: {}}
            result = parse_source_filter(source_filter)
            assert result.filter_name == expected_result


@pytest.mark.parametrize(
    "plugin_name,plugin_type,expected_result",
    [
        (
            "ansible.eda.silent_redirect_source",
            "source",
            "eda.builtin.better_source",
        ),
        (
            "ansible.eda.silent_redirect_filter",
            "filter",
            "eda.builtin.better_filter",
        ),
    ],
)
def test_silent_redirect(plugin_name, plugin_type, expected_result):
    """Test plugins with redirect only (no deprecation)."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        if plugin_type == "source":
            sources = [{plugin_name: {}}]
            result = parse_event_sources(sources)
            assert len(result) == 1
            assert result[0].source_name == expected_result
        else:
            source_filter = {plugin_name: {}}
            result = parse_source_filter(source_filter)
            assert result.filter_name == expected_result


@pytest.mark.parametrize(
    "plugin_name,plugin_type",
    [
        ("ansible.eda.old_custom_source", "source"),
        ("ansible.eda.old_custom_filter", "filter"),
    ],
)
def test_deprecated_without_redirect(plugin_name, plugin_type):
    """Test deprecated plugins without redirect keep original name."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        if plugin_type == "source":
            sources = [{plugin_name: {}}]
            result = parse_event_sources(sources)
            assert len(result) == 1
            assert result[0].source_name == plugin_name
        else:
            source_filter = {plugin_name: {}}
            result = parse_source_filter(source_filter)
            assert result.filter_name == plugin_name


def test_apply_plugin_routing_with_legacy_mapping():
    """Test apply_plugin_routing uses legacy mapping first."""
    # Legacy mapping should be checked before runtime YAML
    result = apply_plugin_routing(
        "ansible.eda.range",
        "event_source",
        LEGACY_SOURCE_MAPPING,
        SourcePluginNotFoundException,
    )

    assert result == "eda.builtin.range"


def test_apply_plugin_routing_returns_original_if_no_routing():
    """Test apply_plugin_routing returns original name when no routing."""
    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=None,
    ):
        # Plugin with no routing info should return original name
        result = apply_plugin_routing(
            "unknown.collection.plugin",
            "event_source",
            LEGACY_SOURCE_MAPPING,
            SourcePluginNotFoundException,
        )

        assert result == "unknown.collection.plugin"


def test_apply_plugin_routing_combined_source_and_filter():
    """Test that apply_plugin_routing works for both sources and filters."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        # Test with source
        source_result = apply_plugin_routing(
            "ansible.eda.deprecated_custom_source",
            "event_source",
            LEGACY_SOURCE_MAPPING,
            SourcePluginNotFoundException,
        )
        assert source_result == "eda.builtin.new_custom_source"

        # Test with filter
        filter_result = apply_plugin_routing(
            "ansible.eda.deprecated_custom_filter",
            "event_filter",
            LEGACY_FILTER_MAPPING,
            SourceFilterNotFoundException,
        )
        assert filter_result == "eda.builtin.new_custom_filter"


def test_apply_plugin_routing_tombstone_raises_correct_exception():
    """Test tombstone raises the correct exception type."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        # Source tombstone should raise SourcePluginNotFoundException
        with pytest.raises(SourcePluginNotFoundException) as exc_info:
            apply_plugin_routing(
                "ansible.eda.removed_source",
                "event_source",
                LEGACY_SOURCE_MAPPING,
                SourcePluginNotFoundException,
            )
        assert "has been removed" in str(exc_info.value)

        # Filter tombstone should raise SourceFilterNotFoundException
        with pytest.raises(SourceFilterNotFoundException) as exc_info:
            apply_plugin_routing(
                "ansible.eda.removed_filter",
                "event_filter",
                LEGACY_FILTER_MAPPING,
                SourceFilterNotFoundException,
            )
        assert "has been removed" in str(exc_info.value)


@pytest.mark.parametrize(
    "plugin_name,obj_type,legacy_mapping",
    [
        ("ansible.eda.loop_source_a", "event_source", "LEGACY_SOURCE_MAPPING"),
        ("ansible.eda.loop_filter_a", "event_filter", "LEGACY_FILTER_MAPPING"),
    ],
)
def test_redirect_loop_detection(plugin_name, obj_type, legacy_mapping):
    """Test that redirect loops are detected and raise ValueError."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    # Get the actual legacy mapping dict based on the string name
    legacy_map = (
        LEGACY_SOURCE_MAPPING
        if legacy_mapping == "LEGACY_SOURCE_MAPPING"
        else LEGACY_FILTER_MAPPING
    )
    exception_type = (
        SourcePluginNotFoundException
        if obj_type == "event_source"
        else SourceFilterNotFoundException
    )

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        # Test redirect loop: plugin_a -> plugin_b -> plugin_a
        with pytest.raises(ValueError) as exc_info:
            apply_plugin_routing(
                plugin_name, obj_type, legacy_map, exception_type
            )
        error_msg = str(exc_info.value)
        assert "plugin redirect loop" in error_msg
        assert plugin_name in error_msg


@pytest.mark.parametrize(
    "plugin_name,obj_type,legacy_mapping,expected_result",
    [
        (
            "ansible.eda.chain_source_hop1",
            "event_source",
            "LEGACY_SOURCE_MAPPING",
            "eda.builtin.final_source",
        ),
        (
            "ansible.eda.chain_filter_hop1",
            "event_filter",
            "LEGACY_FILTER_MAPPING",
            "eda.builtin.final_filter",
        ),
    ],
)
def test_multi_hop_redirect_chain(
    plugin_name, obj_type, legacy_mapping, expected_result
):
    """Test that multi-hop redirect chains work correctly (3+ hops)."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    # Get the actual legacy mapping dict based on the string name
    legacy_map = (
        LEGACY_SOURCE_MAPPING
        if legacy_mapping == "LEGACY_SOURCE_MAPPING"
        else LEGACY_FILTER_MAPPING
    )
    exception_type = (
        SourcePluginNotFoundException
        if obj_type == "event_source"
        else SourceFilterNotFoundException
    )

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        # Test chain: hop1 -> hop2 -> hop3 -> final
        result = apply_plugin_routing(
            plugin_name, obj_type, legacy_map, exception_type
        )
        # Should follow the chain to the final target
        assert result == expected_result


@pytest.mark.parametrize(
    "plugin_name,obj_type,legacy_mapping",
    [
        (
            "ansible.eda.long_chain_source_hop1",
            "event_source",
            "LEGACY_SOURCE_MAPPING",
        ),
        (
            "ansible.eda.long_chain_hop1",
            "event_filter",
            "LEGACY_FILTER_MAPPING",
        ),
    ],
)
def test_max_redirect_chain_limit(plugin_name, obj_type, legacy_mapping):
    """Test that redirect chains exceeding max limit raise RuntimeError."""
    mock_collection_path = os.path.join(HERE, "data/mock_collection")

    # Get the actual legacy mapping dict based on the string name
    legacy_map = (
        LEGACY_SOURCE_MAPPING
        if legacy_mapping == "LEGACY_SOURCE_MAPPING"
        else LEGACY_FILTER_MAPPING
    )
    exception_type = (
        SourcePluginNotFoundException
        if obj_type == "event_source"
        else SourceFilterNotFoundException
    )

    with patch(
        "ansible_rulebook.collection.find_collection",
        return_value=mock_collection_path,
    ):
        # Test chain with 11 hops (exceeds max of 10)
        with pytest.raises(RuntimeError) as exc_info:
            apply_plugin_routing(
                plugin_name, obj_type, legacy_map, exception_type
            )
        error_msg = str(exc_info.value)
        assert "Exceeded max allowed" in error_msg
        assert "redirections" in error_msg
