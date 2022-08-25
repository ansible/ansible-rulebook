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
from functools import partial
from pprint import pprint
from typing import Callable, Dict, List, Optional, Union

import ansible_runner
import dpath.util
import yaml

if os.environ.get("RULES_ENGINE", "durable_rules") == "drools":
    from ansible_events.drools.vendor import lang
else:
    from durable import lang

from .collection import find_playbook, has_playbook, split_collection_name
from .conf import settings
from .exception import ShutdownException
from .util import get_horizontal_rule


async def none(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
):
    await event_log.put(dict(type="Action", action="noop"))


async def debug(event_log, **kwargs):
    print(get_horizontal_rule("="))
    print("context:")
    pprint(lang.c.__dict__)
    print(get_horizontal_rule("="))
    print("facts:")
    pprint(lang.get_facts(kwargs["ruleset"]))
    print(get_horizontal_rule("="))
    print("kwargs:")
    pprint(kwargs)
    print(get_horizontal_rule("="))
    sys.stdout.flush()
    await event_log.put(dict(type="Action", action="debug"))


async def print_event(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    var_root: Union[str, Dict, None] = None,
    pretty: Optional[str] = None,
):
    print_fn: Callable = print
    if pretty:
        print_fn = pprint

    if var_root:
        update_variables(variables, var_root)

    var_name = "event"
    if "events" in variables:
        var_name = "events"

    print_fn(variables[var_name])
    sys.stdout.flush()
    await event_log.put(dict(type="Action", action="print_event"))


async def assert_fact(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    fact: Dict,
):
    logger = logging.getLogger()
    logger.debug(f"assert_fact {ruleset} {fact}")
    lang.assert_fact(ruleset, fact)
    await event_log.put(dict(type="Action", action="assert_fact"))


async def retract_fact(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    fact: Dict,
):
    lang.retract_fact(ruleset, fact)
    await event_log.put(dict(type="Action", action="retract_fact"))


async def post_event(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    event: Dict,
):
    lang.post(ruleset, event)
    await event_log.put(dict(type="Action", action="post_event"))


async def run_playbook(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    name: str,
    assert_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
    verbosity: int = 0,
    var_root: Union[str, Dict, None] = None,
    copy_files: Optional[bool] = False,
    json_mode: Optional[bool] = False,
    retries: Optional[int] = 0,
    retry: Optional[bool] = False,
    delay: Optional[int] = 0,
    **kwargs,
):
    logger = logging.getLogger()

    temp, playbook_name, job_id = await pre_process_runner(
        event_log,
        inventory,
        variables,
        facts,
        ruleset,
        name,
        "run_playbook",
        var_root,
        copy_files,
        True,
        **kwargs,
    )
    logger.info("Calling Ansible runner")

    if retry:
        retries = max(retries, 1)
    for i in range(retries + 1):
        if i > 0 and delay > 0:
            await asyncio.sleep(delay)
        await call_runner(
            event_log,
            job_id,
            temp,
            dict(playbook=playbook_name),
            hosts,
            verbosity,
            json_mode,
        )
        if get_status(temp) != "failed":
            break

    await post_process_runner(
        event_log, temp, ruleset, "run_playbook", assert_facts, post_events
    )


async def run_module(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    name: str,
    assert_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
    verbosity: int = 0,
    var_root: Union[str, Dict, None] = None,
    copy_files: Optional[bool] = False,
    json_mode: Optional[bool] = False,
    module_args: Union[Dict, None] = None,
    retries: Optional[int] = 0,
    retry: Optional[bool] = False,
    delay: Optional[int] = 0,
    **kwargs,
):
    logger = logging.getLogger()

    temp, module_name, job_id = await pre_process_runner(
        event_log,
        inventory,
        variables,
        facts,
        ruleset,
        name,
        "run_module",
        var_root,
        copy_files,
        False,
        **kwargs,
    )
    logger.info("Calling Ansible runner")
    module_args_str = ""
    if module_args:
        for k, v in module_args.items():
            if len(module_args_str) > 0:
                module_args_str += " "
            module_args_str += f'{k}="{v}"'

    if retry:
        retries = max(retries, 1)
    for i in range(retries + 1):
        if i > 0 and delay > 0:
            await asyncio.sleep(delay)
        await call_runner(
            event_log,
            job_id,
            temp,
            dict(
                module=module_name,
                host_pattern=",".join(hosts),
                module_args=module_args_str,
            ),
            hosts,
            verbosity,
            json_mode,
        )
        if get_status(temp) != "failed":
            break

    await post_process_runner(
        event_log, temp, ruleset, "run_module", assert_facts, post_events
    )


async def call_runner(
    event_log,
    job_id: str,
    private_data_dir: str,
    runner_args: Dict,
    hosts: List,
    verbosity: int = 0,
    json_mode: Optional[bool] = False,
):

    host_limit = ",".join(hosts)

    def event_callback(event, *args, **kwargs):
        event["job_id"] = job_id
        event["ansible_events_id"] = settings.identifier
        event_log.put_nowait(dict(type="AnsibleEvent", event=event))

    loop = asyncio.get_running_loop()
    task_pool = concurrent.futures.ThreadPoolExecutor()
    await loop.run_in_executor(
        task_pool,
        partial(
            ansible_runner.run,
            private_data_dir=private_data_dir,
            limit=host_limit,
            verbosity=verbosity,
            event_handler=event_callback,
            json_mode=json_mode,
            **runner_args,
        ),
    )


async def pre_process_runner(
    event_log,
    inventory: Dict,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    name: str,
    action: str,
    var_root: Union[str, Dict, None] = None,
    copy_files: Optional[bool] = False,
    check_files: Optional[bool] = True,
    **kwargs,
):

    logger = logging.getLogger()
    private_data_dir = tempfile.mkdtemp(prefix=action)
    logger.debug(f"private data dir {private_data_dir}")
    logger.debug(f"variables {variables}")
    logger.debug(f"facts {facts}")

    variables["facts"] = facts
    for k, v in kwargs.items():
        variables[k] = v

    if var_root:
        update_variables(variables, var_root)

    playbook_name = name
    if True:
        os.mkdir(os.path.join(private_data_dir, "env"))
        with open(
            os.path.join(private_data_dir, "env", "extravars"), "w"
        ) as f:
            f.write(yaml.dump(variables))
        os.mkdir(os.path.join(private_data_dir, "inventory"))
        with open(
            os.path.join(private_data_dir, "inventory", "hosts"), "w"
        ) as f:
            f.write(yaml.dump(inventory))
        os.mkdir(os.path.join(private_data_dir, "project"))

    if check_files:
        if os.path.exists(name):
            playbook_name = os.path.basename(name)
            shutil.copy(
                name, os.path.join(private_data_dir, "project", playbook_name)
            )
            if copy_files:
                shutil.copytree(
                    os.path.dirname(os.path.abspath(name)),
                    os.path.join(private_data_dir, "project"),
                    dirs_exist_ok=True,
                )
        elif has_playbook(*split_collection_name(name)):
            playbook_name = name
            shutil.copy(
                find_playbook(*split_collection_name(name)),
                os.path.join(private_data_dir, "project", name),
            )
        else:
            raise Exception(f"Could not find a playbook for {name}")

    job_id = str(uuid.uuid4())

    await event_log.put(
        dict(type="Job", job_id=job_id, ansible_events_id=settings.identifier)
    )
    return (private_data_dir, playbook_name, job_id)


async def post_process_runner(
    event_log,
    private_data_dir: str,
    ruleset: str,
    action: str,
    assert_facts: Optional[bool] = None,
    post_events: Optional[bool] = None,
):

    logger = logging.getLogger()
    for rc_file in glob.glob(
        os.path.join(private_data_dir, "artifacts", "*", "rc")
    ):
        with open(rc_file, "r") as f:
            rc = int(f.read())

    status = get_status(private_data_dir)

    if assert_facts or post_events:
        logger.debug("assert_facts")
        for host_facts in glob.glob(
            os.path.join(private_data_dir, "artifacts", "*", "fact_cache", "*")
        ):
            with open(host_facts) as f:
                fact = json.loads(f.read())
            logger.debug(f"fact {fact}")
            if assert_facts:
                lang.assert_fact(ruleset, fact)
            if post_events:
                lang.post(ruleset, fact)

    await event_log.put(
        dict(type="Action", action=action, rc=rc, status=status)
    )


async def shutdown(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
):
    await event_log.put(dict(type="Action", action="shutdown"))
    raise ShutdownException()


actions: Dict[str, Callable] = dict(
    none=none,
    debug=debug,
    print_event=print_event,
    assert_fact=assert_fact,
    retract_fact=retract_fact,
    post_event=post_event,
    run_playbook=run_playbook,
    run_module=run_module,
    shutdown=shutdown,
)


def update_variables(variables: Dict, var_root: Union[str, Dict]):
    var_roots = {var_root: var_root} if isinstance(var_root, str) else var_root
    if "event" in variables:
        for key, _new_key in var_roots.items():
            new_value = dpath.util.get(
                variables["event"], key, separator=".", default=None
            )
            if new_value:
                variables["event"] = new_value
                break
    elif "events" in variables:
        for _k, v in variables["events"].items():
            for old_key, new_key in var_roots.items():
                new_value = dpath.util.get(
                    v, old_key, separator=".", default=None
                )
                if new_value:
                    variables["events"][new_key] = new_value
                    break


def get_status(private_data_dir: str):
    status_files = glob.glob(
        os.path.join(private_data_dir, "artifacts", "*", "status")
    )
    status_files.sort(key=os.path.getmtime, reverse=True)
    with open(status_files[0], "r") as f:
        status = f.read()
    return status
