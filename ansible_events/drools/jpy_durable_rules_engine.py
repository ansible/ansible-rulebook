import json
import logging

import jpy
import jpyutil

_logger = logging.getLogger(__name__)


class JpyDurableRulesEngine:
    def __init__(self, classpath):
        if not isinstance(classpath, list):
            classpath = [classpath]

        jpyutil.init_jvm(jvm_maxmem="512M", jvm_classpath=classpath)

        self._executor_class = jpy.get_type(
            "org.drools.yaml.core.RulesExecutor"
        )
        self._durable_rule_match_class = jpy.get_type(
            "org.drools.yaml.durable.domain.DurableRuleMatch"
        )
        self._durable_notation = jpy.get_type(
            "org.drools.yaml.durable.DurableNotation"
        ).INSTANCE

        self._executor_container = jpy.get_type(
            "org.drools.yaml.core.RulesExecutorContainer"
        ).INSTANCE
        self._last_response = None

    def create_ruleset(self, ruleset_name, ruleset_string):
        payload = {ruleset_name: json.loads(ruleset_string)}
        s = json.dumps(payload)
        executor = self._executor_class.createFromJson(
            self._durable_notation, s
        )
        return executor.getId()

    def assert_event(self, session_id, serialized_fact):
        def command(fact):
            executor = self._executor_container.get(session_id)
            return executor.processEvents(fact)

        return self._process_message(session_id, serialized_fact, command)

    def assert_fact(self, session_id, serialized_fact):
        def command(fact):
            executor = self._executor_container.get(session_id)
            return executor.processFacts(fact)

        return self._process_message(session_id, serialized_fact, command)

    def _process_message(self, session_id, serialized_fact, command):
        result = command(serialized_fact)

        self._last_response = json.loads(
            self._durable_rule_match_class.asJson(result)
        )
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
        executor = self._executor_container.get(session_id)
        executor.retract(serialized_fact)  # ignore bool return value for now
        return (0, session_id)

    def get_facts(self, session_id, _sid):
        executor = self._executor_container.get(session_id)
        return executor.getAllFactsAsJson()
