
from typing import NamedTuple, Union


class Fact(NamedTuple):
    data: dict


class Event(NamedTuple):
    data: dict


FactEvent = Union(Fact, Event)
