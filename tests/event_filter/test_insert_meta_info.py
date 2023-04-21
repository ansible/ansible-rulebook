from unittest.mock import patch

import pytest
from freezegun import freeze_time

from ansible_rulebook.event_filter.insert_meta_info import main as sources_main

DUMMY_UUID = "eb7de03f-6f8f-4943-b69e-3c90db346edf"
DEFAULT_RECEIVED_AT = "2023-03-23T11:11:11Z"
EVENT_DATA_1 = [
    (
        {"myevent": {"name": "fred"}},
        {"source_name": "my_source", "source_type": "stype"},
        {
            "myevent": {"name": "fred"},
            "meta": {
                "source": {"name": "my_source", "type": "stype"},
                "received_at": DEFAULT_RECEIVED_AT,
                "uuid": DUMMY_UUID,
            },
        },
    ),
    (
        {
            "myevent": {"name": "barney"},
            "meta": {"source": {"name": "origin", "type": "regular"}},
        },
        {"source_name": "my_source", "source_type": "stype"},
        {
            "myevent": {"name": "barney"},
            "meta": {
                "source": {"name": "origin", "type": "regular"},
                "received_at": DEFAULT_RECEIVED_AT,
                "uuid": DUMMY_UUID,
            },
        },
    ),
]


@freeze_time("2023-03-23 11:11:11")
@pytest.mark.parametrize("data, args, expected", EVENT_DATA_1)
def test_sources_main(data, args, expected):
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        data = sources_main(data, **args)
        assert data == expected
