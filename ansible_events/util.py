import jinja2
import yaml

from typing import Dict, Union

from typing import Any


def substitute_variables(value: Union[str, int], context: Dict) -> Union[str, int]:
    if isinstance(value, str):
        return jinja2.Template(value, undefined=jinja2.StrictUndefined).render(context)
    elif isinstance(value, dict):
        new_value = value.copy()
        for key, subvalue in new_value.items():
            new_value[key] = jinja2.Template(
                subvalue, undefined=jinja2.StrictUndefined
            ).render(context)
        return new_value
    else:
        return value


def load_inventory(inventory_file: str) -> Any:

    with open(inventory_file) as f:
        inventory_data = yaml.safe_load(f.read())
    return inventory_data
