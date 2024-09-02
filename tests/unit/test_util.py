#  Copyright 2023 Red Hat, Inc.
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
import pytest

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    InvalidFilterNameException,
    VaultDecryptException,
)
from ansible_rulebook.util import decryptable, has_builtin_filter
from ansible_rulebook.vault import Vault

TEST_PASSWORD = "secret"

FRED = (
    "$ANSIBLE_VAULT;1.1;AES256\n"
    "316365636638653961346230633664336265643233"
    "66653065393430383361373438623331363836\n"
    "653336326262313433373035646335626264633631"
    "6433620a313464386630326163353031313563\n"
    "386332303732313831623030326539333135363437"
    "66336132303539373836343137613761663834\n"
    "6134393138383234360a3064393136313030663732"
    "39313031303836653566323930643462623961\n"
    "3866"
)

BARNEY = (
    "$ANSIBLE_VAULT;1.1;AES256\n"
    "616361626134646337386632323933643534663033"
    "35313336633835303230616231663133613061\n"
    "376438356666346164396630613437653466323133"
    "3832630a643138396136623536383532656130\n"
    "343230373864306434383532646435396239396563"
    "33656334323262353436316562643466383564\n"
    "3466376465323866380a3261653138613934646436"
    "64393838336130323537333566386339323733\n"
    "6138"
)


def test_bad_builtin_filter():
    with pytest.raises(InvalidFilterNameException):
        has_builtin_filter("eda.builtin.")


def test_has_builtin_filter():
    assert has_builtin_filter("eda.builtin.insert_meta_info")


def test_has_builtin_filter_missing():
    assert not has_builtin_filter("eda.builtin.something_missing")


def test_builtin_filter_bad_prefix():
    assert not has_builtin_filter("eda.gobbledygook.")


test_data = [
    {
        "A": FRED,
        "NESTED": {"B": BARNEY, "flag": True, "x": [FRED, BARNEY]},
    },
    FRED,
    True,
    12,
    [FRED, BARNEY],
    "Hello World",
    "This is event data {{ event.i }}",
]


@pytest.mark.parametrize("obj", test_data)
def test_decryptable(obj):
    vault_info = {
        "type": "VaultPassword",
        "label": "test",
        "password": TEST_PASSWORD,
    }
    settings.vault = Vault(passwords=[vault_info])

    try:
        decryptable(obj)
    except Exception as exc:
        raise AssertionError(f"test raised an exception {exc}")


bad_test_data = [
    {
        "A": FRED,
        "NESTED": {"B": BARNEY, "flag": True, "x": [FRED, BARNEY]},
    },
    FRED,
    [FRED, BARNEY],
]


@pytest.mark.parametrize("obj", bad_test_data)
def test_decryptable_with_errors(obj):
    vault_info = {
        "type": "VaultPassword",
        "label": "test",
        "password": "bogus",
    }
    settings.vault = Vault(passwords=[vault_info])

    with pytest.raises(VaultDecryptException):
        decryptable(obj)
