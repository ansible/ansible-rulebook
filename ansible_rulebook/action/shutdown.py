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

from ansible_rulebook.exception import ShutdownException
from ansible_rulebook.messages import Shutdown as ShutdownMessage
from ansible_rulebook.util import run_at

from .control import Control
from .helper import INTERNAL_ACTION_STATUS, Helper
from .metadata import Metadata


class Shutdown:
    """shutdown action initiates a shutdown from inside of a rulebook"""

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        self.helper = Helper(metadata, control, "shutdown")
        self.action_args = action_args

    async def __call__(self):
        delay = self.action_args.get("delay", 60.0)
        message = self.action_args.get("message", "Default shutdown message")
        kind = self.action_args.get("kind", "graceful")

        await self.helper.send_status(
            {
                "run_at": run_at(),
                "status": INTERNAL_ACTION_STATUS,
                "matching_events": self.helper.get_events(),
                "delay": delay,
                "message": message,
                "kind": kind,
            }
        )
        print(
            "Ruleset: %s rule: %s has initiated shutdown of type: %s. "
            "Delay: %.3f seconds, Message: %s"
            % (
                self.helper.metadata.rule_set,
                self.helper.metadata.rule,
                kind,
                delay,
                message,
            )
        )
        raise ShutdownException(
            ShutdownMessage(message=message, delay=delay, kind=kind)
        )
