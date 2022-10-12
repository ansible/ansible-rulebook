from ansible_rulebook.collection import (
    find_collection,
    find_source,
    load_rulebook,
    split_collection_name,
)


def test_find_collection():
    location = find_collection("community.general")
    assert location is not None


def test_find_collection_eda():
    location = find_collection("ansible.eda")
    assert location is not None


def test_find_source():
    location = find_source(*split_collection_name("ansible.eda.range"))
    assert location is not None


def test_load_rulebook():
    rules = load_rulebook(*split_collection_name("ansible.eda.hello_events"))
    assert rules is not None
