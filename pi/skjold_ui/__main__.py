#!/usr/bin/env python3
"""skjold-ui: skjermen på Skjold S1 rev F (4,58″ 960 × 320 bar-skjerm på HDMI0) og Skjold Radio (4,3″ DSI 800 × 480).

Tegningen er designets egen canvas-kode (web/s1_draw.js, hentet ut av extract.py) og kjøres i Chromium i kiosk
(cage/Wayland, ingen X). Da blir skjermen piksel-identisk med designfilen uten en egen port av tegnekoden.

Denne prosessen
  * serverer web/ på 127.0.0.1:8766 og videresender /api/* (også SSE) til daemonen på 127.0.0.1:8765,
  * eier engangshilsenen (/etc/skjold/greeting.json: armed → shown, skrevet med fsync før skjermen bytter),
  * tar imot knappe- og hjulhendelser fra skjold-input og avgjør om skjermen bruker dem (meny, hilsen) – se KONTRAKT.md,
  * starter kiosken (cage + chromium) med --kiosk, eller bare serveren med --no-kiosk (utvikling/test).

Oppsett: SKJOLD_UI_LAYOUT=radio (i /etc/ki-amp.env, skrevet av install_skjold_ui.sh) gir radioskjermen
(web/radio.js, 800 × 480, ?layout=radio). Uten den: S1 (960 × 320). Se KONTRAKT.md.
"""
import argparse
import glob
import http.client
import json
import os
import queue
import shutil
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
WEB = os.path.join(HERE, "web")
DAEMON = os.environ.get("SKJOLD_DAEMON", "127.0.0.1:8765")
GREETING = os.environ.get("SKJOLD_GREETING", "/etc/skjold/greeting.json")
LAYOUT = os.environ.get("SKJOLD_UI_LAYOUT", "s1").strip().lower() or "s1"   # s1 | radio
SIZE = {"s1": (960, 320), "radio": (800, 480)}
BACKLIGHT = os.environ.get("SKJOLD_BACKLIGHT", "/sys/class/backlight")
RADIO_SRC = ("wheel", "preset", "power", "volume")   # Skjold Radio (skjold_radio_knapper.py)
TYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css", ".png": "image/png"}

ui = {"menu": False, "setup": False, "bday": False}   # rapportert av skjermen (POST /ui/state)
lock = threading.Lock()
subscribers: list = []


# ---------- engangshilsen ----------
def greeting_read():
    try:
        with open(GREETING, encoding="utf-8") as fh:
            g = json.load(fh)
        return {"name": str(g.get("name") or "Pappa"), "state": "armed" if g.get("state") == "armed" else "shown"}
    except (OSError, ValueError):
        return {"name": "Pappa", "state": "none"}


def greeting_write(g):
    os.makedirs(os.path.dirname(GREETING), exist_ok=True)
    tmp = GREETING + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(g, fh, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, GREETING)
    dfd = os.open(os.path.dirname(GREETING), os.O_RDONLY)
    try:
        os.fsync(dfd)
    finally:
        os.close(dfd)


def broadcast(ev):
    with lock:
        for q in list(subscribers):
            q.put(ev)


def handle_input(ev):
    """Avgjør om skjermen bruker en knappehendelse. Returnerer {"consumed": bool}.

    ev: {"ev":"press|turn|hold|back|menu_toggle", "src":"knob|power|air|aux|radio|usb", "d":±1 (turn)}
    """
    g = greeting_read()
    if g["state"] == "armed":   # første trykk lukker hilsenen og gjør ingenting annet
        if ev.get("ev") in ("press", "hold", "turn", "back", "menu_toggle"):
            g["state"] = "shown"
            greeting_write(g)   # fsync før skjermen bytter (BURSDAGSHILSEN.md punkt 4)
            broadcast({"ev": "dismiss_greeting"})
            return {"consumed": True}
    e, src = ev.get("ev"), ev.get("src", "knob")
    if src in RADIO_SRC:
        return radio_input(ev)
    if e == "menu_toggle" or (e == "hold" and src == "knob"):   # hold volumhjulet 1,5 s = innstillinger
        broadcast({"ev": "menu_toggle"})
        return {"consumed": True}
    with lock:
        menu = ui["menu"]
    if menu and src == "knob" and e in ("turn", "press", "back"):
        broadcast(dict(ev))
        return {"consumed": True}
    if menu and src != "knob" and e == "press":   # en kildeknapp mens menyen er åpen = tilbake
        broadcast({"ev": "back"})
        return {"consumed": True}
    return {"consumed": False}


def radio_input(ev):
    """Skjold Radio: hjulet styrer menyen på skjermen, favorittknappene vises på skjermen.

    hold hjulet          → åpner menyen, eller «tilbake» når den er åpen (brukt)
    drei/trykk hjulet    → navigerer når menyen er åpen (brukt); ellers vanlig handling, og en drei vises som
                           «browse» (hvilken favoritt som starter) på skjermen
    favoritt trykk/lagret → vises på skjermen (lukker menyen); knappen gjør alltid sin vanlige handling
    av/på og volum       → ikke brukt (daemonen viser endringen i status)"""
    e, src = ev.get("ev"), ev.get("src")
    with lock:
        menu = ui["menu"]
    if src == "wheel":
        if e == "hold":
            broadcast({"ev": "back" if menu else "menu_toggle", "src": "wheel"})
            return {"consumed": True}
        if menu and e in ("turn", "press", "back"):
            broadcast(dict(ev))
            return {"consumed": True}
        if e == "turn":
            broadcast({"ev": "browse", "d": 1 if (ev.get("d") or 0) > 0 else -1})
        return {"consumed": False}
    if src == "preset" and e in ("press", "saved"):
        broadcast({"ev": "preset" if e == "press" else "saved", "n": ev.get("n")})
    return {"consumed": False}


def net_info():
    """Vertsnavn og IP-adresse (den som brukes ut mot nettet) til «Innstillinger → Nettverk» på radioskjermen."""
    ip = ""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("192.0.2.1", 9))   # TEST-NET: ingen pakker sendes, bare rutevalg
            ip = s.getsockname()[0]
        finally:
            s.close()
    except OSError:
        pass
    return {"host": socket.gethostname(), "ip": ip}


def set_backlight(level):
    """Lysstyrke 0–1 på DSI-skjermens baklys (/sys/class/backlight/*). Uten skrivetilgang: bare CSS-dimmingen."""
    done = []
    for d in glob.glob(os.path.join(BACKLIGHT, "*")):
        try:
            with open(os.path.join(d, "max_brightness")) as fh:
                mx = int(fh.read().strip() or 255)
            with open(os.path.join(d, "brightness"), "w") as fh:
                fh.write(str(max(1, round(mx * max(0.05, min(1.0, float(level)))))))
            done.append(os.path.basename(d))
        except (OSError, ValueError):
            pass
    return {"ok": bool(done), "devices": done}


class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def do_GET(self):
        p = self.path.split("?")[0]
        if p.startswith("/api/"):
            return self._proxy("GET")
        if p == "/greeting":
            return self._json(greeting_read())
        if p == "/ui":
            with lock:
                return self._json({**ui, "greeting": greeting_read()["state"]})
        if p == "/ui/stream":
            return self._stream()
        if p == "/ui/net":
            return self._json(net_info())
        f = os.path.normpath(os.path.join(WEB, (p.lstrip("/") or "index.html")))
        if not f.startswith(WEB) or not os.path.isfile(f):
            return self._json({"error": "ikke funnet"}, 404)
        b = open(f, "rb").read()
        self.send_response(200)
        self.send_header("Content-Type", TYPES.get(os.path.splitext(f)[1], "application/octet-stream"))
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        p = self.path.split("?")[0]
        if p.startswith("/api/"):
            return self._proxy("POST")
        if p == "/ui/state":
            b = self._body()
            with lock:
                for k in ui:
                    if k in b:
                        ui[k] = bool(b[k])
            return self._json(ui)
        if p == "/ui/event":
            return self._json(handle_input(self._body()))
        if p == "/ui/backlight":   # radioskjermen: {"level": 0–1}
            return self._json(set_backlight(self._body().get("level", 1)))
        if p == "/greeting":   # web-UI → Innstillinger → Hilsen → Installer: {"name","state":"armed"}
            b = self._body()
            g = {"name": str(b.get("name") or "Pappa")[:24], "state": "armed" if b.get("state", "armed") == "armed" else "shown"}
            greeting_write(g)
            broadcast({"ev": "greeting_changed"})
            return self._json(g)
        if p == "/greeting/dismiss":
            return self._json(handle_input({"ev": "press", "src": "knob"}))
        return self._json({"error": "ukjent"}, 404)

    def _stream(self):
        q = queue.Queue()
        with lock:
            subscribers.append(q)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(b": ok\n\n")
            self.wfile.flush()
            while True:
                try:
                    ev = q.get(timeout=15)
                    self.wfile.write(b"data: " + json.dumps(ev).encode() + b"\n\n")
                except queue.Empty:
                    self.wfile.write(b": ping\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with lock:
                if q in subscribers:
                    subscribers.remove(q)
            self.close_connection = True

    def _proxy(self, method):
        host, port = DAEMON.rsplit(":", 1)
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0)) if method == "POST" else None
        try:
            c = http.client.HTTPConnection(host, int(port), timeout=None if self.path.startswith("/api/events") else 8)
            c.request(method, self.path, body=body, headers={"Content-Type": self.headers.get("Content-Type", "application/json")})
            r = c.getresponse()
        except OSError:
            return self._json({"error": "daemonen svarer ikke"}, 502)
        self.send_response(r.status)
        ct = r.getheader("Content-Type", "application/json")
        self.send_header("Content-Type", ct)
        self.send_header("Cache-Control", "no-store")
        if "event-stream" in ct:
            self.end_headers()
            try:
                while True:
                    chunk = r.read1(4096) if hasattr(r, "read1") else r.read(1)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    self.wfile.flush()
            except OSError:
                pass
            self.close_connection = True
            return
        b = r.read()
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def kiosk(port):
    """cage (Wayland-kiosk, ingen X) + Chromium: 960 × 320 på HDMI0 (S1) eller 800 × 480 på DSI (radio)."""
    chromium = shutil.which("chromium") or shutil.which("chromium-browser")
    cage = shutil.which("cage")
    if not (chromium and cage):
        print("skjold-ui: mangler cage/chromium – kjører bare serveren", file=sys.stderr)
        return None
    w, h = SIZE.get(LAYOUT, SIZE["s1"])
    q = "" if LAYOUT == "s1" else f"?layout={LAYOUT}"
    args = [cage, "-d", "-s", "--", chromium, "--kiosk", f"--app=http://127.0.0.1:{port}/{q}",
            "--ozone-platform=wayland", f"--window-size={w},{h}", "--force-device-scale-factor=1",
            "--noerrdialogs", "--disable-infobars", "--no-first-run", "--disable-pinch", "--overscroll-history-navigation=0",
            "--disable-features=Translate,HardwareMediaKeyHandling", "--check-for-update-interval=31536000",
            "--password-store=basic", f"--user-data-dir={os.path.expanduser('~')}/.cache/skjold-ui"]
    return subprocess.Popen(args)


def main():
    ap = argparse.ArgumentParser(description="Skjold-skjermen: S1 (960 × 320) eller radio (800 × 480, SKJOLD_UI_LAYOUT=radio)")
    ap.add_argument("--port", type=int, default=int(os.environ.get("SKJOLD_UI_PORT", "8766")))
    ap.add_argument("--no-kiosk", action="store_true", help="bare server (utvikling/test)")
    a = ap.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", a.port), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"skjold-ui på http://127.0.0.1:{a.port}/ (oppsett {LAYOUT}, daemon {DAEMON})", flush=True)
    proc = None if a.no_kiosk else kiosk(a.port)
    try:
        if proc:
            sys.exit(proc.wait())   # systemd starter oss på nytt hvis kiosken stopper
        threading.Event().wait()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
