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

import json
import logging
import uuid

import xxhash
from psycopg import AsyncClientCursor, AsyncConnection, OperationalError

from .control import Control
from .helper import FAILED_STATUS, Helper
from .metadata import Metadata

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 7 * 1024
MESSAGE_CHUNKED_UUID = "_message_chunked_uuid"
MESSAGE_CHUNK_COUNT = "_message_chunk_count"
MESSAGE_CHUNK_SEQUENCE = "_message_chunk_sequence"
MESSAGE_CHUNK = "_chunk"
MESSAGE_LENGTH = "_message_length"
MESSAGE_XX_HASH = "_message_xx_hash"


class PGNotify:
    """The PGNotify action sends an event to a PG Pub Sub Channel
    Needs
    dsn https://www.postgresql.org/docs/current/libpq-connect.html
    #LIBPQ-CONNSTRING-KEYWORD-VALUE
    channel the channel name to send the notifies
    event
    """

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        self.helper = Helper(metadata, control, "pg_notify")
        self.action_args = action_args

    async def __call__(self):
        if not self.action_args["event"]:
            return

        try:
            async with await AsyncConnection.connect(
                conninfo=self.action_args["dsn"],
                autocommit=True,
            ) as conn:
                async with AsyncClientCursor(connection=conn) as cursor:
                    if self.action_args.get("remove_meta", False):
                        event = self.action_args["event"].copy()
                        if "meta" in event:
                            event.pop("meta")
                    else:
                        event = self.action_args["event"]

                    payload = json.dumps(event)
                    message_length = len(payload)
                    if message_length >= MAX_MESSAGE_LENGTH:
                        for chunk in self._to_chunks(payload, message_length):
                            await cursor.execute(
                                f"NOTIFY {self.action_args['channel']}, "
                                f"'{json.dumps(chunk)}';"
                            )
                    else:
                        await cursor.execute(
                            f"NOTIFY {self.action_args['channel']}, "
                            f"'{payload}';"
                        )
        except OperationalError as e:
            logger.error("PG Notify operational error %s", str(e))
            data = dict(status=FAILED_STATUS, message=str(e))
            await self.helper.send_status(data)
            raise e

        await self.helper.send_default_status()

    def _to_chunks(self, payload: str, message_length: int):
        xx_hash = xxhash.xxh32(payload.encode("utf-8")).hexdigest()
        logger.debug(
            "Message length exceeds %d bytes, will chunk", MAX_MESSAGE_LENGTH
        )
        message_uuid = str(uuid.uuid4())
        number_of_chunks = int(message_length / MAX_MESSAGE_LENGTH) + 1
        chunked = {
            MESSAGE_CHUNKED_UUID: message_uuid,
            MESSAGE_CHUNK_COUNT: number_of_chunks,
            MESSAGE_LENGTH: message_length,
            MESSAGE_XX_HASH: xx_hash,
        }
        logger.debug("Chunk info %s", message_uuid)
        logger.debug("Number of chunks %d", number_of_chunks)
        logger.debug("Total data size %d", message_length)
        logger.debug("XX Hash %s", xx_hash)

        sequence = 1
        for i in range(0, message_length, MAX_MESSAGE_LENGTH):
            chunked[MESSAGE_CHUNK] = payload[i : i + MAX_MESSAGE_LENGTH]
            chunked[MESSAGE_CHUNK_SEQUENCE] = sequence
            sequence += 1
            yield chunked
