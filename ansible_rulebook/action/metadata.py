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

from dataclasses import dataclass


@dataclass(frozen=True)
class Metadata:
    """Metadata class stores the rule specific information
    which is used when reporting stats for the action

    Attributes
    ----------
    rule: str
        Rule name
    rule_uuid: str
        Rule uuid
    rule_set: str
        Rule set name
    rule_set_uuid: str
        Rule set uuid
    rule_run_at: str
        ISO 8601 date/time when the rule was triggered
    """

    __slots__ = [
        "rule",
        "rule_uuid",
        "rule_set",
        "rule_set_uuid",
        "rule_run_at",
    ]
    rule: str
    rule_uuid: str
    rule_set: str
    rule_set_uuid: str
    rule_run_at: str
