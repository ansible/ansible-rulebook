"""
template.py

An ansible-rulebook event source plugin template.
"""
import asyncio
from typing import Any, Dict


DOCUMENTATION = r"""
---
short_description: A template event source plugin
description:
  - An ansible-rulebook event source plugin template.
  - This plugin generates events at a specified interval.
  - Use this as a starting point for developing custom event source plugins.
version_added: "1.0.0"
options:
  delay:
    description:
      - Number of seconds to wait between events.
    type: int
    default: 0
    required: false
  message:
    description:
      - The message to include in generated events.
    type: str
    default: "hello world"
    required: false
notes:
  - This is a template plugin for demonstration purposes.
"""

EXAMPLES = r"""
# Simple example with minimal configuration
- name: Example rulebook using template plugin
  hosts: all
  sources:
    - name: template_source
      template:
        delay: 5
        message: "custom message"

# Example with variables
- name: Using variables
  hosts: all
  sources:
    - name: template_source
      template:
        delay: "{{ event_delay }}"
        message: "{{ event_message }}"
"""


async def main(queue: asyncio.Queue, args: Dict[str, Any]):
    """
    Main plugin entrypoint.

    Args:
        queue: An asyncio queue for sending events to ansible-rulebook
        args: Plugin arguments from the rulebook
    """
    delay = args.get("delay", 0)
    message = args.get("message", "hello world")

    while True:
        await queue.put(dict(template=dict(msg=message)))
        await asyncio.sleep(delay)


if __name__ == "__main__":
    # Test mode - allows standalone execution for development/testing
    class MockQueue:
        async def put(self, event):
            print(event)

    mock_arguments = dict(delay=1, message="test message")
    asyncio.run(main(MockQueue(), mock_arguments))
