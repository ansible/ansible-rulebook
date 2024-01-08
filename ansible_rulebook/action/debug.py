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
import sys
from dataclasses import asdict

import dpath
from drools import ruleset as lang

from ansible_rulebook import terminal

from .control import Control
from .helper import Helper
from .metadata import Metadata

logger = logging.getLogger(__name__)


class Debug:
    """The debug action tries to mimic the ansible debug task with optional
    msg: Prints a message
    var: Prints a variable
    default: print the metadata, control information and facts from the
             rule engine
    At the end we send back the action status
    """

    def __init__(
        self,
        metadata: Metadata,
        control: Control,
        **action_args,
    ):
        self.helper = Helper(metadata, control, "debug")
        self.action_args = action_args
        self.display = terminal.Display()

    async def __call__(self):
        if "msg" in self.action_args:
            messages = self.action_args.get("msg")
            if not isinstance(messages, list):
                messages = [messages]
            for msg in messages:
                self.display.banner("debug", msg)
        elif "var" in self.action_args:
            key = self.action_args.get("var")
            try:
                value = dpath.get(
                    self.helper.control.variables, key, separator="."
                )
                self.display.banner("debug", f"{key}: {value}")
            except KeyError:
                logger.error("Key %s not found in variable pool", key)
                raise
        else:
            args = asdict(self.helper.metadata)
            project_data_file = self.helper.control.project_data_file
            args.update(
                {
                    "inventory": self.helper.control.inventory,
                    "hosts": self.helper.control.hosts,
                    "variables": self.helper.control.variables,
                    "project_data_file": project_data_file,
                }
            )
            self.display.banner("debug: kwargs", args, pretty=True)
            self.display.banner(
                "debug: facts",
                lang.get_facts(self.helper.metadata.rule_set),
                pretty=True,
            )

        sys.stdout.flush()
        await self.helper.send_default_status()
