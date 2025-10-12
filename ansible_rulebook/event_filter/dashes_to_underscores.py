import multiprocessing as mp
from typing import Any

DOCUMENTATION = r"""
---
short_description: Change dashes to underscores.
description:
  - An event filter that changes dashes in keys to underscores.
    For instance, the key X-Y becomes the new key X_Y.
options:
  overwrite:
    description:
      - Overwrite the values if there is a collision with a new key.
    type: bool
    default: true
"""

EXAMPLES = r"""
- ansible.eda.alertmanager:
    host: 0.0.0.0
    port: 5050
  filters:
    - eda.builtin.dashes_to_underscores:
        overwrite: false
"""


def _should_replace_key(obj: dict, new_key: str, overwrite: bool) -> bool:
    """Check if the new key should replace the old one."""
    return (new_key in obj and overwrite) or (new_key not in obj)


def _process_dict(obj: dict, queue: list, logger, overwrite: bool) -> None:
    """Process dictionary keys, replacing dashes with underscores."""
    # list() required: dict modified during iteration (line 40: del obj[key])
    for key in list(obj.keys()):  # NOSONAR(S7504)
        value = obj[key]
        queue.append(value)
        if "-" in key:
            new_key = key.replace("-", "_")
            del obj[key]
            if _should_replace_key(obj, new_key, overwrite):
                obj[new_key] = value
                logger.info("Replacing %s with %s", key, new_key)


def main(
    event: dict[str, Any],
    overwrite: bool = True,  # noqa: FBT001, FBT002
) -> dict[str, Any]:
    """Change dashes in keys to underscores."""
    logger = mp.get_logger()
    logger.info("dashes_to_underscores")
    queue = [event]
    while queue:
        obj = queue.pop()
        if isinstance(obj, dict):
            _process_dict(obj, queue, logger, overwrite)
        elif isinstance(obj, list):
            queue.extend(obj)

    return event
