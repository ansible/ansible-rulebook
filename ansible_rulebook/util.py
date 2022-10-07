import os
from pprint import pprint
from typing import Any, Dict, List, Union

import jinja2
import yaml


def get_horizontal_rule(character):
    try:
        return character * int(os.get_terminal_size()[0])
    except OSError:
        return character * 80


def render_string(value: str, context: Dict) -> str:
    return jinja2.Template(value, undefined=jinja2.StrictUndefined).render(
        context
    )


def render_string_or_return_value(value: Any, context: Dict) -> Any:
    if isinstance(value, str):
        return render_string(value, context)
    return value


def substitute_variables(
    value: Union[str, int, Dict, List], context: Dict
) -> Union[str, int, Dict, List]:
    if isinstance(value, str):
        return render_string_or_return_value(value, context)
    elif isinstance(value, list):
        new_value = []
        for item in value:
            new_value.append(render_string_or_return_value(item, context))
        return new_value
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


def json_count(data):
    s = 0
    q = []
    q.append(data)
    while q:
        o = q.pop()
        if isinstance(o, dict):
            s += len(o)
            if len(o) > 255:
                pprint(data)
                raise Exception(
                    f"Only 255 values supported per dictionary found {len(o)}"
                )
            if s > 255:
                pprint(data)
                raise Exception(
                    f"Only 255 values supported per dictionary found {s}"
                )
            for i in o.values():
                q.append(i)
