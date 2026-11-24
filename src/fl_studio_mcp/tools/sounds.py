"""Sound loading (0.1.6): find FL Studio's stock sounds and load them into
channels with no clicks.

FL's scripting API can't create a channel or load a plugin (see loader.py).
What it can do is drive FL's Browser the way hardware like the Akai Fire
does. BoothMate walks the Browser to the sound, selects the target channel
and presses Enter, which loads the sample into that channel (verified live
on FL 2026.1.7). Opening a file through the OS does NOT work: FL treats it
as a new project, so that route was removed.

Starter kits (fl_load_kit) fill a project's drum and 808 channels with a
matched set of stock sounds for a style, then rename them so BoothMate's
beat tools find them.
"""
from __future__ import annotations

import glob
import os
import subprocess
import time
import sys
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from .. import editions, paths, protocol, safety
from . import kit_data
from ..connection import fetch_all_pages, get_bridge

SOUND_EXTS = {".wav", ".flac", ".mp3", ".ogg", ".aif", ".aiff", ".fst", ".ds", ".flp"}
_MAX_SCAN = 60000


def stock_roots() -> list[Path]:
    """Folders that hold FL Studio's own sounds and presets, plus the user's."""
    roots: list[Path] = []
    if sys.platform == "darwin":
        for app in sorted(glob.glob("/Applications/FL Studio*.app")):
            roots.append(Path(app) / "Contents" / "Resources" / "FL" / "Data" / "Patches")
    elif sys.platform == "win32":
        bases = {os.environ.get("ProgramFiles", r"C:\Program Files"),
                 os.environ.get("ProgramW6432", r"C:\Program Files"),
                 os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")}
        for base in bases:
            for fl in sorted(glob.glob(os.path.join(base, "Image-Line", "FL Studio*"))):
                roots.append(Path(fl) / "Data" / "Patches")
    for il in paths.image_line_dirs():
        roots.append(il / "Data" / "FL Studio")
    seen, out = set(), []
    for r in roots:
        key = str(r)
        if key not in seen and r.is_dir():
            seen.add(key)
            out.append(r)
    return out


def score(path: str, words: list[str]) -> int:
    """How well a file path matches the search words (0 = no match). PURE."""
    low = path.lower().replace("_", " ").replace("-", " ")
    name = os.path.basename(low)
    total = 0
    for w in words:
        if w in name:
            total += 3
        elif w in low:
            total += 1
        else:
            return 0
    return total


def search(query: str, roots: list[Path], limit: int = 15, kinds: set[str] | None = None) -> list[dict]:
    words = [w for w in query.lower().replace("_", " ").replace("-", " ").split() if w]
    exts = kinds or SOUND_EXTS
    hits, scanned = [], 0
    for root in roots:
        for dirpath, _dirs, files in os.walk(root):
            for f in files:
                scanned += 1
                if scanned > _MAX_SCAN:
                    break
                ext = os.path.splitext(f)[1].lower()
                if ext not in exts:
                    continue
                full = os.path.join(dirpath, f)
                s = score(full, words) if words else 1
                if s:
                    hits.append((s, len(full), full, ext))
    hits.sort(key=lambda h: (-h[0], h[1]))
    return [{"path": h[2], "name": os.path.basename(h[2]), "type": h[3].lstrip("."),
             "folder": os.path.relpath(os.path.dirname(h[2]), str(_root_of(h[2], roots)))}
            for h in hits[:limit]]


def _root_of(path: str, roots: list[Path]) -> Path:
    for r in roots:
        if path.startswith(str(r)):
            return r
    return Path(os.path.dirname(path))


def browser_segments(path: str, roots: list[Path]) -> list[str] | None:
    """Browser path for a stock sound: the folders under FL's Patches folder
    match the Browser's top-level folders (Packs, Channel presets, ...). PURE."""
    full = os.path.normpath(path)
    for r in roots:
        if Path(r).name != "Patches":
            continue
        root = os.path.normpath(str(r))
        if full.startswith(root + os.sep):
            return full[len(root) + 1:].split(os.sep)
    return None


def child_names(folder: str) -> set[str]:
    try:
        return {n.lower() for n in os.listdir(folder) if not n.startswith(".")}
    except OSError:
        return set()


# Channel types from FL's channels.getChannelType (CT_Sampler = 0).
CT_SAMPLER = 0
CT_AUDIOCLIP = 4

# Roles a kit fills, in assignment order. `words` match channel names;
# `avoid` stops e.g. "808 Kick" counting as the 808 bass.
ROLES: dict[str, dict] = {
    "Kick":     {"words": ["kick", "bd"], "avoid": []},
    "Snare":    {"words": ["snare", "clap", "sd"], "avoid": []},
    "Open Hat": {"words": ["open hat", "openhat", "oh", "open"], "avoid": []},
    "Hi Hat":   {"words": ["hat", "hihat", "hh", "ch"], "avoid": []},
    "808":      {"words": ["808", "bass", "sub"], "avoid": ["kick", "snare", "clap", "hat", "tom", "cowbell", "conga", "clav", "crash"]},
    "Perc":     {"words": ["perc", "rim", "shaker", "cowbell", "tom"], "avoid": []},
    "Keys":     {"words": ["keys", "piano", "chord", "rhodes", "epiano", "organ"], "avoid": []},
    "Melody":   {"words": ["melody", "bell", "lead", "pluck", "arp", "flute"], "avoid": []},
    "Pad":      {"words": ["pad", "choir", "strings", "aahs", "atmos", "string"], "avoid": []},
}
KITS = kit_data.KITS


def _patches(roots: list[Path]) -> list[Path]:
    return [r for r in roots if Path(r).name == "Patches"]


def _existing(rels: list[str], roots: list[Path], edition: str | None = None) -> str | None:
    for root in _patches(roots):
        for rel in rels:
            if edition is not None and not kit_data.allowed(rel, edition):
                continue
            full = os.path.join(str(root), *rel.split("/"))
            if os.path.isfile(full):
                return full
    return None


def resolve_kit_sound(role_spec, roots: list[Path]) -> str | None:
    """First preferred file that exists on this computer, else best search hit."""
    prefs, query = role_spec
    hit = _existing(prefs, roots)
    if hit:
        return hit
    hits = search(query, _patches(roots), 1, {".wav", ".ogg", ".flac", ".mp3", ".aif", ".aiff"})
    return hits[0]["path"] if hits else None


def assign_roles(names: list[str], roles: list[str], types: list | None = None) -> dict[str, int]:
    """Match kit roles to channels by name; each channel used once. Instrument
    roles nobody's name matched go to leftover instrument channels. PURE."""
    used: set[int] = set()
    out: dict[str, int] = {}
    order = [r for r in ROLES if r in roles]
    for role in order:
        spec = ROLES[role]
        best = None
        for i, raw in enumerate(names):
            if i in used:
                continue
            n = " " + raw.lower().replace("-", " ").replace("_", " ") + " "
            if any(a in n for a in spec["avoid"]):
                continue
            if role == "Hi Hat" and ("open" in n or " oh " in n):
                continue
            if role == "Snare" and "kick" in n:
                continue
            hit = None
            for rank, w in enumerate(spec["words"]):
                if (" %s " % w) in n or (len(w) > 3 and w in n):
                    hit = rank
                    break
            if hit is not None and (best is None or hit < best[0]):
                best = (hit, i)
        if best is not None:
            out[role] = best[1]
            used.add(best[1])
    if types:
        for role in order:
            if role in out or kit_data.ROLE_KIND.get(role) != "inst":
                continue
            for i, t in enumerate(types):
                if i not in used and t not in (CT_SAMPLER, CT_AUDIOCLIP, None) and i < len(names):
                    out[role] = i
                    used.add(i)
                    break
    return out


def pick_inserts(plan: dict[str, int], routing: dict[int, int], taken_by_others: set[int],
                 max_insert: int = 125) -> dict[str, int]:
    """Mixer insert per role: keep a channel's own insert if no other kit role
    shares it, else the role's preferred insert, else the next free one. PURE."""
    out: dict[str, int] = {}
    used: set[int] = set(taken_by_others)
    counts: dict[int, int] = {}
    for ch in plan.values():
        t = routing.get(ch, 0)
        counts[t] = counts.get(t, 0) + 1
    for role in [r for r in kit_data.INSERTS if r in plan]:
        cur = routing.get(plan[role], 0)
        if cur > 0 and counts.get(cur, 0) == 1 and cur not in used:
            out[role] = cur
            used.add(cur)
    for role in [r for r in kit_data.INSERTS if r in plan and r not in out]:
        want = kit_data.INSERTS[role]
        if want in used:
            want = next(i for i in range(1, max_insert) if i not in used)
        out[role] = want
        used.add(want)
    return out


def bring_fl_to_front() -> bool:
    """FL only gives its Browser keyboard focus while FL is the active app
    (verified FL 2026.1.7: focus stays -1 while the user is in Claude)."""
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["osascript", "-e",
                                'tell application id "com.image-line.flstudio" to activate'],
                               capture_output=True, timeout=5)
            return r.returncode == 0
        if sys.platform == "win32":
            r = subprocess.run(["powershell", "-NoProfile", "-Command",
                                "(New-Object -ComObject WScript.Shell).AppActivate('FL Studio')"],
                               capture_output=True, timeout=8)
            return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        pass
    return False


def _call(op: str, **params) -> dict:
    return get_bridge().call(protocol.CMD_BROWSER, {"op": op, **params})


def load_into_channel(path: str, channel: int, roots: list[Path]) -> dict:
    """Walk FL's Browser to `path` and load it into `channel`. Opens only the folders it needs and closes them afterwards."""
    segs = browser_segments(path, roots)
    if not segs:
        return {"ok": False, "error": "BoothMate can only load sounds from FL Studio's own "
                                      "library (the Browser's Packs and preset folders)."}
    trail: list[dict] = []
    opened: list[str] = []
    home = _call("home")
    if not home.get("focused", True):
        bring_fl_to_front()
        time.sleep(0.8)
        home = _call("home")
    if not home.get("focused", True):
        return {"ok": False, "error": "FL Studio's Browser couldn't take focus. Click on FL Studio once and try again."}
    root = os.path.dirname(path)
    for _ in range(len(segs) - 1):
        root = os.path.dirname(root)
    current = root
    for folder in segs[:-1]:
        current = os.path.join(current, folder)
        r = _call("find", name=folder)
        trail.append({"find": folder, "found": r.get("found"), "steps": r.get("steps")})
        if not r.get("found"):
            _collapse(opened)
            return {"ok": False, "error": "Couldn't find the folder '%s' in FL's Browser." % folder,
                    "trail": trail}
        kids = child_names(current)
        _call("toggle", value=-1)
        cap = (_call("next_menu").get("caption") or "").lower()
        if cap in kids:
            opened.append(folder)
        else:
            # It was already open and the toggle closed it: open it again.
            _call("prev_menu")
            _call("toggle", value=-1)
            cap = (_call("next_menu").get("caption") or "").lower()
            if cap not in kids:
                _collapse(opened)
                return {"ok": False, "error": "Couldn't open the folder '%s' in FL's Browser." % folder,
                        "trail": trail}
    name = segs[-1]
    r = _call("find", name=name)
    trail.append({"find": name, "found": r.get("found"), "steps": r.get("steps")})
    if not r.get("found"):
        _collapse(opened)
        return {"ok": False, "error": "Couldn't find '%s' in FL's Browser." % name, "trail": trail}
    res = _call("load", channel=channel, expect=name)
    _collapse(opened)
    out = {"ok": bool(res.get("loaded")) and not res.get("error"), "sound": name,
           "channels_before": res.get("channels_before"),
           "channels_after": res.get("channels_after"), "channel": res.get("channel")}
    if res.get("error"):
        out["error"] = res["error"]
    return out


def _collapse(opened: list[str]) -> None:
    """Close the folders BoothMate opened, deepest first."""
    for folder in reversed(opened):
        try:
            r = _call("find", name=folder, direction=-1)
            if r.get("found"):
                _call("toggle", value=-1)
        except Exception:
            pass


def _channels() -> list[dict]:
    """Channel names and types (type from the Browser driver, paged)."""
    data = fetch_all_pages(get_bridge(), protocol.CMD_CHANNEL_LIST, "channels")
    names = [c.get("name", "") for c in (data.get("channels") or [])]
    types: list[int] = []
    start = 0
    while True:
        t = _call("channel_types", start=start)
        types += list(t.get("types") or [])
        start += 60
        if start >= int(t.get("total") or 0):
            break
    if not names:
        names = [""] * len(types)
    return [{"i": i, "name": names[i] if i < len(names) else "",
             "type": types[i] if i < len(types) else None} for i in range(max(len(names), len(types)))]


def _rel(path: str, roots: list[Path]) -> str | None:
    segs = browser_segments(path, roots)
    return "/".join(segs) if segs else None


def _plugins_on(track: int) -> list[str]:
    try:
        r = get_bridge().call(protocol.CMD_PLUGIN_LIST, {"track": track})
        return [str(x.get("name", "")) for x in (r.get("slots") or [])]
    except Exception:
        return []


def _routing() -> dict[int, int]:
    data = fetch_all_pages(get_bridge(), protocol.CMD_CHANNEL_ROUTING_SUMMARY, "channels")
    return {int(c["channel"]): int(c.get("target_mixer_track") or 0) for c in (data.get("channels") or [])}


def _type_of(ch: int) -> int | None:
    t = _call("channel_types", start=ch)
    types = t.get("types") or []
    return types[0] if types else None


def place(path: str, ch: int, roots: list[Path], replace_instrument: bool = True) -> dict:
    """Put one stock sound, instrument preset or effect on channel `ch` (an
    effect goes on the channel's mixer insert) and check that FL did it."""
    rel = _rel(path, roots) or ""
    kind = kit_data.kind_of(rel)
    name = os.path.basename(path)
    stem = name.rsplit(".", 1)[0].lower()
    if kind == "other":
        return {"ok": False, "error": "BoothMate can't load %s (only sounds, instruments and effects)." % name}
    if kind == "sample":
        if _type_of(ch) not in (CT_SAMPLER, CT_AUDIOCLIP, None):
            if not replace_instrument:
                return {"ok": False, "error": "That channel holds an instrument, not a sampler."}
            sampler = _existing(kit_data.SAMPLER, roots)
            if not sampler:
                return {"ok": False, "error": "Couldn't find FL's Sampler to swap the instrument for."}
            r = load_into_channel(sampler, ch, roots)
            if not r.get("ok") or _type_of(ch) != CT_SAMPLER:
                return {"ok": False, "error": "Couldn't turn the channel into a sampler.", "step": r}
        r = load_into_channel(path, ch, roots)
        r["kind"] = "sample"
        return r
    if kind == "instrument":
        r = load_into_channel(path, ch, roots)
        got = ((r.get("channel") or {}).get("name") or "").strip().lower()
        r["kind"] = "instrument"
        if r.get("ok") and got != stem:
            # FL names the channel after the preset it loaded.
            r.update(ok=False, error="FL didn't load %s onto the channel." % name)
        return r
    # effect: lands on the selected channel's mixer insert
    track = _routing().get(ch, 0)
    if track <= 0:
        return {"ok": False, "error": "Route the channel to a mixer insert before adding effects."}
    before = _plugins_on(track)
    r = load_into_channel(path, ch, roots)
    after = _plugins_on(track)
    r.update(kind="effect", mixer_track=track, effects=after)
    if r.get("ok") and len(after) <= len(before):
        r.update(ok=False, error="FL didn't add %s to mixer insert %d." % (name, track))
    return r


def _write(command, params):
    preview = safety.preview_write(tool=command, command=command, params=params)
    if preview is not None:
        return preview
    return get_bridge().call(command, params)


def register(mcp: FastMCP) -> None:
    _RO = {"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False}
    _WR = {"readOnlyHint": False, "destructiveHint": False,
           "idempotentHint": False, "openWorldHint": True}

    @mcp.tool(annotations={"title": "Find FL Studio stock sounds", **_RO})
    def fl_find_sounds(
        query: Annotated[str, Field(description="Words to match, e.g. '808', 'trap kick', 'open hat', 'bell', 'strings'.")],
        limit: Annotated[int, Field(ge=1, le=50)] = 15,
        presets_only: Annotated[bool, Field(description="Only plugin/channel presets (.fst), not samples.")] = False,
    ) -> dict:
        """Search FL Studio's own sound library (Packs, presets) and the user's
        Image-Line folder for sounds by name. Use before fl_load_sound."""
        roots = stock_roots()
        if not roots:
            return {"ok": False, "error": "Couldn't find FL Studio's sound folders on this computer."}
        res = search(query, roots, limit, {".fst"} if presets_only else None)
        return {"ok": True, "query": query, "roots": [str(r) for r in roots], "results": res}

    @mcp.tool(annotations={"title": "Load a sound, instrument or effect", **_WR})
    def fl_load_sound(
        sound: Annotated[str, Field(description="A path from fl_find_sounds (sample, instrument preset or effect preset), or search words like 'trap clap', 'dark piano', 'bell'.")],
        channel: Annotated[str, Field(description="Channel to load into: its number (0 = first) or a name like 'Kick', 'Keys', '808'. Effects go on this channel's mixer insert.")],
        name: Annotated[str | None, Field(description="Rename the channel afterwards, e.g. 'Kick'.")] = None,
        mixer_track: Annotated[int | None, Field(ge=1, description="Route the channel to this mixer insert.")] = None,
        replace_instrument: Annotated[bool, Field(description="For a sample on an instrument channel: swap the instrument for FL's Sampler first.")] = False,
    ) -> dict:
        """Load FL Studio stock content with no clicks, by driving FL's
        Browser: a sample into a channel, an instrument preset onto a channel
        (FL Keys, 3x Osc, Sytrus, Sakura... replacing what was there), or an
        effect preset onto the channel's mixer insert. Checks that FL did it.
        FL can't add new channels from a script, so the channel must exist."""
        roots = stock_roots()
        if not roots:
            return {"ok": False, "error": "Couldn't find FL Studio's sound folders on this computer."}
        if channel in (None, ""):
            return {"ok": False, "error": "Name a channel to load into. FL Studio can't add new channels "
                                          "from a script; ask the user to add an empty Sampler channel."}
        path = sound if os.path.isfile(sound) else None
        if path is None:
            hits = search(sound, _patches(roots), 1)
            if not hits:
                return {"ok": False, "error": "No FL Studio stock sound matches '%s'." % sound}
            path = hits[0]["path"]
        chans = _channels()
        if str(channel).strip().isdigit():
            target = int(str(channel).strip())
        else:
            want = str(channel).strip().lower()
            pick = ([c["i"] for c in chans if c["name"].lower() == want]
                    or [c["i"] for c in chans if want in c["name"].lower()])
            if not pick:
                return {"ok": False, "error": "No channel named '%s'." % channel,
                        "channels": [c["name"] for c in chans]}
            target = pick[0]
        if target >= len(chans):
            return {"ok": False, "error": "There is no channel %d." % target}
        preview = safety.preview_write(tool="fl_load_sound", command=protocol.CMD_BROWSER,
                                       params={"op": "load", "channel": target, "sound": path})
        if preview is not None:
            return preview
        if mixer_track:
            _write(protocol.CMD_CHANNEL_LINK_MIXER, {"channel": target, "track": mixer_track})
        out = place(path, target, roots, replace_instrument)
        out["path"] = path
        if out.get("ok") and name and out.get("kind") != "effect":
            out["rename"] = _write(protocol.CMD_CHANNEL_SET_NAME, {"channel": target, "name": name})
        return out

    @mcp.tool(annotations={"title": "Load a starter kit", **_WR})
    def fl_load_kit(
        style: Annotated[str, Field(description="Kit style: dark_trap, drill, boom_bap or rnb. Call with 'list' to see them.")],
        keep: Annotated[list[str] | None, Field(description="Roles to leave as they are, e.g. ['808', 'Keys'].")] = None,
        effects: Annotated[bool, Field(description="Add the kit's reverb, delay and clipper to the mixer inserts.")] = True,
        mix: Annotated[bool, Field(description="Route each part to its own named mixer insert and set a starting level and pan.")] = True,
    ) -> dict:
        """Set the project up like a producer would for a style, with no
        clicks: drum and 808 samples (Kick, Snare, Hi Hat, Open Hat, 808,
        Perc), instruments with matching presets (Keys for chords, Melody,
        Pad), each part on its own named mixer insert with a starting level
        and pan, and the kit's effects (reverbs, delay, 808 clipper). Uses
        the channels the project has, matched by name, and leaves out what
        the user's FL edition doesn't include. Call before make_beat."""
        key = style.strip().lower().replace(" ", "_").replace("&", "n").replace("-", "_")
        if key in ("list", "") or key not in KITS:
            return {"ok": key == "list", "kits": {k: v["label"] for k, v in KITS.items()},
                    **({} if key == "list" else {"error": "Unknown kit '%s'." % style})}
        kit = KITS[key]
        roots = stock_roots()
        if not roots:
            return {"ok": False, "error": "Couldn't find FL Studio's sound folders on this computer."}
        edition = editions.get()
        chans = _channels()
        roles = [r for r in list(kit["sounds"]) + list(kit.get("instruments", {}))]
        skip = {k.strip().lower() for k in (keep or [])}
        plan = assign_roles([c["name"] for c in chans], roles, [c["type"] for c in chans])
        preview = safety.preview_write(tool="fl_load_kit", command=protocol.CMD_BROWSER,
                                       params={"op": "load_kit", "style": key, "plan": plan})
        if preview is not None:
            return preview
        filled, skipped, mixed, fx_added = [], [], [], []
        for role in roles:
            if role not in plan:
                skipped.append({"role": role, "why": "no channel for it"})
                continue
            ch = plan[role]
            if role.lower() in skip:
                skipped.append({"role": role, "channel": ch, "why": "kept as asked"})
                continue
            if role in kit["sounds"]:
                path = resolve_kit_sound(kit["sounds"][role], roots)
            else:
                path = _existing(kit["instruments"][role], roots, edition)
            if not path:
                skipped.append({"role": role, "channel": ch, "why": "no matching sound in this FL edition"})
                continue
            r = place(path, ch, roots, replace_instrument=True)
            if not r.get("ok"):
                skipped.append({"role": role, "channel": ch, "why": r.get("error", "load failed")})
                continue
            _write(protocol.CMD_CHANNEL_SET_NAME, {"channel": ch, "name": role})
            filled.append({"role": role, "channel": ch, "was": chans[ch]["name"],
                           "sound": os.path.basename(path).rsplit(".", 1)[0]})
        done = {f["role"]: f["channel"] for f in filled}
        if mix and done:
            routing = _routing()
            others = {t for c, t in routing.items() if c not in done.values() and t > 0}
            inserts = pick_inserts(done, routing, others)
            for role, ch in done.items():
                ins = inserts[role]
                _write(protocol.CMD_CHANNEL_LINK_MIXER, {"channel": ch, "track": ins})
                _write(protocol.CMD_MIXER_SET_NAME, {"track": ins, "name": role})
                db, pan = kit_data.MIX[role]
                safety.safe_write(get_bridge(), tool="mixer_set_volume", scope="mixer_track:%d" % ins,
                                  command=protocol.CMD_MIXER_SET_VOLUME,
                                  params={"track": ins, "value": db, "unit": "db"},
                                  build_restore=lambda b, ins=ins: {"command": protocol.CMD_MIXER_SET_VOLUME,
                                      "params": {"track": ins, "value": b["vol_norm"], "unit": "normalized"}})
                safety.safe_write(get_bridge(), tool="mixer_set_pan", scope="mixer_track:%d" % ins,
                                  command=protocol.CMD_MIXER_SET_PAN, params={"track": ins, "value": pan},
                                  build_restore=lambda b, ins=ins: {"command": protocol.CMD_MIXER_SET_PAN,
                                      "params": {"track": ins, "value": b["pan"]}})
                mixed.append({"role": role, "insert": ins, "db": db, "pan": pan})
        if effects and mix and done:
            for role, presets in kit.get("fx", {}).items():
                if role not in done:
                    continue
                ins = _routing().get(done[role], 0)
                have = [n.lower() for n in _plugins_on(ins)]
                for rel in presets:
                    plug = (kit_data.plugin_of(rel) or "").lower()
                    if plug and plug in have:
                        continue  # already there: don't stack a second copy
                    path = _existing([rel], roots)
                    if not path:
                        continue
                    r = place(path, done[role], roots)
                    if r.get("ok"):
                        fx_added.append({"role": role, "insert": ins, "effect": os.path.basename(path).rsplit(".", 1)[0],
                                         "plugin": kit_data.plugin_of(rel)})
                        have.append(plug)
                    else:
                        skipped.append({"role": role, "effect": os.path.basename(path), "why": r.get("error")})
        return {"ok": bool(filled), "kit": kit["label"], "suggested_tempo": kit["tempo"],
                "edition": edition or "unknown (assumed Producer)",
                "filled": filled, "mixer": mixed, "effects": fx_added, "skipped": skipped}

    @mcp.tool(annotations={"title": "Rename a channel", **_WR})
    def fl_rename_channel(
        channel: Annotated[int, Field(ge=0)],
        name: Annotated[str, Field(min_length=1, max_length=64)],
    ) -> dict:
        """Rename a Channel Rack channel (so BoothMate's roles find it)."""
        return _write(protocol.CMD_CHANNEL_SET_NAME, {"channel": channel, "name": name})

    @mcp.tool(annotations={"title": "Link a channel to a mixer track", **_WR})
    def fl_link_channel_to_mixer(
        channel: Annotated[int, Field(ge=0)],
        track: Annotated[int, Field(ge=0, description="Mixer insert number (0 = Master).")],
    ) -> dict:
        """Route a channel to a mixer insert (same as Ctrl+L in FL)."""
        return _write(protocol.CMD_CHANNEL_LINK_MIXER, {"channel": channel, "track": track})

    @mcp.tool(annotations={"title": "Drive FL's Browser (advanced)", **_WR})
    def fl_browser(
        op: Annotated[str, Field(description="state, show, next, prev, next_menu, prev_menu, tab_right, tab_left, tab_first, toggle, preview, home, find, reset")] = "state",
        shift: bool = False,
        name: Annotated[str | None, Field(description="For op=find: the item caption to move to.")] = None,
    ) -> dict:
        """Low-level: step through FL Studio's Browser. Prefer fl_load_sound
        and fl_load_kit, which do the whole walk and load safely."""
        params: dict = {"op": op, "shift": shift}
        if name:
            params["name"] = name
        return get_bridge().call(protocol.CMD_BROWSER, params)

    @mcp.tool(annotations={"title": "List an FL API module (lab)", **_RO})
    def fl_api_names(
        module: Annotated[str, Field(description="FL module, e.g. 'channels', 'ui', 'mixer', 'plugins', 'general'.")],
        start: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """List the function names FL Studio's scripting API offers in one
        module on this FL version (to find new loading functions)."""
        return get_bridge().call(protocol.CMD_API_PROBE, {"op": "dir", "module": module, "start": start})
