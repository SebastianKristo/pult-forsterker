"""Skjold Kassetthylle – hylle med NFC-leser per plass (esphome/skjold-hylle.yaml).

Omvendt av kassettspilleren: kassettene står i hylla, og den du **tar ut** spilles (på den parede Skjold-enheten,
samme oppsett som Kassett). Settes den tilbake i hylla, stopper avspillingen.

Hylla sender POST /api/hylle/event {device, plass: 1..n, uid, type: "inn"|"ut"} når en brikke dukker opp eller
forsvinner på en plass, og spør GET /api/hylle/lys?device=… for lysene: én bokstav per plass
  «s» = spiller (kassetten fra denne plassen spilles nå) · «i» = kassett står inne · «t» = tom plass
  «u» = ukjent brikke (ikke koblet til noe ennå).
Ren logikk – spilling/pause gjøres av daemonen via ctx (testes i pi/tests/test_hylle.py)."""
from __future__ import annotations

import json
import os
import threading
import time

MAKS_PLASSER = 12


def _tom() -> dict:
    return {"hyller": {}}


class Hylle:
    """ctx: spill(uid, device) → dict (som /api/nfc/scan), stopp(uid) → dict, kjent(uid) → bool, aktiv() → uid som spiller."""

    def __init__(self, ctx: dict, path: str):
        self.ctx = ctx
        self.path = path
        self.lock = threading.Lock()

    def load(self) -> dict:
        try:
            with open(self.path) as fh:
                d = json.load(fh)
            if isinstance(d, dict) and isinstance(d.get("hyller"), dict):
                return d
        except Exception:
            pass
        return _tom()

    def _save(self, d: dict) -> None:
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path + ".tmp", "w") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        os.replace(self.path + ".tmp", self.path)

    @staticmethod
    def _norm(uid: str) -> str:
        return "".join(ch for ch in str(uid or "").upper() if ch in "0123456789ABCDEF")

    def _hylle(self, d: dict, device: str, plasser: int | None = None) -> dict:
        h = d["hyller"].setdefault(device or "hylle", {"navn": "Kassetthylle", "plasser": {}, "ute": "", "sist": 0})
        if plasser:
            h["antall"] = max(1, min(MAKS_PLASSER, int(plasser)))
        return h

    def event(self, b: dict) -> dict:
        device = str(b.get("device") or "hylle")[:40]
        typ = str(b.get("type") or "")
        with self.lock:
            d = self.load()
            h = self._hylle(d, device, b.get("antall"))
            h["sist"] = int(time.time())
            if typ == "hei":
                self._save(d)
                return {"ok": True, "lys": self._lys(h)}
            try:
                plass = int(b.get("plass"))
            except (TypeError, ValueError):
                raise ValueError("plass mangler")
            if not 1 <= plass <= MAKS_PLASSER:
                raise ValueError("plass må være 1–%d" % MAKS_PLASSER)
            uid = self._norm(b.get("uid"))
            p = h["plasser"].setdefault(str(plass), {"uid": "", "inne": False})
            res = {"ok": True}
            if typ == "inn":
                if not uid:
                    raise ValueError("uid mangler")
                p.update(uid=uid, inne=True)
                if h.get("ute") == uid:          # satt tilbake → stopp
                    h["ute"] = ""
                    self._save(d)
                    res["stoppet"] = True
                    self.ctx["stopp"](uid)
                    return {**res, "lys": self._lys(h)}
            elif typ == "ut":
                uid = uid or p.get("uid", "")
                p["inne"] = False
                if uid and self.ctx["kjent"](uid):
                    h["ute"] = uid
                    self._save(d)
                    r = self.ctx["spill"](uid, device) or {}
                    res.update(spiller=True, ok=bool(r.get("ok", True)), feil=r.get("feil", ""))
                    return {**res, "lys": self._lys(h)}
            else:
                raise ValueError("type må være inn, ut eller hei")
            self._save(d)
            return {**res, "lys": self._lys(h)}

    def _lys(self, h: dict) -> str:
        aktiv = self._norm(self.ctx["aktiv"]() if self.ctx.get("aktiv") else "")
        ute = h.get("ute", "")
        if ute and aktiv and ute != aktiv:       # noe annet ble startet (app, kassettspiller) – hylla «slipper»
            ute = ""
        n = int(h.get("antall") or max([int(k) for k in h["plasser"]] or [6]))
        out = []
        for i in range(1, n + 1):
            p = h["plasser"].get(str(i)) or {}
            if not p.get("inne"):
                out.append("s" if ute and p.get("uid") == ute else "t")
            elif not self.ctx["kjent"](p.get("uid", "")):
                out.append("u")
            else:
                out.append("i")
        return "".join(out)

    def lys(self, device: str) -> str:
        with self.lock:
            d = self.load()
            h = d["hyller"].get(device or "hylle")
            return self._lys(h) if h else ""

    def status(self) -> dict:
        with self.lock:
            d = self.load()
            return {"hyller": [{"device": k, "navn": h.get("navn", "Kassetthylle"), "antall": h.get("antall"),
                                "sist": h.get("sist", 0), "ute": h.get("ute", ""), "lys": self._lys(h),
                                "plasser": {k2: v for k2, v in sorted(h["plasser"].items(), key=lambda x: int(x[0]))}}
                               for k, h in d["hyller"].items()]}

    def sett(self, b: dict) -> dict:
        with self.lock:
            d = self.load()
            dev = str(b.get("device") or "")
            if b.get("glem") and dev in d["hyller"]:
                del d["hyller"][dev]
            elif dev:
                h = self._hylle(d, dev, b.get("antall"))
                if b.get("navn"):
                    h["navn"] = str(b["navn"])[:40]
            self._save(d)
        return self.status()
