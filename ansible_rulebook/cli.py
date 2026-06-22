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
import logging
import os
import signal
import sys
from typing import List

import ansible_rulebook.util as util
from ansible_rulebook.exception import (
    SourceFilterNotFoundException,
    SourcePluginMainMissingException,
    SourcePluginNotAsyncioCompatibleException,
    SourcePluginNotFoundException,
)
from ansible_rulebook.messages import DEFAULT_SHUTDOWN_DELAY
from ansible_rulebook.vault import Vault

# ensure a valid JVM is available and configures JAVA_HOME if necessary
# must be done before importing any other modules
util.check_jvm()
if not os.environ.get("JAVA_HOME"):
    os.environ["JAVA_HOME"] = util.get_java_home()

from ansible_rulebook import app  # noqa: E402
from ansible_rulebook import terminal  # noqa: E402
from ansible_rulebook.conf import settings  # noqa: E402
from ansible_rulebook.job_template_runner import (  # noqa: E402
    job_template_runner,
)

display = terminal.Display()

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
        version=util.get_version(),
    )
    parser.add_argument(
        "-S",
        "--source-dir",
        help="Local event source plugins dir for development.",
    )
    parser.add_argument(
        "-F",
        "--filter-dir",
        help="Local event source filters dir for development.",
    )
    parser.add_argument(
        "-i",
        "--inventory",
        help="Path to an inventory file, "
        "can also be passed via the env var ANSIBLE_INVENTORY",
        default=os.environ.get("ANSIBLE_INVENTORY", ""),
    )
    parser.add_argument(
        "-W",
        "--websocket-url",
        "--websocket-address",
        help="Connect the event log to a websocket, "
        "can also be passed via the env var EDA_WEBSOCKET_URL.",
        default=os.environ.get("EDA_WEBSOCKET_URL", ""),
    )
    parser.add_argument(
        "--websocket-ssl-verify",
        help="How to verify SSL when connecting to the "
        "websocket: (yes|true) | (no|false) | <path to a CA bundle>, "
        "default to yes for wss connection, "
        "can also be passed via the env var EDA_WEBSOCKET_SSL_VERIFY.",
        default=os.environ.get("EDA_WEBSOCKET_SSL_VERIFY", "yes"),
    )
    parser.add_argument(
        "--websocket-access-token",
        help="Token used to autheticate the websocket connection, "
        "can also be passed via the env var EDA_WEBSOCKET_ACCESS_TOKEN",
        default=os.environ.get("EDA_WEBSOCKET_ACCESS_TOKEN", ""),
    )
    parser.add_argument(
        "--websocket-refresh-token",
        help="Token used to renew a websocket access token, "
        "can also be passed via the env var EDA_WEBSOCKET_REFRESH_TOKEN",
        default=os.environ.get("EDA_WEBSOCKET_REFRESH_TOKEN", ""),
    )
    parser.add_argument(
        "--websocket-token-url",
        help="Url to renew websocket access token, "
        "can also be passed via the env var EDA_WEBSOCKET_TOKEN_URL",
        default=os.environ.get("EDA_WEBSOCKET_TOKEN_URL", ""),
    )
    parser.add_argument(
        "--id",
        help="Identifier, the activation_instance id which allows "
        "the results to be communicated back to the websocket.",
    )
    parser.add_argument(
        "--persistence-id",
        help="Identifier, the persistence id which allows "
        "for the data to be saved across multiple restarts.",
    )
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
        "passed via the env var EDA_CONTROLLER_URL, if your URL has a path "
        "it should include api in it. api would only be appended if the URL "
        "only contains host, port.",
        default=os.environ.get("EDA_CONTROLLER_URL", ""),
    )
    parser.add_argument(
        "--controller-token",
        help="Controller API authentication token, can also be passed "
        "via env var EDA_CONTROLLER_TOKEN",
        default=os.environ.get("EDA_CONTROLLER_TOKEN", ""),
    )
    parser.add_argument(
        "--controller-username",
        help="Controller API authentication username, can also be passed "
        "via env var EDA_CONTROLLER_USERNAME",
        default=os.environ.get("EDA_CONTROLLER_USERNAME", ""),
    )
    parser.add_argument(
        "--controller-password",
        help="Controller API authentication password, can also be passed "
        "via env var EDA_CONTROLLER_PASSWORD",
        default=os.environ.get("EDA_CONTROLLER_PASSWORD", ""),
    )
    parser.add_argument(
        "--controller-ssl-verify",
        help="How to verify SSL when connecting to the "
        "controller: (yes|true) | (no|false) | <path to a CA bundle>, "
        "default to yes for https connection, "
        "can also be passed via env var EDA_CONTROLLER_SSL_VERIFY",
        default=os.environ.get("EDA_CONTROLLER_SSL_VERIFY", "yes"),
    )
    parser.add_argument(
        "--controller-retry-max-timeout",
        type=float,
        help="Maximum backoff time in seconds for controller API retries "
        "on transient errors (502/503/504). Default is 60. "
        "Can also be passed via env var EDA_CONTROLLER_RETRY_MAX_TIMEOUT",
        default=os.environ.get(
            "EDA_CONTROLLER_RETRY_MAX_TIMEOUT",
            settings.controller_retry_max_timeout,
        ),
    )
    parser.add_argument(
        "--controller-retry-attempts",
        type=int,
        help="Number of retry attempts for controller API calls "
        "on transient errors. Default is 5. "
        "Can also be passed via env var "
        "EDA_CONTROLLER_RETRY_ATTEMPTS",
        default=os.environ.get(
            "EDA_CONTROLLER_RETRY_ATTEMPTS",
            settings.controller_retry_attempts,
        ),
    )
    parser.add_argument(
        "--print-events",
        action="store_true",
        default=settings.print_events,
        help="Print events to stdout, redundant and disabled with -vv",
    )
    parser.add_argument(
        "--shutdown-delay",
        default=os.environ.get("EDA_SHUTDOWN_DELAY", DEFAULT_SHUTDOWN_DELAY),
        type=float,
        help="Maximum number of seconds to wait after issuing a "
        "graceful shutdown, default: 60. The process will shutdown if "
        "all actions complete before this time period. "
        "Can also be passed via the env var EDA_SHUTDOWN_DELAY",
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
    parser.add_argument(
        "--skip-audit-events",
        action="store_true",
        default=settings.skip_audit_events,
        help="Don't send audit events to the server",
    )
    parser.add_argument(
        "--vault-password-file",
        help="The file containing one ansible vault password, "
        "can also be passed via the env var EDA_VAULT_PASSWORD_FILE.",
        default=os.environ.get("EDA_VAULT_PASSWORD_FILE", ""),
    )
    parser.add_argument(
        "--vault-id",
        help="label@filename pointing to an ansible vault password file",
        action="append",
        default=[],
    )
    parser.add_argument(
        "--ask-vault-pass",
        help="Ask vault password interactively",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-m",
        "--max-concurrent-actions",
        help="For parallel execution strategy the maximum number of "
        "concurrent actions. Default is 25 when using parallel strategy. "
        "Only applies to parallel execution strategy. "
        "It can also be passed via the env var EDA_MAX_CONCURRENT_ACTIONS",
        default=os.environ.get("EDA_MAX_CONCURRENT_ACTIONS", "0"),
        type=int,
    )
    parser.add_argument(
        "--max-back-pressure-timeout",
        help="When a back pressure is applied due to actions or reporting "
        "objects being at capacity, how long should we wait before failing "
        "Default is 3600 seconds. It can also "
        "be passed via the env var EDA_MAX_BACK_PRESSURE_TIMEOUT",
        default=os.environ.get("EDA_MAX_BACK_PRESSURE_TIMEOUT", "3600"),
        type=int,
    )
    parser.add_argument(
        "--max-reporting-queue-size",
        help="For rule audits we send back reporting objects, this queue "
        "size is to specify the backlog of reporting objects to be flushed "
        "to the EDA Server default is 50. Increasing this may cause OOM "
        "It can be passed via the env var EDA_MAX_REPORTING_QUEUE_SIZE",
        default=os.environ.get("EDA_MAX_REPORTING_QUEUE_SIZE", "50"),
        type=int,
    )
    parser.add_argument(
        "--max-batch-job-polling-size",
        help="Maximum number of jobs to include in a single batch polling "
        "request to the controller. Default is 25. "
        "It can be passed via the env var EDA_MAX_BATCH_JOB_POLLING_SIZE",
        default=os.environ.get("EDA_MAX_BATCH_JOB_POLLING_SIZE", "25"),
        type=int,
    )
    parser.add_argument(
        "--syntax-check",
        dest="syntax_check",
        action="store_true",
        default=False,
        help="Perform a syntax check on the rulebook, but do not execute it",
    )

    return parser


def validate_args(args: argparse.Namespace) -> None:
    if args.worker and (not args.id or not args.websocket_url):
        raise ValueError("Worker mode needs an id and websocket url specfied")
    if not args.worker and not args.rulebook:
        raise ValueError("Rulebook must be specified in non worker mode")
    if args.syntax_check and args.worker:
        raise ValueError("--syntax-check is not compatible with --worker mode")
    if args.syntax_check and not args.rulebook:
        raise ValueError("--syntax-check requires --rulebook to be specified")


def setup_logging_and_display(args: argparse.Namespace) -> None:
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    stream = sys.stderr
    level = logging.WARNING

    if args.verbosity >= 2:
        level = logging.DEBUG
        stream = sys.stdout
    elif args.verbosity == 1:
        level = logging.INFO
        stream = sys.stdout

    logging.basicConfig(stream=stream, level=level, format=LOG_FORMAT)
    logging.getLogger("drools.").setLevel(level)

    # As Display is a singleton if it was created elsewhere we may need to
    # adjust the level.
    if display.level > level:
        display.level = level


def update_settings(args: argparse.Namespace) -> None:
    """Update settings from CLI arguments.

    Since argparse already uses env vars as defaults, we directly assign
    values from args to settings. CLI args take priority over env vars.

    Note: Do NOT call settings.update_from_env() here - that's only for
    when the websocket handler updates env vars later.
    """
    # Special case: identifier is not in ENV_MAP but can be set via CLI
    if args.id:
        settings.identifier = args.id

    # Direct assignments - argparse already handled env var defaults
    if args.gc_after is not None:
        settings.gc_after = args.gc_after

    if args.execution_strategy:
        settings.default_execution_strategy = args.execution_strategy

    if args.persistence_id:
        settings.persistence_id = args.persistence_id

    if args.max_concurrent_actions > 0:
        settings.max_concurrent_actions = args.max_concurrent_actions

    settings.print_events = args.print_events
    settings.websocket_url = args.websocket_url
    settings.websocket_ssl_verify = args.websocket_ssl_verify
    settings.websocket_token_url = args.websocket_token_url
    settings.websocket_access_token = args.websocket_access_token
    settings.websocket_refresh_token = args.websocket_refresh_token
    settings.skip_audit_events = args.skip_audit_events
    settings.max_back_pressure_timeout = args.max_back_pressure_timeout
    settings.max_reporting_queue_size = args.max_reporting_queue_size
    settings.max_batch_job_polling_size = args.max_batch_job_polling_size
    settings.controller_retry_max_timeout = float(
        args.controller_retry_max_timeout
    )
    settings.controller_retry_attempts = int(args.controller_retry_attempts)
    parse_vault_passwords(args)


def parse_vault_passwords(args: argparse.Namespace) -> None:
    if (
        not args.vault_password_file
        and not args.vault_id
        and not args.ask_vault_pass
    ):
        return

    secret_files = []
    validated_password_file = None
    validated_vault_ids = []

    # Validate vault password file
    if args.vault_password_file:
        try:
            validated_password_file = util.validate_file_path(
                args.vault_password_file, "Vault password file"
            )
            secret_files.append(validated_password_file)
        except ValueError as e:
            logger.error(f"Invalid vault password file: {e}")  # NOSONAR
            sys.exit(1)

    # Validate vault ID files (format: label@filename)
    for vault_id in args.vault_id:
        if "@" in vault_id:
            label, filename = vault_id.split("@", 1)
            try:
                validated_filename = util.validate_file_path(
                    filename, "Vault ID file"
                )
                validated_vault_id = f"{label}@{validated_filename}"
                validated_vault_ids.append(validated_vault_id)
                secret_files.append(validated_filename)
            except ValueError as e:
                logger.error(  # NOSONAR
                    f"Invalid vault ID file '{vault_id}': {e}"
                )
                sys.exit(1)
        else:
            validated_vault_ids.append(vault_id)

    settings.vault = Vault(
        password_file=validated_password_file,
        vault_ids=validated_vault_ids,
        ask_pass=args.ask_vault_pass,
    )


def setup_signal_handlers() -> None:
    """Setup signal handlers for graceful shutdown."""

    def signal_handler(signum, frame):
        sig_name = signal.Signals(signum).name
        logger.info(
            f"Received signal {sig_name} ({signum}), initiating shutdown"
        )
        raise KeyboardInterrupt(f"Signal {sig_name} received")

    # Register handlers for SIGTERM and SIGINT
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    logger.debug("Signal handlers registered for SIGTERM and SIGINT")


def main(args: List[str] = None) -> int:
    parser = get_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    args = parser.parse_args(args)
    validate_args(args)
    update_settings(args)
    setup_logging_and_display(args)
    setup_signal_handlers()

    if args.controller_url:
        job_template_runner.host = args.controller_url
        if args.controller_ssl_verify:
            job_template_runner.verify_ssl = args.controller_ssl_verify

        if args.controller_token:
            job_template_runner.token = args.controller_token
        elif args.controller_username and args.controller_password:
            job_template_runner.username = args.controller_username
            job_template_runner.password = args.controller_password
        else:
            print(
                "Error: controller_token or",
                "controller_username and controller_password is required",
            )
            return 1

    try:
        asyncio.run(app.run(args))
    except KeyboardInterrupt:
        return 0
    except (
        SourcePluginNotFoundException,
        SourceFilterNotFoundException,
        SourcePluginMainMissingException,
        SourcePluginNotAsyncioCompatibleException,
    ) as err:
        logger.error("Terminating due to source error: %s", str(err))
        return 1
    except Exception as err:
        logger.error("Terminating: %s", str(err))
        return 1
    finally:
        settings.vault.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
