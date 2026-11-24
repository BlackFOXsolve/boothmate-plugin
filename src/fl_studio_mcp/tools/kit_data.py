"""Starter kit data (0.1.7): which FL Studio stock sounds, instruments,
effects and mixer levels make up each style.

All paths are relative to FL Studio's Patches folder, the same tree the
Browser shows. Each list is in order of preference; BoothMate uses the first
one that exists on this computer and that the user's FL edition includes.
"""
from __future__ import annotations

# ---- edition tiers ---------------------------------------------------------
# Lowest edition that includes each Image-Line instrument (best known for
# FL Studio 2024-2026; the trial includes everything). Unknown plugins are
# treated as Producer.
EDITION_RANK = {"fruity": 0, "producer": 1, "signature": 2, "all_plugins": 3, "trial": 3}
PLUGIN_TIER = {
    "3x osc": "fruity", "fl keys": "fruity", "simsynth": "fruity", "boobass": "fruity",
    "fruity dx10": "fruity", "plucked!": "fruity", "sampler": "fruity", "flex": "fruity",
    "sytrus": "producer", "sakura": "producer", "poizone": "producer", "harmless": "producer",
    "sawer": "producer", "toxic biohazard": "producer", "kepler": "producer", "directwave": "producer",
    "ogun": "signature", "harmor": "all_plugins", "kepler exo": "all_plugins",
}

SAMPLER = ["Plugin database/Generators/Sampler/Sampler.fst", "Channel presets/Sampler/Default.fst"]

# ---- roles -----------------------------------------------------------------
# kind: "drum" = sample on a sampler channel; "inst" = instrument preset.
# Names are what the channel is renamed to; make_beat finds "Keys" for chords
# (it takes the first keys/pad/bell channel, so Keys sits before Melody/Pad).
ROLE_KIND = {"Kick": "drum", "Snare": "drum", "Hi Hat": "drum", "Open Hat": "drum",
             "808": "drum", "Perc": "drum", "Keys": "inst", "Melody": "inst", "Pad": "inst"}

# Preferred mixer insert per role (a different free insert is used if taken).
INSERTS = {"Kick": 1, "Snare": 2, "Hi Hat": 3, "Open Hat": 4, "808": 5, "Perc": 6,
           "Keys": 7, "Melody": 8, "Pad": 9}

# Starting mix per role: (volume dB, pan -1..1). Kick and 808 lead, hats and
# pads sit back, a little width on hats/perc/melody.
MIX = {"Kick": (-3.0, 0.0), "Snare": (-5.0, 0.0), "Hi Hat": (-10.0, 0.12),
       "Open Hat": (-12.0, -0.15), "808": (-4.0, 0.0), "Perc": (-11.0, -0.25),
       "Keys": (-9.0, 0.0), "Melody": (-9.0, 0.1), "Pad": (-14.0, 0.0)}

_VERB_ROOM = "Plugin presets/Effects/Fruity Reeverb 2/Drum Room.fst"
_VERB_HALL = "Plugin presets/Effects/Fruity Reeverb 2/Large Hall.fst"
_VERB_VENUE = "Plugin presets/Effects/Fruity Reeverb 2/The Venue.fst"
_DELAY = "Plugin presets/Effects/Fruity Delay 3/Tape.fst"
_CLIP = "Plugin database/Effects/Dynamics/Fruity Soft Clipper.fst"

_808_SUB = ["Misc/Used by demo projects/DEDZII - NIGHT TERROR/FLEX 808 Sub.ogg",
            "Packs/Legacy/Drums/Dance/Basic 808 Kick.wav"]

KITS: dict[str, dict] = {
    "dark_trap": {
        "label": "Dark trap (Metro, Southside, 808 Mafia style)",
        "tempo": 140,
        "sounds": {
            "Kick": (["Packs/Drums/Kicks/808 Kick.wav"], "808 kick"),
            "Snare": (["Packs/Drums/Percussion/909 Clap.wav", "Packs/Drums/Snares/808 Snare.wav"], "clap"),
            "Hi Hat": (["Packs/Drums/Hats/808 CH.wav"], "808 ch"),
            "Open Hat": (["Packs/Drums/Hats/808 OH.wav"], "808 oh"),
            "808": (_808_SUB, "808 sub"),
        },
        "instruments": {
            "Keys": ["Plugin presets/Generators/FL Keys/Dark Piano.fst",
                     "Plugin presets/Generators/Sakura/Default/Drama Keys.fst"],
            "Melody": ["Plugin presets/Generators/Sytrus/Bell/Dream bell.fst",
                       "Plugin presets/Generators/Harmor/Bell/Cursed bells.fst",
                       "Channel presets/3x Osc/Bell.fst"],
            "Pad": ["Plugin presets/Generators/Sytrus/Pad/Darkxpad.fst",
                    "Channel presets/3x Osc/Pilch tech pad.fst"],
        },
        "fx": {"Snare": [_VERB_ROOM], "808": [_CLIP], "Melody": [_VERB_HALL, _DELAY],
               "Pad": [_VERB_HALL], "Keys": [_VERB_VENUE]},
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
            "808": (_808_SUB, "808 sub"),
        },
        "instruments": {
            "Keys": ["Plugin presets/Generators/FL Keys/Dark Piano.fst",
                     "Plugin presets/Generators/Sytrus/Piano/Keys.fst"],
            "Melody": ["Plugin presets/Generators/Sytrus/Bell/Tacobell.fst",
                       "Plugin presets/Generators/Harmor/Bell/Cursed bells.fst",
                       "Channel presets/3x Osc/Bell.fst"],
            "Pad": ["Plugin presets/Generators/Sytrus/Pad/Darkxpad.fst",
                    "Channel presets/3x Osc/Pilch tech pad.fst"],
        },
        "fx": {"Snare": [_VERB_ROOM], "808": [_CLIP], "Melody": [_VERB_HALL],
               "Pad": [_VERB_HALL]},
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
        "instruments": {
            "Keys": ["Plugin presets/Generators/FL Keys/ePiano.fst",
                     "Plugin presets/Generators/Sakura/Default/E-Keys 1.fst"],
            "Melody": ["Plugin presets/Generators/Harmless/Keyboards/Dream Keys FG.fst",
                       "Plugin presets/Generators/FL Keys/Broken Piano.fst"],
            "Pad": ["Plugin presets/Generators/Sakura/Default/Pad 1.fst",
                    "Channel presets/3x Osc/Pilch tech pad.fst"],
        },
        "fx": {"Snare": [_VERB_ROOM], "Keys": [_VERB_VENUE], "Pad": [_VERB_HALL]},
    },
    "rnb": {
        "label": "R&B / soul (smooth, Bryson Tiller style)",
        "tempo": 75,
        "sounds": {
            "Kick": (["Packs/Drums/Kicks/Chrome Kick.wav", "Packs/Drums/Kicks/808 Kick.wav"], "kick"),
            "Snare": (["Packs/Drums/Percussion/Pap Clap.wav", "Packs/Drums/Percussion/SC Clap.wav"], "clap"),
            "Hi Hat": (["Packs/Drums/Hats/Ekit 1 Hat.wav", "Packs/Drums/Hats/808 CH.wav"], "hat"),
            "Open Hat": (["Packs/Drums/Hats/808 OH.wav"], "808 oh"),
            "808": (_808_SUB, "808 sub"),
        },
        "instruments": {
            "Keys": ["Plugin presets/Generators/Sakura/Sonic Haiku Bank/KY Warm Keys.fst",
                     "Plugin presets/Generators/FL Keys/ePiano.fst"],
            "Melody": ["Plugin presets/Generators/Sytrus/Bell/Bellarina.fst",
                       "Channel presets/3x Osc/Bell.fst"],
            "Pad": ["Plugin presets/Generators/Sakura/Default/Pad 3.fst",
                    "Channel presets/3x Osc/Pilch tech pad.fst"],
        },
        "fx": {"Snare": [_VERB_ROOM], "Keys": [_VERB_VENUE], "Melody": [_VERB_HALL, _DELAY],
               "Pad": [_VERB_HALL]},
    },
}


def plugin_of(rel: str) -> str | None:
    """Instrument or effect a preset path belongs to, e.g.
    'Plugin presets/Generators/Sytrus/Bell/x.fst' -> 'Sytrus',
    'Plugin database/Effects/Dynamics/Fruity Soft Clipper.fst' -> 'Fruity Soft Clipper',
    'Channel presets/3x Osc/Bell.fst' -> '3x Osc'. PURE."""
    parts = rel.replace("\\", "/").split("/")
    if len(parts) >= 4 and parts[0] == "Plugin presets" and parts[1] in ("Generators", "Effects"):
        return parts[2]
    if parts[0] == "Plugin database" and len(parts) >= 3:
        return parts[-1].rsplit(".", 1)[0]
    if parts[0] == "Channel presets" and len(parts) >= 3:
        return parts[1]
    return None


def kind_of(rel: str) -> str:
    """'effect', 'instrument' or 'sample' for a path under Patches. PURE."""
    parts = rel.replace("\\", "/").split("/")
    if not rel.lower().endswith(".fst"):
        return "sample"
    if len(parts) >= 2 and parts[1] == "Effects":
        return "effect"
    if parts[0] in ("Mixer presets",):
        return "other"
    return "instrument"


def allowed(rel: str, edition: str | None) -> bool:
    """Whether the user's FL edition includes the plugin this preset needs. PURE."""
    plug = (plugin_of(rel) or "").lower()
    tier = PLUGIN_TIER.get(plug, "producer")
    # Unknown edition: assume Producer (the most common paid edition), so a
    # Fruity user isn't handed demo-mode plugins and a trial user still gets
    # good sounds.
    have = EDITION_RANK.get(edition or "producer", 1)
    return EDITION_RANK[tier] <= have
