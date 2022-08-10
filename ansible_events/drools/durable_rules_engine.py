import logging
import os

_logger = logging.getLogger(__name__)


class error(Exception):
    # no doc
    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    __weakref__ = property(
        lambda self: object(), lambda self, v: None, lambda self: None
    )  # default
    """list of weak references to the object (if defined)"""


def make_instance():
    jpy_classpath = os.environ.get("ANSIBLE_EVENTS_DROOLS_JPY_CLASSPATH")
    if jpy_classpath:
        from ansible_events.drools.jpy_durable_rules_engine import (
            JpyDurableRulesEngine,
        )

        return JpyDurableRulesEngine(jpy_classpath)

    from ansible_events.drools.rest_durable_rules_engine import (
        RestDurableRulesEngine,
    )

    return RestDurableRulesEngine(
        os.environ.get("ANSIBLE_EVENTS_DROOLS_HOST", "http://localhost:8080")
    )


# exported methods

_instance = make_instance()


def abandon_action(*args, **kwargs):  # real signature unknown
    pass


def assert_event(session_id, serialized_fact):
    return _instance.assert_event(session_id, serialized_fact)


def assert_events(*args, **kwargs):  # real signature unknown
    raise Exception("assert_events")


def assert_fact(session_id, serialized_fact):
    return _instance.assert_fact(session_id, serialized_fact)


def assert_facts(*args, **kwargs):  # real signature unknown
    pass


def assert_timers(*args, **kwargs):  # real signature unknown
    pass


def cancel_timer(*args, **kwargs):  # real signature unknown
    pass


def complete_get_idle_state(*args, **kwargs):  # real signature unknown
    pass


def complete_get_queued_messages(*args, **kwargs):  # real signature unknown
    pass


def create_ruleset(ruleset_name, ruleset_string):
    return _instance.create_ruleset(ruleset_name, ruleset_string)


def delete_ruleset(*args, **kwargs):  # real signature unknown
    pass


def delete_state(*args, **kwargs):  # real signature unknown
    raise Exception("delete_state")


def get_events(*args, **kwargs):  # real signature unknown
    _logger.warning("get_events() not yet implemented. Ignoring.")
    return "{}"


def get_facts(handle, session_id):  # real signature unknown
    return _instance.get_facts(handle, session_id)


def get_state(*args, **kwargs):  # real signature unknown
    pass


def renew_action_lease(*args, **kwargs):  # real signature unknown
    pass


def retract_fact(handle, payload):
    return _instance.retract_fact(handle, payload)


def retract_facts(*args, **kwargs):  # real signature unknown
    pass


def set_delete_message_callback(*args, **kwargs):  # real signature unknown
    pass


def set_get_idle_state_callback(*args, **kwargs):  # real signature unknown
    pass


def set_get_queued_messages_callback(
    *args, **kwargs
):  # real signature unknown
    pass


def set_queue_message_callback(*args, **kwargs):  # real signature unknown
    pass


def set_store_message_callback(*args, **kwargs):  # real signature unknown
    pass


def start_action(*args, **kwargs):
    _logger.warning("start_action() not yet implemented. Ignoring.")
    return None


def start_action_for_state(handle, state_handle):
    return _instance.start_action_for_state(handle)


def complete_and_start_action(handle, context_handle):
    return _instance.complete_and_start_action(handle)


def start_timer(*args, **kwargs):  # real signature unknown
    pass


def update_state(session_id, args):  # real signature unknown
    return session_id
