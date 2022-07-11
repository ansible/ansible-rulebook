from pyparsing import (
    Combine,
    Literal,
    OpAssoc,
    ParserElement,
    QuotedString,
    ZeroOrMore,
    infix_notation,
    one_of,
    pyparsing_common,
)

ParserElement.enable_packrat()

from ansible_events.condition_types import (  # noqa: E402
    Boolean,
    Condition,
    ExistsExpression,
    Identifier,
    Integer,
    OperatorExpression,
    String,
)

integer = pyparsing_common.signed_integer.copy().add_parse_action(
    lambda toks: Integer(toks[0])
)
ident = pyparsing_common.identifier
varname = (
    Combine(ident + ZeroOrMore("." + ident))
    .copy()
    .add_parse_action(lambda toks: Identifier(toks[0]))
)
true = Literal("true") | Literal("True")
false = Literal("false") | Literal("False")
boolean = (
    (true | false)
    .copy()
    .add_parse_action(lambda toks: Boolean(toks[0].lower()))
)


string1 = (
    QuotedString("'").copy().add_parse_action(lambda toks: String(toks[0]))
)
string2 = (
    QuotedString('"').copy().add_parse_action(lambda toks: String(toks[0]))
)

# REVIEW(cutwater): The expression `lambda toks: OperatorExpression(*toks[0])`
#   is duplicated 8 times here. Can it be a function?
condition = infix_notation(
    integer | boolean | varname | string1 | string2,
    [
        ("+", 1, OpAssoc.RIGHT, lambda toks: ExistsExpression(*toks[0])),
        ("!", 1, OpAssoc.RIGHT),
        (
            one_of("* /"),
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpression(*toks[0]),
        ),
        (
            one_of("+ -"),
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpression(*toks[0]),
        ),
        (">=", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        ("<=", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        (
            one_of("< >"),
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpression(*toks[0]),
        ),
        ("!=", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        ("==", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        ("is not", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        ("is", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        ("and", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        ("or", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
        ("<<", 2, OpAssoc.LEFT, lambda toks: OperatorExpression(*toks[0])),
    ],
).add_parse_action(lambda toks: Condition(toks[0]))


def parse_condition(condition_string: str) -> Condition:
    return condition.parseString(condition_string)[0]
