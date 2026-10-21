#  Copyright 2024 Red Hat, Inc.
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
from unittest.mock import AsyncMock, patch

import pytest

from ansible_rulebook.action.control import Control
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.action.run_ao_workflow import RunAOWorkflow
from ansible_rulebook.ao_workflow_runner import (
    AOExecutionFailedException,
    AOWorkflowNotFoundException,
)


def _validate_action_event(queue, success, reason=None):
    """Helper to validate action event in queue."""
    action = None
    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "Action":
            action = event

    assert action is not None
    assert action["action"] == "run_ao_workflow"

    if reason:
        assert action["reason"] == reason

    required_keys = {
        "action",
        "action_uuid",
        "activation_id",
        "activation_instance_id",
        "rule_run_at",
        "run_at",
        "rule",
        "ruleset",
        "rule_uuid",
        "ruleset_uuid",
        "matching_events",
        "execution_id",
        "status",
        "type",
    }

    if not success:
        required_keys.add("message")
        required_keys.add("reason")

    assert required_keys.issubset(set(action.keys()))
    return action


@pytest.mark.asyncio
async def test_run_ao_workflow_webhook_path():
    """Test run_ao_workflow with direct webhook path."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={"event": {"hostname": "test-host"}},
        project_data_file="",
    )
    action_args = {
        "webhook_path": "ops/test-workflow",
        "payload": {"hostname": "{{ event.hostname }}"},
        "post_facts": False,
    }

    with patch(
        "ansible_rulebook.action.run_ao_workflow.ao_workflow_runner"
    ) as mock_runner:
        mock_runner.trigger_workflow = AsyncMock(return_value="exec-123")
        mock_runner.wait_for_execution = AsyncMock(
            return_value={
                "id": "exec-123",
                "status": "completed",
                "workflow_name": "Test Workflow",
                "created_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:05:00Z",
            }
        )
        mock_runner.is_execution_successful = lambda x, y: True

        action = RunAOWorkflow(metadata, control, **action_args)
        await action()

        # Verify workflow was triggered
        mock_runner.trigger_workflow.assert_called_once()
        call_args = mock_runner.trigger_workflow.call_args
        assert call_args[0][0] == "ops/test-workflow"
        # Payload should have variable substituted
        assert "hostname" in call_args[0][1]

        # Verify execution was monitored
        mock_runner.wait_for_execution.assert_called_once_with(
            "exec-123", 600, 5
        )

    # Validate action event
    action_event = _validate_action_event(queue, success=True)
    assert action_event["execution_id"] == "exec-123"
    assert action_event["status"] == "completed"


@pytest.mark.asyncio
async def test_run_ao_workflow_workflow_name_lookup():
    """Test run_ao_workflow with workflow name lookup."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={},
        project_data_file="",
    )
    action_args = {
        "workflow_name": "Certificate Renewal",
        "project": "IT Operations",
        "post_facts": False,
    }

    with patch(
        "ansible_rulebook.action.run_ao_workflow.ao_workflow_runner"
    ) as mock_runner:
        mock_runner.lookup_webhook_path = AsyncMock(
            return_value="ops/cert-renewal"
        )
        mock_runner.trigger_workflow = AsyncMock(return_value="exec-456")
        mock_runner.wait_for_execution = AsyncMock(
            return_value={
                "id": "exec-456",
                "status": "completed",
                "workflow_name": "Certificate Renewal",
                "created_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:02:00Z",
            }
        )
        mock_runner.is_execution_successful = lambda x, y: True

        action = RunAOWorkflow(metadata, control, **action_args)
        await action()

        # Verify webhook path was looked up
        mock_runner.lookup_webhook_path.assert_called_once_with(
            "Certificate Renewal", "IT Operations"
        )

        # Verify workflow was triggered with resolved path
        mock_runner.trigger_workflow.assert_called_once()
        assert mock_runner.trigger_workflow.call_args[0][0] == "ops/cert-renewal"

    action_event = _validate_action_event(queue, success=True)
    assert action_event["workflow_name"] == "Certificate Renewal"


@pytest.mark.asyncio
async def test_run_ao_workflow_no_path_or_name():
    """Test run_ao_workflow fails without webhook_path or workflow_name."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={},
        project_data_file="",
    )
    action_args = {"post_facts": False}

    action = RunAOWorkflow(metadata, control, **action_args)

    with pytest.raises(ValueError, match="Either 'webhook_path' or 'workflow_name'"):
        await action()


@pytest.mark.asyncio
async def test_run_ao_workflow_execution_failed():
    """Test run_ao_workflow handles execution failure."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={},
        project_data_file="",
    )
    action_args = {
        "webhook_path": "ops/test-workflow",
        "post_facts": False,
    }

    with patch(
        "ansible_rulebook.action.run_ao_workflow.ao_workflow_runner"
    ) as mock_runner:
        mock_runner.trigger_workflow = AsyncMock(return_value="exec-789")
        mock_runner.wait_for_execution = AsyncMock(
            return_value={
                "id": "exec-789",
                "status": "failed",
                "workflow_name": "Test Workflow",
                "created_at": "2024-01-01T00:00:00Z",
                "error_details": {"message": "Execution error"},
            }
        )
        mock_runner.is_execution_successful = lambda x, y: False

        action = RunAOWorkflow(metadata, control, **action_args)
        await action()

    # Should have error in action event
    expected_error = (
        "AO workflow execution exec-789 failed with status: failed, "
        "details: {'message': 'Execution error'}"
    )
    action_event = _validate_action_event(
        queue, success=False, reason={"error": expected_error}
    )
    assert action_event["status"] == "failed"
    assert "error" in action_event


@pytest.mark.asyncio
async def test_run_ao_workflow_not_found():
    """Test run_ao_workflow handles workflow not found error."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={},
        project_data_file="",
    )
    action_args = {
        "workflow_name": "Nonexistent Workflow",
        "post_facts": False,
    }

    with patch(
        "ansible_rulebook.action.run_ao_workflow.ao_workflow_runner"
    ) as mock_runner:
        mock_runner.lookup_webhook_path = AsyncMock(
            side_effect=AOWorkflowNotFoundException(
                "Workflow 'Nonexistent Workflow' not found"
            )
        )

        action = RunAOWorkflow(metadata, control, **action_args)
        await action()

    # Should have error in action event
    action_event = _validate_action_event(queue, success=False)
    assert "error" in action_event
    assert "Nonexistent Workflow" in action_event["error"]


@pytest.mark.asyncio
async def test_run_ao_workflow_with_timeout_and_poll():
    """Test run_ao_workflow with custom timeout and poll interval."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={},
        project_data_file="",
    )
    action_args = {
        "webhook_path": "ops/test-workflow",
        "timeout": 300,
        "poll_interval": 10,
        "post_facts": False,
    }

    with patch(
        "ansible_rulebook.action.run_ao_workflow.ao_workflow_runner"
    ) as mock_runner:
        mock_runner.trigger_workflow = AsyncMock(return_value="exec-999")
        mock_runner.wait_for_execution = AsyncMock(
            return_value={
                "id": "exec-999",
                "status": "completed",
                "workflow_name": "Test Workflow",
                "created_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:03:00Z",
            }
        )
        mock_runner.is_execution_successful = lambda x, y: True

        action = RunAOWorkflow(metadata, control, **action_args)
        await action()

        # Verify custom timeout and poll interval were used
        mock_runner.wait_for_execution.assert_called_once_with(
            "exec-999", 300, 10
        )

    _validate_action_event(queue, success=True)


@pytest.mark.asyncio
async def test_run_ao_workflow_completed_with_errors_as_failure():
    """Test completed_with_errors treated as failure by default."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={},
        project_data_file="",
    )
    action_args = {
        "webhook_path": "ops/test-workflow",
        "treat_errors_as_failure": True,
        "post_facts": False,
    }

    with patch(
        "ansible_rulebook.action.run_ao_workflow.ao_workflow_runner"
    ) as mock_runner:
        mock_runner.trigger_workflow = AsyncMock(return_value="exec-111")
        mock_runner.wait_for_execution = AsyncMock(
            return_value={
                "id": "exec-111",
                "status": "completed_with_errors",
                "workflow_name": "Test Workflow",
                "created_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:01:00Z",
                "error_details": {"warning": "Some steps failed"},
            }
        )
        mock_runner.is_execution_successful = lambda x, y: False

        action = RunAOWorkflow(metadata, control, **action_args)
        await action()

    # Should have error in action event
    action_event = _validate_action_event(queue, success=False)
    assert action_event["status"] == "completed_with_errors"


@pytest.mark.asyncio
async def test_run_ao_workflow_completed_with_errors_as_success():
    """Test completed_with_errors treated as success when configured."""
    queue = asyncio.Queue()
    metadata = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid="u1",
        rule_set_uuid="u2",
        rule_run_at="abc",
    )
    control = Control(
        queue=queue,
        inventory="",
        hosts=["all"],
        variables={},
        project_data_file="",
    )
    action_args = {
        "webhook_path": "ops/test-workflow",
        "treat_errors_as_failure": False,
        "post_facts": False,
    }

    with patch(
        "ansible_rulebook.action.run_ao_workflow.ao_workflow_runner"
    ) as mock_runner:
        mock_runner.trigger_workflow = AsyncMock(return_value="exec-222")
        mock_runner.wait_for_execution = AsyncMock(
            return_value={
                "id": "exec-222",
                "status": "completed_with_errors",
                "workflow_name": "Test Workflow",
                "created_at": "2024-01-01T00:00:00Z",
                "completed_at": "2024-01-01T00:01:00Z",
            }
        )
        mock_runner.is_execution_successful = lambda x, y: True

        action = RunAOWorkflow(metadata, control, **action_args)
        await action()

    # Should succeed
    action_event = _validate_action_event(queue, success=True)
    assert action_event["status"] == "completed_with_errors"
