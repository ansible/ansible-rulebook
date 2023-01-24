"""
Module with tests for websockets
"""
import asyncio
import logging
from functools import partial

import pytest
import websockets.server as ws_server

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_websocket_messages():
    """
    Verify that ansible-rulebook can correctly
    send event messages to a websocket server
    """
    # variables
    host = "localhost"
    endpoint = "/api/ws2"
    proc_id = 42
    port = 31415
    rulebook = (
        utils.BASE_DATA_PATH / "rulebooks/websockets/test_websocket_range.yml"
    )
    websocket_address = f"ws://localhost:{port}{endpoint}"
    cmd = utils.Command(
        rulebook=rulebook,
        websocket=websocket_address,
        proc_id=proc_id,
    )

    # run server and ansible-rulebook
    queue = asyncio.Queue()
    handler = partial(utils.msg_handler, queue=queue)
    async with ws_server.serve(handler, host, port):
        LOGGER.info(f"Running command: {cmd}")
        proc = await asyncio.create_subprocess_shell(
            str(cmd),
            cwd=utils.BASE_DATA_PATH,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await asyncio.wait_for(proc.wait(), timeout=DEFAULT_TIMEOUT)
        assert proc.returncode == 0

    # Verify data
    assert not queue.empty()

    job_id = None
    ansible_event_counter = 0
    job_counter = 0
    action_counter = 0

    while not queue.empty():
        data = await queue.get()
        assert data["path"] == endpoint
        data = data["payload"]

        if data["type"] == "ProcessedEvent":
            assert data["results"]

        if data["type"] == "Action":
            action_counter += 1
            assert data["action"] == "run_playbook"
            assert data["matching_events"] == {"m": {"i": 700}}
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

    assert ansible_event_counter == 9
    assert job_counter == 1
    assert action_counter == 1
