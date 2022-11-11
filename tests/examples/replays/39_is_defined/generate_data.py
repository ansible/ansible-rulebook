#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json

for i in range(10):
    data = {}

    with open(f"{i:02}.json", "w") as f:
        data = dict(root=dict(nested=dict(i=i)))
        f.write(json.dumps(data, sort_keys=True, indent=4))
