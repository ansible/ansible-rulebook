from typing import Any

DOCUMENTATION = r"""
---
short_description: Change the string values to upper case
description:
  - An event filter that convert string values to uppercase.
    For instance, the value abc becomes ABC
"""

EXAMPLES = r"""
- ansible.eda.alertmanager:
    host: 0.0.0.0
    port: 5050
  filters:
    - upcase:
"""


def main(
    event: dict[str, Any],
) -> dict[str, Any]:
    """Change string values to uppercase."""
    for key, value in event.items():
        if isinstance(value, str):
            event[key] = value.upper()
    return event
