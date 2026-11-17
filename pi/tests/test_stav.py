"""Skjold Stav: fjernkontrollen melder seg, Skjold husker den og sender tastene videre."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import skjold_stav as S  # noqa: E402


class TestStav(unittest.TestCase):
    def test_meld_og_tast(self):
        d = tempfile.mkdtemp(); hendelser = []
        st = S.Stav({"on_tast": hendelser.append}, os.path.join(d, "stav.json"))
        st.meld({"id": "AA:BB", "navn": "Stua", "batteri": 81, "lader": False, "versjon": "2026.10.2"})
        self.assertEqual(hendelser, [])
        r = st.meld({"id": "AA:BB", "tast": "ok", "type": "lang"})
        self.assertEqual(r["seq"], 1)
        c = st.config()["enheter"]["aa:bb"]
        self.assertEqual((c["navn"], c["batteri"], c["lader"], c["tast"]["knapp"], c["tast"]["type"], c["tilkoblet"]), ("Stua", 81, False, "ok", "lang", True))
        self.assertEqual(hendelser[0]["knapp"], "ok")
        st.meld({"id": "aa:bb", "tast": "vol_opp", "type": "gjenta"})   # gjentak: ingen hendelse
        self.assertEqual(len(hendelser), 1)
        # husket etter omstart (navn), batteri kommer ved neste melding
        st2 = S.Stav({}, os.path.join(d, "stav.json"))
        self.assertEqual(st2.config()["enheter"]["aa:bb"]["navn"], "Stua")
        self.assertEqual(st2.glem("AA:BB")["enheter"], {})

    def test_mangler_id(self):
        with self.assertRaises(ValueError):
            S.Stav({}, os.path.join(tempfile.mkdtemp(), "s.json")).meld({"batteri": 50})


if __name__ == "__main__":
    unittest.main()
