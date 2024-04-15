"""
Module with tests for websockets
"""
import asyncio
import logging
from functools import partial

import dpath
import pytest
import websockets.server as ws_server

from . import utils

LOGGER = logging.getLogger(__name__)
DEFAULT_TIMEOUT = 15


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_run_module_output():
    """
    Verify that ansible-rulebook can handle output of
    run_module and then used in a condition
    """
    # variables
    host = "127.0.0.1"
    endpoint = "/api/ws2"
    proc_id = "42"
    port = 31416
    rulebook = utils.EXAMPLES_PATH / "29_run_module.yml"
    websocket_address = f"ws://127.0.0.1:{port}{endpoint}"
    cmd = utils.Command(
        rulebook=rulebook,
        websocket=websocket_address,
        proc_id=proc_id,
        heartbeat=2,
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
    rule_matches = {
        "r1": {
            "action": "run_module",
            "event_key": "m/i",
            "event_value": 1,
        },
        "r2": {
            "action": "print_event",
            "event_key": "m/message",
            "event_value": "FRED FLINTSTONE",
        },
    }
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
            assert rule_name in rule_matches.keys()

            matching_events = data["matching_events"]
            assert (
                dpath.get(
                    matching_events, rule_matches[rule_name]["event_key"]
                )
                == rule_matches[rule_name]["event_value"]
            )
            assert data["action"] == rule_matches[rule_name]["action"]

        if data["type"] == "SessionStats":
            session_stats_counter += 1
            stats = data["stats"]
            assert stats["ruleSetName"] == "29 run module"
            assert stats["numberOfRules"] == 2
            assert stats["numberOfDisabledRules"] == 0
            assert data["activation_instance_id"] == proc_id

    assert stats["rulesTriggered"] == 2
    assert stats["eventsProcessed"] == 6
    assert stats["eventsMatched"] == 2

    assert session_stats_counter >= 2
    assert action_counter == 2
