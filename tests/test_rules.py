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

import pytest
import yaml
from drools.ruleset import assert_fact as set_fact, post
from jinja2.exceptions import UndefinedError

from ansible_rulebook.exception import (
    RulenameDuplicateException,
    RulenameEmptyException,
    RulesetNameDuplicateException,
    RulesetNameEmptyException,
)
from ansible_rulebook.rule_generator import generate_rulesets
from ansible_rulebook.rules_parser import parse_rule_sets

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
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
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
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
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
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
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
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
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
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
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


def test_parse_event_sources_with_legacy_mapping():
    """Test that legacy source mappings are applied correctly."""
    from unittest.mock import patch

    from ansible_rulebook.rules_parser import parse_event_sources

    sources = [{"ansible.eda.range": {"limit": 5}}]

    with patch("ansible_rulebook.rules_parser.is_deprecated") as mock_is_dep:
        # is_deprecated should not be called when legacy mapping is used
        mock_is_dep.return_value = (False, None)

        result = parse_event_sources(sources)

        # Should use legacy mapping instead of calling is_deprecated
        assert len(result) == 1
        assert result[0].source_name == "eda.builtin.range"
        assert result[0].source_args["limit"] == 5


def test_parse_event_sources_with_is_deprecated():
    """Test that is_deprecated is used when no legacy mapping exists."""
    from unittest.mock import patch

    from ansible_rulebook.rules_parser import parse_event_sources

    sources = [{"custom.collection.custom_source": {"arg": "value"}}]

    with patch("ansible_rulebook.rules_parser.is_deprecated") as mock_is_dep:
        mock_is_dep.return_value = (True, "custom.builtin.new_source")

        result = parse_event_sources(sources)

        # Should call is_deprecated and use the redirect
        assert len(result) == 1
        assert result[0].source_name == "custom.builtin.new_source"
        assert result[0].source_args["arg"] == "value"
        mock_is_dep.assert_called_once_with(
            "custom.collection.custom_source", "event_source"
        )


def test_parse_event_sources_no_deprecation():
    """Test event sources that are not deprecated."""
    from unittest.mock import patch

    from ansible_rulebook.rules_parser import parse_event_sources

    sources = [{"eda.builtin.range": {"limit": 10}}]

    with patch("ansible_rulebook.rules_parser.is_deprecated") as mock_is_dep:
        mock_is_dep.return_value = (False, None)

        result = parse_event_sources(sources)

        assert len(result) == 1
        assert result[0].source_name == "eda.builtin.range"
        mock_is_dep.assert_called_once()


def test_parse_source_filter_with_legacy_mapping():
    """Test that legacy filter mappings are applied correctly."""
    from unittest.mock import patch

    from ansible_rulebook.rules_parser import parse_source_filter

    source_filter = {"ansible.eda.json_filter": {"exclude_keys": ["key1"]}}

    with patch("ansible_rulebook.rules_parser.is_deprecated") as mock_is_dep:
        # is_deprecated should not be called when legacy mapping is used
        mock_is_dep.return_value = (False, None)

        result = parse_source_filter(source_filter)

        # Should use legacy mapping
        assert result.filter_name == "eda.builtin.json_filter"
        assert result.filter_args["exclude_keys"] == ["key1"]


def test_parse_source_filter_with_is_deprecated():
    """Test that is_deprecated is used when no legacy mapping exists."""
    from unittest.mock import patch

    from ansible_rulebook.rules_parser import parse_source_filter

    source_filter = {"custom.collection.custom_filter": {"option": "value"}}

    with patch("ansible_rulebook.rules_parser.is_deprecated") as mock_is_dep:
        mock_is_dep.return_value = (True, "custom.builtin.new_filter")

        result = parse_source_filter(source_filter)

        # Should call is_deprecated and use the redirect
        assert result.filter_name == "custom.builtin.new_filter"
        assert result.filter_args["option"] == "value"
        mock_is_dep.assert_called_once_with(
            "custom.collection.custom_filter", "event_filter"
        )


def test_parse_source_filter_no_deprecation():
    """Test source filters that are not deprecated."""
    from unittest.mock import patch

    from ansible_rulebook.rules_parser import parse_source_filter

    source_filter = {"eda.builtin.json_filter": {"include_keys": ["key1"]}}

    with patch("ansible_rulebook.rules_parser.is_deprecated") as mock_is_dep:
        mock_is_dep.return_value = (False, None)

        result = parse_source_filter(source_filter)

        assert result.filter_name == "eda.builtin.json_filter"
        mock_is_dep.assert_called_once()


def test_all_legacy_source_mappings():
    """Test all entries in LEGACY_SOURCE_MAPPING."""
    from ansible_rulebook.rules_parser import (
        LEGACY_SOURCE_MAPPING,
        parse_event_sources,
    )

    for old_name, new_name in LEGACY_SOURCE_MAPPING.items():
        sources = [{old_name: {}}]
        result = parse_event_sources(sources)

        assert len(result) == 1
        assert (
            result[0].source_name == new_name
        ), f"Failed for {old_name} -> {new_name}"


def test_all_legacy_filter_mappings():
    """Test all entries in LEGACY_FILTER_MAPPING."""
    from ansible_rulebook.rules_parser import (
        LEGACY_FILTER_MAPPING,
        parse_source_filter,
    )

    for old_name, new_name in LEGACY_FILTER_MAPPING.items():
        source_filter = {old_name: {}}
        result = parse_source_filter(source_filter)

        assert (
            result.filter_name == new_name
        ), f"Failed for {old_name} -> {new_name}"
