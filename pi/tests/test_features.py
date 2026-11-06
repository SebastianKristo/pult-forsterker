"""Intercom, låtgjenkjenning/vinylmodus, dørklokke, rutiner og trygg oppdatering."""
import json
import math
import os
import sys
import wave

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import skjold_doorbell as DB    # noqa: E402
import skjold_intercom as IC    # noqa: E402
import skjold_recognize as RC   # noqa: E402
import skjold_routines as RT    # noqa: E402
import skjold_safeupdate as SU  # noqa: E402

PEERS = [{"id": "kjokken", "navn": "Kjøkken", "base": "http://10.0.0.2:8765"},
         {"id": "soverom", "navn": "Soverom", "base": "http://10.0.0.3:8765"}]


# ---------- intercom ----------
def test_plan_targets():
    assert IC.plan_targets("all", "stue", PEERS) == (True, PEERS)
    assert IC.plan_targets("kjokken", "stue", PEERS) == (False, [PEERS[0]])
    assert IC.plan_targets("stue,soverom", "stue", PEERS) == (True, [PEERS[1]])
    assert IC.plan_targets(["self"], "stue", PEERS) == (True, [])


def test_duck_and_tone(tmp_path):
    assert IC.duck_volume(50, -15) == 25 and IC.duck_volume(0, -15) == 0 and IC.duck_volume(5, -15) == 0
    p = IC.make_tone(str(tmp_path / "d.wav"), "dingdong")
    with wave.open(p) as w:
        assert w.getnchannels() == 2 and w.getframerate() == 48000 and w.getnframes() > 48000


def test_send_forwards_and_plays(tmp_path, monkeypatch):
    played, vols = [], [40]
    ic = IC.Intercom({"announce": played.append, "get_volume": lambda: vols[-1], "set_volume": vols.append,
                      "peers": lambda: PEERS, "self_id": lambda: "stue", "tmpdir": str(tmp_path)})
    sent = []
    monkeypatch.setattr(IC.Intercom, "forward", staticmethod(lambda base, data, ct, s, timeout=15: sent.append(base) or base.endswith("2:8765")))
    res = ic.send(b"RIFF....", "audio/wav", to="all")
    assert res["local"] and res["sent"] == ["Kjøkken"] and res["failed"] == ["Soverom"]
    ic.play_local(str(tmp_path / "x.wav"))   # synkront: dukk → ding → klipp → tilbake
    assert played[-1].endswith("x.wav") and played[-2].endswith("skjold-ding.wav")
    assert vols[-1] == 40 and min(vols) < 40


def test_hop_plays_only_here(tmp_path, monkeypatch):
    ic = IC.Intercom({"announce": lambda p: None, "get_volume": lambda: 0, "set_volume": lambda v: None,
                      "peers": lambda: PEERS, "self_id": lambda: "stue", "tmpdir": str(tmp_path)})
    monkeypatch.setattr(IC.Intercom, "forward", staticmethod(lambda *a, **k: (_ for _ in ()).throw(AssertionError("ingen videresending"))))
    assert ic.send(b"x" * 100, "audio/webm", to="all", hop=True)["sent"] == []


# ---------- gjenkjenning ----------
ACOUSTID = {"status": "ok", "results": [
    {"score": 0.4, "recordings": [{"id": "r1", "title": "Feil", "artists": [{"name": "X"}]}]},
    {"score": 0.95, "recordings": [{"id": "r2", "title": "Take On Me", "artists": [{"name": "a-ha"}],
                                     "releasegroups": [{"id": "rg2", "title": "Hunting High and Low"}]}]}]}


def test_parse_acoustid_and_cover():
    h = RC.parse_acoustid(ACOUSTID)
    assert (h["title"], h["artist"], h["album"], h["mbid"]) == ("Take On Me", "a-ha", "Hunting High and Low", "r2")
    assert RC.cover_url(h).endswith("/release-group/rg2/front-250")


def test_parse_audd():
    h = RC.parse_audd({"status": "success", "result": {"title": "Yellow", "artist": "Coldplay", "album": "Parachutes",
                                                       "spotify": {"album": {"images": [{"url": "https://i/x.jpg"}]}}}})
    assert h["title"] == "Yellow" and RC.cover_url(h) == "https://i/x.jpg"
    assert RC.parse_audd({"status": "success", "result": None}) is None


def test_recognize_falls_back_to_audd(tmp_path, monkeypatch):
    clip = tmp_path / "c.wav"; clip.write_bytes(b"x")
    monkeypatch.setattr(RC, "fingerprint", lambda p: (12, "AQAA"))
    monkeypatch.setattr(RC, "acoustid_lookup", lambda k, d, f: None)
    monkeypatch.setattr(RC, "audd_lookup", lambda t, p: {"title": "Live", "artist": "Band", "album": "", "via": "AudD"})
    res = RC.recognize({"acoustid_key": "k", "audd_token": "t"}, rec=lambda *a: str(clip))
    assert res["found"] and res["via"] == "AudD" and not clip.exists()


def test_wishlist_navidrome(tmp_path):
    calls = []

    def opener(url):
        m = url.split("/rest/")[1].split(".view")[0]
        calls.append(m)
        body = {"status": "ok"}
        if m == "search3":
            body["searchResult3"] = {"song": [{"id": "s9", "title": "Take On Me", "artist": "a-ha"}]}
        if m == "getPlaylists":
            body["playlists"] = {"playlist": []}
        return {"subsonic-response": body}
    wl = RC.Wishlist(str(tmp_path / "w.json"))
    res = wl.add({"title": "Take On Me", "artist": "a-ha"}, RC.Subsonic("http://nd", "u", "p", opener=opener))
    assert res["added"] and res["item"]["navidrome"] and calls == ["search3", "star", "getPlaylists", "createPlaylist"]
    assert not wl.add({"title": "take on me", "artist": "A-HA"})["added"]   # duplikat


# ---------- vinylmodus: spor-skifte ----------
def _blocks(seconds, level, rate=11025, block=0.05, freq=440.0, rng=None):
    n = int(seconds / block)
    out = []
    for i in range(n):
        t = np.arange(int(rate * block)) / rate
        x = level * np.sin(2 * math.pi * freq * t) + (rng.normal(0, 0.0003, t.size) if rng is not None else 0)
        out.append(float(np.sqrt(np.mean(x ** 2))))
    return out


def test_track_detector_gap_and_shift():
    rng = np.random.default_rng(1)
    d = TrackDetectorSeq = RC.TrackDetector()
    seq = _blocks(2.0, 0.0, rng=rng) + _blocks(30, 0.3) + _blocks(2.2, 0.0, rng=rng) + _blocks(25, 0.25) + _blocks(25, 0.012)
    events, t = [], 0.0
    for rms in seq:
        ev = d.feed(rms); t += 0.05
        if ev:
            events.append((ev, round(t, 1)))
    kinds = [e[0] for e in events]
    assert kinds[0] == "start" and "gap" in kinds and "shift" in kinds
    gap_t = next(t for k, t in events if k == "gap")
    assert 34.0 <= gap_t <= 34.4      # rett etter 2,2 s stillhet
    assert not RC.TrackDetector().feed(0.0)


def test_short_pause_is_not_new_track():
    d = RC.TrackDetector()
    evs = [d.feed(r) for r in _blocks(10, 0.3) + _blocks(0.8, 0.0) + _blocks(10, 0.3)]
    assert "gap" not in evs


def test_mb_release_tracks():
    def opener(u):
        return {"releases": [
            {"id": "bootleg", "status": "Bootleg", "media": [{"tracks": [{"title": "x", "recording": {"id": "r2"}}]}]},
            {"id": "rel1", "status": "Official", "title": "Hunting High and Low", "release-group": {"primary-type": "Album"},
             "artist-credit": [{"name": "a-ha"}],
             "media": [{"position": 1, "tracks": [{"title": "Take On Me", "length": 225000, "recording": {"id": "r2"}},
                                                  {"title": "Train of Thought", "length": 254000, "recording": {"id": "r3"}}]}]}]}
    a = RC.mb_release_tracks("r2", opener=opener)
    assert a["rid"] == "rel1" and a["pos"] == 1 and len(a["tracks"]) == 2 and a["cover"].endswith("/release/rel1/front-250")


def test_vinyl_identify_builds_meta():
    w = RC.VinylWatcher({"cfg": lambda: {"acoustid_key": "k"}},
                        lookup=lambda c, p: {"found": True, "title": "Take On Me", "artist": "a-ha", "mbid": "r2", "cover": "c"},
                        release=lambda m: {"album": "Hunting", "cover": "rc", "tracks": [{"n": 1}], "pos": 1})
    m = w.identify(b"\0\0" * 11025 * 12)
    assert m["album"] == "Hunting" and m["art"] == "rc" and m["pos"] == 1


# ---------- dørklokke ----------
def test_is_ring():
    assert DB.is_ring({"entity_id": "binary_sensor.d", "state": "off"}, {"entity_id": "binary_sensor.d", "state": "on"})
    assert not DB.is_ring({"entity_id": "binary_sensor.d", "state": "on"}, {"entity_id": "binary_sensor.d", "state": "on"})
    assert DB.is_ring({"entity_id": "event.d", "state": "2026-01-01T10:00"}, {"entity_id": "event.d", "state": "2026-01-01T10:01"})
    assert not DB.is_ring(None, {"entity_id": "event.d", "state": "2026"})


def test_doorbell_ring_forwards_and_ducks(tmp_path):
    vols, played, ch = [60], [], []
    d = DB.Doorbell({"announce": played.append, "get_volume": lambda: vols[-1], "set_volume": vols.append,
                     "peers": lambda: PEERS, "changed": lambda: ch.append(1), "make_tone": IC.make_tone, "tmpdir": str(tmp_path)},
                    str(tmp_path / "db.json"))
    d.save({"enabled": True, "seconds": 5, "ha_token": "abc", "ha_url": "http://ha", "camera_entity": "camera.dor"})
    assert DB.masked(d.cfg)["ha_token"] == "••••••" and json.load(open(tmp_path / "db.json"))["ha_token"] == "abc"
    fwd = []
    assert d.ring(forward=fwd.append)["ok"] and fwd == [p["base"] for p in PEERS] and ch
    assert d.ring(forward=fwd.append).get("ignored")   # nytt trykk rett etter
    d._stop.set(); d.busy.acquire(); d.busy.release()
    d._play()
    assert played and played[-1].endswith("skjold-doorbell.wav") and min(vols) < 60
    st = d.status()
    assert st and st["camera"]
    req = DB.camera_request(d.cfg)
    assert req.full_url == "http://ha/api/camera_proxy/camera.dor" and req.get_header("Authorization") == "Bearer abc"


# ---------- rutiner ----------
def test_routine_templates_and_clean():
    r = RT.clean_routine(RT.TEMPLATES[0])
    assert r["id"] == "morgen" and r["steg"][2]["verdi"] == 25
    try:
        RT.clean_step({"type": "selvdestruksjon"})
        raise AssertionError
    except ValueError:
        pass


def test_run_steps_order_rooms_and_wait(tmp_path):
    done, sent, slept = [], [], []
    rt = RT.Routines({"do": lambda s: done.append(s["type"]), "peers": lambda: PEERS, "names": lambda: {"stue"}}, str(tmp_path / "r.json"))
    steg = [{"type": "volume", "verdi": 10}, {"type": "power", "verdi": True, "rom": "Kjøkken"},
            {"type": "preset", "verdi": 1, "rom": "Kjøkken"}, {"type": "wait", "verdi": 5},
            {"type": "night", "verdi": True, "rom": "Stue"}, {"type": "volume", "verdi": 3, "rom": "Garasje"}]
    log = rt.run_steps([RT.clean_step(s) for s in steg], sleep=slept.append, send=lambda base, st: sent.append((base, [s["type"] for s in st])))
    assert done == ["volume", "night"] and slept == [5]
    assert sent == [("http://10.0.0.2:8765", ["power", "preset"])]   # vent skjer her, før stue-steget
    assert any("Garasje" in l for l in log)


def test_routines_crud(tmp_path):
    rt = RT.Routines({"do": lambda s: None, "peers": lambda: [], "names": lambda: set()}, str(tmp_path / "r.json"))
    assert {r["id"] for r in rt.load()} == {"morgen", "leggetid"}
    rt.save({"navn": "Fest på kjøkkenet", "steg": [{"type": "volume", "verdi": 60}]})
    assert rt.find("fest-pa-kjokkenet")["navn"] == "Fest på kjøkkenet" and rt.find("Fest på kjøkkenet")
    rt.delete("morgen")
    assert not rt.find("morgen")
    assert rt.run("fest-pa-kjokkenet", background=False)["ok"]


# ---------- trygg oppdatering ----------
def test_snapshot_and_rollback_on_failed_healthcheck(tmp_path, monkeypatch):
    f = tmp_path / "bin" / "ki_amp_daemon.py"; f.parent.mkdir(); f.write_text("v1")
    webapp = tmp_path / "webapp"; webapp.mkdir(); (webapp / "index.html").write_text("gammel")
    root = tmp_path / "rb"; root.mkdir()
    monkeypatch.setattr(SU, "UPD_LOG", str(tmp_path / "upd.log"))
    snap = SU.snapshot("", root=str(root), files=[str(f)], dirs=[str(webapp)])
    assert os.path.exists(root / "pending.json")
    f.write_text("v2 som ikke starter"); (webapp / "index.html").write_text("ny")
    restored = []

    def do_restore(d):
        base = os.path.join(d, "files")
        for dp, _ds, ns in os.walk(base):
            for n in ns:
                src = os.path.join(dp, n)
                dst = "/" + os.path.relpath(src, base)
                with open(src) as a, open(dst, "w") as b:
                    b.write(a.read())
        restored.append(d)
    res = SU.check(timeout=0.01, root=str(root), probe=lambda: (False, "svarer ikke på /api/status"), do_restore=do_restore, sleep=lambda s: None)
    assert res.startswith("rullet tilbake") and restored == [snap]
    assert f.read_text() == "v1" and (webapp / "index.html").read_text() == "gammel"
    assert not os.path.exists(root / "pending.json")
    assert "SKJOLD-RESULTAT: rullet tilbake" in (tmp_path / "upd.log").read_text()


def test_healthy_check_clears_pending(tmp_path):
    root = tmp_path / "rb"; root.mkdir()
    (root / "pending.json").write_text(json.dumps({"snapshot": str(root / "x")}))
    assert SU.check(timeout=5, root=str(root), probe=lambda: (True, ""), sleep=lambda s: None) == "ok"
    assert SU.check(root=str(root)) == "ingen"
