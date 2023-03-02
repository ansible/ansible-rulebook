#  Copyright 2022 Red Hat, Inc.
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

from ansible_rulebook import plugin_utils

EVENT_DATA_1 = [
    (
        {"app": {"target": "webserver"}},
        {"data_host_path": "app.target"},
        ["webserver"],
    ),
    (
        {"app": {"target": "webserver;postgres"}},
        {
            "data_host_path": "app/target",
            "data_path_separator": "/",
            "data_host_separator": ";",
        },
        ["webserver", "postgres"],
    ),
    (
        {
            "app": {"target": ["webserver", "postgres"]},
            "meta": {"source": "upstream"},
        },
        {
            "data_host_path": "app.target",
        },
        ["webserver", "postgres"],
    ),
    (
        {"app": "foo", "meta": {"source": "upstream"}},
        {
            "data_host_path": "bar",
        },
        [],
    ),
    (
        {"app": "foo", "meta": {"source": "upstream"}},
        {
            "foo": "bar",
        },
        [],
    ),
]


@pytest.mark.parametrize("data, args, expected_hosts", EVENT_DATA_1)
def test_find_hosts(data, args, expected_hosts):
    plugin_utils.insert_hosts_to_meta(data, args)
    if expected_hosts:
        assert data["meta"]["hosts"] == expected_hosts
    else:
        assert "hosts" not in data["meta"]


EVENT_DATA_2 = [
    (
        {"app": {"target": 5000}},
        {"data_host_path": "app.target"},
    ),
    (
        {"app": {"target": ("host1", 5000)}},
        {"data_host_path": "app.target"},
    ),
    (
        {"app": {"target": {"foo": "bar"}}},
        {"data_host_path": "app.target"},
    ),
]


@pytest.mark.parametrize("data, args", EVENT_DATA_2)
def test_fail_find_hosts(data, args):
    with pytest.raises(TypeError):
        plugin_utils.insert_hosts_to_meta(data, args)
