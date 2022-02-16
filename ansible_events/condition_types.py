
from typing import NamedTuple, Union



class Integer(NamedTuple):
    value: int


class String(NamedTuple):
    value: str


class Identifier(NamedTuple):
    value: str


class OperatorExpression(NamedTuple):
    left: Union[Integer, String]
    operator: str
    right: Union[Integer, String]

class Condition(NamedTuple):
    value: Union[Integer, String,  Identifier, OperatorExpression]

ConditionTypes = Union[Condition, OperatorExpression, Identifier, String, Integer]
