#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
