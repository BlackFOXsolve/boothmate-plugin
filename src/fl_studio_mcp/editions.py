"""Which FL Studio edition the user has, and what that means for BoothMate.

FL's scripting API doesn't expose the edition or licence, so BoothMate learns
it two ways: trial mode is noticed from FL's welcome window, and the user is
asked once ("Which FL Studio do you have?"). The answer is kept in
~/.flstudio-mcp/profile.json on the user's own computer.

Facts per Image-Line's manual (FL Studio Editions & Features page).
"""
from __future__ import annotations

import json
import os
from pathlib import Path

EDITIONS = {
    "trial": {
        "name": "FL Studio trial",
        "can_record_audio": True,
        "notes": [
            "The trial works like whichever edition was picked on FL's start screen.",
            "You can export your beat (WAV, MP3, OGG or MIDI) in the trial.",
            "Saved trial projects can't be reopened until FL Studio is bought, so "
            "export before closing FL Studio.",
        ],
    },
    "fruity": {
        "name": "Fruity Edition",
        "can_record_audio": False,
        "notes": [
            "Fruity Edition can't record audio, so recording vocals needs Producer "
            "Edition or higher.",
            "Fruity Edition allows up to 8 audio clips in the Playlist.",
        ],
    },
    "producer": {
        "name": "Producer Edition",
        "can_record_audio": True,
        "notes": ["Producer Edition has everything BoothMate uses."],
    },
    "signature": {
        "name": "Signature Bundle",
        "can_record_audio": True,
        "notes": ["Signature Bundle includes NewTone, which can tune vocals."],
    },
    "all_plugins": {
        "name": "All Plugins Edition",
        "can_record_audio": True,
        "notes": ["All Plugins Edition includes every Image-Line plugin, NewTone included."],
    },
}

_ALIASES = {"all plugins": "all_plugins", "all plugins edition": "all_plugins", "apb": "all_plugins",
            "signature bundle": "signature", "producer edition": "producer",
            "fruity edition": "fruity", "free trial": "trial", "demo": "trial"}


def _path() -> Path:
    return Path(os.path.expanduser("~")) / ".flstudio-mcp" / "profile.json"


def _load() -> dict:
    try:
        return json.loads(_path().read_text())
    except (OSError, ValueError):
        return {}


def _save(data: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    tmp.replace(p)


def normalize(edition: str) -> str:
    e = (edition or "").strip().lower()
    e = _ALIASES.get(e, e.replace(" ", "_"))
    if e not in EDITIONS:
        raise ValueError("Unknown edition %r. Use one of: %s." % (edition, ", ".join(EDITIONS)))
    return e


def get() -> str | None:
    return _load().get("fl_edition")


def set_edition(edition: str, source: str = "user") -> str:
    e = normalize(edition)
    data = _load()
    data["fl_edition"] = e
    data["fl_edition_source"] = source
    _save(data)
    return e


def note_trial_seen() -> None:
    """FL's welcome window said 'trial mode'. Record it unless the user has
    told us they own a paid edition."""
    data = _load()
    if data.get("fl_edition_source") != "user" or data.get("fl_edition") in (None, "trial"):
        data["fl_edition"] = "trial"
        data["fl_edition_source"] = "detected"
        _save(data)


def describe(edition: str | None) -> dict:
    if not edition:
        return {"edition": None, "ask_user": "Ask once: which FL Studio do they have? "
                "Trial, Fruity, Producer, Signature Bundle or All Plugins Edition. "
                "Then call set_fl_edition."}
    info = EDITIONS[edition]
    return {"edition": edition, "name": info["name"], "notes": info["notes"]}


def can_record_audio() -> bool:
    e = get()
    return EDITIONS[e]["can_record_audio"] if e else True
