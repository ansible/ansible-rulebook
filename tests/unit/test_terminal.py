import copy
import logging
import os

import pytest

from ansible_rulebook import terminal


@pytest.fixture
def display():
    # Use a copy of the Display singleton so tests that
    # change the display level don't mess up other tests
    # that expect the defaults.
    return copy.copy(terminal.Display())


def test_display_get_banners(display):
    banner = "banner"
    incomplete = os.linesep.join(
        [
            f"** 2023-12-12 12:34:56.123456 [{banner}] ******",
            "line",
            "line",
        ]
    )
    complete = os.linesep.join(
        [
            incomplete,
            "***********************************************",
        ]
    )

    # Incomplete banner output.
    with pytest.raises(terminal.DisplayBannerIncompleteError):
        display.get_banners(banner, incomplete)

    # Complete banner output.
    result = display.get_banners(banner, complete)
    assert len(result) == 1, "get complete banner failed"
    assert result[0] == complete, "incorrect banner returned"

    # Multiple banners.
    multiple = os.linesep.join(
        [
            "line",
            complete,
            "line",
            complete,
            "line",
        ]
    )
    result = display.get_banners(banner, multiple)
    assert len(result) == 2, "get multiple banners failed"
    assert result[0] == complete, "incorrect first banner returned"
    assert result[1] == complete, "incorrect second banner returned"

    # Specific banner from multiple.
    specific = os.linesep.join(
        [
            "** 2023-12-12 12:34:56.123456 [specific] ******",
            "line",
            "line",
            "***********************************************",
        ]
    )
    result = display.get_banners(
        "specific",
        os.linesep.join(
            [
                "line",
                complete,
                specific,
                complete,
                "line",
            ]
        ),
    )
    assert len(result) == 1, "get specific banner failed"
    assert result[0] == specific, "incorrect specific banner returned"


def test_display_banner(display, capsys):
    lines = ["line-one", "line-two", "line-three"]

    # One-shot banner.
    display.banner("banner", lines)
    captured = capsys.readouterr()
    result = display.get_banners("banner", captured.out)
    assert result, "one-shot banner not found"

    # Manually constructed banner.
    display.banner("banner")
    display.output(lines)
    display.banner()
    captured = capsys.readouterr()
    result = display.get_banners("banner", captured.out)
    assert result, "manual banner not found"

    # Output at higher level.
    display.banner("banner", lines, level=logging.WARNING)
    captured = capsys.readouterr()
    result = display.get_banners("banner", captured.out)
    assert result, "banner not found"

    # Output at changed level.
    display.level = logging.WARNING
    display.banner("banner", lines, level=logging.WARNING)
    captured = capsys.readouterr()
    result = display.get_banners("banner", captured.out)
    assert result, "banner not found"

    # No output for lower level.
    display.banner("banner", lines)
    captured = capsys.readouterr()
    result = display.get_banners("banner", captured.out)
    assert not result, "banner found"
