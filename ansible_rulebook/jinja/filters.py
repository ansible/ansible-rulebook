#  Copyright 2026 Red Hat, Inc.
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
import os
import re
from typing import Any, Callable, Dict


def regex_replace(
    value: Any,
    pattern: str,
    replacement: str,
    count: int = 0,
    ignore_case: bool = False,
    multiline: bool = False,
    mandatory_count: int = 0,
) -> str:
    """
    Perform a regex substitution with optional strictness via mandatory_count.
    """
    if value is None:
        return ""

    flags: int = 0
    if ignore_case:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE

    # re.subn returns a Tuple[str, int]
    new_value: str
    actual_count: int
    new_value, actual_count = re.subn(
        pattern, replacement, str(value), count=count, flags=flags
    )

    if mandatory_count > 0 and actual_count < mandatory_count:
        raise ValueError(
            "Regex replace failed: expected at least "
            f"{mandatory_count} replacements, "
            f"but only found {actual_count}."
        )

    return new_value


def basename(
    value: Any,
) -> str:
    """
    Get the basename from a file path
    To get the last name of a file path, like 'cert.pem'
    out of '/etc/certs/cert.pem'.
    """
    if value is None:
        return ""

    return os.path.basename(value)


def dirname(
    value: Any,
) -> str:
    """
    Get the dirname from a file path
    To get the dirname of a file path, like '/etc/certs'
    out of '/etc/certs/cert.pem'.
    if only the filename is passed in dirname will be
    empty string
    """
    if value is None:
        return ""

    return os.path.dirname(value)


def normpath(
    value: Any,
) -> str:
    """
    Get the normalized path from a file path
    Extra slashes get dropped and get normalized
    """
    if value is None:
        return ""

    return os.path.normpath(value)


def bool_filter(
    value: Any,
) -> bool:
    """
    Convert a string to a boolean value.

    Returns True for: 'true', 'yes', '1', 'on' (case-insensitive)
    Returns False for: 'false', 'no', '0', 'off', '' (case-insensitive)
    For other types, returns the Python bool() evaluation.
    """
    if value is None:
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lower_value = value.lower().strip()
        if lower_value in ("true", "yes", "1", "on"):
            return True
        elif lower_value in ("false", "no", "0", "off", ""):
            return False
        else:
            # For any other string, raise an error for clarity
            raise ValueError(
                f"Cannot convert '{value}' to boolean. "
                "Expected: true/false, yes/no, 1/0, on/off"
            )

    # For other types (int, list, etc.), use Python's bool()
    return bool(value)


FILTERS: Dict[str, Callable[..., str]] = {
    "regex_replace": regex_replace,
    "basename": basename,
    "dirname": dirname,
    "normpath": normpath,
    "bool": bool_filter,
}
