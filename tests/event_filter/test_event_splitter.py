#  Copyright 2025 Red Hat, Inc.
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

from ansible_rulebook.event_filter.event_splitter import main as filter_main

EVENT_DATA_1 = [
    (
        {"myevent": {"bundle": [{"name": "Fred"}, {"name": "Barney"}]}},
        {"splitter_key": "myevent.bundle"},
        [{"name": "Fred"}, {"name": "Barney"}],
    ),
    (
        {"myevent": {"bundle": [{"name": "Fred"}, {"name": "Barney"}]}},
        {"splitter_key": "myevent.missing"},
        [{"myevent": {"bundle": [{"name": "Fred"}, {"name": "Barney"}]}}],
    ),
    (
        {
            "myevent": {
                "bundle": [{"name": "Fred"}, {"name": "Barney"}],
                "city": "Bedrock",
            }
        },
        {
            "splitter_key": "myevent.bundle",
            "attributes_key_map": {"town": "myevent.city"},
        },
        [
            {"name": "Fred", "town": "Bedrock"},
            {"name": "Barney", "town": "Bedrock"},
        ],
    ),
    (
        {
            "myevent": {
                "bundle": [{"name": "Fred"}, {"name": "Barney"}],
                "city": "Bedrock",
            }
        },
        {
            "splitter_key": "myevent.bundle",
            "attributes_key_map": {"town": "myevent.city"},
            "extras": {"zip": "07054"},
        },
        [
            {"name": "Fred", "town": "Bedrock", "zip": "07054"},
            {"name": "Barney", "town": "Bedrock", "zip": "07054"},
        ],
    ),
    (
        {
            "myevent": {
                "bundle": [{"name": "Fred"}, {"name": "Barney"}],
                "city": "Bedrock",
            }
        },
        {
            "splitter_key": "myevent.bundle",
            "attributes_key_map": {"town": "myevent.village"},
        },
        [{"name": "Fred"}, {"name": "Barney"}],
    ),
]


@pytest.mark.parametrize("data, args, expected", EVENT_DATA_1)
def test_filter_main(data, args, expected):
    data = filter_main(data, **args)
    assert data == expected


def test_filter_main_exception():
    data = ({"myevent": {"bundle": [{"name": "Fred"}, {"name": "Barney"}]}},)
    args = {"splitter_key": "myevent.missing", "raise_error": True}
    with pytest.raises(KeyError):
        filter_main(data, **args)
