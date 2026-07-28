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
        help="serve streamable-HTTP on 0.0.0.0:PORT instead of stdio",
    )
    args = parser.parse_args()

    from .server import build_app

    app = build_app()
    if args.http:
        app.settings.host = "0.0.0.0"
        app.settings.port = args.http
        app.run(transport="streamable-http")
    else:
        app.run()


if __name__ == "__main__":
    main()
