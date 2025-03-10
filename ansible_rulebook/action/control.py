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

import asyncio
from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Control:
    """Control information when running an action

    Attributes:
    queue: asyncio.Queue
       This is the queue on which we would be sending action status
       periodically when the action is running
    inventory: str
       This is the inventory information from the command line
       It currently is the data that is read from a file, in the future
       it could be a directory or an inventory name from the controller
    hosts: list[str]
       The list of servers passed into ansible-playbook or controller
    variables: dict
       The variables passed in from the command line plus the matching event
       data with event or events key.
    project_data_file: str
       This is the directory where the collection data is sent from the
       AAP server over the websocket is untarred to. The collection could
       contain the playbook that is used in the run_playbook action.
    """

    __slots__ = [
        "queue",
        "inventory",
        "hosts",
        "variables",
        "project_data_file",
    ]
    queue: asyncio.Queue
    inventory: str
    hosts: List[str]
    variables: dict
    project_data_file: str
