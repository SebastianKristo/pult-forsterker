"""Tester for smart radio, Oppdag-liste, vekkelys, tilstede-modus, plugin-butikk og helsesjekk.

Kjør:  python3 -m pytest -q pi/tests/test_smartradio_etc.py
"""
import io
import json
import os
import random
import shutil
import sys
import tempfile
import time
import unittest
import zipfile

HER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HER))
sys.path.insert(0, os.path.dirname(HER))

import numpy as np  # noqa: E402

import skjold_health as hl  # noqa: E402
import skjold_home_extras as hx  # noqa: E402
import skjold_pluginstore as ps  # noqa: E402
import skjold_smartradio as sr  # noqa: E402


def click(bpm, secs=20, rate=sr.SR):
    x = np.zeros(int(secs * rate), dtype=np.float32)
    step = 60.0 / bpm * rate
    n = 0
    while int(n * step) + 200 < len(x):
        i = int(n * step)
        x[i:i + 200] = np.hanning(200) * (1.0 if n % 4 == 0 else 0.6)
        n += 1
    return x


class TestSmartRadio(unittest.TestCase):
    def test_bpm_klikkspor(self):
        for bpm in (90, 120, 140):
            got = sr.bpm_of(click(bpm))
            ok = min(abs(got - bpm), abs(got * 2 - bpm), abs(got / 2 - bpm)) / bpm
            self.assertLess(ok, 0.04, f"{bpm} → {got}")

    def test_likhet(self):
        a = sr.features(click(120))
        b = sr.features(click(121))
        rnd = np.random.default_rng(1)
        noise = sr.features(rnd.uniform(-1, 1, sr.SR * 20).astype(np.float32))
        self.assertLess(sr.distance(a, b), sr.distance(a, noise))

    def test_velger_likeste_og_unngaar_artist_tre_ganger(self):
        cur = {"bpm": 120, "rms": 0.1, "centroid": 1000, "mfcc": [0] * 13}
        near = {"id": "1", "artist": "A", "feat": dict(cur)}
        far = {"id": "2", "artist": "B", "feat": {"bpm": 70, "rms": 0.5, "centroid": 5000, "mfcc": [5] * 13}}
        self.assertEqual(sr.choose_next(cur, [far, near], rnd=random.Random(0))["id"], "1")
        self.assertEqual(sr.choose_next(cur, [far, near], recent_artists=["A", "A"], rnd=random.Random(0))["id"], "2")
        self.assertEqual(sr.choose_next(cur, [far, near], recent_ids=["1"], rnd=random.Random(0))["id"], "2")


class TestOppdag(unittest.TestCase):
    def cands(self):
        return [{"id": f"{a}{i}", "artist": f"Artist {a}", "title": f"Låt {a}{i}",
                 "feat": {"bpm": 90 + i * 5, "rms": 0.1 + 0.01 * i, "centroid": 1000, "mfcc": [i] * 13}}
                for a in "ABCDEFGHIJKLMNOPQRST" for i in range(4)]

    def test_artistgrense_ingen_gjentak_og_spilte_fjernet(self):
        now = time.time()
        hist = [{"t": now - 10 * 86400, "artist": "Artist A", "title": "Låt A0"},
                {"t": now - 200 * 86400, "artist": "Artist B", "title": "Låt B0"}]
        c = self.cands() + [dict(self.cands()[0])]   # duplikat
        out = sr.select_discover(c, hist, now, size=35, rnd=random.Random(7))
        self.assertEqual(len(out), 35)
        self.assertEqual(len({x["id"] for x in out}), len(out))
        per = {}
        for x in out:
            per[x["artist"]] = per.get(x["artist"], 0) + 1
        self.assertLessEqual(max(per.values()), 2)
        self.assertNotIn("A0", [x["id"] for x in out])

    def test_seed_gir_samme_liste(self):
        now = time.time()
        a = sr.select_discover(self.cands(), [], now, rnd=random.Random(3))
        b = sr.select_discover(self.cands(), [], now, rnd=random.Random(3))
        self.assertEqual([x["id"] for x in a], [x["id"] for x in b])


class TestVekkelys(unittest.TestCase):
    def test_rampe(self):
        r = hx.wake_ramp(10, 20)
        self.assertEqual(r[0][1:], (1, 2200))
        self.assertEqual(r[-1], (600, 100, 4000))
        self.assertTrue(all(b1 <= b2 for (_, b1, _), (_, b2, _) in zip(r, r[1:])))
        self.assertEqual(hx.wake_ramp(10, 5)[1][0], 15)    # steg klemmes til 15–30 s

    def test_starter_foer_alarm_med_mock_ha(self):
        calls = []
        cfg = {"enabled": True, "alarms": [{"time": "07:00", "days": [], "on": True}],
               "light": {"enabled": True, "entities": ["light.soverom"], "minutes": 1, "step": 15, "ha_url": "", "ha_token": ""}}
        ctx = {"alarm_cfg": lambda: cfg, "ha_fallback": lambda: {"ha_url": "http://ha:8123", "ha_token": "abc"}, "power": lambda: False}
        wl = hx.WakeLight(ctx, call=lambda *a: calls.append(a))
        alarm = hx.next_alarm_epoch(cfg["alarms"][0], time.time())
        started = []
        wl.start = lambda t, lc: started.append((t, lc))
        wl.tick(now=alarm - 30)
        self.assertEqual(len(started), 1)
        self.assertEqual(started[0][1]["ha_token"], "abc")
        wl.tick(now=alarm - 20)          # ikke to ganger
        self.assertEqual(len(started), 1)
        # selve rampa mot mock-HA (rask: alarm om 0 s → én kort rampe), og stopp
        wl2 = hx.WakeLight(ctx, call=lambda *a: calls.append(a))
        wl2.start(time.time() + 1, {**cfg["light"], "ha_url": "http://ha:8123", "ha_token": "abc"})
        time.sleep(1.5)
        wl2.stop()
        self.assertTrue(calls)
        url, tok, dom, svc, data = calls[0]
        self.assertEqual((dom, svc, data["entity_id"]), ("light", "turn_on", "light.soverom"))
        self.assertEqual(data["brightness_pct"], 1)


class TestTilstede(unittest.TestCase):
    def test_plan_er_deterministisk_og_innenfor_vindu(self):
        c = {"start": "07:00", "end": "23:00", "rooms": ["Stue", "Kjøkken"], "rotate": True}
        a = hx.plan_presence("2026-11-09", c, seed=4)
        self.assertEqual(a, hx.plan_presence("2026-11-09", c, seed=4))
        self.assertNotEqual(a, hx.plan_presence("2026-11-10", c, seed=4))
        self.assertTrue(a)
        for s in a:
            self.assertGreaterEqual(s["start"], 7 * 60)
            self.assertLessEqual(s["end"], 23 * 60)
            self.assertLessEqual(s["end"] - s["start"], 60)
        for x, y in zip(a, a[1:]):
            self.assertGreaterEqual(y["start"] - x["end"], 15)
        self.assertEqual({s["room"] for s in a}, {"Stue", "Kjøkken"})


class TestRadioListe(unittest.TestCase):
    def test_fuzzy(self):
        songs = [{"id": "1", "title": "Take On Me (2015 Remaster)", "artist": "a-ha"}, {"id": "2", "title": "Hunting High and Low", "artist": "a-ha"}]
        s, _ = hx.best_match({"title": "Take on me", "artist": "A-HA"}, songs)
        self.assertEqual(s["id"], "1")
        self.assertIsNone(hx.best_match({"title": "Bohemian Rhapsody", "artist": "Queen"}, songs)[0])
        self.assertIn("#EXTINF:225,a-ha - Take On Me", hx.m3u([{"title": "Take On Me", "artist": "a-ha", "duration": 225}]))


class TestPluginButikk(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.st = ps.Store(self.root, "0.2.0", fetch=self.fake_fetch, index_url="mem://index.json", raw_base="mem://")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def fake_fetch(self, url):
        if url == "mem://index.json":
            return open(os.path.join(REPO, "plugins", "index.json"), "rb").read()
        rel = url.split("/plugins/", 1)[1] if "/plugins/" in url else url[len("mem://"):]
        return open(os.path.join(REPO, "plugins", rel), "rb").read()

    def test_manifest(self):
        m = json.load(open(os.path.join(REPO, "plugins", "hvit-stoy", "plugin.json")))
        self.assertEqual(ps.validate_manifest(m, "0.2.0"), [])
        self.assertTrue(ps.validate_manifest({**m, "id": "Ugyldig ID"}))
        self.assertTrue(ps.validate_manifest({**m, "tillatelser": ["root"]}))
        self.assertTrue(ps.validate_manifest({**m, "entry": "../x.py"}))
        self.assertIn("krever Skjold 9.0 eller nyere", ps.validate_manifest({**m, "minSkjold": "9.0"}, "0.2.0"))

    def test_katalog_install_sha_og_fjern(self):
        cat = self.st.catalog()
        self.assertEqual({p["id"] for p in cat["plugins"]}, {"vaer-for-nyheter", "hvit-stoy", "dagens-lat"})
        self.st.install_from_catalog("dagens-lat")
        self.assertEqual([m["id"] for m in self.st.installed()], ["dagens-lat"])
        self.assertEqual(self.st.catalog()["plugins"][0]["installed"], "1.0.0")
        res = self.st.run("dagens-lat", "test")
        self.assertEqual(res["actions"], [{"navidrome_random": True}])
        due = self.st.due_schedules(time.strptime("2026-11-09 08:00", "%Y-%m-%d %H:%M"))
        self.assertEqual(due, [("dagens-lat", "tick")])
        self.st.remove("dagens-lat")
        self.assertEqual(self.st.installed(), [])

    def test_feil_sha_avvises(self):
        good = self.fake_fetch
        self.st.fetch = lambda u: (b"tuklet" if u.endswith("main.py") else good(u))
        with self.assertRaises(ValueError):
            self.st.install_from_catalog("hvit-stoy")

    def zipped(self, files):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            for n, c in files.items():
                z.writestr(n, c)
        return b.getvalue()

    def manifest(self, **kw):
        return json.dumps({"id": "test-plugin", "navn": "Test", "versjon": "1.0.0", "forfatter": "t", "beskrivelse": "t",
                           "entry": "main.py", "tillatelser": [], **kw})

    def test_sandkasse_tidsgrense_og_tillatelser(self):
        code = ("import urllib.request\n"
                "def spin(d):\n"
                "    while True: pass\n"
                "def register(api):\n"
                "    api.on('loop', spin)\n"
                "    api.on('net', lambda d: urllib.request.urlopen('http://example.com'))\n"
                "    api.on('play', lambda d: api.play('http://x/y.mp3') or 'ok')\n")
        data = self.zipped({"pkg/plugin.json": self.manifest(), "pkg/main.py": code})
        self.st.install_zip(data, ps.sha256(data))
        old = ps.TIMEOUT
        try:
            r = ps.run_python(os.path.join(self.root, "test-plugin"), "main.py", "loop", {}, set(), timeout=2)
            self.assertIn("tidsgrense", r["error"])
        finally:
            ps.TIMEOUT = old
        self.assertIn("http", self.st.run("test-plugin", "net").get("error", ""))
        r = self.st.run("test-plugin", "play")
        self.assertEqual(r["result"], "ok")
        self.assertEqual(r["actions"], [])        # mangler tillatelsen audio → handlingen fjernes

    def test_zip_sti_utenfor_avvises(self):
        with self.assertRaises(ValueError):
            self.st.install_zip(self.zipped({"plugin.json": self.manifest(), "../ond.py": "x"}))
        with self.assertRaises(ValueError):
            self.st.install_zip(self.zipped({"plugin.json": self.manifest()}), "0" * 64)


class TestHelse(unittest.TestCase):
    def test_maskering(self):
        t = ('ha_token="eyJhbGciOi.abc" password: hemmelig url=http://bruker:pass@192.168.1.50:4533/rest?u=seb&p=x '
             'Authorization: Bearer abc.def ip 10.0.0.7 mac b8:27:eb:12:34:56 lokal 127.0.0.1')
        m = hl.mask_text(t)
        for bad in ("eyJhbGciOi", "hemmelig", "bruker:pass", "192.168.1", "abc.def", "10.0.0", "b8:27:eb", "u=seb"):
            self.assertNotIn(bad, m)
        self.assertIn("127.0.0.1", m)
        o = hl.mask_obj({"settings": {"ndPass": "x", "ndUser": "seb", "plugins": {"lastfm": {"secret": "s", "key": ""}}}, "ip": "192.168.0.2"})
        self.assertEqual(o["settings"]["ndPass"], "•••")
        self.assertEqual(o["settings"]["plugins"]["lastfm"]["secret"], "•••")
        self.assertEqual(o["ip"], "x.x.x.2")

    def test_vurdering(self):
        self.assertEqual(hl.assess_temp(55)["niva"], "ok")
        self.assertEqual(hl.assess_temp(74)["niva"], "advarsel")
        self.assertEqual(hl.assess_temp(85)["niva"], "feil")
        self.assertEqual(hl.assess_throttle("0x0")["niva"], "ok")
        self.assertEqual(hl.assess_throttle("0x50000")["niva"], "advarsel")
        self.assertEqual(hl.assess_throttle("0x50005")["niva"], "feil")
        self.assertEqual(hl.assess_pct("disk", "Lagring", 96, 85, 95, "Kortet")["niva"], "feil")
        self.assertEqual(hl.assess_service("camilladsp", "failed")["niva"], "feil")
        self.assertEqual(hl.assess_service("raspotify", "inactive")["niva"], "ok")
        self.assertEqual(hl.overall([hl.assess_temp(50), hl.assess_temp(75)]), "advarsel")

    def test_rapport_og_lenke(self):
        h = {"niva": "ok", "version": "skjold-v0.2", "items": [hl.assess_temp(50)], "errors": ["feil fra 192.168.1.9 token=abc"], "aplay": "card 0"}
        txt = hl.report_text(h)
        self.assertNotIn("192.168.1.9", txt)
        self.assertNotIn("token=abc", txt)
        self.assertTrue(hl.issue_link(txt).startswith(hl.ISSUE_URL + "?title="))
        self.assertIsInstance(hl.collect({}), dict)


if __name__ == "__main__":
    unittest.main()
