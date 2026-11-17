"""Skjold Synk – rom i samme gruppe skal høres samtidig.

Lyrion synkroniserer bare frem til hver spiller (squeezelite). Etter det går lyden gjennom ALSA-loopback,
CamillaDSP og lydkortet, og den veien er ulik lang på hver enhet: 3,5 mm-utgangen på en Pi 3 har store buffere, en
I²S-DAC små. Uten utjevning ligger et rom 0,5–1 s etter et annet.

Slik virker det:
1. Hver enhet måler sin egen utgangsforsinkelse mens den spiller (``maal``):
   - forsinkelsen i loopback-enheten squeezelite skriver til (ALSA «delay» for squeezelite-prosessen),
   - det CamillaDSP har i kø (``GetBufferLevel`` over websocket) pluss én blokk som behandles,
   - forsinkelsen i lydkortet CamillaDSP spiller til (ALSA «delay» for camilladsp-prosessen),
   - pluss en fast finjustering per rom (``trim_ms``, i millisekunder, kan være negativ).
   ALSA-tallene leses fra /proc/asound/card*/pcm*p/sub*/status. Flere målinger gir et glidende snitt.
2. Lederen i gruppen henter målingen fra hvert rom (GET /api/sync/latency) og setter Lyrions
   ``playerpref playDelay`` for hver spiller lik dens forsinkelse. Lyrion starter da spillerne med lang vei tidligere,
   så lyden kommer ut samtidig. Lederen gjentar det mens gruppen spiller, og endrer bare når forskjellen er merkbar.
"""
from __future__ import annotations

import glob
import os
import re
import subprocess
import time

MIN_ENDRING_MS = 15          # endre playDelay bare når forsinkelsen har flyttet seg merkbart
SNITT = 8                    # glidende snitt over så mange målinger


def les(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return ""


def pcm_status(root: str = "/proc/asound") -> list[dict]:
    """Avspillingsstrømmer som går nå: [{card, pid, delay, rate}]. delay i rammer, rate fra hw_params."""
    out = []
    for st in glob.glob(os.path.join(root, "card*", "pcm*p", "sub*", "status")):
        txt = les(st)
        if "RUNNING" not in txt:
            continue
        kv = {}
        for line in txt.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                kv[k.strip()] = v.strip()
        try:
            pid, delay = int(kv.get("owner_pid") or 0), int(kv.get("delay") or 0)
        except ValueError:
            continue
        hw = les(os.path.join(os.path.dirname(st), "hw_params"))
        m = re.search(r"^rate:\s*(\d+)", hw, re.M)
        card_dir = st.split(os.sep + "pcm")[0]
        out.append({"card": les(os.path.join(card_dir, "id")).strip(), "pid": pid, "delay": delay,
                    "rate": int(m.group(1)) if m else 48000})
    return out


def pids(navn: str) -> set[int]:
    try:
        r = subprocess.run(["pidof", navn], capture_output=True, text=True, timeout=3)
        return {int(x) for x in r.stdout.split()}
    except Exception:
        return set()


def camilla_buffer(ws_url: str, timeout: float = 1.5) -> int | None:
    """Rammer CamillaDSP har i kø mot lydkortet (GetBufferLevel), eller None."""
    try:
        import json
        import websocket   # python3-websocket (samme som daemonen bruker for CamillaDSP)
        ws = websocket.create_connection(ws_url, timeout=timeout)
        try:
            ws.send(json.dumps("GetBufferLevel"))
            r = json.loads(ws.recv())
        finally:
            ws.close()
        v = (r.get("GetBufferLevel") or {}).get("value")
        return int(v) if v is not None else None
    except Exception:
        return None


def regn(status: list[dict], sq_pids: set[int], dsp_pids: set[int], dsp_buffer: int | None,
         dsp_rate: int = 48000, chunk: int = 1024, trim_ms: float = 0.0) -> dict:
    """Utgangsforsinkelse i ms fra målingene. running = noe går gjennom kjeden akkurat nå."""
    ms = lambda frames, rate: 1000.0 * frames / max(1, rate)
    loop = sum(ms(s["delay"], s["rate"]) for s in status if s["pid"] in sq_pids)
    kort = sum(ms(s["delay"], s["rate"]) for s in status if s["pid"] in dsp_pids)
    dsp = ms((dsp_buffer or 0) + chunk, dsp_rate) if dsp_pids else 0.0
    running = any(s["pid"] in sq_pids for s in status) and (not dsp_pids or any(s["pid"] in dsp_pids for s in status))
    total = loop + dsp + kort + trim_ms
    return {"ms": round(total, 1), "running": running,
            "deler": {"squeezelite": round(loop, 1), "camilladsp": round(dsp, 1), "lydkort": round(kort, 1), "trim": round(trim_ms, 1)}}


class Maaler:
    """Glidende snitt av utgangsforsinkelsen. Brukes av daemonen (GET /api/sync/latency)."""

    def __init__(self, ws_url: str, root: str = "/proc/asound"):
        self.ws_url, self.root = ws_url, root
        self.hist: list[float] = []
        self.siste: dict = {"ms": None, "running": False, "deler": {}, "t": 0.0}

    def maal(self, trim_ms: float = 0.0, chunk: int = 1024, rate: int = 48000) -> dict:
        sq, dsp = pids("squeezelite"), pids("camilladsp")
        r = regn(pcm_status(self.root), sq, dsp, camilla_buffer(self.ws_url) if dsp else None, rate, chunk, trim_ms)
        if r["running"]:
            self.hist = (self.hist + [r["ms"]])[-SNITT:]
            r["ms"] = round(sum(self.hist) / len(self.hist), 1)
            self.siste = {**r, "t": time.time(), "maalinger": len(self.hist)}
        elif self.siste.get("ms") is not None:
            # spiller ikke nå: siste kjente verdi (bufrene er like store neste gang), justert for ny trim
            gammel_trim = (self.siste.get("deler") or {}).get("trim", 0.0)
            self.siste = {**self.siste, "ms": round(self.siste["ms"] - gammel_trim + trim_ms, 1), "running": False,
                          "deler": {**(self.siste.get("deler") or {}), "trim": round(trim_ms, 1)}}
        return self.siste


def trenger_endring(gammel: float | None, ny: float) -> bool:
    return gammel is None or abs(gammel - ny) >= MIN_ENDRING_MS
