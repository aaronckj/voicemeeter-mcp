"""Mixer state snapshots and diffs — "what changed since the known-good config"."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

SNAPSHOT_DIR = Path.home() / ".config" / "voicemeeter-mcp" / "snapshots"

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
    for section in ("strips", "buses"):
        base_sec = baseline.get(section, {})
        cur_sec = current.get(section, {})
        for idx in sorted(set(base_sec) | set(cur_sec), key=lambda x: int(x)):
            b = base_sec.get(idx, {})
            c = cur_sec.get(idx, {})
            for key in sorted(set(b) | set(c)):
                if b.get(key) != c.get(key):
                    changes.append(
                        {
                            "where": f"{section[:-1]} {idx} ({c.get('label') or b.get('label')})",
                            "param": key,
                            "baseline": b.get(key),
                            "current": c.get(key),
                        }
                    )
    return changes


def save_snapshot(state: dict, name: str) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = SNAPSHOT_DIR / f"{name}-{stamp}.json"
    path.write_text(json.dumps(state, indent=2))
    return path
