"""Dørklokke-modus: når noen ringer på, dukkes musikken, en dørklokke spilles og kamerabildet vises på Touch/appene.

Utløses av POST /api/doorbell (webhook fra Home Assistant/Homey) eller ved at Skjold følger med på en HA-entitet
(binary_sensor/event/input_button). Første enhet som får ringet sender det videre til de andre rommene.
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request

DEFAULTS = {"enabled": False, "sound": "dingdong", "file": "", "duck_db": -20, "seconds": 20, "volume": 0,
            "ha_url": "", "ha_token": "", "trigger_entity": "", "camera_entity": "", "camera_url": "", "all_rooms": True}
SOUNDS = ("dingdong", "chime", "ding", "file")


def clean(cfg: dict, body: dict) -> dict:
    out = dict(cfg)
    for k, v in body.items():
        if k not in DEFAULTS:
            continue
        if k == "ha_token" and isinstance(v, str) and v.startswith("••••"):
            continue
        if k == "sound" and v not in SOUNDS:
            raise ValueError("ukjent lyd")
        if k in ("duck_db",):
            v = max(-40, min(0, int(v)))
        if k in ("seconds",):
            v = max(5, min(120, int(v)))
        if k == "volume":
            v = max(0, min(100, int(v)))
        if k in ("enabled", "all_rooms"):
            v = bool(v)
        if isinstance(DEFAULTS[k], str):
            v = str(v or "")[:500]
        out[k] = v
    return out


def masked(cfg: dict) -> dict:
    c = dict(cfg)
    if c.get("ha_token"):
        c["ha_token"] = "••••••"
    return c


def ha_state(ha_url: str, token: str, entity: str, timeout: float = 5.0) -> dict:
    req = urllib.request.Request(ha_url.rstrip("/") + "/api/states/" + entity, headers={"Authorization": "Bearer " + token})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def is_ring(prev: dict | None, cur: dict) -> bool:
    """Ringer det nå? binary_sensor: off→on. event/input_button: nytt tidsstempel i state."""
    if not cur:
        return False
    ent = cur.get("entity_id", "")
    if ent.startswith(("event.", "input_button.", "button.")):
        return bool(prev) and cur.get("state") != (prev or {}).get("state") and cur.get("state") not in ("unknown", "unavailable")
    return cur.get("state") == "on" and (prev or {}).get("state") != "on"


def camera_request(cfg: dict) -> urllib.request.Request | None:
    if cfg.get("camera_entity") and cfg.get("ha_url") and cfg.get("ha_token"):
        return urllib.request.Request(cfg["ha_url"].rstrip("/") + "/api/camera_proxy/" + cfg["camera_entity"],
                                      headers={"Authorization": "Bearer " + cfg["ha_token"]})
    if cfg.get("camera_url"):
        return urllib.request.Request(cfg["camera_url"])
    return None


class Doorbell:
    def __init__(self, ctx: dict, path: str):
        """ctx: announce(path), get_volume(), set_volume(v), peers(), changed(), make_tone(path, kind), tmpdir."""
        self.ctx, self.path = ctx, path
        self.cfg = dict(DEFAULTS)
        try:
            with open(path) as fh:
                self.cfg.update(json.load(fh))
        except Exception:
            pass
        self.last = 0.0
        self.busy = threading.Lock()
        self._stop = threading.Event()

    def save(self, body: dict) -> dict:
        self.cfg = clean(self.cfg, body)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path + ".tmp", "w") as fh:
            json.dump(self.cfg, fh)
        os.chmod(self.path + ".tmp", 0o600)
        os.replace(self.path + ".tmp", self.path)
        return masked(self.cfg)

    def status(self) -> dict | None:
        """Til /api/status: vises i 60 s etter ring, så Touch og appene kan vise kamera/varsel."""
        if time.time() - self.last > max(30, int(self.cfg.get("seconds") or 20) + 10):
            return None
        return {"t": self.last, "camera": bool(camera_request(self.cfg)), "seconds": self.cfg.get("seconds", 20)}

    def ring(self, hop: bool = False, forward=None) -> dict:
        """Ring på: varsel + lyd her, og (første gang) videre til alle rom."""
        now = time.time()
        if now - self.last < 4:   # flere trykk / flere kilder rett etter hverandre
            return {"ok": True, "ignored": True}
        self.last = now
        self.ctx["changed"]()
        if not hop and self.cfg.get("all_rooms", True):
            for p in self.ctx["peers"]():
                try:
                    (forward or self._forward)(p["base"])
                except Exception:
                    pass
        threading.Thread(target=self._play, daemon=True).start()
        return {"ok": True}

    @staticmethod
    def _forward(base: str) -> None:
        req = urllib.request.Request(base.rstrip("/") + "/api/doorbell?hop=1", data=b"{}", method="POST",
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=4).read()

    def _play(self) -> None:
        if not self.busy.acquire(blocking=False):
            return
        try:
            c = self.cfg
            v0 = self.ctx["get_volume"]()
            ducked = max(0, int(round(v0 + float(c.get("duck_db", -20)) / 0.6))) if v0 else 0
            if c.get("volume"):
                ducked = min(ducked, int(c["volume"])) if v0 else int(c["volume"])
            self.ctx["set_volume"](ducked)
            try:
                sound = c.get("file") if c.get("sound") == "file" and c.get("file") else \
                    self.ctx["make_tone"](os.path.join(self.ctx.get("tmpdir", "/tmp"), "skjold-doorbell.wav"), c.get("sound") or "dingdong")
                self.ctx["announce"](sound)
                end = time.time() + float(c.get("seconds", 20))
                while time.time() < end and not self._stop.is_set():
                    time.sleep(0.5)
            except Exception as e:
                print("Dørklokke:", e, flush=True)
            finally:
                if self.ctx["get_volume"]() == ducked:
                    self.ctx["set_volume"](v0)
        finally:
            self.busy.release()

    def watch(self) -> None:
        """Følg med på HA-entiteten (hvert 2. s) når den er satt. Kjøres i egen tråd."""
        prev = None
        while not self._stop.is_set():
            c = self.cfg
            if c.get("enabled") and c.get("trigger_entity") and c.get("ha_url") and c.get("ha_token"):
                try:
                    cur = ha_state(c["ha_url"], c["ha_token"], c["trigger_entity"])
                    if prev is not None and is_ring(prev, cur):
                        self.ring()
                    prev = cur
                except Exception:
                    time.sleep(8)
            else:
                prev = None
            self._stop.wait(2)
