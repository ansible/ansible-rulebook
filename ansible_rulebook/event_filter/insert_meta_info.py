"""
insert_meta_info.py

An ansible-rulebook event filter that sets the source name and type
in the event meta field. A source name is needed to track where the
event originated from. If the event meta already has a source.name
or source.type field specified it will be ignored. This filter is
automatically added to every source. This filter also adds the
received_at iso8601 UTC datetime stamp to every event.

Arguments:
          source_name
          source_type
Example:
    - eda.builtin.insert_meta_info

"""

import uuid
from datetime import datetime, timezone
from typing import Any, Dict


def main(
    event: Dict[str, Any],
    source_name: str,
    source_type: str,
) -> Dict[str, Any]:
    if "meta" not in event:
        event["meta"] = {}

    if "source" not in event["meta"]:
        event["meta"]["source"] = {}

    if "name" not in event["meta"]["source"]:
        event["meta"]["source"]["name"] = source_name

    if "type" not in event["meta"]["source"]:
        event["meta"]["source"]["type"] = source_type

    if "received_at" not in event["meta"]:
        event["meta"]["received_at"] = _received_at()

    if "uuid" not in event["meta"]:
        event["meta"]["uuid"] = str(uuid.uuid4())

    return event


def _received_at() -> str:
    return f"{datetime.now(timezone.utc).isoformat()}".replace("+00:00", "Z")
