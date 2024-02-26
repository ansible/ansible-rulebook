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

import os

import pytest

from ansible_rulebook.exception import VaultDecryptException
from ansible_rulebook.vault import Vault


@pytest.fixture
def encrypt_hello():
    return (
        "$ANSIBLE_VAULT;1.1;AES256\n"
        "66613134623661333435363432336431316133396261373931616462643134393732343736336266\n"  # noqa: E501
        "6535303139326434373031336663333865313134353161310a663965656561656262393166396634\n"  # noqa: E501
        "61383065613366336530616666306438633866623033346661626433376436316435666137333638\n"  # noqa: E501
        "6138326466356262360a646663653962363036623939346466373938656433363035316333366565\n"  # noqa: E501
        "3639"
    )


@pytest.fixture
def encrypt_world():
    return (
        "$ANSIBLE_VAULT;1.1;AES256;label1\n"
        "31323665343066323133636236666564356433336534363430646266323364363535366131313762\n"  # noqa: E501
        "3439333463303665373365353666663663373430623263620a396163383938393536623532363832\n"  # noqa: E501
        "38666565323934343130636165653838323030656139313638396662643930656639626530356331\n"  # noqa: E501
        "3532653233323666380a323266656462323636636332323733323363323332623362366564653963\n"  # noqa: E501
        "3935"
    )


HERE = os.path.dirname(os.path.abspath(__file__))


def test_decrypt(encrypt_hello, encrypt_world):
    os.chdir(HERE)
    passwords = [
        {"type": "VaultPassword", "label": "label1", "password": "pass2"}
    ]
    myvault = Vault(passwords=passwords, password_file="./pass1.txt")

    try:
        assert myvault.is_encrypted(encrypt_hello)
        assert myvault.is_encrypted(encrypt_world)
        assert myvault.decrypt(encrypt_hello) == "hello"
        assert myvault.decrypt(encrypt_world) == "world"
    finally:
        myvault.close()


def test_decrypt_vault_id(encrypt_hello, encrypt_world):
    os.chdir(HERE)
    passwords = [
        {"type": "VaultPassword", "label": "label1", "password": "pass2"}
    ]
    myvault = Vault(passwords=passwords, vault_ids=["lab@./pass1.txt"])

    try:
        assert os.path.exists(myvault.tempfiles[0].name)
        assert myvault.is_encrypted(encrypt_hello)
        assert myvault.is_encrypted(encrypt_world)
        assert myvault.decrypt(encrypt_hello) == "hello"
        assert myvault.decrypt(encrypt_world) == "world"
    finally:
        myvault.close()
        assert not os.path.exists(myvault.tempfiles[0].name)


def test_decrypt_error(encrypt_world):
    os.chdir(HERE)
    myvault = Vault(password_file="./pass1.txt")
    with pytest.raises(VaultDecryptException):
        try:
            myvault.decrypt(encrypt_world)
        finally:
            myvault.close()
