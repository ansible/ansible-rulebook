#  Copyright 2025 Red Hat, Inc.
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

from ansible_rulebook.event_filter.dashes_to_underscores import (
    main as filter_main,
)

# Test data: (input_event, filter_args, expected_output)
EVENT_DATA = [
    # Test 1: Basic dash replacement
    (
        {"key-name": "value1", "other-key": "value2"},
        {},
        {"key_name": "value1", "other_key": "value2"},
    ),
    # Test 2: Mixed keys - some with dashes, some without
    (
        {"key-with-dash": "value1", "normal_key": "value2"},
        {},
        {"key_with_dash": "value1", "normal_key": "value2"},
    ),
    # Test 3: Multiple dashes in one key
    (
        {"this-is-a-long-key": "value"},
        {},
        {"this_is_a_long_key": "value"},
    ),
    # Test 4: No dashes (should remain unchanged)
    (
        {"key1": "value1", "key2": "value2"},
        {},
        {"key1": "value1", "key2": "value2"},
    ),
    # Test 5: Nested dictionary with dashes
    (
        {"top-level": {"nested-key": "value"}},
        {},
        {"top_level": {"nested_key": "value"}},
    ),
    # Test 6: Key collision with overwrite=True (default)
    (
        {"key-name": "from_dash", "key_name": "original"},
        {"overwrite": True},
        {"key_name": "from_dash"},
    ),
    # Test 7: Key collision with overwrite=False
    (
        {"key-name": "from_dash", "key_name": "original"},
        {"overwrite": False},
        {"key_name": "original"},
    ),
    # Test 8: Complex nested structure
    (
        {
            "outer-key": {
                "inner-key": {
                    "deep-key": "value",
                }
            }
        },
        {},
        {
            "outer_key": {
                "inner_key": {
                    "deep_key": "value",
                }
            }
        },
    ),
    # Test 9: Multiple levels of nesting
    (
        {
            "level-1": {
                "level-2": {
                    "level-3": "value",
                    "no-dash-here": "value2",
                }
            },
            "top": "level",
        },
        {},
        {
            "level_1": {
                "level_2": {
                    "level_3": "value",
                    "no_dash_here": "value2",
                }
            },
            "top": "level",
        },
    ),
    # Test 10: Mixed nested structure with lists and dicts
    (
        {
            "top-level": {
                "items": [
                    {"item-id": 1, "item-name": "first"},
                    {"item-id": 2, "item-name": "second"},
                ]
            }
        },
        {},
        {
            "top_level": {
                "items": [
                    {"item_id": 1, "item_name": "first"},
                    {"item_id": 2, "item_name": "second"},
                ]
            }
        },
    ),
]


@pytest.mark.parametrize("data, args, expected", EVENT_DATA)
def test_dashes_to_underscores(data, args, expected):
    """Test dashes_to_underscores filter with various configurations."""
    result = filter_main(data, **args)
    assert result == expected
