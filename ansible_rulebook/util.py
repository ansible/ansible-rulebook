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
import glob
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import typing
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import ansible_runner
import jinja2
from jinja2.nativetypes import NativeTemplate
from packaging import version
from packaging.version import InvalidVersion

from ansible_rulebook import terminal
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import (
    InvalidFilterNameException,
    InventoryNotFound,
)

logger = logging.getLogger(__name__)


EDA_BUILTIN_FILTER_PREFIX = "eda.builtin."


def render_string(value: str, context: Dict) -> str:
    if "{{" in value and "}}" in value:
        return NativeTemplate(value, undefined=jinja2.StrictUndefined).render(
            context
        )

    return value


def render_string_or_return_value(value: Any, context: Dict) -> Any:
    if isinstance(value, str):
        return render_string(value, context)
    return value


def substitute_variables(
    value: Union[str, int, Dict, List], context: Dict
) -> Union[str, int, Dict, List]:
    if isinstance(value, str):
        return render_string_or_return_value(value, context)
    elif isinstance(value, list):
        new_value = []
        for item in value:
            new_value.append(substitute_variables(item, context))
        return new_value
    elif isinstance(value, dict):
        new_value = value.copy()
        for key, subvalue in new_value.items():
            new_value[key] = substitute_variables(subvalue, context)
        return new_value
    else:
        return value


def collect_ansible_facts(inventory: str) -> List[Dict]:
    hosts_facts = []
    with tempfile.TemporaryDirectory(
        prefix="gather_facts"
    ) as private_data_dir:
        inventory_dir = os.path.join(private_data_dir, "inventory")
        os.mkdir(inventory_dir)
        create_inventory(inventory_dir, inventory)

        r = ansible_runner.run(
            private_data_dir=private_data_dir,
            module="ansible.builtin.setup",
            host_pattern="*",
        )
        if r.rc != 0:
            raise Exception(
                "Error collecting facts in ansible_runner.run "
                f"rc={r.rc}, status={r.status}"
            )

        host_path = os.path.join(
            private_data_dir, "artifacts", "*", "fact_cache", "*"
        )
        for host_file in glob.glob(host_path):
            hostname = os.path.basename(host_file)
            with open(host_file) as f:
                data = json.load(f)
            data["meta"] = dict(hosts=hostname)
            hosts_facts.append(data)

    return hosts_facts


def run_java_settings(exec_path: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [exec_path, "-XshowSettings:properties", "-version"],
        check=True,
        text=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )


def get_java_home() -> typing.Optional[str]:
    """
    Get the java home path. It tries to get the path
    from the default java installation if JAVA_HOME is not set.
    If is not possible to find the java home path, it returns None.
    """

    # if java_home is set, return it
    java_home = os.environ.get("JAVA_HOME", None)
    if java_home:
        return java_home

    # if default java executable is not found, return None
    exec_path = shutil.which("java")
    if not exec_path:
        return None

    # try to get the java home path from the default java executable
    try:
        result = run_java_settings(exec_path)
    except subprocess.CalledProcessError:
        return None

    for line in result.stderr.splitlines():
        if "java.home" in line:
            return line.split("=")[-1].strip()

    return None


def get_java_version() -> str:
    java_home = get_java_home()

    if not java_home:
        return "Java executable not found."

    exec_path = f"{java_home}/bin/java"
    try:
        result = run_java_settings(exec_path)
    except subprocess.CalledProcessError as exc:
        logger.error("java executable failed: %s", exc)
        return "Java error"
    for line in result.stderr.splitlines():
        if "java.version" in line:
            return line.split("=")[-1].strip()

    return "Java version not found."


def check_jvm():
    """
    Ensures that a valid JVM is properly installed
    """
    java_home = get_java_home()
    if not java_home:
        terminal.Display.instance().banner(
            "util",
            "Java executable or JAVA_HOME environment variable not found."
            "Please install a valid JVM.",
            file=sys.stderr,
        )
        sys.exit(1)

    java_version = get_java_version()

    try:
        # Keep only "x.y.z" section
        clean_version = re.match(r"(\d+\.\d+\.\d+).*", java_version)
        if clean_version:
            java_version = clean_version.groups()[0]
        if version.parse(java_version) < version.parse("17"):
            terminal.Display.instance().banner(
                "util",
                "The minimum supported Java version is 17. "
                f"Found version: {java_version}",
                file=sys.stderr,
            )
            sys.exit(1)
    except InvalidVersion as exinfo:
        terminal.Display.instance().banner(
            "util: exception",
            exinfo,
            file=sys.stderr,
        )
        sys.exit(1)


def has_builtin_filter(name: str) -> bool:
    return _builtin_filter_path(name)[0]


def find_builtin_filter(name: str) -> Optional[str]:
    found, path = _builtin_filter_path(name)
    if found:
        return path
    return None


def run_at() -> str:
    return f"{datetime.now(timezone.utc).isoformat()}".replace("+00:00", "Z")


async def send_session_stats(event_log: asyncio.Queue, stats: Dict):
    await event_log.put(
        dict(
            type="SessionStats",
            activation_id=settings.identifier,
            activation_instance_id=settings.identifier,
            stats=stats,
            reported_at=run_at(),
        )
    )


def create_inventory(runner_inventory_dir: str, inventory: str) -> None:
    if os.path.isfile(inventory):
        shutil.copy(os.path.abspath(inventory), runner_inventory_dir)
    elif os.path.exists(inventory):
        shutil.copytree(
            os.path.abspath(inventory),
            runner_inventory_dir,
            dirs_exist_ok=True,
        )
    else:
        raise InventoryNotFound(f"Inventory {inventory} not found")


def _builtin_filter_path(name: str) -> Tuple[bool, str]:
    if not name.startswith(EDA_BUILTIN_FILTER_PREFIX):
        return False, ""
    filter_name = name.split(".")[-1]

    if not filter_name:
        raise InvalidFilterNameException(name)

    dirname = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(dirname, "event_filter", filter_name + ".py")
    return os.path.exists(path), path


# TODO(alex): This function should be removed after the
# controller templates are refactored to deduplicate code
def process_controller_host_limit(
    job_args: dict,
    parent_hosts: list[str],
) -> str:
    if "limit" in job_args:
        if isinstance(job_args["limit"], list):
            return ",".join(job_args["limit"])
        return str(job_args["limit"])
    return ",".join(parent_hosts)


def ensure_trailing_slash(url: str) -> str:
    if not url.endswith("/"):
        return url + "/"
    return url
