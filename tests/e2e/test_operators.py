"""
Module with tests for operators
"""
import logging
import subprocess

import pytest

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook",
    [
        pytest.param("test_lt_operator.yml", id="lt"),
        pytest.param("test_le_operator.yml", id="le"),
    ],
)
def test_less_operators(rulebook):
    """
    GIVEN a rulebook with range source plugin that produces 8 events
        and a condition like "i less than 4"
        or a condition like "i less or equal 3"
        and an action to run a playbook that prints the event
    WHEN the program is executed
    THEN the playbook must be executed 4 times printing each event
        and the program must finish without errors
    """
    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
    )

    output = utils.assert_playbook_output(result)

    printed_events = [
        line for line in output if "Event matched" in line["stdout"]
    ]

    assert len(printed_events) == 4

    for event, expected in zip(printed_events, range(4)):
        assert f"{{'i': {expected}}}" in event["stdout"]


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook, expected",
    [
        pytest.param("test_eq_operator_int.yml", "{'i': 4}", id="int"),
        pytest.param("test_eq_operator_str.yml", "{'i': '4'}", id="str"),
    ],
)
def test_eq_operator(rulebook, expected):
    """
    GIVEN a rulebook with range source plugin that produces 8 events
        and a condition like "i equal 4"
        or a condition like "i equal '4'" (str)
        and an action to run a playbook that prints the event
    WHEN the program is executed
    THEN the playbook must be executed 1 time printing the event
        and the program must finish without errors
    """
    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
    )

    output = utils.assert_playbook_output(result)

    printed_event = next(
        line for line in output if "Event matched" in line["stdout"]
    )

    assert expected in printed_event["stdout"]


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook",
    [
        pytest.param("test_ge_operator.yml", id="ge_operator"),
        pytest.param("test_gt_operator.yml", id="gt_operator"),
    ],
)
def test_greater_operators(rulebook):
    """
    GIVEN a rulebook with range source plugin that produces 8 events
        and a condition like "i greater or equal than 5"
        or a condition like "i greater than 4"
        and an action to run a playbook that prints the event
    WHEN the program is executed
    THEN the playbook must be executed 3 times printing the event
        and the program must finish without errors
    """
    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
    )

    output = utils.assert_playbook_output(result)

    printed_events = [
        line for line in output if "Event matched" in line["stdout"]
    ]

    assert len(printed_events) == 3

    for event, expected in zip(printed_events, range(5, 8)):
        assert f"{{'i': {expected}}}" in event["stdout"]


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook",
    [
        pytest.param("test_ne_operator_str.yml", id="str"),
        pytest.param("test_ne_operator_int.yml", id="int"),
    ],
)
def test_ne_operator(rulebook, request):
    """
    GIVEN a rulebook with range source plugin that produces 8 events
        and a condition like "i not equal 5"
        and an action to run a playbook that prints the event
    WHEN the program is executed
    THEN the playbook must be executed 7 times printing the event
        and the program must finish without errors
    """
    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
    )

    output = utils.assert_playbook_output(result)

    printed_events = [
        line for line in output if "Event matched" in line["stdout"]
    ]

    assert len(printed_events) == 7
    for event, expected in zip(printed_events, [0, 1, 2, 3, 4, 6, 7]):
        if "str" in request.node.callspec.id:
            expected = f"{{'i': {str(expected)!r}}}"
        else:
            expected = f"{{'i': {expected}}}"
        assert expected in event["stdout"]


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook",
    [
        pytest.param("test_is_defined_operator_str.yml", id="str"),
        pytest.param("test_is_defined_operator_int.yml", id="int"),
        pytest.param("test_is_defined_operator_nested.yml", id="nested"),
        pytest.param(
            "test_not_defined_operator.yml",
            id="negative",
            marks=pytest.mark.xfail(
                reason="Bug https://issues.redhat.com/browse/AAP-7240"
            ),
        ),
        pytest.param(
            "test_not_defined_operator_nested.yml",
            id="negative_nested",
            marks=pytest.mark.xfail(
                reason="Bug https://issues.redhat.com/browse/AAP-7240"
            ),
        ),
    ],
)
def test_defined_operator(rulebook):
    """
    GIVEN a rulebook with range source plugin that produces 5 events
        and a condition like "i is defined"
        and an action to run a playbook that prints the event
    WHEN the program is executed
    THEN the playbook must be executed 5 times printing the event
        and the program must finish without errors
    """

    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
    )

    output = utils.assert_playbook_output(result)

    printed_events = [
        line for line in output if "Event matched" in line["stdout"]
    ]

    assert len(printed_events) == 5


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook,expected_count",
    [
        pytest.param(
            "test_contains_str_single_operator.yml",
            3,
            id="contains_str_single",
        ),
        pytest.param(
            "test_contains_str_single_neg_operator.yml",
            0,
            id="contains_str_single_neg",
        ),
        pytest.param(
            "test_contains_str_combined_operator.yml",
            1,
            id="contains_str_combined",
        ),
        pytest.param(
            "test_contains_int_single_operator.yml",
            3,
            id="contains_int_single",
        ),
        pytest.param(
            "test_contains_int_combined_operator.yml",
            1,
            id="contains_int_combined",
        ),
        pytest.param(
            "test_not_contains_str_single_operator.yml",
            0,
            id="not_contains_str_single",
        ),
        pytest.param(
            "test_not_contains_str_combined_neg_operator.yml",
            2,
            id="not_contains_str_combined",
        ),
        pytest.param(
            "test_not_contains_int_combined_operator.yml",
            1,
            id="not_contains_int_combined",
        ),
    ],
)
def test_contains_operator(rulebook, expected_count):
    """
    GIVEN a rulebook with range source plugin that produces events
        and the event contains an array
        and a condition like "{array} [not] contains {str|int}"
        and an action to run a playbook that prints the event
    WHEN the program is executed
    THEN the playbook must be executed the expected times printing the event
        and the program must finish without errors
    """

    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    cmd = utils.Command(rulebook=rulebook)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
    )

    output = utils.assert_playbook_output(result)

    printed_events = [
        line for line in output if "Event matched" in line["stdout"]
    ]

    assert len(printed_events) == expected_count


@pytest.mark.e2e
@pytest.mark.parametrize(
    "rulebook,expected_count",
    [
        pytest.param(
            "test_in_str_multiple_extra_vars_operator.yml",
            2,
            id="int_combined_multiple_extravars",
        ),
        pytest.param(
            "test_in_int_single_operator.yml",
            1,
            id="int_single",
        ),
        pytest.param(
            "test_not_in_int_extra_vars_operator.yml",
            2,
            id="not_in_int_extravars",
        ),
        pytest.param(
            "test_not_in_str_extra_vars_operator.yml",
            3,
            id="not_in_str_extravars",
        ),
        pytest.param(
            "test_in_str_single_operator.yml",
            2,
            id="str_single",
        ),
        pytest.param(
            "test_not_in_str_single_operator.yml",
            3,
            id="not_in_str_single",
        ),
    ],
)
def test_in_operator(rulebook, expected_count):
    """
    GIVEN a rulebook with range source plugin that produces events
        and the event contains an array
        and a condition like "{array} [not] contains {str|int}"
        and an action to run a playbook that prints the event
    WHEN the program is executed
    THEN the playbook must be executed the expected times printing the event
        and the program must finish without errors
    """

    rulebook = utils.BASE_DATA_PATH / f"rulebooks/operators/{rulebook}"
    vars_file = utils.BASE_DATA_PATH / "extra_vars/operator_variables.yml"
    cmd = utils.Command(rulebook=rulebook, vars_file=vars_file)

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
    )

    output = utils.assert_playbook_output(result)

    printed_events = [
        line for line in output if "Event matched" in line["stdout"]
    ]

    assert len(printed_events) == expected_count
