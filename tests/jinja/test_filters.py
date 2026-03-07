import pytest
from jinja2 import Environment

from ansible_rulebook.jinja import (
    basename,
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
