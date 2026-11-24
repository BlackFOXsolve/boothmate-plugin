import math
import os
import struct
import time
import wave

from fl_studio_mcp.tools import loops


def _tone_wav(path, bpm=145.0, bars=4, freqs=(73.42, 293.66, 349.23, 440.0), sr=22050):
    dur = bars * 240.0 / bpm
    n = int(dur * sr)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        frames = bytearray()
        for i in range(n):
            v = sum(math.sin(2 * math.pi * f * i / sr) for f in freqs) / len(freqs)
            s = int(v * 20000)
            frames += struct.pack("<hh", s, s)
        w.writeframes(bytes(frames))
    return dur


def test_tempo_from_length():
    assert loops.tempo_from_length(26.483) == (145.0, 16)
    assert loops.tempo_from_length(240.0 / 90 * 4) == (90.0, 4)


def test_analyze_loop_finds_tempo_and_d_minor(tmp_path):
    p = tmp_path / "loop.wav"
    _tone_wav(p)   # D2 bass + D F A
    info = loops.analyze_loop(str(p))
    assert info["bars"] == 4 and abs(info["bpm"] - 145) < 0.5
    assert info["root"] == "D" and info["mode"] == "minor"
    assert info["per_bar"][0]["bass"] == "D"


def test_clashes():
    dorian = ["C", "D", "E", "F", "G", "A", "B"]
    assert loops.clashes(dorian, "D minor")          # D minor has Bb, the loop has B
    assert not loops.clashes(["C", "D", "D#", "F", "G", "G#", "A#"], "C minor")


def test_intro_drop_layout():
    lanes = loops.intro_drop("trap", 4, 4)
    S = 16
    assert all(st >= 4 * S for st in lanes["kick"])               # no kick in the intro
    intro_hats = [st for st in lanes["hat"] if st < 4 * S]
    assert intro_hats and min(intro_hats) >= 2 * S                 # hats creep in late
    snare_key = "snare" if "snare" in lanes else "clap"
    assert any(3 * S <= st < 4 * S for st in lanes[snare_key])     # roll in the last intro bar
    assert max(max(v) for v in lanes.values()) < 8 * S


def test_bass_line_follows_drop_kicks_on_root():
    kicks = [64, 74, 80, 90]
    notes = loops.bass_line(kicks, 2, 8)
    assert [n["time_bars"] for n in notes] == [4.0, 4.625, 5.0, 5.625]
    assert notes[0]["pitch"] % 12 == 2 and notes[0]["pitch"] < 40
    assert notes[-1]["pitch"] == notes[0]["pitch"] + 12             # octave jump, end of 2nd bar


def test_newest_download_and_import(tmp_path):
    dl = tmp_path / "Downloads"
    dl.mkdir()
    old = dl / "old-loop.wav"
    old.write_bytes(b"a")
    time.sleep(0.01)
    new = dl / "type-shii-loop.wav"
    new.write_bytes(b"bb")
    os.utime(old, (1, 1))
    (dl / "notes.txt").write_text("x")
    assert loops.newest_download("", dl) == new
    assert loops.newest_download("latest old", dl) == old
    dest = loops.import_audio(new, tmp_path / "Audio")
    assert dest == tmp_path / "Audio" / "BoothMate" / "type-shii-loop.wav" and dest.read_bytes() == b"bb"
    assert new.exists()
