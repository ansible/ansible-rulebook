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

import asyncio
import glob
import json
import logging
import os
import shutil
import tempfile
from typing import Any

import drools
import yaml

from ansible_rulebook.collection import (
    find_playbook,
    has_playbook,
    split_collection_name,
)
from ansible_rulebook.exception import (
    MissingArtifactKeyException,
    PlaybookNotFoundException,
    PlaybookStatusNotFoundException,
)
from ansible_rulebook.util import create_inventory, run_at

from .control import Control
from .metadata import Metadata
from .run_base import RunBase
from .runner import Runner

logger = logging.getLogger(__name__)

tar = shutil.which("tar")


class RunPlaybook(RunBase):
    """run_playbook action runs an ansible playbook using the
    ansible-runner
    """

    @property
    def _action_name(self) -> str:
        return "run_playbook"

    @property
    def _job_data(self) -> dict:
        data = super()._job_data
        data["hosts"] = self.host_limit
        return data

    def __init__(self, metadata: Metadata, control: Control, **action_args):
        super().__init__(metadata, control, **action_args)
        self.default_copy_files = True
        self.default_check_files = True
        self.verbosity = self.action_args.get("verbosity", 0)
        self.json_mode = self.action_args.get("json_mode", False)
        self.host_limit = ",".join(self.helper.control.hosts)
        self.private_data_dir = tempfile.mkdtemp(prefix="eda")
        self.output_key = None
        self.inventory = None

    async def __call__(self):
        try:
            logger.info(
                f"ruleset: {self.helper.metadata.rule_set}, "
                f"rule: {self.helper.metadata.rule}"
            )
            logger.debug("private data dir %s", self.private_data_dir)
            await super().__call__()
        finally:
            if os.path.exists(self.private_data_dir):
                shutil.rmtree(self.private_data_dir)

    async def _run(self):
        logger.info("Calling Ansible runner")
        await super()._run()

    async def _do_run(self) -> bool:
        await Runner(
            self.private_data_dir,
            self.host_limit,
            self.verbosity,
            self.job_id,
            self.json_mode,
            self.helper,
            self._runner_args(),
        )()
        return self._get_latest_artifact("status") == "failed"

    def _runner_args(self) -> dict:
        return {"playbook": self.name, "inventory": self.inventory}

    async def _pre_process(self) -> None:
        await super()._pre_process()

        playbook_extra_vars = self.helper.collect_extra_vars(
            self.action_args.get("extra_vars", {})
        )

        env_dir = os.path.join(self.private_data_dir, "env")
        inventory_dir = os.path.join(self.private_data_dir, "inventory")
        project_dir = os.path.join(self.private_data_dir, "project")

        os.mkdir(env_dir)
        with open(os.path.join(env_dir, "extravars"), "w") as file_handle:
            file_handle.write(yaml.dump(playbook_extra_vars))
        os.mkdir(inventory_dir)

        if self.helper.control.inventory:
            create_inventory(inventory_dir, self.helper.control.inventory)
            self.inventory = os.path.join(
                inventory_dir, os.path.basename(self.helper.control.inventory)
            )
        os.mkdir(project_dir)

        logger.debug(
            "project_data_file: %s", self.helper.control.project_data_file
        )
        if self.helper.control.project_data_file:
            if os.path.exists(self.helper.control.project_data_file):
                await self._untar_project(
                    project_dir, self.helper.control.project_data_file
                )
                return
        self._copy_playbook_files(project_dir)

    async def _post_process(self) -> None:
        rc = int(self._get_latest_artifact("rc"))
        status = self._get_latest_artifact("status")
        logger.info("Ansible runner rc: %d, status: %s", rc, status)
        if rc != 0:
            error_message = self._get_latest_artifact("stderr")
            if not error_message:
                error_message = self._get_latest_artifact("stdout")
            logger.error(error_message)

        await self.helper.send_status(
            {
                "playbook_name": self.name,
                "job_id": self.job_id,
                "rc": rc,
                "status": status,
                "run_at": run_at(),
                "matching_events": self.helper.get_events(),
            }
        )
        set_facts = self.action_args.get("set_facts", False)
        post_events = self.action_args.get("post_events", False)

        if rc == 0 and (set_facts or post_events):
            logger.debug("set_facts")
            fact_folder = self._get_latest_artifact("fact_cache", False)
            ruleset = self.action_args.get(
                "ruleset", self.helper.metadata.rule_set
            )
            for host_facts in glob.glob(os.path.join(fact_folder, "*")):
                with open(host_facts) as file_handle:
                    fact = json.loads(file_handle.read())
                if self.output_key:
                    if self.output_key not in fact:
                        logger.error(
                            "The artifacts from the ansible-runner "
                            "does not have key %s",
                            self.output_key,
                        )
                        raise MissingArtifactKeyException(
                            f"Missing key: {self.output_key} in artifacts"
                        )
                    fact = fact[self.output_key]
                fact = self.helper.embellish_internal_event(fact)
                logger.debug("fact %s", fact)
                if set_facts:
                    drools.ruleset.assert_fact(ruleset, fact)
                if post_events:
                    drools.ruleset.post(ruleset, fact)

        await super()._post_process()

    def _copy_playbook_files(self, project_dir) -> None:
        if self.action_args.get("check_files", self.default_check_files):
            if os.path.exists(self.name):
                tail_name = os.path.basename(self.name)
                shutil.copy(self.name, os.path.join(project_dir, tail_name))
                if self.action_args.get("copy_files", self.default_copy_files):
                    shutil.copytree(
                        os.path.dirname(os.path.abspath(self.name)),
                        project_dir,
                        dirs_exist_ok=True,
                    )
                self.name = tail_name
            elif has_playbook(*split_collection_name(self.name)):
                shutil.copy(
                    find_playbook(*split_collection_name(self.name)),
                    os.path.join(project_dir, self.name),
                )
            else:
                msg = (
                    f"Could not find a playbook for {self.name} "
                    f"from {os.getcwd()}"
                )
                logger.error(msg)
                raise PlaybookNotFoundException(msg)

    def _get_latest_artifact(
        self, component: str, content: bool = True
    ) -> Any:
        files = glob.glob(
            os.path.join(self.private_data_dir, "artifacts", "*", component)
        )
        files.sort(key=os.path.getmtime, reverse=True)
        if not files:
            raise PlaybookStatusNotFoundException(f"No {component} file found")
        if content:
            with open(files[0], "r") as file_handle:
                content = file_handle.read()
            return content
        return files[0]

    async def _untar_project(self, output_dir, project_data_file) -> None:

        cmd = [tar, "zxvf", project_data_file]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=output_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await proc.communicate()

        if stdout:
            logger.debug(stdout.decode())
        if stderr:
            logger.debug(stderr.decode())
