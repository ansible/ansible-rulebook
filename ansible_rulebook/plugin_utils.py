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

from typing import Any, Dict, NoReturn

import dpath


def insert_hosts_to_meta(
    event_data: Dict[str, Any], args: Dict[str, Any]
) -> NoReturn:
    """Find hosts and insert them to the meta dict in an event

    When ansible-rulebook runs a playbook it automatically fetches hosts in
    the meta dict in the event data and limit the playbook running only on
    the selected hosts. This function helps to extract hosts from the original
    event data and insert them to the meta dict. It is a helper method for
    plugin development.

    Parameters
    ----------
    event_data: Dict[str, Any]
        The original event data containing the hosts. Hosts meta will be
        inserted to the same data.
    args: Dict[str, Any]
        The parameters passed to the plugin to start the main. The following
        keys are searched:
            data_host_path: The json path inside the event data to find hosts.
                            Do nothing if the key is not present.
            data_path_separator: The separator to interpret data_host_path.
                                 Default to "."
            data_host_separator: The separator to interpet host string.
                                 data_host_path can point to a string or a
                                 list. If it is a single string but contains
                                 multiple hosts, use this parameter to delimits
                                 the hosts. Treat the vale as a single host if
                                 the key is not present.
    Raises
    ------
    TypeError
        If data_host_path points to a value that cannot be interpret as a host
        or a list of hosts
    """
    if "data_host_path" not in args:
        return

    host_path = str(args.get("data_host_path"))
    path_separator = str(args.get("data_path_separator", "."))
    host_separator = str(args.get("data_host_separator", ""))

    try:
        hosts = dpath.get(event_data, host_path, path_separator)
    except KeyError:
        # does not contain host
        return

    if isinstance(hosts, str):
        hosts = hosts.split(host_separator) if host_separator else [hosts]
    elif isinstance(hosts, list) or isinstance(hosts, tuple):
        for h in hosts:
            if not isinstance(h, str):
                raise TypeError(f"{h} is not a valid hostname")
    else:
        raise TypeError(f"{hosts} is not a valid hostname")

    if "meta" not in event_data:
        event_data["meta"] = {}
    event_data["meta"]["hosts"] = hosts
