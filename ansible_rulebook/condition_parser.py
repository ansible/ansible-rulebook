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

from ansible_rulebook.condition_types import (  # noqa: E402
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


def OperatorExpressionFactory(tokens):
    return_value = None
    while tokens:
        if return_value is None:
            return_value = OperatorExpression(tokens[0], tokens[1], tokens[2])
            tokens = tokens[3:]
        else:
            return_value = OperatorExpression(
                return_value, tokens[0], tokens[1]
            )
            tokens = tokens[2:]
    return return_value


condition = infix_notation(
    integer | boolean | varname | string1 | string2,
    [
        ("+", 1, OpAssoc.RIGHT, lambda toks: ExistsExpression(*toks[0])),
        ("!", 1, OpAssoc.RIGHT),
        (
            one_of("* /"),
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            one_of("+ -"),
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            ">=",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "<=",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            one_of("< >"),
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "!=",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "==",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "is not",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "is",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "and",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "or",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
        (
            "<<",
            2,
            OpAssoc.LEFT,
            lambda toks: OperatorExpressionFactory(toks[0]),
        ),
    ],
).add_parse_action(lambda toks: Condition(toks[0]))


def parse_condition(condition_string: str) -> Condition:
    return condition.parseString(condition_string)[0]
