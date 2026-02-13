"""
Test ansible-rulebook with periodic process restarts
to verify event persistence and recovery
"""

import asyncio
import fcntl
import logging
import os
import platform
import shutil
import signal
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Union

import dpath
import pytest
import websockets.asyncio.server as ws_server
import yaml

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 30
RESTART_INTERVAL = 3  # seconds between restarts
NUM_RESTARTS = 3  # number of times to restart the process

TEST_DATA = [
    (
        {
            "rules_triggered": 1,
            "events_processed": 10,
            "events_matched": 3,
            "number_of_actions": 1,
            "number_of_session_stats": 6,
            "number_of_rules": 1,
            "number_of_disabled_rules": 0,
        },
        utils.BASE_DATA_PATH / "rulebooks/persistence/multi_event_rule.yml",
        [
            {
                "rule_name": "r1",
                "action": "debug",
                "events": [
                    {"key": "m_2/i", "value": 7},
                    {"key": "m_0/i", "value": 1},
                    {"key": "m_1/i", "value": 3},
                ],
            },
        ],
        "Multi Event Rule",
    ),
    (
        {
            "rules_triggered": 4,
            "events_processed": 10,
            "events_matched": 4,
            "number_of_actions": 4,
            "number_of_session_stats": 6,
            "number_of_rules": 1,
            "number_of_disabled_rules": 0,
        },
        utils.BASE_DATA_PATH / "rulebooks/persistence/single_event_rule.yml",
        [
            {
                "rule_name": "r1",
                "action": "debug",
                "events": [{"key": "m/i", "value": 2}],
            },
            {
                "rule_name": "r1",
                "action": "debug",
                "events": [{"key": "m/i", "value": 1}],
            },
            {
                "rule_name": "r1",
                "action": "debug",
                "events": [{"key": "m/i", "value": 4}],
            },
            {
                "rule_name": "r1",
                "action": "debug",
                "events": [{"key": "m/i", "value": 3}],
            },
        ],
        "Single Event Rule",
    ),
    (
        {
            "rules_triggered": 3,
            "events_processed": 10,
            "events_matched": 3,
            "number_of_actions": 3,
            "number_of_session_stats": 6,
            "number_of_rules": 3,
            "number_of_disabled_rules": 0,
        },
        (
            utils.BASE_DATA_PATH
            / "rulebooks/persistence/single_event_different_rules.yml"
        ),
        [
            {
                "rule_name": "r1",
                "action": "debug",
                "events": [{"key": "m/i", "value": 1}],
            },
            {
                "rule_name": "r5",
                "action": "debug",
                "events": [{"key": "m/i", "value": 5}],
            },
            {
                "rule_name": "r9",
                "action": "print_event",
                "events": [{"key": "m/i", "value": 9}],
            },
        ],
        "Single Event Different Rules",
    ),
]


def setup_vars_file(temp_dir: Union[str, Path]) -> tuple[Path, Path]:
    """
    Set up the variables file with the JSON data file path.

    Args:
        temp_dir: Path to the temporary directory (string or Path object)

    Returns:
        Path to the created vars file
        Path to H2 DB File
    """
    temp_dir = Path(temp_dir)

    with open(utils.BASE_DATA_PATH / "extra_vars/drools_db_vars.yml") as f:
        vars_data = yaml.safe_load(f)

    shutil.copy2(
        utils.BASE_DATA_PATH / "data/items.json", temp_dir / "items.json"
    )
    vars_data["json_data_file"] = str(temp_dir / "items.json")
    vars_data["drools_db_file_path"] = str(temp_dir / ("test;"))
    db_path = temp_dir / "test.mv.db"

    vars_file = temp_dir / "vars.yml"
    with open(vars_file, "w") as f:
        yaml.dump(vars_data, f)

    print(vars_data["json_data_file"])
    return vars_file, db_path


def accumulate_lifecycle_stats(
    total_stats: Dict[str, Any], lifecycle_stats: Dict[str, Any]
) -> None:
    """
    Accumulate statistics from a single lifecycle into the total statistics.

    Args:
        total_stats: Dictionary containing cumulative statistics
        lifecycle_stats: Dictionary containing statistics from a single
            lifecycle
    """
    total_stats["total_events_processed"] += lifecycle_stats[
        "events_processed"
    ]
    total_stats["total_rules_triggered"] += lifecycle_stats["rules_triggered"]
    total_stats["total_events_matched"] += lifecycle_stats["events_matched"]
    total_stats["total_actions"] += lifecycle_stats["action_counter"]
    total_stats["total_session_stats"] += lifecycle_stats[
        "session_stats_counter"
    ]

    # Merge actions by rule
    for rule, count in lifecycle_stats["actions_by_rule"].items():
        total_stats["all_actions_by_rule"][rule] = (
            total_stats["all_actions_by_rule"].get(rule, 0) + count
        )

    # Merge matches found
    total_stats["all_matches_found"].extend(lifecycle_stats["matches_found"])


async def run_process_lifecycle(
    cmd: utils.Command, is_final_run: bool
) -> asyncio.subprocess.Process:
    """
    Start and manage a single process lifecycle.

    Args:
        cmd: Command to execute
        is_final_run: Whether this is the final lifecycle (no restart)

    Returns:
        The created subprocess
    """
    LOGGER.info(f"Running command: {cmd}")

    proc = await asyncio.create_subprocess_exec(
        *cmd.to_list(),
        cwd=utils.BASE_DATA_PATH,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    if not is_final_run:
        await asyncio.sleep(RESTART_INTERVAL)

    return proc


async def terminate_process(
    proc: asyncio.subprocess.Process, restart_num: int, db_path: Path
) -> None:
    """
    Gracefully terminate a process, with fallback to force kill.

    Args:
        proc: The subprocess to terminate
        restart_num: Current restart number (for logging)

    Raises:
        RuntimeError: If the process has already exited with an error
    """
    LOGGER.info(f"Killing process (restart {restart_num + 1}/{NUM_RESTARTS})")

    # Check if process has already exited with an error
    if proc.returncode is not None and proc.returncode != 0:
        error_msg = (
            f"Process exited unexpectedly with return code {proc.returncode} "
            f"during restart {restart_num + 1}/{NUM_RESTARTS}"
        )
        LOGGER.error(error_msg)

        # Read and log any output from the process
        try:
            stdout, stderr = await proc.communicate()
            if stdout:
                LOGGER.error(f"Process stdout:\n{stdout.decode()}")
            if stderr:
                LOGGER.error(f"Process stderr:\n{stderr.decode()}")
        except Exception as e:
            LOGGER.warning(f"Could not read process output: {e}")

        raise RuntimeError(error_msg)

    # Check if process exited successfully (return code 0)
    if proc.returncode == 0:
        LOGGER.info(
            "Process already completed successfully, no need to terminate"
        )
        return

    # Process is still running, terminate it gracefully
    try:
        LOGGER.warning("Sending SIGTERM to process")
        proc.send_signal(signal.SIGTERM)
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        LOGGER.warning("Process didn't terminate gracefully, forcing kill")
        proc.kill()
        await proc.wait()

    # Add a small delay to ensure the process has fully exited
    # and file handles are released
    LOGGER.info("Waiting for process cleanup...")
    await ensure_file_is_free(db_path)
    await asyncio.sleep(1)


def log_final_results(
    total_stats: Dict[str, Any],
    restart_count: int,
    lifecycle_results: List[Dict[str, Any]],
) -> None:
    """
    Log the final test results and statistics.

    Args:
        total_stats: Dictionary containing cumulative statistics
        restart_count: Number of times the process was restarted
        lifecycle_results: List of result dictionaries from each lifecycle
    """
    LOGGER.info("=" * 80)
    LOGGER.info(f"Test completed with {restart_count} restarts")
    LOGGER.info(f"Total lifecycles: {len(lifecycle_results)}")
    LOGGER.info(
        f"Total events processed across all restarts: "
        f"{total_stats['total_events_processed']}"
    )
    LOGGER.info(
        f"Total rules triggered across all restarts: "
        f"{total_stats['total_rules_triggered']}"
    )
    LOGGER.info(
        f"Total events matched across all restarts: "
        f"{total_stats['total_events_matched']}"
    )
    LOGGER.info(
        f"Total actions across all restarts: "
        f"{total_stats['total_actions']}"
    )
    LOGGER.info(
        f"Actions by rule across all restarts: "
        f"{total_stats['all_actions_by_rule']}"
    )
    LOGGER.info(
        f"Total session stats messages: {total_stats['total_session_stats']}"
    )
    LOGGER.info("=" * 80)

    for i, result in enumerate(lifecycle_results):
        LOGGER.info(f"Lifecycle {i}: {result}")

    LOGGER.info(
        f"All matches found across lifecycles: "
        f"{total_stats['all_matches_found']}"
    )


def validate_final_results(
    total_stats: Dict[str, Any],
    restart_count: int,
    rule_matches: List[Dict[str, Any]],
    counts: Dict[str, int],
) -> None:
    """
    Validate that the test results meet expectations.

    Args:
        total_stats: Dictionary containing cumulative statistics
        restart_count: Number of times the process was restarted
        rule_matches: List of expected rule matches
    """
    # Validate that all expected matches were found across all lifecycles
    for expected_match in rule_matches:
        assert expected_match in total_stats["all_matches_found"], (
            f"Expected match not found across all lifecycles: "
            f"{expected_match}. "
            f"Found matches: {total_stats['all_matches_found']}"
        )

    # Verify we got session stats from multiple lifecycles
    assert total_stats["total_session_stats"] > 1, (
        f"Expected multiple SessionStats messages, "
        f"got {total_stats['total_session_stats']}"
    )

    # Verify we had the expected number of restarts
    assert (
        restart_count == NUM_RESTARTS
    ), f"Expected {NUM_RESTARTS} restarts, got {restart_count}"

    # Note: With restarts, we might see different event counts than the
    # original test. The exact counts will depend on event persistence and
    # recovery behavior. For now, we just verify that we got some events
    # and actions
    assert (
        total_stats["total_events_processed"] > 0
    ), "No events were processed across all restarts"
    # For actions without external job tracking (debug, print_event, noop),
    # we cannot guarantee exact deduplication across process restarts due to
    # the race condition between action execution and status persistence
    assert total_stats["total_actions"] >= counts["number_of_actions"], (
        f"Expected at least {counts['number_of_actions']} actions, "
        f"got {total_stats['total_actions']}"
    )


async def process_queue_messages(
    queue: asyncio.Queue,
    endpoint: str,
    rule_matches: List[Dict[str, Any]],
    counts: Dict[str, int],
    rule_set_name: str,
    proc_id: str,
    validate_all_matches: bool = False,
) -> Dict[str, Any]:
    """
    Process all messages in the queue and return statistics.
    This is called after each process lifecycle to accumulate data.

    rule_matches: A list of expected match dictionaries with structure:
        [
            {
                "rule_name": "r1",
                "action": "debug",
                "events": [
                    {"key": "path/to/value", "value": expected_value},
                    ...
                ]
            },
            ...
        ]
        Each match represents one expected action firing. The "events" array
        defines the expected values for specific paths in the matching_events
        using dpath.

    validate_all_matches: If True, requires ALL expected matches to be
        present. If False, only validates that found matches are correct
        (but not that all are present).
    """
    action_counter = 0
    session_stats_counter = 0
    events_processed = 0
    rules_triggered = 0
    events_matched = 0
    actions_by_rule = {}

    # Track which expected matches have been found
    matches_found = []

    while not queue.empty():
        data = await queue.get()
        assert data["path"] == endpoint
        data = data["payload"]

        if data["type"] == "Action":
            action_counter += 1
            assert data["action_uuid"] is not None
            assert data["ruleset_uuid"] is not None
            assert data["rule_uuid"] is not None
            assert data["status"] == "successful"
            rule_name = data["rule"]

            # Track actions per rule
            if rule_name not in actions_by_rule:
                actions_by_rule[rule_name] = 0
            actions_by_rule[rule_name] += 1

            matching_events = data["matching_events"]
            action_type = data["action"]

            # Find which match specification this action satisfies
            match_found = None
            for expected_match in rule_matches:
                if expected_match["rule_name"] != rule_name:
                    continue
                if expected_match["action"] != action_type:
                    continue

                # Check if all event key/value pairs match
                all_events_match = True
                for event_check in expected_match["events"]:
                    try:
                        actual_value = dpath.get(
                            matching_events, event_check["key"]
                        )
                        if actual_value != event_check["value"]:
                            all_events_match = False
                            break
                    except KeyError:
                        all_events_match = False
                        break

                if all_events_match:
                    match_found = expected_match
                    matches_found.append(expected_match)
                    break

            assert match_found is not None, (
                f"Action for rule '{rule_name}' did not match any "
                f"expected patterns. "
                f"Action: {action_type}, Matching events: {matching_events}, "
                f"Expected matches: {rule_matches}"
            )

        if data["type"] == "SessionStats":
            session_stats_counter += 1
            stats = data["stats"]

            # Capture the stats from this session
            events_processed = stats.get("eventsProcessed", 0)
            rules_triggered = stats.get("rulesTriggered", 0)
            events_matched = stats.get("eventsMatched", 0)

            assert stats["ruleSetName"] == rule_set_name
            assert stats["numberOfRules"] == counts["number_of_rules"]
            assert (
                stats["numberOfDisabledRules"]
                == counts["number_of_disabled_rules"]
            )
            assert data["activation_instance_id"] == proc_id

    # Verify matches based on validation mode
    if validate_all_matches:
        # Strict validation: ALL expected matches must be found
        for expected_match in rule_matches:
            assert expected_match in matches_found, (
                f"Expected match not found: {expected_match}. "
                f"Found matches: {matches_found}"
            )
    else:
        # Lenient validation: Any matches found must be valid, but not all
        # expected matches are required. This is appropriate for partial
        # lifecycles during restarts
        pass  # Validation already done during action processing

    return {
        "action_counter": action_counter,
        "session_stats_counter": session_stats_counter,
        "events_processed": events_processed,
        "rules_triggered": rules_triggered,
        "events_matched": events_matched,
        "actions_by_rule": actions_by_rule,
        "matches_found": matches_found,
    }


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "counts, rulebook, rule_matches, rule_set_name", TEST_DATA
)
async def test_multi_restart_rulebook(
    counts: Dict[str, int],
    rulebook: Path,
    rule_matches: List[Dict[str, Any]],
    rule_set_name: str,
) -> None:
    """
    Verify that we can run an example rulebook with periodic restarts
    and track how many events get triggered across restarts.
    This tests event persistence and recovery capabilities.
    """
    # Test configuration
    host = "127.0.0.1"
    endpoint = "/api/ws2"
    proc_id = "42"
    port = utils.get_safe_port()

    async with h2_persistence_context() as temp_dir:
        # Set up the vars file
        vars_file, db_path = setup_vars_file(temp_dir)

        websocket_address = f"ws://127.0.0.1:{port}{endpoint}"
        cmd = utils.Command(
            rulebook=rulebook,
            websocket=websocket_address,
            proc_id=proc_id,
            heartbeat=2,
            vars_file=vars_file,
            persistence_id=str(uuid.uuid4()),
        )

        # Initialize tracking statistics
        total_stats = {
            "total_events_processed": 0,
            "total_rules_triggered": 0,
            "total_events_matched": 0,
            "total_actions": 0,
            "total_session_stats": 0,
            "all_actions_by_rule": {},
            "all_matches_found": [],
        }
        restart_count = 0
        lifecycle_results = []

        # Run server and ansible-rulebook
        queue = asyncio.Queue()
        handler = partial(
            utils.msg_handler, queue=queue, ignore_connection_closed=True
        )

        async with ws_server.serve(handler, host, port):
            # +1 for initial run
            for restart_num in range(NUM_RESTARTS + 1):
                LOGGER.info(
                    f"Starting process iteration "
                    f"{restart_num}/{NUM_RESTARTS}"
                )
                is_final_run = restart_num >= NUM_RESTARTS

                # Start the process
                proc = await run_process_lifecycle(cmd, is_final_run)

                if not is_final_run:
                    # Terminate the process and process the queue
                    await terminate_process(proc, restart_num, db_path)
                    restart_count += 1

                    LOGGER.info(
                        f"Processing {queue.qsize()} messages from "
                        f"lifecycle {restart_num}"
                    )
                    lifecycle_stats = await process_queue_messages(
                        queue,
                        endpoint,
                        rule_matches,
                        counts,
                        rule_set_name,
                        proc_id,
                        validate_all_matches=False,
                    )
                    lifecycle_results.append(lifecycle_stats)
                    accumulate_lifecycle_stats(total_stats, lifecycle_stats)

                    LOGGER.info(
                        f"Lifecycle {restart_num} stats: {lifecycle_stats}"
                    )
                    LOGGER.info(
                        f"Process killed, total restarts so far: "
                        f"{restart_count}"
                    )
                else:
                    # Final run - let it complete normally
                    LOGGER.info("Final run - waiting for completion")
                    await asyncio.wait_for(
                        proc.wait(), timeout=DEFAULT_TIMEOUT
                    )
                    if proc.returncode != 0:
                        stdout, stderr = await proc.communicate()
                        raise AssertionError(
                            "Final lifecycle failed:\n"
                            f"stdout:\n{stdout.decode()}\n"
                            f"stderr:\n{stderr.decode()}"
                        )

                    LOGGER.info(
                        f"Processing final {queue.qsize()} messages from "
                        f"lifecycle {restart_num}"
                    )
                    lifecycle_stats = await process_queue_messages(
                        queue,
                        endpoint,
                        rule_matches,
                        counts,
                        rule_set_name,
                        proc_id,
                        validate_all_matches=False,
                    )
                    lifecycle_results.append(lifecycle_stats)
                    accumulate_lifecycle_stats(total_stats, lifecycle_stats)

                    LOGGER.info(f"Final lifecycle stats: {lifecycle_stats}")

        # Log and validate results
        log_final_results(total_stats, restart_count, lifecycle_results)
        validate_final_results(
            total_stats, restart_count, rule_matches, counts
        )


async def ensure_file_is_free(db_path: Path, timeout: int = 5):
    """Wait until the Linux kernel confirms no one has an flock on the file."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            LOGGER.info(f"Attemping to lock : {db_path}")
            with open(db_path, "rb+") as f:
                # Attempt an exclusive non-blocking lock
                # If this succeeds, the file is truly free
                fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(f, fcntl.LOCK_UN)
                return True
        except IOError:
            # File is still locked by the dying JVM or kernel cleanup
            LOGGER.info(f"File is still locked : {db_path}")
            await asyncio.sleep(1)
    return False


@asynccontextmanager
async def h2_persistence_context():
    # 1. Setup: Determine base path (Linux RAM disk vs Mac Temp)
    base_path = (
        "/dev/shm"
        if platform.system() == "Linux" and os.path.exists("/dev/shm")
        else None
    )

    # 2. Create unique directory
    db_dir = tempfile.mkdtemp(prefix="h2_test_", dir=base_path)

    try:
        # Yield the path to the database (not the directory)
        yield db_dir
    finally:
        # 3. Cleanup: This runs after the 'with' block exits
        # We add a tiny delay to let the OS release the final file handles
        await asyncio.sleep(0.2)
        shutil.rmtree(db_dir, ignore_errors=True)
