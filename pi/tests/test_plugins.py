"""Tester for plugin-delen av ki_amp_daemon.py (sovetimer, vekkerklokke, volumtak, sangtekster, barnerom, romkorreksjon).

Kjør:  python3 -m unittest discover -s pi/tests -v
"""
import os
import sys
import tempfile
import time
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402


def tm(y=2026, mo=11, da=9, h=7, mi=0):
    return time.strptime(f"{y}-{mo:02d}-{da:02d} {h:02d}:{mi:02d}", "%Y-%m-%d %H:%M")   # 9.11.2026 er en mandag


class TestAlarm(unittest.TestCase):
    def test_gaar_paa_riktig_tid_og_dag_en_gang(self):
        a = {"time": "07:00", "days": [0, 1, 2, 3, 4], "id": "a0"}
        fired = set()
        k = d.alarm_due(a, tm(), fired)
        self.assertTrue(k)
        fired.add(k)
        self.assertIsNone(d.alarm_due(a, tm(), fired))          # samme minutt: bare én gang
        self.assertIsNone(d.alarm_due(a, tm(mi=1), set()))       # feil minutt
        self.assertIsNone(d.alarm_due(a, tm(da=14), set()))      # lørdag
        self.assertTrue(d.alarm_due({**a, "days": []}, tm(da=14), set()))   # ingen dager = hver dag
        self.assertIsNone(d.alarm_due({**a, "on": False}, tm(), set()))
        self.assertIsNone(d.alarm_due({**a, "time": "7:00"}, tm(), set()))


class TestSovetimer(unittest.TestCase):
    def test_fade_siste_minutt(self):
        self.assertEqual(d.sleep_fade_volume(40, 120), 40)
        self.assertEqual(d.sleep_fade_volume(40, 60), 40)
        self.assertEqual(d.sleep_fade_volume(40, 30), 20)
        self.assertEqual(d.sleep_fade_volume(40, 0), 0)
        self.assertEqual(d.sleep_fade_volume(40, -5), 0)


class TestVolumtak(unittest.TestCase):
    def test_vindu_over_midnatt(self):
        self.assertTrue(d.in_window("23:30", "22:00", "07:00"))
        self.assertTrue(d.in_window("03:00", "22:00", "07:00"))
        self.assertFalse(d.in_window("07:00", "22:00", "07:00"))
        self.assertFalse(d.in_window("12:00", "22:00", "07:00"))
        self.assertTrue(d.in_window("13:00", "12:00", "14:00"))
        self.assertFalse(d.in_window("13:00", "12:00", "12:00"))
        self.assertFalse(d.in_window("13:00", "x", "14:00"))


class TestSangtekster(unittest.TestCase):
    def test_lrc_og_lrclib(self):
        lrc = "[00:12.50]Første linje\n[00:15.00][01:15.00]Refreng\nikke en linje\n[02:00]Siste"
        p = d.parse_lrc(lrc)
        self.assertEqual([x["t"] for x in p], [12.5, 15.0, 75.0, 120.0])
        self.assertEqual(p[1]["l"], "Refreng")
        r = d.lyrics_from_lrclib({"plainLyrics": "", "syncedLyrics": lrc, "instrumental": False})
        self.assertTrue(r["found"])
        self.assertIn("Første linje", r["plain"])
        self.assertFalse(d.lyrics_from_lrclib(None)["found"])

    def test_cache_og_404(self):
        import urllib.error
        kall = []

        def falsk(req, timeout=0):
            kall.append(req.full_url)
            raise urllib.error.HTTPError(req.full_url, 404, "nf", {}, None)
        gammel = d.urllib.request.urlopen
        d.urllib.request.urlopen = falsk
        try:
            r1 = d.fetch_lyrics("Ukjent", "Ingenting", 200)
            r2 = d.fetch_lyrics("ukjent", "ingenting", 200)
        finally:
            d.urllib.request.urlopen = gammel
        self.assertFalse(r1["found"])
        self.assertEqual(r1, r2)
        self.assertEqual(len(kall), 1)
        self.assertIn("duration=200", kall[0])


class TestScrobble(unittest.TestCase):
    def test_regel_og_signatur(self):
        self.assertFalse(d.scrobble_due(60, 200))
        self.assertTrue(d.scrobble_due(100, 200))
        self.assertTrue(d.scrobble_due(240, 900))
        self.assertFalse(d.scrobble_due(20, 25))
        self.assertTrue(d.scrobble_due(240, 0))
        self.assertEqual(d.lastfm_sig({"b": "2", "a": "1", "format": "json"}, "s"),
                         __import__("hashlib").md5(b"a1b2s").hexdigest())


class TestPluginInnstillinger(unittest.TestCase):
    def setUp(self):
        self._st = dict(d.state.get("settings") or {})
        d.save_state = lambda: None

    def tearDown(self):
        d.state["settings"] = self._st

    def test_lagres_og_valideres(self):
        d.state["settings"] = {}
        d.plugin_update("nightcap", {"enabled": True, "start": "23:00", "max": "20"})
        c = d.plug_cfg("nightcap")
        self.assertTrue(c["enabled"]); self.assertEqual(c["max"], 20); self.assertEqual(c["start"], "23:00")
        with self.assertRaises(ValueError):
            d.plugin_update("nightcap", {"start": "25:00"})
        with self.assertRaises(ValueError):
            d.plugin_update("spotty", {"enabled": True})
        with self.assertRaises(KeyError):
            d.plugin_update("finnes-ikke", {})
        self.assertEqual(d.nightcap_limit("23:30"), 20)
        self.assertIsNone(d.nightcap_limit("12:00"))

    def test_barnerom_pin_og_maskering(self):
        d.state["settings"] = {}
        d.plugin_update("kids", {"enabled": True, "pin": "4321", "max": 30, "inputs": ["radio", "finnes-ikke"], "presets": [2, 1, 99]})
        c = d.plug_cfg("kids")
        self.assertEqual(c["inputs"], ["radio"]); self.assertEqual(c["presets"], [1, 2])
        with self.assertRaises(ValueError):
            d.plugin_update("kids", {"enabled": False, "pin_check": "0000"})
        pl = {p["id"]: p for p in d.plugins_payload()["plugins"]}
        self.assertEqual(pl["kids"]["cfg"]["pin"], "••••••")
        d.plugin_update("kids", {"enabled": False, "pin_check": "4321", "pin": "••••••"})
        self.assertFalse(d.plug_cfg("kids")["enabled"]); self.assertEqual(d.plug_cfg("kids")["pin"], "4321")

    def test_romkorreksjon_grenser_og_dsp(self):
        d.state["settings"] = {}
        d.dsp.update = lambda: None
        d.plugin_update("roomeq", {"enabled": True, "filters": [{"f": 55, "q": 5, "g": -14}, {"f": 120, "q": 3, "g": 6}, {"f": 1000, "q": 2, "g": -3}]})
        self.assertEqual(d.roomeq_filters(), [(55.0, 5.0, -10.0), (120.0, 3.0, 3.0)])
        cfg = d.dsp_config()
        self.assertIn("rq0:", cfg); self.assertIn("rq1", cfg)
        import yaml
        yaml.safe_load(cfg)

    def test_hoyttalerprofil_dsp_og_romkorreksjon(self):
        import yaml
        d.state["settings"] = {}
        d.dsp.update = lambda: None
        d.plugin_update("speakers", {"enabled": True, "target": "tull", "profile": {
            "brand": "Dali", "model": "Oberon 3", "filters": [{"f": 150, "q": 2, "g": -4}, {"f": 3000, "q": 2, "g": 8}, {"x": 1}]}})
        c = d.plug_cfg("speakers")
        self.assertEqual(c["target"], "flat")
        self.assertEqual([f["g"] for f in c["profile"]["filters"]], [-4.0, 3.0])
        self.assertEqual(d.speaker_filters(), [(150.0, 2.0, -4.0), (3000.0, 2.0, 3.0)])
        cfg = yaml.safe_load(d.dsp_config())
        self.assertIn("sp1", cfg["filters"]); self.assertEqual(cfg["filters"]["pre"]["parameters"]["gain"], -3.0)
        d.plugin_update("roomeq", {"enabled": True, "filters": [{"f": 55, "q": 5, "g": -6}]})
        cfg = yaml.safe_load(d.dsp_config())
        names = cfg["pipeline"][0]["names"]
        self.assertEqual([n for n in names if n.startswith("sp")], ["sp0"])   # bassen eies av romkorreksjonen
        self.assertEqual(cfg["filters"]["sp0"]["parameters"]["freq"], 3000.0)

    def test_xtc_sync_sub_dsp(self):
        import tempfile, yaml
        from skjold_sync import dspblocks
        d.state["settings"] = {}
        d.dsp.update = lambda: None
        with self.assertRaises(ValueError):
            d.plugin_update("sync", {"sub_phase": 90})
        d.plugin_update("sync", {"enabled": True, "role": "leader", "buffer_ms": 900, "sub_mode": "main", "sub_xover": 40})
        c = d.plug_cfg("sync")
        self.assertEqual((c["buffer_ms"], c["sub_xover"]), (500, 60))
        cfg = yaml.safe_load(d.dsp_config())
        self.assertEqual(cfg["filters"]["sub_hp"]["parameters"]["order"], 4)
        self.assertEqual(cfg["filters"]["sync_delay"]["parameters"]["delay"], 500.0)
        d.plugin_update("sync", {"role": "follower", "sub_mode": "sub", "sub_phase": 180})
        x = dspblocks.extra({"enabled": True, "strength": 70}, d.plug_cfg("sync"), tempfile.mkdtemp())
        cfg = yaml.safe_load(d.dsp_config())
        self.assertTrue(cfg["filters"]["sub_gain"]["parameters"]["inverted"]); self.assertIn("sub_mono", cfg["mixers"])
        self.assertNotIn("xtc_d", x[0])   # sub-enheten bruker ikke romlig stereo
        d.state["settings"] = {}
        x = dspblocks.extra({"enabled": True, "strength": 70}, {}, tempfile.mkdtemp())
        y = yaml.safe_load("filters:" + x[0] + "\nmixers:" + x[1] + "\npipeline:\n" + "\n".join(x[2]))
        self.assertEqual(len(y["pipeline"]), 6)

    def test_sweep(self):
        x = d.log_sweep(dur=0.5, sr=8000)
        self.assertEqual(len(x), 4000)
        self.assertLessEqual(float(abs(x).max()), 0.5001)


if __name__ == "__main__":
    unittest.main()
