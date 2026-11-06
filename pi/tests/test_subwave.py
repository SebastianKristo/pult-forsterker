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
