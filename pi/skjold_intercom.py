"""Intercom og kunngjøring: et lydklipp (eller tekst → tale) spilles oppå det som spiller, i ett, flere eller alle rom.

Daemonen kaller `Intercom(ctx)` med disse funksjonene i `ctx`:
  announce(path)      spiller en lydfil oppå avspillingen (ffmpeg → dmix), blokkerer til den er ferdig
  get_volume()/set_volume(v)   for å dukke musikken mens klippet spilles
  peers()             [{id, navn, base}] – andre Skjold på nettet (mDNS/Skjold-hjem)
  self_id()           denne enhetens id
  tts(text) -> path   valgfri: tekst → wav (piper/espeak), None hvis ikke tilgjengelig
"""
from __future__ import annotations

import math
import os
import struct
import tempfile
import threading
import time
import urllib.request
import wave

EXT = {"audio/webm": ".webm", "audio/ogg": ".ogg", "audio/opus": ".opus", "audio/mp4": ".m4a", "audio/m4a": ".m4a",
       "audio/x-m4a": ".m4a", "audio/aac": ".aac", "audio/wav": ".wav", "audio/x-wav": ".wav", "audio/wave": ".wav",
       "audio/mpeg": ".mp3"}
MAX_BYTES = 8 * 1024 * 1024
DUCK_DB = -15.0


def duck_volume(v: int, db: float) -> int:
    """Omtrentlig volum-prosent for en demping i dB (volumet i Skjold er tilnærmet logaritmisk, ~0,6 dB per steg)."""
    return max(0, min(100, int(round(v + db / 0.6)))) if v > 0 else 0


def make_tone(path: str, kind: str = "ding", rate: int = 48000) -> str:
    """Kort signal før beskjeden: «ding» (to toner) eller «dingdong» (dørklokke). Skrives som 16-bit stereo wav."""
    notes = {"ding": [(880.0, 0.16), (1174.7, 0.30)],
             "dingdong": [(659.3, 0.55), (523.3, 0.85)],
             "chime": [(523.3, 0.25), (659.3, 0.25), (784.0, 0.25), (1046.5, 0.6)]}.get(kind) or [(880.0, 0.3)]
    frames = bytearray()
    for f, dur in notes:
        n = int(rate * dur)
        for i in range(n):
            t = i / rate
            env = min(1.0, t / 0.01) * math.exp(-3.2 * t / dur)
            s = 0.42 * env * (math.sin(2 * math.pi * f * t) + 0.35 * math.sin(4 * math.pi * f * t))
            v = int(max(-1.0, min(1.0, s)) * 32767)
            frames += struct.pack("<hh", v, v)
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate); w.writeframes(bytes(frames))
    return path


def plan_targets(to, self_id: str, peers: list[dict]) -> tuple[bool, list[dict]]:
    """Hvem skal få klippet? `to` er «all», en id, eller en liste med id-er. Returnerer (spill lokalt?, andre rom)."""
    if to in (None, "", "all", "alle", ["all"]):
        return True, list(peers)
    ids = [to] if isinstance(to, str) else [str(x) for x in to]
    ids = [i for x in ids for i in str(x).split(",") if i]
    local = self_id in ids or "self" in ids or "her" in ids
    return local, [p for p in peers if str(p.get("id")) in ids]


class Intercom:
    def __init__(self, ctx: dict):
        self.ctx = ctx
        self.lock = threading.Lock()
        self.tmp = ctx.get("tmpdir") or tempfile.gettempdir()
        self.last = None   # {t, from, to, ok}

    # ---------- avspilling her ----------
    def play_local(self, path: str, chime: bool = True, duck_db: float = DUCK_DB) -> None:
        with self.lock:
            v0 = self.ctx["get_volume"]()
            ducked = duck_volume(v0, duck_db)
            try:
                if ducked != v0:
                    self.ctx["set_volume"](ducked)
                if chime:
                    self.ctx["announce"](make_tone(os.path.join(self.tmp, "skjold-ding.wav"), "ding"))
                self.ctx["announce"](path)
            except Exception as e:
                print("Intercom:", e, flush=True)
            finally:
                if ducked != v0 and self.ctx["get_volume"]() == ducked:
                    self.ctx["set_volume"](v0)

    # ---------- videresending ----------
    @staticmethod
    def forward(base: str, data: bytes, ctype: str, sender: str, timeout: float = 15.0) -> bool:
        req = urllib.request.Request(base.rstrip("/") + "/api/intercom?to=self&hop=1", data=data, method="POST",
                                     headers={"Content-Type": ctype or "application/octet-stream", "X-Skjold-From": sender})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return 200 <= r.status < 300
        except Exception:
            return False

    def save_clip(self, data: bytes, ctype: str) -> str:
        if not data:
            raise ValueError("tomt lydklipp")
        if len(data) > MAX_BYTES:
            raise ValueError("lydklippet er for stort (maks 8 MB)")
        fd, path = tempfile.mkstemp(prefix="skjold-intercom-", suffix=EXT.get((ctype or "").split(";")[0].strip(), ".bin"), dir=self.tmp)
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        return path

    def send(self, data: bytes | None, ctype: str, to=None, text: str = "", sender: str = "", hop: bool = False) -> dict:
        """Ta imot et klipp (eller tekst), spill her og/eller send videre. Returnerer {local, sent:[navn], failed:[navn]}."""
        if not data and text:
            tts = self.ctx.get("tts")
            path = tts(text) if tts else None
            if not path:
                raise ValueError("tekst til tale er ikke tilgjengelig på denne enheten")
            with open(path, "rb") as fh:
                data, ctype = fh.read(), "audio/wav"
        path = self.save_clip(data, ctype)
        local, others = (True, []) if hop else plan_targets(to, self.ctx["self_id"](), self.ctx["peers"]())
        sent, failed = [], []
        for p in others:
            (sent if self.forward(p["base"], data, ctype, sender or self.ctx["self_id"]()) else failed).append(p.get("navn") or p.get("id"))
        if local:
            def run():
                try:
                    self.play_local(path)
                finally:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
            threading.Thread(target=run, daemon=True).start()
        else:
            os.unlink(path)
        self.last = {"t": time.time(), "from": sender, "local": local, "sent": sent, "failed": failed}
        return dict(self.last)
