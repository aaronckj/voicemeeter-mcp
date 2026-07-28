# voicemeeter-mcp

An MCP (Model Context Protocol) server for controlling
[Voicemeeter](https://vb-audio.com/Voicemeeter/) (Basic, Banana, or Potato)
on Windows: strip and bus gains, mutes, output routing, live levels, macro
buttons, presets, and audio-engine restarts.

- Uses the official Voicemeeter Remote API (via
  [voicemeeter-api](https://pypi.org/project/voicemeeter-api/)).
- **Windows-only, local-only** — the Remote API is an in-process DLL, so this
  server must run on the PC where Voicemeeter runs. From another machine,
  connect over SSH stdio (example below).
- Every mutating tool accepts `dry_run=true` and returns a preview instead of
  acting.

## Quick start (on the Voicemeeter PC)

```bash
# select your edition: basic | banana | potato   (default: banana)
set VM_MCP_KIND=banana

claude mcp add voicemeeter -s user -- uvx voicemeeter-mcp
```

From a different machine (SSH stdio):

```bash
claude mcp add voicemeeter -s user -- ssh streampc "uvx voicemeeter-mcp"
```

## Tools

| Tool | Purpose |
|---|---|
| `mixer_state` | full snapshot: every strip/bus with label, gain, mute, routing |
| `set_strip_gain` / `mute_strip` | input fader control |
| `set_strip_routing` | send a strip to A1/A2/A3/B1/B2 outputs |
| `set_bus_gain` / `mute_bus` | output control |
| `get_levels` | live post-fader levels — find silent or clipping paths |
| `trigger_macro_button` | press a Voicemeeter macro button |
| `load_preset` | load a settings XML |
| `restart_audio_engine` | the classic crackle fix |
| `health_check` | connection + version |

A typical agent ask: *"the game audio is too loud on stream"* →
`mixer_state` to find the strip by label → `set_strip_gain(strip, -12)`.

## Development

```bash
pip install -e '.[dev]'
ruff check src tests && pytest
```

Tests run anywhere (fake Remote API); only live use requires Windows.

## License

MIT
