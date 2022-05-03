from ansible_events.collection import (
    find_collection,
    split_collection_name,
    find_source,
    load_rules,
)


def test_find_collection():
    location = find_collection("community.general")
    assert location is not None


def test_find_collection_eda():
    location = find_collection("benthomasson.eda")
    assert location is not None


def test_find_source():
    location = find_source(*split_collection_name("benthomasson.eda.range"))
    assert location is not None


def test_load_rules():
    rules = load_rules(*split_collection_name("benthomasson.eda.hello_events"))
    assert rules is not None
