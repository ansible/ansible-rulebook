

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

    result = condition.parseString('fact.text')[0]
    print(result)
    print(visit_condition(result, {}).define())

    result = condition.parseString('""')[0]
    print(result)
    print(visit_condition(result, {}))

    result = condition.parseString('fact.text != ""')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.text != "").define())
    assert visit_condition(result, {}).define() == (m.text != "").define()

    result = condition.parseString('fact.x != fact.y')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
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

    result = parse_condition('fact.text')[0]
    print(result)
    print(visit_condition(result, {}))
    assert visit_condition(result, {}) == ''

    result = parse_condition('""')[0]
    print(result)
    print(visit_condition(result, {}))
    assert visit_condition(result, {}) == ''

    result = parse_condition('fact.text != ""')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.text != "").define())
    assert visit_condition(result, {}).define() == (m.text != "").define()

    result = parse_condition('fact.x != fact.y')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == (m.x != m.y).define()

    result = parse_condition('fact.payload.text != ""')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == (m.payload.text != "").define()

    result = parse_condition('fact.i == 1')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == (m.i == 1).define()

    result = parse_condition('+fact.i')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == (+m.i).define()

    result = parse_condition('fact.i is defined')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == (+m.i).define()

    result = parse_condition('fact.x == "foo" and fact.y == "bar"')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == ((m.x == 'foo') & (m.y == 'bar')).define()

    result = parse_condition('events.first << fact.x == "foo" and fact.y == "bar"')[0]
    print(result)
    print(visit_condition(result, {}).define())
    print((m.x != m.y).define())
    assert visit_condition(result, {}).define() == ((m.x == 'foo') & (m.y == 'bar')).define()
