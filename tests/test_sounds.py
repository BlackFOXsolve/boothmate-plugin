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


def test_open_with_fl_rejects_missing_file():
    assert sounds.open_with_fl("/definitely/not/here.wav")["ok"] is False
