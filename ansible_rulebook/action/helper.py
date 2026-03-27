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
import uuid
from typing import Dict, Optional

from ansible_rulebook.conf import settings
from ansible_rulebook.event_filter.insert_meta_info import main as insert_meta
from ansible_rulebook.job_template_runner import job_template_runner
from ansible_rulebook.persistence import update_action_info
from ansible_rulebook.util import run_at

from .control import Control
from .metadata import Metadata

logger = logging.getLogger(__name__)

KEY_EDA_VARS = "ansible_eda"
INTERNAL_ACTION_STATUS = "successful"
FAILED_STATUS = "failed"
SUCCESSFUL_STATUS = "successful"
STARTED_STATUS = "started"


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

    def collect_extra_vars(
        self, user_extra_vars: Dict, include_events: bool = True
    ) -> Dict:
        """When we send information to ansible-playbook or job template
        on AWX, we need the rule and optionally event specific information to
        be sent to this external process

        the caller passes in the user_extra_vars from the action args
        and then we append eda specific vars and return that as a
        the updated dictionary that is sent to the external process

        if the caller doesn't want to include events data return the
        user_extra_vars.
        """
        if not include_events:
            return user_extra_vars

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

    def update_action_state(self, info: dict) -> None:
        """Update action state in the persistence store.

        This method persists action execution state to the database when
        persistence is enabled, allowing actions to be tracked and recovered
        across rulebook restarts or failover scenarios.

        Args:
            info: Dictionary containing action state information to persist

        Returns:
            None
        """
        if self.metadata.persistent_info:
            update_action_info(
                self.metadata.rule_set,
                self.metadata.persistent_info.matching_uuid,
                self.metadata.persistent_info.action_index,
                info,
            )

    def get_event_uuid_label(self) -> str:
        """Extract event UUID and format it as a label.

        This method retrieves the UUID from the matching event(s) and
        formats it as a label string that can be used to tag jobs in the
        controller. This enables correlation between jobs and the events
        that triggered them.

        Returns:
            str: Formatted label string in the format "eda-event-uuid-{uuid}"

        Raises:
            ValueError: If the event structure is invalid (no 'm' or 'm_0' key)
        """
        events = self.get_events()
        if "m" in events:
            try:
                event_uuid = events["m"]["meta"]["uuid"]
            except KeyError:
                raise ValueError(
                    "Event missing meta.uuid in single event match"
                )
        elif "m_0" in events:
            try:
                event_uuid = events["m_0"]["meta"]["uuid"]
            except KeyError:
                raise ValueError(
                    "Event missing meta.uuid in multi event match"
                )
        else:
            raise ValueError("Invalid event type")

        return f"eda-event-uuid-{event_uuid}"

    async def get_old_job_url(
        self,
        name: str,
        organization: str,
        obj_type: str,
        add_event_uuid_label: bool,
    ) -> Optional[str]:
        """Retrieve job URL from a previous execution for resumption.

        In persistence/HA mode, this method attempts to retrieve the URL of
        a job that was launched in a previous execution but may not have
        completed due to a process restart or failover. This enables the
        action to resume monitoring the existing job rather than launching
        a duplicate.

        Args:
            name: Name of the job or workflow template
            organization: Organization name containing the template
            obj_type: Type of template ("job_template" or
                "workflow_template")
            add_event_uuid_label: If True, attempt to find job by event
                UUID label when job_url is not directly available

        Returns:
            Optional[str]: The job URL if found from a previous run,
                None otherwise
        """
        if not self.metadata.persistent_info:
            return None

        a_priori = self.metadata.persistent_info.a_priori
        if not a_priori:
            return None
        if a_priori.get("job_url"):
            job_url = a_priori["job_url"]
            logger.debug("Will monitor job %s from earlier run", job_url)
            return job_url
        if a_priori.get("status") == STARTED_STATUS and add_event_uuid_label:
            logger.debug("Fetching job url using event label from earlier run")
            job_url = await job_template_runner.get_job_url_from_label(
                name,
                organization,
                obj_type,
                self.get_event_uuid_label(),
            )
            logger.debug("Will monitor job %s from earlier run", job_url)
            return job_url

        return None
