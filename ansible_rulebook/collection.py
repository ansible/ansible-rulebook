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

import os
import shutil
import subprocess
from functools import lru_cache

import yaml

ANSIBLE_GALAXY = shutil.which("ansible-galaxy")


def split_collection_name(collection_resource):
    collection, _, resource = collection_resource.rpartition(".")
    return collection, resource


@lru_cache
def find_collection(name):
    if ANSIBLE_GALAXY is None:
        raise Exception("ansible-galaxy is not installed")
    try:
        output = subprocess.check_output(
            [ANSIBLE_GALAXY, "collection", "list", name],
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError:
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


def has_object(collection, name, object_type, extension):
    if find_collection(collection) is None:
        return False
    return os.path.exists(
        os.path.join(find_collection(collection), object_type, name)
        + extension
    )


def find_object(collection, name, object_type, extension):
    if find_collection(collection) is None:
        return False
    location = (
        os.path.join(find_collection(collection), object_type, name)
        + extension
    )
    if not os.path.exists(location):
        raise Exception(
            f"Cannot find {object_type} {name} in {collection} at {location}"
        )
    return location


def has_rulebook(collection, rulebook):
    return has_object(collection, rulebook, "rulebooks", ".yml")


def load_rulebook(collection, rulebook):
    location = find_object(collection, rulebook, "rulebooks", ".yml")
    if not location:
        return False
    with open(location) as f:
        print(f"Loading rulebook from {location}")
        return yaml.safe_load(f.read())


def has_source(collection, source):
    return has_object(collection, source, "plugins/event_source", ".py")


def find_source(collection, source):
    return find_object(collection, source, "plugins/event_source", ".py")


def has_source_filter(collection, source_filter):
    return has_object(collection, source_filter, "plugins/event_filter", ".py")


def find_source_filter(collection, source_filter):
    return find_object(
        collection, source_filter, "plugins/event_filter", ".py"
    )


def has_playbook(collection, source_filter):
    return has_object(collection, source_filter, "", ".yml")


def find_playbook(collection, source_filter):
    return find_object(collection, source_filter, "", ".yml")
