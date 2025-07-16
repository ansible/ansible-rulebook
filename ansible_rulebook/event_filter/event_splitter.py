#  Copyright 2025 Red Hat, Inc.
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
import copy
import multiprocessing as mp
from typing import Any, Optional

import dpath

DOCUMENTATION = r"""
---
short_description: Split an event payload to multiple events based on a key
description: |
  - An event filter that allows users to split an event payload which has
    several events bundled inside.
  - For instance, Prometheus and Big Panda send in a collection of events
    If we know the key name that stores this array of events we can have
    the event filter slit the payload into individual events.
    If the splitter key doesn't exist the payload is left intact
  - Optionally we can include other attributes from the payload into every
    event
  - Optionally we can add additional static data into each event
options:
  splitter_key:
    description:
      - This mandatory field specifies the key in the payload
      - that has an array (list) of events
      - You can use dotted notation to specify the key path.
      - Example splitter_key: topkey1.key2.key3
    type: str
  attributes_key_map:
    description:
      - This optional field can be used to augment the event with data
      - from the parent nodes in the event payload. The map is defined
      - as a dictionary it contains the attribute name to add in the event and
      - the value is the key path from the event payload.
      - You can use dotted notation to specify the key path.
      - Example
      -    my_attr: payload.id
      -    my_zone: payload.zone
    type: dict
  extras:
    description:
      - This optional field can be used to augment the event with some
      - static data defined as key:value object
      - Example
      -    my_region: us-east
      -    my_cost_center: us-east
    type: dict
  raise_error:
    description:
      - This optional field can be used to raise an error and stopping
      - the rulebook if the splitter_key is missing.
      - Example
      -    raise_error: true
    type: bool
    default: false
"""

EXAMPLES = r"""
- ansible.eda.alertmanager:
    host: 0.0.0.0
    port: 5050
  filters:
    eda.builtin.event_splitter:
      splitter_key: incident.alerts

- ansible.eda.alertmanager:
    host: 0.0.0.0
    port: 5050
  filters:
    eda.builtin.event_splitter:
      splitter_key: incident.alerts
      attributes_key_map:
         id: incident.id
         active: incident.active
      extras:
         region: us-east
      raise_error: true
"""


def main(
    event: dict[str, Any],
    splitter_key: str,
    attributes_key_map: Optional[dict[str, Any]] = None,
    extras: Optional[dict[str, Any]] = None,
    raise_error: bool = False,
) -> list[dict[str, Any]]:
    """Split event into an array of events."""
    logger = mp.get_logger()
    try:
        event_array = dpath.get(event, splitter_key, separator=".")
    except KeyError:
        if raise_error:
            logger.error(f"Key {splitter_key} doesn't exist terminating")
            raise
        logger.warning(
            f"Key {splitter_key} doesn't exist leaving event intact"
        )
        return [event]

    results = []
    additional_dict = {}

    if isinstance(attributes_key_map, dict):
        for key, value in attributes_key_map.items():
            try:
                additional_dict[key] = dpath.get(event, value, separator=".")
            except KeyError:
                logger.warning(
                    "Attribute Key Map %s missing, skipping.", value
                )

    if isinstance(extras, dict):
        for key, value in extras.items():
            additional_dict[key] = value

    for item in event_array:
        single_event = copy.deepcopy(item)
        if additional_dict:
            single_event.update(additional_dict)
        results.append(single_event)

    logger.debug(
        f"Splitting event payload into {len(results)} individual events"
    )
    return results
