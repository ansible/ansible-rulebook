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

from dataclasses import dataclass, field
from typing import Dict, List

from ansible_rulebook.rule_types import RuleSet


@dataclass
class StartupArgs:
    rulesets: List[RuleSet] = field(default_factory=list)
    variables: Dict = field(default_factory=dict)
    controller_url: str = field(default="")
    controller_token: str = field(default="")
    controller_ssl_verify: str = field(default="")
    project_data_file: str = field(default="")
    inventory: str = field(default="")
    check_controller_connection: bool = field(default=False)
