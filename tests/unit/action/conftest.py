import asyncio

import pytest

from ansible_rulebook.action.control import Control
from ansible_rulebook.action.metadata import Metadata


@pytest.fixture
def base_metadata():
    return Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )


# TODO : Seems like asyncio.Queue() in a fixture is causing test failure
@pytest.fixture
def base_control():
    return Control(
        queue=asyncio.Queue(),
        inventory="abc",
        hosts=["all"],
        variables={"a": 1},
        project_data_file="",
    )
