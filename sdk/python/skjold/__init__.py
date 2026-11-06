"""Skjold – Python-klient for det lokale API-et (docs/api/openapi.yaml). Bare standardbiblioteket.

    from skjold import Skjold
    s = Skjold("skjold.local")
    s.power(True); s.volume(30); s.preset(1)
    for st in s.events():
        print(st["volume"])
"""
import json
import urllib.request

__all__ = ["Skjold", "SkjoldFeil"]
__version__ = "1.0.0"


class SkjoldFeil(Exception):
    def __init__(self, status, melding):
        super().__init__(f"{status}: {melding}")
        self.status = status


class Skjold:
    def __init__(self, vert="skjold.local", port=8765, timeout=6.0, base=None):
        self.base = (base or f"http://{vert}:{port}").rstrip("/")
        self.timeout = timeout

    # --- lavnivå ---
    def request(self, metode, sti, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + sti, data=data, method=metode,
                                     headers={"content-type": "application/json"} if data else {})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read()).get("error") or e.reason
            except Exception:
                msg = e.reason
            raise SkjoldFeil(e.code, msg) from None
        return json.loads(raw) if raw else {}

    def get(self, sti):
        return self.request("GET", sti)

    def post(self, sti, body=None):
        return self.request("POST", sti, body or {})

    # --- vanlige kall ---
    def status(self):
        return self.get("/api/status")

    def power(self, on=True):
        return self.post("/api/power", {"on": bool(on)})

    def toggle(self):
        return self.post("/api/toggle")

    def volume(self, volume=None, delta=None):
        return self.post("/api/volume", {"delta": int(delta)} if delta is not None else {"volume": int(volume)})

    def mute(self, mute=True):
        return self.post("/api/mute", {"mute": bool(mute)})

    def input(self, kilde):
        return self.post("/api/input", {"input": kilde})

    def preset(self, n):
        return self.post("/api/preset", {"n": int(n)})

    def play(self, url, **ekstra):
        return self.post("/api/play", {"url": url, **ekstra})

    def transport(self, action):
        return self.post("/api/transport", {"action": action})

    def events(self):
        """Generator over status-oppdateringer fra Server-Sent Events (/api/events). Blokkerer."""
        req = urllib.request.Request(self.base + "/api/events", headers={"accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=None) as r:
            data = []
            for linje in r:
                linje = linje.decode("utf-8").rstrip("\r\n")
                if linje.startswith("data:"):
                    data.append(linje[5:].lstrip())
                elif not linje and data:
                    try:
                        yield json.loads("\n".join(data))
                    except ValueError:
                        pass
                    data = []
