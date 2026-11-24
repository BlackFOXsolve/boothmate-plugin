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


def test_load_into_channel_walks_opens_and_closes(monkeypatch, tmp_path: Path):
    root = tmp_path / "Patches"
    kicks = root / "Packs" / "Drums" / "Kicks"
    kicks.mkdir(parents=True)
    (kicks / "22in Kick.wav").write_bytes(b"x")
    (kicks / "707 Kick.wav").write_bytes(b"x")
    # Fake Browser: a flat visible list with expandable folders.
    tree = {"Packs": ["Drums"], "Drums": ["Kicks"], "Kicks": ["22in Kick.wav", "707 Kick.wav"]}
    state = {"items": ["Current project", "Packs", "Plugin presets"], "pos": 0, "open": set(), "calls": []}

    def rebuild():
        out = []
        def add(name):
            out.append(name)
            if name in state["open"]:
                for c in tree.get(name, []):
                    add(c)
        for top in ["Current project", "Packs", "Plugin presets"]:
            add(top)
        state["items"] = out

    def call(op, **p):
        state["calls"].append(op)
        items = state["items"]
        cur = items[state["pos"]]
        if op == "home":
            state["pos"] = 0
            return {"focused": True}
        if op == "find":
            d = p.get("direction", 1)
            i = state["pos"]
            while 0 <= i < len(items):
                if items[i].lower() == p["name"].lower():
                    state["pos"] = i
                    return {"found": True, "steps": 1}
                i += d
            return {"found": False}
        if op == "toggle":
            state["open"] ^= {cur}
            rebuild()
            state["pos"] = state["items"].index(cur)
            return {}
        if op == "next_menu":
            state["pos"] = min(state["pos"] + 1, len(state["items"]) - 1)
            return {"caption": state["items"][state["pos"]]}
        if op == "prev_menu":
            state["pos"] = max(state["pos"] - 1, 0)
            return {"caption": state["items"][state["pos"]]}
        if op == "load":
            assert cur == p["expect"]
            return {"loaded": True, "channels_before": 7, "channels_after": 7,
                    "channel": {"i": p["channel"], "name": cur}}
        raise AssertionError(op)

    monkeypatch.setattr(sounds, "_call", call)
    # Drums starts already open: the loader must notice and not close it.
    state["open"] = {"Drums"}
    rebuild()
    res = sounds.load_into_channel(str(kicks / "707 Kick.wav"), 3, [root])
    assert res["ok"] is True and res["sound"] == "707 Kick.wav"
    assert state["open"] == {"Drums"}


def test_load_brings_fl_to_front_when_browser_has_no_focus(monkeypatch, tmp_path: Path):
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
    res = sounds.load_into_channel(str(f), 0, [root])
    assert calls == {"front": 1, "home": 2}
    assert "Couldn't find the folder" in res["error"]


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
    assert kit_data.allowed(harm, "trial") and kit_data.allowed(harm, "all_plugins")
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


def _fake_patches(tmp_path):
    root = tmp_path / "Patches"
    for rel in ["Packs/Drums/Kicks/808 Kick.wav", "Plugin database/Generators/Sampler/Sampler.fst",
                "Plugin presets/Generators/FL Keys/Dark Piano.fst",
                "Plugin presets/Effects/Fruity Reeverb 2/Drum Room.fst"]:
        f = root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(b"x")
    return root


def test_place_sample_on_instrument_swaps_in_sampler_first(monkeypatch, tmp_path):
    root = _fake_patches(tmp_path)
    types = {3: 2}
    loads = []

    def fake_load(path, ch, roots):
        loads.append(os.path.basename(path))
        if path.endswith("Sampler.fst"):
            types[ch] = 0
        return {"ok": True, "channel": {"i": ch, "name": "x"}}
    monkeypatch.setattr(sounds, "load_into_channel", fake_load)
    monkeypatch.setattr(sounds, "_type_of", lambda ch: types.get(ch, 0))
    r = sounds.place(str(root / "Packs/Drums/Kicks/808 Kick.wav"), 3, [root])
    assert r["ok"] and loads == ["Sampler.fst", "808 Kick.wav"]
    r = sounds.place(str(root / "Packs/Drums/Kicks/808 Kick.wav"), 5, [root])
    assert loads[-1] == "808 Kick.wav"
    types[7] = 2
    r = sounds.place(str(root / "Packs/Drums/Kicks/808 Kick.wav"), 7, [root], replace_instrument=False)
    assert r["ok"] is False


def test_place_instrument_checks_fl_renamed_channel(monkeypatch, tmp_path):
    root = _fake_patches(tmp_path)
    monkeypatch.setattr(sounds, "load_into_channel",
                        lambda p, ch, roots: {"ok": True, "channel": {"i": ch, "name": "Dark Piano"}})
    assert sounds.place(str(root / "Plugin presets/Generators/FL Keys/Dark Piano.fst"), 5, [root])["ok"]
    monkeypatch.setattr(sounds, "load_into_channel",
                        lambda p, ch, roots: {"ok": True, "channel": {"i": ch, "name": "FL Keys"}})
    r = sounds.place(str(root / "Plugin presets/Generators/FL Keys/Dark Piano.fst"), 5, [root])
    assert r["ok"] is False and "didn't load" in r["error"]


def test_place_effect_needs_insert_and_checks_slot_added(monkeypatch, tmp_path):
    root = _fake_patches(tmp_path)
    fx = {4: ["Fruity Reeverb 2"]}
    monkeypatch.setattr(sounds, "_routing", lambda: {3: 4, 2: 0})
    monkeypatch.setattr(sounds, "_plugins_on", lambda t: list(fx.get(t, [])))

    def fake_load(path, ch, roots):
        fx[4].append("Fruity Reeverb 2")
        return {"ok": True}
    monkeypatch.setattr(sounds, "load_into_channel", fake_load)
    verb = str(root / "Plugin presets/Effects/Fruity Reeverb 2/Drum Room.fst")
    r = sounds.place(verb, 3, [root])
    assert r["ok"] and r["mixer_track"] == 4 and len(r["effects"]) == 2
    assert sounds.place(verb, 2, [root])["ok"] is False   # channel on master
    monkeypatch.setattr(sounds, "load_into_channel", lambda p, ch, roots: {"ok": True})
    assert sounds.place(verb, 3, [root])["ok"] is False   # nothing added
