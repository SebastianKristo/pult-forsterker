"""Sikkerhetsmodus, sanglek, lydbøker (Audiobookshelf), køhistorikk, bass management og AirPlay-ID."""
import os
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import skjold_abs as ab          # noqa: E402
import skjold_airplay as ap      # noqa: E402
import skjold_bassmgmt as bm     # noqa: E402
import skjold_qhist as qh        # noqa: E402
import skjold_quiz as qz         # noqa: E402
import skjold_security as sec    # noqa: E402


# ---------- sikkerhetsmodus ----------
def _sec_ctx(log, power=False, vol=20):
    st = {"power": power, "vol": vol}
    return st, {"get_power": lambda: st["power"], "set_power": lambda on: (st.__setitem__("power", on), log.append(("power", on))),
                "get_volume": lambda: st["vol"], "set_volume": lambda v: (st.__setitem__("vol", v), log.append(("vol", v))),
                "announce": lambda src: (log.append(("ann", os.path.basename(str(src)))), time.sleep(0.02)),
                "say": lambda t: "/tmp/tale.wav", "post": lambda url, body: log.append(("post", url, body["action"]))}


def test_security_krever_paa(tmp_path):
    log = []
    _, ctx = _sec_ctx(log)
    s = sec.Security(ctx, str(tmp_path / "s.json"), sound_dir=str(tmp_path))
    assert s.trigger({})["ok"] is False and not log


def test_security_utloser_fra_standby_og_gjenoppretter(tmp_path):
    log = []
    st, ctx = _sec_ctx(log)
    s = sec.Security(ctx, str(tmp_path / "s.json"), sound_dir=str(tmp_path), sleep=lambda x: time.sleep(0.01))
    s.sett({"på": True, "rom": ["http://kjokken:8765"], "volum": 90})
    assert s.trigger({"grunn": "dør"})["ok"]
    time.sleep(0.2)
    assert s.active and st["power"] and st["vol"] == 90
    assert ("post", "http://kjokken:8765/api/security", "trigger") in log
    assert any(x[0] == "ann" and "sirene" in x[1] for x in log) and ("ann", "tale.wav") in log
    s.stop()
    for _ in range(50):
        if not s.active:
            break
        time.sleep(0.05)
    assert not s.active and st["vol"] == 20 and st["power"] is False
    assert ("post", "http://kjokken:8765/api/security", "stop") in log


def test_siren_wav(tmp_path):
    p = sec.siren_wav(str(tmp_path / "s.wav"), secs=0.2)
    assert os.path.getsize(p) > 0.2 * 48000 * 4


# ---------- sanglek ----------
def test_quiz_poeng():
    assert qz.poeng("Linkin Park – Numb", "Linkin Park", "Numb") == 2
    assert qz.poeng("numb linkin park", "Linkin Park", "Numb") == 2
    assert qz.poeng("linkn park", "Linkin Park", "Numb") == 1
    assert qz.poeng("Coldplay", "Linkin Park", "Numb") == 0
    assert qz.poeng("Something Just Like This", "The Chainsmokers & Coldplay", "Something Just Like This (feat. Coldplay)") >= 1


def test_quiz_runde():
    played, paused = [], threading.Event()
    songs = [{"title": f"Låt {i}", "artist": "Artist", "album": "A", "cover": "", "url": f"http://x/{i}", "duration": 200} for i in range(5)]
    q = qz.Quiz({"songs": lambda *a: songs, "play": lambda url, t, c, start: played.append((url, start)), "pause": paused.set})
    q.handle({"action": "bli_med", "navn": "Ola"})
    st = q.handle({"action": "start", "runder": 3, "sekunder": 5})
    assert st["aktiv"] and st["runder"] == 3
    q.handle({"action": "spill"})
    assert played and 20 <= played[0][1] <= 200 - 10
    cur = q.songs[0]
    q.handle({"action": "svar", "spiller": "Ola", "svar": f"{cur['artist']} - {cur['title']}"})
    st = q.handle({"action": "vis"})
    assert st["svar"]["tittel"] == cur["title"] and st["spillere"][0]["poeng"] == 2
    st = q.handle({"action": "vis"})                       # vis to ganger gir ikke dobbelt poeng
    assert st["spillere"][0]["poeng"] == 2
    q.handle({"action": "slutt"})


def test_subsonic_songs():
    calls = []
    def call(m, **p):
        calls.append((m, p))
        return {"randomSongs": {"song": [{"id": "1", "title": "T", "artist": "A", "coverArt": "c1", "duration": 180}]}}
    r = qz.subsonic_songs(call, lambda i: "http://nd/" + i, lambda c: "http://cov/" + c, "tiår", tiar=1990, n=5)
    assert r[0]["url"] == "http://nd/1" and r[0]["cover"] == "http://cov/c1"
    assert calls[0][1]["fromYear"] == 1990 and calls[0][1]["toYear"] == 1999


# ---------- lydbøker ----------
class _FakeAbs:
    def __init__(self, url, token):
        self.url, self.saved = url, []

    def book(self, item_id):
        files = [{"url": "http://abs/f1?token=t", "start": 0.0, "varighet": 1000.0},
                 {"url": "http://abs/f2?token=t", "start": 1000.0, "varighet": 1000.0}]
        return {"id": item_id, "tittel": "Bok", "forfatter": "F", "varighet": 2000.0, "cover": "", "filer": files,
                "kapitler": [{"tittel": "Kap 1", "start": 0, "slutt": 900}, {"tittel": "Kap 2", "start": 900, "slutt": 2000}],
                "sist_tid": 1200.0, "progresjon": 0.6}

    def save_progress(self, item_id, cur, dur):
        _FakeAbs.last = (item_id, round(cur), dur)


def test_abs_fortsett_og_sovetimer(tmp_path):
    pos = {"url": None, "pos": 0.0}
    played, queued, paused = [], [], []
    ctx = {"play": lambda u, t, c, s: (played.append((u, s)), pos.update(url=u, pos=s)),
           "queue": lambda u, t: queued.append(u), "position": lambda: (pos["url"], pos["pos"]),
           "pause": lambda: paused.append(1), "playing": lambda: True}
    a = ab.Audiobooks(ctx, str(tmp_path / "abs.json"), client_factory=_FakeAbs)
    a.sett({"url": "abs.local:13378", "token": "t"})
    assert a.cfg["url"] == "http://abs.local:13378"
    a.play("bok1")
    assert played == [("http://abs/f2?token=t", 200.0)] and queued == []      # fortsetter i fil 2, 200 s inn
    assert a.now()["kapittel"] == "Kap 2"
    a.tick(now=time.time())
    assert _FakeAbs.last == ("bok1", 1200, 2000.0)
    pos["url"], pos["pos"] = "http://abs/f1?token=x", 850.0
    a.set_sleep("kapittel")
    assert a.sleep["slutt"] == 900
    pos["pos"] = 900.0
    a.tick()
    assert paused and a.sleep is None


def test_abs_locate():
    files = [{"start": 0, "varighet": 10}, {"start": 10, "varighet": 10}]
    assert ab.locate(files, 15) == (1, 5) and ab.locate(files, 3) == (0, 3) and ab.locate(files, 99) == (1, 89)


# ---------- køhistorikk ----------
def test_qhist_kveld_over_midnatt_og_okter():
    base = 1_700_000_000          # 2023-11-14 22:13:20 UTC
    items = [{"t": base, "rom": "Stue", "title": "A", "artist": "X", "input": "lms"},
             {"t": base + 600, "rom": "Stue", "title": "B", "artist": "X", "input": "lms"},
             {"t": base + 3 * 3600, "rom": "Stue", "title": "C", "artist": "X", "input": "lms"},   # 01:13 neste dag
             {"t": base + 60, "rom": "Kjøkken", "title": "NRK P3", "url": "http://nrk/p3", "input": "radio"},
             {"t": base + 120, "rom": "Kjøkken", "title": "NRK P3 låt 2", "url": "http://nrk/p3", "input": "radio"}]
    f = qh.filtrer(items, dag="2023-11-14", fra="18:00", til="02:00", tz_offset_s=0)
    assert len(f) == 5
    assert len(qh.filtrer(items, dag="2023-11-14", fra="18:00", til="02:00", rom="Stue", tz_offset_s=0)) == 3
    ok = qh.okter(f)
    stue = [o for o in ok if o["rom"] == "Stue"]
    assert len(stue) == 2 and len(stue[0]["spor"]) == 2          # 3 t pause = ny økt
    kj = [o for o in ok if o["rom"] == "Kjøkken"][0]
    assert len(qh.unike_spor(kj["spor"])) == 1                   # samme radiokanal = én
    assert qh.spillbar(kj["spor"][0])["type"] == "url"
    assert qh.spillbar(items[0])["type"] == "sok"


# ---------- bass management ----------
def test_bass_finner_forsinkelse_fase_og_niva():
    m, s = bm._sim(sub_delay_ms=-5.0)            # sub-en kommer 5 ms for tidlig → forsink sub-en
    r = bm.analyze(m, s)
    assert r["sub_phase"] == 0 and abs(r["sub_fine_ms"] - 5.0) <= 0.3 and r["main_delay_ms"] == 0
    assert r["flatness_db"] < r["flatness_before_db"]
    m, s = bm._sim(sub_delay_ms=0.0, invert=True, sub_gain_db=-6)
    r = bm.analyze(m, s)
    assert r["sub_phase"] == 180 and r["sub_fine_ms"] <= 0.3 and 4 <= r["sub_level"] <= 6
    m, s = bm._sim(sub_delay_ms=4.0)             # sub-en kommer for sent → hovedenheten må forsinkes
    r = bm.analyze(m, s)
    assert r["sub_fine_ms"] == 0 and abs(r["main_delay_ms"] - 4.0) <= 0.3
    assert len(r["freqs"]) == len(r["after"]) == len(r["before"])


def test_bass_slot_irs():
    import numpy as np
    import skjold_placement as pl
    sw = pl.sweep()
    rec = np.zeros(int((0.5 + 2 * pl.SLOT_S + 1.0) * pl.SR))
    for i, (a, _b) in enumerate(pl.sequence_signal(2)):
        k = int(a * pl.SR) + 48 * (1 + 3 * i)
        rec[k:k + len(sw)] += sw[:len(rec) - k]
    irs = bm.slot_irs(rec, 2)
    assert len(irs) == 2
    assert abs(int(np.argmax(np.abs(irs[0]))) - 48) <= 2 and abs(int(np.argmax(np.abs(irs[1]))) - 192) <= 2


# ---------- AirPlay ----------
def test_airplay_id_unik_og_settes_inn():
    a = ap.device_id("m1", "aa:bb:cc:dd:ee:01", "stue")
    b = ap.device_id("m1", "aa:bb:cc:dd:ee:02", "stue")
    assert a != b and a.startswith("0x") and len(a) == 14 and int(a[2:4], 16) & 0x02 and not int(a[2:4], 16) & 0x01
    conf = 'general =\n{\n  name = "Stue";\n};\nalsa =\n{\n};\n'
    c2 = ap.ensure_id(conf, a)
    assert ap.current_id(c2) == a and c2.count("airplay_device_id") == 1 and 'name = "Stue"' in c2
    c3 = ap.ensure_id(c2, b)
    assert ap.current_id(c3) == b and c3.count("airplay_device_id") == 1
    repo = open(os.path.join(os.path.dirname(__file__), "..", "shairport-sync.conf")).read()
    assert ap.current_id(ap.ensure_id(repo, a)) == a
