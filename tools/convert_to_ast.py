import argparse
import json
import os
import sys
from pathlib import Path
from typing import List

import yaml

from ansible_rulebook.json_generator import visit_ruleset
from ansible_rulebook.rules_parser import parse_rule_sets


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-r",
        "--rulebook",
        help="The rulebook file or rulebook from a collection",
        required=True,
    )
    parser.add_argument(
        "-e",
        "--vars",
        help="Variables file",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="output ast file",
    )
    parser.add_argument(
        "-E",
        "--env-vars",
        help=(
            "Comma separated list of variables to import from the environment"
        ),
    )
    return parser


def load_rules(rules_file, variables):
    with open(rules_file) as f:
        data = yaml.safe_load(f.read())

    return parse_rule_sets(data, variables)


def main(args: List[str] = None) -> int:
    parser = get_parser()
    cmdline_args = parser.parse_args(args)

    variables = {}
    if cmdline_args.vars:
        with open(cmdline_args.vars) as f:
            variables = yaml.safe_load(f.read())

    if cmdline_args.env_vars:
        for var in cmdline_args.env_vars.split(","):
            variables[var] = os.environ.get(var)

    file_name = cmdline_args.rulebook
    if cmdline_args.output:
        ast_file_name = cmdline_args.output
        ast_file_json = f"{ast_file_name}.json"
    else:
        ast_file_name = f"{Path(file_name).stem}_ast.yml"
        ast_file_json = f"{Path(file_name).stem}_ast.json"

    ruleset_asts = []
    for ruleset in load_rules(file_name, variables):
        ruleset_asts.append(visit_ruleset(ruleset, variables))

    with open(ast_file_name, "w") as f:
        yaml.dump(ruleset_asts, f)

    with open(ast_file_json, "w") as outfile:
        json.dump(ruleset_asts, outfile, indent=4)


if __name__ == "__main__":
    sys.exit(main())
