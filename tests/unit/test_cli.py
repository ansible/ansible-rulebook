import re
import sys
from unittest.mock import patch

import pytest

from ansible_rulebook.cli import get_version, main
from ansible_rulebook.util import check_jvm


def test_get_version():
    output = get_version()
    pattern = re.compile(
        r"""\d+\.\d+\.\d+
  Executable location = (.+)
  Drools_jpy version = \d+\.\d+\.\d+
  Java home = (.+)
  Java version = \d+(\.\d+)?(\.\d+)?(\.\d+)?
  Python version = \d+\.\d+\.\d+ (.+)$"""
    )
    assert pattern.match(output)


@patch("ansible_rulebook.util.get_java_home")
def test_check_jvm_bad_java_home(mock_response):
    mock_response.return_value = None

    with pytest.raises(SystemExit) as excinfo:
        check_jvm()
        assert excinfo.value.code == 1


@pytest.mark.parametrize(
    "mocked_version",
    [
        pytest.param(
            "11.0.2",
            id="lower",
        ),
        pytest.param(
            "1.8.0_875",
            id="lower_wrong_semantic",
        ),
        pytest.param("Not found", id="not_found"),
    ],
)
@patch("ansible_rulebook.util.get_java_version")
def test_check_jvm_bad_version(mock, mocked_version):
    mock.return_value = mocked_version

    with pytest.raises(SystemExit) as excinfo:
        check_jvm()
        assert excinfo.value.code == 1


@pytest.mark.parametrize(
    "mocked_version",
    [
        pytest.param(
            "17.0.2",
            id="semantic",
        ),
        pytest.param("17.1.5.3", id="semantic_extended"),
        pytest.param("17.1.5_3", id="wrong_semantic"),
    ],
)
@patch("ansible_rulebook.util.get_java_version")
def test_check_jvm_java_version(mock, mocked_version):
    mock.return_value = mocked_version
    result = check_jvm()
    assert result is None


def test_main_no_args():
    with patch.object(sys, "argv", ["ansible-rulebook"]):
        with pytest.raises(SystemExit) as excinfo:
            main([])
            assert excinfo.value.code == 1


all_args = [
    "-r",
    "rulebook.yml",
    "-vv",
    "--controller-url",
    "https://www.example.com",
    "--controller-token",
    "abc",
    "--controller-ssl-verify",
    "no",
]
test_data = [
    (KeyboardInterrupt("Bail"), 0, ["-r", "rulebook.yml", "-v"], True),
    (Exception("Kaboom"), 1, ["-r", "rulebook.yml"], True),
    (None, 1, ["-r", "rulebook.yml", "--controller-url", "abc"], False),
    (None, 0, ["-w", "--id", "123", "-W", "example.com"], True),
    (None, 0, all_args, True),
]


@pytest.mark.parametrize("ex, expected_rc, args, called", test_data)
@patch("ansible_rulebook.cli.app.run")
def test_main_raise_exception(mock, ex, expected_rc, args, called):
    if ex:
        mock.side_effect = ex
    with patch.object(sys, "argv", args):
        rc = main(args)
        assert mock.called == called
        assert rc == expected_rc


test_data = [
    (["-r", "helloworld.yml", "-w"]),
    (["-vv", "--id", "10"]),
]


@pytest.mark.parametrize("args", test_data)
def test_main_invalid_args(args):
    with patch.object(sys, "argv", args):
        with pytest.raises(ValueError):
            main(args)
