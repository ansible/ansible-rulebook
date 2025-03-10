import asyncio

import pytest

from ansible_rulebook.action.control import Control
from ansible_rulebook.action.run_job_template import RunJobTemplate
from ansible_rulebook.action.run_workflow_template import RunWorkflowTemplate


@pytest.mark.parametrize(
    "template_class",
    [
        pytest.param(RunJobTemplate, id="job_template"),
        pytest.param(RunWorkflowTemplate, id="workflow_template"),
    ],
)
@pytest.mark.parametrize(
    "input,expected",
    [
        pytest.param({"limit": "localhost"}, "localhost", id="single_host"),
        pytest.param(
            {"limit": "localhost,localhost2"},
            "localhost,localhost2",
            id="multiple_hosts_str",
        ),
        pytest.param(
            {"limit": ["localhost", "localhost2"]},
            "localhost,localhost2",
            id="multiple_hosts",
        ),
        pytest.param({}, "all", id="default"),
    ],
)
@pytest.mark.asyncio
async def test_controller_custom_host_limit(
    input, expected, template_class, base_metadata
):
    """Test controller templates process the host limit in job_args."""
    action_args = {
        "name": "fred",
        "organization": "Default",
        "retries": 1,
        "retry": True,
        "delay": 1,
        "set_facts": True,
        "job_args": input,
    }
    base_control = Control(
        queue=asyncio.Queue(),
        inventory="abc",
        hosts=["all"],
        variables={"a": 1},
        project_data_file="",
    )
    template = template_class(base_metadata, base_control, **action_args)
    assert template.job_args["limit"] == expected
