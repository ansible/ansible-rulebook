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


def parse_inventory_pattern(pattern):
    return [i.strip() for i in pattern.split(",")]


def matches_host(subpattern, host):
    if subpattern == "all" and host == "localhost":
        return False
    elif subpattern == "all":
        return True
    elif subpattern == host:
        return True
    return False


def matching_hosts(inventory, pattern):
    subpatterns = parse_inventory_pattern(pattern)
    hosts = []
    for group in inventory.values():
        for host in group.get("hosts").keys():
            for sp in subpatterns:
                if matches_host(sp, host):
                    hosts.append(host)
                    break
    return hosts
