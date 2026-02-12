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

import logging
import os
import subprocess
from functools import lru_cache
from typing import Optional

import yaml

from ansible_rulebook import terminal
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import RulebookNotFoundException
from ansible_rulebook.vault import has_vaulted_str

EDA_PATH_PREFIX = "extensions/eda"
EVENT_SOURCE_OBJ_TYPE = "event_source"
EVENT_SOURCE_FILTER_OBJ_TYPE = "event_filter"
EDA_RUNTIME_FILE = "eda_runtime.yml"

EDA_FILTER_PATHS = [
    f"{EDA_PATH_PREFIX}/plugins/event_filter",
    f"{EDA_PATH_PREFIX}/plugins/event_filters",
    "plugins/event_filter",
]

EDA_SOURCE_PATHS = [
    f"{EDA_PATH_PREFIX}/plugins/event_source",
    f"{EDA_PATH_PREFIX}/plugins/event_sources",
    "plugins/event_source",
]

EDA_PLAYBOOKS_PATHS = [".", "playbooks"]

EDA_YAML_EXTENSIONS = [".yml", ".yaml"]

LEGACY_FILTER_MAPPING = {
    "ansible.eda.dashes_to_underscores": (
        "ansible.builtin.dashes_to_underscores"
    ),
    "ansible.eda.json_filter": "eda.builtin.json_filter",
    "ansible.eda.normalize_keys": "eda.builtin.normalize_keys",
    "ansible.eda.insert_hosts_to_meta": "eda.builtin.insert_hosts_to_meta",
    "ansible.eda.noop": "eda.builtin.noop",
}

LEGACY_SOURCE_MAPPING = {
    "ansible.eda.pg_listener": "eda.builtin.pg_listener",
    "ansible.eda.generic": "eda.builtin.generic",
    "ansible.eda.range": "eda.builtin.range",
}

logger = logging.getLogger(__name__)


def split_collection_name(collection_resource):
    collection, _, resource = collection_resource.rpartition(".")
    return collection, resource


@lru_cache
def find_collection(name):
    if settings.ansible_galaxy_path is None:
        raise Exception("ansible-galaxy is not installed")
    try:
        env = os.environ.copy()
        env["ANSIBLE_LOCAL_TEMP"] = "/tmp"
        output = subprocess.check_output(
            [settings.ansible_galaxy_path, "collection", "list", name],
            stderr=subprocess.STDOUT,
            env=env,
        )
    except subprocess.CalledProcessError as e:
        logger.error("Error listing collections: %s", e.output)
        return None
    output = output.decode()
    parts = name.split(".")
    for line in output.splitlines():
        if line.startswith("# "):
            location = line[2:]
            location = os.path.join(location, *parts)
            if os.path.exists(location):
                return location
    return None


def has_object(collection, name, object_types, extensions):
    if find_collection(collection) is None:
        return False

    if not isinstance(extensions, list):
        extensions = [extensions]

    for object_type in object_types:
        for extension in extensions:
            if os.path.exists(
                os.path.join(find_collection(collection), object_type, name)
                + extension
            ):
                return True
    return False


@lru_cache
def _load_eda_runtime(collection_name: str) -> dict:
    """Load and cache the eda_runtime.yml file for a collection.

    This function is cached to avoid repeatedly reading and parsing
    the YAML file for the same collection.

    Args:
        collection_name: Name of the collection (e.g., 'ansible.eda')

    Returns:
        Dictionary containing the runtime data, or empty dict if not found
    """
    path = find_collection(collection_name)
    if path is None:
        return {}

    eda_runtime_yml = os.path.join(
        path, "extensions", "eda", "eda_runtime.yml"
    )

    if not os.path.exists(eda_runtime_yml):
        return {}

    try:
        with open(eda_runtime_yml) as file:
            data = yaml.safe_load(file)
            if isinstance(data, dict):
                return data
            raise ValueError(f"Expected dict, got {type(data).__name__}")
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(
            f"error parsing eda collection metadata "
            f"`{eda_runtime_yml}`: {exc}"
        )


def load_plugin_routing(
    name: str,
) -> Optional[dict]:
    collection_name, plugin_name = split_collection_name(name)

    if not collection_name or not plugin_name:
        return None

    data = _load_eda_runtime(collection_name)
    if data:
        plugin_routing = data.get("plugin_routing")
        if isinstance(plugin_routing, dict):
            return plugin_routing
        raise ValueError(
            f"expected plugin_routing as dict. "
            f"Got {type(plugin_routing)} instead."
        )

    return None


def get_redirect_info(
    plugin_routing_data: dict, obj_type: str, plugin_name: str
) -> Optional[str]:
    """Get redirect target for a plugin from plugin_routing data.

    Uses ansible-core format: plugin_routing.{obj_type}.{plugin_name}.redirect

    Args:
        plugin_routing_data: The plugin_routing dictionary
        obj_type: Type of plugin ('event_source' or 'event_filter')
        plugin_name: Simple plugin name (e.g., 'range')

    Returns:
        Redirect target FQCN if found, None otherwise

    Raises:
        ValueError
    """
    type_section = plugin_routing_data.get(obj_type, {})
    if not isinstance(type_section, dict):
        raise ValueError(f"expected dict, got {type(type_section).__name__}")
    plugin_data = type_section.get(plugin_name, {})
    if not isinstance(plugin_data, dict):
        raise ValueError(f"expected dict, got {type(plugin_data).__name__}")
    return plugin_data.get("redirect")


def get_deprecation_info(
    plugin_routing_data: dict, obj_type: str, plugin_name: str
) -> Optional[dict]:
    """Get deprecation data for a plugin from plugin_routing data.

    Args:
        plugin_routing_data: The plugin_routing dictionary
        obj_type: Type of plugin ('event_source' or 'event_filter')
        plugin_name: Simple plugin name (e.g., 'range')

    Returns:
        Deprecation metadata dict if found, None otherwise

    Raises:
        ValueError
    """
    type_section = plugin_routing_data.get(obj_type, {})
    if not isinstance(type_section, dict):
        raise ValueError(f"expected dict, got {type(type_section).__name__}")
    plugin_data = type_section.get(plugin_name, {})
    if not isinstance(plugin_data, dict):
        raise ValueError(f"expected dict, got {type(plugin_data).__name__}")
    return plugin_data.get("deprecation")


def get_tombstone_info(
    plugin_routing_data: dict, obj_type: str, plugin_name: str
) -> Optional[dict]:
    """Get tombstone data for a plugin from plugin_routing data.

    Uses ansible-core format: plugin_routing.{obj_type}.{plugin_name}.tombstone

    Args:
        plugin_routing_data: The plugin_routing dictionary
        obj_type: Type of plugin ('event_source' or 'event_filter')
        plugin_name: Simple plugin name (e.g., 'range')

    Returns:
        Tombstone metadata dict if found, None otherwise

    Raises:
        ValueError
    """
    type_section = plugin_routing_data.get(obj_type, {})
    if not isinstance(type_section, dict):
        raise ValueError(f"expected dict, got {type(type_section).__name__}")
    plugin_data = type_section.get(plugin_name, {})
    if not isinstance(plugin_data, dict):
        raise ValueError(f"expected dict, got {type(plugin_data).__name__}")
    return plugin_data.get("tombstone")


def log_deprecation_warning(
    plugin_name: str,
    plugin_type: str,
    deprecation_data: dict,
) -> None:
    """Log deprecation warning following ansible-core's format.

    Args:
        plugin_name: Fully qualified plugin name (e.g., 'ansible.eda.generic')
        plugin_type: Type of plugin ('event_source' or 'event_filter')
        deprecation_data: Dictionary containing deprecation metadata with keys:
            - warning_text: Custom warning message
            - removal_version: Version when feature will be removed
            - removal_date: Date when feature
              will be removed (takes precedence)
    """
    if not deprecation_data:
        return

    warning_text = deprecation_data.get("warning_text", "") or ""
    removal_date = deprecation_data.get("removal_date")
    removal_version = deprecation_data.get("removal_version")

    if not (warning_text or removal_date or removal_version):
        return

    # Prefer removal_date over removal_version (like ansible-core)
    if removal_date is not None:
        removal_version = None

    # Format main message
    msg = f"{plugin_name} has been deprecated."
    if warning_text:
        msg += f" {warning_text}"

    # Add removal info
    collection_name, simple_plugin_name = split_collection_name(plugin_name)

    # Format plugin type for display
    if plugin_type == EVENT_SOURCE_OBJ_TYPE:
        plugin_type_display = "event source"
    elif plugin_type == EVENT_SOURCE_FILTER_OBJ_TYPE:
        plugin_type_display = "event filter"
    else:
        plugin_type_display = plugin_type

    # Build removal message
    if removal_date:
        removal_info = (
            f" This feature will be removed from {plugin_type_display} "
            f"'{simple_plugin_name}' in collection '{collection_name}' "
            f"in a release after {removal_date}."
        )
    elif removal_version:
        removal_info = (
            f" This feature will be removed from {plugin_type_display} "
            f"'{simple_plugin_name}' in collection '{collection_name}' "
            f"version {removal_version}."
        )

    else:
        removal_info = (
            f" This feature will be removed from {plugin_type_display} "
            f"'{simple_plugin_name}' in collection '{collection_name}' "
            f"in a future release."
        )

    msg += removal_info

    logger.warning(msg)


def apply_plugin_routing(
    plugin_name: str,
    obj_type: str,
    legacy_mapping: dict,
    tombstone_exception: type,
) -> str:
    """Apply plugin routing (legacy, deprecation, tombstone, redirect).

    Follows ansible-core behavior:
    - Applies legacy mappings first
    - Follows redirect chains (not just single redirects)
    - Checks deprecation before tombstone for each plugin in chain
    - Detects redirect loops

    Args:
        plugin_name: The plugin name (source or filter)
        obj_type: Type of plugin ('event_source' or 'event_filter')
        legacy_mapping: Legacy mapping dict for this plugin type
        tombstone_exception: Exception to raise if tombstoned

    Returns:
        The final plugin name after applying routing rules

    Raises:
        tombstone_exception: If plugin is tombstoned
        ValueError: If redirect loop detected
    """
    # Check legacy mapping first
    if plugin_name in legacy_mapping:
        logger.info(
            f"redirecting (type: {obj_type}) "
            f"{plugin_name} to {legacy_mapping[plugin_name]}"
        )
        return legacy_mapping[plugin_name]

    # Track redirect path to detect loops
    MAX_REDIRECT_CHAIN_LEN = 10
    redirect_chain = [plugin_name]
    current_name = plugin_name

    # Follow redirect chain
    jump_count = 0
    while jump_count < MAX_REDIRECT_CHAIN_LEN:
        # Load runtime plugin routing for current plugin
        plugin_routing = load_plugin_routing(current_name)
        if not plugin_routing:
            return current_name

        _, simple_plugin_name = split_collection_name(current_name)

        # First: Check deprecation
        deprecation_data = get_deprecation_info(
            plugin_routing, obj_type, simple_plugin_name
        )
        if deprecation_data:
            log_deprecation_warning(current_name, obj_type, deprecation_data)

        # Second: Check tombstone - if tombstoned, fail immediately
        tombstone_data = get_tombstone_info(
            plugin_routing, obj_type, simple_plugin_name
        )
        if tombstone_data:
            error_msg = (
                f"The {current_name} {obj_type} has been removed. "
                f"{tombstone_data.get('warning_text', '')}"
            )
            raise tombstone_exception(current_name, message=error_msg)

        # Third: Check for redirect
        redirect = get_redirect_info(
            plugin_routing, obj_type, simple_plugin_name
        )
        if redirect:
            # Check for redirect loop
            if redirect in redirect_chain:
                raise ValueError(
                    f"plugin redirect loop resolving {plugin_name} "
                    f"(path: {redirect_chain + [redirect]})"
                )

            logger.info(
                f"redirecting (type: {obj_type}) "
                f"{current_name} to {redirect}"
            )
            redirect_chain.append(redirect)
            current_name = redirect
        else:
            return current_name

        jump_count += 1

    # This is raised when the while condition is no longer True
    error_msg = f"Exceeded max allowed ({MAX_REDIRECT_CHAIN_LEN}) redirections"
    # RuntimeError seems ok here, but maybe we need a different exception
    raise RuntimeError(error_msg)


def find_object(collection, name, object_types, extensions):
    if find_collection(collection) is None:
        return False

    if not isinstance(extensions, list):
        extensions = [extensions]

    for object_type in object_types:
        for extension in extensions:
            location = (
                os.path.join(find_collection(collection), object_type, name)
                + extension
            )
            if os.path.exists(location):
                return location

    raise FileNotFoundError(
        f"Cannot find {object_type} {name} in {collection} at {location}"
    )


def has_rulebook(collection, rulebook):
    return has_object(
        collection,
        rulebook,
        [f"{EDA_PATH_PREFIX}/rulebooks", "rulebooks"],
        ".yml",
    )


def load_rulebook(collection, rulebook):
    location = find_object(
        collection,
        rulebook,
        [f"{EDA_PATH_PREFIX}/rulebooks", "rulebooks"],
        ".yml",
    )
    if not location:
        raise RulebookNotFoundException(f"Cannot find collection {collection}")

    with open(location, "rb") as f:
        terminal.Display.instance().banner(
            "collection", f"Loading rulebook from {location}"
        )
        raw_data = f.read()
        vaulted = has_vaulted_str(raw_data)
        return vaulted, yaml.safe_load(raw_data)


def has_source(collection, source):
    return has_object(
        collection,
        source,
        EDA_SOURCE_PATHS,
        ".py",
    )


def find_source(collection, source):
    return find_object(
        collection,
        source,
        EDA_SOURCE_PATHS,
        ".py",
    )


def has_source_filter(collection, source_filter):
    return has_object(
        collection,
        source_filter,
        EDA_FILTER_PATHS,
        ".py",
    )


def find_source_filter(collection, source_filter):
    return find_object(
        collection,
        source_filter,
        EDA_FILTER_PATHS,
        ".py",
    )


def has_playbook(collection, playbook):
    return has_object(
        collection, playbook, EDA_PLAYBOOKS_PATHS, EDA_YAML_EXTENSIONS
    )


def find_playbook(collection, playbook):
    return find_object(
        collection, playbook, EDA_PLAYBOOKS_PATHS, EDA_YAML_EXTENSIONS
    )


# This is a test function intentionally not covered by tests.
# Less than 20 lines of code.
def uncovered_test_function_1():
    """Add this function intentionally not covered by tests."""
    result = 0
    for i in range(10):
        result += i
        if result > 5:
            logger.info("Result is greater than 5")
    return result
