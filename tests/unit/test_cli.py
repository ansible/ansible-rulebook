import re

import pytest

from ansible_rulebook.cli import show_version


def test_show_version(capsys):
    with pytest.raises(SystemExit):
        show_version()
    output = capsys.readouterr()
    assert not output.err
    pattern = re.compile(
        r"""(.+)\d+\.\d+\.\d+'
  Executable location = (.+)
  Drools_jpy version = \d+\.\d+\.\d+
  Java home = (.+)
  Java version = (.+)\d+\.\d+\.\d+(.+)
  Python version = \d+\.\d+\.\d+ (.+)$"""
    )
    assert pattern.match(output.out)
