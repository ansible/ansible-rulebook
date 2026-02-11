from __future__ import annotations

import fnmatch
from typing import Any, Optional

DOCUMENTATION = r"""
---
short_description: Filter keys out of events.
description:
  - An event filter that filters keys out of events.
    Includes override excludes.
    This is useful to exclude information from events that is not
    needed by the rule engine.
options:
  exclude_keys:
    description:
      - A list of strings or patterns to remove.
    type: list
    elements: str
    default: null
  include_keys:
    description:
      - A list of strings or patterns to keep even if it matches
        exclude_keys patterns.
    type: list
    elements: str
    default: null
notes:
  - The values in both parameters - include_keys and exclude_keys,
    must be a full path in top-to-bottom order to the keys to be
    filtered (or left-to-right order if it is given as a list),
    as shown in the examples below.
"""

EXAMPLES = r"""
- eda.builtin.generic:
    payload:
      key1:
        key2:
          f_ignore_1: 1
          f_ignore_2: 2
      key3:
        key4:
          f_use_1: 42
          f_use_2: 45
  filters:
    - eda.builtin.json_filter:
        include_keys:
          - key3
          - key4
          - f_use*
        exclude_keys: ['key1', 'key2', 'f_ignore_1']
"""


def _matches_include_keys(include_keys: list[str], string: str) -> bool:
    return any(fnmatch.fnmatch(string, pattern) for pattern in include_keys)


def _matches_exclude_keys(exclude_keys: list[str], string: str) -> bool:
    return any(fnmatch.fnmatch(string, pattern) for pattern in exclude_keys)


def _should_include(item: str, include_keys: list[str]) -> bool:
    """Check if item should be included based on include_keys."""
    return (item in include_keys) or _matches_include_keys(include_keys, item)


def _should_exclude(item: str, exclude_keys: list[str]) -> bool:
    """Check if item should be excluded based on exclude_keys."""
    return (item in exclude_keys) or _matches_exclude_keys(exclude_keys, item)


def _process_dict_keys(
    obj: dict[str, Any],
    queue: list,
    exclude_keys: list[str],
    include_keys: list[str],
) -> None:
    """Process dictionary keys for filtering."""
    # list() required: dict modified during iteration (line 85: del obj[item])
    for item in list(obj.keys()):  # NOSONAR(S7504)
        if _should_include(item, include_keys):
            queue.append(obj[item])
        elif _should_exclude(item, exclude_keys):
            del obj[item]
        else:
            queue.append(obj[item])


def main(
    event: dict[str, Any],
    exclude_keys: Optional[list[str]] = None,  # noqa: UP045
    include_keys: Optional[list[str]] = None,  # noqa: UP045
) -> dict[str, Any]:
    """Filter keys out of events."""
    exclude_keys = exclude_keys or []
    include_keys = include_keys or []

    queue = [event]
    while queue:
        obj = queue.pop()
        if isinstance(obj, dict):
            _process_dict_keys(obj, queue, exclude_keys, include_keys)

    return event
