"""Rettelser fra gjennomgangen før lansering: opphav (Origin), hemmeligheter i status, maks volum, atomisk lagring,
AirPlay som spiller bak en annen kilde, og standby på AUX/USB.

Kjør:  python3 -m unittest pi.tests.test_herding -v
"""
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import ki_amp_daemon as d  # noqa: E402


class Req:
    def __init__(self, origin=None, host="skjold-stue.local:8765", method="POST"):
        self.headers = {"Origin": origin} if origin else {}
        self.host, self.method = host, method


class Origin(unittest.TestCase):
    def test_tillatt(self):
        for o in (None, "http://skjold-stue.local:8765", "capacitor://localhost", "https://localhost", "http://localhost:4173",
                  "http://10.69.1.97:8765", "http://192.168.1.20", "http://homeassistant.local:8123", "http://homeassistant:8123",
                  "http://[fe80::1]:8765"):
            self.assertTrue(d._origin_ok(Req(o)), o)

    def test_fremmed_nettside_avvises(self):
        for o in ("https://ond.example.com", "http://8.8.8.8", "https://skjold-stue.local.example.com", "null"):
            self.assertFalse(d._origin_ok(Req(o)), o)

    def test_egen_liste(self):
        with mock.patch.object(d, "CORS_EXTRA", {"https://ha.mitt-domene.no"}):
            self.assertTrue(d._origin_ok(Req("https://ha.mitt-domene.no")))


class Hemmeligheter(unittest.TestCase):
    def test_status_uten_passord_og_tokens(self):
        s = {"vmax": 1, "ndUrl": "http://nas:4533", "ndUser": "per", "ndPass": "hemmelig", "plexToken": "t", "ytmCookie": "c",
             "maToken": "m", "plugins": {"mqtt": {"password": "p"}}}
        with mock.patch.dict(d.state, {"settings": s}):
            pub = d.public_settings()
            st = json.dumps(d.read_status())
        self.assertEqual(pub, {"vmax": 1, "ndUrl": "http://nas:4533", "ndUser": "per"})
        for hem in ("hemmelig", "plexToken", "ytmCookie", "maToken"):
            self.assertNotIn(hem, st)


class Volum(unittest.TestCase):
    def test_maks_volum_gjelder_alle_veier(self):
        with mock.patch.dict(d.state, {"settings": {**d.state.get("settings", {}), "vmax": 3}, "volume": 20}), \
                mock.patch.object(d, "apply_volume"), mock.patch.object(d, "changed"):
            d.set_volume(100)
            self.assertEqual(d.state["volume"], 70)


class Lagring(unittest.TestCase):
    def test_atomisk_og_bare_ved_endring(self):
        t = tempfile.mkdtemp(prefix="ki-st-")
        fil = os.path.join(t, "state.json")
        with mock.patch.object(d, "STATE_FILE", fil), mock.patch.object(d, "_saved_state", [""]):
            d.save_state()
            self.assertTrue(json.load(open(fil))["input"])
            self.assertFalse(os.path.exists(fil + ".tmp"))
            m = os.stat(fil).st_mtime_ns
            with mock.patch.object(d.os, "replace") as rep:
                d.save_state()          # ingen endring → ingen skriving (sparer SD-kortet)
                rep.assert_not_called()
            self.assertEqual(os.stat(fil).st_mtime_ns, m)


class Kildebytte(unittest.TestCase):
    def test_airplay_bak_radio_pauses(self):
        kall = []
        with mock.patch.object(d, "read_raw", return_value={"playing": True, "source": "airplay"}), \
                mock.patch.object(d, "read_status", return_value={"playing": False, "source": "radio"}), \
                mock.patch.object(d, "_busctl", side_effect=lambda *a: kall.append(a)), \
                mock.patch.object(d.threading, "Thread"), \
                mock.patch.dict(d.lyr.info, {"mode": "stop"}), mock.patch.dict(d.spotify, {"playing": False}), \
                mock.patch.dict(d.plex, {"playing": False}):
            d._pause_others("radio")
        self.assertTrue(any(a[-1] == "Pause" and a[1] == d.SPS[0] for a in kall), kall)

    def test_airplay_valgt_pauses_ikke(self):
        kall = []
        with mock.patch.object(d, "read_raw", return_value={"playing": True, "source": "airplay"}), \
                mock.patch.object(d, "read_status", return_value={"playing": True, "source": "airplay"}), \
                mock.patch.object(d, "_busctl", side_effect=lambda *a: kall.append(a)), \
                mock.patch.dict(d.lyr.info, {"mode": "stop"}), mock.patch.dict(d.spotify, {"playing": False}), \
                mock.patch.dict(d.plex, {"playing": False}):
            d._pause_others("airplay")
        self.assertEqual(kall, [])



class UgyldigKropp(unittest.TestCase):
    """Ødelagt eller uventet innhold i en forespørsel gir 400 med forklaring, ikke 500."""

    def kjor(self, handler, method="POST"):
        import asyncio

        class R:
            path, headers, host = "/api/x", {}, "skjold.local:8765"
        R.method = method
        return asyncio.run(d.cors_mw(R(), handler))

    def test_odelagt_json(self):
        async def h(_r):
            return json.loads("{ikke json")
        resp = self.kjor(h)
        self.assertEqual(resp.status, 400)
        self.assertIn("ugyldig JSON", resp.text)

    def test_manglende_felt_og_feil_type(self):
        async def mangler(_r):
            return {}["volume"]

        async def liste(_r):
            return [].get("x")
        self.assertEqual(self.kjor(mangler).status, 400)
        self.assertIn("mangler", self.kjor(mangler).text)
        self.assertEqual(self.kjor(liste).status, 400)

    def test_lesing_skjuler_ikke_feil(self):
        async def h(_r):
            return {}["x"]
        with self.assertRaises(KeyError):          # en feil i en GET er vår egen, og skal synes i loggen som før
            self.kjor(h, "GET")

if __name__ == "__main__":
    unittest.main()
