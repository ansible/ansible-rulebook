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
import tempfile

import pexpect

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
        cli_args = ""
        if ask_pass:
            self.secret = getpass.getpass(prompt="Vault password: ")
            cli_args = " --ask-vault-pass"
        else:
            self.secret = None

        if password_file:
            cli_args += f" --vault-password-file {password_file}"

        if not vault_ids:
            vault_ids = []
        self.tempfiles = []
        for item in passwords or []:
            if item["type"] == "VaultPassword":
                tmpf = tempfile.NamedTemporaryFile("w+t")
                tmpf.write(item["password"])
                tmpf.flush()
                self.tempfiles.append(tmpf)
                vault_ids.append(f"{item['label']}@{tmpf.name}")

        for vid in vault_ids:
            cli_args += f" --vault-id {vid}"

        if cli_args:
            if not shutil.which("ansible-vault"):
                raise AnsibleVaultNotFound
            self.cli = f"ansible-vault decrypt {cli_args}"
        else:
            self.cli = None

    def decrypt(self, vault_text: str) -> str:
        """Decrypt a vault text."""
        if not self.cli:
            raise VaultDecryptException("No vault secrets were provided")
        child = pexpect.spawn(self.cli)
        if self.secret:
            child.expect("Vault password: ")
            child.sendline(self.secret)
        child.expect("Reading ciphertext input from stdin")
        child.sendline(vault_text)
        child.sendcontrol("D")
        i = child.expect(["Decryption successful", "ERROR"])
        if i == 0:
            child.readline()
            decrypted_text = "".join(line.decode() for line in child)
            return decrypted_text.strip()
        else:
            error_msg = child.readline()
            raise VaultDecryptException(error_msg.decode())

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
