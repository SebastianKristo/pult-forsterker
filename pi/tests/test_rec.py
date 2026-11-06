import os
import sys
import types

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_rec as R  # noqa: E402

SR = 8000   # raskere tester; algoritmen er uavhengig av rate


# ---------- tittel ----------
@pytest.mark.parametrize("raw,exp", [
    ("Coldplay - Yellow", ("Coldplay", "Yellow")),
    ("A-ha – Take On Me", ("A-ha", "Take On Me")),
    ("Röyksopp — Eple", ("Röyksopp", "Eple")),
    ("Take On Me by a-ha", ("a-ha", "Take On Me")),
    ("Kygo: Firestone", ("Kygo", "Firestone")),
    ("DAVID BOWIE - HEROES", ("David Bowie", "Heroes")),
    ("Adele - Hello (Radio Edit)", ("Adele", "Hello")),
    ("Adele - Hello [Live]", ("Adele", "Hello [Live]")),
    ("NRK P3", None), ("", None), ("Reklame", None), ("- ", None), ("https://p3.no", None),
])
def test_parse_title(raw, exp):
    assert R.parse_title(raw) == exp


def test_safe_name_and_path():
    assert R.safe_name('AC/DC: "Back" *in* <Black>?') == "AC DC Back in Black"
    assert R.safe_name("Prince.") == "Prince"
    assert R.safe_name("CON") == "_CON"
    assert R.safe_name("") == "Ukjent"
    assert R.song_relpath("AC/DC", "T.N.T.", "flac") == os.path.join("AC DC", "AC DC - T.N.T.flac")
    assert R.song_relpath("A", "B", "x").endswith(".mp3")


# ---------- SMB ----------
def test_smb_norm_and_cmd():
    assert R.smb_norm_share("nas.local/musikk/") == "//nas.local/musikk"
    assert R.smb_norm_share("\\\\NAS\\Musikk") == "//NAS/Musikk"
    assert R.smb_norm_share("smb://nas/m") == "//nas/m"
    cmd = R.smb_mount_cmd("nas/m", "2.1", 1000, 29, "/mnt/x", "/etc/c")
    assert cmd[:5] == ["mount", "-t", "cifs", "//nas/m", "/mnt/x"]
    o = cmd[-1].split(",")
    assert "vers=2.1" in o and "uid=1000" in o and "gid=29" in o and "credentials=/etc/c" in o
    assert "guest" in R.smb_mount_cmd("nas/m", guest=True)[-1]
    assert R.smb_versions("auto") == ["3.0", "2.1"] and R.smb_versions("1.0") == ["1.0"]
    assert "password=p w" in R.smb_cred_text("u", "p w", "D") and "domain=D" in R.smb_cred_text("u", "p", "D")


def test_smb_errors():
    assert "Tilgang nektet" in R.smb_error("mount error(13): Permission denied")
    assert "Fant ikke" in R.smb_error("mount error(2): No such file or directory")
    assert "versjonen" in R.smb_error("mount error(95): Operation not supported")
    assert "serveren" in R.smb_error("mount error(112): Host is down")


def test_smb_mount_fallback(tmp_path):
    calls = []

    def run(cmd, **kw):
        calls.append(cmd)
        if cmd[0] == "mount":
            v = [o for o in cmd[-1].split(",") if o.startswith("vers=")][0]
            ok = v == "vers=2.1"
            return types.SimpleNamespace(returncode=0 if ok else 32, stdout="", stderr="" if ok else "mount error(95): Operation not supported")
        return types.SimpleNamespace(returncode=0, stdout="", stderr="")
    cred = tmp_path / "c.cred"
    ok, msg = R.smb_mount({"smb_share": "nas/m", "smb_user": "u", "smb_password": "pw"}, run=run, mnt=str(tmp_path / "mnt"), cred=str(cred))
    assert ok and "2.1" in msg
    assert oct(cred.stat().st_mode & 0o777) == "0o600" and "password=pw" in cred.read_text()
    ok, msg = R.smb_mount({"smb_share": ""}, run=run)
    assert not ok


def test_smb_list_shares():
    def run(cmd, **kw):
        assert "-U" in cmd and "D/u%p" in cmd
        return types.SimpleNamespace(returncode=0, stdout="Disk|musikk|\nDisk|IPC$|\nPrinter|hp|\nDisk|backup|\n", stderr="")
    assert R.smb_list_shares("//nas/x", "u", "p", "D", run=run) == ["musikk", "backup"]


# ---------- lydanalyse ----------
def _song(sec, f0, rng):
    t = np.arange(int(sec * SR)) / SR
    x = 0.4 * np.sin(2 * np.pi * f0 * t) + 0.2 * np.sin(2 * np.pi * f0 * 1.5 * t) + 0.02 * rng.standard_normal(len(t))
    fade = int(2 * SR)
    x[:fade] *= np.linspace(0, 1, fade)
    x[-fade:] *= np.linspace(1, 0, fade)
    return x


def _speech(sec, rng):
    n = int(sec * SR)
    x = 0.3 * rng.standard_normal(n)
    env = (np.sin(2 * np.pi * 3 * np.arange(n) / SR) > 0.2).astype(float)   # ord og pauser
    return x * env


def _mk(rng):
    parts, bounds, t = [], [], 0.0
    for sec, f0 in ((90, 220), (120, 330), (100, 262)):
        s = _song(sec, f0, rng)
        bounds.append(t)
        parts.append(s)
        parts.append(np.zeros(int(0.8 * SR)))
        t += sec + 0.8
    return np.concatenate(parts).astype(np.float32), bounds, t


def test_find_cut_and_delay():
    rng = np.random.default_rng(1)
    pcm, bounds, total = _mk(rng)
    f = R.features(pcm, SR)
    lag = 8.0   # metadata kommer 8 s etter at låta starter
    meta = [b + lag for b in bounds[1:]]
    d = R.estimate_delay(f, meta)
    assert abs(d - lag) < 2.0
    for b, m in zip(bounds[1:], meta):
        t, s = R.find_cut(f, m, 20, d)
        assert abs(t - (b - 0.4)) < 1.5, (t, b)


def test_plan_songs_and_min_len():
    rng = np.random.default_rng(2)
    pcm, bounds, total = _mk(rng)
    f = R.features(pcm, SR)
    ev = [(bounds[0] + 5, "A - En"), (bounds[1] + 6, "B - To"), (bounds[2] + 6, "C - Tre"), (total - 30, "NRK P3")]
    songs, d = R.plan_songs(f, ev, total, 60)
    names = [(s["artist"], s["title"]) for s in songs]
    assert ("B", "To") in names and ("C", "Tre") in names
    b = [s for s in songs if s["artist"] == "B"][0]
    assert abs(b["start"] - bounds[1]) < 2 and abs(b["end"] - bounds[2]) < 2
    # kanal-ident uten artist-tittel lagres ikke, og korte låter forkastes
    assert all(s["artist"] != "NRK P3" for s in songs)
    songs2, _ = R.plan_songs(f, ev, total, 200)
    assert songs2 == []


def test_trim_speech_max_15s():
    rng = np.random.default_rng(3)
    x = np.concatenate([_speech(30, rng), _song(100, 300, rng)]).astype(np.float32)
    f = R.features(x, SR)
    a, b = R.trim_speech(f, 0.0, len(x) / SR)
    assert 5 <= a <= 15.0 + 1e-6
    assert b == pytest.approx(len(x) / SR)
