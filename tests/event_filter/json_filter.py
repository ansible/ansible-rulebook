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
json_filter.py:   An event filter that filters keys out of events.

Includes override excludes.

This is useful to exclude information from events that is unneeded
by the rule engine.

Arguments:
    * exclude_keys = a list of strings or patterns to remove
    * include_keys = a list of strings or patterns to keep even if it matches
        exclude_keys patterns.
"""


import fnmatch


def matches_include_keys(include_keys, s):
    for pattern in include_keys:
        if fnmatch.fnmatch(s, pattern):
            return True
    return False


def matches_exclude_keys(exclude_keys, s):
    for pattern in exclude_keys:
        if fnmatch.fnmatch(s, pattern):
            return True
    return False


def main(event, exclude_keys=None, include_keys=None):
    exclude_keys = exclude_keys or []
    include_keys = include_keys or []
    q = []
    q.append(event)
    while q:
        o = q.pop()
        if isinstance(o, dict):
            for i in list(o.keys()):
                if i in include_keys:
                    q.append(o[i])
                elif matches_include_keys(include_keys, i):
                    q.append(o[i])
                elif i in exclude_keys:
                    del o[i]
                elif matches_exclude_keys(exclude_keys, i):
                    del o[i]
                else:
                    q.append(o[i])

    return event
