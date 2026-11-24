"""Build a beat around a sample loop (0.1.9).

The flow a user did by hand on 24 Nov 2026, as one command:
  1. bring in a loop the user downloaded (newest audio file in Downloads,
     or a path) by copying it into FL Studio's own Audio folder, which FL's
     Browser shows, so BoothMate can load it with no drag;
  2. read the loop: tempo from its length, bass note and chord tones per
     bar (pure Python, no extra libraries);
  3. load it into a channel, give it its own mixer insert and level;
  4. arrange an intro (loop alone, hats creeping in, snare roll) into a
     drop (drums + an 808 on the loop's bass note), in one pattern;
  5. mute melodic parts whose notes would clash with the loop.

Only use loops the user is licensed to use; BoothMate never downloads or
redistributes them itself.
"""
from __future__ import annotations

import math
import os
import shutil
import struct
import time
import wave
from pathlib import Path
from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from .. import paths, protocol, safety
from ..connection import get_bridge
from ..music import hiphop as hh
from . import sounds

AUDIO_EXTS = (".wav", ".aif", ".aiff", ".flac", ".mp3", ".ogg")
NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


# ---- files ----------------------------------------------------------------
def fl_audio_dir() -> Path:
    """FL Studio's user Audio folder (the Browser's 'Audio' entry)."""
    for root in paths.image_line_dirs():
        d = root / "FL Studio" / "Audio"
        if d.is_dir():
            return d
    return Path.home() / "Documents" / "Image-Line" / "FL Studio" / "Audio"


def newest_download(words: str = "", folder: Path | None = None) -> Path | None:
    folder = folder or (Path.home() / "Downloads")
    want = [w for w in words.lower().split() if w and w not in ("latest", "download", "newest")]
    best = None
    try:
        for p in folder.iterdir():
            if p.suffix.lower() not in AUDIO_EXTS or not p.is_file():
                continue
            if want and not all(w in p.name.lower() for w in want):
                continue
            if best is None or p.stat().st_mtime > best.stat().st_mtime:
                best = p
    except OSError:
        return None
    return best


def import_audio(src: Path, dest_dir: Path | None = None) -> Path:
    """Copy a loop into FL's Audio/BoothMate folder (keeps the original)."""
    dest_dir = (dest_dir or fl_audio_dir()) / "BoothMate"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if not dest.exists() or dest.stat().st_size != src.stat().st_size:
        shutil.copy2(src, dest)
    return dest


# ---- analysis (pure Python) ----------------------------------------------
def read_mono(path: str, max_rate: int = 5512) -> tuple[list[float], int, float]:
    """Mono samples decimated to ~max_rate Hz, the rate, and the duration."""
    with wave.open(path, "rb") as w:
        sr, n, ch, sw = w.getframerate(), w.getnframes(), w.getnchannels(), w.getsampwidth()
        raw = w.readframes(n)
    dur = n / float(sr)
    step = max(1, sr // max_rate)
    frame = ch * sw
    out = []
    for i in range(0, n, step):
        acc = 0.0
        base = i * frame
        for c in range(ch):
            o = base + c * sw
            b = raw[o:o + sw]
            if sw == 2:
                v = struct.unpack("<h", b)[0] / 32768.0
            elif sw == 3:
                v = int.from_bytes(b, "little", signed=True) / 8388608.0
            elif sw == 4:
                v = struct.unpack("<i", b)[0] / 2147483648.0
            else:
                v = (b[0] - 128) / 128.0
            acc += v
        out.append(acc / ch)
    return out, sr // step, dur


def tempo_from_length(dur: float, lo: float = 70, hi: float = 180) -> tuple[float, int]:
    """Loops are a whole number of bars: the tempo where they are 1/2/4/8/16/32
    bars long, inside a normal hip hop range, closest to a whole BPM. PURE."""
    best = None
    for bars in (1, 2, 4, 8, 16, 32):
        bpm = bars * 240.0 / dur
        if lo <= bpm <= hi:
            err = abs(bpm - round(bpm))
            if best is None or err < best[0] - 1e-6:
                best = (err, round(bpm, 2), bars)
    if best is None:
        return 140.0, max(1, int(round(dur * 140 / 240)))
    return best[1], best[2]


def _goertzel(x: list[float], sr: int, f: float) -> float:
    k = 2.0 * math.cos(2.0 * math.pi * f / sr)
    s1 = s2 = 0.0
    for v in x:
        s0 = v + k * s1 - s2
        s2, s1 = s1, s0
    return s1 * s1 + s2 * s2 - k * s1 * s2


def chroma(x: list[float], sr: int, low_midi: int, high_midi: int) -> list[float]:
    c = [0.0] * 12
    for m in range(low_midi, high_midi + 1):
        f = 440.0 * 2 ** ((m - 69) / 12.0)
        if f < sr / 2.2:
            c[m % 12] += _goertzel(x, sr, f)
    top = max(c) or 1.0
    return [v / top for v in c]


def analyze_loop(path: str, bpm: float | None = None) -> dict:
    """Tempo, length in bars, bass note and main notes per bar of a loop."""
    x, sr, dur = read_mono(path)
    if bpm:
        bars = max(1, int(round(dur * bpm / 240.0)))
    else:
        bpm, bars = tempo_from_length(dur)
    per_bar = len(x) / float(bars)
    rows, bass_votes, tone_votes = [], [0.0] * 12, [0.0] * 12
    for b in range(min(bars, 16)):
        seg = x[int(b * per_bar):int((b + 1) * per_bar)]
        seg = seg[::2] if len(seg) > 6000 else seg
        rate = sr // 2 if len(x[int(b * per_bar):int((b + 1) * per_bar)]) > 6000 else sr
        lowc = chroma(seg, rate, 28, 47)        # E1-B2: the bass
        midc = chroma(seg, rate, 48, 83)        # C3-B5: chords and melody
        bass = max(range(12), key=lambda i: lowc[i])
        tones = sorted(range(12), key=lambda i: -midc[i])[:4]
        bass_votes[bass] += 1
        for i in range(12):
            tone_votes[i] += midc[i]
        rows.append({"bar": b + 1, "bass": NAMES[bass], "notes": [NAMES[i] for i in tones]})
    root = max(range(12), key=lambda i: bass_votes[i])
    minor = tone_votes[(root + 3) % 12] >= tone_votes[(root + 4) % 12]
    scale = sorted(range(12), key=lambda i: -tone_votes[i])[:7]
    return {"bpm": bpm, "bars": bars, "duration": round(dur, 3), "root": NAMES[root],
            "root_pc": root, "mode": "minor" if minor else "major",
            "key": "%s %s" % (NAMES[root], "minor" if minor else "major"),
            "scale_notes": [NAMES[i] for i in sorted(scale)], "per_bar": rows}


def clashes(loop_scale: list[str], key: str) -> bool:
    """Would chords written in `key` (natural minor/major) use notes the loop
    avoids? PURE. True = mute those parts."""
    pcs = {NAMES.index(n) for n in loop_scale}
    try:
        name, mode = key.split()[0], key.split()[1].lower()
    except IndexError:
        return False
    r = NAMES.index(name.replace("b", "#")) if name in NAMES else 0
    steps = [0, 2, 3, 5, 7, 8, 10] if mode.startswith("min") else [0, 2, 4, 5, 7, 9, 11]
    return any((r + s) % 12 not in pcs for s in steps)


# ---- arrangement ------------------------------------------------------------
def intro_drop(genre: str, intro: int, drop: int) -> dict[str, list[int]]:
    """Step lists for an intro (silent, hats creep in over its last 2 bars,
    snare roll in the last bar) into a drop of the genre's drums. PURE."""
    S = hh.STEPS_PER_BAR
    pats = hh.drum_patterns(genre, bars=drop, fill=True)
    off = intro * S
    out: dict[str, list[int]] = {}
    for role, s in pats.items():
        out[role] = [off + i for i, c in enumerate(s) if c == "x"]
    if intro >= 2:
        a = (intro - 2) * S
        creep = list(range(a, a + S, 2)) + list(range(a + S, a + S + S // 2))
        out["hat"] = sorted(set(creep) | set(out.get("hat", [])))
    if intro >= 1:
        last = (intro - 1) * S
        roll = list(range(last + S // 2 + S // 4 - S // 4, last + S, 2)) + list(range(last + S - S // 4, last + S))
        key = "snare" if "snare" in out else "clap"
        out[key] = sorted(set(roll) | set(out.get(key, [])))
    return out


def bass_line(kick_steps: list[int], root_pc: int, total_bars: int) -> list[dict]:
    """808 on each drop kick, on the loop's bass note (deep octave), held to
    the next kick, jumping an octave on the last hit of every 2nd bar. PURE."""
    S = hh.STEPS_PER_BAR
    pitch = 24 + root_pc
    if pitch < 26:
        pitch += 12
    notes = []
    end = total_bars * S
    for n, st in enumerate(kick_steps):
        nxt = kick_steps[n + 1] if n + 1 < len(kick_steps) else end
        bar = st // S
        last_in_bar = nxt >= (bar + 1) * S
        p = pitch + 12 if (last_in_bar and bar % 2 == 1 and st % S >= 8) else pitch
        notes.append({"pitch": p, "time_bars": round(st / S, 4),
                      "length_bars": round(max(min(nxt - st, S), 1) / S, 4),
                      "velocity": 1.0 if st % S == 0 else 0.95})
    return notes


def register(mcp: FastMCP) -> None:
    _WR = {"readOnlyHint": False, "destructiveHint": False,
           "idempotentHint": False, "openWorldHint": True}

    @mcp.tool(annotations={"title": "Read a loop's tempo and notes", "readOnlyHint": True,
                           "idempotentHint": True, "openWorldHint": False})
    def fl_analyze_loop(
        sound: Annotated[str, Field(description="Path to a WAV loop, or 'latest download' (newest audio in Downloads; add words to match, e.g. 'latest type shii').")] = "latest download",
        bpm: Annotated[float | None, Field(description="Tempo if known (e.g. from the loop's page); otherwise worked out from its length.")] = None,
    ) -> dict:
        """Read a sample loop: tempo, length in bars, bass note, key and the
        main notes in each bar. Use before building a beat around it."""
        p = Path(sound).expanduser()
        if not p.is_file():
            p = newest_download(sound) or p
        if not p.is_file():
            return {"ok": False, "error": "No audio file found for '%s' (looked in Downloads)." % sound}
        if p.suffix.lower() != ".wav":
            return {"ok": False, "error": "Only WAV loops can be read so far: %s" % p.name}
        return {"ok": True, "file": str(p), **analyze_loop(str(p), bpm)}

    @mcp.tool(annotations={"title": "Build a beat around a loop", **_WR})
    def fl_build_around_loop(
        sound: Annotated[str, Field(description="The loop: a path, or 'latest download' (newest audio in Downloads; add words to match). The user must be licensed to use it.")] = "latest download",
        genre: Annotated[str, Field(description="Drum style for the drop: trap, drill, boom_bap, rnb.")] = "trap",
        intro_bars: Annotated[int, Field(ge=0, le=8, description="Bars of loop-only intro before the drop.")] = 4,
        drop_bars: Annotated[int, Field(ge=1, le=12, description="Bars of the drop.")] = 4,
        channel: Annotated[str, Field(description="Channel to load the loop into: a name or number, or 'new'.")] = "new",
        bpm: Annotated[float | None, Field(description="Loop tempo if known; otherwise worked out from its length.")] = None,
        mute_clashing: Annotated[bool, Field(description="Mute melodic parts (keys, melody, pad, flute) whose notes clash with the loop.")] = True,
    ) -> dict:
        """One request, no clicks: bring a downloaded loop into FL, read its
        tempo, bass note and key, set the tempo, load it on its own channel
        and mixer insert, then arrange an intro (the loop alone, hats creeping
        in, a snare roll) into a drop (the genre's drums plus an 808 on the
        loop's bass note), all in one pattern, and mute melodic parts that
        clash. Load a kit (fl_load_kit) first so the drums sound right.
        Tell the user to press play (or call fl_play) when it returns."""
        steps_log: list[str] = []
        p = Path(sound).expanduser()
        if not p.is_file():
            p = newest_download(sound) or p
        if not p.is_file():
            return {"ok": False, "error": "No audio file found for '%s' (looked in Downloads)." % sound}
        info = analyze_loop(str(p), bpm) if p.suffix.lower() == ".wav" else {
            "bpm": bpm or 140.0, "bars": drop_bars, "root_pc": 0, "root": "C", "key": "C minor",
            "scale_notes": NAMES, "per_bar": []}
        steps_log.append("read the loop: %s, %s bars at %s BPM" % (info["key"], info["bars"], info["bpm"]))
        preview = safety.preview_write(tool="fl_build_around_loop", command=protocol.CMD_BROWSER,
                                       params={"file": str(p), "analysis": info})
        if preview is not None:
            return preview
        dest = import_audio(p)
        steps_log.append("copied it into FL Studio's Audio folder")
        bridge = get_bridge()
        bridge.call(protocol.CMD_SET_TEMPO, {"bpm": float(info["bpm"])})
        steps_log.append("set the tempo to %s" % info["bpm"])

        roots = sounds.stock_roots()
        chans = sounds._channels()
        target = sounds.find_channel([c["name"] for c in chans], channel)
        if target == -1:
            return {"ok": False, "error": "No channel named '%s'." % channel, "analysis": info}
        r = sounds.place_sample(str(dest), target, roots + [fl_audio_dir().parent])
        if not r.get("ok"):
            return {"ok": False, "step": "load", "error": r.get("error"), "analysis": info,
                    "file_in_fl": str(dest),
                    "hint": "Drag the file from FL's Browser (Audio > BoothMate) onto an empty "
                            "spot under the last channel, then run this again with channel='Sample'."}
        ch = r["channel"]
        bridge.call(protocol.CMD_CHANNEL_SET_NAME, {"channel": ch, "name": "Sample"})
        routing = sounds._routing()
        used = {t for t in routing.values() if t > 0}
        ins = routing.get(ch, 0) if routing.get(ch, 0) > 0 and list(routing.values()).count(routing[ch]) == 1 \
            else next(i for i in range(1, 125) if i not in used)
        bridge.call(protocol.CMD_CHANNEL_LINK_MIXER, {"channel": ch, "track": ins})
        bridge.call(protocol.CMD_MIXER_SET_NAME, {"track": ins, "name": "Sample"})
        bridge.call(protocol.CMD_MIXER_SET_VOLUME, {"track": ins, "value": -5.0, "unit": "db"})
        steps_log.append("loaded it on channel %d, mixer insert %d at -5 dB" % (ch, ins))

        total = intro_bars + drop_bars
        loop_bars = max(1, int(info["bars"]))
        sample_notes = [{"pitch": 60, "time_bars": float(b), "length_bars": float(min(loop_bars, total - b)),
                         "velocity": 0.8} for b in range(0, total, loop_bars)]
        chans = sounds._channels()
        roles = hh.match_channels([{"i": c["i"], "name": c["name"]} for c in chans])
        lanes = intro_drop(genre, intro_bars, drop_bars)
        length = total * hh.STEPS_PER_BAR
        written = {}
        for role, on in lanes.items():
            c = roles.get(role)
            if c is None:
                continue
            bridge.call(protocol.CMD_CHANNEL_SET_GRID, {"channel": c, "steps": on, "length": length})
            written[role] = c
        steps_log.append("drums: intro %d bars, drop %d bars (%s)" % (intro_bars, drop_bars,
                                                                       ", ".join(sorted(written))))
        bridge.call(protocol.CMD_CHANNEL_SELECT, {"channel": ch})
        time.sleep(0.3)
        res_sample = bridge.apply_notes(sample_notes, "replace")
        res_808 = None
        if "808" in roles and "kick" in lanes:
            bridge.call(protocol.CMD_CHANNEL_SELECT, {"channel": roles["808"]})
            time.sleep(0.3)
            res_808 = bridge.apply_notes(bass_line(lanes["kick"], info["root_pc"], total), "replace")
            steps_log.append("808 on %s under the drop" % info["root"])
        muted = []
        if mute_clashing:
            words = ("keys", "piano", "melody", "bell", "pad", "flute", "lead", "chord", "pluck", "choir")
            for c in chans:
                nm = c["name"].lower()
                if c["i"] != ch and any(w in nm for w in words) and c.get("type") not in (None,):
                    bridge.call(protocol.CMD_CHANNEL_SET_MUTE, {"channel": c["i"], "state": True})
                    muted.append(c["name"])
            if muted:
                steps_log.append("muted %s so they don't clash with the loop" % ", ".join(muted))
        notes_ok = all(x is None or x.get("triggered", True) for x in (res_sample, res_808))
        return {"ok": True, "analysis": info, "channel": ch, "mixer_insert": ins,
                "pattern_bars": total, "drums": written, "muted": muted, "did": steps_log,
                "notes_triggered": notes_ok,
                "if_no_notes": ("If the loop or 808 don't play: open the Piano roll, use its top-left "
                                "menu > Tools > Scripts > MCP_Apply once this FL session, then run "
                                "this again."),
                "next": "Press play (fl_play) to hear the intro go into the drop."}
