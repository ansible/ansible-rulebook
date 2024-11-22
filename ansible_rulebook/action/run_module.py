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
import os

import yaml

from .control import Control
from .metadata import Metadata
from .run_playbook import RunPlaybook

logger = logging.getLogger(__name__)


class RunModule(RunPlaybook):
    """run_module runs an ansible module using the ansible runner"""

    MODULE_OUTPUT_KEY = "module_result"

    def __init__(
        self,
        metadata: Metadata,
        control: Control,
        **action_args,
    ):
        super().__init__(metadata, control, **action_args)
        self.helper.set_action("run_module")
        self.output_key = self.MODULE_OUTPUT_KEY

    async def _pre_process(self) -> None:
        await super()._pre_process()
        self.playbook = os.path.join(self.private_data_dir, "wrapper.yml")
        self._wrap_module_in_playbook()

    def _copy_playbook_files(self, project_dir):
        pass

    def _runner_args(self):
        return {"playbook": self.playbook, "inventory": self.inventory}

    def _wrap_module_in_playbook(self) -> None:
        module_args = self.action_args.get("module_args", {})
        module_task = {
            "name": "Module wrapper",
            self.name: module_args,
            "register": self.MODULE_OUTPUT_KEY,
        }
        result_str = "{{ " + self.MODULE_OUTPUT_KEY + " }}"
        set_fact_task = {
            "name": "save result",
            "ansible.builtin.set_fact": {
                self.MODULE_OUTPUT_KEY: result_str,
                "cacheable": True,
            },
        }
        tasks = [module_task, set_fact_task]
        wrapper = [
            dict(
                name="wrapper",
                hosts=self.host_limit,
                gather_facts=False,
                tasks=tasks,
            )
        ]
        with open(self.playbook, "w") as f:
            yaml.dump(wrapper, f)
