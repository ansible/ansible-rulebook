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

import uuid
from typing import Dict

from ansible_rulebook.conf import settings
from ansible_rulebook.event_filter.insert_meta_info import main as insert_meta
from ansible_rulebook.util import run_at

from .control import Control
from .metadata import Metadata

KEY_EDA_VARS = "ansible_eda"
INTERNAL_ACTION_STATUS = "successful"


class Helper:
    """
    Helper class stores the metadata, the control attributes and has
    methods to send data to the Queue.

    Attributes
    ----------
      metadata : Metadata
         a data class that stores rule specific data
      control : Control
         a control dataclass that stores the runtime information about
         the queue on which we send the status for the action, the inventory
         information, the hosts data and the variables that we would like
         to pass into the action
      uuid : str
         each action has a uuid that is generated to track it
      action : str
         the name of the action, set by the sub classe

    Methods
    -------
       send_status(data={}, obj_type:"action")
          Sends the action status information on the queue
       send_default_status()
          Sends the default action status, used mostly with internal
          actions like debug, print_event, set_fact, retract_fact,
          noop, post_event
       get_events()
          Fetches the matching events from the variables
       collect_extra_vars()
          Create extra_vars to be sent to playbook and job template which
          includes rule and matching events.
       embellish_internal_event()
          Add internal sources for facts and events posted from inside of
          a rulebook
    """

    def __init__(self, metadata: Metadata, control: Control, action: str):
        self.metadata = metadata
        self.control = control
        self.uuid = str(uuid.uuid4())
        self.action = action

    async def send_status(self, data: Dict, obj_type: str = "Action") -> None:
        """Send Action status information on the queue"""
        if settings.skip_audit_events:
            return
        payload = {
            "type": obj_type,
            "action": self.action,
            "action_uuid": self.uuid,
            "ruleset": self.metadata.rule_set,
            "ruleset_uuid": self.metadata.rule_set_uuid,
            "rule": self.metadata.rule,
            "rule_uuid": self.metadata.rule_uuid,
            "rule_run_at": self.metadata.rule_run_at,
            "activation_id": settings.identifier,
            "activation_instance_id": settings.identifier,
        }
        payload.update(data)
        await self.control.queue.put(payload)

    async def send_default_status(self):
        """Send default action status information on the queue"""
        if settings.skip_audit_events:
            return
        await self.send_status(
            {
                "run_at": run_at(),
                "status": INTERNAL_ACTION_STATUS,
                "matching_events": self.get_events(),
            }
        )

    def get_events(self) -> Dict:
        """From the control variables, detect if its a single event
        match or a multi event match and return a dictionary with
        the event data with
        m key for single event stored in the event key
        m_0,m_1,.... for multiple matching events stored in
        the events key
        """
        if "event" in self.control.variables:
            return {"m": self.control.variables["event"]}
        if "events" in self.control.variables:
            return self.control.variables["events"]
        return {}

    def embellish_internal_event(self, event: Dict) -> Dict:
        """Insert metadata for every internally generated event"""
        return insert_meta(
            event, **{"source_name": self.action, "source_type": "internal"}
        )

    def set_action(self, action) -> None:
        self.action = action

    def collect_extra_vars(self, user_extra_vars: Dict) -> Dict:
        """When we send information to ansible-playbook or job template
        on AWX, we need the rule and event specific information to
        be sent to this external process

        the caller passes in the user_extra_vars from the action args
        and then we append eda specific vars and return that as a
        the updated dictionary that is sent to the external process
        """
        extra_vars = user_extra_vars.copy() if user_extra_vars else {}

        eda_vars = {
            "ruleset": self.metadata.rule_set,
            "rule": self.metadata.rule,
        }
        if "events" in self.control.variables:
            eda_vars["events"] = self.control.variables["events"]
        if "event" in self.control.variables:
            eda_vars["event"] = self.control.variables["event"]

        extra_vars[KEY_EDA_VARS] = eda_vars
        return extra_vars
