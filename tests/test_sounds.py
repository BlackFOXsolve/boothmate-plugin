import os
from pathlib import Path

from fl_studio_mcp.tools import sounds


def test_score_prefers_filename_and_needs_every_word():
    assert sounds.score("/x/Packs/Drums/Kicks/Trap Kick 01.wav", ["trap", "kick"]) == 6
    assert sounds.score("/x/Packs/Trap/Kicks/Hard 01.wav", ["trap", "kick"]) == 2
    assert sounds.score("/x/Packs/Drums/Snares/Snare.wav", ["kick"]) == 0


def test_search_finds_sounds_and_skips_other_files(tmp_path: Path):
    d = tmp_path / "Packs" / "Drums" / "808"
    d.mkdir(parents=True)
    (d / "808 Long Boom.wav").write_bytes(b"x")
    (d / "readme.txt").write_text("808")
    (tmp_path / "Bell Dark.fst").write_bytes(b"x")
    res = sounds.search("808", [tmp_path])
    assert [r["name"] for r in res] == ["808 Long Boom.wav"]
    assert sounds.search("bell", [tmp_path], kinds={".fst"})[0]["type"] == "fst"


def test_browser_segments_only_for_fl_library(tmp_path: Path):
    root = tmp_path / "Patches"
    (root / "Packs" / "Drums" / "Kicks").mkdir(parents=True)
    f = root / "Packs" / "Drums" / "Kicks" / "808 Kick.wav"
    f.write_bytes(b"x")
    assert sounds.browser_segments(str(f), [root]) == ["Packs", "Drums", "Kicks", "808 Kick.wav"]
    other = tmp_path / "Mine" / "a.wav"
    other.parent.mkdir()
    other.write_bytes(b"x")
    assert sounds.browser_segments(str(other), [root, other.parent]) is None


def test_assign_roles_matches_names_once_and_keeps_808_apart():
    names = ["808 Kick", "808 Clap", "808 HiHat", "808 Snare", "808 Astronomic", "FL Keys", "Open Hat"]
    plan = sounds.assign_roles(names, ["Kick", "Snare", "Hi Hat", "Open Hat", "808"])
    assert plan["Kick"] == 0
    assert plan["Snare"] in (1, 3)
    assert plan["Hi Hat"] == 2
    assert plan["Open Hat"] == 6
    assert plan["808"] == 4
    assert len(set(plan.values())) == len(plan)


def test_assign_roles_skips_missing_roles():
    plan = sounds.assign_roles(["Kick", "Piano"], ["Kick", "Snare", "808"])
    assert plan == {"Kick": 0}


def test_every_kit_role_is_known_and_paths_are_relative():
    for kit in sounds.KITS.values():
        for role, (prefs, query) in kit["sounds"].items():
            assert role in sounds.ROLES
            assert prefs and query
            assert all(not p.startswith("/") for p in prefs)


def test_resolve_kit_sound_prefers_listed_file_then_searches(tmp_path: Path):
    root = tmp_path / "Patches"
    k = root / "Packs" / "Drums" / "Kicks"
    k.mkdir(parents=True)
    (k / "Other Kick.wav").write_bytes(b"x")
    got = sounds.resolve_kit_sound((["Packs/Drums/Kicks/808 Kick.wav"], "kick"), [root])
    assert got.endswith("Other Kick.wav")
    (k / "808 Kick.wav").write_bytes(b"x")
    got = sounds.resolve_kit_sound((["Packs/Drums/Kicks/808 Kick.wav"], "kick"), [root])
    assert got.endswith("808 Kick.wav")



from fl_studio_mcp.tools import kit_data


def test_plugin_and_kind_from_preset_paths():
    assert kit_data.plugin_of("Plugin presets/Generators/Sytrus/Bell/Dream bell.fst") == "Sytrus"
    assert kit_data.plugin_of("Plugin database/Effects/Dynamics/Fruity Soft Clipper.fst") == "Fruity Soft Clipper"
    assert kit_data.plugin_of("Channel presets/3x Osc/Bell.fst") == "3x Osc"
    assert kit_data.plugin_of("Plugin presets/Effects/Fruity Reeverb 2/Drum Room.fst") == "Fruity Reeverb 2"
    assert kit_data.kind_of("Packs/Drums/Kicks/808 Kick.wav") == "sample"
    assert kit_data.kind_of("Plugin presets/Effects/Fruity Reeverb 2/Drum Room.fst") == "effect"
    assert kit_data.kind_of("Plugin database/Effects/Dynamics/Fruity Soft Clipper.fst") == "effect"
    assert kit_data.kind_of("Plugin presets/Generators/FL Keys/Dark Piano.fst") == "instrument"


def test_edition_gating():
    sy = "Plugin presets/Generators/Sytrus/Bell/Dream bell.fst"
    osc = "Channel presets/3x Osc/Bell.fst"
    harm = "Plugin presets/Generators/Harmor/Bell/Cursed bells.fst"
    assert kit_data.allowed(osc, "fruity") and not kit_data.allowed(sy, "fruity")
    assert kit_data.allowed(sy, "producer") and not kit_data.allowed(harm, "producer")
    assert not kit_data.allowed(harm, "trial") and kit_data.allowed(harm, "all_plugins")
    sak = "Plugin presets/Generators/Sakura/Default/Smoker Flute.fst"
    assert not kit_data.allowed(sak, "trial") and kit_data.allowed(sak, "signature")
    assert kit_data.allowed(sy, None) and not kit_data.allowed(harm, None)


def test_every_instrument_role_has_a_fruity_option():
    for name, kit in kit_data.KITS.items():
        for role, rels in kit.get("instruments", {}).items():
            assert role in kit_data.ROLE_KIND and kit_data.ROLE_KIND[role] == "inst"
            assert any(kit_data.allowed(r, "fruity") for r in rels), (name, role)
        for role in kit.get("fx", {}):
            assert role in kit["sounds"] or role in kit["instruments"], (name, role)
        for role in list(kit["sounds"]) + list(kit.get("instruments", {})):
            assert role in kit_data.MIX and role in kit_data.INSERTS


def test_assign_roles_melodic_by_name_then_leftover_instruments():
    names = ["Kick", "Snare", "Hi Hat", "Open Hat", "808 Astronomic", "FL Keys", "Choir Aahs", "Sytrus"]
    types = [0, 0, 0, 0, 2, 2, 2, 2]
    plan = sounds.assign_roles(names, ["Kick", "Snare", "Hi Hat", "Open Hat", "808", "Keys", "Melody", "Pad"], types)
    assert plan["808"] == 4 and plan["Keys"] == 5 and plan["Pad"] == 6
    assert plan["Melody"] == 7  # leftover instrument channel
    plan2 = sounds.assign_roles(names[:7], ["Keys", "Melody", "Pad", "808"], types[:7])
    assert "Melody" not in plan2


def test_pick_inserts_keeps_own_insert_and_avoids_others():
    plan = {"Kick": 0, "Snare": 1, "Keys": 5, "Pad": 6}
    routing = {0: 1, 1: 1, 5: 7, 6: 0}   # kick+snare share insert 1, pad on master
    out = sounds.pick_inserts(plan, routing, taken_by_others={9, 2})
    assert out["Keys"] == 7               # its own, unshared insert is kept
    assert out["Kick"] == 1               # preferred insert
    assert out["Snare"] not in (1, 2, 9)  # shared/taken -> a free one
    assert out["Pad"] not in (9,) and len(set(out.values())) == 4


class FakeFL:
    """FL's Browser as observed on FL 2026.1.7: a flat list of visible items;
    selection changes apply only AFTER the call returns; Enter puts a sample
    in the selected channel, an instrument preset in the focused instrument
    window (or a NEW channel when none is open), an effect on the selected
    mixer track."""

    def __init__(self, root, channels):
        self.root = root
        self.ch = [dict(c) for c in channels]
        self.sel, self.pending_sel = 0, None
        self.mix, self.pending_mix = 0, None
        self.focused_editor = None
        self.fx = {}
        self.items, self.pos, self.open = [], 0, set()
        self.routing = {}
        self.history = []
        self.new_when_focused = False
        self._rebuild()

    def _tree(self, rel=""):
        base = self.root / rel if rel else self.root
        return sorted(p.name for p in base.iterdir())

    def _rebuild(self):
        out = []

        def add(rel):
            out.append((rel.split("/")[-1], rel))
            if rel in self.open and (self.root / rel).is_dir():
                for c in self._tree(rel):
                    add(rel + "/" + c)
        for top in self._tree():
            add(top)
        self.items = out

    def __call__(self, op, **p):
        if self.pending_sel is not None:
            self.sel, self.pending_sel = self.pending_sel, None
        if self.pending_mix is not None:
            self.mix, self.pending_mix = self.pending_mix, None
        cur_name, cur_rel = self.items[self.pos]
        if op == "home":
            self.pos = 0
            return {"focused": True}
        if op == "find":
            d, i = p.get("direction", 1), self.pos
            while 0 <= i < len(self.items):
                if self.items[i][0].lower() == p["name"].lower():
                    self.pos = i
                    return {"found": True, "steps": 1}
                i += d
            return {"found": False}
        if op == "toggle":
            self.open ^= {cur_rel}
            self._rebuild()
            self.pos = [r for _, r in self.items].index(cur_rel)
            return {}
        if op in ("next_menu", "prev_menu"):
            self.pos = max(0, min(len(self.items) - 1, self.pos + (1 if op == "next_menu" else -1)))
            return {"caption": self.items[self.pos][0]}
        if op == "select_channel":
            self.pending_sel = p["channel"]
            return {}
        if op == "select_mixer":
            self.pending_mix = p["track"]
            return {}
        if op == "hide_editors":
            self.focused_editor = None
            return {}
        if op == "focus_editor":
            self.focused_editor = p["channel"]
            return {}
        if op == "state":
            return {"selected_channel": self.sel, "mixer_track": self.mix, "channel_count": len(self.ch)}
        if op == "channel_info":
            return {"channel": {"i": p["channel"], "name": self.ch[p["channel"]]["name"]}}
        if op == "channel_types":
            return {"types": [c["type"] for c in self.ch[p.get("start", 0):]], "total": len(self.ch)}
        if op == "load":
            assert cur_name == p["expect"]
            stem = cur_name.rsplit(".", 1)[0]
            if not cur_name.endswith(".fst"):
                if self.ch[self.sel]["type"] == 0:
                    self.ch[self.sel]["sample"] = cur_name
            elif "/Effects/" in "/" + cur_rel:
                self.fx.setdefault(self.mix, []).append(cur_rel.split("/")[2])
            else:
                typ = 0 if stem == "Sampler" else 2
                self.history.append([dict(c) for c in self.ch])
                if self.new_when_focused and self.focused_editor is not None:
                    self.ch.append({"name": stem, "type": typ, "preset": stem})
                else:
                    self.ch[self.sel].update(name=stem, type=typ, preset=stem, sample=None)
            return {"loaded": True, "channels_before": len(self.ch)}
        if op == "undo":
            if self.history:
                self.ch = self.history.pop()
            return {}
        if op == "escape":
            return {}
        raise AssertionError(op)


def _fake_patches(tmp_path):
    root = tmp_path / "Patches"
    for rel in ["Packs/Drums/Kicks/22in Kick.wav", "Packs/Drums/Kicks/808 Kick.wav",
                "Packs/Drums/Hats/808 OH.wav",
                "Plugin database/Generators/Sampler/Sampler.fst",
                "Plugin presets/Generators/FL Keys/Dark Piano.fst",
                "Plugin presets/Effects/Fruity Reeverb 2/Drum Room.fst"]:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    return root


def _setup(monkeypatch, tmp_path, channels):
    root = _fake_patches(tmp_path)
    fl = FakeFL(root, channels)
    monkeypatch.setattr(sounds, "_call", fl)
    monkeypatch.setattr(sounds.time, "sleep", lambda s: None)
    monkeypatch.setattr(sounds, "_routing", lambda: dict(fl.routing))
    monkeypatch.setattr(sounds, "_plugins_on", lambda t: list(fl.fx.get(t, [])))
    monkeypatch.setattr(sounds, "get_bridge", lambda: None)
    monkeypatch.setattr(sounds, "fetch_all_pages", lambda b, cmd, key: {key: [
        {"channel": i, "name": c["name"], "target_mixer_track": fl.routing.get(i, 0)}
        for i, c in enumerate(fl.ch)]})
    monkeypatch.setattr(sounds, "_write", lambda cmd, p: fl.routing.__setitem__(p["channel"], p["track"])
                        if "track" in p else None)
    return root, fl


RACK = [{"name": "Kick", "type": 0}, {"name": "Snare", "type": 0}, {"name": "Open Hat", "type": 0},
        {"name": "808 Astronomic", "type": 2}, {"name": "FL Keys", "type": 2}]


def test_sample_lands_on_the_target_not_the_old_selection(monkeypatch, tmp_path):
    root, fl = _setup(monkeypatch, tmp_path, RACK)
    r = sounds.place(str(root / "Packs/Drums/Hats/808 OH.wav"), 2, [root])
    assert r["ok"] and fl.ch[2].get("sample") == "808 OH.wav"
    assert "sample" not in fl.ch[0]
    assert fl.open == set()


def test_sample_on_instrument_channel_swaps_in_sampler(monkeypatch, tmp_path):
    root, fl = _setup(monkeypatch, tmp_path, RACK)
    r = sounds.place(str(root / "Packs/Drums/Kicks/808 Kick.wav"), 3, [root])
    assert r["ok"] and fl.ch[3]["type"] == 0 and fl.ch[3]["sample"] == "808 Kick.wav"
    assert len(fl.ch) == len(RACK)
    r = sounds.place(str(root / "Packs/Drums/Kicks/808 Kick.wav"), 4, [root], replace_instrument=False)
    assert r["ok"] is False and fl.ch[4]["type"] == 2


def test_instrument_preset_goes_into_target_channel_and_keeps_routing(monkeypatch, tmp_path):
    root, fl = _setup(monkeypatch, tmp_path, RACK)
    fl.routing = {4: 6}
    r = sounds.place(str(root / "Plugin presets/Generators/FL Keys/Dark Piano.fst"), 4, [root])
    assert r["ok"] and r["channel"] == 4 and fl.ch[4]["preset"] == "Dark Piano"
    assert fl.ch[3]["name"] == "808 Astronomic"
    assert fl.routing[4] == 6


def test_load_that_lands_on_wrong_channel_is_undone(monkeypatch, tmp_path):
    root, fl = _setup(monkeypatch, tmp_path, RACK)
    real = fl.__call__

    def stubborn(op, **p):
        if op == "select_channel":
            return {}                     # FL ignores the selection
        return real(op, **p)
    monkeypatch.setattr(sounds, "_call", stubborn)
    monkeypatch.setattr(sounds, "select_channel", lambda ch: True)
    fl.sel = 0
    before = [dict(c) for c in fl.ch]
    r = sounds.place(str(root / "Plugin presets/Generators/FL Keys/Dark Piano.fst"), 4, [root])
    assert r["ok"] is False
    assert [c["name"] for c in fl.ch] == [c["name"] for c in before]


def test_new_channel_when_fl_adds_one_and_undo_when_it_replaces(monkeypatch, tmp_path):
    root, fl = _setup(monkeypatch, tmp_path, RACK)
    fl.new_when_focused = True
    r = sounds.place(str(root / "Plugin presets/Generators/FL Keys/Dark Piano.fst"), None, [root])
    assert r["ok"] and r["new"] and r["channel"] == len(RACK) and fl.ch[4]["name"] == "FL Keys"
    r = sounds.place(str(root / "Packs/Drums/Kicks/22in Kick.wav"), None, [root])
    assert r["ok"] and fl.ch[r["channel"]]["sample"] == "22in Kick.wav" and fl.ch[r["channel"]]["type"] == 0
    root2, fl2 = _setup(monkeypatch, tmp_path / "b", RACK)
    names = [c["name"] for c in fl2.ch]
    r = sounds.place(str(root2 / "Plugin presets/Generators/FL Keys/Dark Piano.fst"), None, [root2])
    assert r["ok"] is False and [c["name"] for c in fl2.ch] == names


def test_effect_goes_on_the_channels_own_mixer_insert(monkeypatch, tmp_path):
    root, fl = _setup(monkeypatch, tmp_path, RACK)
    fl.routing = {1: 2, 0: 0}
    fl.mix = 4
    verb = str(root / "Plugin presets/Effects/Fruity Reeverb 2/Drum Room.fst")
    r = sounds.place(verb, 1, [root])
    assert r["ok"] and r["mixer_track"] == 2 and fl.fx == {2: ["Fruity Reeverb 2"]}
    assert sounds.place(verb, 0, [root])["ok"] is False


def test_load_brings_fl_to_front_when_browser_has_no_focus(monkeypatch, tmp_path):
    root = tmp_path / "Patches"
    (root / "Packs").mkdir(parents=True)
    f = root / "Packs" / "a.wav"
    f.write_bytes(b"x")
    calls = {"front": 0, "home": 0}
    monkeypatch.setattr(sounds, "bring_fl_to_front", lambda: calls.__setitem__("front", calls["front"] + 1) or True)
    monkeypatch.setattr(sounds.time, "sleep", lambda s: None)

    def call(op, **p):
        if op == "home":
            calls["home"] += 1
            return {"focused": calls["front"] > 0}
        return {"found": False}
    monkeypatch.setattr(sounds, "_call", call)
    res = sounds.browse_and_enter(str(f), [root])
    assert calls == {"front": 1, "home": 2}
    assert "Couldn't find the folder" in res["error"]


def test_find_channel_prefers_exact_name_over_number():
    names = ["Kick", "808", "Snare", "FL Keys", "Keys"]
    assert sounds.find_channel(names, "808") == 1
    assert sounds.find_channel(names, "3") == 3
    assert sounds.find_channel(names, "keys") == 4
    assert sounds.find_channel(names, "snar") == 2
    assert sounds.find_channel(names, "new") is None
    assert sounds.find_channel(names, "Bell") == -1


def test_browser_segments_for_fl_audio_folder(monkeypatch, tmp_path):
    from fl_studio_mcp import paths
    il = tmp_path / "Image-Line"
    f = il / "FL Studio" / "Audio" / "BoothMate" / "loop.wav"
    f.parent.mkdir(parents=True)
    f.write_bytes(b"x")
    monkeypatch.setattr(paths, "image_line_dirs", lambda: [il])
    assert sounds.browser_segments(str(f), []) == ["Audio", "BoothMate", "loop.wav"]


def test_fill_spare_drums_uses_unused_samplers_only():
    plan = {"Kick": 0, "Snare": 3, "Hi Hat": 2, "808": 4}
    out = sounds.fill_spare_drums(plan, ["Kick", "Snare", "Hi Hat", "Open Hat", "808", "Keys"],
                                  {"Kick", "Snare", "Hi Hat", "Open Hat", "808"}, [0, 0, 0, 0, 0, 2])
    assert out["Open Hat"] == 1 and "Keys" not in out
