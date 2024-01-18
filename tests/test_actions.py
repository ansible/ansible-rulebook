import asyncio
import os
from unittest.mock import MagicMock

import pytest

from ansible_rulebook.rule_set_runner import RuleSetRunner

HERE = os.path.dirname(os.path.abspath(__file__))


def test_find_noaction():
    runner = RuleSetRunner(
        None, MagicMock(), None, None, None, action_directories=[]
    )
    assert runner.find_action("no_action") is None


def test_find_action():

    runner = RuleSetRunner(
        None,
        MagicMock(),
        None,
        None,
        None,
        action_directories=[os.path.join(HERE, "actions")],
    )
    assert runner.find_action("uri") is not None


@pytest.mark.asyncio
async def test_call_action():
    queue = asyncio.Queue()
    runner = RuleSetRunner(
        queue,
        MagicMock(),
        None,
        None,
        None,
        action_directories=[os.path.join(HERE, "actions")],
    )
    assert (
        await runner._call_action(
            MagicMock(),
            "uri",
            MagicMock(),
            MagicMock(),
            None,
            None,
            MagicMock(),
        )
        is None
    )
