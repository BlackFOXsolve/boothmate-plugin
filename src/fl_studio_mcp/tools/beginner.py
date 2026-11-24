"""Beginner layer: one-call beats, chords, 808s and booth commands.

These tools sit on top of the upstream primitives (step sequencer, piano-roll
note bridge, transport) so a first-time producer can say "make me a dark trap
beat at 140" or "run it back" and get a result. Every write still goes through
the safety layer: dry-run aware, logged, and undoable with
fl_rollback_last_change.
"""
from __future__ import annotations

import time
from typing import Annotated, Dict, List, Literal, Optional

from fastmcp import FastMCP
from pydantic import Field

from .. import protocol, safety
from ..connection import fetch_all_pages, get_bridge
from .. import editions, fl_launcher
from ..music import hiphop as hh
from .transport import _safe_call

# Pause between two piano-roll writes so FL finishes running the first script
# before the second one overwrites it.
_PIANO_ROLL_GAP_S = 1.5
_BEATS_PER_BAR = 4


def _channels():
    data = fetch_all_pages(get_bridge(), protocol.CMD_CHANNEL_LIST, "channels")
    return data.get("channels", []) if isinstance(data, dict) else []


def _write_drums(patterns: Dict[str, str], roles: Dict[str, int], tool: str):
    """All drum lanes as ONE undo step."""
    writes, written = [], {}
    for role, steps_str in patterns.items():
        ch = roles.get(role)
        if ch is None:
            continue
        on = [i for i, c in enumerate(steps_str) if c == "x"]
        length = len(steps_str)

        def _restore(before, ch=ch, length=length):
            return {"command": protocol.CMD_CHANNEL_SET_GRID,
                    "params": {"channel": ch, "length": length,
                               "steps": before.get("steps", [])}}
        writes.append({"snap_scope": "grid:%d:%d" % (ch, length),
                       "command": protocol.CMD_CHANNEL_SET_GRID,
                       "params": {"channel": ch, "steps": on, "length": length},
                       "restore": _restore})
        written[role] = {"channel": ch, "pattern": steps_str}
    if not writes:
        return {"ok": False, "written": {}}
    res = safety.safe_write_group(get_bridge(), tool=tool, scope="beginner_drums",
                                  writes=writes, delay=0.1)
    res["written"] = written
    return res


def _write_notes(notes: List[dict], channel: Optional[int], label: str):
    preview = safety.preview_write(tool=label, params={"notes": notes, "channel": channel})
    if preview is not None:
        return preview
    bridge = get_bridge()
    if channel is not None:
        bridge.call(protocol.CMD_CHANNEL_SELECT, {"channel": channel})
    return bridge.apply_notes(notes, "replace")


def _readable(notes):
    return [{"note": hh.note_name(n["pitch"]), "bar": round(n["time_bars"] + 1, 3),
             "len_bars": n["length_bars"], **({"slide": True} if n.get("porta") else {})}
            for n in notes]


def register(mcp: FastMCP) -> None:
    _RO = {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True}
    _WR = {"readOnlyHint": False, "destructiveHint": True,
           "idempotentHint": False, "openWorldHint": True}

    # ------------------------------------------------------------------ setup
    # Plain-language next steps. Never send a beginner to a terminal: each
    # status names the BoothMate tool Claude should call instead.
    _BEGINNER_NEXT = {
        "FL_NOT_INSTALLED": ("FL Studio isn't installed on this computer. Install it from "
                             "image-line.com (the free trial works), open it once, then ask "
                             "me to set up BoothMate.", None),
        "USER_DATA_MISSING": ("FL Studio hasn't been opened on this computer yet.", "open_fl_studio"),
        "CONTROLLER_MISSING": ("BoothMate isn't installed into FL Studio yet.", "setup_boothmate"),
        "VERSION_MISMATCH": ("BoothMate's FL Studio script needs updating.", "setup_boothmate"),
        "FL_CLOSED": ("FL Studio is closed.", "open_fl_studio"),
        "NO_HEARTBEAT": ("FL Studio is open but hasn't loaded BoothMate yet. It needs one "
                         "restart (save your project first).", "open_fl_studio"),
        "PING_TIMEOUT": ("FL Studio is busy, probably showing a window or message.", "open_fl_studio"),
        "PORTS_MISSING": ("On Windows, BoothMate needs two free loopMIDI ports named "
                          "'FLStudioMCP RX' and 'FLStudioMCP TX'. Install loopMIDI from "
                          "tobias-erichsen.de and add them, then ask me again.", None),
        "MIDI_UNAVAILABLE": ("This copy of Claude can't use MIDI directly. Ask for help at "
                             "github.com/BlackFOXsolve/boothmate-plugin/issues.", None),
        "BRIDGE_STOPPED": ("BoothMate's background helper isn't running. Ask for help at "
                           "github.com/BlackFOXsolve/boothmate-plugin/issues.", None),
    }

    def _report(diag: dict) -> dict:
        status = diag["status"]
        say, tool = _BEGINNER_NEXT.get(status, ("FL Studio isn't connected yet.", "setup_boothmate"))
        return {"ready": False, "status": status, "say": say, "next_tool": tool,
                "fl_running": fl_launcher.is_running(),
                "edition": editions.describe(editions.get())}

    # ------------------------------------------------------------------ setup
    @mcp.tool(annotations={"title": "Studio check (start here)", **_RO})
    def studio_check() -> dict:
        """START HERE. Checks FL Studio is connected, reads the Channel rack,
        and reports which sounds were found for each beat role (kick, snare,
        clap, hat, open_hat, 808, chords) plus what's missing. Also reports
        the user's FL Studio edition (ask once if unknown, then call
        set_fl_edition). When not ready it returns `next_tool`: call it
        (open_fl_studio needs restart=true only after the user has saved).
        Never tell the user to run terminal commands. Relay `say`."""
        from .. import setup_cli
        diag = setup_cli.diagnose(wait=3.0)
        if diag["status"] != "READY":
            return _report(diag)
        chans = _channels()
        roles = hh.match_channels(chans)
        missing = [r for r in ("kick", "snare", "hat", "808", "chords") if r not in roles]
        say = "Connected to FL Studio. Found: %s." % (
            ", ".join("%s on channel %d" % (r, i) for r, i in roles.items()) or "no named sounds")
        if missing:
            say += (" Missing: %s. Drag a sound for each into the Channel rack and name it "
                    "(e.g. '808', 'Keys'), or tell me which channel to use." % ", ".join(missing))
        return {"ready": True, "roles": roles, "missing": missing,
                "channels": [{"index": c.get("i", c.get("index")), "name": c.get("name")}
                             for c in chans],
                "edition": editions.describe(editions.get()),
                "say": say}

    @mcp.tool(annotations={"title": "Install BoothMate into FL Studio",
                           "readOnlyHint": False, "destructiveHint": False,
                           "idempotentHint": True, "openWorldHint": False})
    def setup_boothmate() -> dict:
        """One-time install, so beginners never open a terminal. Copies the
        BoothMate controller script into FL Studio's Settings/Hardware folder
        (an older, different copy is backed up, never overwritten) and the
        MCP_Apply script into the Piano roll scripts folder, then checks the
        connection. FL Studio links BoothMate by itself; if FL was already
        open it needs one restart (open_fl_studio with restart=true, after
        the user saves). Returns `say` and `next_tool`."""
        from .. import setup_cli
        installed = setup_cli.install_controller()
        if not installed.get("ok"):
            return {"ok": False, "installed": installed, "next_tool": "open_fl_studio",
                    "say": "FL Studio needs to be opened once so it creates its settings "
                           "folder. I can open it for you."}
        note_script = setup_cli.seed_note_bridge()
        diag = setup_cli.diagnose(wait=3.0)
        if diag["status"] == "READY":
            return {"ok": True, "controller": installed, "piano_roll_script": note_script,
                    "status": "READY", "say": "All set. BoothMate is connected to FL Studio."}
        out = _report(diag)
        out.update(ok=True, controller=installed, piano_roll_script=note_script)
        if fl_launcher.is_running():
            out["say"] = ("Installed. FL Studio needs one restart to load BoothMate. "
                          "Save your project, then I'll restart it for you.")
            out["next_tool"] = "open_fl_studio"
        return out

    @mcp.tool(annotations={"title": "Open (or restart) FL Studio",
                           "readOnlyHint": False, "destructiveHint": False,
                           "idempotentHint": True, "openWorldHint": False})
    def open_fl_studio(
        restart: Annotated[bool, Field(description="Quit and reopen FL Studio. Only after the user has saved their project or said it's fine; FL shows its own save prompt if needed.")] = False,
    ) -> dict:
        """Open FL Studio for the user, close its start-up welcome window, and
        wait until BoothMate is connected. Notices trial mode from the
        welcome window. Use whenever studio_check says FL is closed, or (with
        restart=true, after the user agrees) to load BoothMate the first time."""
        from .. import setup_cli
        steps = {}
        if restart and fl_launcher.is_running():
            steps["quit"] = fl_launcher.quit_app()
            if not steps["quit"]["ok"]:
                return {"ok": False, "steps": steps, "say": steps["quit"]["error"]}
            time.sleep(2.0)
        if not fl_launcher.is_running():
            steps["launch"] = fl_launcher.launch()
            if not steps["launch"]["ok"]:
                return {"ok": False, "steps": steps, "say": steps["launch"]["error"]}
        # Wait for FL's window, then close the welcome screen.
        welcome = {"ok": False}
        for _ in range(30):
            time.sleep(2.0)
            welcome = fl_launcher.dismiss_welcome()
            if welcome.get("ok"):
                break
        steps["welcome"] = welcome
        if welcome.get("trial"):
            editions.note_trial_seen()
        diag = setup_cli.diagnose(wait=15.0)
        if diag["status"] == "READY":
            say = "FL Studio is open and BoothMate is connected."
            if editions.get() == "trial":
                say += (" You're on the FL Studio trial: export your beat before closing "
                        "FL Studio, because saved trial projects can't be reopened.")
            return {"ok": True, "steps": steps, "status": "READY",
                    "edition": editions.describe(editions.get()), "say": say}
        out = _report(diag)
        out.update(ok=False, steps=steps)
        if diag["status"] == "NO_HEARTBEAT" and not restart:
            out["say"] = ("FL Studio is open, but BoothMate isn't loaded in it yet. It needs "
                          "one restart; save your project and I'll restart it.")
        return out

    @mcp.tool(annotations={"title": "Remember the user's FL Studio edition",
                           "readOnlyHint": False, "destructiveHint": False,
                           "idempotentHint": True, "openWorldHint": False})
    def set_fl_edition(
        edition: Annotated[str, Field(description="trial, fruity, producer, signature or all_plugins.")],
    ) -> dict:
        """Save which FL Studio the user has (asked once). BoothMate adapts:
        trial users get export reminders, Fruity Edition can't record audio,
        Signature and All Plugins include NewTone for vocal tuning."""
        try:
            e = editions.set_edition(edition)
        except ValueError as err:
            return {"ok": False, "error": str(err)}
        return {"ok": True, **editions.describe(e)}

    @mcp.tool(annotations={"title": "List genres and moods", **_RO})
    def beat_styles() -> dict:
        """Genres (with default tempo and mood) and moods (chord progressions)
        that make_beat, write_chords and write_808 understand."""
        return {"ok": True, **hh.describe()}

    @mcp.tool(annotations={"title": "Scale and chords for a key (for melodies)", **_RO})
    def beat_theory(
        key: Annotated[str, Field(description="e.g. 'F# minor', 'Bb', 'C major'.")],
        mood: Annotated[str, Field(description="Mood whose progression to show.")] = "dark",
    ) -> dict:
        """Scale notes and the mood's chords in a key, with FL note names. Use
        this before writing a melody with fl_write_piano_roll_notes so every
        note fits the beat. Read-only."""
        prog = hh.progression(key, mood)
        steps = hh.SCALES[prog["scale"]]
        root = prog["root_pc"]
        scale = [hh.note_name(60 + root + s).rstrip("0123456789") for s in steps]
        return {"ok": True, "key": prog["key"], "scale_type": prog["scale"],
                "scale_notes": scale,
                "scale_midi_from_C5": [60 + root + s for s in steps],
                "chords": [c["name"] for c in prog["chords"]], "about": prog["about"],
                "tip": "Melodies sound best landing on chord tones on beats 1 and 3."}

    # ------------------------------------------------------------------ writes
    @mcp.tool(annotations={"title": "Write a drum pattern by genre", **_WR})
    def write_drums(
        genre: Annotated[str, Field(description="trap, drill, boom_bap, rnb, lofi, jersey_club.")] = "trap",
        bars: Annotated[int, Field(ge=1, le=16, description="Pattern length in bars.")] = 4,
        fill: Annotated[bool, Field(description="Put a drum fill in the last bar.")] = True,
        channels: Annotated[Optional[Dict[str, int]], Field(description="Force role -> channel, e.g. {'kick': 0, 'snare': 3}. Roles: kick, snare, clap, hat, open_hat.")] = None,
    ) -> dict:
        """Program a genre drum pattern into the step sequencer of the CURRENT
        pattern, matching drum sounds by channel name (Kick, Snare, Clap, Hat,
        Open Hat). One undo step. Works without the piano-roll setup."""
        try:
            genre = hh.resolve_genre(genre)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        roles = hh.match_channels(_channels(), channels)
        pats = hh.merge_backbeat(hh.drum_patterns(genre, bars, fill), roles)
        res = _write_drums(pats, roles, "write_drums")
        res.update(genre=genre, bars=bars,
                   skipped=[r for r in pats if r not in roles])
        if res.get("skipped"):
            res["say"] = ("No channel found for %s. Add those sounds to the Channel rack, "
                          "or tell me which channel to use." % ", ".join(res["skipped"]))
        return res

    @mcp.tool(annotations={"title": "Write chords by mood", **_WR})
    def write_chords(
        key: Annotated[str, Field(description="e.g. 'F# minor', 'C', 'Bb major'. Minor if not said.")],
        mood: Annotated[str, Field(description="dark, sad, menacing, hype, chill, love, happy.")] = "dark",
        channel: Annotated[Optional[int], Field(ge=0, description="Channel for chords; auto-found by name (Keys, Piano, Pad...) if omitted.")] = None,
        bars_per_chord: Annotated[float, Field(gt=0, le=4)] = 1.0,
        repeat: Annotated[int, Field(ge=1, le=4, description="Times to repeat the progression.")] = 1,
        degrees: Annotated[Optional[List[int]], Field(description="Custom progression as scale degrees 1-7, e.g. [1,6,3,7]. Overrides the mood's.")] = None,
    ) -> dict:
        """Write a 4-chord progression for a mood, in a key, into the piano roll
        of a chords channel. Needs the one-time 'MCP_Apply' arm per FL session.
        Replaces that channel's notes in the current pattern."""
        try:
            prog = hh.progression(key, mood, degrees)
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        if channel is None:
            channel = hh.match_channels(_channels()).get("chords")
            if channel is None:
                return {"ok": False, "error": "No chords channel found.",
                        "say": "Add a keys/piano/pad sound to the Channel rack (or tell me "
                               "its channel number) and I'll write the chords."}
        notes = hh.chord_notes(prog, bars_per_chord, repeat=repeat)
        res = _write_notes(notes, channel, "write_chords")
        return {"ok": bool(res.get("ok", True)), "key": prog["key"], "mood": prog["mood"],
                "chords": [c["name"] for c in prog["chords"]], "channel": channel,
                "about": prog["about"], "bridge": res}

    @mcp.tool(annotations={"title": "Write an 808 line", **_WR})
    def write_808(
        key: Annotated[str, Field(description="Same key as the chords, e.g. 'F# minor'.")],
        genre: Annotated[str, Field(description="Sets the rhythm (follows the genre's kick) and slides.")] = "trap",
        mood: Annotated[Optional[str], Field(description="Chord progression to follow; genre default if omitted.")] = None,
        channel: Annotated[Optional[int], Field(ge=0, description="808/bass channel; auto-found by name if omitted.")] = None,
        bars_per_chord: Annotated[float, Field(gt=0, le=4)] = 1.0,
        repeat: Annotated[int, Field(ge=1, le=4)] = 1,
    ) -> dict:
        """Write an 808 that hits with the kick and follows the chord roots
        (drill adds octave slides). Piano-roll write: needs the 'MCP_Apply' arm."""
        try:
            g = hh.resolve_genre(genre)
            prog = hh.progression(key, mood or hh.GENRES[g]["mood"])
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        if channel is None:
            channel = hh.match_channels(_channels()).get("808")
            if channel is None:
                return {"ok": False, "error": "No 808 channel found.",
                        "say": "Add an 808 to the Channel rack and name it '808' (or tell me "
                               "its channel number)."}
        notes = hh.eight_oh_eight(prog, g, bars_per_chord, repeat)
        res = _write_notes(notes, channel, "write_808")
        return {"ok": bool(res.get("ok", True)), "key": prog["key"], "genre": g,
                "channel": channel, "notes": _readable(notes), "bridge": res}

    @mcp.tool(annotations={"title": "Make a whole beat (one call)", **_WR})
    def make_beat(
        genre: Annotated[str, Field(description="trap, drill, boom_bap, rnb, lofi, jersey_club.")] = "trap",
        key: Annotated[str, Field(description="e.g. 'F# minor'. Minor if not said.")] = "C minor",
        mood: Annotated[Optional[str], Field(description="Override the genre's mood: dark, sad, menacing, hype, chill, love, happy.")] = None,
        bpm: Annotated[Optional[float], Field(ge=40, le=220, description="Tempo; genre default if omitted.")] = None,
        parts: Annotated[List[Literal["drums", "chords", "808"]], Field(description="Which parts to write.")] = ["drums", "chords", "808"],  # noqa: B006
        channels: Annotated[Optional[Dict[str, int]], Field(description="Force role -> channel, e.g. {'808': 5, 'chords': 4}.")] = None,
    ) -> dict:
        """The beginner one-shot: sets the tempo, programs genre drums, then
        writes chords and an 808 in the key, all into the CURRENT pattern
        (4 bars). Drums work right away; chords/808 need the one-time
        'MCP_Apply' arm in the piano roll. Tell the user what you'll make
        before calling. Undo: fl_rollback_last_change (once per part + tempo)."""
        try:
            g = hh.resolve_genre(genre)
            prog = hh.progression(key, mood or hh.GENRES[g]["mood"])
        except ValueError as e:
            return {"ok": False, "error": str(e)}
        tempo = float(bpm or hh.GENRES[g]["bpm"])
        bars = len(prog["chords"])
        roles = hh.match_channels(_channels(), channels)
        out = {"genre": g, "key": prog["key"], "mood": prog["mood"], "bpm": tempo,
               "bars": bars, "chords": [c["name"] for c in prog["chords"]],
               "roles": roles, "parts": {}, "notes_for_user": []}

        out["parts"]["tempo"] = safety.safe_write(
            get_bridge(), tool="set_tempo", scope="tempo",
            command=protocol.CMD_SET_TEMPO, params={"bpm": tempo},
            build_restore=lambda b: {"command": protocol.CMD_SET_TEMPO,
                                     "params": {"bpm": b["bpm"]}})

        if "drums" in parts:
            pats = hh.merge_backbeat(hh.drum_patterns(g, bars, True), roles)
            out["parts"]["drums"] = _write_drums(pats, roles, "make_beat_drums")
            skipped = [r for r in pats if r not in roles]
            if skipped:
                out["notes_for_user"].append("No channel for %s: those drum lanes were skipped."
                                             % ", ".join(skipped))

        wrote_piano = False
        for part, role, build in (
            ("chords", "chords", lambda: hh.chord_notes(prog, 1.0)),
            ("808", "808", lambda: hh.eight_oh_eight(prog, g, 1.0)),
        ):
            if part not in parts:
                continue
            ch = roles.get(role)
            if ch is None:
                out["parts"][part] = {"ok": False, "skipped": "no %s channel" % role}
                out["notes_for_user"].append(
                    "Add a %s sound to the Channel rack and name it '%s' to get %s."
                    % ("keys/piano" if role == "chords" else "808", "Keys" if role == "chords" else "808", part))
                continue
            if wrote_piano and not safety.is_dry_run():
                time.sleep(_PIANO_ROLL_GAP_S)
            out["parts"][part] = _write_notes(build(), ch, "make_beat_" + part)
            wrote_piano = True
        if wrote_piano:
            out["notes_for_user"].append(
                "If the chords or 808 didn't show up: open the Piano roll, run "
                "Scripting > MCP Apply once (one time per FL session), then ask again.")
        out["ok"] = all(p.get("ok", True) is not False for p in out["parts"].values()
                        if not p.get("skipped"))
        return out

    # ------------------------------------------------------------------ booth
    @mcp.tool(annotations={"title": "Booth command (run it back, from the top...)",
                           "readOnlyHint": False, "destructiveHint": False,
                           "idempotentHint": False, "openWorldHint": True})
    def booth(
        action: Annotated[Literal["run_it_back", "from_bar", "stop", "play",
                                  "record_take", "back_up"],
                          Field(description=(
                              "run_it_back = restart from the top and play ('run it back', "
                              "'from the top', 'again'); from_bar = jump to a bar and play "
                              "('take it from bar 9', 'go to the hook'); stop ('cut', 'hold up'); "
                              "play ('let it ride'); record_take = arm recording and play from "
                              "a bar ('let me lay it', 'punch in at 17'); back_up = go back N bars "
                              "and play ('back it up 4').")
                          )],
        bar: Annotated[Optional[int], Field(ge=1, description="Bar number (1 = song start) for from_bar / record_take; bars to go back for back_up.")] = None,
    ) -> dict:
        """Studio-talk transport for artists in the booth. Map what the artist
        says to an action. Assumes 4/4. record_take is the only action that
        records; confirm before it if the artist hasn't clearly asked to record."""
        def goto(beats):
            return _safe_call(protocol.CMD_SET_SONG_POS, {"beats": float(max(beats, 0.0))})

        steps = []
        if action == "stop":
            steps.append(_safe_call(protocol.CMD_STOP))
        elif action == "play":
            steps.append(_safe_call(protocol.CMD_PLAY))
        elif action == "run_it_back":
            steps += [_safe_call(protocol.CMD_STOP), goto(0), _safe_call(protocol.CMD_PLAY)]
        elif action == "from_bar":
            if bar is None:
                return {"ok": False, "error": "Which bar? e.g. bar=9"}
            steps += [_safe_call(protocol.CMD_STOP), goto((bar - 1) * _BEATS_PER_BAR),
                      _safe_call(protocol.CMD_PLAY)]
        elif action == "back_up":
            n = bar or 4
            pos = _safe_call(protocol.CMD_GET_SONG_POS) or {}
            cur = float(pos.get("position_beats", 0.0)) if isinstance(pos, dict) else 0.0
            steps += [_safe_call(protocol.CMD_STOP), goto(cur - n * _BEATS_PER_BAR),
                      _safe_call(protocol.CMD_PLAY)]
        elif action == "record_take":
            if not editions.can_record_audio():
                return {"ok": False, "action": action,
                        "say": "FL Studio Fruity Edition can't record audio. Recording vocals "
                               "needs Producer Edition or higher."}
            state = _safe_call(protocol.CMD_GET_PLAY_STATE) or {}
            steps.append(_safe_call(protocol.CMD_STOP))
            steps.append(goto(((bar or 1) - 1) * _BEATS_PER_BAR))
            if not (isinstance(state, dict) and state.get("recording")):
                steps.append(_safe_call(protocol.CMD_RECORD))
            steps.append(_safe_call(protocol.CMD_PLAY))
        return {"ok": True, "action": action, "bar": bar, "steps": steps}
