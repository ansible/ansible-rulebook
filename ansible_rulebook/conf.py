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

import json
import logging
import os
import shutil
import uuid
from typing import Any, Type

from ansible_rulebook.vault import Vault

logger = logging.getLogger(__name__)

DEFAULT_EDA_LABEL = "Activated by Event-Driven Ansible"
DEFAULT_MAX_CONCURRENT_ACTIONS = 25


class _Settings:
    # Simple map: attribute_name -> (env_var_name, type)
    # Only these settings can be updated from environment variables
    ENV_MAP = {
        "gc_after": ("EDA_GC_AFTER", int),
        "default_execution_strategy": ("EDA_EXECUTION_STRATEGY", str),
        "max_feedback_timeout": ("EDA_MAX_FEEDBACK_TIMEOUT", int),
        "print_events": ("EDA_PRINT_EVENTS", bool),
        "websocket_url": ("EDA_WEBSOCKET_URL", str),
        "websocket_ssl_verify": ("EDA_WEBSOCKET_SSL_VERIFY", str),
        "websocket_token_url": ("EDA_WEBSOCKET_TOKEN_URL", str),
        "websocket_access_token": ("EDA_WEBSOCKET_ACCESS_TOKEN", str),
        "websocket_refresh_token": ("EDA_WEBSOCKET_REFRESH_TOKEN", str),
        "skip_audit_events": ("EDA_SKIP_AUDIT_EVENTS", bool),
        "persistence_enabled": ("EDA_PERSISTENCE_ENABLED", bool),
        "persistence_id": ("EDA_PERSISTENCE_ID", str),
        "max_concurrent_actions": ("EDA_MAX_CONCURRENT_ACTIONS", int),
        "max_actions_timeout": ("EDA_MAX_ACTIONS_TIMEOUT", int),
        "max_back_pressure_timeout": ("EDA_MAX_BACK_PRESSURE_TIMEOUT", int),
        "max_reporting_queue_size": ("EDA_MAX_REPORTING_QUEUE_SIZE", int),
        "max_batch_job_polling_size": (
            "EDA_MAX_BATCH_JOB_POLLING_SIZE",
            int,
        ),
        "eda_labels": ("EDA_LABELS", list),
    }

    # Settings that must be positive integers (>= 1)
    # Note: max_concurrent_actions is NOT in this set because 0 is a valid
    # sentinel value meaning "use default of 25"
    POSITIVE_INT_SETTINGS = frozenset(
        {
            "max_actions_timeout",
            "max_back_pressure_timeout",
            "max_reporting_queue_size",
            "max_batch_job_polling_size",
            "gc_after",
            "max_feedback_timeout",
        }
    )

    def __init__(self):
        # Set defaults first
        self.identifier = str(uuid.uuid4())
        self.gc_after = 1000
        self.default_execution_strategy = "sequential"
        self.max_feedback_timeout = 5
        self.print_events = False
        self.websocket_url = None
        self.websocket_ssl_verify = "yes"
        self.websocket_token_url = None
        self.websocket_access_token = None
        self.websocket_refresh_token = None
        self.skip_audit_events = False
        self.vault = Vault()
        self.ansible_galaxy_path = shutil.which("ansible-galaxy")
        self.eda_labels = [DEFAULT_EDA_LABEL]
        self.persistence_enabled = False
        self.persistence_id = None
        self.controller_retry_max_timeout = 60.0
        self.controller_retry_attempts = 5
        # max_concurrent_actions: 0 is a sentinel for "use default of 25"
        # This allows setup_semaphores() to apply the default
        # if not explicitly set
        self.max_concurrent_actions = 0
        self.max_actions_semaphore = None
        self.max_actions_timeout = 3600
        self.max_back_pressure_timeout = 3600
        self.max_reporting_queue_size = 50
        self.max_batch_job_polling_size = 25

        self.update_from_env()

    def update_from_env(self):
        """Update settings from environment variables (only if env var exists)

        This is called:
        1. On initialization to read initial env vars
        2. After websocket handler sets new env vars
        """
        for attr_name, (env_key, type_class) in self.ENV_MAP.items():
            env_value = os.environ.get(env_key)
            if env_value is not None:
                try:
                    converted_value = self._convert_type(env_value, type_class)
                    if (
                        attr_name in self.POSITIVE_INT_SETTINGS
                        and converted_value < 1
                    ):
                        logger.warning(
                            "Env var %s=%s must be >= 1, using default %s",
                            env_key,
                            env_value,
                            getattr(self, attr_name),
                        )
                        continue
                    # Special validation for max_concurrent_actions:
                    # 0 is valid (sentinel for "use default"),
                    # but negative is not
                    if (
                        attr_name == "max_concurrent_actions"
                        and converted_value < 0
                    ):
                        logger.warning(
                            "Env var %s=%s must be >= 0, using default %s",
                            env_key,
                            env_value,
                            getattr(self, attr_name),
                        )
                        continue
                    setattr(self, attr_name, converted_value)
                except (ValueError, TypeError) as e:
                    logger.warning(
                        f"Failed to convert env var {env_key}={env_value!r} "
                        f"to type {type_class.__name__}: {e}"
                    )

    @staticmethod
    def _convert_to_list(value: Any) -> list:
        if isinstance(value, list):
            return value
        if not isinstance(value, str):
            return [value]
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        return parsed if isinstance(parsed, list) else [parsed]

    @staticmethod
    def _convert_type(value: Any, target_type: Type) -> Any:
        if isinstance(value, target_type):
            return value

        if target_type == bool:
            if isinstance(value, str):
                return value.lower() in ("true", "1", "yes", "on")
            return bool(value)
        elif target_type == list:
            return _Settings._convert_to_list(value)
        elif target_type == int:
            return int(value)
        elif target_type == str:
            return str(value)

        return value


settings = _Settings()
