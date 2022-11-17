#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

"""
Usage:
    generate_inventory [options] <n>

Options:
    -h, --help        Show this page
    --debug            Show debug logging
    --verbose        Show verbose logging
    --local
    --python=<p>
"""
import logging
import sys

import yaml
from docopt import docopt

logger = logging.getLogger(__name__)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    parsed_args = docopt(__doc__, args)
    if parsed_args["--debug"]:
        logging.basicConfig(level=logging.DEBUG)
    elif parsed_args["--verbose"]:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.WARNING)

    inventory = dict(all=dict(hosts={}))

    for i in range(int(parsed_args["<n>"])):
        data = dict()
        if parsed_args["--local"]:
            data["ansible_connection"] = "local"
        else:
            data["ansible_host"] = "localhost"
        if parsed_args["--python"]:
            data["ansible_python_interpreter"] = parsed_args["--python"]
        inventory["all"]["hosts"][f"localhost{i}"] = data

    print(yaml.dump(inventory, default_flow_style=False))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
