"""
Usage:
    ansible-rulebook [options]

Options:
    -h, --help                  Show this page
    -v, --vars=<v>              Variables file
    -i, --inventory=<i>         Inventory
    --rulebook=<r>              The rulebook file or rulebook from a collection
    -S=<S>, --source_dir=<S>    Source dir
    --vars=<v>                  A vars file
    --env-vars=<e>              Comma separated list of variables to import
                                from the environment
    --redis_host_name=<h>       Redis host name
    --redis_port=<p>            Redis port
    --debug                     Show debug logging
    --verbose                   Show verbose logging
    --version                   Show the version and exit
    --websocket-address=<w>     Connect the event log to a websocket
    --id=<i>                    Identifier
    --worker                    Enable worker mode
    --project-tarball=<p>       Project tarball
"""
import argparse
import asyncio
import logging
import os
import sys
from typing import List, NoReturn

import ansible_rulebook
from ansible_rulebook import app
from ansible_rulebook.conf import settings

logger = logging.getLogger(__name__)


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rulebook",
        help="The rulebook file or rulebook from a collection",
    )
    parser.add_argument(
        "--vars",
        help="Variables file",
    )
    parser.add_argument(
        "--env-vars",
        help=(
            "Comma separated list of variables to import from the environment"
        ),
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug logging",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose logging",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show the version and exit",
    )
    parser.add_argument(
        "--redis-host-name",
        help="Redis host name",
    )
    parser.add_argument(
        "--redis-port",
        help="Redis port",
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
    )
    parser.add_argument(
        "--websocket-address",
        help="Connect the event log to a websocket",
    )
    parser.add_argument("--id", help="Identifier", type=int)
    parser.add_argument(
        "--worker",
        action="store_true",
        help="Enable worker mode",
    )
    parser.add_argument(
        "--project-tarball",
        help="A tarball of the project",
    )
    return parser


def show_version() -> NoReturn:
    print(ansible_rulebook.__version__)
    print(settings.identifier)
    sys.exit(0)


def setup_logging(args: argparse.Namespace) -> None:
    if args.debug:
        level = logging.DEBUG
    elif args.verbose:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level)


def main(args: List[str] = None) -> int:
    parser = get_parser()
    args = parser.parse_args(args)

    if os.environ.get("RULES_ENGINE", "drools") == "drools":
        if os.environ.get("JAVA_HOME") is None:
            print(
                "JAVA_HOME is not set. "
                "Please install Java 11+ and set JAVA_HOME"
            )
            sys.exit(1)

    if args.version:
        show_version()

    if args.rulebook and not args.inventory:
        print("Error: inventory is required")
        return 1

    if args.id:
        settings.identifier = args.id

    setup_logging(args)

    try:
        asyncio.run(app.run(args))
    except KeyboardInterrupt:
        return 0
    except Exception:
        logger.exception("Unexpected exception")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
