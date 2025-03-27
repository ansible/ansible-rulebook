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
from ansible_rulebook.util import (
    MASKED_STRING,
    decryptable,
    has_builtin_filter,
    mask_sensitive_variable_values,
)
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


@pytest.mark.parametrize(
    "extra_vars, expected",
    [
        ({"password": "dummy"}, {"password": MASKED_STRING}),
        (
            {
                "TOWER_HOST": "https://ansible.com",
                "TOWER_OAUTH_TOKEN": "dummy-token",
                "TOWER_USERNAME": "admin",
                "TOWER_PASSWORD": "dummy-password",
                "CONTROLLER_HOST": "https://ansible.com",
                "CONTROLLER_OAUTH_TOKEN": "dummy-token",
                "CONTROLLER_USERNAME": "admin",
                "CONTROLLER_PASSWORD": "dummy-password",
            },
            {
                "TOWER_HOST": "https://ansible.com",
                "TOWER_OAUTH_TOKEN": MASKED_STRING,
                "TOWER_USERNAME": "admin",
                "TOWER_PASSWORD": MASKED_STRING,
                "CONTROLLER_HOST": "https://ansible.com",
                "CONTROLLER_OAUTH_TOKEN": MASKED_STRING,
                "CONTROLLER_USERNAME": "admin",
                "CONTROLLER_PASSWORD": MASKED_STRING,
            },
        ),
        (
            {
                "AAP_HOST": "https://ansible.com",
                "AAP_OAUTH_TOKEN": "dummy-token",
                "AAP_USERNAME": "admin",
                "AAP_PASSWORD": "dummy-password",
            },
            {
                "AAP_HOST": "https://ansible.com",
                "AAP_OAUTH_TOKEN": MASKED_STRING,
                "AAP_USERNAME": "admin",
                "AAP_PASSWORD": MASKED_STRING,
            },
        ),
        (
            {
                "postgres_db_host": "https://ansible.com",
                "postgres_db_name": "dummy",
                "postgres_db_port": 5432,
                "postgres_db_password": "dummy-password",
                "postgres_db_user": "dummy",
            },
            {
                "postgres_db_host": "https://ansible.com",
                "postgres_db_name": "dummy",
                "postgres_db_port": 5432,
                "postgres_db_password": MASKED_STRING,
                "postgres_db_user": "dummy",
            },
        ),
        (
            {
                "private_key": "my-private-key",
            },
            {
                "private_key": MASKED_STRING,
            },
        ),
        (
            {"list_check": ["item1", "item2"]},
            {"list_check": ["item1", "item2"]},
        ),
        (
            {"list_check_password": ["item1", "item2"]},
            {"list_check_password": ["item1", "item2"]},
        ),
        (
            {"boolean_test": True, "integer_test": 0},
            {"boolean_test": True, "integer_test": 0},
        ),
        (
            {
                "postgres": {
                    "auth": {"username": "admin", "password": "dummy"}
                },
                "contoller": {
                    "controller_username": "admin",
                    "controller_password": "dummy",
                },
                "test": [
                    {
                        "service1_username": "admin",
                        "service1_password": "dummy",
                        "service1_token": "dummy",
                    },
                    {"service2_username": "admin", "service2_token": "dummy"},
                ],
                "aap_token": "dummy",
            },
            {
                "postgres": {
                    "auth": {"username": "admin", "password": MASKED_STRING}
                },
                "contoller": {
                    "controller_username": "admin",
                    "controller_password": MASKED_STRING,
                },
                "test": [
                    {
                        "service1_username": "admin",
                        "service1_password": MASKED_STRING,
                        "service1_token": MASKED_STRING,
                    },
                    {
                        "service2_username": "admin",
                        "service2_token": MASKED_STRING,
                    },
                ],
                "aap_token": MASKED_STRING,
            },
        ),
    ],
)
def test_mask_sensitive_variable_values(extra_vars, expected):
    assert mask_sensitive_variable_values(extra_vars) == expected
