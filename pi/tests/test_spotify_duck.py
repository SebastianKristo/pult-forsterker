"""Spotify-fremdrift (librespot --onevent) og ducking (POST /api/duck)."""
import os
import sys
import tempfile

os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import ki_amp_daemon as d  # noqa: E402


def test_spotify_metadata_og_fremdrift(monkeypatch):
    t = [1000.0]
    monkeypatch.setattr(d.time, "time", lambda: t[0])
    d.spotify.update(playing=False, paused=False, position=0, pos_t=0.0, duration=0)
    d.spotify_event({"event": "track_changed", "name": "Numb", "artists": "Linkin Park", "album": "Meteora",
                     "covers": "https://i.scdn.co/image/abc\nhttps://i.scdn.co/image/small", "duration_ms": "185000"})
    d.spotify_event({"event": "playing", "position_ms": "10000"})
    assert d.spotify["title"] == "Numb" and d.spotify["cover"] == "https://i.scdn.co/image/abc" and d.spotify["duration"] == 185
    t[0] += 30
    assert d.spotify_pos() == 40
    d.spotify_event({"event": "paused"})
    t[0] += 60
    assert d.spotify_pos() == 40          # står stille på pause
    t[0] += 1000
    d.spotify.update(playing=True)
    assert d.spotify_pos() == 185         # aldri forbi slutten


def test_duck_senker_leser_og_lofter(tmp_path):
    import skjold_duck as D
    vol, hendt = [50], []
    ctx = {"get_volume": lambda: vol[0], "set_volume": lambda v: (vol.__setitem__(0, v), hendt.append(("vol", v))),
           "say": lambda t: hendt.append(("si", t)) or "/tmp/x.wav", "announce": lambda u: hendt.append(("spill", u)),
           "post": lambda u, b: hendt.append(("post", u))}
    dk = D.Ducker(ctx, str(tmp_path / "d.json"), sleep=lambda s: None)
    r = dk.duck({"tekst": "Vaskemaskinen er ferdig", "kilde": "ha"})
    assert r["til"] == D.ducked_volume(50, -20) == 17
    assert ("si", "Vaskemaskinen er ferdig") in hendt and ("spill", "/tmp/x.wav") in hendt and vol[0] == 50
    dk.sett({"homey": False})
    assert not dk.duck({"tekst": "x", "kilde": "homey"})["ok"]


def test_duck_telefon_holder_til_slutt(tmp_path):
    import skjold_duck as D
    vol = [40]
    ctx = {"get_volume": lambda: vol[0], "set_volume": lambda v: vol.__setitem__(0, v), "say": lambda t: None,
           "announce": lambda u: None, "post": lambda u, b: None}
    import time as _t
    dk = D.Ducker(ctx, None, sleep=lambda s: None if s < 100 else _t.sleep(5))   # tidsavbruddet skal ikke slå til i testen
    dk.duck({"kilde": "telefon"})
    assert vol[0] == D.ducked_volume(40, -20)
    dk.duck({"kilde": "telefon", "slutt": True})
    assert vol[0] == 40
