"""
Module with tests for websockets
"""

import asyncio
import logging
import subprocess
import time
from functools import partial

import pytest
import websockets.server as ws_server

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize("expect_failure", [True, False])
async def test_websocket_messages(expect_failure):
    """
    Verify that ansible-rulebook can correctly
    send event messages to a websocket server
    """
    # variables
    host = "127.0.0.1"
    endpoint = "/api/ws2"
    proc_id = "42"
    port = utils.get_safe_port()
    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/websockets/test_websocket_range.yml"
    )
    websocket_address = f"ws://127.0.0.1:{port}{endpoint}"
    cmd = utils.Command(
        rulebook=rulebook,
        websocket=websocket_address,
        proc_id=proc_id,
        heartbeat=2,
    )

    # run server and ansible-rulebook
    queue = asyncio.Queue()
    handler = partial(utils.msg_handler, queue=queue, failed=expect_failure)
    async with ws_server.serve(handler, host, port):
        LOGGER.info(f"Running command: {cmd}")
        proc = await asyncio.create_subprocess_shell(
            str(cmd),
            cwd=utils.BASE_DATA_PATH,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await asyncio.wait_for(proc.wait(), timeout=DEFAULT_TIMEOUT)
        if expect_failure:
            assert proc.returncode == 1
            assert queue.qsize() == 2
            return
        else:
            assert proc.returncode == 0

    # Verify data
    assert not queue.empty()

    job_id = None
    ansible_event_counter = 0
    job_counter = 0
    action_counter = 0
    session_stats_counter = 0
    stats = None
    while not queue.empty():
        data = await queue.get()
        assert data["path"] == endpoint
        data = data["payload"]

        if data["type"] == "Action":
            action_counter += 1
            assert data["action"] == "run_playbook"
            assert data["action_uuid"] is not None
            assert data["ruleset_uuid"] is not None
            assert data["rule_uuid"] is not None
            matching_events = data["matching_events"]
            del matching_events["m"]["meta"]
            assert matching_events == {"m": {"i": 700}}
            assert data["status"] == "successful"

        if data["type"] == "Job":
            job_counter += 1
            job_id = data["job_id"]
            assert data["ansible_rulebook_id"] == proc_id
            assert data["action"] == "run_playbook"
            assert data["name"] == "print_event.yml"
            assert data["rule"] == "match the event"
            assert data["ruleset"] == "Test websocket range events"

        if data["type"] == "AnsibleEvent":
            ansible_event_counter += 1
            event = data["event"]
            assert event["job_id"] == job_id
            assert event["event_data"]["playbook"] == "print_event.yml"
            assert event["ansible_rulebook_id"] == proc_id
            assert data["run_at"]

        if data["type"] == "SessionStats":
            session_stats_counter += 1
            stats = data["stats"]
            assert stats["ruleSetName"] == "Test websocket range events"
            assert stats["numberOfRules"] == 1
            assert stats["numberOfDisabledRules"] == 0
            assert data["activation_id"] == proc_id

    assert stats["rulesTriggered"] == 1
    assert stats["eventsProcessed"] == 2000
    assert stats["eventsMatched"] == 1
    assert stats["eventsSuppressed"] == 1999

    assert ansible_event_counter == 9
    assert session_stats_counter >= 2
    assert job_counter == 1
    assert action_counter == 1


@pytest.mark.e2e
@pytest.mark.asyncio
@pytest.mark.parametrize("verbosity", [1, 2])
async def test_worker_startup_output(verbosity):
    """
    Verify that ansible-rulebook produces the expected log messages
    when starting in worker mode
    """
    # variables
    timeout = 5
    host = "127.0.0.1"
    endpoint = "/api/ws2"
    proc_id = "42"
    port = utils.get_safe_port()
    websocket_address = f"ws://127.0.0.1:{port}{endpoint}"
    cmd = utils.Command(
        rulebook=None,
        inventory=None,
        worker_mode=True,
        verbosity=verbosity,
        websocket=websocket_address,
        proc_id=proc_id,
        sources=None,
    )
    # run server and ansible-rulebook
    queue = asyncio.Queue()
    handler = partial(utils.msg_handler, queue=queue)
    async with ws_server.serve(handler, host, port):
        LOGGER.info(f"Running command: {cmd}")
        process = subprocess.Popen(
            cmd,
            cwd=utils.BASE_DATA_PATH,
            text=True,
            stdout=subprocess.PIPE,
        )
        lines = []
        start = time.time()
        while line := process.stdout.readline():
            lines.append(line)
            if "Starting worker mode" in line:
                break
            if time.time() - start > timeout:
                break
            time.sleep(0.1)

        process.kill()

    assert lines, "No output from ansible-rulebook"
    info_messages = [
        "ansible-rulebook",
        "Python version",
    ]

    for expected in info_messages:
        assert any(
            expected in line for line in lines
        ), f"Missing expected output: {expected}"

    if verbosity == 1:
        assert not any(
            "Installed collections" in line for line in lines
        ), "Unexpected output"
    elif verbosity == 2:
        assert any(
            "Installed collections" in line for line in lines
        ), "Missing expected output"
