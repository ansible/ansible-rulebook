import jinja2
import yaml

from ansible_events.rule_types import RuleSet
from typing import List, Dict, Union

from typing import Any


def substitute_variables(value: Union[str, int], context: Dict) -> Union[str, int]:
    if isinstance(value, str):
        return jinja2.Template(value, undefined=jinja2.StrictUndefined).render(context)
    else:
        return value


def load_inventory(inventory_file: str) -> Any:

    with open(inventory_file) as f:
        inventory_data = yaml.safe_load(f.read())
    return inventory_data
