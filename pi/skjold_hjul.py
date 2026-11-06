"""Skjold Hjul – liten ESPHome-fjernkontroll (esphome/skjold-hjul.yaml): dreieknapp med trykk og 4 favorittknapper.

Hjulet sender hendelser til POST /api/hjul/event på «sin» Skjold:
  {"device": "hjul-ab12", "type": "rot", "delta": +1}      volum opp/ned (delta = antall hakk)
  {"type": "klikk"}  spill/pause · {"type": "dobbel"}  neste · {"type": "lang"}  bytt rom
  {"type": "fav", "n": 1..4}  start favoritt n · valgfritt "batteri": prosent
Velger hjulet et annet rom, videresendes volum/spill/pause til den Skjold-en (med "lokal": true), og favoritter
kjøres som rutinesteg med rom. Svaret ({rom, volum, spiller}) brukes til statuslyset. Ren logikk (pi/tests/test_hjul.py)."""
from __future__ import annotations

import json
import os
import threading
import time

TYPES = ("rot", "klikk", "dobbel", "lang", "fav", "hei")
HER = "Her"


def blank_cfg() -> dict:
    return {"favoritter": [None, None, None, None], "steg": 2, "enheter": {}}


class Hjul:
    """ctx: get_volume(), set_volume(v), transport(action), playing(), run_steps(steps), steps_for(card),
    peers() → [{navn, base}], forward(base, body) → dict, clean_card(card) → card."""

    def __init__(self, ctx: dict, path: str):
        self.ctx = ctx
        self.path = path
        self.lock = threading.Lock()

    def load(self) -> dict:
        try:
            with open(self.path) as fh:
                d = json.load(fh)
        except Exception:
            d = {}
        c = blank_cfg()
        if isinstance(d, dict):
            c.update({k: d[k] for k in c if k in d})
        favs = list(c["favoritter"] or [])[:4]
        c["favoritter"] = favs + [None] * (4 - len(favs))
        return c

    def _save(self, c: dict) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path + ".tmp", "w") as fh:
            json.dump(c, fh, ensure_ascii=False, indent=1)
        os.replace(self.path + ".tmp", self.path)

    def config(self) -> dict:
        c = self.load()
        c["rom"] = self.rooms()
        return c

    def set_config(self, b: dict) -> dict:
        with self.lock:
            c = self.load()
            if "steg" in b:
                c["steg"] = max(1, min(10, int(b["steg"])))
            if "favoritter" in b:
                favs = []
                for f in list(b["favoritter"] or [])[:4]:
                    if not f:
                        favs.append(None); continue
                    f = dict(f); f.setdefault("uid", "00")   # clean_card krever uid; ikke brukt for favoritter
                    cc = self.ctx["clean_card"](f); cc.pop("uid", None)
                    favs.append(cc)
                c["favoritter"] = favs + [None] * (4 - len(favs))
            for dev, e in (b.get("enheter") or {}).items():
                if dev in c["enheter"] and isinstance(e, dict):
                    if "navn" in e:
                        c["enheter"][dev]["navn"] = str(e["navn"])[:40]
                    if "rom" in e:
                        c["enheter"][dev]["rom"] = str(e["rom"] or HER)
            for dev in b.get("glem") or []:
                c["enheter"].pop(dev, None)
            self._save(c)
        return self.config()

    def rooms(self) -> list[str]:
        out = [HER]
        for p in self.ctx["peers"]():
            n = str(p.get("navn") or "")
            if n and n not in out:
                out.append(n)
        return out

    def _peer(self, rom: str):
        for p in self.ctx["peers"]():
            if str(p.get("navn") or "").lower() == rom.lower():
                return p
        return None

    def _local_state(self, rom: str = HER) -> dict:
        try:
            playing = bool(self.ctx["playing"]())
        except Exception:
            playing = False
        return {"rom": rom, "volum": int(self.ctx["get_volume"]()), "spiller": playing}

    def event(self, b: dict) -> dict:
        t = str(b.get("type") or "")
        if t not in TYPES:
            raise ValueError(f"ukjent hendelse «{t}»")
        if b.get("lokal"):   # videresendt fra en annen Skjold: utfør her
            return self._do_local(t, b, self.load())
        dev = str(b.get("device") or "hjul")[:40]
        with self.lock:
            c = self.load()
            e = c["enheter"].setdefault(dev, {"navn": "Skjold Hjul", "rom": HER})
            e["sist"] = int(time.time())
            if b.get("batteri") is not None:
                e["batteri"] = max(0, min(100, int(b["batteri"])))
            if t == "lang":
                rooms = self.rooms()
                cur = e.get("rom") or HER
                e["rom"] = rooms[(rooms.index(cur) + 1) % len(rooms)] if cur in rooms else HER
            self._save(c)
        rom = e.get("rom") or HER
        peer = None if rom == HER else self._peer(rom)
        if rom != HER and not peer:
            rom, peer = HER, None   # rommet er borte: styr denne
        if t == "fav":
            n = int(b.get("n") or 0)
            fav = c["favoritter"][n - 1] if 1 <= n <= 4 else None
            if not fav:
                raise ValueError(f"favoritt {n} er ikke satt opp")
            steps = self.ctx["steps_for"]({**fav, "rom": [] if rom == HER else [rom]})
            self.ctx["run_steps"](steps)
            res = self._local_state(rom) if rom == HER else {"rom": rom}
            res["favoritt"] = fav.get("navn", "")
            return res
        if peer and t in ("rot", "klikk", "dobbel"):
            fwd = {"type": t, "delta": b.get("delta"), "lokal": True}
            try:
                r = self.ctx["forward"](peer["base"], fwd) or {}
            except Exception as ex:
                return {"rom": rom, "feil": str(ex)}
            return {**r, "rom": rom}
        if t in ("lang", "hei"):
            return self._local_state(rom) if rom == HER else {"rom": rom}
        return {**self._do_local(t, b, c), "rom": rom}

    def _do_local(self, t: str, b: dict, c: dict) -> dict:
        if t == "rot":
            d = max(-20, min(20, int(b.get("delta") or 0)))
            self.ctx["set_volume"](max(0, min(100, int(self.ctx["get_volume"]()) + d * int(c.get("steg") or 2))))
        elif t == "klikk":
            self.ctx["transport"]("playpause")
        elif t == "dobbel":
            self.ctx["transport"]("next")
        return self._local_state()
