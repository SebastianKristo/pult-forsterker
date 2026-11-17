"""Grupper (Lyrion-synk): rommene synkes med lederen, rom på en annen Lyrion flyttes hit først, oppløsning."""
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402

LEDER, S1, NODE = "aa:aa:aa:aa:aa:01", "bb:bb:bb:bb:bb:02", "cc:cc:cc:cc:cc:03"


class FalskLyrion:
    def __init__(self):
        self.host, self.port, self.player = "10.0.0.5", 9000, LEDER
        self.players = {LEDER, S1}
        self.synk = set()
        self.kall = []

    def rpc(self, cmd, player=True):
        self.kall.append(("leder", cmd))
        if cmd[0] == "players":
            return {"players_loop": [{"playerid": p} for p in self.players]}
        if cmd[0] == "status":
            return {"sync_slaves": ",".join(sorted(self.synk))} if self.synk else {}
        if cmd[0] == "sync":
            self.synk.add(cmd[1])
        return {}

    def rpc_as(self, p, cmd):
        self.kall.append((p, cmd))
        if cmd == ["sync", "-"]:
            self.synk.discard(p)
        return {}


class TestGruppe(unittest.TestCase):
    def setUp(self):
        self.old = (d.lyr, d._peer_json, d.time.sleep)
        self.lyr = d.lyr = FalskLyrion()
        self.peer = []
        st = {"http://s1:8765": {"name": "S1", "lms_player": S1, "lms_host": "10.0.0.5"},
              "http://node:8765": {"name": "Node", "lms_player": NODE, "lms_host": "10.0.0.9"},
              "http://meg:8765": {"name": "Touch", "lms_player": LEDER, "lms_host": "10.0.0.5"}}

        def peer(base, path, body=None, timeout=5):
            self.peer.append((base, path, body))
            if path == "/api/status":
                if base not in st:
                    raise OSError("nede")
                return st[base]
            if path == "/api/group/join" and body and body.get("host"):
                self.lyr.players.add(NODE)   # Node kobler seg til lederens server
            return {"ok": True}
        d._peer_json = peer
        d.time.sleep = lambda s: None
        d._group["bases"] = {}

    def tearDown(self):
        d.lyr, d._peer_json, d.time.sleep = self.old

    def test_synker_rom_paa_samme_server(self):
        res = d.group_set(["http://meg:8765", "http://s1:8765"])
        self.assertEqual([x["ok"] for x in res], [True])
        self.assertIn(("leder", ["sync", S1]), self.lyr.kall)
        self.assertFalse(any(p[1] == "/api/group/join" for p in self.peer))

    def test_rom_paa_annen_lyrion_flyttes_hit(self):
        res = d.group_set(["http://node:8765"])
        self.assertTrue(res[0]["ok"])
        self.assertIn(("http://node:8765", "/api/group/join", {"host": "10.0.0.5", "port": 9000}), self.peer)
        self.assertEqual(self.lyr.synk, {NODE})

    def test_losne_opp_og_sende_hjem(self):
        d.group_set(["http://s1:8765", "http://node:8765"])
        d.group_set([])
        self.assertEqual(self.lyr.synk, set())
        self.assertIn(("http://node:8765", "/api/group/join", {"leave": True}), self.peer)

    def test_rom_som_ikke_svarer(self):
        res = d.group_set(["http://borte:8765"])
        self.assertEqual(res, [{"base": "http://borte:8765", "ok": False, "error": "svarer ikke"}])


if __name__ == "__main__":
    unittest.main()
