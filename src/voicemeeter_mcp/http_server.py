"""Hardened streamable-HTTP serving for --http mode.

Mitigations for network exposure:
- binds 127.0.0.1 unless --http-host is given explicitly;
- rejects requests whose Host header is not an IP-literal[:port] — DNS
  rebinding attacks must arrive under an attacker DNS name, so IP-only
  Host values kill that class;
- optional shared secret: set VM_MCP_HTTP_TOKEN and clients must send
  "Authorization: Bearer <token>".
"""

from __future__ import annotations

import hmac
import ipaddress
import os


def _host_is_ip_literal(host_header: str) -> bool:
    host = host_header
    if ":" in host and not host.startswith("["):
        host = host.rsplit(":", 1)[0]
    if host.startswith("[") and "]" in host:  # [v6]:port
        host = host[1 : host.index("]")]
    if host in ("localhost",):
        return True
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


class HardenedASGI:
    def __init__(self, inner):
        self.inner = inner
        self.token = os.environ.get("VM_MCP_HTTP_TOKEN", "")

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
            reason = None
            if not _host_is_ip_literal(headers.get("host", "")):
                reason = b"host header must be an IP literal"
            elif self.token:
                supplied = headers.get("authorization", "").removeprefix("Bearer ").strip()
                if not hmac.compare_digest(supplied, self.token):
                    reason = b"missing or invalid bearer token"
            if reason:
                await send(
                    {
                        "type": "http.response.start",
                        "status": 403,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send({"type": "http.response.body", "body": reason})
                return
        await self.inner(scope, receive, send)


def serve(app, host: str, port: int) -> None:
    import os
    import sys

    import uvicorn

    # Under pythonw (no console) std streams are None; uvicorn's logging
    # would crash writing to them.
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")  # noqa: SIM115 - lives for process lifetime
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")  # noqa: SIM115
    asgi = HardenedASGI(app.streamable_http_app())
    uvicorn.run(asgi, host=host, port=port, log_level="warning")
