import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ansible_rulebook.cli import main
from ansible_rulebook.util import (
    check_jvm,
    get_version,
    validate_file_path,
    validate_url,
)


def test_get_version():
    output = get_version()
    pattern = re.compile(
        r"""ansible-rulebook \[\d+\.\d+\.\d+(?:\..*)?\]
  Executable location = (.+)
  Drools_jpy version = \d+\.\d+\.\d+
  Java home = (.+)
  Java version = \d+(\.\d+)?(\.\d+)?(\.\d+)?
  Ansible core version = \d+\.\d+\.\d+([a-zA-Z0-9\+\-\.]*)?
  Python version = \d+\.\d+\.\d+([a-zA-Z0-9\+\-\.]*)?
  Python executable = (\S+)
  Platform = (.+)$"""
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


@pytest.mark.parametrize(
    "url, url_type, expected_bool",
    [
        ("http:///example.com", "controller", False),
        ("example.com:8080", "controller", False),
        ("https://example.com", "controller", True),
        ("https://example.com:8080", "controller", True),
        ("wss://example.com:443", "websocket", True),
        ("wss:///example.com:443", "websocket", False),
    ],
)
def test_validate_url(url, url_type, expected_bool):
    res = validate_url(url, url_type)
    assert res == expected_bool


class TestVaultFilePathValidation:
    """Tests for vault password file path validation."""

    def test_validate_vault_file_path_valid(self):
        """Test validation with a valid vault password file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test_password")
            temp_path = f.name

        try:
            result = validate_file_path(temp_path, "Vault password file")
            # Should return the resolved absolute path
            assert result is not None
            assert Path(result).exists()
            assert Path(result).is_file()
        finally:
            Path(temp_path).unlink()

    def test_validate_vault_file_path_empty_string(self):
        """Test validation rejects empty string."""
        with pytest.raises(ValueError) as exc_info:
            validate_file_path("", "Vault password file")

        assert "cannot be empty" in str(exc_info.value)

    def test_validate_vault_file_path_nonexistent(self):
        """Test validation rejects nonexistent file."""
        with pytest.raises(ValueError) as exc_info:
            validate_file_path(
                "/tmp/nonexistent_vault_file_xyz123", "Vault password file"
            )

        assert "does not exist" in str(exc_info.value)

    def test_validate_vault_file_path_directory(self):
        """Test validation rejects directory paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(ValueError) as exc_info:
                validate_file_path(temp_dir, "Vault password file")

            assert "not a file" in str(exc_info.value)

    def test_validate_vault_file_path_null_byte(self):
        """Test validation rejects paths with null bytes."""
        with pytest.raises(ValueError) as exc_info:
            validate_file_path("/tmp/file\x00injected", "Vault password file")

        # OS raises ValueError with "null character" or our custom check
        assert "null" in str(exc_info.value).lower()

    def test_validate_vault_file_path_resolves_symlinks(self):
        """Test that validation resolves symlinks to canonical path."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            f.write("test_password")
            real_path = f.name

        try:
            # Create a symlink to the real file
            symlink_path = f"{real_path}_link"
            Path(symlink_path).symlink_to(real_path)

            try:
                result = validate_file_path(
                    symlink_path, "Vault password file"
                )
                # Should resolve to the real file path
                assert Path(result).resolve() == Path(real_path).resolve()
            finally:
                Path(symlink_path).unlink()
        finally:
            Path(real_path).unlink()

    def test_validate_vault_file_path_relative_path(self):
        """Test validation handles relative paths."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=".") as f:
            f.write("test_password")
            temp_path = Path(f.name).name  # Just the filename

        try:
            # Change to the directory containing the file
            result = validate_file_path(temp_path, "Vault password file")
            # Should resolve to absolute path
            assert Path(result).is_absolute()
            assert Path(result).exists()
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestParseVaultPasswords:
    """Tests for vault password parsing with file validation."""

    def test_parse_vault_password_file_valid(self, tmp_path):
        """Test parsing with valid vault password file."""
        from argparse import Namespace

        from ansible_rulebook.cli import parse_vault_passwords

        # Create a temporary vault password file
        vault_file = tmp_path / "vault_password"
        vault_file.write_text("my_secret_password")

        args = Namespace(
            vault_password_file=str(vault_file),
            vault_id=[],
            ask_vault_pass=False,
        )

        # Should not raise any exception
        parse_vault_passwords(args)

    def test_parse_vault_password_file_invalid(self, capsys):
        """Test parsing with invalid vault password file."""
        from argparse import Namespace

        from ansible_rulebook.cli import parse_vault_passwords

        args = Namespace(
            vault_password_file="/nonexistent/vault_file",
            vault_id=[],
            ask_vault_pass=False,
        )

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            parse_vault_passwords(args)

        assert exc_info.value.code == 1

    def test_parse_vault_id_with_file_valid(self, tmp_path):
        """Test parsing with valid vault ID file."""
        from argparse import Namespace

        from ansible_rulebook.cli import parse_vault_passwords

        # Create a temporary vault ID file
        vault_id_file = tmp_path / "vault_id_file"
        vault_id_file.write_text("vault_secret")

        args = Namespace(
            vault_password_file=None,
            vault_id=[f"prod@{vault_id_file}"],
            ask_vault_pass=False,
        )

        # Should not raise any exception
        parse_vault_passwords(args)

    def test_parse_vault_id_with_file_invalid(self):
        """Test parsing with invalid vault ID file."""
        from argparse import Namespace

        from ansible_rulebook.cli import parse_vault_passwords

        args = Namespace(
            vault_password_file=None,
            vault_id=["prod@/nonexistent/vault_id_file"],
            ask_vault_pass=False,
        )

        # Should exit with error
        with pytest.raises(SystemExit) as exc_info:
            parse_vault_passwords(args)

        assert exc_info.value.code == 1

    def test_parse_vault_id_without_file(self):
        """Test parsing vault ID without file (prompt case)."""
        from argparse import Namespace

        from ansible_rulebook.cli import parse_vault_passwords

        args = Namespace(
            vault_password_file=None,
            vault_id=["prod"],  # No @ means it's a prompt ID
            ask_vault_pass=False,
        )

        # Should not raise any exception
        parse_vault_passwords(args)

    def test_parse_vault_no_options(self):
        """Test parsing with no vault options."""
        from argparse import Namespace

        from ansible_rulebook.cli import parse_vault_passwords

        args = Namespace(
            vault_password_file=None, vault_id=[], ask_vault_pass=False
        )

        # Should return early without error
        parse_vault_passwords(args)
