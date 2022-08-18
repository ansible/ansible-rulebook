import logging

import jpy
import jpyutil

_logger = logging.getLogger(__name__)


class JpyDurableRulesEngine:
    def __init__(self, classpath):
        if not isinstance(classpath, list):
            classpath = [classpath]

        jpyutil.init_jvm(jvm_maxmem="512M", jvm_classpath=classpath)

        JpyDurableRulesEngine_JavaAPI = jpy.get_type(
            "org.drools.yaml.durable.jpy.JpyDurableRulesEngine"
        )
        self._api = JpyDurableRulesEngine_JavaAPI()

    def create_ruleset(self, ruleset_name, ruleset_string):
        return self._api.createRuleset(ruleset_name, ruleset_string)

    def assert_event(self, session_id, serialized_fact):
        return (self._api.assertEvent(session_id, serialized_fact), session_id)

    def assert_fact(self, session_id, serialized_fact):
        return (self._api.assertFact(session_id, serialized_fact), session_id)

    def start_action_for_state(self, handle):
        resp = self._api.advanceState()
        if resp is None:
            return None
        return ('{ "sid":"0", "id":"sid-0", "$s":1}', resp, handle)

    def complete_and_start_action(self, handle):  # real signature unknown
        resp = self._api.advanceState()
        return resp

    def retract_fact(self, session_id, serialized_fact):
        return (self._api.retractFact(session_id, serialized_fact), session_id)

    def get_facts(self, session_id, _sid):
        return self._api.getFacts(session_id)
