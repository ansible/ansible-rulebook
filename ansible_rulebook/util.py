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

import glob
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import typing
from typing import Any, Dict, List, Union

import ansible_runner
import jinja2
from jinja2.nativetypes import NativeTemplate
from packaging import version

logger = logging.getLogger(__name__)


def get_horizontal_rule(character):
    try:
        return character * int(os.get_terminal_size()[0])
    except OSError:
        return character * 80


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


def load_inventory(inventory_file: str) -> Any:

    with open(inventory_file) as f:
        inventory_data = f.read()
    return inventory_data


def collect_ansible_facts(inventory: str) -> List[Dict]:
    hosts_facts = []
    with tempfile.TemporaryDirectory(
        prefix="gather_facts"
    ) as private_data_dir:
        os.mkdir(os.path.join(private_data_dir, "inventory"))
        with open(
            os.path.join(private_data_dir, "inventory", "hosts"), "w"
        ) as f:
            f.write(inventory)

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
        print(
            "Java executable or JAVA_HOME environment variable not found."
            "Please install a valid JVM.",
            file=sys.stderr,
        )
        sys.exit(1)

    java_version = get_java_version()
    if version.parse(java_version) < version.parse("17"):
        print(
            "The minimum supported Java version is 17. "
            f"Found version: {java_version}",
            file=sys.stderr,
        )
        sys.exit(1)
