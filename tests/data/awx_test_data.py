UNIFIED_JOB_TEMPLATE_COUNT = 2
ORGANIZATION_NAME = "Default"
JOB_TEMPLATE_NAME_1 = "JT1"
JOB_TEMPLATE_1_LAUNCH_SLUG = "api/v2/job_templates/255/launch/"
JOB_TEMPLATE_2_LAUNCH_SLUG = "api/v2/workflow_job_templates/300/launch/"

JOB_TEMPLATE_1 = dict(
    type="job_template",
    name=JOB_TEMPLATE_NAME_1,
    ask_limit_on_launch=False,
    ask_variables_on_launch=False,
    ask_inventory_on_launch=False,
    related=dict(launch=JOB_TEMPLATE_1_LAUNCH_SLUG),
    summary_fields=dict(organization=dict(name=ORGANIZATION_NAME)),
)

JOB_TEMPLATE_2 = dict(
    type="workflow_job_template",
    name=JOB_TEMPLATE_NAME_1,
    ask_limit_on_launch=False,
    ask_variables_on_launch=False,
    ask_inventory_on_launch=False,
    related=dict(launch=JOB_TEMPLATE_2_LAUNCH_SLUG),
)

UNIFIED_JOB_TEMPLATE_PAGE1_SLUG = (
    f"api/v2/unified_job_templates/?name={JOB_TEMPLATE_NAME_1}"
)
UNIFIED_JOB_TEMPLATE_PAGE2_SLUG = (
    f"api/v2/unified_job_templates/?name={JOB_TEMPLATE_NAME_1}&page=2"
)
UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE = dict(
    count=UNIFIED_JOB_TEMPLATE_COUNT,
    next=UNIFIED_JOB_TEMPLATE_PAGE2_SLUG,
    previous=None,
    results=[JOB_TEMPLATE_1],
)

NO_JOB_TEMPLATE_PAGE1_RESPONSE = dict(
    count=0,
    next=None,
    previous=None,
    results=[],
)

UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE = dict(
    count=UNIFIED_JOB_TEMPLATE_COUNT,
    previous=UNIFIED_JOB_TEMPLATE_PAGE1_SLUG,
    next=None,
    results=[JOB_TEMPLATE_2],
)

JOB_STATUS_RUNNING = "running"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_SUCCESSFUL = "successful"
JOB_ARTIFACTS = {
    "fred": 45,
    "barney": 90,
}
JOB_ID_1 = 909
JOB_1_SLUG = f"api/v2/jobs/{JOB_ID_1}/"
JOB_TEMPLATE_POST_RESPONSE = dict(
    job=JOB_ID_1,
    url=JOB_1_SLUG,
    status=JOB_STATUS_SUCCESSFUL,
    artifacts=JOB_ARTIFACTS,
)
JOB_1_RUNNING = dict(
    job=JOB_ID_1,
    url=JOB_1_SLUG,
    status=JOB_STATUS_RUNNING,
)

JOB_1_SUCCESSFUL = dict(
    job=JOB_ID_1,
    url=JOB_1_SLUG,
    status=JOB_STATUS_SUCCESSFUL,
    artifacts=JOB_ARTIFACTS,
)
