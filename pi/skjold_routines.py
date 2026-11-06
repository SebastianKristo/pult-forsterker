"""Rutiner med ett trykk: en navngitt liste med steg (strøm, kilde, radiofavoritt, URL, NRK, Music Assistant, volum,
vent, EQ, kunngjøring, sovetimer, nattmodus) – kjøres fra appene, web, S1-knapp, Siri, Home Assistant og Homey.

Steg med «rom» kjøres på den andre Skjold-enheten via dens /api/routines/steps (samme modul der).
"""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
import uuid

STEP_TYPES = ("power", "input", "preset", "play_url", "nrk", "ma", "volume", "wait", "eq", "announce", "sleep", "night", "podsum")
ICONS = ("sun", "moon", "music", "radio", "coffee", "bed", "home", "party", "news", "star")

TEMPLATES = [
    {"id": "morgen", "navn": "Morgen", "ikon": "sun", "steg": [
        {"type": "power", "verdi": True, "rom": "Kjøkken"},
        {"type": "nrk", "verdi": "Dagsnytt", "rom": "Kjøkken", "tittel": "Siste nyheter fra NRK"},
        {"type": "volume", "verdi": 25, "rom": "Kjøkken"},
        {"type": "wait", "verdi": 300},
        {"type": "preset", "verdi": "NRK P1", "rom": "Kjøkken"},
        {"type": "volume", "verdi": 25, "rom": "Kjøkken"}]},
    {"id": "leggetid", "navn": "Leggetid", "ikon": "moon", "steg": [
        {"type": "volume", "verdi": 15},
        {"type": "sleep", "verdi": 30},
        {"type": "night", "verdi": True}]},
]


def slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower().replace("æ", "ae").replace("ø", "o").replace("å", "a")).strip("-")
    return s or uuid.uuid4().hex[:8]


def clean_step(s: dict) -> dict:
    t = s.get("type")
    if t not in STEP_TYPES:
        raise ValueError(f"ukjent steg: {t}")
    out = {"type": t, "verdi": s.get("verdi")}
    if s.get("rom"):
        out["rom"] = str(s["rom"])[:60]
    if s.get("tittel"):
        out["tittel"] = str(s["tittel"])[:120]
    v = out["verdi"]
    if t in ("volume",):
        out["verdi"] = max(0, min(100, int(v)))
    elif t in ("wait",):
        out["verdi"] = max(0, min(3600, int(v)))
    elif t in ("sleep",):
        out["verdi"] = max(0, min(240, int(v)))
    elif t in ("power", "night"):
        out["verdi"] = bool(v) if not isinstance(v, str) else v.lower() not in ("av", "off", "false", "0")
    else:
        out["verdi"] = v if isinstance(v, (int, float, dict, list, bool)) else str(v or "")[:500]
    return out


def clean_routine(r: dict) -> dict:
    navn = str(r.get("navn") or "").strip()[:40]
    if not navn:
        raise ValueError("rutinen må ha et navn")
    steg = [clean_step(s) for s in (r.get("steg") or [])[:30]]
    if not steg:
        raise ValueError("rutinen må ha minst ett steg")
    return {"id": str(r.get("id") or slug(navn))[:40], "navn": navn,
            "ikon": r.get("ikon") if r.get("ikon") in ICONS else "star", "steg": steg}


def split_by_room(steg: list[dict], here: set[str]) -> list[tuple[str | None, list[dict]]]:
    """Grupper sammenhengende steg per rom (None = her), så rekkefølgen beholdes og hvert rom får sine steg samlet."""
    groups: list[tuple[str | None, list[dict]]] = []
    for s in steg:
        rom = s.get("rom")
        key = None if not rom or rom.lower() in here else rom
        if s["type"] == "wait":
            key = None   # vent her: stegene før er sendt, stegene etter venter (også i andre rom)
        if groups and groups[-1][0] == key:
            groups[-1][1].append(s)
        else:
            groups.append((key, [s]))
    return groups


class Routines:
    def __init__(self, ctx: dict, path: str):
        """ctx: do(step) – utfør ett steg lokalt; peers() – [{id,navn,base}]; names() – navn på denne enheten (lowercase)."""
        self.ctx, self.path = ctx, path
        self.running: dict[str, float] = {}
        self.last: dict = {}

    def load(self) -> list[dict]:
        try:
            with open(self.path) as fh:
                data = json.load(fh)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
        return [dict(t) for t in TEMPLATES]

    def _write(self, items: list[dict]) -> list[dict]:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path + ".tmp", "w") as fh:
            json.dump(items, fh, ensure_ascii=False)
        os.replace(self.path + ".tmp", self.path)
        return items

    def save(self, r: dict) -> list[dict]:
        r = clean_routine(r)
        items = [x for x in self.load() if x.get("id") != r["id"]]
        items.append(r)
        return self._write(items[:50])

    def delete(self, rid: str) -> list[dict]:
        return self._write([x for x in self.load() if x.get("id") != rid])

    def find(self, key: str) -> dict | None:
        k = str(key).strip().lower()
        for r in self.load():
            if r.get("id", "").lower() == k or r.get("navn", "").lower() == k:
                return r
        return None

    @staticmethod
    def _send_remote(base: str, steps: list[dict]) -> None:
        req = urllib.request.Request(base.rstrip("/") + "/api/routines/steps", method="POST",
                                     data=json.dumps({"steg": steps}).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10).read()

    def run_steps(self, steg: list[dict], sleep=time.sleep, send=None) -> list[str]:
        """Utfør stegene i rekkefølge. Returnerer en logg (brukes også i testene)."""
        log: list[str] = []
        peers = {str(p.get("navn") or "").lower(): p for p in self.ctx["peers"]()}
        for rom, group in split_by_room(steg, self.ctx["names"]()):
            if rom is None:
                for s in group:
                    if s["type"] == "wait":
                        log.append(f"vent {s['verdi']}"); sleep(int(s["verdi"])); continue
                    try:
                        self.ctx["do"](s); log.append(f"her {s['type']}")
                    except Exception as e:
                        log.append(f"feil {s['type']}: {e}")
            else:
                p = peers.get(rom.lower())
                if not p:
                    log.append(f"fant ikke rommet {rom}"); continue
                remote = [{k: v for k, v in s.items() if k != "rom"} for s in group]
                try:
                    (send or self._send_remote)(p["base"], remote); log.append(f"{rom}: {len(remote)} steg")
                except Exception as e:
                    log.append(f"{rom} feil: {e}")
        return log

    def run(self, key: str, background: bool = True) -> dict:
        r = self.find(key)
        if not r:
            raise KeyError(f"fant ikke rutinen «{key}»")
        def go():
            self.running[r["id"]] = time.time()
            try:
                self.last = {"id": r["id"], "t": time.time(), "log": self.run_steps(r["steg"])}
            finally:
                self.running.pop(r["id"], None)
        if background:
            threading.Thread(target=go, daemon=True).start()
        else:
            go()
        return {"ok": True, "id": r["id"], "navn": r["navn"]}
