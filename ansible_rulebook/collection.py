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
import shutil
import subprocess
from functools import lru_cache

import yaml

from ansible_rulebook import terminal

ANSIBLE_GALAXY = shutil.which("ansible-galaxy")
EDA_PATH_PREFIX = "extensions/eda"

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
    if ANSIBLE_GALAXY is None:
        raise Exception("ansible-galaxy is not installed")
    try:
        env = os.environ.copy()
        env["ANSIBLE_LOCAL_TEMP"] = "/tmp"
        output = subprocess.check_output(
            [ANSIBLE_GALAXY, "collection", "list", name],
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
        return False
    with open(location) as f:
        terminal.Display.instance().banner(
            "collection", f"Loading rulebook from {location}"
        )
        return yaml.safe_load(f.read())


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
