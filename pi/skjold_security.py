"""Sikkerhetsmodus: sirene eller kunngjøring på full styrke når alarmen utløses.

Utløses fra Home Assistant (tjeneste skjold.security_trigger / alarm_control_panel-automasjon), Homey (flytkort) eller
API-et. Krever at sikkerhetsmodus er slått på i innstillingene – ellers avvises utløsningen.

POST /api/security {action: "trigger"|"stop", rom?: [http://host:8765 …], lyd?: "sirene"|"pip"|url, tekst?: str}
GET/POST /api/security/innstillinger {på, lyd, tekst, volum, maks_min, rom, gjenta_s}
GET /api/security → {aktiv, startet, grunn, cfg}

Ved utløsning: Skjold slås på (også fra standby), volumet settes til «volum» (standard 100, barnemodus-grensen
overstyres mens alarmen går), og sirenen/kunngjøringen gjentas til «stop» eller til maks_min er gått. Andre rom
i «rom» får samme kommando. Etterpå settes volum og av/på tilbake slik de var.
"""
import json
import math
import os
import struct
import threading
import time
import urllib.request
import wave

LYDER = ("sirene", "pip")


def siren_wav(path: str, secs: float = 6.0, sr: int = 48000, kind: str = "sirene") -> str:
    """Lag en sirene (sveip 600–1400 Hz) eller pipelyd som 16-bit stereo WAV."""
    n = int(secs * sr)
    frames = bytearray()
    phase = 0.0
    for i in range(n):
        t = i / sr
        if kind == "pip":
            f = 2800.0
            amp = 0.9 if (t % 0.5) < 0.25 else 0.0
        else:
            f = 1000 + 400 * math.sin(2 * math.pi * 0.5 * t)
            amp = 0.9
        phase += 2 * math.pi * f / sr
        v = int(max(-1.0, min(1.0, amp * math.sin(phase))) * 32767)
        frames += struct.pack("<hh", v, v)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(bytes(frames))
    return path


def http_post(url, body, timeout=5):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as f:
        return json.loads(f.read() or b"{}")


class Security:
    STD = {"på": False, "lyd": "sirene", "tekst": "Inntrenger oppdaget. Du er filmet, og politiet er varslet.",
           "volum": 100, "maks_min": 5, "rom": [], "gjenta_s": 2}

    def __init__(self, ctx, path=None, sound_dir="/tmp", sleep=time.sleep):
        """ctx: get_power(), set_power(on), get_volume(), set_volume(v), announce(sti|url), say(tekst) → wav|None,
        post(url, body)."""
        self.ctx, self.path, self.sound_dir, self.sleep = ctx, path, sound_dir, sleep
        self.cfg = json.loads(json.dumps(self.STD))
        self.active = False
        self.started = 0.0
        self.reason = ""
        self._stop = threading.Event()
        self._prev = None
        self._thread = None
        if path and os.path.exists(path):
            try:
                self.cfg.update({k: v for k, v in json.load(open(path)).items() if k in self.STD})
            except Exception:
                pass

    def sett(self, b):
        if "på" in b:
            self.cfg["på"] = bool(b["på"])
        if b.get("lyd") is not None:
            v = str(b["lyd"])
            if v in LYDER or v.startswith(("http://", "https://")):
                self.cfg["lyd"] = v
        if b.get("tekst") is not None:
            self.cfg["tekst"] = str(b["tekst"])[:300]
        for k, lo, hi in (("volum", 10, 100), ("maks_min", 1, 30), ("gjenta_s", 0, 30)):
            if b.get(k) is not None:
                self.cfg[k] = int(max(lo, min(hi, int(b[k]))))
        if isinstance(b.get("rom"), list):
            self.cfg["rom"] = [str(x).rstrip("/") for x in b["rom"] if str(x).startswith(("http://", "https://"))][:20]
        if self.path:
            with open(self.path + ".tmp", "w") as f:
                json.dump(self.cfg, f)
            os.replace(self.path + ".tmp", self.path)
        return dict(self.cfg)

    def status(self):
        return {"aktiv": self.active, "startet": self.started, "grunn": self.reason, "cfg": dict(self.cfg)}

    def _sound(self, lyd):
        if lyd and str(lyd).startswith(("http://", "https://")):
            return lyd
        kind = lyd if lyd in LYDER else "sirene"
        p = os.path.join(self.sound_dir, f"skjold-sikkerhet-{kind}.wav")
        if not os.path.exists(p):
            siren_wav(p, kind=kind)
        return p

    def trigger(self, b=None, forward=True):
        b = b or {}
        if not self.cfg["på"]:
            return {"ok": False, "error": "sikkerhetsmodus er ikke slått på i innstillingene"}
        rom = b.get("rom") if isinstance(b.get("rom"), list) else self.cfg["rom"]
        if forward:
            for host in rom:
                try:
                    self.ctx["post"](host.rstrip("/") + "/api/security", {"action": "trigger", "lyd": b.get("lyd"),
                                                                          "tekst": b.get("tekst"), "videresendt": True})
                except Exception:
                    pass
        if self.active:
            return {"ok": True, "aktiv": True}
        self._prev = (self.ctx["get_power"](), self.ctx["get_volume"]())
        self.active, self.started, self.reason = True, time.time(), str(b.get("grunn") or "")[:100]
        self._stop.clear()
        lyd = b.get("lyd") or self.cfg["lyd"]
        tekst = b.get("tekst") if b.get("tekst") is not None else self.cfg["tekst"]
        self._thread = threading.Thread(target=self._run, args=(lyd, tekst), daemon=True)
        self._thread.start()
        return {"ok": True, "aktiv": True}

    def _run(self, lyd, tekst):
        try:
            if not self.ctx["get_power"]():
                self.ctx["set_power"](True)
            self.ctx["set_volume"](int(self.cfg["volum"]))
            src = self._sound(lyd)
            msg = None
            if tekst:
                try:
                    msg = self.ctx["say"](tekst)
                except Exception:
                    msg = None
            slutt = self.started + 60 * float(self.cfg["maks_min"])
            while not self._stop.is_set() and time.time() < slutt:
                # hold volumet oppe selv om noe (barnemodus, en app) har skrudd det ned
                if self.ctx["get_volume"]() < int(self.cfg["volum"]):
                    self.ctx["set_volume"](int(self.cfg["volum"]))
                self.ctx["announce"](src)
                if self._stop.is_set():
                    break
                if msg:
                    self.ctx["announce"](msg)
                self.sleep(float(self.cfg["gjenta_s"]))
        finally:
            self._restore()

    def _restore(self):
        prev, self._prev = self._prev, None
        self.active = False
        if prev:
            power, vol = prev
            try:
                self.ctx["set_volume"](vol)
                if not power:
                    self.ctx["set_power"](False)
            except Exception:
                pass

    def stop(self, forward=True, rom=None):
        if forward:
            for host in (rom if isinstance(rom, list) else self.cfg["rom"]):
                try:
                    self.ctx["post"](host.rstrip("/") + "/api/security", {"action": "stop", "videresendt": True})
                except Exception:
                    pass
        self._stop.set()
        t = self._thread
        if t and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=2)
        if self.active and not (t and t.is_alive()):
            self._restore()
        return {"ok": True, "aktiv": self.active}
