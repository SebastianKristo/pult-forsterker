"""Node: volumknotten blar i innstillingsmenyen i stedet for å endre volumet, og Skjermsparer finnes i menyen."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402


class TestKnottMeny(unittest.TestCase):
    def setUp(self):
        self.orig = (d.set_volume, d.write_ctrl, dict(d.smenu), dict(d._pot_menu))
        self.vol = []
        d.set_volume = lambda v, *a, **k: self.vol.append(v)
        d.write_ctrl = lambda *a, **k: None
        d._pot_menu.update(ref=None, last=None)

    def tearDown(self):
        d.set_volume, d.write_ctrl = self.orig[0], self.orig[1]
        d.smenu.clear(); d.smenu.update(self.orig[2]); d._pot_menu.clear(); d._pot_menu.update(self.orig[3])

    def test_knotten_blar_i_menyen(self):
        d.pot_volume(40)
        d.smenu.update(open=True, idx=0, until=0); self.vol.clear()
        d.pot_volume(43)                         # under ett hakk: ingenting
        self.assertEqual(d.smenu["idx"], 0)
        d.pot_volume(47)                         # ett hakk frem
        self.assertEqual(d.smenu["idx"], 1)
        d.pot_volume(39)                         # ett hakk tilbake
        self.assertEqual(d.smenu["idx"], 0)
        self.assertEqual(self.vol, [])           # volumet er urørt mens menyen er åpen

    def test_volum_når_menyen_er_lukket(self):
        d.smenu["open"] = False
        d.state["volume"] = 10
        d.pot_volume(30)
        self.assertEqual(self.vol, [30])

    def test_skjermsparer_i_menyen(self):
        k = [x[0] for x in d.SMENU_ITEMS]
        self.assertIn("saver", k)
        self.assertIn("saver", d.SETTINGS_DEF)


if __name__ == "__main__":
    unittest.main()
