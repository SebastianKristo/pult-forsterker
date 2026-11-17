"""Skjold Stav – fjernkontrollen (esphome/skjold-fjernkontroll*.yaml) melder seg hos Skjold-en den styrer.

Staven sender POST /api/stav {id, navn, batteri, lader, versjon, tast, type} hvert 5. minutt og ved hver tast.
Skjold husker stavene (navn og sist sett, i stav.json) og holder batteri, lader og siste tast i minnet, så
Home Assistant-integrasjonen og Homey-appen kan vise Staven som egen enhet med batteri og tastehendelser.
"""
from __future__ import annotations

import json
import os
import threading
import time

TYPER = ("kort", "lang", "dobbel")
BORTE_S = 15 * 60          # ikke hørt fra på et kvarter (Staven sover mellom trykk): «ikke tilkoblet»


class Stav:
    def __init__(self, ctx: dict, path: str):
        self.ctx, self.path = ctx, path
        self.lock = threading.Lock()
        self.enheter: dict[str, dict] = {}
        self.seq = 0
        try:
            with open(path) as f:
                for k, v in (json.load(f).get("enheter") or {}).items():
                    if isinstance(v, dict):
                        self.enheter[str(k)] = {"navn": str(v.get("navn") or "Skjold Stav"), "sist": float(v.get("sist") or 0)}
        except (OSError, ValueError):
            pass

    def _lagre(self):
        try:
            os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
            tmp = self.path + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"enheter": {k: {"navn": v["navn"], "sist": v.get("sist", 0)} for k, v in self.enheter.items()}}, f)
            os.replace(tmp, self.path)
        except OSError:
            pass

    def meld(self, b: dict, ip: str = "") -> dict:
        """POST /api/stav fra Staven. Returnerer {ok, seq}."""
        dev = str(b.get("id") or "").strip().lower()[:40]
        if not dev:
            raise ValueError("mangler id")
        nå = time.time()
        tast = str(b.get("tast") or "")[:32]
        typ = str(b.get("type") or "kort")[:12]
        with self.lock:
            e = self.enheter.setdefault(dev, {"navn": "Skjold Stav", "sist": 0})
            ny = not e.get("sist")
            e["navn"] = str(b.get("navn") or e.get("navn") or "Skjold Stav")[:40]
            bat = b.get("batteri")
            if isinstance(bat, (int, float)) and 0 <= bat <= 100:
                e["batteri"] = int(bat)
            if "lader" in b:
                e["lader"] = bool(b.get("lader"))
            if b.get("versjon"):
                e["versjon"] = str(b["versjon"])[:24]
            if ip:
                e["ip"] = ip
            lagre = ny or nå - e.get("sist", 0) > 3600
            e["sist"] = nå
            if tast and typ != "gjenta":
                self.seq += 1
                e["tast"] = {"knapp": tast, "type": typ if typ in TYPER else "kort", "t": nå, "seq": self.seq}
            if lagre:
                self._lagre()
            seq = self.seq
        if tast and typ != "gjenta":
            cb = self.ctx.get("on_tast")
            if cb:
                try:
                    cb({"enhet": dev, "navn": e["navn"], "knapp": tast, "type": typ})
                except Exception:
                    pass
        return {"ok": True, "seq": seq}

    def config(self) -> dict:
        nå = time.time()
        with self.lock:
            return {"seq": self.seq, "enheter": {k: {**v, "tilkoblet": nå - v.get("sist", 0) < BORTE_S} for k, v in self.enheter.items()}}

    def glem(self, dev: str) -> dict:
        with self.lock:
            self.enheter.pop(str(dev).lower(), None)
            self._lagre()
        return self.config()
