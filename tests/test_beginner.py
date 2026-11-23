"""BoothMate beginner layer: pure music engine + registered tools against a
stateful fake FL (no DAW, no MIDI, no keystrokes)."""
from __future__ import annotations

import pytest
from fastmcp import Client

from fl_studio_mcp import connection, safety
from fl_studio_mcp.music import hiphop as hh
from fl_studio_mcp.server import build_server

# ---------------------------------------------------------------- pure engine


def test_every_genre_pattern_is_whole_bars():
    for g, spec in hh.GENRES.items():
        for role, pat in spec["drums"].items():
            assert len(pat) % 16 == 0, (g, role)
            assert set(pat) <= {"x", "."}, (g, role)
        for role, pat in spec.get("fill", {}).items():
            assert len(pat) == 16, (g, role)


@pytest.mark.parametrize("bars", [1, 2, 4, 8])
def test_drum_patterns_cover_requested_bars(bars):
    for g in hh.GENRES:
        for role, s in hh.drum_patterns(g, bars).items():
            assert len(s) == bars * 16


@pytest.mark.parametrize("text,expected", [
    ("F# minor", (6, "minor")), ("Bb", (10, "minor")), ("C major", (0, "major")),
    ("am", (9, "minor")), ("Eb maj", (3, "major")), ("g#m", (8, "minor")),
])
def test_parse_key(text, expected):
    assert hh.parse_key(text) == expected


def test_parse_key_rejects_garbage():
    with pytest.raises(ValueError):
        hh.parse_key("H dorian-ish")


def test_dark_progression_in_c_minor():
    prog = hh.progression("C minor", "dark")
    assert [c["name"] for c in prog["chords"]] == ["Cm", "G#", "Fm", "G"]


def test_love_mood_uses_sevenths():
    prog = hh.progression("C major", "love")
    assert [c["name"] for c in prog["chords"]] == ["Cmaj7", "Am7", "Fmaj7", "G7"]


def test_key_quality_overrides_mood_scale():
    # 'happy' is a major mood, but the user asked for A minor.
    prog = hh.progression("A minor", "happy")
    assert prog["scale"] == "minor"
    assert prog["chords"][0]["name"] == "Am"


def test_808_follows_kick_and_chord_roots():
    prog = hh.progression("F minor", "dark")
    notes = hh.eight_oh_eight(prog, "trap")
    kick = hh.drum_patterns("trap", 4, fill=False)["kick"]
    assert [round(n["time_bars"] * 16) for n in notes] == [i for i, c in enumerate(kick) if c == "x"]
    assert all(33 <= n["pitch"] <= 56 for n in notes)
    assert notes[0]["pitch"] % 12 == 5            # F
    assert not any(n["porta"] for n in notes)


def test_drill_808_slides():
    notes = hh.eight_oh_eight(hh.progression("C# minor", "menacing"), "drill")
    assert any(n["porta"] for n in notes)


def test_match_channels_fl_default_template_plus_extras():
    chans = [{"i": 0, "name": "Kick"}, {"i": 1, "name": "Clap"}, {"i": 2, "name": "Hat"},
             {"i": 3, "name": "Snare"}, {"i": 4, "name": "808 Mafia"},
             {"i": 5, "name": "Keys"}, {"i": 6, "name": "Open Hat"}]
    assert hh.match_channels(chans) == {"kick": 0, "snare": 3, "clap": 1, "open_hat": 6,
                                        "hat": 2, "808": 4, "chords": 5}


def test_match_channels_bass_drum_is_not_808():
    roles = hh.match_channels([{"i": 0, "name": "Bass Drum"}, {"i": 1, "name": "Sub Bass"}])
    assert roles == {"kick": 0, "808": 1}


def test_merge_backbeat_folds_clap_into_snare():
    pats = {"snare": "....x...", "clap": "x.......", "kick": "x......."}
    merged = hh.merge_backbeat(pats, {"snare": 1, "kick": 0})
    assert "clap" not in merged and merged["snare"] == "x...x..."


# ---------------------------------------------------------------- tools


class FakeFL:
    def __init__(self, channels):
        self.channels = channels
        self.grids = {}
        self.bpm = 120.0
        self.pos = 0.0
        self.playing = self.recording = False
        self.selected = None
        self.notes = {}
        self.log = []

    def call(self, command, params=None, timeout=None):
        p = dict(params or {})
        self.log.append(command)
        if command == "get_project_state":
            return {"project_token": "t", "project_loading": False}
        if command == "channel_list":
            return {"total": len(self.channels), "next_start": None, "channels": self.channels}
        if command == "channel_get_grid":
            return {"ok": True, "pattern": 1,
                    "steps": self.grids.get(p["channel"], [])}
        if command == "channel_set_grid":
            self.grids[p["channel"]] = list(p["steps"])
            return {"ok": True}
        if command == "get_tempo":
            return {"bpm": self.bpm}
        if command == "set_tempo":
            self.bpm = p["bpm"]
            return {"bpm": self.bpm}
        if command == "channel_select":
            self.selected = p["channel"]
            return {"ok": True}
        if command == "stop":
            self.playing = False
            return {"playing": False, "recording": self.recording}
        if command == "play":
            self.playing = True
            return {"playing": True, "recording": self.recording}
        if command == "record":
            self.recording = not self.recording
            return {"recording": self.recording}
        if command == "get_play_state":
            return {"playing": self.playing, "recording": self.recording}
        if command == "set_song_position":
            self.pos = p["beats"]
            return {"ok": True}
        if command == "get_song_position":
            return {"position_beats": self.pos}
        return {}

    def apply_notes(self, notes, mode="replace", **_):
        self.notes[self.selected] = notes
        return {"ok": True, "count": len(notes), "triggered": True}


TEMPLATE = [{"i": 0, "name": "Kick"}, {"i": 1, "name": "Clap"}, {"i": 2, "name": "Hat"},
            {"i": 3, "name": "Snare"}, {"i": 4, "name": "808"}, {"i": 5, "name": "Keys"}]


@pytest.fixture
def fl(monkeypatch, tmp_path):
    fake = FakeFL(list(TEMPLATE))
    monkeypatch.setattr(connection, "_bridge", fake)
    monkeypatch.setattr(safety, "_DIR", tmp_path)
    monkeypatch.setattr(safety, "_PATH", tmp_path / "log.jsonl")
    monkeypatch.setattr(safety, "_log", safety.ChangeLog())
    monkeypatch.setattr(safety.time, "sleep", lambda *_: None)
    from fl_studio_mcp.tools import beginner
    monkeypatch.setattr(beginner.time, "sleep", lambda *_: None)
    safety.set_dry_run(False)
    return fake


async def _call(name, args):
    async with Client(build_server()) as client:
        return (await client.call_tool(name, args)).data


@pytest.mark.asyncio
async def test_make_beat_writes_everything_and_drums_undo_as_one(fl):
    out = await _call("make_beat", {"genre": "trap", "key": "F# minor"})
    assert out["ok"] is True and out["bpm"] == 140 and fl.bpm == 140
    assert out["chords"] == ["F#m", "D", "Bm", "C#"]
    assert set(fl.grids) == {0, 1, 2, 3}                 # kick, clap, hat, snare
    assert len(fl.notes[5]) == 12                        # 4 triads on Keys
    assert all(n["pitch"] < 57 for n in fl.notes[4])     # 808 sits low
    # Undo: piano-roll notes aren't in the changelog; drums then tempo are.
    safety.rollback_last_change(fl)
    assert all(v == [] for v in fl.grids.values())
    safety.rollback_last_change(fl)
    assert fl.bpm == 120.0


@pytest.mark.asyncio
async def test_make_beat_reports_missing_sounds(fl):
    fl.channels = [{"i": 0, "name": "Kick"}, {"i": 1, "name": "Snare"}]
    out = await _call("make_beat", {"genre": "drill", "key": "C# minor"})
    assert out["parts"]["808"]["skipped"] and out["parts"]["chords"]["skipped"]
    assert any("808" in n for n in out["notes_for_user"])
    assert set(fl.grids) == {0, 1}


@pytest.mark.asyncio
async def test_write_drums_respects_channel_override(fl):
    out = await _call("write_drums", {"genre": "boom_bap", "bars": 2,
                                      "channels": {"kick": 3}})
    assert out["written"]["kick"]["channel"] == 3


@pytest.mark.asyncio
async def test_unknown_genre_is_a_friendly_error(fl):
    out = await _call("write_drums", {"genre": "polka"})
    assert out["ok"] is False and "trap" in out["error"]


@pytest.mark.asyncio
async def test_booth_run_it_back_and_from_bar(fl):
    fl.pos = 37.0
    await _call("booth", {"action": "run_it_back"})
    assert fl.pos == 0 and fl.playing
    await _call("booth", {"action": "from_bar", "bar": 9})
    assert fl.pos == 32.0 and fl.playing
    await _call("booth", {"action": "back_up", "bar": 4})
    assert fl.pos == 16.0


@pytest.mark.asyncio
async def test_booth_record_take_arms_once(fl):
    await _call("booth", {"action": "record_take", "bar": 17})
    assert fl.recording and fl.playing and fl.pos == 64.0
    await _call("booth", {"action": "record_take", "bar": 17})
    assert fl.recording                                   # not toggled off


@pytest.mark.asyncio
@pytest.mark.parametrize("name,args", [
    ("make_beat", {}), ("write_drums", {}), ("write_chords", {"key": "C", "channel": 5}),
    ("write_808", {"key": "C", "channel": 4}),
])
async def test_dry_run_never_touches_fl(monkeypatch, name, args):
    class ReadOnly(FakeFL):
        def call(self, command, params=None, timeout=None):
            assert command in ("channel_list",), "dry run dispatched %s" % command
            return super().call(command, params)

        def apply_notes(self, *a, **k):
            pytest.fail("dry run applied notes")

    monkeypatch.setattr(connection, "_bridge", ReadOnly(list(TEMPLATE)))
    safety.set_dry_run(True)
    try:
        out = await _call(name, args)
        assert "dry_run" in str(out)
    finally:
        safety.set_dry_run(False)


@pytest.mark.asyncio
async def test_beginner_tools_are_listed():
    async with Client(build_server()) as client:
        names = {t.name for t in await client.list_tools()}
    assert {"studio_check", "make_beat", "write_drums", "write_chords", "write_808",
            "booth", "beat_theory", "beat_styles"} <= names


@pytest.mark.asyncio
async def test_setup_boothmate_installs_and_reports(monkeypatch, fl):
    from fl_studio_mcp import setup_cli
    monkeypatch.setattr(setup_cli, "install_controller",
                        lambda: {"ok": True, "action": "installed", "path": "x"})
    monkeypatch.setattr(setup_cli, "seed_note_bridge", lambda: "MCP_Apply.pyscript")
    monkeypatch.setattr(setup_cli, "diagnose",
                        lambda wait=0: {"status": "CONTROLLER_MISSING", "next": "Restart FL"})
    out = await _call("setup_boothmate", {})
    assert out["ok"] and "reopen" in out["say"]
    monkeypatch.setattr(setup_cli, "install_controller",
                        lambda: {"ok": False, "status": "USER_DATA_MISSING"})
    out = await _call("setup_boothmate", {})
    assert out["ok"] is False and "Open FL Studio once" in out["say"]
