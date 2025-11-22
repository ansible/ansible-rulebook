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
from typing import Optional, Tuple

import yaml

from ansible_rulebook import terminal
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import RulebookNotFoundException
from ansible_rulebook.vault import has_vaulted_str

EDA_PATH_PREFIX = "extensions/eda"
EDA_EXTENSIONS = "extensions.eda"
EVENT_SOURCE_OBJ_TYPE = "event_source"
EVENT_SOUURCE_FILTER_OBJ_TYPE = "event_filter"

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


def is_deprecated(name: str, obj_type: str) -> Tuple[bool, Optional[str]]:
    """Check if a plugin is deprecated and get its redirect target.

    Checks the collection's meta/runtime.yml file for deprecation information
    about event sources and event filters. If the plugin is deprecated, logs
    a warning with the deprecation message and removal version.

    Args:
        name: str
            Fully qualified name of the plugin (ex:'ansible.eda.json_filter')
        obj_type: str
            Type of plugin object, either 'event_source' or 'event_filter'

    Returns:
        A tuple of (is_deprecated : bool, redirect_target : str | None) where:
        - is_deprecated: True if the plugin is deprecated, False otherwise
        - redirect_target:
                The fully qualified name to redirect to if deprecated,
                None otherwise (e.g., 'eda.builtin.json_filter')

    Example:
        >>> is_deprecated('ansible.eda.json_filter', 'event_filter')
        (True, 'eda.builtin.json_filter')
        >>> is_deprecated('ansible.eda.range', 'event_source')
        (True, 'eda.builtin.range')
        >>> is_deprecated('some.unknown.plugin', 'event_source')
        (False, None)
    """

    parts = name.split(".")
    if len(parts) < 2:
        return False, None
    collection_name = ".".join(parts[:-1])
    path = find_collection(collection_name)
    if path is None:
        return (False, None)
    runtime_yml = os.path.join(path, "meta", "runtime.yml")
    if os.path.exists(runtime_yml):
        with open(runtime_yml) as file:
            data = yaml.safe_load(file)

        if "plugin_routing" in data:

            deprecated_objs = data["plugin_routing"].get(
                f"{EDA_EXTENSIONS}.plugins.{obj_type}", {}
            )
            deprecated_item = deprecated_objs.get(name, {})
            if "redirect" in deprecated_item:

                deprecation_details = deprecated_item.get("deprecation", {})
                warning_text = deprecation_details.get("warning_text", "")
                removal_version = deprecation_details.get("removal_version")

                msg = warning_text
                if removal_version:
                    msg += f" It will be removed in version {removal_version}."

                logger.warning(msg)

                return True, deprecated_item["redirect"]

    return False, None


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
