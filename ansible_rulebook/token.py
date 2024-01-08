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
import ssl
import typing as tp

import aiohttp

from ansible_rulebook.conf import settings
from ansible_rulebook.exception import TokenNotFound

logger = logging.getLogger(__name__)


async def renew_token() -> str:
    logger.info("Renew websocket token from %s", settings.websocket_token_url)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            settings.websocket_token_url,
            data={"refresh": settings.websocket_refresh_token},
            ssl_context=_sslcontext(),
        ) as resp:
            data = await resp.json()
            if "access" not in data:
                logger.error(f"Failed to renew token. Error: {str(data)}")
                raise TokenNotFound("Response does not contain access token")
            return data["access"]


def _sslcontext() -> tp.Optional[ssl.SSLContext]:
    if settings.websocket_token_url.startswith("https"):
        ssl_verify = settings.websocket_ssl_verify.lower()
        if ssl_verify in ["yes", "true"]:
            return ssl.create_default_context()
        if ssl_verify in ["no", "false"]:
            return ssl._create_unverified_context()
        return ssl.create_default_context(cafile=ssl_verify)
    return None
