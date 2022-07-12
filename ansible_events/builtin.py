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
from typing import Callable, Dict, List, Optional

import ansible_runner
import dpath.util
import durable.lang
import yaml

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
    pprint(durable.lang.c.__dict__)
    print(get_horizontal_rule("="))
    print("facts:")
    pprint(durable.lang.get_facts(kwargs["ruleset"]))
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
    var_root: Optional[str] = None,
    pretty: Optional[str] = None,
):
    print_fn: Callable = print
    if pretty:
        print_fn = pprint
    if var_root:
        print_fn(dpath.util.get(variables["event"], var_root, separator="."))
    else:
        print_fn(variables["event"])
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
    durable.lang.assert_fact(ruleset, fact)
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
    durable.lang.retract_fact(ruleset, fact)
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
    durable.lang.post(ruleset, event)
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
    var_root: Optional[str] = None,
    copy_files: Optional[bool] = False,
    **kwargs,
):
    logger = logging.getLogger()

    temp = tempfile.mkdtemp(prefix="run_playbook")
    logger.debug(f"temp {temp}")
    logger.debug(f"variables {variables}")
    logger.debug(f"facts {facts}")

    variables["facts"] = facts

    if var_root:
        o = dpath.util.get(variables["event"], var_root, separator=".")
        variables["event"] = o

    os.mkdir(os.path.join(temp, "env"))
    with open(os.path.join(temp, "env", "extravars"), "w") as f:
        f.write(yaml.dump(variables))
    os.mkdir(os.path.join(temp, "inventory"))
    with open(os.path.join(temp, "inventory", "hosts"), "w") as f:
        f.write(yaml.dump(inventory))
    os.mkdir(os.path.join(temp, "project"))

    if os.path.exists(name):
        playbook_name = os.path.basename(name)
        shutil.copy(name, os.path.join(temp, "project", playbook_name))
        if copy_files:
            shutil.copytree(
                os.path.dirname(os.path.abspath(name)),
                os.path.join(temp, "project"),
                dirs_exist_ok=True,
            )
    elif has_playbook(*split_collection_name(name)):
        playbook_name = name
        shutil.copy(
            find_playbook(*split_collection_name(name)),
            os.path.join(temp, "project", name),
        )
    else:
        raise Exception(f"Could not find a playbook for {name}")

    host_limit = ",".join(hosts)

    job_id = str(uuid.uuid4())

    await event_log.put(
        dict(type="Job", job_id=job_id, ansible_events_id=settings.identifier)
    )

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
            playbook=playbook_name,
            private_data_dir=temp,
            limit=host_limit,
            verbosity=verbosity,
            event_handler=event_callback,
        ),
    )

    if assert_facts or post_events:
        logger.debug("assert_facts")
        for host_facts in glob.glob(
            os.path.join(temp, "artifacts", "*", "fact_cache", "*")
        ):
            with open(host_facts) as f:
                fact = json.loads(f.read())
            logger.debug(f"fact {fact}")
            if assert_facts:
                durable.lang.assert_fact(ruleset, fact)
            if post_events:
                durable.lang.post(ruleset, fact)
    await event_log.put(dict(type="Action", action="run_playbook"))


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
    shutdown=shutdown,
)
