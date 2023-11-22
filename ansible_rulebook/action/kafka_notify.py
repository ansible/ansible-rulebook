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

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError

from .control import Control
from .helper import Helper
from .metadata import Metadata

logger = logging.getLogger(__name__)
# TODO: Use FAILED_STATUS and FAILED_STATUS from helper
SUCCESSFUL_STATUS = "successful"
FAILED_STATUS = "failed"


class KafkaNotify:
    """The Kafka notify action used to send messages to a Kafka topic
    The required arguments are:
    connection: The connection object with the Kafka properties
    topic: The name of the topic
    event: The matching event

    At the end we send back the action status
    """

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        self.helper = Helper(metadata, control, "kafka_notify")
        self.action_args = action_args

    async def __call__(self):
        producer = None
        try:
            producer = AIOKafkaProducer(**self.action_args["connection"])
            await producer.start()
            await producer.send_and_wait(
                self.action_args["topic"],
                json.dumps(self.action_args["event"]).encode("utf-8"),
            )
        except (ValueError, KafkaError) as e:
            logger.error("Kafka Producer error %s", str(e))
            data = {"status": FAILED_STATUS, "message": str(e)}
            await self.helper.send_status(data)
            raise e
        finally:
            if producer:
                await producer.stop()

        await self.helper.send_default_status()
