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

import logging

from ansible_rulebook.exception import JobTemplateNotFoundException
from ansible_rulebook.job_template_runner import job_template_runner

from .run_base import RunTemplate

logger = logging.getLogger(__name__)


class RunJobTemplate(RunTemplate):
    """run_job_template action launches a specified job template on
    the controller. It waits for the job to be complete.
    """

    @property
    def _action_name(self):
        return "run_job_template"

    @property
    def _exceptions(self):
        return super()._exceptions + (JobTemplateNotFoundException,)

    @property
    def _run_job(self):
        return job_template_runner.run_job_template

    @property
    def _template_name(self):
        return "job template"

    @property
    def _url_prefix(self):
        return super()._url_prefix + "jobs/"

    def _make_log(self):
        log = super()._make_log()
        log["job_template_name"] = self.name
        return log
