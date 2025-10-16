"""
E2E tests for collection plugin deprecation handling.
"""

import logging
import os
import subprocess

import pytest

from ansible_rulebook.conf import settings as app_settings

from . import utils
from .settings import SETTINGS

LOGGER = logging.getLogger(__name__)
DEFAULT_CMD_TIMEOUT = SETTINGS["cmd_timeout"]


@pytest.mark.e2e
def test_collection_plugin_deprecation(update_environment):
    """
    Ensure deprecation warnings are printed for redirected collection plugins.
    """
    if app_settings.ansible_galaxy_path is None:
        pytest.skip("ansible-galaxy command is not available")

    collections_root = (utils.BASE_DATA_PATH / "collections").resolve()

    env = update_environment()
    existing_paths = env.get("ANSIBLE_COLLECTIONS_PATHS", "")
    path_list = [str(collections_root)]
    if existing_paths:
        path_list.append(existing_paths)

    env.update(
        {
            "ANSIBLE_COLLECTIONS_PATHS": os.pathsep.join(path_list),
            "ANSIBLE_COLLECTIONS_PATH": str(collections_root),
        }
    )

    rulebook = utils.BASE_DATA_PATH / "rulebooks/plugin_deprecation.yml"
    cmd = utils.Command(
        rulebook=rulebook,
        sources=None,
        filters=None,
    )

    LOGGER.info("Running command: %s", cmd)
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
        env=env,
    )

    assert result.returncode == 0
    stderr_output = result.stderr or ""
    assert "Use testns.testcol.new_plugin instead." in stderr_output
    assert "Redirects to 'testns.testcol.new_plugin'." in stderr_output

    stdout_output = result.stdout or ""
    assert "redirected plugin executed" in stdout_output
