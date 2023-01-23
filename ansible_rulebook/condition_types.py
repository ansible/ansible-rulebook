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


class Integer(NamedTuple):
    value: int


class Float(NamedTuple):
    value: float


class String(NamedTuple):
    value: str


class Boolean(NamedTuple):
    value: str


class Identifier(NamedTuple):
    value: str


class OperatorExpression(NamedTuple):
    left: Union[Float, Integer, String, List]
    operator: str
    right: Union[Float, Integer, String, List]


class NegateExpression(NamedTuple):
    operator: str
    value: Union[Boolean, Identifier, OperatorExpression]


class ExistsExpression(NamedTuple):
    operator: str
    value: String


class Condition(NamedTuple):
    value: Union[
        Float,
        Integer,
        String,
        Identifier,
        OperatorExpression,
        ExistsExpression,
        NegateExpression,
    ]


ConditionTypes = Union[
    List,
    Condition,
    OperatorExpression,
    Identifier,
    String,
    Integer,
    Float,
    ExistsExpression,
    NegateExpression,
]
