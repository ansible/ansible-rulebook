#  Copyright 2025 Red Hat, Inc.
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

import shutil

# Constants for collection
ANSIBLE_GALAXY = shutil.which("ansible-galaxy")
EDA_PATH_PREFIX = "extensions/eda"

EDA_FILTER_PATHS = [
    f"{EDA_PATH_PREFIX}/plugins/event_filter",
    f"{EDA_PATH_PREFIX}/plugins/event_filters",
    "plugins/event_filter",
]

EDA_SOURCE_PATHS = [
    f"{EDA_PATH_PREFIX}/plugins/event_source",
    f"{EDA_PATH_PREFIX}/plugins/event_sources",
    "plugins/event_source",
]

EDA_PLAYBOOKS_PATHS = [".", "playbooks"]

EDA_YAML_EXTENSIONS = [".yml", ".yaml"]

# Constants for condition parser
VALID_SELECT_ATTR_OPERATORS = [
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "regex",
    "search",
    "match",
    "in",
    "not in",
    "contains",
    "not contains",
]

VALID_SELECT_OPERATORS = [
    "==",
    "!=",
    ">",
    ">=",
    "<",
    "<=",
    "regex",
    "search",
    "match",
]
SUPPORTED_SEARCH_KINDS = ("match", "regex", "search")

# Constants for json generator
OPERATOR_MNEMONIC = {
    "!=": "NotEqualsExpression",
    "==": "EqualsExpression",
    "and": "AndExpression",
    "or": "OrExpression",
    ">": "GreaterThanExpression",
    "<": "LessThanExpression",
    ">=": "GreaterThanOrEqualToExpression",
    "<=": "LessThanOrEqualToExpression",
    "+": "AdditionExpression",
    "-": "SubtractionExpression",
    "<<": "AssignmentExpression",
    "in": "ItemInListExpression",
    "not in": "ItemNotInListExpression",
    "contains": "ListContainsItemExpression",
    "not contains": "ListNotContainsItemExpression",
}

# Constant for messages
DEFAULT_SHUTDOWN_DELAY = 60.0

# Constant for util
EDA_BUILTIN_FILTER_PREFIX = "eda.builtin."

# Constant for validators
DEFAULT_RULEBOOK_SCHEMA = "ruleset_schema"

# Constant for vault
VAULT_HEADER = "$ANSIBLE_VAULT"
b_VAULT_HEADER = b"$ANSIBLE_VAULT"

# Constant for websocket
BACKOFF_MIN = 1.92
BACKOFF_MAX = 60.0
BACKOFF_FACTOR = 1.618
BACKOFF_INITIAL = 5
