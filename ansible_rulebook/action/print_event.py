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

import sys
from pprint import pprint
from typing import Callable

from .control import Control
from .helper import Helper
from .metadata import Metadata


class PrintEvent:
    """The print_event action defined in the rule book
    prints the event information to stdout and
    send the action status
    """

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        self.helper = Helper(metadata, control, "print_event")
        self.action_args = action_args

    async def __call__(self):
        print_fn: Callable = print
        if "pretty" in self.action_args:
            print_fn = pprint

        var_name = (
            "events" if "events" in self.helper.control.variables else "event"
        )

        print_fn(self.helper.control.variables[var_name])
        sys.stdout.flush()
        await self.helper.send_default_status()
