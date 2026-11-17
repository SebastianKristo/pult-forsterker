"""SUB/WAVE-klienten (MCP over streamable HTTP) mot en falsk MCP-server – både JSON- og SSE-svar."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
os.environ.setdefault("KI_AMP_SKY_FILE", os.path.join(tempfile.mkdtemp(), "sky.json"))
os.environ.setdefault("KI_AMP_LMS", "0")
import ki_amp_daemon as d  # noqa: E402

TOOLS = [{"name": "subwave_now_playing", "inputSchema": {"type": "object", "properties": {}}},
         {"name": "subwave_request_song", "inputSchema": {"type": "object", "properties": {"request": {"type": "string"}, "requester_name": {"type": "string"}}}},
         {"name": "subwave_skip_track", "inputSchema": {"type": "object", "properties": {}}}]


def server(sse):
    seen = {"calls": [], "auth": [], "sessions": []}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass

        def do_POST(self):
            msg = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            seen["auth"].append(self.headers.get("Authorization"))
            seen["sessions"].append(self.headers.get("Mcp-Session-Id"))
            if "id" not in msg:   # notifikasjon
                self.send_response(202); self.end_headers(); return
            m = msg["method"]
            if m == "initialize": res = {"protocolVersion": "2025-03-26", "capabilities": {}}
            elif m == "tools/list": res = {"tools": TOOLS}
            elif m == "tools/call":
                seen["calls"].append(msg["params"])
                if msg["params"]["name"] == "subwave_now_playing":
                    res = {"content": [{"type": "text", "text": json.dumps({"track": {"title": "Nattlys", "artist": "Kaja", "album": "Byen", "cover_url": "https://x/c.jpg"}, "listeners": 3})}]}
                else:
                    res = {"structuredContent": {"queued": True}}
            body = json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": res})
            self.send_response(200)
            if m == "initialize": self.send_header("Mcp-Session-Id", "sess-1")
            if sse:
                self.send_header("Content-Type", "text/event-stream"); self.end_headers()
                self.wfile.write(("event: message\ndata: " + body + "\n\n").encode())
            else:
                self.send_header("Content-Type", "application/json"); self.end_headers()
                self.wfile.write(body.encode())

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, seen


class TestSubwave(unittest.TestCase):
    def _run(self, sse):
        srv, seen = server(sse)
        try:
            os.environ["no_proxy"] = os.environ["NO_PROXY"] = "127.0.0.1"
            cl = d.SubwaveClient(f"http://127.0.0.1:{srv.server_port}/", "dj", "hemmelig")
            np = cl.call("subwave_now_playing", cache=True)
            self.assertEqual(np["track"]["title"], "Nattlys")
            cl.call("subwave_now_playing", cache=True)   # fra cache
            res = cl.call("subwave_request_song", {"text": "noe rolig", "name": "Seb"})
            self.assertEqual(res, {"queued": True})
            self.assertEqual(len(seen["calls"]), 2)
            self.assertEqual(seen["calls"][1]["arguments"], {"request": "noe rolig", "requester_name": "Seb"})
            self.assertIn("sess-1", seen["sessions"])
            self.assertTrue(all(a and a.startswith("Basic ") for a in seen["auth"]))
        finally:
            srv.shutdown()

    def test_json(self): self._run(False)

    def test_sse(self): self._run(True)

    def test_parse_sse_med_flere_meldinger(self):
        raw = b'event: message\ndata: {"jsonrpc":"2.0","method":"notifications/progress"}\n\ndata: {"jsonrpc":"2.0","id":7,"result":{"ok":1}}\n\n'
        self.assertEqual(d.SubwaveClient.parse_body("text/event-stream", raw, 7)["result"], {"ok": 1})

    def test_stream_url_med_passord(self):
        d.save_state = lambda: None
        old = dict(d.state.get("settings") or {})
        try:
            d.state["settings"] = {"plugins": {"subwave": {"enabled": True, "url": "https://radio.example.no/", "user": "", "password": "p@ss"}}}
            self.assertEqual(d.subwave_stream_url(), "https://skjold:p%40ss@radio.example.no/stream.mp3")
        finally:
            d.state["settings"] = old


if __name__ == "__main__":
    unittest.main()


class TestFlereStasjoner(unittest.TestCase):
    def setUp(self):
        self._old = json.loads(json.dumps(d.state.get("settings") or {}))
        d.state.setdefault("settings", {})["plugins"] = {"subwave": {
            "enabled": True, "url": "https://radio.a.no/", "name": "Stua-DJ", "user": "", "password": "",
            "extra": [{"name": "Kontor", "url": "https://b.no/radio", "user": "dj", "password": "pw"},
                      {"name": "Uten adresse", "url": ""}]}}

    def tearDown(self):
        d.state["settings"] = self._old

    def test_liste_og_url(self):
        st = d.sw_stations()
        self.assertEqual([x["name"] for x in st], ["Stua-DJ", "Kontor"])
        self.assertEqual(d.subwave_stream_url("mp3", 0), "https://radio.a.no/stream.mp3")
        self.assertEqual(d.subwave_stream_url("opus", 1), "https://dj:pw@b.no/radio/stream.opus")

    def test_hvilken_spiller(self):
        old_in, old_info = d.state.get("input"), dict(d.lyr.info or {})
        try:
            d.state["input"] = "radio"; d.lyr.info = {"url": "https://dj:pw@b.no/radio/stream.mp3"}
            self.assertEqual(d.subwave_playing_idx(), 1)
            self.assertEqual(d._sw_station()["name"], "Kontor")
            d.lyr.info = {"url": "https://annen.no/stream.mp3"}
            self.assertIsNone(d.subwave_playing_idx())
        finally:
            d.state["input"] = old_in; d.lyr.info = old_info


class TestAdminHopp(TestFlereStasjoner):
    """«Neste» på Touch/knotten hopper over låten når SUB/WAVE-stasjonen som spiller har admin-passord."""

    def _spill(self, url):
        self._oi, self._ol = d.state.get("input"), dict(d.lyr.info or {})
        d.state["input"] = "radio"; d.lyr.info = {"url": url}

    def _stopp(self):
        d.state["input"] = self._oi; d.lyr.info = self._ol

    def test_admin_hopper_over(self):
        self._spill("https://dj:pw@b.no/radio/stream.mp3")
        kall = []
        class Falsk:
            _cache = {"x": 1}
            def call(self, tool, values=None, cache=False): kall.append(tool)
        old = d.subwave
        try:
            d.subwave = lambda i=None: Falsk()
            self.assertTrue(d.subwave_admin())
            d.transport("next")
            self.assertEqual(kall, ["subwave_skip_track"])
        finally:
            d.subwave = old; self._stopp()

    def test_uten_admin_bytter_stasjon(self):
        self._spill("https://radio.a.no/stream.mp3")
        steg = []
        old = d.step_preset
        try:
            d.step_preset = lambda n: steg.append(n)
            self.assertFalse(d.subwave_admin())
            d.transport("next")
            self.assertEqual(steg, [1])
        finally:
            d.step_preset = old; self._stopp()


class TestLagreStasjoner(unittest.TestCase):
    def test_extra_renses(self):
        old = json.loads(json.dumps(d.state.get("settings") or {}))
        try:
            d.plugin_update("subwave", {"enabled": True, "url": "https://a.no", "extra": [{"name": "B" * 60, "url": " https://b.no ", "x": 1}, "tull"]})
            c = d.plug_cfg("subwave")
            self.assertEqual(c["extra"], [{"name": "B" * 40, "url": "https://b.no", "user": "", "password": "", "image": ""}])
            self.assertEqual(len(d.sw_stations(c)), 2)
            d.plugin_update("subwave", {"extra": [{"url": "https://b.no", "image": "data:image/jpeg;base64,AAAA"}, {"url": "https://c.no", "image": "javascript:x"}]})
            self.assertEqual([x["image"] for x in d.plug_cfg("subwave")["extra"]], ["data:image/jpeg;base64,AAAA", ""])
            self.assertEqual(len(d.sw_stations(c)), 2)
        finally:
            d.state["settings"] = old


class SubwavePosisjon(unittest.TestCase):
    """Sangteksten på SUB/WAVE gikk ikke i takt: Lyrion kjenner bare tiden siden radiostrømmen startet."""

    def test_starttid_gir_posisjon_minus_strømforsinkelse(self):
        now = 1_800_000_000.0
        r = d.subwave_pos({"track": {"duration": 200}, "started_at": now - 50}, {"duration": 200}, "Låt", now=now)
        self.assertAlmostEqual(r["position"], 50 - d.SW_DELAY, places=3)
        self.assertEqual(r["duration"], 200)

    def test_iso_starttid_og_millisekunder(self):
        r = d.subwave_pos({"started_at": "2027-01-15T08:00:00Z"}, {"duration": 180000}, "x", now=1_800_000_000.0 + 0)
        self.assertEqual(r["duration"], 180.0)

    def test_elapsed_teller_videre_mellom_svar(self):
        d._swpos.update(key=None, t=0.0)
        a = d.subwave_pos({"elapsed": 30}, {"duration": 240}, "Sang", now=1000.0)
        b = d.subwave_pos({"elapsed": 30}, {"duration": 240}, "Sang", now=1008.0)   # samme hurtigbufrede svar 8 s senere
        self.assertAlmostEqual(b["position"] - a["position"], 8.0, places=3)

    def test_uten_tid_regner_fra_tittelbyttet(self):
        d._swpos.update(title=None, first=0.0)
        a = d.subwave_pos({"title": "x"}, {"title": "x"}, "x", now=500.0)
        b = d.subwave_pos({"title": "x"}, {"title": "x"}, "x", now=530.0)
        self.assertAlmostEqual(a["position"], 0.0, places=3)
        self.assertAlmostEqual(b["position"], 30.0, places=3)
        self.assertEqual(d.subwave_pos({}, {}, ""), {})
