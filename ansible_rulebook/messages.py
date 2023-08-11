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

DEFAULT_SHUTDOWN_DELAY = 60.0


@dataclass(frozen=True)
class Shutdown:
    message: str = "Not specified"
    delay: float = DEFAULT_SHUTDOWN_DELAY
    kind: str = "graceful"
    source_plugin: str = ""


@dataclass(frozen=True)
class Action:
    action: str
    action_uuid: str
    ruleset: str
    ruleset_uuid: str
    rule: str
    rule_uuid: str
    activation_id: str
    run_at: str
    status: str
    matching_events: list
    rule_run_at: str
    playbook_name: str = None
    job_id: str = None
    rc: int = None
    delay: int = None
    message: str = None
    kind: str = None
    job_template_name: str = None
    organization: str = None
    url: str = None
    type: str = "Action"


@dataclass(frozen=True)
class Job:
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

serialize = asdict
