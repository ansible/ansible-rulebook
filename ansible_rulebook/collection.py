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
import sys
from functools import lru_cache
from typing import Any, Dict, Set, Tuple

import yaml

from ansible_rulebook import terminal
from ansible_rulebook.conf import settings
from ansible_rulebook.exception import RulebookNotFoundException
from ansible_rulebook.vault import has_vaulted_str

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

EDA_PLUGIN_KIND_LABELS = {
    "event_source": "Event source",
    "event_filter": "Event filter",
}

_displayed_plugin_warnings: Set[Tuple[str, str]] = set()


@lru_cache
def _load_collection_runtime(collection: str) -> Dict[str, Any]:
    if not collection:
        return {}

    collection_path = find_collection(collection)
    if not collection_path:
        return {}

    runtime_path = os.path.join(collection_path, "meta", "runtime.yml")
    if not os.path.exists(runtime_path):
        return {}

    try:
        with open(runtime_path, "r", encoding="utf-8") as runtime_file:
            data = yaml.safe_load(runtime_file) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning(
            "Failed to read runtime metadata for collection %s: %s",
            collection,
            exc,
        )
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def _normalize_plugin_routing_section(
    section: Any,
) -> Dict[str, Dict[str, Any]]:
    if isinstance(section, dict):
        return section

    if isinstance(section, list):
        combined: Dict[str, Dict[str, Any]] = {}
        for item in section:
            if isinstance(item, dict):
                combined.update(item)
        return combined

    return {}


def _candidate_plugin_keys(
    collection: str,
    name: str,
) -> Tuple[str, ...]:
    candidates = [name]
    if name.endswith(".py"):
        candidates.append(name[:-3])
    else:
        candidates.append(f"{name}.py")

    if collection:
        fq_name = f"{collection}.{name}"
        candidates.append(fq_name)
        if not fq_name.endswith(".py"):
            candidates.append(f"{fq_name}.py")

    seen = set()
    result = []
    for candidate in candidates:
        candidate = candidate.strip()
        if candidate and candidate not in seen:
            seen.add(candidate)
            result.append(candidate)
    return tuple(result)


def _get_eda_plugin_entry(
    collection: str,
    plugin_type: str,
    name: str,
) -> Dict[str, Any]:
    runtime = _load_collection_runtime(collection)
    if not runtime:
        return {}

    plugin_routing = runtime.get("plugin_routing")
    if not isinstance(plugin_routing, dict):
        return {}

    section = _normalize_plugin_routing_section(
        plugin_routing.get(plugin_type)
    )
    if not section:
        return {}

    for candidate in _candidate_plugin_keys(collection, name):
        entry = section.get(candidate)
        if isinstance(entry, dict):
            return entry

    for key, entry in section.items():
        if not isinstance(entry, dict):
            continue
        key_name = os.path.splitext(os.path.basename(key))[0]
        if key_name == name:
            return entry

    return {}


def _format_sentence(text: str) -> str:
    formatted = text.strip()
    if not formatted:
        return ""
    if formatted[-1] not in ".!?":
        formatted = f"{formatted}."
    return formatted


def _emit_plugin_messages(
    collection: str,
    name: str,
    plugin_type: str,
    entry: Dict[str, Any],
) -> None:
    fq_name = name if not collection else f"{collection}.{name}"
    key = (plugin_type, fq_name)
    if key in _displayed_plugin_warnings:
        return

    plugin_kind = EDA_PLUGIN_KIND_LABELS.get(plugin_type, "Plugin")

    deprecation = entry.get("deprecation") or {}
    redirect = entry.get("redirect")

    sentences = []

    warning_text = None
    if isinstance(deprecation, dict):
        warning_text = deprecation.get("warning_text")
        if isinstance(warning_text, str) and warning_text.strip():
            sentences.append(warning_text.strip())
        else:
            details = "is deprecated"
            extras = []
            removal_version = deprecation.get("removal_version")
            removal_date = deprecation.get("removal_date")
            if removal_version is not None:
                version_text = str(removal_version).strip()
                if version_text:
                    extras.append(f"removal version {version_text}")
            if removal_date is not None:
                date_text = str(removal_date).strip()
                if date_text:
                    extras.append(f"removal date {date_text}")
            if extras:
                details = f"{details} ({', '.join(extras)})"
            sentences.append(details)

    if isinstance(redirect, str) and redirect.strip():
        sentences.append(f"Redirects to '{redirect.strip()}'")

    sentences = [s for s in sentences if s]
    if not sentences:
        return

    formatted_sentences = [
        _format_sentence(sentence) for sentence in sentences
    ]

    separator = ": " if warning_text else " "
    message = (
        f"{plugin_kind} plugin '{fq_name}'"
        f"{separator}{formatted_sentences[0]}"
    )
    if len(formatted_sentences) > 1:
        message = f"{message} {' '.join(formatted_sentences[1:])}"

    _displayed_plugin_warnings.add(key)

    terminal.Display.instance().banner(
        "deprecation",
        message,
        level=logging.WARNING,
        file=sys.stderr,
    )
    logger.warning(message)


def _resolve_eda_plugin(
    collection: str,
    name: str,
    plugin_type: str,
) -> Tuple[str, str]:
    if not collection:
        return collection, name

    current_collection = collection
    current_name = name
    visited: Set[Tuple[str, str, str]] = set()

    while True:
        entry = _get_eda_plugin_entry(
            current_collection, plugin_type, current_name
        )
        if not entry:
            return current_collection, current_name

        _emit_plugin_messages(
            current_collection, current_name, plugin_type, entry
        )

        redirect = entry.get("redirect")
        if not isinstance(redirect, str) or not redirect.strip():
            return current_collection, current_name

        redirected_collection, redirected_name = split_collection_name(
            redirect.strip()
        )
        if not redirected_collection:
            redirected_collection = current_collection
        if not redirected_name:
            logger.warning(
                "Invalid redirect target '%s' for %s plugin '%s.%s'",
                redirect,
                plugin_type,
                current_collection,
                current_name,
            )
            return current_collection, current_name

        key = (plugin_type, redirected_collection, redirected_name)
        if key in visited:
            logger.warning(
                "Circular redirect detected for %s plugin '%s.%s'",
                plugin_type,
                current_collection,
                current_name,
            )
            return current_collection, current_name

        visited.add(key)
        current_collection = redirected_collection
        current_name = redirected_name


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
    resolved_collection, resolved_source = (
        _resolve_eda_plugin(collection, source, "event_source")
        if collection
        else (collection, source)
    )
    return has_object(
        resolved_collection,
        resolved_source,
        EDA_SOURCE_PATHS,
        ".py",
    )


def find_source(collection, source):
    resolved_collection, resolved_source = (
        _resolve_eda_plugin(collection, source, "event_source")
        if collection
        else (collection, source)
    )
    return find_object(
        resolved_collection,
        resolved_source,
        EDA_SOURCE_PATHS,
        ".py",
    )


def has_source_filter(collection, source_filter):
    resolved_collection, resolved_source_filter = (
        _resolve_eda_plugin(collection, source_filter, "event_filter")
        if collection
        else (collection, source_filter)
    )
    return has_object(
        resolved_collection,
        resolved_source_filter,
        EDA_FILTER_PATHS,
        ".py",
    )


def find_source_filter(collection, source_filter):
    resolved_collection, resolved_source_filter = (
        _resolve_eda_plugin(collection, source_filter, "event_filter")
        if collection
        else (collection, source_filter)
    )
    return find_object(
        resolved_collection,
        resolved_source_filter,
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
