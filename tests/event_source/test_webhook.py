import asyncio
import pathlib
import shutil
import ssl
import subprocess
from http import HTTPStatus
from typing import Any, Optional

import aiohttp
import pytest

from ansible_rulebook.event_source.webhook import main as webhook_main


async def wait_for_server(
    host: str,
    port: int,
    timeout: float = 5.0,
    check_interval: float = 0.1,
    use_ssl: bool = False,
) -> None:
    """Wait for the webhook server to be ready to accept connections.

    Args:
        host: Server hostname
        port: Server port
        timeout: Maximum time to wait in seconds
        check_interval: Time between connection attempts in seconds
        use_ssl: Whether to use SSL/TLS connection

    Raises:
        TimeoutError: If server is not ready within timeout period
    """
    start_time = asyncio.get_event_loop().time()

    while True:
        try:
            # Try to establish a TCP connection to check if server is listening
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=0.5
            )
            writer.close()
            await writer.wait_closed()
            # Server is accepting connections
            return
        except (OSError, asyncio.TimeoutError):
            # Server not ready yet
            pass

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            scheme = "https" if use_ssl else "http"
            raise TimeoutError(
                f"Server at {scheme}://{host}:{port} did not become ready "
                f"within {timeout}s"
            )

        await asyncio.sleep(check_interval)


@pytest.fixture(scope="session")
def dynamic_certs(tmp_path_factory: pytest.TempPathFactory) -> pathlib.Path:
    sscg = shutil.which("sscg")
    if not sscg:
        pytest.skip("'sscg' is not available")
    path = tmp_path_factory.mktemp("certs")
    subprocess.run(
        [
            sscg,
            "--cert-file",
            "server.crt",
            "--cert-key-file",
            "server.key",
            "--client-file",
            "client.crt",
            "--client-key-file",
            "client.key",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=path,
    )
    return path


async def start_server(
    queue: asyncio.Queue[Any], args: dict[str, Any]
) -> None:
    await webhook_main(queue, args)


async def post_code(
    server_task: asyncio.Task[None], info: dict[str, Any]
) -> None:
    url = f'http://{info["host"]}/{info["endpoint"]}'
    payload = info["payload"]

    connector = None
    if "client_certfile" in info:
        url = f'https://{info["host"]}/{info["endpoint"]}'
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.load_cert_chain(
            info["client_certfile"], info["client_keyfile"]
        )
        connector = aiohttp.TCPConnector(ssl=context)
    async with aiohttp.ClientSession(connector=connector) as session:
        headers = {"Authorization": "Bearer secret"}
        async with session.post(url, json=payload, headers=headers) as resp:
            print(resp.status)

    server_task.cancel()


async def assert_post(
    server_task: asyncio.Task[None],
    info: dict[str, Any],
    expected_status: HTTPStatus = HTTPStatus.OK,
    expected_text: Optional[str] = None,
) -> None:
    url = f'http://{info["host"]}/{info["endpoint"]}'
    payload = info["payload"]
    headers = {}

    if "token" in info:
        headers["Authorization"] = f"Bearer {info['token']}"

    if "hmac_header" in info:
        headers[info["hmac_header"]] = info["hmac_digest"]

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            server_task.cancel()
            assert resp.status == expected_status
            if expected_text:
                assert expected_text in await resp.text()


async def cancel_code(server_task: asyncio.Task[None]) -> None:
    server_task.cancel()


@pytest.mark.asyncio
async def test_cancel() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {"host": "localhost", "port": 8000, "token": "secret"}
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])
    plugin_task.cancel()

    # The webhook server logs cancellation and re-raises CancelledError
    with pytest.raises(asyncio.CancelledError):
        await plugin_task


@pytest.mark.asyncio
async def test_post_endpoint(dynamic_certs: pathlib.Path) -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "token": "secret",
        "certfile": str(dynamic_certs / "server.crt"),
        "keyfile": str(dynamic_certs / "server.key"),
        "cafile": str(dynamic_certs / "ca.crt"),
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"], use_ssl=True)

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
        "client_certfile": str(dynamic_certs / "client.crt"),
        "client_keyfile": str(dynamic_certs / "client.key"),
    }

    post_task = asyncio.create_task(post_code(plugin_task, task_info))

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]
    assert data["meta"]["endpoint"] == task_info["endpoint"]
    assert data["meta"]["headers"]["Host"] == task_info["host"]


@pytest.mark.asyncio
async def test_post_unsupported_body() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    args = {"host": "localhost", "port": 8000}

    async def do_request() -> None:
        async with aiohttp.ClientSession() as session:
            url = f'http://{args["host"]}:{args["port"]}/test'
            async with session.post(url, data="not a json") as resp:
                plugin_task.cancel()
                assert resp.status == HTTPStatus.BAD_REQUEST

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])
    request_task = asyncio.create_task(do_request())
    await asyncio.gather(plugin_task, request_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_post_hmac_hex_endpoint() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "hmac_secret": "secret",
        "hmac_algo": "sha256",
        "hmac_header": "x-hub-signature-256",
        "hmac_format": "hex",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": args["hmac_header"],
        "hmac_digest": (
            "sha256=9ec8272937a36a4b4427d4f9ab7b0425"
            "856c5ef5d7e1b496f864aaf99c1910ca"
        ),
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    post_task = asyncio.create_task(assert_post(plugin_task, task_info))

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]
    assert data["meta"]["endpoint"] == task_info["endpoint"]
    assert data["meta"]["headers"]["Host"] == task_info["host"]


@pytest.mark.asyncio
async def test_post_hmac_hex_wo_digest_prefix_endpoint() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "hmac_secret": "secret",
        "hmac_algo": "sha256",
        "hmac_header": "x-hub-signature-256",
        "hmac_format": "hex",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": args["hmac_header"],
        "hmac_digest": (
            "9ec8272937a36a4b4427d4f9ab7b0425"
            "856c5ef5d7e1b496f864aaf99c1910ca"
        ),
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    post_task = asyncio.create_task(assert_post(plugin_task, task_info))

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]
    assert data["meta"]["endpoint"] == task_info["endpoint"]
    assert data["meta"]["headers"]["Host"] == task_info["host"]


@pytest.mark.asyncio
async def test_post_hmac_hex_endpoint_invalid_signature() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "hmac_secret": "secret",
        "hmac_algo": "sha256",
        "hmac_header": "x-hub-signature-256",
        "hmac_format": "hex",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": args["hmac_header"],
        "hmac_digest": (
            "sha256=11f8feeab79372c842f0097fc105dd66"
            "d90c41412ab9d3c4071859d7b6ae864b"
        ),
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.UNAUTHORIZED)
    )

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_post_hmac_hex_endpoint_missing_signature() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "hmac_secret": "secret",
        "hmac_algo": "sha256",
        "hmac_header": "x-hub-signature-256",
        "hmac_format": "hex",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": "x-not-a-signature-header",
        "hmac_digest": (
            "sha256=205009e3e895e0fe0ff982e1020dd0fb"
            "4b6d16cf9c666652b3492e20429ccdb8"
        ),
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.BAD_REQUEST)
    )

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_post_hmac_base64_endpoint() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "hmac_secret": "secret",
        "hmac_algo": "sha256",
        "hmac_header": "x-custom-signature",
        "hmac_format": "base64",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": args["hmac_header"],
        "hmac_digest": "sha256=nsgnKTejaktEJ9T5q3sEJYVsXvXX4bSW+GSq+ZwZEMo=",
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    post_task = asyncio.create_task(assert_post(plugin_task, task_info))

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]
    assert data["meta"]["endpoint"] == task_info["endpoint"]
    assert data["meta"]["headers"]["Host"] == task_info["host"]


@pytest.mark.asyncio
async def test_post_hmac_base64_endpoint_invalid_signature() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "hmac_secret": "secret",
        "hmac_algo": "sha256",
        "hmac_header": "x-hub-signature-256",
        "hmac_format": "hex",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": args["hmac_header"],
        "hmac_digest": "nsgnKTejaktEJ9T5q3sEJYVsXvXX4bSW+GSq+ZwZEMo=",
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.UNAUTHORIZED)
    )

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_post_token_and_hmac_hex_endpoint() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "token": "secret",
        "hmac_secret": "secret",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": "x-hub-signature-256",
        "hmac_digest": (
            "sha256=9ec8272937a36a4b4427d4f9ab7b0425"
            "856c5ef5d7e1b496f864aaf99c1910ca"
        ),
        "token": args["token"],
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    post_task = asyncio.create_task(assert_post(plugin_task, task_info))

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]
    assert data["meta"]["endpoint"] == task_info["endpoint"]
    assert data["meta"]["headers"]["Host"] == task_info["host"]


@pytest.mark.asyncio
async def test_post_token_and_hmac_hex_endpoint_invalid_signature() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = args = {
        "host": "localhost",
        "port": 8000,
        "token": "secret",
        "hmac_secret": "secret",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": "x-hub-signature-256",
        "hmac_digest": (
            "11f8feeab79372c842f0097fc105dd66"
            "d90c41412ab9d3c4071859d7b6ae864b"
        ),
        "token": args["token"],
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    expected_text = "HMAC verification failed"
    post_task = asyncio.create_task(
        assert_post(
            plugin_task, task_info, HTTPStatus.UNAUTHORIZED, expected_text
        )
    )

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_post_token_and_hmac_hex_endpoint_invalid_token() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()

    args = {
        "host": "localhost",
        "port": 8000,
        "token": "secret",
        "hmac_secret": "secret",
    }

    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server(args["host"], args["port"])

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "hmac_header": "x-hub-signature-256",
        "hmac_digest": (
            "11f8feeab79372c842f0097fc105dd66"
            "d90c41412ab9d3c4071859d7b6ae864b"
        ),
        "token": "invalid_token",
        "endpoint": "test",
        "host": f'{args["host"]}:{args["port"]}',
    }

    expected_text = "Invalid authorization token"
    post_task = asyncio.create_task(
        assert_post(
            plugin_task, task_info, HTTPStatus.UNAUTHORIZED, expected_text
        )
    )

    await asyncio.gather(plugin_task, post_task, return_exceptions=True)
