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

from .. import paths, protocol, safety
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
}

# Starter kits: each role lists stock sounds (relative to FL's Patches folder)
# in order of preference, plus a search to fall back on if a FL version
# doesn't ship that file.
KITS: dict[str, dict] = {
    "dark_trap": {
        "label": "Dark trap (Metro, Southside, 808 Mafia style)",
        "tempo": 140,
        "sounds": {
            "Kick": (["Packs/Drums/Kicks/808 Kick.wav"], "808 kick"),
            "Snare": (["Packs/Drums/Percussion/909 Clap.wav", "Packs/Drums/Snares/808 Snare.wav"], "clap"),
            "Hi Hat": (["Packs/Drums/Hats/808 CH.wav"], "808 ch"),
            "Open Hat": (["Packs/Drums/Hats/808 OH.wav"], "808 oh"),
            "808": (["Misc/Used by demo projects/DEDZII - NIGHT TERROR/FLEX 808 Sub.ogg",
                     "Packs/Legacy/Drums/Dance/Basic 808 Kick.wav"], "808 sub"),
        },
    },
    "drill": {
        "label": "Drill (UK / NY drill)",
        "tempo": 142,
        "sounds": {
            "Kick": (["Packs/Drums/Kicks/909 Kick.wav", "Packs/Drums/Kicks/808 Kick.wav"], "909 kick"),
            "Snare": (["Packs/Drums/Snares/RD Snare.wav", "Packs/Drums/Snares/909 Snare.wav"], "snare"),
            "Hi Hat": (["Packs/Drums/Hats/Ice Hat 1.wav"], "ice hat"),
            "Open Hat": (["Packs/Drums/Hats/808 OH.wav"], "808 oh"),
            "Perc": (["Packs/Drums/Percussion/808 Cowbell.wav"], "cowbell"),
            "808": (["Misc/Used by demo projects/DEDZII - NIGHT TERROR/FLEX 808 Sub.ogg",
                     "Packs/Legacy/Drums/Dance/Basic 808 Kick.wav"], "808 sub"),
        },
    },
    "boom_bap": {
        "label": "Boom bap (90s New York)",
        "tempo": 90,
        "sounds": {
            "Kick": (["Packs/Drums/Kicks/Grv Kick 03.wav", "Packs/Drums/Kicks/FPC 1 Kick.wav"], "grv kick"),
            "Snare": (["Packs/Drums/Snares/Linn Snare.wav", "Packs/Drums/Snares/Scot Snare.wav"], "linn snare"),
            "Hi Hat": (["Packs/Legacy/Drums/HipHop/HIP_Hat.wav", "Packs/Drums/Hats/Jung Hat 1.wav"], "hip hat"),
            "Open Hat": (["Packs/Legacy/Drums/Vintage/VT_OHiHat.wav"], "ohihat"),
            "Perc": (["Packs/Drums/Percussion/Pap Clap.wav"], "pap clap"),
        },
    },
    "rnb": {
        "label": "R&B / soul (smooth, Bryson Tiller style)",
        "tempo": 75,
        "sounds": {
            "Kick": (["Packs/Drums/Kicks/Chrome Kick.wav", "Packs/Drums/Kicks/808 Kick.wav"], "kick"),
            "Snare": (["Packs/Drums/Percussion/Pap Clap.wav", "Packs/Drums/Percussion/SC Clap.wav"], "clap"),
            "Hi Hat": (["Packs/Drums/Hats/Ekit 1 Hat.wav", "Packs/Drums/Hats/808 CH.wav"], "hat"),
            "Open Hat": (["Packs/Drums/Hats/808 OH.wav"], "808 oh"),
            "808": (["Misc/Used by demo projects/DEDZII - NIGHT TERROR/FLEX 808 Sub.ogg",
                     "Packs/Legacy/Drums/Dance/Basic 808 Kick.wav"], "808 sub"),
        },
    },
}


def resolve_kit_sound(role_spec, roots: list[Path]) -> str | None:
    """First preferred file that exists on this computer, else best search hit."""
    prefs, query = role_spec
    for root in roots:
        if Path(root).name != "Patches":
            continue
        for rel in prefs:
            full = os.path.join(str(root), *rel.split("/"))
            if os.path.isfile(full):
                return full
    hits = search(query, [r for r in roots if Path(r).name == "Patches"], 1,
                  {".wav", ".ogg", ".flac", ".mp3", ".aif", ".aiff"})
    return hits[0]["path"] if hits else None


def assign_roles(names: list[str], roles: list[str]) -> dict[str, int]:
    """Match kit roles to channels by name; each channel used once. PURE."""
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

    @mcp.tool(annotations={"title": "Load a sound into a channel", **_WR})
    def fl_load_sound(
        sound: Annotated[str, Field(description="A path from fl_find_sounds, or search words like 'trap clap' or '808 open hat'.")],
        channel: Annotated[str, Field(description="Channel to load into: its number (0 = first) or a name like 'Kick', 'Snare', '808'. FL can't add channels from a script, so it must be an existing one.")],
        name: Annotated[str | None, Field(description="Rename the channel after loading, e.g. 'Kick'.")] = None,
        mixer_track: Annotated[int | None, Field(ge=1, description="Mixer insert to route the channel to.")] = None,
        replace_instrument: Annotated[bool, Field(description="Allow loading a sample over a channel that holds an instrument plugin (it becomes a sampler). Off by default.")] = False,
    ) -> dict:
        """Load one of FL Studio's stock sounds into a Channel Rack channel
        with no clicks. BoothMate walks FL's Browser to the sound, selects
        the channel and loads it (the way an Akai Fire does), then can rename
        it and route it to a mixer track. Samples only go onto sampler
        channels unless replace_instrument is on."""
        roots = stock_roots()
        if not roots:
            return {"ok": False, "error": "Couldn't find FL Studio's sound folders on this computer."}
        path = sound if os.path.isfile(sound) else None
        if path is None:
            hits = search(sound, [r for r in roots if r.name == "Patches"], 1)
            if not hits:
                return {"ok": False, "error": "No FL Studio stock sound matches '%s'." % sound}
            path = hits[0]["path"]
        if channel in (None, ""):
            return {"ok": False, "error": "Name a channel to load into. FL Studio can't add new channels "
                                          "from a script; ask the user to add an empty Sampler channel."}
        target = -1
        chans = _channels()
        if str(channel).strip().isdigit():
            target = int(str(channel).strip())
        else:
            want = str(channel).strip().lower()
            exact = [c["i"] for c in chans if c["name"].lower() == want]
            part = [c["i"] for c in chans if want in c["name"].lower()]
            pick = exact or part
            if not pick:
                return {"ok": False, "error": "No channel named '%s'." % channel,
                        "channels": [c["name"] for c in chans]}
            target = pick[0]
        if target >= len(chans):
            return {"ok": False, "error": "There is no channel %d." % target}
        ctype = chans[target]["type"]
        if ctype not in (CT_SAMPLER, CT_AUDIOCLIP, None) and not replace_instrument:
            return {"ok": False, "error": "Channel '%s' holds an instrument plugin, not a sampler. "
                                          "Pick a sampler channel, or set replace_instrument "
                                          "to swap the instrument for this sample." % chans[target]["name"]}
        preview = safety.preview_write(tool="fl_load_sound", command=protocol.CMD_BROWSER,
                                       params={"op": "load", "channel": target, "sound": path})
        if preview is not None:
            return preview
        out = load_into_channel(path, target, roots)
        out["path"] = path
        if not out.get("ok"):
            return out
        ch = target
        if name:
            out["rename"] = _write(protocol.CMD_CHANNEL_SET_NAME, {"channel": ch, "name": name})
        if mixer_track:
            out["link"] = _write(protocol.CMD_CHANNEL_LINK_MIXER, {"channel": ch, "track": mixer_track})
        return out

    @mcp.tool(annotations={"title": "Load a starter kit", **_WR})
    def fl_load_kit(
        style: Annotated[str, Field(description="Kit style: dark_trap, drill, boom_bap or rnb. Call with 'list' to see them.")],
        rename: Annotated[bool, Field(description="Rename filled channels to their role (Kick, Snare, Hi Hat, Open Hat, 808, Perc) so make_beat finds them.")] = True,
    ) -> dict:
        """Fill the project's drum and 808 channels with a matched set of FL
        Studio stock sounds for a style, with no clicks. Matches kit roles
        to channels by name (Kick, Snare/Clap, Hat, Open Hat, 808, Perc),
        loads each sound into its channel and renames it. Only sampler
        channels are filled; instrument channels are left alone and reported.
        Use before make_beat so the beat plays with sounds that fit."""
        key = style.strip().lower().replace(" ", "_").replace("&", "n").replace("-", "_")
        if key in ("list", "") or key not in KITS:
            return {"ok": key == "list", "kits": {k: v["label"] for k, v in KITS.items()},
                    **({} if key == "list" else {"error": "Unknown kit '%s'." % style})}
        kit = KITS[key]
        roots = stock_roots()
        if not roots:
            return {"ok": False, "error": "Couldn't find FL Studio's sound folders on this computer."}
        chans = _channels()
        plan = assign_roles([c["name"] for c in chans], list(kit["sounds"]))
        preview = safety.preview_write(tool="fl_load_kit", command=protocol.CMD_BROWSER,
                                       params={"op": "load_kit", "style": key, "plan": plan})
        if preview is not None:
            return preview
        filled, skipped = [], []
        for role in kit["sounds"]:
            if role not in plan:
                skipped.append({"role": role, "why": "no channel for it (add or name a channel '%s')" % role})
                continue
            ch = plan[role]
            if chans[ch]["type"] not in (CT_SAMPLER, CT_AUDIOCLIP, None):
                skipped.append({"role": role, "channel": ch, "name": chans[ch]["name"],
                                "why": "instrument plugin, left as is"})
                continue
            path = resolve_kit_sound(kit["sounds"][role], roots)
            if not path:
                skipped.append({"role": role, "why": "sound not found in this FL version"})
                continue
            r = load_into_channel(path, ch, roots)
            if not r.get("ok"):
                skipped.append({"role": role, "channel": ch, "why": r.get("error", "load failed")})
                continue
            if rename:
                _write(protocol.CMD_CHANNEL_SET_NAME, {"channel": ch, "name": role})
            filled.append({"role": role, "channel": ch, "was": chans[ch]["name"],
                           "sound": os.path.basename(path)})
        return {"ok": bool(filled), "kit": kit["label"], "suggested_tempo": kit["tempo"],
                "filled": filled, "skipped": skipped}

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
