import json
import logging

import requests

_logger = logging.getLogger(__name__)


class DurableRulesEngine:
    _host = None
    _last_resp = None

    def __init__(self, host):
        self._host = host

    def create_ruleset(self, ruleset_name, ruleset_string):
        req = {ruleset_name: json.loads(ruleset_string)}

        r = requests.post(
            self._host + "/create-durable-rules-executor", json=req
        )
        if r.status_code != 200:
            raise Exception(
                f"Invalid status code: {r.status_code} - {r.reason}\n"
                + json.loads(r.content)["details"]
            )

        id = r.text
        return id

    def assert_event(self, session_id, serialized_fact):
        _logger.warning("assert_event not yet implemented: using assert_fact")
        return self.assert_fact(session_id, serialized_fact)

    def assert_fact(self, session_id, serialized_fact):
        d = json.loads(serialized_fact)
        if "j" in serialized_fact:
            d["j"] = 1

        serialized_fact = json.dumps(d)

        r = requests.post(
            f"{self._host}/rules-durable-executors/{session_id}/process",
            json=json.loads(serialized_fact),
        )

        if r.status_code != 200:
            raise Exception(
                f"Invalid status code: {r.status_code} - {r.reason}\n"
                + json.loads(r.content)["details"]
            )

        self._last_resp = r.json()
        self._last_resp.reverse()

        return (0, session_id)

    def start_action_for_state(self, handle):  # real signature unknown

        if self._last_resp:
            resp = self._last_resp.pop()
        else:
            return None

        return ('{ "sid":"0", "id":"sid-0", "$s":1}', json.dumps(resp), handle)

    def complete_and_start_action(self, handle):  # real signature unknown
        _logger.info("complete_and_start_action: %d", handle)

        if self._last_resp:
            resp = self._last_resp.pop()
        else:
            return None

        return json.dumps(resp)

    def retract_fact(self, session_id, serialized_fact):
        r = requests.post(
            f"{self._host}/rules-durable-executors/{session_id}/retract-fact",
            json=json.loads(serialized_fact),
        )
        if r.status_code != 200:
            raise Exception(
                f"Invalid status code: {r.status_code} - {r.reason}\n"
                + json.loads(r.content)["details"]
            )

        return (0, session_id)

    def get_facts(self, session_id, _sid):
        r = requests.post(
            f"{self._host}/rules-durable-executors/{session_id}/get-all-facts"
        )
        if r.status_code != 200:
            raise Exception(
                f"Invalid status code: {r.status_code} - {r.reason}\n"
                + json.loads(r.content)["details"]
            )

        return r.content


class error(Exception):
    # no doc
    def __init__(self, *args, **kwargs):  # real signature unknown
        pass

    __weakref__ = property(
        lambda self: object(), lambda self, v: None, lambda self: None
    )  # default
    """list of weak references to the object (if defined)"""


# exported methods

_instance = DurableRulesEngine("http://localhost:8080")


def abandon_action(*args, **kwargs):  # real signature unknown
    pass


def assert_event(session_id, serialized_fact):
    return _instance.assert_fact(session_id, serialized_fact)


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
