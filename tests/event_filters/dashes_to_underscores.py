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
dashes_to_underscores.py: An event filter that changes dashes
in keys to underscores.

For instance, the key X-Y becomes the new key X_Y.

Arguments:
    * overwrite: Overwrite the values if there is a collision with a new key.
"""

import logging


def main(event, overwrite=True):
    logger = logging.getLogger(__name__)
    logger.info("dashes_to_underscores")
    q = []
    q.append(event)
    while q:
        o = q.pop()
        if isinstance(o, dict):
            for key in list(o.keys()):
                value = o[key]
                q.append(value)
                if "-" in key:
                    new_key = key.replace("-", "_")
                    del o[key]
                    if new_key in o and overwrite:
                        o[new_key] = value
                        logger.info("Replacing %s with %s", key, new_key)
                    elif new_key not in o:
                        o[new_key] = value
                        logger.info("Replacing %s with %s", key, new_key)

    return event
