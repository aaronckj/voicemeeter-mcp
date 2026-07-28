"""Voicemeeter Remote API connection wrapper (via voicemeeter-api / voicemeeterlib)."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("voicemeeter_mcp")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# Strip/bus counts per Voicemeeter kind: (hardware strips, virtual strips, buses)
KINDS = {
    "basic": (2, 1, 2),
    "banana": (3, 2, 5),
    "potato": (5, 3, 8),
}


class VmError(RuntimeError):
    pass


class VM:
    """Lazy holder for a voicemeeterlib remote (injectable for tests)."""

    def __init__(self, remote: Any = None, kind: str | None = None):
        self._remote = remote
        self.kind = kind or os.environ.get("VM_MCP_KIND", "banana")
        if self.kind not in KINDS:
            raise VmError(f"unknown Voicemeeter kind: {self.kind!r} (basic|banana|potato)")

    @property
    def remote(self) -> Any:
        if self._remote is None:
            try:
                import voicemeeterlib
            except ImportError as exc:
                raise VmError(
                    "voicemeeter-api is Windows-only; run this server on the PC "
                    "where Voicemeeter is installed"
                ) from exc
            try:
                self._remote = voicemeeterlib.api(self.kind)
                self._remote.login()
            except Exception as exc:
                raise VmError(
                    f"cannot connect to Voicemeeter {self.kind} — is it running? ({exc})"
                ) from exc
        return self._remote

    def counts(self) -> tuple[int, int, int]:
        return KINDS[self.kind]

    def strip(self, i: int) -> Any:
        hw, virt, _ = self.counts()
        if not 0 <= i < hw + virt:
            raise VmError(f"strip index {i} out of range for {self.kind} (0..{hw + virt - 1})")
        return self.remote.strip[i]

    def bus(self, i: int) -> Any:
        _, _, buses = self.counts()
        if not 0 <= i < buses:
            raise VmError(f"bus index {i} out of range for {self.kind} (0..{buses - 1})")
        return self.remote.bus[i]


def preview(action: str, would: dict) -> dict:
    return {"preview": True, "action": action, "would": would}


_vm: VM | None = None


def get_vm() -> VM:
    global _vm
    if _vm is None:
        _vm = VM()
    return _vm
