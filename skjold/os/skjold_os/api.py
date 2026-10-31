"""Poller daemonens HTTP-API (127.0.0.1:8765). Kun standardbiblioteket."""
import json, threading, time, urllib.request

class DaemonClient:
    def __init__(self, base="http://127.0.0.1:8765", hz=8.0):
        self.base = base.rstrip("/"); self.period = 1.0 / hz
        self.status = None          # siste gyldige /api/status
        self.settings = {}          # /api/settings["settings"]
        self.online = False
        self.last_ok = 0.0
        self.cover = None           # (key, bytes)
        self._lock = threading.Lock(); self._stop = False; self._n = 0

    def _get(self, path, timeout=1.5, raw=False):
        with urllib.request.urlopen(self.base + path, timeout=timeout) as r:
            data = r.read()
            return data if raw else json.loads(data.decode("utf-8"))

    def poll_once(self):
        try:
            st = self._get("/api/status")
            with self._lock:
                self.status, self.online, self.last_ok = st, True, time.time()
            if self._n % 25 == 0 or not self.settings:          # innstillinger sjeldnere (~3 s)
                try:
                    self.settings = self._get("/api/settings").get("settings", {}) or {}
                except Exception:
                    pass
            key = (st.get("input"), st.get("cover"), st.get("title"), st.get("station"))
            if st.get("cover") and (self.cover is None or self.cover[0] != key):
                try:
                    self.cover = (key, self._get("/api/cover", raw=True))
                except Exception:
                    self.cover = (key, None)
            elif not st.get("cover"):
                self.cover = None
        except Exception:
            with self._lock:
                self.online = False
        self._n += 1

    def run(self):
        while not self._stop:
            t = time.time(); self.poll_once()
            time.sleep(max(0.02, self.period - (time.time() - t)))

    def start(self):
        threading.Thread(target=self.run, daemon=True, name="skjold-poll").start(); return self

    def stop(self): self._stop = True

    def snapshot(self):
        with self._lock:
            return self.online, self.status, dict(self.settings), self.cover
