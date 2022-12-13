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
import os
import shutil
import subprocess
import tempfile
from pprint import pprint
from typing import Any, Dict, List, Union

import ansible_runner
import jinja2
import yaml


def get_horizontal_rule(character):
    try:
        return character * int(os.get_terminal_size()[0])
    except OSError:
        return character * 80


def render_string(value: str, context: Dict) -> str:
    return jinja2.Template(value, undefined=jinja2.StrictUndefined).render(
        context
    )


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
            new_value.append(render_string_or_return_value(item, context))
        return new_value
    elif isinstance(value, dict):
        new_value = value.copy()
        for key, subvalue in new_value.items():
            new_value[key] = render_string_or_return_value(subvalue, context)
        return new_value
    else:
        return value


def load_inventory(inventory_file: str) -> Any:

    with open(inventory_file) as f:
        inventory_data = yaml.safe_load(f.read())
    return inventory_data


def json_count(data):
    s = 0
    q = []
    q.append(data)
    while q:
        o = q.pop()
        if isinstance(o, dict):
            s += len(o)
            if len(o) > 255:
                pprint(data)
                raise Exception(
                    f"Only 255 values supported per dictionary found {len(o)}"
                )
            if s > 255:
                pprint(data)
                raise Exception(
                    f"Only 255 values supported per dictionary found {s}"
                )
            for i in o.values():
                q.append(i)


def collect_ansible_facts(inventory: Dict) -> List[Dict]:
    hosts_facts = []
    with tempfile.TemporaryDirectory(
        prefix="gather_facts"
    ) as private_data_dir:
        os.mkdir(os.path.join(private_data_dir, "inventory"))
        with open(
            os.path.join(private_data_dir, "inventory", "hosts"), "w"
        ) as f:
            f.write(yaml.dump(inventory))

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


def get_java_version() -> str:
    exec_path = shutil.which("java")
    if not exec_path:
        return "Java executable not found."
    try:
        result = subprocess.run(
            [exec_path, "--version"], capture_output=True, check=True
        )
    except subprocess.CalledProcessError as exc:
        print(exc)
        return "Java error"

    return result.stdout.splitlines()[0].decode()
