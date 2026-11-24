"""FastMCP entry point for the FL Studio MCP server.

Run with::

    python -m fl_studio_mcp.server

or, after ``pip install -e .``, with::

    fl-studio-mcp

One-time setup, connection check and client entry::

    fl-studio-mcp setup
    fl-studio-mcp doctor
    fl-studio-mcp connect

To see what MIDI ports the host OS exposes::

    fl-studio-mcp --list-ports
"""

from __future__ import annotations

import logging
import os
import sys

from fastmcp import FastMCP

from . import __version__
from .connection import list_ports
from .protocol import port_from_fl_name, port_to_fl_name
from .tools import arrange as arrange_tools
from .tools import audio as audio_tools
from .tools import beginner as beginner_tools
from .tools import bulk as bulk_tools
from .tools import chains as chains_tools
from .tools import color as color_tools
from .tools import compose as compose_tools
from .tools import drums as drums_tools
from .tools import export as export_tools
from .tools import mix_doctor as mix_doctor_tools
from .tools import mixing as mixing_tools
from .tools import phase1 as phase1_tools
from .tools import pattern as pattern_tools
from .tools import pianoroll as pianoroll_tools
from .tools import plugin as plugin_tools
from .tools import presets as presets_tools
from .tools import resources as resource_defs
from .tools import routing as routing_tools
from .tools import steps as steps_tools
from .tools import transport as transport_tools


from .tools import capabilities as capabilities_tools
from .tools import loader as loader_tools
from .tools import sounds as sounds_tools
from .tools import playlist as playlist_tools
from .tools import vst as vst_tools

logger = logging.getLogger("fl_studio_mcp")


SERVER_INSTRUCTIONS = """\
BoothMate -- make beats and run sessions in FL Studio by just asking.
(Fork of flstudio-mcp by rosasynthesiz, MIT.)

BEGINNERS FIRST
  Most users are new producers and rappers. Start with studio_check, talk in
  plain language, and prefer the one-call tools: make_beat, write_drums,
  write_chords, write_808, beat_theory, and booth (run it back / from the
  top / punch in). Reach for the low-level fl_* tools only when those can't
  do what was asked. Tell the user what you're about to make before writing,
  and remind them "undo" works (fl_rollback_last_change).

CONNECTION
  Call fl_ping first. It returns a `status` code and a `next` step. If the
  status is not READY, tell the user that one step; do not retry other tools.
  One-time setup for the user is `fl-studio-mcp setup` in a terminal, then
  opening FL Studio. `fl-studio-mcp doctor` re-checks at any time.

LIMITS YOU SHOULD KNOW ABOUT (these are FL API limitations, not server bugs)
  - Cannot load new VST/AU plugin instances. You can only control plugins
    that already exist in the project.
  - Cannot load audio files or render audio.
  - Patterns: fl_arrange_new_pattern names and selects the next EMPTY
    pattern, fl_arrange_clone_pattern copies one. Patterns cannot be deleted.
  - FL refuses every write while a dialog is open (the welcome screen
    counts). The error says FL_BUSY; ask the user to close it.

When the user asks for something outside these limits, explain the limit
clearly rather than retrying.
"""


def build_server() -> FastMCP:
    mcp = FastMCP(
        name="boothmate",
        version=__version__,
        instructions=SERVER_INSTRUCTIONS,
    )
    beginner_tools.register(mcp)    # BoothMate: one-call beats, chords, 808s, booth commands
    transport_tools.register(mcp)
    phase1_tools.register(mcp)      # project/mixer/channel read+write + safety
    pianoroll_tools.register(mcp)   # Phase 2: write notes into the piano roll
    plugin_tools.register(mcp)      # Phase 1B: plugin param read/write (name or index)
    mixing_tools.register(mcp)      # Slice B: high-level EQ mixing intents
    routing_tools.register(mcp)     # Routing/cleanup Slice 1: read-only
    bulk_tools.register(mcp)        # Bulk mute/solo: server-side group orchestration
    color_tools.register(mcp)       # Track/channel coloring: name/hex -> FL RGB, one rollback unit
    arrange_tools.register(mcp)     # Arrangement Slice 1: pattern create/clone + markers
    resource_defs.register(mcp)     # MCP resources: fl://status, fl://project, ...
    audio_tools.register(mcp)       # Integration 2/3: audio analysis (tempo/key)
    compose_tools.register(mcp)     # Raga/scale composer: write Claude notes via the bridge
    chains_tools.register(mcp)      # Genre chain setup: map recipes to existing plugins
    export_tools.register(mcp)      # MIDI export: arrangement spec -> type-1 .mid on disk
    presets_tools.register(mcp)     # Preset suggester: read preset names from disk
    mix_doctor_tools.register(mcp)  # Mix Doctor: diagnose whole mix + gated apply-fixes
    steps_tools.register(mcp)       # Step sequencer: read/write drum steps (safety layer)
    drums_tools.register(mcp)       # Drums to MIDI, optionally into the step sequencer
    sounds_tools.register(mcp)      # 0.1.5 lab: find + load stock sounds, rename, link to mixer, browser
    pattern_tools.register(mcp)     # E-2: pattern list/select/rename/get_length
    capabilities_tools.register(mcp)
    loader_tools.register(mcp)
    playlist_tools.register(mcp)
    vst_tools.register(mcp)
    return mcp


def _print_ports() -> int:
    ports = list_ports()
    expected_out = port_to_fl_name()
    expected_in = port_from_fl_name()
    print("Expected port names (override via FLSTUDIO_MCP_PORT_TO_FL / _FROM_FL):")
    print("  server output (commands -> FL):  %r" % expected_out)
    print("  server input  (responses <- FL): %r" % expected_in)
    print()
    print("MIDI output ports visible to this Python process:")
    for name in ports["outputs"]:
        marker = "  -> " if expected_out.lower() in name.lower() else "     "
        print(marker + repr(name))
    print()
    print("MIDI input ports visible to this Python process:")
    for name in ports["inputs"]:
        marker = "  <- " if expected_in.lower() in name.lower() else "     "
        print(marker + repr(name))
    return 0


def _ensure_controller_installed() -> None:
    """BoothMate: put the FL controller script in place BEFORE any MIDI port
    exists, so FL links the port to BoothMate the first time it sees it and
    nobody has to open MIDI Settings. Quiet and best-effort: if FL Studio has
    never been opened, setup_boothmate handles it later."""
    try:
        from . import setup_cli
        res = setup_cli.install_controller()
        if res.get("ok"):
            setup_cli.seed_note_bridge()
        logger.info("controller install at startup: %s", res.get("action", res.get("status")))
    except Exception as e:  # noqa: BLE001 - never block the server on this
        logger.warning("controller install at startup skipped: %s", e)


def warm_bridge(block: bool = False) -> None:
    """BoothMate (macOS/Linux): create the shared virtual MIDI port now, so it
    already exists when FL Studio starts. FL links devices to their script
    when it starts; a port that appears later is filed as a generic
    controller. Best-effort and quiet."""
    if sys.platform not in ("darwin", "linux"):
        return

    def _go() -> None:
        try:
            from .connection import get_bridge
            get_bridge()
            logger.info("BoothMate MIDI port ready before FL Studio starts")
        except Exception as e:  # noqa: BLE001
            logger.info("early MIDI port skipped: %s", e)

    if block:
        _go()
    else:
        import threading
        threading.Thread(target=_go, name="boothmate-warm", daemon=True).start()


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("FLSTUDIO_MCP_LOG", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    if "--list-ports" in sys.argv:
        sys.exit(_print_ports())
    if "--version" in sys.argv:
        print(__version__)
        sys.exit(0)
    if len(sys.argv) > 1 and sys.argv[1] in ("setup", "doctor", "connect"):
        from . import setup_cli
        sys.exit(setup_cli.run(sys.argv[1:]))

    _ensure_controller_installed()
    warm_bridge()
    logger.info(
        "fl-studio-mcp %s; ports: out=%r, in=%r",
        __version__, port_to_fl_name(), port_from_fl_name(),
    )
    server = build_server()
    server.run()  # stdio transport by default


if __name__ == "__main__":
    main()
