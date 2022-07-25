#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

MAX_ATTRIBUTES = 250


for i in range(1):
    data = {}

    with open(f"{i:02}.json", "w") as f:
        data = {}
        for j in range(MAX_ATTRIBUTES):
            data[f"attr_{j}"] = j
        f.write(json.dumps(data, sort_keys=True, indent=4))
