import json
import logging

import requests

_logger = logging.getLogger(__name__)


class RestDurableRulesEngine:
    def __init__(self, host):
        self._host = host
        self._last_response = None

    def create_ruleset(self, ruleset_name, ruleset_string):
        request = {ruleset_name: json.loads(ruleset_string)}

        response = requests.post(
            self._host + "/create-durable-rules-executor", json=request
        )
        if response.status_code != 200:
            raise Exception(
                "Invalid status code: "
                f"{response.status_code} - {response.reason}\n"
                + json.loads(response.content)["details"]
            )

        return response.text

    def assert_event(self, session_id, serialized_fact):
        return self._process_message(
            session_id, serialized_fact, "process-events"
        )

    def assert_fact(self, session_id, serialized_fact):
        return self._process_message(
            session_id, serialized_fact, "process-facts"
        )

    def _process_message(self, session_id, serialized_fact, command):
        if command not in ["process-events", "process-facts"]:
            raise Exception("Unknown command " + command)

        fact = json.loads(serialized_fact)
        serialized_fact = json.dumps(fact)

        response = requests.post(
            f"{self._host}/rules-durable-executors/{session_id}/{command}",
            json=json.loads(serialized_fact),
        )

        if response.status_code != 200:
            raise Exception(
                "Invalid status code: "
                f"{response.status_code} - {response.reason}\n"
                + json.loads(response.content)["details"]
            )

        self._last_response = response.json()
        # drools returns the list in the opposite order
        self._last_response.reverse()

        return (0, session_id)

    def start_action_for_state(self, handle):  # real signature unknown

        if self._last_response:
            resp = self._last_response.pop()
        else:
            return None

        return ('{ "sid":"0", "id":"sid-0", "$s":1}', json.dumps(resp), handle)

    def complete_and_start_action(self, handle):  # real signature unknown
        _logger.info("complete_and_start_action: %s", handle)

        if self._last_response:
            resp = self._last_response.pop()
        else:
            return None

        return json.dumps(resp)

    def retract_fact(self, session_id, serialized_fact):
        response = requests.post(
            f"{self._host}/rules-durable-executors/{session_id}/retract-fact",
            json=json.loads(serialized_fact),
        )
        if response.status_code != 200:
            raise Exception(
                "Invalid status code: "
                f"{response.status_code} - {response.reason}\n"
                + json.loads(response.content)["details"]
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
