"""module with utils for e2e tests"""

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path
from subprocess import CompletedProcess
from typing import Iterable, List, Optional, Union

import websockets.server as ws_server

BASE_DATA_PATH = Path(f"{__file__}").parent / Path("files")
DEFAULT_SOURCES = Path(f"{__file__}").parent / Path("../sources")
DEFAULT_INVENTORY = BASE_DATA_PATH / "inventories/default_inventory.yml"


@dataclass
class Command:
    """
    Represents the command and their arguments and
    provides methods to render it for cmd runners
    """

    rulebook: Path
    program_name: str = "ansible-rulebook"
    cwd: Path = BASE_DATA_PATH
    inventory: Path = DEFAULT_INVENTORY
    sources: Optional[Path] = DEFAULT_SOURCES
    vars_file: Optional[Path] = None
    envvars: Optional[str] = None
    proc_id: Union[str, int, None] = None
    verbose: bool = False
    debug: bool = False
    websocket: Optional[str] = None
    project_tarball: Optional[Path] = None
    worker_mode: bool = False

    def __str__(self) -> str:
        return self.to_string()

    def __iter__(self) -> Iterable:
        return (item for item in self.to_list())

    def to_list(self) -> List:
        result = [self.program_name]

        result.extend(["-i", str(self.inventory.absolute())])

        if self.sources:
            result.extend(["-S", str(self.sources.absolute())])
        if self.vars_file:
            result.extend(["--vars", str(self.vars_file.absolute())])
        if self.envvars:
            result.extend(["--env-vars", self.envvars])
        if self.proc_id:
            result.extend(["--id", str(self.proc_id)])
        if self.websocket:
            result.extend(["--websocket-address", self.websocket])
        if self.project_tarball:
            result.extend(
                ["--project-tarball", str(self.project_tarball.absolute())]
            )
        if self.worker_mode:
            result.append("--worker")
        if self.rulebook:
            result.extend(["--rulebook", str(self.rulebook.absolute())])
        if self.verbose:
            result.append("--verbose")
        if self.debug:
            result.append("--debug")

        return result

    def to_string(self) -> str:
        return " ".join(self.to_list())


def jsonify_output(output: str) -> List[dict]:
    """
    Receives an str from the cmd output when json_mode is enabled
    and returns the list of dicts
    """
    return [json.loads(line) for line in output.splitlines()]


def assert_playbook_output(result: CompletedProcess) -> List[dict]:
    """
    Common logic to assert a succesful execution of a run_playbook action.
    Returns the stdout deserialized
    """
    assert result.returncode == 0
    assert not result.stderr

    output = jsonify_output(result.stdout.decode())

    if output:
        assert output[-1]["event_data"]["ok"]
        assert not output[-1]["event_data"]["failures"]

    return output


async def msg_handler(
    websocket: ws_server.WebSocketServerProtocol, queue: asyncio.Queue
):
    """
    Handler for a websocket server that passes json messages
    from ansible-rulebook in the given queue
    """
    async for message in websocket:
        payload = json.loads(message)
        data = {"path": websocket.path, "payload": payload}
        await queue.put(data)
