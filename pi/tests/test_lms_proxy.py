"""Lyrion-fjernkontrollen: /api/lms/rpc videresender til serveren, sperrer farlige kommandoer; /api/lms/img bare bildestier."""
import asyncio
import os
import sys
import tempfile
import unittest

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402


class FalskLyrion:
    host, port, player = "10.0.0.5", 9000, "aa:aa:aa:aa:aa:01"

    def __init__(self):
        self.kall = []

    def rpc_as(self, p, cmd):
        self.kall.append((p, cmd))
        return {"ok": True, "cmd": cmd}


class Req:
    def __init__(self, body=None, query=None):
        self._b, self.query = body, query or {}

    async def json(self):
        if self._b is None:
            raise ValueError
        return self._b


def kjor(coro):
    return asyncio.new_event_loop().run_until_complete(coro)


class TestLmsProxy(unittest.TestCase):
    def setUp(self):
        self.gammel = d.lyr
        self.lyr = d.lyr = FalskLyrion()

    def tearDown(self):
        d.lyr = self.gammel

    def test_videresender(self):
        r = kjor(d.h_lms_rpc(Req({"player": "bb:bb:bb:bb:bb:02", "cmd": ["mixer", "volume", 30]})))
        self.assertEqual(r.status, 200)
        self.assertEqual(self.lyr.kall, [("bb:bb:bb:bb:bb:02", ["mixer", "volume", 30])])

    def test_serverkommando(self):
        r = kjor(d.h_lms_rpc(Req({"cmd": ["serverstatus", 0, 100]})))
        self.assertEqual(r.status, 200)
        self.assertEqual(self.lyr.kall[0][0], "")

    def test_sperret_og_ugyldig(self):
        for cmd in (["stopserver"], ["pref", "x", "y"]):
            self.assertEqual(kjor(d.h_lms_rpc(Req({"cmd": cmd}))).status, 403)
        self.assertEqual(kjor(d.h_lms_rpc(Req({"cmd": "status"}))).status, 400)
        self.assertEqual(kjor(d.h_lms_rpc(Req({"player": "x; rm", "cmd": ["status"]}))).status, 400)
        self.assertEqual(kjor(d.h_lms_rpc(Req(None))).status, 400)
        self.assertEqual(self.lyr.kall, [])

    def test_uten_server(self):
        self.lyr.host = None
        self.assertEqual(kjor(d.h_lms_rpc(Req({"cmd": ["status"]}))).status, 503)

    def test_bilde_bare_lyrion_stier(self):
        for p in ("http://evil/x.png", "/../etc/passwd", "/music/../../x", "/settings/index.html"):
            self.assertEqual(kjor(d.h_lms_img(Req(query={"p": p}))).status, 404, p)


if __name__ == "__main__":
    unittest.main()
