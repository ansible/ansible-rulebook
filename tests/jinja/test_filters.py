import pytest
from jinja2 import Environment
from jinja2.nativetypes import NativeEnvironment

from ansible_rulebook.jinja import (
    basename,
    bool_filter,
    dirname,
    normpath,
    regex_replace,
    register_filters,
)


# 1. Test the function directly
def test_regex_replace_logic():
    result = regex_replace("version-1.2.3", r"\d", "x")
    assert result == "version-x.x.x"


# 2. Test the None case (Standard practice)
def test_regex_replace_none():
    assert regex_replace(None, r".*", "foo") == ""


# 3. Test integration with Jinja
def test_jinja_integration():
    env = Environment()
    register_filters(env)

    template = env.from_string(
        "{{ 'hello 123' | regex_replace('[0-9]', '') | trim }}"
    )
    assert template.render() == "hello"


def test_mandatory_count_success():
    # Should work fine
    assert regex_replace("aaa", "a", "b", mandatory_count=3) == "bbb"


def test_mandatory_count_failure():
    # Should raise ValueError because there are only 2 'a's
    with pytest.raises(ValueError, match="expected at least 3"):
        regex_replace("aa", "a", "b", mandatory_count=3)


def test_regex_ignore_case():
    text = "Apple apple APPLE"
    pattern = "apple"
    replacement = "fruit"

    # Test 1: Case-sensitive (Default)
    # Should only replace the lowercase 'apple'
    assert regex_replace(text, pattern, replacement) == "Apple fruit APPLE"

    # Test 2: Case-insensitive
    # Should replace all three versions
    assert (
        regex_replace(text, pattern, replacement, ignore_case=True)
        == "fruit fruit fruit"
    )


def test_regex_multiline():
    # A string with internal newlines
    multiline_text = "start of line\nstart of line"
    pattern = "^start"
    replacement = "end"

    # Test 1: Standard mode (Default)
    # '^' only matches the very beginning of the whole string
    assert (
        regex_replace(multiline_text, pattern, replacement)
        == "end of line\nstart of line"
    )

    # Test 2: Multiline mode
    # '^' matches the beginning of EVERY line
    assert (
        regex_replace(multiline_text, pattern, replacement, multiline=True)
        == "end of line\nend of line"
    )


def test_jinja_kwargs():
    env = Environment()
    register_filters(env)

    # Testing ignore_case inside a template
    template_str = (
        "{{ 'BANANA' | regex_replace('banana', 'apple', ignore_case=True) }}"
    )
    assert env.from_string(template_str).render() == "apple"

    # Testing count + ignore_case combined
    template_str_2 = (
        "{{ 'A a A' | regex_replace('a', 'b', count=2, ignore_case=True) }}"
    )
    assert env.from_string(template_str_2).render() == "b b A"


@pytest.mark.parametrize(
    "value, pattern, repl, kwargs, expected",
    [
        # Basic replacement
        ("hello 123", r"\d+", "world", {}, "hello world"),
        # ignore_case testing
        (
            "Apple apple APPLE",
            "apple",
            "fruit",
            {"ignore_case": True},
            "fruit fruit fruit",
        ),
        (
            "Apple apple APPLE",
            "apple",
            "fruit",
            {"ignore_case": False},
            "Apple fruit APPLE",
        ),
        # multiline testing
        (
            "line1\nline2",
            "^line",
            "start",
            {"multiline": True},
            "start1\nstart2",
        ),
        (
            "line1\nline2",
            "^line",
            "start",
            {"multiline": False},
            "start1\nline2",
        ),
        # count testing
        ("aaaaa", "a", "b", {"count": 2}, "bbaaa"),
        # mandatory_count success
        (
            "target target",
            "target",
            "found",
            {"mandatory_count": 2},
            "found found",
        ),
        # Edge cases
        (None, ".*", "anything", {}, ""),
        (12345, "123", "999", {}, "99945"),
    ],
)
def test_regex_replace_scenarios(value, pattern, repl, kwargs, expected):
    assert regex_replace(value, pattern, repl, **kwargs) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("/etc/certs/cert.pem", "cert.pem"),
        ("cert.pem", "cert.pem"),
    ],
)
def test_basename(value, expected):
    assert basename(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("/etc/certs/cert.pem", "/etc/certs"),
        ("cert.pem", ""),
    ],
)
def test_dirname(value, expected):
    assert dirname(value) == expected


@pytest.mark.parametrize(
    "value, expected",
    [
        ("/etc/certs///cert.pem", "/etc/certs/cert.pem"),
        ("/etc//certs///cert.pem/", "/etc/certs/cert.pem"),
        ("cert.pem//", "cert.pem"),
    ],
)
def test_normpath(value, expected):
    assert normpath(value) == expected


# Tests for bool_filter
@pytest.mark.parametrize(
    "value, expected",
    [
        # String values - truthy
        ("true", True),
        ("True", True),
        ("TRUE", True),
        ("yes", True),
        ("Yes", True),
        ("YES", True),
        ("1", True),
        ("on", True),
        ("On", True),
        ("ON", True),
        # String values - falsy
        ("false", False),
        ("False", False),
        ("FALSE", False),
        ("no", False),
        ("No", False),
        ("NO", False),
        ("0", False),
        ("off", False),
        ("Off", False),
        ("OFF", False),
        ("", False),
        # String values with whitespace
        ("  true  ", True),
        ("  false  ", False),
        ("  yes  ", True),
        ("  no  ", False),
        # Boolean values
        (True, True),
        (False, False),
        # None
        (None, False),
        # Other types
        (1, True),
        (0, False),
        ([], False),
        ([1, 2], True),
        ({}, False),
        ({"a": 1}, True),
    ],
)
def test_bool_filter(value, expected):
    assert bool_filter(value) == expected


def test_bool_filter_invalid_string():
    # Test that invalid string values raise ValueError
    with pytest.raises(ValueError, match="Cannot convert 'maybe' to boolean"):
        bool_filter("maybe")

    with pytest.raises(
        ValueError, match="Cannot convert 'invalid' to boolean"
    ):
        bool_filter("invalid")


def test_bool_filter_jinja_integration():
    env = Environment()
    register_filters(env)

    # Test truthy string
    template = env.from_string("{{ 'yes' | bool }}")
    assert template.render() == "True"

    # Test falsy string
    template = env.from_string("{{ 'no' | bool }}")
    assert template.render() == "False"

    # Test with variable
    template = env.from_string(
        "{% if enabled | bool %}enabled{% else %}disabled{% endif %}"
    )
    assert template.render(enabled="true") == "enabled"
    assert template.render(enabled="false") == "disabled"
    assert template.render(enabled="1") == "enabled"
    assert template.render(enabled="0") == "disabled"


def test_bool_filter_native_environment():
    """Test bool filter with NativeEnvironment to get actual boolean values."""
    env = NativeEnvironment()
    register_filters(env)

    # Test truthy string - should return actual boolean True
    template = env.from_string("{{ 'yes' | bool }}")
    result = template.render()
    assert result is True
    assert isinstance(result, bool)

    # Test falsy string - should return actual boolean False
    template = env.from_string("{{ 'no' | bool }}")
    result = template.render()
    assert result is False
    assert isinstance(result, bool)

    # Test various truthy strings
    for truthy_value in [
        "true",
        "True",
        "TRUE",
        "yes",
        "Yes",
        "1",
        "on",
        "ON",
    ]:
        template = env.from_string("{{ value | bool }}")
        result = template.render(value=truthy_value)
        assert (
            result is True
        ), f"Expected True for '{truthy_value}', got {result}"
        assert isinstance(result, bool)

    # Test various falsy strings
    for falsy_value in [
        "false",
        "False",
        "FALSE",
        "no",
        "No",
        "0",
        "off",
        "OFF",
        "",
    ]:
        template = env.from_string("{{ value | bool }}")
        result = template.render(value=falsy_value)
        assert (
            result is False
        ), f"Expected False for '{falsy_value}', got {result}"
        assert isinstance(result, bool)

    # Test with conditional logic
    template = env.from_string(
        "{% if enabled | bool %}enabled{% else %}disabled{% endif %}"
    )
    assert template.render(enabled="true") == "enabled"
    assert template.render(enabled="false") == "disabled"
    assert template.render(enabled="1") == "enabled"
    assert template.render(enabled="0") == "disabled"

    # Test that boolean values can be used in expressions
    template = env.from_string("{{ ('yes' | bool) and ('true' | bool) }}")
    result = template.render()
    assert result is True
    assert isinstance(result, bool)

    template = env.from_string("{{ ('yes' | bool) and ('false' | bool) }}")
    result = template.render()
    assert result is False
    assert isinstance(result, bool)
