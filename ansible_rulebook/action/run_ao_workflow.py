#  Copyright 2026 Red Hat, Inc.
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

from drools import ruleset as lang

from ansible_rulebook import terminal
from ansible_rulebook.ao_workflow_runner import (
    AOExecutionFailedException,
    AOWorkflowNotFoundException,
    AOWorkflowRunnerException,
    ao_workflow_runner,
)
from ansible_rulebook.conf import settings
from ansible_rulebook.util import run_at

from .control import Control
from .helper import Helper
from .metadata import Metadata

logger = logging.getLogger(__name__)


class RunAOWorkflow:
    """run_ao_workflow action triggers an Automation Orchestrator workflow
    via webhook and optionally waits for completion.

    Parameters:
        webhook_path (str): Direct webhook path (e.g., "ops/disk-cleanup")
        workflow_name (str): Workflow name for lookup (alternative to webhook_path)
        project (str): Project name for workflow lookup (optional)
        payload (dict): Data to send as webhook payload (optional)
        timeout (int): Max wait time in seconds (default: 600)
        poll_interval (int): Seconds between status checks (default: 5)
        post_facts (bool): Post execution results as facts (default: True)
        post_events (bool): Post execution results as events (default: False)
        treat_errors_as_failure (bool): Treat completed_with_errors as failure
            (default: True)
        ruleset (str): Ruleset name for posting facts/events (optional)
        ao_host (str): AO base URL (optional, can use env EDA_AO_URL)
        ao_client_id (str): OAuth2 client ID (optional, can use env EDA_AO_CLIENT_ID)
        ao_client_secret (str): OAuth2 client secret (optional, can use env EDA_AO_CLIENT_SECRET)
        ao_verify_ssl (str): SSL verification (optional, can use env EDA_AO_SSL_VERIFY)
    """

    def __init__(
        self,
        metadata: Metadata,
        control: Control,
        **action_args,
    ):
        self.helper = Helper(metadata, control, "run_ao_workflow")
        self.action_args = action_args
        self.execution_id = None
        self.execution_result = {}
        self.display = terminal.Display()

    async def __call__(self):
        """Execute the action."""
        # Configure AO credentials if provided in action args
        # This allows passing credentials directly from AAP credential extra_vars
        ao_host = self.action_args.get("ao_host")
        ao_client_id = self.action_args.get("ao_client_id")
        ao_client_secret = self.action_args.get("ao_client_secret")
        ao_verify_ssl = self.action_args.get("ao_verify_ssl")

        if ao_host:
            ao_workflow_runner.host = ao_host
            logger.debug("Using AO host from action args: %s", ao_host)

        if ao_client_id:
            ao_workflow_runner.client_id = ao_client_id
            logger.debug("Using AO client_id from action args")

        if ao_client_secret:
            ao_workflow_runner.client_secret = ao_client_secret
            logger.debug("Using AO client_secret from action args")

        if ao_verify_ssl:
            ao_workflow_runner.verify_ssl = ao_verify_ssl
            logger.debug(
                "Using AO verify_ssl from action args: %s", ao_verify_ssl
            )

        # Validate parameters
        webhook_path = self.action_args.get("webhook_path")
        workflow_name = self.action_args.get("workflow_name")

        if not webhook_path and not workflow_name:
            raise ValueError(
                "Either 'webhook_path' or 'workflow_name' must be provided"
            )

        # Get configuration parameters
        project = self.action_args.get("project")
        payload = self.action_args.get("payload", {})
        timeout = self.action_args.get("timeout", 600)
        poll_interval = self.action_args.get("poll_interval", 5)
        treat_errors_as_failure = self.action_args.get(
            "treat_errors_as_failure", True
        )

        logger.info(
            "Running AO workflow: webhook_path=%s, workflow_name=%s, project=%s",
            webhook_path,
            workflow_name,
            project,
        )
        logger.debug(
            "ruleset: %s, rule %s",
            self.helper.metadata.rule_set,
            self.helper.metadata.rule,
        )

        # Substitute variables in payload
        if payload:
            payload = self.helper.collect_extra_vars(
                payload, include_events=True
            )

        await self._run(
            webhook_path,
            workflow_name,
            project,
            payload,
            timeout,
            poll_interval,
            treat_errors_as_failure,
        )

    async def _run(
        self,
        webhook_path: str,
        workflow_name: str,
        project: str,
        payload: dict,
        timeout: int,
        poll_interval: int,
        treat_errors_as_failure: bool,
    ):
        """Execute workflow and handle results."""
        try:
            # Resolve webhook path if not provided directly
            if not webhook_path:
                logger.info(
                    "Looking up webhook path for workflow '%s'%s",
                    workflow_name,
                    f" in project '{project}'" if project else "",
                )
                webhook_path = await ao_workflow_runner.lookup_webhook_path(
                    workflow_name, project
                )
                logger.info("Resolved webhook path: %s", webhook_path)

            # Trigger workflow
            self.execution_id = await ao_workflow_runner.trigger_workflow(
                webhook_path, payload
            )

            # Wait for completion
            execution = await ao_workflow_runner.wait_for_execution(
                self.execution_id, timeout, poll_interval
            )

            # Check if successful
            is_successful = ao_workflow_runner.is_execution_successful(
                execution, treat_errors_as_failure
            )

            self.execution_result = {
                "execution_id": execution.get("id", self.execution_id),
                "workflow_name": execution.get("workflow_name", workflow_name),
                "status": execution.get("status"),
                "created_at": execution.get("created_at"),
                "completed_at": execution.get("completed_at"),
                "webhook_path": webhook_path,
            }

            # Add error details if present
            if execution.get("error_details"):
                self.execution_result["error_details"] = execution[
                    "error_details"
                ]

            # Calculate duration if timestamps available
            if execution.get("created_at") and execution.get("completed_at"):
                try:
                    from datetime import datetime

                    created = datetime.fromisoformat(
                        execution["created_at"].replace("Z", "+00:00")
                    )
                    completed = datetime.fromisoformat(
                        execution["completed_at"].replace("Z", "+00:00")
                    )
                    duration = (completed - created).total_seconds()
                    self.execution_result["duration_seconds"] = duration
                except (ValueError, AttributeError) as e:
                    logger.debug("Could not calculate duration: %s", e)

            if not is_successful:
                error_msg = (
                    f"AO workflow execution {self.execution_id} failed "
                    f"with status: {execution.get('status')}"
                )
                if execution.get("error_details"):
                    error_msg += f", details: {execution['error_details']}"
                # Set error in execution_result before raising
                self.execution_result["error"] = error_msg
                raise AOExecutionFailedException(error_msg)

            logger.info(
                "AO workflow execution completed successfully: %s",
                self.execution_id,
            )

        except AOExecutionFailedException as ex:
            # Execution was triggered but failed - keep execution status
            logger.error("AO workflow execution error: %s", ex)
            # execution_result should already be set with the actual status
        except (
            AOWorkflowRunnerException,
            AOWorkflowNotFoundException,
        ) as ex:
            # Workflow trigger/lookup failed - set generic failed status
            logger.error("AO workflow execution error: %s", ex)
            self.execution_result = {
                "execution_id": self.execution_id,
                "status": "failed",
                "error": str(ex),
                "created_at": run_at(),
            }
            if webhook_path:
                self.execution_result["webhook_path"] = webhook_path
            if workflow_name:
                self.execution_result["workflow_name"] = workflow_name

        await self._post_process()

    async def _post_process(self) -> None:
        """Post-process execution results and send status."""
        # Send audit log
        a_log = {
            "execution_id": self.execution_result.get("execution_id"),
            "workflow_name": self.execution_result.get("workflow_name"),
            "webhook_path": self.execution_result.get("webhook_path"),
            "status": self.execution_result.get("status"),
            "run_at": self.execution_result.get("created_at", run_at()),
            "matching_events": self.helper.get_events(),
        }

        if "error" in self.execution_result:
            error_msg = self.execution_result["error"]
            a_log["message"] = error_msg
            a_log["reason"] = {"error": error_msg}
            a_log["error"] = error_msg
        else:
            logger.info(
                "AO execution ID: %s, status: %s",
                self.execution_result.get("execution_id"),
                self.execution_result.get("status"),
            )

        await self.helper.send_status(a_log)

        # Post facts or events if configured
        post_facts = self.action_args.get("post_facts", True)
        post_events = self.action_args.get("post_events", False)

        if (
            post_facts or post_events
        ) and "error" not in self.execution_result:
            level = logging.DEBUG
            if settings.print_events:
                level = self.display.level

            self.display.banner("ao_workflow: post-results", level=level)

            ruleset = self.action_args.get(
                "ruleset", self.helper.metadata.rule_set
            )

            # Prepare result data
            result_data = {
                "ao_execution_id": self.execution_result.get("execution_id"),
                "ao_workflow_name": self.execution_result.get("workflow_name"),
                "ao_status": self.execution_result.get("status"),
                "ao_webhook_path": self.execution_result.get("webhook_path"),
            }

            # Add optional fields if present
            if "created_at" in self.execution_result:
                result_data["ao_created_at"] = self.execution_result[
                    "created_at"
                ]
            if "completed_at" in self.execution_result:
                result_data["ao_completed_at"] = self.execution_result[
                    "completed_at"
                ]
            if "duration_seconds" in self.execution_result:
                result_data["ao_duration_seconds"] = self.execution_result[
                    "duration_seconds"
                ]
            if "error_details" in self.execution_result:
                result_data["ao_error_details"] = self.execution_result[
                    "error_details"
                ]

            result_data = self.helper.embellish_internal_event(result_data)
            self.display.output(result_data, level=level, pretty=True)

            if post_facts:
                lang.assert_fact(ruleset, result_data)
                logger.debug("Posted AO execution results as facts")

            if post_events:
                lang.post(ruleset, result_data)
                logger.debug("Posted AO execution results as events")

            self.display.banner(level=level)
