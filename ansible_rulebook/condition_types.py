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

from typing import List, NamedTuple, Union

from .exception import InvalidTypeException


class Integer(NamedTuple):
    value: int


class Float(NamedTuple):
    value: float


class String(NamedTuple):
    value: str


class Boolean(NamedTuple):
    value: str


class Null(NamedTuple):
    value = None


class Identifier(NamedTuple):
    value: str


class KeywordValue(NamedTuple):
    name: String
    value: Union[Integer, String, Boolean]


class SearchType(NamedTuple):
    kind: String
    pattern: String
    options: List[KeywordValue] = None


class SelectattrType(NamedTuple):
    key: String
    operator: String
    value: Union[Float, Integer, String, Boolean, List]


class SelectType(NamedTuple):
    operator: String
    value: Union[Float, Integer, String, Boolean, List]


class OperatorExpression(NamedTuple):
    left: Union[Float, Integer, String, List]
    operator: str
    right: Union[Float, Integer, String, List, SearchType, SelectType]


class NegateExpression(NamedTuple):
    operator: str
    value: Union[Boolean, Identifier, OperatorExpression]


class Condition(NamedTuple):
    value: Union[
        Float,
        Integer,
        String,
        Identifier,
        OperatorExpression,
        NegateExpression,
        KeywordValue,
        SearchType,
        SelectattrType,
        SelectType,
    ]


ConditionTypes = Union[
    List,
    Condition,
    OperatorExpression,
    Identifier,
    String,
    Integer,
    Float,
    NegateExpression,
    KeywordValue,
    SearchType,
    SelectType,
    SelectattrType,
]


def to_condition_type(value):
    if isinstance(value, int):
        return Integer(value)
    elif isinstance(value, bool):
        return Boolean(value)
    elif isinstance(value, str):
        return String(value)
    elif isinstance(value, float):
        return Float(value)
    elif isinstance(value, type(None)):
        return Null()
    elif isinstance(value, list):
        return [to_condition_type(v) for v in value]
    else:
        raise InvalidTypeException(f"Invalid type for {value}")
