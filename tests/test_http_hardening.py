import asyncio

from voicemeeter_mcp.http_server import HardenedASGI, _host_is_ip_literal


def test_host_literal_detection():
    assert _host_is_ip_literal("10.0.0.41:8766")
    assert _host_is_ip_literal("127.0.0.1")
    assert _host_is_ip_literal("localhost")
    assert _host_is_ip_literal("[::1]:8766")
    assert not _host_is_ip_literal("attacker.example.com:8766")
    assert not _host_is_ip_literal("mixer.local")


def run_request(app, headers):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        sent.append(msg)

    scope = {"type": "http", "headers": headers, "path": "/mcp", "method": "POST"}
    asyncio.run(app(scope, receive, send))
    return sent


async def inner_ok(scope, receive, send):
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"ok"})


def test_dns_name_host_rejected():
    app = HardenedASGI.__new__(HardenedASGI)
    app.inner = inner_ok
    app.token = ""
    sent = run_request(app, [(b"host", b"attacker.example.com")])
    assert sent[0]["status"] == 403


def test_ip_host_passes():
    app = HardenedASGI.__new__(HardenedASGI)
    app.inner = inner_ok
    app.token = ""
    sent = run_request(app, [(b"host", b"10.0.0.41:8766")])
    assert sent[0]["status"] == 200


def test_token_enforced():
    app = HardenedASGI.__new__(HardenedASGI)
    app.inner = inner_ok
    app.token = "sekrit"
    assert run_request(app, [(b"host", b"10.0.0.41")])[0]["status"] == 403
    ok = run_request(app, [(b"host", b"10.0.0.41"), (b"authorization", b"Bearer sekrit")])
    assert ok[0]["status"] == 200
