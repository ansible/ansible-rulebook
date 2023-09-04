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


import argparse
import asyncio
import importlib.metadata
import logging
import os
import sys
from typing import List

import ansible_rulebook.util as util
from ansible_rulebook.messages import DEFAULT_SHUTDOWN_DELAY

# ensure a valid JVM is available and configures JAVA_HOME if necessary
# must be done before importing any other modules
util.check_jvm()
if not os.environ.get("JAVA_HOME"):
    os.environ["JAVA_HOME"] = util.get_java_home()


import ansible_rulebook  # noqa: E402
from ansible_rulebook import app  # noqa: E402
from ansible_rulebook.conf import settings  # noqa: E402
from ansible_rulebook.job_template_runner import (  # noqa: E402
    job_template_runner,
)

DEFAULT_VERBOSITY = 0

logger = logging.getLogger(__name__)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-r",
        "--rulebook",
        help="The rulebook file or rulebook from a collection",
    )
    parser.add_argument(
        "-e",
        "--vars",
        help="Variables file",
    )
    parser.add_argument(
        "-E",
        "--env-vars",
        help=(
            "Comma separated list of variables to import from the environment"
        ),
    )
    parser.add_argument(
        "-v",
        "--verbose",
        dest="verbosity",
        default=DEFAULT_VERBOSITY,
        action="count",
        help="Causes ansible-rulebook to print more debug messages. "
        "Adding multiple -v will increase the verbosity, "
        "the default value is 0. The maximum value is 2. "
        "Events debugging might require -vv.",
    )
    parser.add_argument(
        "--version",
        action="version",
        help="Show the version and exit",
        version=get_version(),
    )
    parser.add_argument(
        "-S",
        "--source-dir",
        help="Source dir",
    )
    parser.add_argument(
        "-i",
        "--inventory",
        help="Inventory",
        default=os.environ.get("ANSIBLE_INVENTORY", ""),
    )
    parser.add_argument(
        "-W",
        "--websocket-address",
        "--websocket-url",
        help="Connect the event log to a websocket",
    )
    parser.add_argument(
        "--websocket-ssl-verify",
        help="How to verify SSL when connecting to the "
        "websocket, yes|no|<path to a CA bundle>, "
        "default to yes for wss connection.",
        default="yes",
    )
    parser.add_argument("--id", help="Identifier")
    parser.add_argument(
        "-w",
        "--worker",
        action="store_true",
        help="Enable worker mode",
        default=False,
    )
    parser.add_argument(
        "-T",
        "--project-tarball",
        help="A tarball of the project",
    )
    parser.add_argument(
        "--controller-url",
        help="Controller API base url, e.g. https://host1:8080 can also be "
        "passed via the env var EDA_CONTROLLER_URL",
        default=os.environ.get("EDA_CONTROLLER_URL", ""),
    )
    parser.add_argument(
        "--controller-token",
        help="Controller API authentication token, can also be passed "
        "via env var EDA_CONTROLLER_TOKEN",
        default=os.environ.get("EDA_CONTROLLER_TOKEN", ""),
    )
    parser.add_argument(
        "--controller-ssl-verify",
        help="How to verify SSL when connecting to the "
        "controller, yes|no|<path to a CA bundle>, "
        "default to yes for https connection."
        "can also be passed via env var EDA_CONTROLLER_SSL_VERIFY",
        default=os.environ.get("EDA_CONTROLLER_SSL_VERIFY", "yes"),
    )
    parser.add_argument(
        "--print-events",
        action="store_true",
        help="Print events to stdout, redundant and disabled with -vv",
    )
    parser.add_argument(
        "--shutdown-delay",
        default=os.environ.get("EDA_SHUTDOWN_DELAY", DEFAULT_SHUTDOWN_DELAY),
        type=float,
        help="Maximum number of seconds to wait after issuing a "
        "graceful shutdown, default: 60. The process will shutdown if "
        "all actions complete before this time period",
    )
    parser.add_argument(
        "--gc-after",
        default=os.environ.get("EDA_GC_AFTER", settings.gc_after),
        type=int,
        help="Run the garbage collector after this number of events. "
        "It can be configured with the environment variable EDA_GC_AFTER",
    )
    parser.add_argument(
        "--heartbeat",
        default=0,
        type=int,
        help="Send heartbeat to the server after every n seconds"
        "Default is 0, no heartbeat is sent",
    )
    parser.add_argument(
        "--execution-strategy",
        default=settings.default_execution_strategy,
        choices=["sequential", "parallel"],
        help="Actions can be executed in sequential order or in parallel."
        "Default is sequential, actions will be run only after the "
        "previous one ends",
    )
    parser.add_argument(
        "--hot-reload",
        help="Will perform hot-reload on rulebook file changes "
        "(when running in non-worker mode)."
        "This option is ignored in worker mode.",
        default="false",
        action="store_true",
    )
    return parser


def get_version() -> str:
    java_home = util.get_java_home()
    java_version = util.get_java_version()
    result = [
        f"{ansible_rulebook.__version__}",
        f"  Executable location = {sys.argv[0]}",
        f"  Drools_jpy version = {importlib.metadata.version('drools_jpy')}",
        f"  Java home = {java_home}",
        f"  Java version = {java_version}",
        f"  Python version = {''.join(sys.version.splitlines())}",
    ]
    return "\n".join(result)


def validate_args(args: argparse.Namespace) -> None:
    if args.worker and (not args.id or not args.websocket_address):
        raise ValueError(
            "Worker mode needs an id and websocket address specfied"
        )
    if not args.worker and not args.rulebook:
        raise ValueError("Rulebook must be specified in non worker mode")


def setup_logging(args: argparse.Namespace) -> None:
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    stream = sys.stderr
    level = logging.WARNING

    if args.verbosity >= 2:
        level = logging.DEBUG
        stream = sys.stdout
        args.print_events = False
    elif args.verbosity == 1:
        level = logging.INFO
        stream = sys.stdout

    logging.basicConfig(stream=stream, level=level, format=LOG_FORMAT)
    logging.getLogger("drools.").setLevel(level)


def main(args: List[str] = None) -> int:
    parser = get_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args(args)
    validate_args(args)

    if args.controller_url:
        if args.controller_token:
            job_template_runner.host = args.controller_url
            job_template_runner.token = args.controller_token
            if args.controller_ssl_verify:
                job_template_runner.verify_ssl = args.controller_ssl_verify
        else:
            print("Error: controller_token is required")
            return 1

    if args.id:
        settings.identifier = args.id

    if args.gc_after is not None:
        settings.gc_after = args.gc_after

    if args.execution_strategy:
        settings.default_execution_strategy = args.execution_strategy

    setup_logging(args)

    try:
        asyncio.run(app.run(args))
    except KeyboardInterrupt:
        return 0
    except Exception as err:
        logger.error("Terminating %s", str(err))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
