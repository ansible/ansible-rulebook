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

import json

DEPTH = 3
WIDTH = 3


def recursive(o, depth):
    if depth == 0:
        for i in range(WIDTH):
            o[f"leaf_{i}"] = i
    else:
        for i in range(WIDTH):
            new_o = dict()
            o[f"branch_{i}"] = new_o
            recursive(new_o, depth - 1)


for i in range(1):
    data = {}

    with open(f"{i:02}.json", "w") as f:
        data = {}
        recursive(data, DEPTH)
        f.write(json.dumps(data, sort_keys=True, indent=4))
