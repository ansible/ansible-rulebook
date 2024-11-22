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


class RetractFact:
    """The retract_fact action removes a fact information from the Drools
    rule engine, which can then trigger the rules based on removed
    facts.
    The action_args includes the following parameters
    ruleset: str
         The name of the ruleset to retract the fact from
    fact: dict
         The fact to retract from Drools
    partial: true|false, default is true
         if the fact has partial information or it has complete
         information.
    """

    def __init__(
        self,
        metadata: Metadata,
        control: Control,
        **action_args,
    ):
        self.helper = Helper(metadata, control, "retract_fact")
        self.action_args = action_args

    async def __call__(self):
        partial = self.action_args.get("partial", True)
        if not partial:
            exclude_keys = ["meta"]
        else:
            exclude_keys = []

        lang.retract_matching_facts(
            self.action_args["ruleset"],
            self.action_args["fact"],
            partial,
            exclude_keys,
        )
        await self.helper.send_default_status()
