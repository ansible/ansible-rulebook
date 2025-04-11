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
import importlib.metadata
import logging
import subprocess
from unittest.mock import patch

import pytest

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    InvalidFilterNameException,
    VaultDecryptException,
)
from ansible_rulebook.util import (
    MASKED_STRING,
    decryptable,
    get_installed_collections,
    get_package_version,
    get_version,
    has_builtin_filter,
    mask_sensitive_variable_values,
    startup_logging,
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


def test_get_package_version(caplog):
    assert get_package_version("aiohttp") == importlib.metadata.version(
        "aiohttp"
    )

    # assert outcome when package is not found
    with patch(
        "importlib.metadata.version",
        side_effect=importlib.metadata.PackageNotFoundError,
    ):
        assert get_package_version("idonotexist") == "unknown"
        assert "Cannot read version" in caplog.text


@patch("ansible_rulebook.conf.settings.ansible_galaxy_path", None)
def test_get_installed_collections_no_ansible_galaxy_path():
    assert get_installed_collections() is None


@patch(
    "ansible_rulebook.conf.settings.ansible_galaxy_path",
    "/path/to/ansible-galaxy",
)
def test_get_installed_collections_success():
    subprocess_output = "collection1\ncollection2\n"
    subprocess_mock = subprocess.CompletedProcess(
        args=["/path/to/ansible-galaxy", "collection", "list"],
        returncode=0,
        stdout=subprocess_output,
        stderr="",
    )
    subprocess_run_mock = subprocess_mock
    subprocess_run_mock.stdout = subprocess_output
    subprocess_run_mock.stderr = ""
    subprocess_run_mock.check_returncode = lambda: None

    with patch("subprocess.run", return_value=subprocess_run_mock) as run_mock:
        assert get_installed_collections() == subprocess_output

    run_mock.assert_called_once_with(
        ["/path/to/ansible-galaxy", "collection", "list"],
        check=True,
        text=True,
        capture_output=True,
    )


@patch(
    "ansible_rulebook.conf.settings.ansible_galaxy_path",
    "/path/to/ansible-galaxy",
)
def test_get_installed_collections_error():
    subprocess_error = subprocess.CalledProcessError(
        returncode=1, cmd=["ansible-galaxy"]
    )
    subprocess_run_mock = subprocess_error
    subprocess_run_mock.check_returncode = lambda: None

    with patch("subprocess.run", side_effect=subprocess_run_mock) as run_mock:
        assert get_installed_collections() is None

    run_mock.assert_called_once_with(
        [settings.ansible_galaxy_path, "collection", "list"],
        check=True,
        text=True,
        capture_output=True,
    )


def test_startup_logging(caplog):
    logger = logging.getLogger("test_logger")
    version_output = get_version()

    with patch(
        "ansible_rulebook.util.get_installed_collections",
        return_value="collection1\ncollection2\n",
    ):
        startup_logging(logger)
    assert version_output in caplog.text
    assert "collection1\ncollection2" not in caplog.text
    logger.setLevel(logging.DEBUG)
    with patch(
        "ansible_rulebook.util.get_installed_collections",
        return_value="collection1\ncollection2\n",
    ):
        startup_logging(logger)
    assert "collection1\ncollection2" in caplog.text


def test_startup_logging_no_collections(caplog):
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.DEBUG)
    version_output = get_version()
    with patch(
        "ansible_rulebook.util.get_installed_collections",
        return_value=None,
    ):
        startup_logging(logger)
    assert version_output in caplog.text
    assert "No collections found" in caplog.text


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