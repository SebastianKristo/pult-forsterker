import os
import struct
import subprocess
import sys
import shutil
import math

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_vinyl as V  # noqa: E402


def lv(pattern):
    """[(sekunder, loud?)] → nivåliste med HOP-oppløsning (-20 dB musikk, -70 dB stillhet)."""
    out = []
    for secs, on in pattern:
        out += [-20.0 if on else -70.0] * int(round(secs / V.HOP))
    return out


def test_rms_db():
    assert V.rms_db(b"") == -120.0
    assert V.rms_db(b"\x00\x00" * 100) == -120.0
    full = struct.pack("<4h", 32767, -32767, 32767, -32767)
    assert V.rms_db(full, step=1) > -0.1


def test_split_three_tracks():
    levels = lv([(1, 0), (180, 1), (3, 0), (200, 1), (2, 0), (150, 1), (5, 0)])
    segs = V.split_segments(levels)
    assert len(segs) == 3
    assert abs(segs[0][0] - 1) < 0.1 and abs(segs[0][1] - 181) < 0.1
    assert abs(segs[2][1] - 536) < 0.1


def test_short_pause_inside_song_and_short_fragment():
    # 0.5 s pause (for kort) og et 10 s fragment (for kort spor) skal ikke bli egne spor
    levels = lv([(100, 1), (0.5, 0), (100, 1), (3, 0), (10, 1), (2, 0), (120, 1)])
    segs = V.split_segments(levels)
    assert len(segs) == 2


def test_fit_tracklist_merge_and_split():
    levels = lv([(120, 1), (2, 0), (60, 1), (1.5, 0), (60, 1), (3, 0), (200, 1)])
    segs = V.split_segments(levels)
    assert len(segs) == 4
    fit = V.fit_tracklist(segs, [120, 121, 200], levels)
    assert len(fit) == 3
    # én lang bit som egentlig er to spor uten pause, men med et stille punkt nær 150 s
    levels2 = [-20.0] * int(300 / V.HOP)
    for i in range(int(149.5 / V.HOP), int(150.5 / V.HOP)):
        levels2[i] = -50.0
    fit2 = V.fit_tracklist([(0.0, 300.0)], [148, 152], levels2)
    assert len(fit2) == 2 and abs(fit2[0][1] - 149.5) < 1.0


def test_paths_and_plan():
    assert V.track_relpath("AC/DC", "Back: in Black", 3, "Hells Bells?") == os.path.join("AC DC", "Back  in Black".replace("  ", " "), "03 Hells Bells.flac")
    sides = [{"name": "A", "segs": [(0, 100), (102, 200)], "raw": "a.wav"}, {"name": "B", "segs": [(0, 90)], "raw": "b.wav"}]
    plan = V.plan_tracks({"tracks": [{"title": "En"}, {"title": "To"}]}, sides)
    assert [t["n"] for t in plan] == [1, 2, 3]
    assert [t["title"] for t in plan] == ["En", "To", "Spor 3"]
    assert plan[2]["side"] == "B" and plan[2]["raw"] == "b.wav"


def test_cut_cmd():
    c = V.ffmpeg_cut_cmd("in.wav", "out.flac", 1.5, 10, {"TITLE": "X", "DATE": ""}, "c.jpg")
    assert c[-1] == "out.flac" and "TITLE=X" in c and not any(x.startswith("DATE=") for x in c)
    assert "attached_pic" in c and "flac" in c


def test_archive_edit(tmp_path):
    a = V.Archive(str(tmp_path / "v.json"))
    root = tmp_path / "root"
    f = root / V.track_relpath("A", "B", 1, "Spor 1")
    f.parent.mkdir(parents=True)
    f.write_bytes(b"x")
    a.add({"id": "p1", "artist": "A", "album": "B", "tracks": [{"n": 1, "title": "Spor 1", "file": V.track_relpath("A", "B", 1, "Spor 1")}]})
    rec = a.edit("p1", {"album": "C", "tracks": [{"n": 1, "title": "Ny"}]}, str(root))
    assert rec["tracks"][0]["file"] == V.track_relpath("A", "C", 1, "Ny")
    assert (root / rec["tracks"][0]["file"]).exists()
    assert a.delete("p1") == []
    with pytest.raises(KeyError):
        a.get("p1")


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg mangler")
def test_session_end_to_end(tmp_path, monkeypatch):
    """Syntetisk plateside: 3 toner med stillhet imellom, «ALSA» erstattes av en WAV-fil."""
    import wave
    src = tmp_path / "side.wav"
    sr = V.SR
    with wave.open(str(src), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr)
        for secs, f in [(1, 0), (40, 440), (3, 0), (35, 660), (3, 0), (45, 330), (2, 0)]:
            n = int(secs * sr)
            frames = bytearray()
            for i in range(n):
                v = int(8000 * math.sin(2 * math.pi * f * i / sr)) if f else 0
                frames += struct.pack("<hh", v, v)
            w.writeframes(bytes(frames))
    real_popen = subprocess.Popen

    def fake_popen(cmd, **kw):
        if "-f" in cmd and "alsa" in cmd:
            cmd = ["ffmpeg", "-nostdin", "-loglevel", "error", "-i", str(src), "-f", "s16le", "-ac", "2", "-ar", str(sr), "-"]
        return real_popen(cmd, **kw)
    monkeypatch.setattr(V.subprocess, "Popen", fake_popen)
    root = tmp_path / "nas"
    s = V.Session({"device": lambda: "hw:0", "root": lambda: (str(root), "smb"), "tmp": str(tmp_path / "tmp"),
                   "identify": lambda p: {"found": True, "mbid": "m1", "artist": "Testband", "album": "Prøve"},
                   "release": lambda m: {"artist": "Testband", "album": "Prøve", "rid": "r1", "cover": "",
                                         "tracks": [{"n": 1, "title": "Én", "ms": 40000}, {"n": 2, "title": "To", "ms": 35000},
                                                    {"n": 3, "title": "Tre", "ms": 45000}]},
                   "cfg": lambda: {}, "on_change": lambda: None}, V.Archive(str(tmp_path / "v.json")))
    s.start_side()
    s.proc.wait(timeout=60)
    import time
    time.sleep(0.5)
    s.state = "recording"
    s.proc = subprocess.Popen(["true"])
    st = s.stop_side()
    assert st["sides"][0]["spor"] == 3
    for _ in range(100):
        if s.album.get("album"):
            break
        time.sleep(0.1)
    assert [t["title"] for t in s.status()["tracks"]] == ["Én", "To", "Tre"]
    s.finish()
    for _ in range(300):
        if s.state == "idle":
            break
        time.sleep(0.1)
    assert s.state == "idle", s.msg
    alb = s.archive.load()[0]
    assert alb["album"] == "Prøve" and len(alb["tracks"]) == 3
    assert (root / "Testband" / "Prøve" / "02 To.flac").exists()
