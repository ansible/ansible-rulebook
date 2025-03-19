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

import logging

import aiohttp

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import TokenNotFound
from ansible_rulebook.util import create_context

logger = logging.getLogger(__name__)


async def renew_token() -> str:
    logger.info("Renew websocket token from %s", settings.websocket_token_url)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            settings.websocket_token_url,
            data={"refresh": settings.websocket_refresh_token},
            ssl_context=_sslcontext(),
        ) as resp:
            try:
                data = await resp.json()
            except aiohttp.client_exceptions.ContentTypeError as e:
                logger.error(f"failed to renew token. Error: {e}")
                msg = "Refresh token URL does not return expected format"
                raise TokenNotFound(msg) from e
            if "access" not in data:
                logger.error(f"Failed to renew token. Error: {str(data)}")
                raise TokenNotFound("Response does not contain access token")
            return data["access"]


def _sslcontext():
    return create_context(settings.websocket_token_url, "https")
