
import durable.lang

from typing import Dict
import ansible_runner


def assert_fact(ruleset: str, fact: Dict):
    durable.lang.assert_fact(ruleset, fact)


def retract_fact(ruleset: str, fact: Dict):
    durable.lang.retract_fact(ruleset, fact)


def post_event(ruleset: str, fact: Dict):
    durable.lang.post(ruleset, fact)


def run_playbook():
    pass


actions = dict(assert_fact=assert_fact,
               retract_fact=retract_fact,
               post_event=post_event,
               run_playbook=run_playbook)

