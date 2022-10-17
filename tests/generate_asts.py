#!/usr/bin/env python3

import os
import traceback

import yaml

from ansible_rulebook.json_generator import generate_dict_rulesets
from ansible_rulebook.rules_parser import parse_rule_sets

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    rules = list(os.walk(os.path.join(HERE, "rules")))
    rules.extend(list(os.walk(os.path.join(HERE, "examples"))))
    for root, _, files in rules:
        for file in files:
            if file.endswith(".yml"):
                print(os.path.join(root, file))
                try:
                    with open(os.path.join(root, file)) as f:
                        data = yaml.safe_load(f.read())
                        ruleset = generate_dict_rulesets(
                            parse_rule_sets(data), {}
                        )

                    with open(os.path.join(HERE, "asts", file), "w") as f:
                        f.write(yaml.dump(ruleset))
                except Exception:
                    data = None
                    ruleset = None
                    traceback.print_exc()


if __name__ == "__main__":
    main()
