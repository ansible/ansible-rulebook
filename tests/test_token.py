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

from unittest.mock import patch

import pytest

from ansible_rulebook import token
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import TokenNotFound


class MockResponse:
    def __init__(self, data):
        self.data = data

    async def json(self):
        return self.data

    async def __aexit__(self, exc_type, exc, tb):
        pass

    async def __aenter__(self):
        return self


def prepare_settings() -> None:
    settings.websocket_token_url = "https://dummy.org/xyz"
    settings.websocket_access_token = "dummy"
    settings.websocket_refresh_token = "dummy"


@pytest.mark.asyncio
async def test_renew_token():
    prepare_settings()
    with patch("ansible_rulebook.token.aiohttp.ClientSession.post") as mock:
        data = {"access": "new_token"}
        mock.return_value = MockResponse(data)
        renewed = await token.renew_token()
        assert renewed == "new_token"


@pytest.mark.asyncio
async def test_renew_invalid_token():
    prepare_settings()
    with patch("ansible_rulebook.token.aiohttp.ClientSession.post") as mock:
        data = {"error": "invalid_token"}
        mock.return_value = MockResponse(data)
        with pytest.raises(TokenNotFound):
            await token.renew_token()
