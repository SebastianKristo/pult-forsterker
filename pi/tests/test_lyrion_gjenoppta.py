"""Radio fortsetter av seg selv når Lyrion-serveren (f.eks. på S1) har vært borte en stund."""
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402


class TestGjenoppta(unittest.TestCase):
    def setUp(self):
        self.old = (dict(d.last_play), d.state.get("input"), d.state.get("power"), d.play_url, d.lyr.info, d.threading.Thread)
        self.spilt = []
        def spill(url, title="", art="", *a, **k):
            self.spilt.append((url, title)); d.lyr.info = {"mode": "play"}
        d.play_url = spill
        class T:   # kjør tråden med en gang
            def __init__(s, target=None, daemon=None): s.t = target
            def start(s): s.t()
        d.threading.Thread = T
        d.state["input"], d.state["power"] = "radio", True
        d.last_play.clear(); d.last_play.update(url="http://sw/stream.mp3", title="Natt-DJ", art="", t=time.time() - 5)
        d.lyr.info = {"mode": "play"}; d.lyr.resume = None; d.lyr.RESUME_WAIT = 0

    def tearDown(self):
        lp, inp, pw, d.play_url, d.lyr.info, d.threading.Thread = self.old
        d.last_play.clear(); d.last_play.update(lp); d.state["input"], d.state["power"] = inp, pw

    def test_fortsetter_etter_at_serveren_var_borte(self):
        d.lyr._husk_avspilling()
        d.lyr.info = {"mode": "stop"}
        d.lyr._gjenoppta()
        self.assertEqual(self.spilt, [("http://sw/stream.mp3", "Natt-DJ")])
        d.lyr._gjenoppta()   # bare én gang
        self.assertEqual(len(self.spilt), 1)

    def test_ikke_naar_noe_annet_er_valgt_eller_for_lenge_siden(self):
        d.lyr._husk_avspilling(); d.lyr.info = {"mode": "stop"}
        d.state["input"] = "bt"
        d.lyr._gjenoppta()
        d.state["input"] = "radio"
        d.lyr._husk_avspilling.__func__  # noqa
        d.lyr.info = {"mode": "play"}; d.lyr._husk_avspilling(); d.lyr.info = {"mode": "stop"}
        d.lyr.resume["t"] -= d.lyr.RESUME_S + 1
        d.lyr._gjenoppta()
        self.assertEqual(self.spilt, [])

    def test_ikke_bibliotekslaater(self):
        d.last_play["source"] = "navidrome"
        d.lyr._husk_avspilling()
        self.assertIsNone(d.lyr.resume)


if __name__ == "__main__":
    unittest.main()
