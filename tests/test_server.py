import asyncio
import json
from types import SimpleNamespace

import voicemeeter_mcp.client as client_mod
from voicemeeter_mcp.client import VM, VmError
from voicemeeter_mcp.server import build_app

EXPECTED = {
    "mixer_state", "set_strip_gain", "mute_strip", "set_strip_routing",
    "set_bus_gain", "mute_bus", "get_levels", "trigger_macro_button",
    "load_preset", "restart_audio_engine", "health_check",
    "snapshot_state", "diff_vs_snapshot", "set_strip_comp", "set_strip_gate",
    "set_strip_label", "set_bus_label",
    "set_bus_eq", "set_strip_device",
}


class FakeStrip:
    def __init__(self, label):
        self.label = label
        self.gain = 0.0
        self.mute = False
        self.A1 = True
        self.A2 = False
        self.B1 = False
        self.levels = SimpleNamespace(postfader=[-20.0, -20.0])


class FakeBus:
    def __init__(self, label):
        self.label = label
        self.gain = 0.0
        self.mute = False
        self.levels = SimpleNamespace(all=[-18.0, -18.0])


class FakeRemote:
    def __init__(self):
        self.strip = [FakeStrip(f"strip{i}") for i in range(5)]
        self.bus = [FakeBus(f"bus{i}") for i in range(5)]
        self.version = "banana 2.1.1.4"


def make_app():
    client_mod._vm = VM(remote=FakeRemote(), kind="banana")
    return build_app()


def teardown_function():
    client_mod._vm = None


def call_tool(app, name, args=None):
    result = asyncio.run(app.call_tool(name, args or {}))
    blocks = result[0] if isinstance(result, tuple) else result
    return json.loads(blocks[0].text)


def test_all_tools_registered():
    app = make_app()
    tools = asyncio.run(app.list_tools())
    assert {t.name for t in tools} == EXPECTED


def test_mixer_state_counts_banana():
    app = make_app()
    out = call_tool(app, "mixer_state")
    assert out["kind"] == "banana"
    assert len(out["strips"]) == 5  # 3 hardware + 2 virtual
    assert len(out["buses"]) == 5
    assert out["strips"][0]["routing"]["A1"] is True


def test_set_strip_gain_clamps():
    app = make_app()
    call_tool(app, "set_strip_gain", {"strip": 0, "gain_db": -100})
    assert client_mod._vm.strip(0).gain == -60.0


def test_mute_strip_dry_run_no_change():
    app = make_app()
    out = call_tool(app, "mute_strip", {"strip": 1, "muted": True, "dry_run": True})
    assert out["preview"] is True
    assert client_mod._vm.strip(1).mute is False


def test_routing_validation():
    app = make_app()
    out = call_tool(app, "set_strip_routing", {"strip": 0, "route": "Z9", "enabled": True})
    assert "error" in out
    out = call_tool(app, "set_strip_routing", {"strip": 0, "route": "b1", "enabled": True})
    assert out["enabled"] is True
    assert client_mod._vm.strip(0).B1 is True


def test_strip_index_out_of_range():
    client_mod._vm = VM(remote=FakeRemote(), kind="banana")
    try:
        client_mod._vm.strip(9)
        raise AssertionError("expected VmError")
    except VmError as exc:
        assert "out of range" in str(exc)
