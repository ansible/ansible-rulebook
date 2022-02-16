

from typing import NamedTuple
import durable.lang
from durable.lang import *
from pyparsing import pyparsing_common, infix_notation, OpAssoc, one_of, ParserElement, QuotedString
ParserElement.enable_packrat()
from ansible_events.condition_parser import parse_condition
from ansible_events.rule_generator import visit_condition


def call(args, **kwargs):
    print('args', args)
    for i in args:
        print(type(i))
        for j in i:
            print(type(j))
    return args


class String(NamedTuple):
    value: str


class Identifier(NamedTuple):
    value: str


class OperatorExpression(NamedTuple):
    left: str
    operator: str
    right: str

integer = pyparsing_common.signed_integer
varname = pyparsing_common.identifier.copy().add_parse_action(lambda toks: Identifier(toks[0]))


string1 = QuotedString("'").copy().add_parse_action(lambda toks: String(toks[0]))
string2 = QuotedString('"').copy().add_parse_action(lambda toks: String(toks[0]))

arith_expr = infix_notation(integer | varname | string1 | string2,
                            [
                                ('!', 1, OpAssoc.RIGHT, call),
                                (one_of('* /'), 2, OpAssoc.LEFT),
                                (one_of('+ -'), 2, OpAssoc.LEFT),
                                (one_of('< >'), 2, OpAssoc.LEFT),
                                ('!=', 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
                                ('==', 2, OpAssoc.LEFT),
                                ('>=', 2, OpAssoc.LEFT),
                                ('<=', 2, OpAssoc.LEFT),
                            ])

def test_infix():
    arith_expr.run_tests('''
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


def visit(parsed_condition, condition):
    if isinstance(parsed_condition, Identifier):
        return condition.__getattr__(parsed_condition.value)
    if isinstance(parsed_condition, String):
        return parsed_condition.value
    if isinstance(parsed_condition, OperatorExpression):
        if parsed_condition.operator == "!=":
            return visit(parsed_condition.left, condition).__ne__(visit(parsed_condition.right, condition))


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
    arith_expr.run_tests('''
                         x
                         x > y
                         x == y
                         x < y
                         text != ""
    ''', full_dump=False)

    result = arith_expr.parseString('text')[0]
    print(result)
    print(visit(result, m).define())

    result = arith_expr.parseString('""')[0]
    print(result)
    print(visit(result, m))

    result = arith_expr.parseString('text != ""')[0]
    print(result)
    print(visit(result, m).define())
    print((m.text != "").define())
    assert visit(result, m).define() == (m.text != "").define()

    result = arith_expr.parseString('x != y')[0]
    print(result)
    print(visit(result, m).define())
    print((m.x != m.y).define())
    assert visit(result, m).define() == (m.x != m.y).define()


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
    print(visit_condition(result, m).define())

    result = parse_condition('""')[0]
    print(result)
    print(visit_condition(result, m))

    result = parse_condition('text != ""')[0]
    print(result)
    print(visit_condition(result, m).define())
    print((m.text != "").define())
    assert visit_condition(result, m).define() == (m.text != "").define()

    result = parse_condition('x != y')[0]
    print(result)
    print(visit_condition(result, m).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m).define() == (m.x != m.y).define()

    result = parse_condition('payload.text != ""')[0]
    print(result)
    print(visit_condition(result, m).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m).define() == (m.payload.text != "").define()

    result = parse_condition('i == 1')[0]
    print(result)
    print(visit_condition(result, m).define())
    print((m.x != m.y).define())
    assert visit_condition(result, m).define() == (m.i == 1).define()
