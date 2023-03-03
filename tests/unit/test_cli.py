import re
from unittest.mock import patch

import pytest

from ansible_rulebook.cli import get_version
from ansible_rulebook.util import check_jvm


def test_get_version():
    output = get_version()
    pattern = re.compile(
        r"""(.+)\d+\.\d+\.\d+'
  Executable location = (.+)
  Drools_jpy version = \d+\.\d+\.\d+
  Java home = (.+)
  Java version = \d+\.\d+\.\d+(\.\d+)?
  Python version = \d+\.\d+\.\d+ (.+)$"""
    )
    assert pattern.match(output)


def test_check_jvm_bad_java_home():
    @patch("ansible_rulebook.util.get_java_home")
    def get_java_home(mock_response):
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
        pytest.param("Not found", id="not_found"),
    ],
)
def test_check_jvm_bad_version(mocked_version):
    @patch("ansible_rulebook.util.get_java_version")
    def get_java_version(mock_response):
        mock_response.return_value = mocked_version
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
    ],
)
def test_check_jvm_java_version(mocked_version):
    @patch("ansible_rulebook.util.get_java_version")
    def get_java_version(mock_response):
        mock_response.return_value = mocked_version
        result = check_jvm()
        assert result is None
