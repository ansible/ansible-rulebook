import jinja2
import yaml
import os
import json
import multiprocessing as mp
import dpath.util
from .filters.lookup import lookup

from typing import Dict, Union

from typing import Any

jinja2_env = jinja2.Environment(undefined=jinja2.StrictUndefined)
jinja2_env.globals["lookup"] = lookup

def get_horizontal_rule(character):
    try:
        return character * int(os.get_terminal_size()[0])
    except OSError:
        return character * 80


def render_string(value: str, context: Dict) -> str:
    return jinja2_env.from_string(value).render(context)


def render_string_or_return_value(value: Any, context: Dict) -> Any:
    if isinstance(value, str):
        if value.startswith('{{') and value.endswith('}}'):
            try:
                return dpath.util.get(context, value[2:-2], separator='.')
            except KeyError:
                return render_string(value, context)
        else:
            return render_string(value, context)


def substitute_variables(value: Union[str, int, Dict], context: Dict) -> Union[str, int, Dict]:
    if isinstance(value, str):
        return render_string_or_return_value(value, context)
    elif isinstance(value, dict):
        new_value = value.copy()
        for key, subvalue in new_value.items():
            new_value[key] = render_string_or_return_value(subvalue, context)
        return new_value
    else:
        return value


def load_inventory(inventory_file: str) -> Any:

    with open(inventory_file) as f:
        inventory_data = yaml.safe_load(f.read())
    return inventory_data
