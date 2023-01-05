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

import asyncio
import os
from queue import Queue

if os.environ.get("EDA_RULES_ENGINE", "drools") == "drools":
    from drools.ruleset import assert_fact as set_fact, post
else:
    from durable import lang
    from durable.lang import (
        assert_fact as set_fact,
        c,
        m,
        post,
        rule,
        ruleset,
        when_all,
    )

import pytest
import yaml

from ansible_rulebook.rule_generator import generate_rulesets
from ansible_rulebook.rules_parser import parse_rule_sets

HERE = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.skipif(
    os.environ.get("EDA_RULES_ENGINE", "drools") == "drools",
    reason="durable rules only test",
)
def test_m():
    assert m
    assert m.x
    assert m.x.define() == {"$m": "x"}
    assert m.x > m.y
    assert (m.x > m.y).define() == {"$gt": {"x": {"$m": "y"}}}
    assert m.x == m.y
    assert (m.x == m.y).define() == {"x": {"$m": "y"}}
    assert m.x < m.y
    assert (m.x < m.y).define() == {"$lt": {"x": {"$m": "y"}}}
    assert (+m.x).define() == {"$ex": {"x": 1}}
    assert (-m.x).define() == {"$nex": {"x": 1}}
    assert (m.x.y.z == "foo").define() == {"x.y.z": "foo"}
    assert (m.x.y.z == "foo").define() == {"x.y.z": "foo"}
    assert ((m.x == "foo") & (m.y == "bar")).define() == {
        "$and": [{"x": "foo"}, {"y": "bar"}]
    }
    assert ((m.x == "foo") & (m.y == "bar")).define() == {
        "$and": [{"x": "foo"}, {"y": "bar"}]
    }
    assert (c.first << (m.x == "eats") & (m.y == "flies")).define() == {
        "$and": [{"x": "eats"}, {"y": "flies"}]
    }
    assert c.first._name == "first"
    o = (m.x == "eats") & (m.y == "flies")
    c.first << o
    assert o._name == "first"
    assert (
        (m.x == "lives") & (m.y == "water") & (m.subject == c.first.subject)
    ).define() == {
        "$and": [
            {"x": "lives"},
            {"y": "water"},
            {"subject": {"first": "subject"}},
        ]
    }
    assert (
        when_all(
            c.first << m.t == "purchase",
            c.second << m.location != c.first.location,
        )
    ).define() == {
        "all": [
            {"first": {"t": "purchase"}},
            {"second": {"$neq": {"location": {"first": "location"}}}},
        ]
    }


@pytest.mark.skipif(
    os.environ.get("EDA_RULES_ENGINE", "drools") == "drools",
    reason="durable rules only test",
)
def test_ruleset():

    some_rules = ruleset("test_rules")

    assert some_rules
    assert lang._rulesets
    assert lang._rulesets["test_rules"] == some_rules

    assert len(lang._ruleset_stack) == 0

    with some_rules:
        assert lang._ruleset_stack[-1] == some_rules

    assert len(lang._ruleset_stack) == 0

    assert some_rules.define() == ("test_rules", {})


@pytest.mark.skipif(
    os.environ.get("EDA_RULES_ENGINE", "drools") == "drools",
    reason="durable rules only test",
)
def test_rules():

    some_rules = ruleset("test_rules1")

    assert some_rules
    assert lang._rulesets
    assert lang._rulesets["test_rules1"] == some_rules

    assert len(lang._ruleset_stack) == 0

    with some_rules:
        assert lang._ruleset_stack[-1] == some_rules

        def x(c):
            print("c")

        # when_all(m.x == 5)(x)
        rule("all", True, m.x == 5)(x)

    assert len(lang._ruleset_stack) == 0

    assert some_rules.define() == (
        "test_rules1",
        {"r_0": {"all": [{"m": {"x": 5}}], "run": x}},
    )
    post("test_rules1", {"x": 5})


@pytest.mark.skipif(
    os.environ.get("EDA_RULES_ENGINE", "drools") == "drools",
    reason="durable rules only test",
)
def test_set_facts():

    some_rules = ruleset("test_set_facts")

    with some_rules:

        @when_all(+m.subject.x)
        def output(c):
            print(
                "Fact: {0} {1} {2}".format(
                    c.m.subject.x, c.m.predicate, c.m.object
                )
            )

    set_fact(
        "test_set_facts",
        {"subject": {"x": "Kermit"}, "predicate": "eats", "object": "flies"},
    )


@pytest.mark.skipif(
    os.environ.get("EDA_RULES_ENGINE", "drools") == "drools",
    reason="durable rules only test",
)
def test_parse_rules():
    os.chdir(HERE)
    with open("rules/rules.yml") as f:
        data = yaml.safe_load(f.read())

    parse_rule_sets(data)


@pytest.mark.asyncio
async def test_generate_rules():
    os.chdir(HERE)
    with open("rules/rules.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())
    set_fact("Demo rules", {"payload": {"text": "hello"}})

    assert durable_rulesets[0].plan.queue.get_nowait().action == "slack"
    assert durable_rulesets[0].plan.queue.get_nowait().rule == "assert fact"
    assert durable_rulesets[0].plan.queue.get_nowait().ruleset == "Demo rules"


@pytest.mark.asyncio
async def test_generate_rules_multiple_conditions_any():
    os.chdir(HERE)
    with open("rules/rules_with_multiple_conditions.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())

    post("Demo rules multiple conditions any", {"i": 0})
    assert durable_rulesets[0].plan.queue.get_nowait().action == "debug"
    post("Demo rules multiple conditions any", {"i": 1})
    assert durable_rulesets[0].plan.queue.get_nowait().action == "debug"


@pytest.mark.asyncio
async def test_generate_rules_multiple_conditions_all():
    os.chdir(HERE)
    with open("rules/rules_with_multiple_conditions2.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())

    post("Demo rules multiple conditions all", {"i": 0})
    assert durable_rulesets[0].plan.queue.qsize() == 0
    post("Demo rules multiple conditions all", {"i": 1})
    assert durable_rulesets[0].plan.queue.qsize() == 1
    assert durable_rulesets[0].plan.queue.get_nowait().action == "debug"


@pytest.mark.asyncio
async def test_generate_rules_multiple_conditions_all_3():
    os.chdir(HERE)
    with open("rules/rules_with_multiple_conditions3.yml") as f:
        data = yaml.safe_load(f.read())
    with open("playbooks/inventory.yml") as f:
        inventory = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
    print(rulesets)
    ruleset_queues = [(ruleset, Queue()) for ruleset in rulesets]
    durable_rulesets = generate_rulesets(ruleset_queues, dict(), inventory)

    durable_rulesets[0].plan.queue = asyncio.Queue()
    print(durable_rulesets[0].ruleset.define())

    post("Demo rules multiple conditions reference assignment", {"i": 0})
    assert durable_rulesets[0].plan.queue.qsize() == 0
    post("Demo rules multiple conditions reference assignment", {"i": 1})
    assert durable_rulesets[0].plan.queue.qsize() == 0
    post("Demo rules multiple conditions reference assignment", {"i": 2})
    assert durable_rulesets[0].plan.queue.qsize() == 1
    assert durable_rulesets[0].plan.queue.get_nowait().action == "debug"
