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
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from freezegun import freeze_time

from ansible_rulebook.action.control import Control
from ansible_rulebook.action.helper import (
    FAILED_STATUS,
    INTERNAL_ACTION_STATUS,
    KEY_EDA_VARS,
    STARTED_STATUS,
    Helper,
)
from ansible_rulebook.action.metadata import Metadata
from ansible_rulebook.conf import settings

DUMMY_UUID = "eb7de03f-6f8f-4943-b69e-3c90db346edf"
RULE_UUID = "abcdef3f-6f8f-4943-b69e-3c90db346edf"
RULE_SET_UUID = "00aabbcc-1111-2222-b69e-3c90db346edf"
RULE_RUN_AT = "2023-06-11T12:13:10Z"
ACTION_RUN_AT = "2023-06-11T12:13:14Z"
EVENT_UUID = "event-uuid-123"


@pytest.fixture
def metadata():
    return Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
    )


@pytest_asyncio.fixture
async def control():
    queue = asyncio.Queue()
    return Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": {"a": 1}},
        project_data_file="",
    )


@pytest.mark.asyncio
async def test_helper_init(metadata, control):
    """Test Helper initialization"""
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        helper = Helper(metadata, control, "test_action")
        assert helper.metadata == metadata
        assert helper.control == control
        assert helper.uuid == DUMMY_UUID
        assert helper.action == "test_action"


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
async def test_send_status(metadata, control):
    """Test send_status sends correct payload to queue"""
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        helper = Helper(metadata, control, "test_action")

        data = {
            "status": "successful",
            "run_at": ACTION_RUN_AT,
        }

        await helper.send_status(data, obj_type="Action")

        assert not control.queue.empty()
        payload = await control.queue.get()

        assert payload["type"] == "Action"
        assert payload["action"] == "test_action"
        assert payload["action_uuid"] == DUMMY_UUID
        assert payload["ruleset"] == metadata.rule_set
        assert payload["ruleset_uuid"] == metadata.rule_set_uuid
        assert payload["rule"] == metadata.rule
        assert payload["rule_uuid"] == metadata.rule_uuid
        assert payload["rule_run_at"] == metadata.rule_run_at
        assert payload["activation_id"] == settings.identifier
        assert payload["activation_instance_id"] == settings.identifier
        assert payload["status"] == "successful"
        assert payload["run_at"] == ACTION_RUN_AT


@pytest.mark.asyncio
async def test_send_status_skip_audit_events(metadata, control):
    """Test send_status skips when skip_audit_events is True"""
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        helper = Helper(metadata, control, "test_action")

        original_skip = settings.skip_audit_events
        try:
            settings.skip_audit_events = True

            data = {"status": "successful"}
            await helper.send_status(data)

            assert control.queue.empty()
        finally:
            settings.skip_audit_events = original_skip


@freeze_time("2023-06-11 12:13:14")
@pytest.mark.asyncio
async def test_send_default_status(metadata, control):
    """Test send_default_status sends default payload"""
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        helper = Helper(metadata, control, "test_action")

        await helper.send_default_status()

        assert not control.queue.empty()
        payload = await control.queue.get()

        assert payload["status"] == INTERNAL_ACTION_STATUS
        assert payload["matching_events"] == {"m": {"a": 1}}
        assert "run_at" in payload


@pytest.mark.asyncio
async def test_send_default_status_skip_audit_events(metadata, control):
    """Test send_default_status skips when skip_audit_events is True"""
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        helper = Helper(metadata, control, "test_action")

        original_skip = settings.skip_audit_events
        try:
            settings.skip_audit_events = True

            await helper.send_default_status()

            assert control.queue.empty()
        finally:
            settings.skip_audit_events = original_skip


@pytest.mark.asyncio
async def test_get_events_single_event(metadata, control):
    """Test get_events returns single event with 'm' key"""
    helper = Helper(metadata, control, "test_action")

    events = helper.get_events()

    assert events == {"m": {"a": 1}}


@pytest.mark.asyncio
async def test_get_events_multiple_events(metadata):
    """Test get_events returns multiple events"""
    queue = asyncio.Queue()
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"events": {"m_0": {"a": 1}, "m_1": {"b": 2}}},
        project_data_file="",
    )

    helper = Helper(metadata, control, "test_action")

    events = helper.get_events()

    assert events == {"m_0": {"a": 1}, "m_1": {"b": 2}}


@pytest.mark.asyncio
async def test_get_events_no_events(metadata):
    """Test get_events returns empty dict when no events"""
    queue = asyncio.Queue()
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"other": "data"},
        project_data_file="",
    )

    helper = Helper(metadata, control, "test_action")

    events = helper.get_events()

    assert events == {}


@pytest.mark.asyncio
async def test_embellish_internal_event(metadata, control):
    """Test embellish_internal_event adds metadata"""
    with patch("uuid.uuid4", return_value=DUMMY_UUID):
        helper = Helper(metadata, control, "test_action")

        event = {"data": "test"}

        with patch(
            "ansible_rulebook.action.helper.insert_meta"
        ) as mock_insert:
            mock_insert.return_value = {
                "data": "test",
                "meta": {
                    "source_name": "test_action",
                    "source_type": "internal",
                },
            }

            result = helper.embellish_internal_event(event)

            mock_insert.assert_called_once_with(
                event, source_name="test_action", source_type="internal"
            )
            assert result["meta"]["source_name"] == "test_action"
            assert result["meta"]["source_type"] == "internal"


@pytest.mark.asyncio
async def test_set_action(metadata, control):
    """Test set_action updates action name"""
    helper = Helper(metadata, control, "original_action")
    assert helper.action == "original_action"

    helper.set_action("new_action")
    assert helper.action == "new_action"


@pytest.mark.asyncio
async def test_collect_extra_vars_with_event(metadata, control):
    """Test collect_extra_vars includes event data"""
    helper = Helper(metadata, control, "test_action")

    user_vars = {"user_var": "value"}

    result = helper.collect_extra_vars(user_vars, include_events=True)

    assert result["user_var"] == "value"
    assert KEY_EDA_VARS in result
    assert result[KEY_EDA_VARS]["ruleset"] == metadata.rule_set
    assert result[KEY_EDA_VARS]["rule"] == metadata.rule
    assert result[KEY_EDA_VARS]["event"] == {"a": 1}


@pytest.mark.asyncio
async def test_collect_extra_vars_with_events(metadata):
    """Test collect_extra_vars includes multiple events data"""
    queue = asyncio.Queue()
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"events": {"m_0": {"a": 1}, "m_1": {"b": 2}}},
        project_data_file="",
    )

    helper = Helper(metadata, control, "test_action")

    user_vars = {"user_var": "value"}

    result = helper.collect_extra_vars(user_vars, include_events=True)

    assert result["user_var"] == "value"
    assert KEY_EDA_VARS in result
    assert result[KEY_EDA_VARS]["events"] == {"m_0": {"a": 1}, "m_1": {"b": 2}}


@pytest.mark.asyncio
async def test_collect_extra_vars_without_events(metadata, control):
    """Test collect_extra_vars excludes event data when include_events=False"""
    helper = Helper(metadata, control, "test_action")

    user_vars = {"user_var": "value"}

    result = helper.collect_extra_vars(user_vars, include_events=False)

    assert result == {"user_var": "value"}
    assert KEY_EDA_VARS not in result


@pytest.mark.asyncio
async def test_collect_extra_vars_none_user_vars(metadata, control):
    """Test collect_extra_vars handles None user_vars"""
    helper = Helper(metadata, control, "test_action")

    result = helper.collect_extra_vars(None, include_events=True)

    assert KEY_EDA_VARS in result
    assert result[KEY_EDA_VARS]["ruleset"] == metadata.rule_set
    assert result[KEY_EDA_VARS]["rule"] == metadata.rule
    assert result[KEY_EDA_VARS]["event"] == {"a": 1}


@pytest.mark.asyncio
async def test_collect_extra_vars_preserves_user_vars(metadata, control):
    """Test collect_extra_vars doesn't modify original user_vars"""
    helper = Helper(metadata, control, "test_action")

    user_vars = {"user_var": "value"}
    original_vars = user_vars.copy()

    result = helper.collect_extra_vars(user_vars, include_events=True)

    assert user_vars == original_vars
    assert result != user_vars


@pytest.mark.asyncio
async def test_update_action_state_with_persistent_info(metadata, control):
    """Test update_action_state calls update_action_info when
    persistent_info exists"""
    # Create metadata with persistent_info
    persistent_info = MagicMock()
    persistent_info.matching_uuid = "matching-uuid-123"
    persistent_info.action_index = 0

    metadata_with_persistence = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
        persistent_info=persistent_info,
    )

    helper = Helper(metadata_with_persistence, control, "test_action")

    info = {"status": "completed"}

    with patch(
        "ansible_rulebook.action.helper.update_action_info"
    ) as mock_update:
        helper.update_action_state(info)

        mock_update.assert_called_once_with(
            "rs1", "matching-uuid-123", 0, info
        )


@pytest.mark.asyncio
async def test_update_action_state_without_persistent_info(metadata, control):
    """Test update_action_state doesn't call update_action_info when no
    persistent_info"""
    helper = Helper(metadata, control, "test_action")

    info = {"status": "completed"}

    with patch(
        "ansible_rulebook.action.helper.update_action_info"
    ) as mock_update:
        helper.update_action_state(info)

        mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_get_event_uuid_label_single_event(metadata):
    """Test get_event_uuid_label with single event"""
    queue = asyncio.Queue()
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": {"meta": {"uuid": EVENT_UUID}}},
        project_data_file="",
    )

    helper = Helper(metadata, control, "test_action")

    label = helper.get_event_uuid_label()

    assert label == f"eda-event-uuid-{EVENT_UUID}"


@pytest.mark.asyncio
async def test_get_event_uuid_label_multiple_events(metadata):
    """Test get_event_uuid_label with multiple events (uses first event)"""
    queue = asyncio.Queue()
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"events": {"m_0": {"meta": {"uuid": EVENT_UUID}}}},
        project_data_file="",
    )

    helper = Helper(metadata, control, "test_action")

    label = helper.get_event_uuid_label()

    assert label == f"eda-event-uuid-{EVENT_UUID}"


@pytest.mark.asyncio
async def test_get_event_uuid_label_invalid_event(metadata):
    """Test get_event_uuid_label raises ValueError for invalid event"""
    queue = asyncio.Queue()
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"other": "data"},
        project_data_file="",
    )

    helper = Helper(metadata, control, "test_action")

    with pytest.raises(ValueError, match="Invalid event type"):
        helper.get_event_uuid_label()


@pytest.mark.asyncio
async def test_get_old_job_url_no_persistent_info(metadata, control):
    """Test get_old_job_url returns None when no persistent_info"""
    helper = Helper(metadata, control, "test_action")

    result = await helper.get_old_job_url(
        "test-job", "test-org", "job_template", False
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_old_job_url_no_a_priori(metadata, control):
    """Test get_old_job_url returns None when no a_priori data"""
    persistent_info = MagicMock()
    persistent_info.matching_uuid = "matching-uuid-123"
    persistent_info.action_index = 0
    persistent_info.a_priori = None

    metadata_with_persistence = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
        persistent_info=persistent_info,
    )

    helper = Helper(metadata_with_persistence, control, "test_action")

    result = await helper.get_old_job_url(
        "test-job", "test-org", "job_template", False
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_old_job_url_with_job_url(metadata, control):
    """Test get_old_job_url returns job_url from a_priori"""
    persistent_info = MagicMock()
    persistent_info.matching_uuid = "matching-uuid-123"
    persistent_info.action_index = 0
    persistent_info.a_priori = {"job_url": "https://example.com/job/123"}

    metadata_with_persistence = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
        persistent_info=persistent_info,
    )

    helper = Helper(metadata_with_persistence, control, "test_action")

    result = await helper.get_old_job_url(
        "test-job", "test-org", "job_template", False
    )

    assert result == "https://example.com/job/123"


@pytest.mark.asyncio
async def test_get_old_job_url_started_status_with_label(metadata):
    """Test get_old_job_url fetches job_url using label when status is
    started"""
    queue = asyncio.Queue()
    control = Control(
        queue=queue,
        inventory="abc",
        hosts=["all"],
        variables={"event": {"meta": {"uuid": EVENT_UUID}}},
        project_data_file="",
    )

    persistent_info = MagicMock()
    persistent_info.matching_uuid = "matching-uuid-123"
    persistent_info.action_index = 0
    persistent_info.a_priori = {"status": STARTED_STATUS}

    metadata_with_persistence = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
        persistent_info=persistent_info,
    )

    helper = Helper(metadata_with_persistence, control, "test_action")

    with patch(
        "ansible_rulebook.action.helper.job_template_runner."
        "get_job_url_from_label",
        new_callable=AsyncMock,
    ) as mock_get_url:
        mock_get_url.return_value = "https://example.com/job/456"

        result = await helper.get_old_job_url(
            "test-job", "test-org", "job_template", add_event_uuid_label=True
        )

        mock_get_url.assert_called_once_with(
            "test-job",
            "test-org",
            "job_template",
            f"eda-event-uuid-{EVENT_UUID}",
        )
        assert result == "https://example.com/job/456"


@pytest.mark.asyncio
async def test_get_old_job_url_started_status_without_label(metadata, control):
    """Test get_old_job_url returns None when status is started but no
    label requested"""
    persistent_info = MagicMock()
    persistent_info.matching_uuid = "matching-uuid-123"
    persistent_info.action_index = 0
    persistent_info.a_priori = {"status": STARTED_STATUS}

    metadata_with_persistence = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
        persistent_info=persistent_info,
    )

    helper = Helper(metadata_with_persistence, control, "test_action")

    result = await helper.get_old_job_url(
        "test-job", "test-org", "job_template", add_event_uuid_label=False
    )

    assert result is None


@pytest.mark.asyncio
async def test_get_old_job_url_failed_status(metadata, control):
    """Test get_old_job_url returns None when status is failed"""
    persistent_info = MagicMock()
    persistent_info.matching_uuid = "matching-uuid-123"
    persistent_info.action_index = 0
    persistent_info.a_priori = {"status": FAILED_STATUS}

    metadata_with_persistence = Metadata(
        rule="r1",
        rule_set="rs1",
        rule_uuid=RULE_UUID,
        rule_set_uuid=RULE_SET_UUID,
        rule_run_at=RULE_RUN_AT,
        persistent_info=persistent_info,
    )

    helper = Helper(metadata_with_persistence, control, "test_action")

    result = await helper.get_old_job_url(
        "test-job", "test-org", "job_template", add_event_uuid_label=True
    )

    assert result is None
