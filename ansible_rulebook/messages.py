#  Copyright 2022 Red Hat, Inc.
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

from dataclasses import asdict, dataclass

from typing import Optional

from pydantic import BaseModel

DEFAULT_SHUTDOWN_DELAY = 60.0


class Shutdown(BaseModel):
    message: str = "Not specified"
    delay: float = DEFAULT_SHUTDOWN_DELAY
    kind: str = "graceful"
    source_plugin: str = ""


class Action(BaseModel):
    action: str
    action_uuid: str
    activation_id: str
    run_at: str
    ruleset: str
    ruleset_uuid: str
    rule: str
    rule_uuid: str
    matching_events: dict = {}
    status: Optional[str] = ""
    url: Optional[str] = ""
    rule_run_at: Optional[str] = ""
    playbook_name: Optional[str] = ""
    job_template_name: Optional[str] = ""
    organization: Optional[str] = ""
    job_id: Optional[str] = ""
    rc: Optional[int] = -1
    delay: Optional[float] = 0.0
    message: Optional[str] = ""
    kind: Optional[str] = ""
    type: str = "Action"


class Job(BaseModel):
    job_id: str
    ansible_rulebook_id: str
    name: str
    ruleset: str
    ruleset_uuid: str
    rule: str
    rule_uuid: str
    hosts: str
    action: str
    type: str = "Job"


class AnsibleEvent(BaseModel):
    event: dict
    type: str = "AnsibleEvent"


def serialize(model):
    return model.model_dump()
