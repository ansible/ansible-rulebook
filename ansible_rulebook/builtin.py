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

import asyncio
import concurrent.futures
import glob
import json
import logging
import os
import shutil
import sys
import tempfile
import uuid
from asyncio.exceptions import CancelledError
from functools import partial
from pprint import pprint
from typing import Callable, Dict, List, Optional, Union

import ansible_runner
import dpath
import janus
import yaml
from drools import ruleset as lang

from .collection import find_playbook, has_playbook, split_collection_name
from .conf import settings
from .event_filter.insert_meta_info import main as insert_meta
from .exception import (
    ControllerApiException,
    JobTemplateNotFoundException,
    PlaybookNotFoundException,
    PlaybookStatusNotFoundException,
    ShutdownException,
)
from .job_template_runner import job_template_runner
from .messages import Shutdown
from .util import create_inventory, get_horizontal_rule, run_at

logger = logging.getLogger(__name__)

tar = shutil.which("tar")

KEY_EDA_VARS = "ansible_eda"
INTERNAL_ACTION_STATUS = "successful"


async def none(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
):
    await event_log.put(
        dict(
            type="Action",
            action="noop",
            action_uuid=str(uuid.uuid4()),
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            activation_id=settings.identifier,
            run_at=run_at(),
            status=INTERNAL_ACTION_STATUS,
            matching_events=_get_events(variables),
            rule_run_at=rule_run_at,
        )
    )


async def debug(event_log, **kwargs):
    if "msg" in kwargs:
        messages = kwargs.get("msg")
        if not isinstance(messages, list):
            messages = [messages]
        for msg in messages:
            print(msg)
    elif "var" in kwargs:
        key = kwargs.get("var")
        try:
            print(dpath.get(kwargs.get("variables"), key, separator="."))
        except KeyError:
            logger.error("Key %s not found in variable pool", key)
            return
    else:
        print(get_horizontal_rule("="))
        print("kwargs:")
        pprint(kwargs)
        print(get_horizontal_rule("="))
        print("facts:")
        pprint(lang.get_facts(kwargs["source_ruleset_name"]))
        print(get_horizontal_rule("="))
    sys.stdout.flush()
    await event_log.put(
        dict(
            type="Action",
            action="debug",
            action_uuid=str(uuid.uuid4()),
            playbook_name=kwargs.get("name"),
            ruleset=kwargs.get("source_ruleset_name"),
            ruleset_uuid=kwargs.get("source_ruleset_uuid"),
            rule=kwargs.get("source_rule_name"),
            rule_uuid=kwargs.get("source_rule_uuid"),
            rule_run_at=kwargs.get("rule_run_at"),
            activation_id=settings.identifier,
            run_at=run_at(),
            status=INTERNAL_ACTION_STATUS,
            matching_events=_get_events(kwargs.get("variables")),
        )
    )


async def print_event(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    name: Optional[str] = None,
    pretty: Optional[str] = None,
):
    print_fn: Callable = print
    if pretty:
        print_fn = pprint

    var_name = "events" if "events" in variables else "event"

    print_fn(variables[var_name])
    sys.stdout.flush()
    await event_log.put(
        dict(
            type="Action",
            action="print_event",
            action_uuid=str(uuid.uuid4()),
            activation_id=settings.identifier,
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            playbook_name=name,
            run_at=run_at(),
            status=INTERNAL_ACTION_STATUS,
            matching_events=_get_events(variables),
            rule_run_at=rule_run_at,
        )
    )


async def set_fact(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    fact: Dict,
    name: Optional[str] = None,
):
    logger.debug("set_fact %s %s", ruleset, fact)
    lang.assert_fact(ruleset, _embellish_internal_event(fact, "set_fact"))
    await event_log.put(
        dict(
            type="Action",
            action="set_fact",
            action_uuid=str(uuid.uuid4()),
            activation_id=settings.identifier,
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            playbook_name=name,
            run_at=run_at(),
            status=INTERNAL_ACTION_STATUS,
            matching_events=_get_events(variables),
            rule_run_at=rule_run_at,
        )
    )


async def retract_fact(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    fact: Dict,
    partial: bool = True,
    name: Optional[str] = None,
):

    if not partial:
        exclude_keys = ["meta"]
    else:
        exclude_keys = []

    lang.retract_matching_facts(ruleset, fact, partial, exclude_keys)
    await event_log.put(
        dict(
            type="Action",
            action="retract_fact",
            action_uuid=str(uuid.uuid4()),
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            activation_id=settings.identifier,
            playbook_name=name,
            run_at=run_at(),
            status=INTERNAL_ACTION_STATUS,
            matching_events=_get_events(variables),
            rule_run_at=rule_run_at,
        )
    )


async def post_event(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    event: Dict,
):
    lang.post(ruleset, _embellish_internal_event(event, "post_event"))

    await event_log.put(
        dict(
            type="Action",
            action="post_event",
            action_uuid=str(uuid.uuid4()),
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            activation_id=settings.identifier,
            run_at=run_at(),
            status=INTERNAL_ACTION_STATUS,
            matching_events=_get_events(variables),
            rule_run_at=rule_run_at,
        )
    )


async def run_playbook(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    name: str,
    set_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
    verbosity: int = 0,
    copy_files: Optional[bool] = False,
    json_mode: Optional[bool] = False,
    retries: Optional[int] = 0,
    retry: Optional[bool] = False,
    delay: Optional[int] = 0,
    extra_vars: Optional[Dict] = None,
    **kwargs,
):

    logger.info("running Ansible playbook: %s", name)
    temp_dir, playbook_name = await pre_process_runner(
        event_log,
        inventory,
        variables,
        source_ruleset_name,
        source_rule_name,
        name,
        "run_playbook",
        copy_files,
        True,
        project_data_file,
        extra_vars,
        **kwargs,
    )

    job_id = str(uuid.uuid4())

    logger.info(f"ruleset: {source_ruleset_name}, rule: {source_rule_name}")
    await event_log.put(
        dict(
            type="Job",
            job_id=job_id,
            ansible_rulebook_id=settings.identifier,
            name=playbook_name,
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            hosts=",".join(hosts),
            action="run_playbook",
        )
    )

    logger.info("Calling Ansible runner")

    if retry:
        retries = max(retries, 1)
    for i in range(retries + 1):
        if i > 0:
            if delay > 0:
                await asyncio.sleep(delay)
            logger.info(
                "Previous run_playbook failed. Retry %d of %d", i, retries
            )

        action_run_at = run_at()
        await call_runner(
            event_log,
            job_id,
            temp_dir,
            dict(playbook=playbook_name),
            hosts,
            inventory,
            verbosity,
            json_mode,
        )
        if _get_latest_artifact(temp_dir, "status") != "failed":
            break

    await post_process_runner(
        event_log,
        variables,
        temp_dir,
        ruleset,
        source_ruleset_uuid,
        source_rule_name,
        source_rule_uuid,
        rule_run_at,
        settings.identifier,
        name,
        "run_playbook",
        job_id,
        action_run_at,
        set_facts,
        post_events,
    )

    shutil.rmtree(temp_dir)


async def run_module(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    name: str,
    set_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
    verbosity: int = 0,
    copy_files: Optional[bool] = False,
    json_mode: Optional[bool] = False,
    module_args: Union[Dict, None] = None,
    retries: Optional[int] = 0,
    retry: Optional[bool] = False,
    delay: Optional[int] = 0,
    extra_vars: Optional[Dict] = None,
    **kwargs,
):
    temp_dir, module_name = await pre_process_runner(
        event_log,
        inventory,
        variables,
        source_ruleset_name,
        source_rule_name,
        name,
        "run_module",
        copy_files,
        False,
        project_data_file,
        extra_vars,
        **kwargs,
    )
    job_id = str(uuid.uuid4())

    await event_log.put(
        dict(
            type="Job",
            job_id=job_id,
            ansible_rulebook_id=settings.identifier,
            name=module_name,
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            hosts=",".join(hosts),
            action="run_module",
        )
    )

    logger.info("Calling Ansible runner")
    module_args_str = ""
    if module_args:
        for k, v in module_args.items():
            if len(module_args_str) > 0:
                module_args_str += " "
            module_args_str += f"{k}={v!r}"

    if retry:
        retries = max(retries, 1)
    for i in range(retries + 1):
        if i > 0:
            if delay > 0:
                await asyncio.sleep(delay)
            logger.info(
                "Previous run_module failed. Retry %d of %d", i, retries
            )
        action_run_at = run_at()
        await call_runner(
            event_log,
            job_id,
            temp_dir,
            dict(
                module=module_name,
                host_pattern=",".join(hosts),
                module_args=module_args_str,
            ),
            hosts,
            inventory,
            verbosity,
            json_mode,
        )
        if _get_latest_artifact(temp_dir, "status") != "failed":
            break

    await post_process_runner(
        event_log,
        variables,
        temp_dir,
        ruleset,
        source_ruleset_uuid,
        source_rule_name,
        source_rule_uuid,
        rule_run_at,
        settings.identifier,
        name,
        "run_module",
        job_id,
        action_run_at,
        set_facts,
        post_events,
    )
    shutil.rmtree(temp_dir)


async def call_runner(
    event_log,
    job_id: str,
    private_data_dir: str,
    runner_args: Dict,
    hosts: List,
    inventory: str,
    verbosity: int = 0,
    json_mode: Optional[bool] = False,
):

    host_limit = ",".join(hosts)
    shutdown = False

    loop = asyncio.get_running_loop()

    queue = janus.Queue()

    # The event_callback is called from the ansible-runner thread
    # It needs a thread-safe synchronous queue.
    # Janus provides a sync queue connected to an async queue
    # Here we push the event into the sync side of janus
    def event_callback(event, *args, **kwargs):
        event["job_id"] = job_id
        event["ansible_rulebook_id"] = settings.identifier
        queue.sync_q.put(dict(type="AnsibleEvent", event=event))

    # Here we read the async side and push it into the event queue
    # which is also async.
    # We do this until cancelled at the end of the ansible runner call.
    # We might need to drain the queue here before ending.
    async def read_queue():
        try:
            while True:
                val = await queue.async_q.get()
                event_data = val.get("event", {})
                val["run_at"] = event_data.get("created")
                await event_log.put(val)
        except CancelledError:
            logger.info("Ansible Runner Queue task cancelled")

    def cancel_callback():
        return shutdown

    tasks = []

    tasks.append(asyncio.create_task(read_queue()))

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as task_pool:
        try:
            await loop.run_in_executor(
                task_pool,
                partial(
                    ansible_runner.run,
                    private_data_dir=private_data_dir,
                    limit=host_limit,
                    verbosity=verbosity,
                    event_handler=event_callback,
                    cancel_callback=cancel_callback,
                    inventory=os.path.join(
                        private_data_dir,
                        "inventory",
                        os.path.basename(inventory),
                    ),
                    json_mode=json_mode,
                    **runner_args,
                ),
            )
        except CancelledError:
            logger.debug("Ansible Runner Thread Pool executor task cancelled")
            shutdown = True
            raise
        finally:
            # Cancel the queue reading task
            for task in tasks:
                if not task.done():
                    logger.debug("Cancel Queue reading task")
                    task.cancel()

            await asyncio.gather(*tasks)


async def untar_project(output_dir, project_data_file):

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


async def pre_process_runner(
    event_log,
    inventory: str,
    variables: Dict,
    ruleset: str,
    rulename: str,
    name: str,
    action: str,
    copy_files: Optional[bool] = False,
    check_files: Optional[bool] = True,
    project_data_file: Optional[str] = None,
    extra_vars: Optional[Dict] = None,
    **kwargs,
):

    private_data_dir = tempfile.mkdtemp(prefix=action)
    logger.debug("private data dir %s", private_data_dir)

    playbook_extra_vars = _collect_extra_vars(
        variables, extra_vars, ruleset, rulename
    )

    env_dir = os.path.join(private_data_dir, "env")
    inventory_dir = os.path.join(private_data_dir, "inventory")
    project_dir = os.path.join(private_data_dir, "project")

    playbook_name = name

    os.mkdir(env_dir)
    with open(os.path.join(env_dir, "extravars"), "w") as f:
        f.write(yaml.dump(playbook_extra_vars))
    os.mkdir(inventory_dir)
    if inventory:
        create_inventory(inventory_dir, inventory)
    os.mkdir(project_dir)

    logger.debug("project_data_file: %s", project_data_file)
    if project_data_file:
        if os.path.exists(project_data_file):
            await untar_project(project_dir, project_data_file)
            return (private_data_dir, playbook_name)

    if check_files:
        if os.path.exists(name):
            playbook_name = os.path.basename(name)
            shutil.copy(name, os.path.join(project_dir, playbook_name))
            if copy_files:
                shutil.copytree(
                    os.path.dirname(os.path.abspath(name)),
                    project_dir,
                    dirs_exist_ok=True,
                )
        elif has_playbook(*split_collection_name(name)):
            playbook_name = name
            shutil.copy(
                find_playbook(*split_collection_name(name)),
                os.path.join(project_dir, name),
            )
        else:
            msg = f"Could not find a playbook for {name} from {os.getcwd()}"
            logger.error(msg)
            raise PlaybookNotFoundException(msg)

    return (private_data_dir, playbook_name)


async def post_process_runner(
    event_log,
    variables: Dict,
    private_data_dir: str,
    ruleset: str,
    ruleset_uuid: str,
    rule: str,
    rule_uuid: str,
    rule_run_at: str,
    activation_id: str,
    name: str,
    action: str,
    job_id: str,
    run_at: str,
    set_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
):

    rc = int(_get_latest_artifact(private_data_dir, "rc"))
    status = _get_latest_artifact(private_data_dir, "status")
    logger.info("Playbook rc: %d, status: %s", rc, status)
    if rc != 0:
        error_message = _get_latest_artifact(private_data_dir, "stderr")
        if not error_message:
            error_message = _get_latest_artifact(private_data_dir, "stdout")
        logger.error(error_message)

    result = dict(
        type="Action",
        action=action,
        action_uuid=str(uuid.uuid4()),
        activation_id=activation_id,
        playbook_name=name,
        job_id=job_id,
        ruleset=ruleset,
        ruleset_uuid=ruleset_uuid,
        rule=rule,
        rule_uuid=rule_uuid,
        rc=rc,
        status=status,
        run_at=run_at,
        matching_events=_get_events(variables),
        rule_run_at=rule_run_at,
    )
    await event_log.put(result)

    if rc == 0 and (set_facts or post_events):
        logger.debug("set_facts")
        fact_folder = _get_latest_artifact(
            private_data_dir, "fact_cache", False
        )
        for host_facts in glob.glob(os.path.join(fact_folder, "*")):
            with open(host_facts) as f:
                fact = json.loads(f.read())
            fact = _embellish_internal_event(fact, action)
            logger.debug("fact %s", fact)
            if set_facts:
                lang.assert_fact(ruleset, fact)
            if post_events:
                lang.post(ruleset, fact)


async def run_job_template(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    name: str,
    organization: str,
    job_args: Optional[dict] = None,
    set_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
    verbosity: int = 0,
    copy_files: Optional[bool] = False,
    json_mode: Optional[bool] = False,
    retries: Optional[int] = 0,
    retry: Optional[bool] = False,
    delay: Optional[int] = 0,
    **kwargs,
):

    logger.info(
        "running job template: %s, organization: %s", name, organization
    )
    logger.info("ruleset: %s, rule %s", source_ruleset_name, source_rule_name)

    hosts_limit = ",".join(hosts)
    if not job_args:
        job_args = {}
    job_args["limit"] = hosts_limit

    job_args["extra_vars"] = _collect_extra_vars(
        variables,
        job_args.get("extra_vars", {}),
        source_ruleset_name,
        source_rule_name,
    )

    job_id = str(uuid.uuid4())

    await event_log.put(
        dict(
            type="Job",
            job_id=job_id,
            ansible_rulebook_id=settings.identifier,
            name=name,
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            hosts=hosts_limit,
            action="run_job_template",
        )
    )

    if retry:
        retries = max(retries, 1)

    try:
        for i in range(retries + 1):
            if i > 0:
                if delay > 0:
                    await asyncio.sleep(delay)
                logger.info(
                    "Previous run_job_template failed. Retry %d of %d",
                    i,
                    retries,
                )
            controller_job = await job_template_runner.run_job_template(
                name,
                organization,
                job_args,
            )
            if controller_job["status"] != "failed":
                break
    except (ControllerApiException, JobTemplateNotFoundException) as ex:
        logger.error(ex)
        controller_job = {}
        controller_job["status"] = "failed"
        controller_job["created"] = run_at()
        controller_job["error"] = str(ex)

    a_log = dict(
        type="Action",
        action="run_job_template",
        action_uuid=str(uuid.uuid4()),
        activation_id=settings.identifier,
        job_template_name=name,
        organization=organization,
        job_id=job_id,
        ruleset=ruleset,
        ruleset_uuid=source_ruleset_uuid,
        rule=source_rule_name,
        rule_uuid=source_rule_uuid,
        status=controller_job["status"],
        run_at=controller_job["created"],
        url=_controller_job_url(controller_job),
        matching_events=_get_events(variables),
        rule_run_at=rule_run_at,
    )
    if "error" in controller_job:
        a_log["message"] = controller_job["error"]
    await event_log.put(a_log)

    if set_facts or post_events:
        logger.debug("set_facts")
        facts = controller_job["artifacts"]
        if facts:
            facts = _embellish_internal_event(facts, "run_job_template")
            logger.debug("facts %s", facts)
            if set_facts:
                lang.assert_fact(ruleset, facts)
            if post_events:
                lang.post(ruleset, facts)
        else:
            logger.debug("Empty facts are not set")


async def shutdown(
    event_log,
    inventory: str,
    hosts: List,
    variables: Dict,
    project_data_file: str,
    source_ruleset_name: str,
    source_ruleset_uuid: str,
    source_rule_name: str,
    source_rule_uuid: str,
    rule_run_at: str,
    ruleset: str,
    delay: float = 60.0,
    message: str = "Default shutdown message",
    kind: str = "graceful",
):
    await event_log.put(
        dict(
            type="Action",
            action="shutdown",
            action_uuid=str(uuid.uuid4()),
            activation_id=settings.identifier,
            ruleset=source_ruleset_name,
            ruleset_uuid=source_ruleset_uuid,
            rule=source_rule_name,
            rule_uuid=source_rule_uuid,
            run_at=run_at(),
            status=INTERNAL_ACTION_STATUS,
            matching_events=_get_events(variables),
            delay=delay,
            message=message,
            kind=kind,
            rule_run_at=rule_run_at,
        )
    )

    print(
        "Ruleset: %s rule: %s has initiated shutdown of type: %s. "
        "Delay: %.3f seconds, Message: %s"
        % (source_ruleset_name, source_rule_name, kind, delay, message)
    )
    raise ShutdownException(Shutdown(message=message, delay=delay, kind=kind))


actions: Dict[str, Callable] = dict(
    none=none,
    debug=debug,
    print_event=print_event,
    set_fact=set_fact,
    retract_fact=retract_fact,
    post_event=post_event,
    run_playbook=run_playbook,
    run_module=run_module,
    run_job_template=run_job_template,
    shutdown=shutdown,
)


def _get_latest_artifact(data_dir: str, artifact: str, content: bool = True):
    files = glob.glob(os.path.join(data_dir, "artifacts", "*", artifact))
    files.sort(key=os.path.getmtime, reverse=True)
    if not files:
        raise PlaybookStatusNotFoundException(f"No {artifact} file found")
    if content:
        with open(files[0], "r") as f:
            content = f.read()
        return content
    return files[0]


def _get_events(variables: Dict):
    if "event" in variables:
        return {"m": variables["event"]}
    elif "events" in variables:
        return variables["events"]
    return {}


def _collect_extra_vars(
    variables: Dict, user_extra_vars: Dict, ruleset: str, rule: str
):
    extra_vars = user_extra_vars.copy() if user_extra_vars else {}
    eda_vars = dict(ruleset=ruleset, rule=rule)
    if "events" in variables:
        eda_vars["events"] = variables["events"]
    if "event" in variables:
        eda_vars["event"] = variables["event"]
    extra_vars[KEY_EDA_VARS] = eda_vars
    return extra_vars


def _embellish_internal_event(event: Dict, method_name: str) -> Dict:
    return insert_meta(
        event, **dict(source_name=method_name, source_type="internal")
    )


def _controller_job_url(data: dict) -> str:
    if "id" in data:
        return f"{job_template_runner.host}/#/jobs/{data['id']}/details"
    return ""
