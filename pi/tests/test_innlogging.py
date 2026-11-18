"""Delte innlogginger mellom Skjold-enhetene (pi/skjold_innlogging.py)."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_innlogging as I  # noqa: E402


def ytm(cookie, ts):
    return {"ytm": {"ts": ts, "data": {"ytmEn": bool(cookie), "ytmUser": "", "ytmCookie": cookie}}}


class Flett(unittest.TestCase):
    def test_nyeste_vinner(self):
        ta, send = I.flett(ytm("gammel", 100), ytm("ny", 200))
        self.assertEqual(ta["ytm"]["data"]["ytmCookie"], "ny"); self.assertEqual(send, set())
        ta, send = I.flett(ytm("ny", 200), ytm("gammel", 100))
        self.assertEqual(ta, {}); self.assertEqual(send, {"ytm"})

    def test_utlogging_deles_ogsaa(self):
        ta, _ = I.flett(ytm("cookie", 100), ytm("", 300))
        self.assertEqual(ta["ytm"]["data"]["ytmCookie"], "")

    def test_uten_tidsstempel_fylles_bare_det_som_mangler(self):
        ta, send = I.flett(ytm("", 0), ytm("deres", 0))
        self.assertEqual(ta["ytm"]["data"]["ytmCookie"], "deres")
        ta, send = I.flett(ytm("min", 0), ytm("deres", 0))
        self.assertEqual((ta, send), ({}, set()))                     # begge satt opp, ingen vet hvem som er nyest
        ta, send = I.flett(ytm("min", 0), ytm("", 0))
        self.assertEqual(send, {"ytm"})

    def test_tjenester_for_noklene(self):
        self.assertEqual(I.tjenester_for(["ndPass", "volume", "ytmCookie"]), {"nd", "ytm"})
        self.assertEqual(I.tjenester_for(["bass"]), set())


class Enhet(unittest.TestCase):
    def setUp(self):
        self.data = {t: {} for t in I.TJENESTER}
        self.tid = [1000.0]
        self.fil = os.path.join(tempfile.mkdtemp(), "delt.json")

    def ny(self):
        return I.Deling(self.fil, lambda t: dict(self.data[t]), lambda t, d: self.data[t].update(d), lambda: [],
                        lambda: "meg", aktiv=False, clock=lambda: self.tid[0])

    def test_endring_faar_tidsstempel_som_huskes(self):
        d = self.ny()
        self.data["nd"] = {"ndUrl": "http://nd:4533"}
        d.endret(["nd", "ukjent"])
        self.assertEqual(d.alle()["nd"]["ts"], 1000.0)
        self.assertEqual(self.ny().alle()["nd"]["ts"], 1000.0)          # lagret til fil

    def test_ta_imot_nyere_subwave(self):
        d = self.ny()
        nye = d.ta_imot({"subwave": {"ts": 5000, "data": {"enabled": True, "url": "https://radio.example", "password": "x"}}})
        self.assertEqual(nye, ["subwave"])
        self.assertEqual(self.data["subwave"]["url"], "https://radio.example")
        self.assertEqual(d.alle()["subwave"]["ts"], 5000)
        self.assertEqual(d.ta_imot({"subwave": {"ts": 4000, "data": {"url": "eldre"}}}), [])   # eldre: ignoreres
        self.assertEqual(self.data["subwave"]["url"], "https://radio.example")


if __name__ == "__main__":
    unittest.main()
