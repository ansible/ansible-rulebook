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
async def test_skip_audit_events():
    """
    Verify that ansible-rulebook can skip sending
    audit events but still keep sending heartbeat
    data
    """
    # variables
    host = "127.0.0.1"
    endpoint = "/api/ws2"
    proc_id = "42"
    port = 31417
    rulebook = utils.BASE_DATA_PATH / "rulebooks/test_match_multiple_rules.yml"
    websocket_address = f"ws://127.0.0.1:{port}{endpoint}"
    cmd = utils.Command(
        rulebook=rulebook,
        websocket=websocket_address,
        proc_id=proc_id,
        heartbeat=2,
        skip_audit_events=True,
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

    action_counter = 0
    session_stats_counter = 0
    stats = None
    while not queue.empty():
        data = await queue.get()
        assert data["path"] == endpoint
        data = data["payload"]

        if data["type"] == "Action":
            action_counter += 1

        if data["type"] == "SessionStats":
            session_stats_counter += 1
            stats = data["stats"]
            assert stats["ruleSetName"] == "Test match multiple rules"
            assert stats["numberOfRules"] == 2
            assert stats["numberOfDisabledRules"] == 0
            assert data["activation_instance_id"] == proc_id

    assert stats["rulesTriggered"] == 2
    assert stats["eventsProcessed"] == 5
    assert stats["eventsMatched"] == 1

    assert session_stats_counter >= 2
    assert action_counter == 0
