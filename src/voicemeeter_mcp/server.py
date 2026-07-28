"""FastMCP app: Voicemeeter strips, buses, macro buttons, presets."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .client import get_vm, preview

ROUTES = ("A1", "A2", "A3", "B1", "B2", "B3")


def build_app() -> FastMCP:
    mcp = FastMCP(
        "voicemeeter",
        instructions=(
            "Control Voicemeeter (Basic/Banana/Potato) on this Windows machine: "
            "strip/bus gains and mutes, output routing, levels, macro buttons, "
            "and presets. Strips are inputs (hardware first, then virtual); "
            "buses are outputs (A = hardware, B = virtual). Every mutating tool "
            "accepts dry_run=True."
        ),
    )

    @mcp.tool()
    def mixer_state() -> dict:
        """Full mixer snapshot: every strip and bus with label, gain, mute, routing."""
        vm = get_vm()
        hw, virt, buses = vm.counts()
        strips = []
        for i in range(hw + virt):
            s = vm.strip(i)
            routing = {r: bool(getattr(s, r, False)) for r in ROUTES if hasattr(s, r)}
            strips.append(
                {
                    "index": i,
                    "label": s.label,
                    "kind": "hardware" if i < hw else "virtual",
                    "gain_db": round(s.gain, 1),
                    "muted": bool(s.mute),
                    "routing": routing,
                }
            )
        bus_list = []
        for i in range(buses):
            b = vm.bus(i)
            bus_list.append(
                {
                    "index": i,
                    "label": b.label,
                    "gain_db": round(b.gain, 1),
                    "muted": bool(b.mute),
                }
            )
        return {"kind": vm.kind, "strips": strips, "buses": bus_list}

    @mcp.tool()
    def set_strip_gain(strip: int, gain_db: float, dry_run: bool = False) -> dict:
        """Set a strip's fader gain in dB (0 = unity; range -60..+12)."""
        if dry_run:
            return preview("set_strip_gain", {"strip": strip, "gain_db": gain_db})
        vm = get_vm()
        vm.strip(strip).gain = max(-60.0, min(12.0, gain_db))
        return {"strip": strip, "gain_db": gain_db}

    @mcp.tool()
    def mute_strip(strip: int, muted: bool, dry_run: bool = False) -> dict:
        """Mute or unmute an input strip."""
        if dry_run:
            return preview("mute_strip", {"strip": strip, "muted": muted})
        vm = get_vm()
        vm.strip(strip).mute = muted
        return {"strip": strip, "muted": muted}

    @mcp.tool()
    def set_strip_routing(strip: int, route: str, enabled: bool, dry_run: bool = False) -> dict:
        """Send or stop sending a strip to an output. route: A1|A2|A3|B1|B2 (kind-dependent)."""
        route = route.upper()
        if route not in ROUTES:
            return {"error": f"route must be one of {ROUTES}"}
        if dry_run:
            return preview(
                "set_strip_routing", {"strip": strip, "route": route, "enabled": enabled}
            )
        vm = get_vm()
        s = vm.strip(strip)
        if not hasattr(s, route):
            return {"error": f"{vm.kind} has no {route} routing on strip {strip}"}
        setattr(s, route, enabled)
        return {"strip": strip, "route": route, "enabled": enabled}

    @mcp.tool()
    def set_bus_gain(bus: int, gain_db: float, dry_run: bool = False) -> dict:
        """Set a bus (output) gain in dB."""
        if dry_run:
            return preview("set_bus_gain", {"bus": bus, "gain_db": gain_db})
        vm = get_vm()
        vm.bus(bus).gain = max(-60.0, min(12.0, gain_db))
        return {"bus": bus, "gain_db": gain_db}

    @mcp.tool()
    def mute_bus(bus: int, muted: bool, dry_run: bool = False) -> dict:
        """Mute or unmute an output bus."""
        if dry_run:
            return preview("mute_bus", {"bus": bus, "muted": muted})
        vm = get_vm()
        vm.bus(bus).mute = muted
        return {"bus": bus, "muted": muted}

    @mcp.tool()
    def get_levels() -> dict:
        """Current audio levels (post-fader) per strip and bus — spot silent or clipping paths."""
        vm = get_vm()
        hw, virt, buses = vm.counts()
        return {
            "strips": [
                {
                    "index": i,
                    "label": vm.strip(i).label,
                    "levels": list(vm.strip(i).levels.postfader),
                }
                for i in range(hw + virt)
            ],
            "buses": [
                {"index": i, "label": vm.bus(i).label, "levels": list(vm.bus(i).levels.all)}
                for i in range(buses)
            ],
        }

    @mcp.tool()
    def trigger_macro_button(button: int, dry_run: bool = False) -> dict:
        """Press-and-release a Voicemeeter macro button by index."""
        if dry_run:
            return preview("trigger_macro_button", {"button": button})
        vm = get_vm()
        vm.remote.button[button].trigger = True
        vm.remote.button[button].trigger = False
        return {"triggered": button}

    @mcp.tool()
    def load_preset(xml_path: str, dry_run: bool = False) -> dict:
        """Load a Voicemeeter settings XML preset from the local filesystem."""
        if dry_run:
            return preview("load_preset", {"xml_path": xml_path})
        vm = get_vm()
        vm.remote.set("command.load", xml_path)
        return {"loaded": xml_path}

    @mcp.tool()
    def restart_audio_engine(dry_run: bool = False) -> dict:
        """Restart the Voicemeeter audio engine (fixes crackle/desync; brief dropout)."""
        if dry_run:
            return preview("restart_audio_engine", {"note": "brief audio dropout"})
        vm = get_vm()
        vm.remote.command.restart()
        return {"restarted": True}

    @mcp.tool()
    def health_check() -> dict:
        """Verify connection to Voicemeeter and report kind/version."""
        try:
            vm = get_vm()
            hw, virt, buses = vm.counts()
            _ = vm.strip(0).label
            return {
                "status": "ok",
                "kind": vm.kind,
                "strips": hw + virt,
                "buses": buses,
                "version": getattr(vm.remote, "version", "unknown"),
            }
        except Exception as exc:  # noqa: BLE001 - health check reports, never raises
            return {"status": f"error: {exc}"}

    return mcp
