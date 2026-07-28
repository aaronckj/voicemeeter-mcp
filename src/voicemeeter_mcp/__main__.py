"""CLI entry: stdio MCP by default; --http serves streamable-HTTP on the LAN.

HTTP mode exists for Windows session isolation: the VoicemeeterRemote DLL
only reaches the engine from inside the interactive desktop session, so the
server runs there (e.g. a logon task) and MCP clients connect over HTTP.
"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(prog="voicemeeter-mcp")
    parser.add_argument(
        "--http",
        type=int,
        metavar="PORT",
        help="serve hardened streamable-HTTP on PORT instead of stdio",
    )
    parser.add_argument(
        "--http-host",
        default="127.0.0.1",
        metavar="ADDR",
        help="bind address for --http (default 127.0.0.1; set 0.0.0.0 only on "
        "a trusted LAN, ideally with a firewall rule and VM_MCP_HTTP_TOKEN)",
    )
    args = parser.parse_args()

    from .server import build_app

    app = build_app()
    if args.http:
        from .http_server import serve

        serve(app, args.http_host, args.http)
    else:
        app.run()


if __name__ == "__main__":
    main()
