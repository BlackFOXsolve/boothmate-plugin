"""Sound loading (0.1.5, lab): find FL Studio's stock sounds and load them
without the user dragging anything.

FL's scripting API can't create a channel or load a plugin (see loader.py), so
loading goes through the operating system instead: BoothMate asks the OS to
open a sound/preset file with FL Studio (like double-clicking it), then reads
the channel rack to see what FL did, names the new channel and links it to a
mixer track over the normal bridge.

Also exposes an experimental Browser driver (the way hardware like the Akai
Fire browses FL's sounds) so the live test can find out which route works.
"""
from __future__ import annotations

import glob
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from .. import fl_launcher, paths, protocol, safety
from ..connection import get_bridge

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


def open_with_fl(path: str) -> dict:
    """Ask the OS to open a file with FL Studio (same as double-clicking it)."""
    if not os.path.exists(path):
        return {"ok": False, "error": "File not found: %s" % path}
    try:
        if sys.platform == "darwin":
            r = subprocess.run(["open", "-b", fl_launcher.BUNDLE_ID, path],
                               capture_output=True, text=True, timeout=20)
            return {"ok": r.returncode == 0, "error": r.stderr.strip() or None}
        if sys.platform == "win32":
            exe = fl_launcher._windows_exe()
            if not exe:
                return {"ok": False, "error": "FL Studio isn't installed."}
            subprocess.Popen([exe, path])
            return {"ok": True}
    except (OSError, subprocess.SubprocessError) as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "Only macOS and Windows are supported."}


def _channel_count() -> int | None:
    try:
        return int(get_bridge().call(protocol.CMD_GET_PROJECT_STATE, {}).get("channel_count"))
    except Exception:
        return None


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

    @mcp.tool(annotations={"title": "Load a sound into FL Studio (lab)", **_WR})
    def fl_load_sound(
        path: Annotated[str, Field(description="Full path from fl_find_sounds.")],
        channel_name: Annotated[str | None, Field(description="Name for the new channel, e.g. 'Kick', '808', 'Bell'.")] = None,
        mixer_track: Annotated[int | None, Field(ge=1, description="Mixer insert to link the new channel to.")] = None,
        wait_seconds: Annotated[float, Field(ge=1, le=15)] = 6.0,
    ) -> dict:
        """Load a sample or preset into FL Studio with no clicks: opens the
        file with FL (like double-clicking it), detects the new channel, then
        names it and links it to a mixer track. Reports exactly what FL did."""
        before = _channel_count()
        opened = open_with_fl(path)
        if not opened.get("ok"):
            return {"ok": False, "step": "open", **opened}
        after, waited = before, 0.0
        while waited < wait_seconds:
            time.sleep(0.5)
            waited += 0.5
            after = _channel_count()
            if before is not None and after is not None and after > before:
                break
        out = {"opened": path, "channels_before": before, "channels_after": after}
        if before is None or after is None or after <= before:
            out.update(ok=False, result="no_new_channel",
                       hint="FL didn't add a channel. It may have opened the file somewhere else "
                            "(Edison, a new project or a dialog). Look at FL Studio's screen.")
            return out
        ch = after - 1
        out.update(ok=True, result="new_channel", channel=ch)
        if channel_name:
            out["rename"] = _write(protocol.CMD_CHANNEL_SET_NAME, {"channel": ch, "name": channel_name})
        if mixer_track:
            out["link"] = _write(protocol.CMD_CHANNEL_LINK_MIXER, {"channel": ch, "track": mixer_track})
        return out

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

    @mcp.tool(annotations={"title": "Drive FL's Browser (lab)", **_WR})
    def fl_browser(
        op: Annotated[str, Field(description="state, show, next, prev, next_menu, prev_menu, tab_right, tab_left, tab_first, toggle, preview, select, enter")] = "state",
        shift: bool = False,
    ) -> dict:
        """Experimental: move through FL Studio's Browser and try loading the
        highlighted item. Returns the highlighted item and the channel count,
        so a load attempt shows up as a new or changed channel."""
        return get_bridge().call(protocol.CMD_BROWSER, {"op": op, "shift": shift})

    @mcp.tool(annotations={"title": "List an FL API module (lab)", **_RO})
    def fl_api_names(
        module: Annotated[str, Field(description="FL module, e.g. 'channels', 'ui', 'mixer', 'plugins', 'general'.")],
        start: Annotated[int, Field(ge=0)] = 0,
    ) -> dict:
        """List the function names FL Studio's scripting API offers in one
        module on this FL version (to find new loading functions)."""
        return get_bridge().call(protocol.CMD_API_PROBE, {"op": "dir", "module": module, "start": start})
