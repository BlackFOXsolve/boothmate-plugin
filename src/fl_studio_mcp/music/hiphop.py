"""Beginner beat engine (PURE: no bridge, no writes).

Turns simple requests ("dark trap beat in F# minor", "chill lo-fi chords") into
concrete step-sequencer patterns and piano-roll notes. The tools in
``tools/beginner.py`` write these through the existing safety layer.

Conventions
-----------
* Drum patterns are 16-step strings per bar ('x' = hit, '.' = rest), 1/16 grid.
  A genre may give a 2-bar (32-step) pattern; it is tiled to the requested bars,
  and the last bar can be swapped for a ``fill`` variant.
* Notes use the piano-roll bridge format: pitch (MIDI, 60 = middle C, which FL
  labels C5), time_bars, length_bars, velocity 0..1, porta (slide).
* Time signature is assumed 4/4 (16 steps = 1 bar = 4 beats).
"""
from __future__ import annotations

import re

STEPS_PER_BAR = 16

# --------------------------------------------------------------------------
# Keys and scales
# --------------------------------------------------------------------------
_PC = {"c": 0, "d": 2, "e": 4, "f": 5, "g": 7, "a": 9, "b": 11}
_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
}


def parse_key(key: str | None, default_quality: str = "minor"):
    """'F#m', 'F# minor', 'Bb', 'a min', 'C major' -> (root_pc, 'minor'|'major').

    Hip-hop defaults to minor when no quality is given."""
    if not key:
        return 0, default_quality
    s = key.strip().lower().replace("♯", "#").replace("♭", "b")
    m = re.match(r"^([a-g])\s*([#b]?)\s*(.*)$", s)
    if not m:
        raise ValueError("Couldn't read key %r. Try something like 'F# minor' or 'C'." % key)
    pc = (_PC[m.group(1)] + {"#": 1, "b": -1, "": 0}[m.group(2)]) % 12
    rest = m.group(3).strip()
    if rest in ("", ):
        quality = default_quality
    elif rest in ("m", "min", "minor", "-", "mi"):
        quality = "minor"
    elif rest in ("maj", "major", "M", "ma"):
        quality = "major"
    else:
        raise ValueError("Couldn't read the quality in key %r (use 'minor' or 'major')." % key)
    return pc, quality


def key_name(pc: int, quality: str) -> str:
    return "%s %s" % (_NAMES[pc % 12], quality)


def note_name(pitch: int) -> str:
    """FL-style name: MIDI 60 -> 'C5' (FL labels middle C as C5)."""
    return "%s%d" % (_NAMES[pitch % 12], pitch // 12)


# --------------------------------------------------------------------------
# Moods -> chord progressions
# --------------------------------------------------------------------------
# degrees are 1-based scale degrees; chords are stacked thirds in `scale`.
MOODS = {
    "dark":      {"scale": "harmonic_minor", "degrees": [1, 6, 4, 5], "sevenths": False,
                  "about": "i - VI - iv - V. Classic dark trap tension."},
    "sad":       {"scale": "minor", "degrees": [1, 6, 3, 7], "sevenths": False,
                  "about": "i - VI - III - VII. Emotional, melodic rap."},
    "menacing":  {"scale": "phrygian", "degrees": [1, 2, 1, 6], "sevenths": False,
                  "about": "i - bII - i - VI. Drill-style menace."},
    "hype":      {"scale": "minor", "degrees": [1, 7, 6, 7], "sevenths": False,
                  "about": "i - VII - VI - VII. Driving, energetic."},
    "chill":     {"scale": "dorian", "degrees": [1, 4, 1, 5], "sevenths": True,
                  "about": "i7 - IV7 - i7 - v7. Smooth lo-fi / boom bap."},
    "love":      {"scale": "major", "degrees": [1, 6, 4, 5], "sevenths": True,
                  "about": "Imaj7 - vi7 - IVmaj7 - V7. Warm R&B."},
    "happy":     {"scale": "major", "degrees": [1, 5, 6, 4], "sevenths": False,
                  "about": "I - V - vi - IV. Bright pop-rap."},
}


def _chord_tones(root_pc, scale, degree, sevenths):
    steps = SCALES[scale]
    idx = degree - 1
    count = 4 if sevenths else 3
    tones = []
    for k in range(count):
        j = idx + 2 * k
        octave, pos = divmod(j, 7)
        tones.append(root_pc + steps[pos] + 12 * octave)
    return tones  # semitones above the key root's C-octave reference


def progression(key=None, mood="dark", degrees=None):
    """Chords for a mood in a key. Returns list of {degree, name, tones(pcs offsets)}."""
    mood = (mood or "dark").lower()
    if mood not in MOODS:
        raise ValueError("Unknown mood %r. Try: %s." % (mood, ", ".join(sorted(MOODS))))
    spec = MOODS[mood]
    root_pc, quality = parse_key(key, "major" if spec["scale"] == "major" else "minor")
    scale = spec["scale"]
    # If the user's key quality disagrees with the mood's scale family, follow the key.
    if quality == "major" and scale != "major":
        scale = "major"
    elif quality == "minor" and scale == "major":
        scale = "minor"
    degs = list(degrees) if degrees else list(spec["degrees"])
    chords = []
    for d in degs:
        if not 1 <= int(d) <= 7:
            raise ValueError("Scale degrees must be 1-7, got %r" % d)
        tones = _chord_tones(root_pc, scale, int(d), spec["sevenths"])
        chords.append({"degree": int(d), "tones": tones,
                       "name": _chord_name(tones)})
    return {"key": key_name(root_pc, quality), "root_pc": root_pc, "scale": scale,
            "mood": mood, "about": spec["about"], "chords": chords}


def _chord_name(tones):
    root = tones[0] % 12
    third = (tones[1] - tones[0]) % 12
    fifth = (tones[2] - tones[0]) % 12
    q = {(4, 7): "", (3, 7): "m", (3, 6): "dim", (4, 8): "aug"}.get((third, fifth), "")
    if len(tones) > 3:
        sev = (tones[3] - tones[0]) % 12
        q = {("", 11): "maj7", ("", 10): "7", ("m", 10): "m7", ("m", 11): "m(maj7)",
             ("dim", 10): "m7b5", ("dim", 9): "dim7"}.get((q, sev), q + "7")
    return _NAMES[root] + q


def chord_notes(prog, bars_per_chord=1.0, octave_base=48, velocity=0.7, repeat=1):
    """Block-chord piano-roll notes. octave_base 48 = C3 in MIDI (FL shows C4)."""
    notes, t = [], 0.0
    for _ in range(max(1, int(repeat))):
        for ch in prog["chords"]:
            base = octave_base + (ch["tones"][0] % 12)
            first = ch["tones"][0]
            for tone in ch["tones"]:
                notes.append({"pitch": base + (tone - first), "time_bars": round(t, 4),
                              "length_bars": float(bars_per_chord), "velocity": velocity,
                              "porta": False})
            t += bars_per_chord
    return notes


# --------------------------------------------------------------------------
# Genres -> drums, tempo, 808 behaviour
# --------------------------------------------------------------------------
GENRES = {
    "trap": {
        "bpm": 140, "mood": "dark",
        "drums": {
            "kick":     "x.........x.....x.....x...x.....",
            "snare":    "........x...............x.......",
            "clap":     "........x...............x.......",
            "hat":      "x.x.x.x.x.x.x.x.x.x.x.x.xxx.x.x.",
            "open_hat": "..............x...............x.",
        },
        "fill": {"hat": "xxxxx.x.xxx.xxxx", "snare": "........x.....xx"},
        "slide": False,
        "about": "Half-time snare on beat 3, rolling hats, 808 follows the kick.",
    },
    "drill": {
        "bpm": 142, "mood": "menacing",
        "drums": {
            "kick":     "x.........x.....x.....x...x.x...",
            "snare":    "........x.......x.......x.....x.",
            "clap":     "........x...............x.......",
            "hat":      "x..x..x.x.x..x..x..x..x.x.x..xx.",
            "open_hat": "................................",
        },
        "fill": {"snare": "........x..x.xx."},
        "slide": True,
        "about": "Syncopated snares and triplet-feel hats, sliding 808s.",
    },
    "boom_bap": {
        "bpm": 90, "mood": "chill",
        "drums": {
            "kick":     "x.........x.x...x......x..x.....",
            "snare":    "....x.......x.......x.......x...",
            "clap":     "................................",
            "hat":      "x.x.x.x.x.x.x.x.x.x.x.x.x.x.x.xx",
            "open_hat": "..............x...............x.",
        },
        "fill": {"kick": "x.........x.x.x.", "snare": "....x.......x.xx"},
        "slide": False,
        "about": "Snare on 2 and 4, dusty swing; bass follows the kick.",
    },
    "rnb": {
        "bpm": 72, "mood": "love",
        "drums": {
            "kick":     "x......x..x.....x.....x...x.....",
            "snare":    "........x...............x.......",
            "clap":     "........x...............x.......",
            "hat":      "x.x.x.x.x.x.x.x.x.x.x.x.x.xxx.x.",
            "open_hat": "................................",
        },
        "fill": {"hat": "x.x.x.x.x.xxx.xx"},
        "slide": False,
        "about": "Laid-back half-time groove with smooth 7th chords.",
    },
    "lofi": {
        "bpm": 80, "mood": "chill",
        "drums": {
            "kick":     "x......x..x.....x.....x.......x.",
            "snare":    "....x.......x.......x.......x...",
            "clap":     "................................",
            "hat":      "..x...x...x...x...x...x...x...x.",
            "open_hat": "................................",
        },
        "fill": {"snare": "....x.......x..x"},
        "slide": False,
        "about": "Relaxed, sparse drums under jazzy 7th chords.",
    },
    "jersey_club": {
        "bpm": 140, "mood": "hype",
        "drums": {
            "kick":     "x..x..x.x..x..x.x..x..x.x..x..x.",
            "snare":    "....x.......x.......x.......x...",
            "clap":     "....x.......x.......x.......x...",
            "hat":      "..x...x...x...x...x...x...x...x.",
            "open_hat": "................................",
        },
        "fill": {"kick": "x.x.x.x.x.x.xxxx"},
        "slide": False,
        "about": "Bouncy triplet-feel kick pattern, claps on 2 and 4.",
    },
}

GENRE_ALIASES = {"boombap": "boom_bap", "boom bap": "boom_bap", "r&b": "rnb", "rnb": "rnb",
                 "lo-fi": "lofi", "lo fi": "lofi", "jersey": "jersey_club",
                 "jersey club": "jersey_club", "uk drill": "drill", "ny drill": "drill"}

DRUM_ROLES = ("kick", "snare", "clap", "hat", "open_hat")


def resolve_genre(genre: str | None) -> str:
    g = (genre or "trap").strip().lower()
    g = GENRE_ALIASES.get(g, g.replace(" ", "_").replace("-", "_"))
    if g not in GENRES:
        raise ValueError("Unknown genre %r. Try: %s." % (genre, ", ".join(sorted(GENRES))))
    return g


def drum_patterns(genre, bars=4, fill=True):
    """Role -> step string covering `bars` bars (tiled; last bar gets the fill)."""
    spec = GENRES[resolve_genre(genre)]
    total = bars * STEPS_PER_BAR
    out = {}
    for role in DRUM_ROLES:
        base = spec["drums"].get(role, "")
        if not base or "x" not in base:
            continue
        reps = -(-total // len(base))
        s = (base * reps)[:total]
        f = spec.get("fill", {}).get(role) if fill and bars >= 2 else None
        if f:
            s = s[:total - STEPS_PER_BAR] + f
        out[role] = s
    return out


def eight_oh_eight(prog, genre="trap", bars_per_chord=1.0, repeat=1, velocity=0.85):
    """808 / bass line: one note per kick hit, pitched to the current chord root,
    held until the next kick (max 1 bar). Drill slides the last hit of each bar
    up an octave with portamento."""
    spec = GENRES[resolve_genre(genre)]
    chords = prog["chords"] * max(1, int(repeat))
    bars = int(round(len(chords) * bars_per_chord))
    kick = drum_patterns(genre, bars=max(bars, 1), fill=False)["kick"]
    hits = [i for i, c in enumerate(kick) if c == "x"]
    notes = []
    for n, step in enumerate(hits):
        t = step / STEPS_PER_BAR
        chord = chords[min(int(t // bars_per_chord), len(chords) - 1)]
        root_pc = chord["tones"][0] % 12
        pitch = 24 + root_pc
        if pitch < 33:          # keep the sub between A1 and G#2 (FL: A2-G#3)
            pitch += 12
        nxt = hits[n + 1] if n + 1 < len(hits) else len(kick)
        length = min((nxt - step) / STEPS_PER_BAR, 1.0)
        porta = False
        if spec["slide"]:
            bar_end = (int(t) + 1) * STEPS_PER_BAR
            if nxt >= bar_end and step % STEPS_PER_BAR >= 8:   # last hit in the bar
                pitch += 12
                porta = True
        notes.append({"pitch": pitch, "time_bars": round(t, 4),
                      "length_bars": round(max(length, 0.0625), 4),
                      "velocity": velocity, "porta": porta})
    return notes


# --------------------------------------------------------------------------
# Channel matching (by channel-rack name)
# --------------------------------------------------------------------------
_ROLE_WORDS = {
    "kick": ("kick", "kik", "bd", "bassdrum", "bass drum"),
    "snare": ("snare", "snr", "sd", "rim"),
    "clap": ("clap", "clp"),
    "open_hat": ("open hat", "openhat", "open", "ohh", "oh "),
    "hat": ("hat", "hihat", "hi-hat", "hh", "closed"),
    "808": ("808", "sub", "bass"),
    "chords": ("chord", "keys", "piano", "pad", "rhodes", "epiano", "e-piano", "synth",
               "pluck", "strings", "organ", "guitar", "bell"),
}
_ORDER = ("kick", "snare", "clap", "open_hat", "hat", "808", "chords")
# Exact channel names (what fl_load_kit names its parts) win over fuzzy
# matches, so a kit's "Keys" beats an older "FL Keys" channel.
_EXACT = {"kick": ("kick",), "snare": ("snare",), "clap": ("clap",), "open_hat": ("open hat",),
          "hat": ("hi hat", "hihat", "hat"), "808": ("808",), "chords": ("keys",)}


def match_channels(channels, overrides=None):
    """channels: [{'i'|'index', 'name'}] (controller uses 'i') -> {role: index}. First match wins;
    a channel is used for one role only. overrides force a role -> index."""
    used, out = set(), {}
    for role, idx in (overrides or {}).items():
        out[role] = int(idx)
        used.add(int(idx))
    for role in _ORDER:
        if role in out:
            continue
        for ch in channels or []:
            idx = ch.get("i", ch.get("index", ch.get("channel")))
            if idx is not None and idx not in used and \
                    (ch.get("name") or "").strip().lower() in _EXACT[role]:
                out[role] = idx
                used.add(idx)
                break
    for role in _ORDER:
        if role in out:
            continue
        for ch in channels or []:
            idx = ch.get("i", ch.get("index", ch.get("channel")))
            if idx is None or idx in used:
                continue
            nm = " %s " % (ch.get("name") or "").lower()
            words = _ROLE_WORDS[role]
            if role == "808" and ("bass drum" in nm or "bassdrum" in nm):
                continue
            if role == "hat" and ("open" in nm or "ohh" in nm):
                continue
            if any(w in nm for w in words):
                out[role] = idx
                used.add(idx)
                break
    return out


def merge_backbeat(patterns, roles_available):
    """If the project has a snare but no clap (or vice versa), fold the missing
    one onto the one that exists so the backbeat is never lost."""
    p = dict(patterns)
    for want, alt in (("clap", "snare"), ("snare", "clap")):
        if want in p and want not in roles_available and alt in roles_available:
            if alt in p:
                p[alt] = "".join("x" if a == "x" or b == "x" else "."
                                 for a, b in zip(p[alt], p[want]))
            else:
                p[alt] = p[want]
            del p[want]
    return p


def describe():
    return {
        "genres": {g: {"bpm": s["bpm"], "default_mood": s["mood"], "about": s["about"]}
                   for g, s in GENRES.items()},
        "moods": {m: s["about"] for m, s in MOODS.items()},
    }
