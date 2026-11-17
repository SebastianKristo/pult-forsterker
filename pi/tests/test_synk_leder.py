"""Skjold Synk: lederen henter målingene fra rommene og setter Lyrions playDelay per spiller."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402

LEDER, NODE = "aa:aa:aa:aa:aa:01", "cc:cc:cc:cc:cc:03"


class FalskLyrion:
    def __init__(self, master=LEDER):
        self.host, self.port, self.player = "10.0.0.5", 9000, LEDER
        self.master = master
        self.kall = []

    def rpc(self, cmd, player=True):
        if cmd[0] == "status":
            return {"sync_master": self.master, "sync_slaves": NODE}
        self.kall.append((LEDER, cmd))
        return {}

    def rpc_as(self, p, cmd):
        self.kall.append((p, cmd))
        return {}


class TestLeder(unittest.TestCase):
    def setUp(self):
        self.orig = (d.lyr, d._peer_json, d.output_latency, dict(d._group["bases"]))
        d._justert.clear()
        d._group["bases"] = {NODE: "http://10.0.0.9:8765"}
        d._peer_json = lambda base, path, body=None, timeout=4: {"ms": 712.4, "running": True}
        d.output_latency = lambda: {"ms": 85.0, "running": True}

    def tearDown(self):
        d.lyr, d._peer_json, d.output_latency, d._group["bases"] = self.orig
        d._justert.clear()

    def test_setter_playdelay_per_spiller(self):
        d.lyr = FalskLyrion()
        ut = d.group_align()
        self.assertEqual(sorted((x["player"], x["ms"]) for x in ut), [(LEDER, 85), (NODE, 712)])
        self.assertIn((LEDER, ["playerpref", "playDelay", "85"]), d.lyr.kall)
        self.assertIn((NODE, ["playerpref", "playDelay", "712"]), d.lyr.kall)
        d.lyr.kall.clear()
        d.group_align()   # uendret: ingen nye kall
        self.assertEqual(d.lyr.kall, [])

    def test_bare_lederen_justerer(self):
        d.lyr = FalskLyrion(master=NODE)
        self.assertEqual(d.group_align(), [])
        self.assertEqual(d.lyr.kall, [])


if __name__ == "__main__":
    unittest.main()
