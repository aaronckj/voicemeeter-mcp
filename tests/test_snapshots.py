from types import SimpleNamespace

from voicemeeter_mcp.client import VM
from voicemeeter_mcp.snapshots import capture_state, diff_states


class Knob:
    def __init__(self, v):
        self.knob = v


class FakeStrip:
    def __init__(self, label, gain=0.0):
        self.label = label
        self.gain = gain
        self.mute = False
        self.A1 = True
        self.B1 = False
        self.comp = Knob(0.0)
        self.gate = Knob(2.5)
        self.levels = SimpleNamespace(postfader=[-20.0])


class FakeBus:
    def __init__(self, label):
        self.label = label
        self.gain = 0.0
        self.mute = False
        self.eq = SimpleNamespace(on=False)
        self.levels = SimpleNamespace(all=[-18.0])


class FakeRemote:
    def __init__(self):
        self.strip = [FakeStrip(f"s{i}") for i in range(5)]
        self.bus = [FakeBus(f"b{i}") for i in range(5)]


def test_capture_and_diff_roundtrip():
    vm = VM(remote=FakeRemote(), kind="banana")
    baseline = capture_state(vm)
    assert baseline["strips"]["0"]["gate"] == 2.5
    assert diff_states(baseline, capture_state(vm)) == []


def test_diff_detects_changes():
    vm = VM(remote=FakeRemote(), kind="banana")
    baseline = capture_state(vm)
    vm.remote.strip[1].gain = -12.0
    vm.remote.strip[1].mute = True
    vm.remote.bus[0].eq = SimpleNamespace(on=True)
    changes = diff_states(baseline, capture_state(vm))
    params = {(c["where"], c["param"]) for c in changes}
    assert ("strip 1 (s1)", "gain") in params
    assert ("strip 1 (s1)", "mute") in params
    assert ("bus 0 (b0)", "eq") in params
    assert len(changes) == 3
