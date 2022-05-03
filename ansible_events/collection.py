
import os
import shutil
import subprocess
import yaml
from functools import lru_cache

ANSIBLE_GALAXY = shutil.which('ansible-galaxy')


def split_collection_name(collection_resource):
    collection, _, resource = collection_resource.rpartition(".")
    return collection, resource


@lru_cache
def find_collection(name):
    if ANSIBLE_GALAXY is None:
        raise Exception('ansible-galaxy is not installed')
    try:
        output = subprocess.check_output(
            [ANSIBLE_GALAXY, 'collection', 'list', name], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return None
    output = output.decode()
    parts = name.split('.')
    for line in output.splitlines():
        if line.startswith('# '):
            location = line[2:]
            location = os.path.join(location, *parts)
            if os.path.exists(location):
                return location
    return None


def has_object(collection, name, object_type, extension):
    if find_collection(collection) is None:
        return False
    return os.path.exists(os.path.join(find_collection(collection), object_type, name) + extension)


def find_object(collection, name, object_type, extension):
    if find_collection(collection) is None:
        return False
    location = os.path.join(find_collection(
        collection), object_type, name) + extension
    if not os.path.exists(location):
        raise Exception(
            f'Cannot find {object_type} {name} in {collection} at {location}')
    return location


def has_rules(collection, rules):
    return has_object(collection, rules, 'rules', ".yml")


def load_rules(collection, rules):
    location = find_object(collection, rules, 'rules', '.yml')
    if not location:
        return False
    with open(location) as f:
        print(f'Loading rules from {location}')
        return yaml.safe_load(f.read())


def has_source(collection, source):
    return has_object(collection, source, 'plugins/event_source', ".py")


def find_source(collection, source):
    return find_object(collection, source, 'plugins/event_source', '.py')


def has_source_filter(collection, source_filter):
    return has_object(collection, source_filter, 'plugins/event_filter', ".py")


def find_source_filter(collection, source_filter):
    return find_object(collection, source_filter, 'plugins/event_filter', '.py')


def has_playbook(collection, source_filter):
    return has_object(collection, source_filter, '', ".yml")


def find_playbook(collection, source_filter):
    return find_object(collection, source_filter, '', '.yml')
