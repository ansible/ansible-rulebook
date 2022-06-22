import durable.lang

from typing import Dict, List, Callable
import asyncio
import concurrent.futures
import ansible_runner
import shutil
import tempfile
import os
import yaml
import glob
import json
import dpath.util
import sys
import logging
import uuid
from functools import partial
from pprint import pprint
from .util import get_horizontal_rule
from .collection import split_collection_name, has_playbook, find_playbook
from .conf import settings

from typing import Optional


async def none(
    event_log, inventory: Dict, hosts: List, variables: Dict, facts: Dict, ruleset: str
):
    pass


async def debug(**kwargs):
    print(get_horizontal_rule("="))
    pprint(durable.lang.c.__dict__)
    print(get_horizontal_rule("="))
    pprint(durable.lang.get_facts(kwargs["ruleset"]))
    print(get_horizontal_rule("="))
    pprint(kwargs)
    print(get_horizontal_rule("="))
    sys.stdout.flush()


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


async def post_event(
    event_log,
    inventory: Dict,
    hosts: List,
    variables: Dict,
    facts: Dict,
    ruleset: str,
    fact: Dict,
):
    durable.lang.post(ruleset, fact)


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
        shutil.copy(name, os.path.join(temp, "project", name))
    elif has_playbook(*split_collection_name(name)):
        shutil.copy(
            find_playbook(*split_collection_name(name)),
            os.path.join(temp, "project", name),
        )
    else:
        raise Exception(f"Could not find a playbook for {name}")

    if copy_files:
        shutil.copytree(
            os.path.dirname(os.path.abspath(name)),
            os.path.join(temp, "project"),
            dirs_exist_ok=True,
        )

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
            playbook=name,
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


actions: Dict[str, Callable] = dict(
    none=none,
    debug=debug,
    print_event=print_event,
    assert_fact=assert_fact,
    retract_fact=retract_fact,
    post_event=post_event,
    run_playbook=run_playbook,
)
