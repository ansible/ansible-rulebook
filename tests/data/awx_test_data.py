from urllib.parse import urlencode

from ansible_rulebook.conf import DEFAULT_EDA_LABEL

UNIFIED_JOB_TEMPLATE_COUNT = 2
ORGANIZATION_NAME = "Default"
JOB_TEMPLATE_NAME_1 = "JT1"
JOB_TEMPLATE_1_LAUNCH_SLUG = "api/v2/job_templates/255/launch/"
JOB_TEMPLATE_2_LAUNCH_SLUG = "api/v2/workflow_job_templates/300/launch/"

JOB_TEMPLATE_1 = {
    "type": "job_template",
    "name": JOB_TEMPLATE_NAME_1,
    "ask_limit_on_launch": False,
    "ask_variables_on_launch": False,
    "ask_inventory_on_launch": False,
    "ask_labels_on_launch": True,
    "related": {"launch": JOB_TEMPLATE_1_LAUNCH_SLUG},
    "summary_fields": {"organization": {"name": ORGANIZATION_NAME}},
}

JOB_TEMPLATE_1_NO_LABELS = {
    "type": "job_template",
    "name": JOB_TEMPLATE_NAME_1,
    "ask_limit_on_launch": False,
    "ask_variables_on_launch": False,
    "ask_inventory_on_launch": False,
    "ask_labels_on_launch": False,
    "related": {"launch": JOB_TEMPLATE_1_LAUNCH_SLUG},
    "summary_fields": {"organization": {"name": ORGANIZATION_NAME}},
}

JOB_TEMPLATE_2 = {
    "type": "workflow_job_template",
    "name": JOB_TEMPLATE_NAME_1,
    "ask_limit_on_launch": False,
    "ask_variables_on_launch": False,
    "ask_inventory_on_launch": True,
    "ask_labels_on_launch": True,
    "related": {"launch": JOB_TEMPLATE_2_LAUNCH_SLUG},
}

JOB_TEMPLATE_2_NO_LABELS = {
    "type": "workflow_job_template",
    "name": JOB_TEMPLATE_NAME_1,
    "ask_limit_on_launch": False,
    "ask_variables_on_launch": False,
    "ask_inventory_on_launch": True,
    "ask_labels_on_launch": False,
    "related": {"launch": JOB_TEMPLATE_2_LAUNCH_SLUG},
}

UNIFIED_JOB_TEMPLATE_PAGE1_SLUG = (
    f"api/v2/unified_job_templates/?name={JOB_TEMPLATE_NAME_1}"
)
UNIFIED_JOB_TEMPLATE_PAGE2_SLUG = (
    f"api/v2/unified_job_templates/?name={JOB_TEMPLATE_NAME_1}&page=2"
)
UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE = {
    "count": UNIFIED_JOB_TEMPLATE_COUNT,
    "next": UNIFIED_JOB_TEMPLATE_PAGE2_SLUG,
    "previous": None,
    "results": [JOB_TEMPLATE_1],
}

UNIFIED_JOB_TEMPLATE_PAGE1_RESPONSE_NO_LABELS = {
    "count": UNIFIED_JOB_TEMPLATE_COUNT,
    "next": UNIFIED_JOB_TEMPLATE_PAGE2_SLUG,
    "previous": None,
    "results": [JOB_TEMPLATE_1_NO_LABELS],
}

NO_JOB_TEMPLATE_PAGE1_RESPONSE = {
    "count": 0,
    "next": None,
    "previous": None,
    "results": [],
}

UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE = {
    "count": UNIFIED_JOB_TEMPLATE_COUNT,
    "previous": UNIFIED_JOB_TEMPLATE_PAGE1_SLUG,
    "next": None,
    "results": [JOB_TEMPLATE_2],
}

UNIFIED_JOB_TEMPLATE_PAGE2_RESPONSE_NO_LABELS = {
    "count": UNIFIED_JOB_TEMPLATE_COUNT,
    "previous": UNIFIED_JOB_TEMPLATE_PAGE1_SLUG,
    "next": None,
    "results": [JOB_TEMPLATE_2_NO_LABELS],
}

JOB_STATUS_RUNNING = "running"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_SUCCESSFUL = "successful"
JOB_ARTIFACTS = {
    "fred": 45,
    "barney": 90,
}
JOB_ID_1 = 909
JOB_1_SLUG = f"api/v2/jobs/{JOB_ID_1}/"
JOB_TEMPLATE_POST_RESPONSE = {
    "job": JOB_ID_1,
    "url": JOB_1_SLUG,
    "status": JOB_STATUS_SUCCESSFUL,
    "artifacts": JOB_ARTIFACTS,
}

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

ORGANIZATION_SLUG = f"api/v2/organizations/?name={ORGANIZATION_NAME}"

ORGANIZATION_DATA = {"id": 1, "name": ORGANIZATION_NAME}

ORGANIZATION_RESPONSE = {
    "count": 1,
    "next": None,
    "results": [ORGANIZATION_DATA],
}

LABEL_QUERY_PARAMS = {"name": DEFAULT_EDA_LABEL}
DEFAULT_LABEL_SLUG = f"api/v2/labels/?{urlencode(LABEL_QUERY_PARAMS)}"
DEFAULT_LABEL_DATA = {"id": 1, "name": DEFAULT_EDA_LABEL}

DEFAULT_LABEL_RESPONSE = {
    "count": 1,
    "next": "None",
    "results": [DEFAULT_LABEL_DATA],
}

LABEL_POST_SLUG = "api/v2/labels/"
CUSTOMER_LABEL = "This is for Slate&Rock \nCompany"
CUSTOMER_LABEL_QUERY_PARAMS = {"name": CUSTOMER_LABEL}
CUSTOMER_LABEL_SLUG = (
    f"api/v2/labels/?{urlencode(CUSTOMER_LABEL_QUERY_PARAMS)}"
)

NO_SUCH_LABEL = NO_JOB_TEMPLATE_PAGE1_RESPONSE
NO_SUCH_ORGANIZATION = NO_JOB_TEMPLATE_PAGE1_RESPONSE

CUSTOMER_LABEL_DATA = {"id": 2, "name": CUSTOMER_LABEL}

CUSTOMER_LABEL_RESPONSE = {
    "count": 1,
    "next": None,
    "results": [CUSTOMER_LABEL_DATA],
}
