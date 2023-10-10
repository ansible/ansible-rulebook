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

import logging

from drools import ruleset as lang

from .control import Control
from .helper import Helper
from .metadata import Metadata

logger = logging.getLogger(__name__)


class SetFact:
    """The set_fact action sends the fact information into the Drools
    rule engine, which can then trigger the rules based on matching
    facts. To mark that this is an internal fact coming from inside
    the rulebook we embellish the fact with source information to
    indicate that its an internal fact.
    """

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        self.helper = Helper(metadata, control, "set_fact")
        self.action_args = action_args

    async def __call__(self):
        logger.debug(
            "set_fact %s %s",
            self.action_args["ruleset"],
            self.action_args["fact"],
        )
        lang.assert_fact(
            self.action_args["ruleset"],
            self.helper.embellish_internal_event(self.action_args["fact"]),
        )
        await self.helper.send_default_status()
