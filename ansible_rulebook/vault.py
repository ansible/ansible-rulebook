#  Copyright 2024 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import getpass
import shutil
import subprocess
import tempfile

from ansible_rulebook.exception import (
    AnsibleVaultNotFound,
    VaultDecryptException,
)

VAULT_HEADER = "$ANSIBLE_VAULT"
b_VAULT_HEADER = b"$ANSIBLE_VAULT"


class Vault:
    """Vault class allows for decryption."""

    def __init__(
        self,
        passwords: list[dict] = None,
        password_file: str = None,
        vault_ids: list[str] = None,
        ask_pass: bool = False,
    ):
        cli_args = []
        self.tempfiles = []

        has_vault_config = ask_pass or password_file or vault_ids or passwords
        if has_vault_config and not shutil.which("ansible-vault"):
            raise AnsibleVaultNotFound

        if ask_pass:
            secret = getpass.getpass(prompt="Vault password: ")
            tmpf = tempfile.NamedTemporaryFile("w+t", suffix=".vaultpw")
            tmpf.write(secret)
            tmpf.flush()
            self.tempfiles.append(tmpf)
            cli_args += ["--vault-password-file", tmpf.name]

        if password_file:
            cli_args += ["--vault-password-file", password_file]

        if not vault_ids:
            vault_ids = []
        for item in passwords or []:
            if item["type"] == "VaultPassword":
                tmpf = tempfile.NamedTemporaryFile("w+t")
                tmpf.write(item["password"])
                tmpf.flush()
                self.tempfiles.append(tmpf)
                vault_ids.append(f"{item['label']}@{tmpf.name}")

        for vid in vault_ids:
            cli_args += ["--vault-id", vid]

        if cli_args:
            self.cli_args = ["ansible-vault", "decrypt"] + cli_args
        else:
            self.cli_args = None

    def decrypt(self, vault_text: str) -> str:
        """Decrypt a vault text.

        Pipes ciphertext to ansible-vault via subprocess stdin.
        subprocess.run with input= uses communicate() for coordinated
        read/write, handling arbitrarily large payloads on all platforms.
        """
        if not self.cli_args:
            raise VaultDecryptException("No vault secrets were provided")

        try:
            result = subprocess.run(
                self.cli_args,
                capture_output=True,
                input=vault_text,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise VaultDecryptException(
                "ansible-vault decrypt timed out"
            ) from exc

        if result.returncode != 0:
            raise VaultDecryptException(result.stderr.strip())

        return result.stdout.rstrip("\n")

    @staticmethod
    def is_encrypted(vault_text: str) -> bool:
        """Check if a text is encrypted."""
        return vault_text.count(VAULT_HEADER) > 0

    def close(self) -> None:
        for file in self.tempfiles:
            file.close()


def has_vaulted_str(data: bytes) -> bool:
    """Check whether the data may contain ansible vault encrypted string"""
    return data.count(b_VAULT_HEADER) > 0
