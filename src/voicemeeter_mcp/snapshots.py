"""Mixer state snapshots and diffs — "what changed since the known-good config"."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path

SNAPSHOT_DIR = Path.home() / ".config" / "voicemeeter-mcp" / "snapshots"
_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def resolve_snapshot_path(path: str) -> Path:
    """Resolve a snapshot path, refusing anything outside SNAPSHOT_DIR."""
    rp = Path(path).expanduser().resolve()
    base = SNAPSHOT_DIR.resolve()
    if not rp.is_relative_to(base):
        raise ValueError(f"snapshot path must be inside {base}")
    return rp

STRIP_PARAMS = ("gain", "mute", "A1", "A2", "A3", "B1", "B2", "B3", "comp", "gate")
BUS_PARAMS = ("gain", "mute", "eq")


def capture_state(vm) -> dict:
    hw, virt, buses = vm.counts()
    state: dict = {"kind": vm.kind, "strips": {}, "buses": {}}
    for i in range(hw + virt):
        s = vm.strip(i)
        entry = {"label": s.label}
        for p in STRIP_PARAMS:
            if hasattr(s, p):
                v = getattr(s, p)
                # comp/gate are sub-objects (knob) in some lib versions
                v = getattr(v, "knob", v)
                entry[p] = round(v, 2) if isinstance(v, float) else v
        state["strips"][str(i)] = entry
    for i in range(buses):
        b = vm.bus(i)
        entry = {"label": b.label}
        for p in BUS_PARAMS:
            if hasattr(b, p):
                v = getattr(b, p)
                v = getattr(v, "on", v)
                entry[p] = round(v, 2) if isinstance(v, float) else v
        state["buses"][str(i)] = entry
    return state


def diff_states(baseline: dict, current: dict) -> list[dict]:
    """List every parameter that differs between two snapshots."""
    changes: list[dict] = []
    for section, singular in (("strips", "strip"), ("buses", "bus")):
        base_sec = baseline.get(section, {})
        cur_sec = current.get(section, {})
        for idx in sorted(set(base_sec) | set(cur_sec), key=lambda x: int(x)):
            b = base_sec.get(idx, {})
            c = cur_sec.get(idx, {})
            for key in sorted(set(b) | set(c)):
                if b.get(key) != c.get(key):
                    changes.append(
                        {
                            "where": f"{singular} {idx} ({c.get('label') or b.get('label')})",
                            "param": key,
                            "baseline": b.get(key),
                            "current": c.get(key),
                        }
                    )
    return changes


def save_snapshot(state: dict, name: str) -> Path:
    if not _NAME_RE.match(name):
        raise ValueError("snapshot name must be 1-64 chars of letters, digits, _ or -")
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = SNAPSHOT_DIR / f"{name}-{stamp}.json"
    path.write_text(json.dumps(state, indent=2))
    return path
