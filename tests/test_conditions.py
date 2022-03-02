

from durable.lang import m

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

    result = condition.parseString('text')[0]
    print(result)
    print(visit_condition(result, m, {}).define())

    result = condition.parseString('""')[0]
    print(result)
    print(visit_condition(result, m, {}))

    result = condition.parseString('text != ""')[0]
    print(result)
    print(visit_condition(result, m, {}).define())
    print((m.text != "").define())
    assert visit_condition(result, m, {}).define() == (m.text != "").define()

    result = condition.parseString('x != y')[0]
    print(result)
    print(visit_condition(result, m, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m, {}).define() == (m.x != m.y).define()


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

    result = parse_condition('text')[0]
    print(result)
    print(visit_condition(result, m, {}).define())

    result = parse_condition('""')[0]
    print(result)
    print(visit_condition(result, m, {}))

    result = parse_condition('text != ""')[0]
    print(result)
    print(visit_condition(result, m, {}).define())
    print((m.text != "").define())
    assert visit_condition(result, m, {}).define() == (m.text != "").define()

    result = parse_condition('x != y')[0]
    print(result)
    print(visit_condition(result, m, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m, {}).define() == (m.x != m.y).define()

    result = parse_condition('payload.text != ""')[0]
    print(result)
    print(visit_condition(result, m, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m, {}).define() == (m.payload.text != "").define()

    result = parse_condition('i == 1')[0]
    print(result)
    print(visit_condition(result, m, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m, {}).define() == (m.i == 1).define()

    result = parse_condition('+i')[0]
    print(result)
    print(visit_condition(result, m, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m, {}).define() == (+m.i).define()
