import pytest

from ansible_rulebook.event_filter.json_filter import main as filter_main

# Test data: (input_event, filter_args, expected_output)
EVENT_DATA = [
    # Test 1: Basic exclude - remove single key
    (
        {"key1": "value1", "key2": "value2", "key3": "value3"},
        {"exclude_keys": ["key1"]},
        {"key2": "value2", "key3": "value3"},
    ),
    # Test 2: Include alone doesn't remove keys (only exclude does)
    # include_keys protects keys from being excluded, doesn't act as whitelist
    (
        {"key1": "value1", "key2": "value2", "key3": "value3"},
        {"include_keys": ["key1"]},
        {"key1": "value1", "key2": "value2", "key3": "value3"},
    ),
    # Test 3: Include overrides exclude
    (
        {"key1": "value1", "key2": "value2", "key3": "value3"},
        {"exclude_keys": ["key1", "key2"], "include_keys": ["key1"]},
        {"key1": "value1", "key3": "value3"},
    ),
    # Test 4: Exclude with wildcard pattern
    (
        {"key1": "value1", "key2": "value2", "key3": "value3"},
        {"exclude_keys": ["key*"]},
        {},
    ),
    # Test 5: Include with wildcard pattern (doesn't remove non-matching)
    (
        {"prefix_a": 1, "prefix_b": 2, "other": 3},
        {"include_keys": ["prefix_*"]},
        {"prefix_a": 1, "prefix_b": 2, "other": 3},
    ),
    # Test 6: Wildcard exclude with specific include
    (
        {"key1": "value1", "key2": "value2", "key3": "value3"},
        {"exclude_keys": ["key*"], "include_keys": ["key1"]},
        {"key1": "value1"},
    ),
    # Test 7: Nested dictionaries - exclude nested key
    (
        {
            "key1": {"nested1": "val1", "nested2": "val2"},
            "key2": "value2",
        },
        {"exclude_keys": ["nested1"]},
        {"key1": {"nested2": "val2"}, "key2": "value2"},
    ),
    # Test 8: Nested dictionaries - exclude top-level key
    (
        {
            "key1": {"nested1": "val1", "nested2": "val2"},
            "key2": "value2",
        },
        {"exclude_keys": ["key1"]},
        {"key2": "value2"},
    ),
    # Test 9: Multiple wildcard patterns
    (
        {
            "remove_a": 1,
            "remove_b": 2,
            "keep_x": 3,
            "keep_y": 4,
        },
        {"exclude_keys": ["remove_*"]},
        {"keep_x": 3, "keep_y": 4},
    ),
    # Test 10: Empty exclude_keys list
    (
        {"key1": "value1", "key2": "value2"},
        {"exclude_keys": []},
        {"key1": "value1", "key2": "value2"},
    ),
    # Test 11: Empty include_keys list (keeps everything)
    (
        {"key1": "value1", "key2": "value2"},
        {"include_keys": []},
        {"key1": "value1", "key2": "value2"},
    ),
    # Test 12: Complex nested structure
    (
        {
            "level1": {
                "level2": {
                    "target": "keep",
                    "remove": "discard",
                },
                "other": "data",
            },
            "top": "level",
        },
        {"exclude_keys": ["remove"]},
        {
            "level1": {
                "level2": {"target": "keep"},
                "other": "data",
            },
            "top": "level",
        },
    ),
    # Test 13: Include with nested patterns (doesn't remove non-matching)
    (
        {
            "app_config": {"value": 1},
            "app_settings": {"value": 2},
            "other": {"value": 3},
        },
        {"include_keys": ["app_*"]},
        {
            "app_config": {"value": 1},
            "app_settings": {"value": 2},
            "other": {"value": 3},
        },
    ),
    # Test 14: No matching exclude patterns
    (
        {"key1": "value1", "key2": "value2"},
        {"exclude_keys": ["nonexistent"]},
        {"key1": "value1", "key2": "value2"},
    ),
    # Test 15: No matching include patterns (keeps all)
    (
        {"key1": "value1", "key2": "value2"},
        {"include_keys": ["nonexistent"]},
        {"key1": "value1", "key2": "value2"},
    ),
    # Test with None arguments
    (
        {"key1": "value1", "key2": "value2"},
        {},
        {"key1": "value1", "key2": "value2"},
    ),
]


@pytest.mark.parametrize("data, args, expected", EVENT_DATA)
def test_json_filter(data, args, expected):
    """Test json_filter with various configurations."""
    result = filter_main(data, **args)
    assert result == expected


def test_json_filter_nested_lists_with_dicts():
    """Test filtering with lists containing dictionaries.

    Note: json_filter does NOT process dicts inside lists.
    Lists are added to the queue but their items are not traversed.
    """
    data = {
        "items": [
            {"keep": "yes", "remove": "no"},
            {"keep": "yes", "remove": "no"},
        ],
        "other": "data",
    }
    result = filter_main(data, exclude_keys=["remove"])

    # The filter does NOT remove keys from dicts inside lists
    # So 'remove' keys remain in the list items
    expected = {
        "items": [
            {"keep": "yes", "remove": "no"},
            {"keep": "yes", "remove": "no"},
        ],
        "other": "data",
    }

    assert result == expected
    # Verify the 'remove' key was NOT excluded from list items
    assert result["items"][0]["remove"] == "no"
    assert result["items"][1]["remove"] == "no"


def test_json_filter_question_mark_wildcard():
    """Test ? wildcard (matches single character)."""
    data = {
        "key1": "value1",
        "key2": "value2",
        "key10": "value10",
    }
    result = filter_main(data, exclude_keys=["key?"])
    assert result == {"key10": "value10"}


def test_json_filter_complex_include_exclude():
    """Test complex scenario with both include and exclude patterns."""
    data = {
        "app_config_dev": 1,
        "app_config_prod": 2,
        "app_settings": 3,
        "db_config": 4,
        "cache_config": 5,
    }
    result = filter_main(
        data,
        exclude_keys=["*_config*"],
        include_keys=["app_config_prod"],
    )
    # app_config_prod is included despite matching exclude pattern
    # app_settings doesn't match exclude pattern
    assert result == {"app_config_prod": 2, "app_settings": 3}


def test_json_filter_deeply_nested():
    """Test filtering deeply nested structures."""
    data = {
        "level1": {
            "level2": {
                "level3": {
                    "level4": {
                        "target": "found",
                        "exclude_me": "gone",
                    }
                }
            }
        }
    }
    result = filter_main(data, exclude_keys=["exclude_me"])
    expected = {
        "level1": {"level2": {"level3": {"level4": {"target": "found"}}}}
    }
    assert result == expected
