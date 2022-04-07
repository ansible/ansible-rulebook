from durable.lang import m, c, assert_fact, ruleset, rule, when_all, post
from durable.lang import statechart, state, to
import durable


def test_statemachine():

    statemachine = statechart('hello')

    assert statemachine
    assert durable.lang._rulesets
    assert durable.lang._rulesets["hello"] == statemachine

    with statemachine:
        a_state = state('initial')

    assert statemachine.define() == ('hello$state', {'initial': {}})


def test_states():

    some_states = statechart("test_states1")

    assert some_states
    assert durable.lang._rulesets
    assert durable.lang._rulesets["test_states1"] == some_states

    assert len(durable.lang._ruleset_stack) == 0

    with some_states:
        assert durable.lang._ruleset_stack[-1] == some_states

        a_state = state('initial')

        with a_state:
            #@to('end_state')
            #@when_all(m.x == 5)
            def x(c):
                print("c")
            # when_all(m.x == 5)(x)
            #rule("all", True, m.x == 5)(to('end_state',x))
            to('end_state')(rule("all", True, m.x == 5)(x))

        state('end_state')

    assert len(durable.lang._ruleset_stack) == 0

    print(some_states.define())
    assert some_states.define() == (
        "test_states1$state", {'end_state': {},
            'initial': {'t_0': {'all': [{'m': {'x': 5}}], 'run': x, 'to': 'end_state'}}},
    )
    post("test_states1", {"x": 5})

def no_test_assert_facts():

    some_rules = ruleset("test_assert_facts")

    with some_rules:

        @when_all(+m.subject.x)
        def output(c):
            print("Fact: {0} {1} {2}".format(c.m.subject.x, c.m.predicate, c.m.object))

    assert_fact(
        "test_assert_facts",
        {"subject": {"x": "Kermit"}, "predicate": "eats", "object": "flies"},
    )


def no_test_parse_rules():
    os.chdir(HERE)
    with open("rules.yml") as f:
        data = yaml.safe_load(f.read())

    rulesets = parse_rule_sets(data)
