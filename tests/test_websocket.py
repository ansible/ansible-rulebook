import asyncio
import base64
import hashlib
import json
import os
from typing import Dict, List
from unittest import mock
from unittest.mock import AsyncMock, patch

import pytest
import websockets

from ansible_rulebook.conf import settings
from ansible_rulebook.websocket import (
    request_workload,
    send_event_log_to_websocket,
)


def prepare_settings() -> None:
    settings.websocket_url = "wss://dummy.org/ws"
    settings.websocket_token_url = "https://dummy.org/token"
    settings.websocket_access_token = "dummy"
    settings.websocket_refresh_token = "dummy"


def file_sha256(filename: str) -> str:
    sha256_hash = hashlib.sha256()
    with open(filename, "rb") as f:
        while filedata := f.read(4096):
            sha256_hash.update(filedata)
    return sha256_hash.hexdigest()


def dict2json(data: Dict) -> str:
    return json.dumps(data).encode("utf-8")


def load_file(
    filename: str,
    data_type: str,
    data_list: List,
    whole_file=False,
    block_size: int = 1024,
) -> None:
    with open(filename, "rb") as f:
        if whole_file:
            data_list.append(
                json.dumps(
                    {
                        "type": data_type,
                        "data": base64.b64encode(f.read()).decode("ascii"),
                    }
                ).encode("utf-8")
            )
        else:
            while filedata := f.read(block_size):
                data_list.append(
                    json.dumps(
                        {
                            "type": data_type,
                            "data": base64.b64encode(filedata).decode("ascii"),
                            "more": True,
                        }
                    ).encode("utf-8")
                )
            data_list.append(dict2json({"type": data_type}))


HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.asyncio
async def test_request_workload():
    prepare_settings()
    os.chdir(HERE)
    controller_url = "https://www.example.com"
    controller_token = "abc"
    controller_ssl_verify = "no"
    test_data = []
    tar_file = "./data/test.tar"
    sha1 = "9691bc9ed954cb3302240fb83ccb60dc2dd999ee24ab2bf5af7427433f9ce2ca"
    test_data.append(
        dict2json(
            dict(
                type="ControllerInfo",
                url=controller_url,
                token=controller_token,
                ssl_verify=controller_ssl_verify,
            )
        )
    )
    load_file(tar_file, "ProjectData", test_data, False)
    load_file("./rules/rules.yml", "Rulebook", test_data, True)
    load_file("./playbooks/inventory.yml", "Inventory", test_data, True)
    load_file("./data/test_vars.yml", "ExtraVars", test_data, True)
    test_data.append(dict2json({"type": "EndOfResponse"}))

    with patch("ansible_rulebook.websocket.websockets.connect") as mo:
        mo.return_value.__aenter__.return_value.recv.side_effect = test_data
        mo.return_value.__aenter__.return_value.send.return_value = None

        response = await request_workload("dummy")
        sha2 = file_sha256(response.project_data_file)
        assert sha1 == sha2
        assert response.controller_url == controller_url
        assert response.controller_token == controller_token
        assert response.controller_ssl_verify == controller_ssl_verify
        assert response.rulesets[0].name == "Demo rules"
        assert len(response.rulesets[0].rules) == 6


@pytest.mark.asyncio
async def test_send_event_log_to_websocket():
    prepare_settings()
    queue = asyncio.Queue()
    queue.put_nowait({"a": 1})
    queue.put_nowait({"b": 1})
    queue.put_nowait(dict(type="Exit"))

    data_sent = []

    def my_func(data):
        data_sent.append(data)

    with patch("ansible_rulebook.websocket.websockets.connect") as mo:
        mock_object = AsyncMock()
        mo.return_value = mock_object
        mo.return_value.__aenter__.return_value = mock_object
        mo.return_value.__anext__.return_value = mock_object
        mo.return_value.__aiter__.side_effect = [mock_object]
        mo.return_value.send.side_effect = my_func
        await send_event_log_to_websocket(queue)
        assert data_sent == ['{"a": 1}', '{"b": 1}']


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "exception_class",
    [
        websockets.exceptions.ConnectionClosedError,
        websockets.exceptions.ConnectionClosedError,
    ],
)
@mock.patch("ansible_rulebook.websocket.websockets.connect")
async def test_send_event_log_to_websocket_with_exception(
    socket_mock: AsyncMock, exception_class
):
    prepare_settings()
    queue = asyncio.Queue()
    queue.put_nowait({"a": 1})
    queue.put_nowait({"b": 2})
    queue.put_nowait(dict(type="Exit"))

    data_sent = []

    mock_object = AsyncMock()
    socket_mock.return_value = mock_object
    socket_mock.return_value.__aenter__.return_value = mock_object
    socket_mock.return_value.__anext__.return_value = mock_object
    socket_mock.return_value.__aiter__.side_effect = [mock_object]

    socket_mock.return_value.send.side_effect = [
        exception_class(rcvd=None, sent=None),
        data_sent.append({"a": 1}),
        data_sent.append({"b": 2}),
    ]

    await send_event_log_to_websocket(queue)
    assert data_sent == [{"a": 1}, {"b": 2}]


@pytest.mark.asyncio
@mock.patch("ansible_rulebook.websocket.websockets.connect")
async def test_send_event_log_to_websocket_with_non_recoverable_exception(
    socket_mock: AsyncMock,
):
    prepare_settings()
    queue = asyncio.Queue()
    queue.put_nowait({"a": 1})
    queue.put_nowait({"b": 2})
    queue.put_nowait(dict(type="Exit"))

    mock_object = AsyncMock()
    socket_mock.return_value = mock_object
    socket_mock.return_value.__aenter__.return_value = mock_object
    socket_mock.return_value.__anext__.return_value = mock_object
    socket_mock.return_value.__aiter__.side_effect = [mock_object]

    rcvd = mock.Mock()
    rcvd.code = 1011
    socket_mock.return_value.send.side_effect = (
        websockets.exceptions.ConnectionClosedError(rcvd=rcvd, sent=None)
    )

    with pytest.raises(websockets.exceptions.ConnectionClosedError):
        await send_event_log_to_websocket(queue)
