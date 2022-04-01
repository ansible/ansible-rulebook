

from durable.lang import m, c

from ansible_events.condition_parser import parse_condition, Identifier, String, OperatorExpression, condition
from ansible_events.rule_generator import visit_condition


def test_infix():
    condition.run_tests('''
        5+3*6
        (5+3)*6
        -2--11
        a!=4
        a==4
        a>4
        a>=4
        a<=4
        a<4
        a != 'hey'
        !True
        False
        true
        false
        ''', full_dump=False)


def test_m():
    assert m
    assert m.x
    assert m.x.define() == {'$m': 'x'}
    assert m.x > m.y
    assert (m.x > m.y).define() == {'$gt': {'x': {'$m': 'y'}}}
    assert m.x == m.y
    assert (m.x == m.y).define() == {'x': {'$m': 'y'}}
    assert m.x < m.y
    assert (m.x < m.y).define() == {'$lt': {'x': {'$m': 'y'}}}
    condition.run_tests('''
                         x
                         x > y
                         x == y
                         x < y
                         text != ""
    ''', full_dump=False)

    result = condition.parseString('event.text')[0]
    print(result)
    print(visit_condition(result, {}).define())

    result = condition.parseString('""')[0]
    print(result)
    print(visit_condition(result, {}))

    result = condition.parseString('event.text != ""')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (m.text != "").define()

    result = condition.parseString('event.x != event.y')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (m.x != m.y).define()


def test_parse_condition():
    assert m
    assert m.x
    assert m.x.define() == {'$m': 'x'}
    assert m.x > m.y
    assert (m.x > m.y).define() == {'$gt': {'x': {'$m': 'y'}}}
    assert m.x == m.y
    assert (m.x == m.y).define() == {'x': {'$m': 'y'}}
    assert m.x < m.y
    assert (m.x < m.y).define() == {'$lt': {'x': {'$m': 'y'}}}

    result = parse_condition('event.text')[0]
    print(result)
    print(visit_condition(result, {}))
    assert visit_condition(result, {}) == ''

    result = parse_condition('""')[0]
    print(result)
    print(visit_condition(result, {}))
    assert visit_condition(result, {}) == ''

    result = parse_condition('event.text != ""')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (m.text != "").define()

    result = parse_condition('event.x != event.y')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == (m.x != m.y).define()

    result = parse_condition('event.payload.text != ""')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (m.payload.text != "").define()

    result = parse_condition('event.i == 1')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (m.i == 1).define()

    result = parse_condition('+event.i')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (+m.i).define()

    result = parse_condition('event.i is defined')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (+m.i).define()

    result = parse_condition('event.x == "foo" and event.y == "bar"')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == ((m.x == 'foo') & (m.y == 'bar')).define()

    result = parse_condition('events.first << event.x == "foo" and event.y == "bar"')[0]
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == ((m.x == 'foo') & (m.y == 'bar')).define()

    result = parse_condition('events.first << event.payload.src_path == "{{src_path}}"')[0]
    print(result)
    print(visit_condition(result, {'src_path': 'x'}).define())
    assert visit_condition(result, {'src_path': 'x'}).define() == (c.first << (m.payload.src_path == 'x')).define()

    result = parse_condition("(event.payload.repository.full_name == \"{{repo_name}}\") and (event.payload.after is defined)")
    print(result)
    print(visit_condition(result, {'repo_name': 'x'}).define())
    assert visit_condition(result, {'repo_name': 'x'}).define() == ((m.payload.repository.full_name == 'x') & (+m.payload.after)).define()

    result = parse_condition("((event.x == 5) and (event.y == 6)) and (event.z == 7)")
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (((m.x == 5) & (m.y == 6)) & (m.z == 7)).define()

    result = parse_condition("events.first << event.t == 'purchase'")
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (m.t == 'purchase').define()

    result = parse_condition("facts.process_pid << fact.pid is defined")
    print(result)
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (+m.pid).define()

    result = parse_condition("event.process_check.pid == facts.process_pid.pid")
    print(result)
    print(visit_condition(result, {}))
    print((m.process_check.pid == c.__getattr__('process_pid').__getattr__('pid')).define())
    print(visit_condition(result, {}).define())
    assert visit_condition(result, {}).define() == (m.process_check.pid == c.process_pid.pid).define()
