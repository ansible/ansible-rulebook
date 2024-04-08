"""
Module with tests for the use of variables
"""
import logging
import subprocess

import pexpect
import pytest

from . import utils
from .settings import SETTINGS

LOGGER = logging.getLogger(__name__)
DEFAULT_CMD_TIMEOUT = SETTINGS["cmd_timeout"]
DEFAULT_EVENT_DELAY = SETTINGS["default_event_delay"]


@pytest.mark.e2e
def test_decrypt_vault():
    """
    Execute a rulebook that has variable encrypted in place or via an
    external variable.
    """
    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_vaulted_rulebook.yml"
    vars_file = utils.BASE_DATA_PATH / "extra_vars/vaulted_variables.yml"
    vault_password_file = utils.BASE_DATA_PATH / "passwords/pass3.txt"
    vault_ids = [
        ("label1", utils.BASE_DATA_PATH / "passwords/pass1.txt"),
        (None, utils.BASE_DATA_PATH / "passwords/pass2.txt"),
    ]
    cmd = utils.Command(
        rulebook=rulebook,
        vars_file=vars_file,
        vault_ids=vault_ids,
        vault_password_file=vault_password_file,
    )

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )
    assert result.returncode == 0
    assert not result.stderr
    assert "hello" in result.stdout


@pytest.mark.e2e
def test_decrypt_vault_ask_pass():
    """
    Execute a rulebook that needs a password from cli console.
    """
    password = "secret3"
    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_vaulted_v2.yml"
    command = f"ansible-rulebook --rulebook {rulebook} --ask-vault-pass"
    child = pexpect.spawn(command)
    child.timeout = 10
    child.expect("Vault password: ")
    child.sendline(password)
    child.sendcontrol("D")
    child.readline()
    child.readline()
    child.readline()
    assert b"hello" in child.readline()


@pytest.mark.e2e
def test_decrypt_vault_with_interpolation():
    """
    Execute a rulebook that has variable encrypted with string interpolation.
    """
    rulebook = (
        utils.BASE_DATA_PATH
        / "rulebooks/test_vaulted_rulebook_interpolate.yml"
    )
    vars_file = utils.BASE_DATA_PATH / "extra_vars/vaulted_variables.yml"
    vault_password_file = utils.BASE_DATA_PATH / "passwords/pass3.txt"
    vault_ids = [
        ("label1", utils.BASE_DATA_PATH / "passwords/pass1.txt"),
        (None, utils.BASE_DATA_PATH / "passwords/pass2.txt"),
    ]
    cmd = utils.Command(
        rulebook=rulebook,
        vars_file=vars_file,
        vault_ids=vault_ids,
        vault_password_file=vault_password_file,
    )

    LOGGER.info(f"Running command: {cmd}")
    result = subprocess.run(
        cmd,
        timeout=DEFAULT_CMD_TIMEOUT,
        capture_output=True,
        cwd=utils.BASE_DATA_PATH,
        text=True,
    )
    assert result.returncode == 0
    assert not result.stderr
    assert "hello" in result.stdout
