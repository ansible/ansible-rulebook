import asyncio
import json
import time
from http import HTTPStatus
from typing import Any, Optional
from unittest.mock import patch

import aiohttp
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from ansible_rulebook.event_source.webhook import (
    AuthenticationFailed,
    Oauth2Authentication,
    Oauth2JwtAuthentication,
    main as webhook_main,
)


async def wait_for_server(
    host: str,
    port: int,
    timeout: float = 5.0,
    check_interval: float = 0.1,
) -> None:
    start_time = asyncio.get_event_loop().time()
    while True:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=0.5
            )
            writer.close()
            await writer.wait_closed()
            return
        except (OSError, asyncio.TimeoutError):
            pass

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed >= timeout:
            raise TimeoutError(
                "Server at "
                + host
                + ":"
                + str(port)
                + " did not become ready within "
                + str(timeout)
                + "s"
            )
        await asyncio.sleep(check_interval)


async def start_server(
    queue: asyncio.Queue[Any], args: dict[str, Any]
) -> None:
    await webhook_main(queue, args)


async def assert_post(
    server_task: asyncio.Task[None],
    info: dict[str, Any],
    expected_status: HTTPStatus = HTTPStatus.OK,
    expected_text: Optional[str] = None,
) -> None:
    host = info["host"]
    endpoint = info["endpoint"]
    url = "http://" + host + "/" + endpoint
    payload = info["payload"]
    headers = {}

    if "token" in info:
        headers["Authorization"] = f"Bearer {info['token']}"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            server_task.cancel()
            assert resp.status == expected_status
            if expected_text:
                assert expected_text in await resp.text()


# ---------------------------------------------------------------------------
# RSA key helpers for JWT tests
# ---------------------------------------------------------------------------


def _generate_rsa_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048
    )
    return private_key


def _jwk_from_public_key(public_key, kid="test-key-1"):
    from jwt.algorithms import RSAAlgorithm

    jwk_dict = json.loads(RSAAlgorithm.to_jwk(public_key))
    jwk_dict["kid"] = kid
    jwk_dict["use"] = "sig"
    jwk_dict["alg"] = "RS256"
    return jwk_dict


def _make_jwt(private_key, kid="test-key-1", claims=None, headers=None):
    payload = {"sub": "testuser", "exp": 9999999999, "iat": 1000000000}
    if claims:
        payload.update(claims)
    extra_headers = {"kid": kid}
    if headers:
        extra_headers.update(headers)
    return jwt.encode(
        payload, private_key, algorithm="RS256", headers=extra_headers
    )


# ---------------------------------------------------------------------------
# Mock OAuth2 introspection server
# ---------------------------------------------------------------------------


async def _run_mock_introspection_server(port, responses):
    from aiohttp import web

    async def introspect(request):
        data = await request.post()
        token = data.get("token", "")
        if token in responses:
            return web.json_response(responses[token])
        return web.json_response({"active": False})

    app = web.Application()
    app.router.add_post("/introspect", introspect)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)
    await site.start()
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


# ---------------------------------------------------------------------------
# Mock JWKS server
# ---------------------------------------------------------------------------


async def _run_mock_jwks_server(port, jwks_data):
    from aiohttp import web

    async def jwks_endpoint(request):
        return web.json_response(jwks_data)

    app = web.Application()
    app.router.add_get("/jwks", jwks_endpoint)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", port)
    await site.start()
    try:
        await asyncio.Future()
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


# ===================================================================
# OAuth2 Introspection tests
# ===================================================================


@pytest.mark.asyncio
async def test_oauth_introspection_valid_token() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9100
    webhook_port = 8200

    mock_task = asyncio.create_task(
        _run_mock_introspection_server(
            mock_port,
            {"valid-token-123": {"active": True, "username": "testuser"}},
        )
    )
    await wait_for_server("localhost", mock_port)

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_introspection_url": (
            "http://localhost:" + str(mock_port) + "/introspect"
        ),
        "oauth_client_id": "my_client",
        "oauth_client_secret": "my_secret",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": "valid-token-123",
    }
    post_task = asyncio.create_task(assert_post(plugin_task, task_info))
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]
    assert data["meta"]["endpoint"] == task_info["endpoint"]
    assert "Authorization" not in data["meta"]["headers"]


@pytest.mark.asyncio
async def test_oauth_introspection_inactive_token() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9101
    webhook_port = 8201

    mock_task = asyncio.create_task(
        _run_mock_introspection_server(
            mock_port,
            {"valid-token-123": {"active": True}},
        )
    )
    await wait_for_server("localhost", mock_port)

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_introspection_url": (
            "http://localhost:" + str(mock_port) + "/introspect"
        ),
        "oauth_client_id": "my_client",
        "oauth_client_secret": "my_secret",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": "unknown-token",
    }
    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.UNAUTHORIZED)
    )
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_oauth_introspection_missing_auth_header() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9102
    webhook_port = 8202

    mock_task = asyncio.create_task(
        _run_mock_introspection_server(mock_port, {})
    )
    await wait_for_server("localhost", mock_port)

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_introspection_url": (
            "http://localhost:" + str(mock_port) + "/introspect"
        ),
        "oauth_client_id": "my_client",
        "oauth_client_secret": "my_secret",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    url = "http://localhost:" + str(webhook_port) + "/test"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json={"test": 1}) as resp:
            plugin_task.cancel()
            assert resp.status == HTTPStatus.UNAUTHORIZED

    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_oauth_introspection_non_bearer_scheme() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9103
    webhook_port = 8203

    mock_task = asyncio.create_task(
        _run_mock_introspection_server(mock_port, {})
    )
    await wait_for_server("localhost", mock_port)

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_introspection_url": (
            "http://localhost:" + str(mock_port) + "/introspect"
        ),
        "oauth_client_id": "my_client",
        "oauth_client_secret": "my_secret",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    url = "http://localhost:" + str(webhook_port) + "/test"
    headers = {"Authorization": "Basic dXNlcjpwYXNz"}
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, json={"test": 1}, headers=headers
        ) as resp:
            plugin_task.cancel()
            assert resp.status == HTTPStatus.UNAUTHORIZED

    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)


# ===================================================================
# OAuth2 Introspection config validation tests
# ===================================================================


@pytest.mark.asyncio
async def test_oauth_introspection_missing_client_id() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    args = {
        "host": "localhost",
        "port": 8204,
        "oauth_introspection_url": "http://localhost:9999/introspect",
        "oauth_client_secret": "my_secret",
    }
    with pytest.raises(ValueError, match="oauth_client_id"):
        await webhook_main(queue, args)


@pytest.mark.asyncio
async def test_oauth_introspection_missing_client_secret() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    args = {
        "host": "localhost",
        "port": 8205,
        "oauth_introspection_url": "http://localhost:9999/introspect",
        "oauth_client_id": "my_client",
    }
    with pytest.raises(ValueError, match="oauth_client_secret"):
        await webhook_main(queue, args)


@pytest.mark.asyncio
async def test_oauth_introspection_missing_both_credentials() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    args = {
        "host": "localhost",
        "port": 8206,
        "oauth_introspection_url": "http://localhost:9999/introspect",
    }
    with pytest.raises(ValueError, match="oauth_client_id"):
        await webhook_main(queue, args)


@pytest.mark.asyncio
async def test_oauth_introspection_empty_client_id() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    args = {
        "host": "localhost",
        "port": 8207,
        "oauth_introspection_url": "http://localhost:9999/introspect",
        "oauth_client_id": "",
        "oauth_client_secret": "my_secret",
    }
    with pytest.raises(ValueError, match="oauth_client_id"):
        await webhook_main(queue, args)


@pytest.mark.asyncio
async def test_oauth_introspection_and_jwks_mutually_exclusive() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    args = {
        "host": "localhost",
        "port": 8208,
        "oauth_introspection_url": "http://localhost:9999/introspect",
        "oauth_client_id": "my_client",
        "oauth_client_secret": "my_secret",
        "oauth_jwks_url": "http://localhost:9999/jwks",
    }
    with pytest.raises(ValueError, match="mutually exclusive"):
        await webhook_main(queue, args)


# ===================================================================
# OAuth2 JWT / JWKS tests
# ===================================================================


@pytest.mark.asyncio
async def test_oauth_jwt_valid_token() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9110
    webhook_port = 8210

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    jwks_data = {"keys": [jwk]}

    mock_task = asyncio.create_task(
        _run_mock_jwks_server(mock_port, jwks_data)
    )
    await wait_for_server("localhost", mock_port)

    token = _make_jwt(private_key, kid="key-1")

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_jwks_url": "http://localhost:" + str(mock_port) + "/jwks",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": token,
    }
    post_task = asyncio.create_task(assert_post(plugin_task, task_info))
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]
    assert data["meta"]["endpoint"] == task_info["endpoint"]
    assert "Authorization" not in data["meta"]["headers"]


@pytest.mark.asyncio
async def test_oauth_jwt_valid_token_with_audience() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9111
    webhook_port = 8211

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    jwks_data = {"keys": [jwk]}

    mock_task = asyncio.create_task(
        _run_mock_jwks_server(mock_port, jwks_data)
    )
    await wait_for_server("localhost", mock_port)

    token = _make_jwt(private_key, kid="key-1", claims={"aud": "my_audience"})

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_jwks_url": "http://localhost:" + str(mock_port) + "/jwks",
        "oauth_audience": "my_audience",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": token,
    }
    post_task = asyncio.create_task(assert_post(plugin_task, task_info))
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)

    data = await queue.get()
    assert data["payload"] == task_info["payload"]


@pytest.mark.asyncio
async def test_oauth_jwt_wrong_audience() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9112
    webhook_port = 8212

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    jwks_data = {"keys": [jwk]}

    mock_task = asyncio.create_task(
        _run_mock_jwks_server(mock_port, jwks_data)
    )
    await wait_for_server("localhost", mock_port)

    token = _make_jwt(
        private_key, kid="key-1", claims={"aud": "wrong_audience"}
    )

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_jwks_url": "http://localhost:" + str(mock_port) + "/jwks",
        "oauth_audience": "my_audience",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"src_path": "https://example.com/payload"},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": token,
    }
    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.UNAUTHORIZED)
    )
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_oauth_jwt_expired_token() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9113
    webhook_port = 8213

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    jwks_data = {"keys": [jwk]}

    mock_task = asyncio.create_task(
        _run_mock_jwks_server(mock_port, jwks_data)
    )
    await wait_for_server("localhost", mock_port)

    token = _make_jwt(private_key, kid="key-1", claims={"exp": 1000000000})

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_jwks_url": "http://localhost:" + str(mock_port) + "/jwks",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"test": 1},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": token,
    }
    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.UNAUTHORIZED)
    )
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_oauth_jwt_unknown_kid() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9114
    webhook_port = 8214

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    jwks_data = {"keys": [jwk]}

    mock_task = asyncio.create_task(
        _run_mock_jwks_server(mock_port, jwks_data)
    )
    await wait_for_server("localhost", mock_port)

    token = _make_jwt(private_key, kid="unknown-key")

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_jwks_url": "http://localhost:" + str(mock_port) + "/jwks",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"test": 1},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": token,
    }
    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.UNAUTHORIZED)
    )
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)


@pytest.mark.asyncio
async def test_oauth_jwt_tampered_token() -> None:
    queue: asyncio.Queue[Any] = asyncio.Queue()
    mock_port = 9115
    webhook_port = 8215

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="key-1")
    jwks_data = {"keys": [jwk]}

    mock_task = asyncio.create_task(
        _run_mock_jwks_server(mock_port, jwks_data)
    )
    await wait_for_server("localhost", mock_port)

    other_key = _generate_rsa_keypair()
    token = _make_jwt(other_key, kid="key-1")

    args = {
        "host": "localhost",
        "port": webhook_port,
        "oauth_jwks_url": "http://localhost:" + str(mock_port) + "/jwks",
    }
    plugin_task = asyncio.create_task(start_server(queue, args))
    await wait_for_server("localhost", webhook_port)

    task_info = {
        "payload": {"test": 1},
        "endpoint": "test",
        "host": "localhost:" + str(webhook_port),
        "token": token,
    }
    post_task = asyncio.create_task(
        assert_post(plugin_task, task_info, HTTPStatus.UNAUTHORIZED)
    )
    await post_task
    await asyncio.gather(plugin_task, return_exceptions=True)
    mock_task.cancel()
    await asyncio.gather(mock_task, return_exceptions=True)


# ===================================================================
# Unit tests for Oauth2JwtAuthentication
# ===================================================================


@pytest.mark.asyncio
async def test_jwt_auth_missing_kid_in_header() -> None:
    auth = Oauth2JwtAuthentication(
        jwks_url="http://localhost:1/jwks", audience=None
    )
    private_key = _generate_rsa_keypair()
    token = jwt.encode(
        {"sub": "user", "exp": 9999999999, "iat": 1000000000},
        private_key,
        algorithm="RS256",
    )
    with pytest.raises(AuthenticationFailed, match="missing kid"):
        await auth.authenticate(token)


# ===================================================================
# Unit tests for Oauth2Authentication
# ===================================================================


@pytest.mark.asyncio
async def test_introspection_auth_network_failure() -> None:
    auth = Oauth2Authentication(
        introspection_url="http://localhost:1/introspect",
        client_id="client",
        client_secret="secret",
    )
    with pytest.raises(AuthenticationFailed):
        await auth.authenticate("some-token")


# ===================================================================
# JWKS cache tests
# ===================================================================


@pytest.mark.asyncio
async def test_jwks_cache_is_reused() -> None:
    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="cached-key")
    jwks_data = {"keys": [jwk]}

    fetch_count = 0

    async def counting_refresh(self):
        nonlocal fetch_count
        fetch_count += 1
        self._jwks_cache = jwks_data
        self._jwks_cache_time = time.monotonic()

    auth = Oauth2JwtAuthentication(
        jwks_url="http://localhost:1/jwks", audience=None
    )

    with patch.object(
        Oauth2JwtAuthentication, "_refresh_jwks", counting_refresh
    ):
        token1 = _make_jwt(private_key, kid="cached-key")
        await auth.authenticate(token1)
        assert fetch_count == 1

        token2 = _make_jwt(private_key, kid="cached-key")
        await auth.authenticate(token2)
        assert fetch_count == 1


@pytest.mark.asyncio
async def test_jwks_cache_refresh_on_kid_miss() -> None:
    private_key1 = _generate_rsa_keypair()
    public_key1 = private_key1.public_key()
    jwk1 = _jwk_from_public_key(public_key1, kid="key-1")

    private_key2 = _generate_rsa_keypair()
    public_key2 = private_key2.public_key()
    jwk2 = _jwk_from_public_key(public_key2, kid="key-2")

    call_count = 0
    jwks_versions = [{"keys": [jwk1]}, {"keys": [jwk1, jwk2]}]

    async def staged_refresh(self):
        nonlocal call_count
        self._jwks_cache = jwks_versions[min(call_count, 1)]
        self._jwks_cache_time = time.monotonic()
        call_count += 1

    auth = Oauth2JwtAuthentication(
        jwks_url="http://localhost:1/jwks", audience=None
    )

    with patch.object(
        Oauth2JwtAuthentication, "_refresh_jwks", staged_refresh
    ):
        token1 = _make_jwt(private_key1, kid="key-1")
        await auth.authenticate(token1)
        assert call_count == 1

        from ansible_rulebook.event_source.webhook import (
            JWKS_MIN_REFRESH_INTERVAL,
        )

        auth._jwks_cache_time -= JWKS_MIN_REFRESH_INTERVAL + 1

        token2 = _make_jwt(private_key2, kid="key-2")
        await auth.authenticate(token2)
        assert call_count == 2


@pytest.mark.asyncio
async def test_jwks_cache_expires_after_ttl() -> None:
    from ansible_rulebook.event_source.webhook import JWKS_CACHE_TTL

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="ttl-key")
    jwks_data = {"keys": [jwk]}

    fetch_count = 0

    async def counting_refresh(self):
        nonlocal fetch_count
        fetch_count += 1
        self._jwks_cache = jwks_data
        self._jwks_cache_time = time.monotonic()

    auth = Oauth2JwtAuthentication(
        jwks_url="http://localhost:1/jwks", audience=None
    )

    with patch.object(
        Oauth2JwtAuthentication, "_refresh_jwks", counting_refresh
    ):
        token1 = _make_jwt(private_key, kid="ttl-key")
        await auth.authenticate(token1)
        assert fetch_count == 1

        auth._jwks_cache_time -= JWKS_CACHE_TTL + 1

        token2 = _make_jwt(private_key, kid="ttl-key")
        await auth.authenticate(token2)
        assert fetch_count == 2


@pytest.mark.asyncio
async def test_jwks_forced_refresh_is_throttled() -> None:
    from ansible_rulebook.event_source.webhook import JWKS_MIN_REFRESH_INTERVAL

    private_key = _generate_rsa_keypair()
    public_key = private_key.public_key()
    jwk = _jwk_from_public_key(public_key, kid="known-key")
    jwks_data: dict = {"keys": [jwk]}

    fetch_count = 0

    async def counting_refresh(self):
        nonlocal fetch_count
        fetch_count += 1
        self._jwks_cache = jwks_data
        self._jwks_cache_time = time.monotonic()

    auth = Oauth2JwtAuthentication(
        jwks_url="http://localhost:1/jwks", audience=None
    )

    with patch.object(
        Oauth2JwtAuthentication, "_refresh_jwks", counting_refresh
    ):
        token = _make_jwt(private_key, kid="known-key")
        await auth.authenticate(token)
        assert fetch_count == 1

        for _ in range(5):
            with pytest.raises(AuthenticationFailed, match="Unable to find"):
                bad_token = _make_jwt(private_key, kid="bogus")
                await auth.authenticate(bad_token)

        assert fetch_count == 1

        auth._jwks_cache_time -= JWKS_MIN_REFRESH_INTERVAL + 1

        with pytest.raises(AuthenticationFailed, match="Unable to find"):
            bad_token = _make_jwt(private_key, kid="bogus")
            await auth.authenticate(bad_token)

        assert fetch_count == 2


@pytest.mark.asyncio
async def test_jwks_fetch_network_error() -> None:
    auth = Oauth2JwtAuthentication(
        jwks_url="http://localhost:1/jwks", audience=None
    )
    private_key = _generate_rsa_keypair()
    token = _make_jwt(private_key, kid="net-err")
    with pytest.raises(AuthenticationFailed):
        await auth.authenticate(token)


@pytest.mark.asyncio
async def test_jwks_fetch_http_error() -> None:
    from aiohttp import web as aio_web

    app = aio_web.Application()

    async def jwks_handler(request):
        return aio_web.Response(status=500, text="internal error")

    app.router.add_get("/jwks", jwks_handler)

    runner = aio_web.AppRunner(app)
    await runner.setup()
    site = aio_web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]

    jwks_url = "http://127.0.0.1:" + str(port) + "/jwks"
    auth = Oauth2JwtAuthentication(jwks_url=jwks_url, audience=None)

    try:
        private_key = _generate_rsa_keypair()
        token = _make_jwt(private_key, kid="http-err")
        with pytest.raises(AuthenticationFailed):
            await auth.authenticate(token)
    finally:
        await runner.cleanup()
