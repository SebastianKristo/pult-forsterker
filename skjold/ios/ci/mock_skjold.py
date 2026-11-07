#!/usr/bin/env python3
"""Falsk Skjold-enhet for skjermbilder av iOS-appen i simulatoren (brukes av .github/workflows/ios-skjermbilder.yml).

Svarer på /api/* med demodata fra demodata.json (samme data som web-demoen): rommet «Stue» (S1), NRK Jazz spiller,
radiofavoritter, EQ og innstillinger. Logoer hentes fra pi/logos/nrk/*.png. Bare standardbiblioteket.
Bruk: python3 mock_skjold.py [port]   (standard 8765)
"""
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HER = os.path.dirname(os.path.abspath(__file__))
FX = json.load(open(os.path.join(HER, "demodata.json"), encoding="utf-8"))
LOGOER = os.path.normpath(os.path.join(HER, "..", "..", "..", "pi", "logos", "nrk"))
ST = FX["status"]
LOCK = threading.Lock()


def logo(k):
    k = (k or "").lower()
    for navn in ("p1plus", "p1", "p2", "p3", "jazz", "klassisk", "mp3", "folkemusikk", "sport"):
        if navn in k:
            p = os.path.join(LOGOER, f"nrk-{navn}.png")
            if os.path.isfile(p):
                return open(p, "rb").read()
    return None


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        sys.stderr.write("%s %s\n" % (self.command, self.path))

    def send(self, code, body=b"", ctype="application/json"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        p = u.path
        if not p.startswith("/api/"):
            return self.send(404, {"error": "ikke funnet"})
        k = p[5:].split("/")[0]
        if k == "events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            try:
                while True:
                    with LOCK:
                        data = json.dumps(ST, ensure_ascii=False)
                    self.wfile.write(f"data: {data}\n\n".encode())
                    self.wfile.flush()
                    time.sleep(2)
            except (BrokenPipeError, ConnectionResetError):
                return
        if k == "status":
            with LOCK:
                ST["position"] = (ST.get("position", 0) + 1) % max(1, ST.get("duration", 300))
                return self.send(200, ST)
        if k == "logo":
            b = logo(parse_qs(u.query).get("k", [""])[0])
            return self.send(200, b, "image/png") if b else self.send(404, b"ingen logo", "text/plain")
        if k == "cover":
            b = logo("jazz")
            return self.send(200, b, "image/png") if b else self.send(404, b"", "text/plain")
        if k in FX:
            return self.send(200, FX[k])
        return self.send(200, {})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            b = json.loads(self.rfile.read(n) or b"{}")
        except Exception:
            b = {}
        k = urlparse(self.path).path[5:].split("/")[0]
        with LOCK:
            if k == "volume" and "volume" in b:
                ST["volume"] = int(b["volume"])
            elif k == "mute":
                ST["mute"] = bool(b.get("mute"))
            elif k == "power":
                ST["power"] = bool(b.get("on"))
            elif k == "input" and b.get("input"):
                ST["input"] = b["input"]
            elif k == "preset" and b.get("n"):
                ST["preset"] = int(b["n"])
            elif k == "settings":
                FX["settings"]["settings"].update(b if isinstance(b, dict) else {})
                return self.send(200, FX["settings"])
            return self.send(200, ST)

    def do_OPTIONS(self):
        self.send(204)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    print(f"Falsk Skjold på 0.0.0.0:{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), H).serve_forever()
