
from typing import NamedTuple, Union, List



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

class ExistsExpression(NamedTuple):
    operator: str
    value: String

class Condition(NamedTuple):
    value: Union[Integer, String,  Identifier, OperatorExpression, ExistsExpression]

ConditionTypes = Union[List, Condition, OperatorExpression, Identifier, String, Integer, ExistsExpression]
