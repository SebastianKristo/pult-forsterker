"""Senk musikken automatisk (ducking) og les opp et varsel: dørklokke, Home Assistant/Homey-hendelser og telefonsamtaler.

POST /api/duck {tekst?, lyd?, db?, sekunder?, kilde?, rom?}
  - db: hvor mye volumet senkes (negativt, standard fra innstillingene, −20 dB)
  - sekunder: hvor lenge musikken holdes nede etter varselet (standard 0 for tekst/lyd, 20 for «telefon» uten slutt)
  - tekst: leses opp (piper/espeak-ng), lyd: http(s)-adresse eller fil som spilles oppå
  - kilde: «ha», «homey», «telefon», «dørklokke», «api» – styrer om innstillingene tillater det
  - rom: liste med andre Skjold-adresser (http://host:8765) som også skal senke; tom = bare denne
  POST /api/duck {kilde: "telefon", slutt: true}   løft igjen når samtalen er over
GET/POST /api/duck/innstillinger {på, db, ha, homey, telefon, dørklokke, rom}

Volumet løftes mykt tilbake (1,5 s), og bare hvis ingen har endret volumet mens det var senket.
"""
import json
import os
import threading
import time
import urllib.request

KILDER = ("ha", "homey", "telefon", "dørklokke", "api")


def ducked_volume(v0, db):
    """Samme regel som dørklokka: −20 dB ≈ 33 trinn ned på Skjolds volumskala (0,6 dB per trinn rundt normalt nivå)."""
    if not v0:
        return 0
    return max(0, int(round(v0 + float(db) / 0.6)))


class Ducker:
    STD = {"på": True, "db": -20, "ha": True, "homey": True, "telefon": True, "dørklokke": True, "rom": []}

    def __init__(self, ctx, path=None, sleep=time.sleep):
        """ctx: get_volume(), set_volume(v), say(tekst) → wav-sti|None, announce(sti_eller_url), post(url, body)."""
        self.ctx, self.path, self.sleep = ctx, path, sleep
        self.cfg = json.loads(json.dumps(self.STD))
        self._lock = threading.Lock()
        self._call = None          # (v0, ducked) mens en telefonsamtale holder musikken nede
        if path and os.path.exists(path):
            try:
                self.cfg.update({k: v for k, v in json.load(open(path)).items() if k in self.STD})
            except Exception:
                pass

    def sett(self, b):
        for k in ("på", "ha", "homey", "telefon", "dørklokke"):
            if k in b:
                self.cfg[k] = bool(b[k])
        if b.get("db") is not None:
            self.cfg["db"] = max(-60, min(-3, int(b["db"])))
        if isinstance(b.get("rom"), list):
            self.cfg["rom"] = [str(x).rstrip("/") for x in b["rom"] if str(x).startswith(("http://", "https://"))][:20]
        if self.path:
            with open(self.path + ".tmp", "w") as f:
                json.dump(self.cfg, f)
            os.replace(self.path + ".tmp", self.path)
        return dict(self.cfg)

    def tillatt(self, kilde):
        return self.cfg["på"] and (kilde not in KILDER or kilde == "api" or self.cfg.get(kilde, True))

    def _fade(self, fra, til, steg=6, tid=1.5):
        for i in range(1, steg + 1):
            self.ctx["set_volume"](int(round(fra + (til - fra) * i / steg)))
            self.sleep(tid / steg)

    def _videresend(self, b):
        for base in self.cfg.get("rom") or []:
            try:
                self.ctx["post"](base + "/api/duck", {**b, "rom": [], "hop": True})
            except Exception:
                pass

    def duck(self, b):
        kilde = str(b.get("kilde") or "api")
        if not self.tillatt(kilde):
            return {"ok": False, "grunn": f"slått av for {kilde}"}
        if not b.get("hop"):
            threading.Thread(target=self._videresend, args=(b,), daemon=True).start()
        db = float(b["db"]) if b.get("db") is not None else float(self.cfg["db"])
        if kilde == "telefon":
            return self._telefon(b, db)
        with self._lock:
            v0 = self.ctx["get_volume"]()
            ned = ducked_volume(v0, db)
            if v0:
                self._fade(v0, ned, steg=3, tid=0.4)
            try:
                if b.get("tekst"):
                    wav = self.ctx["say"](str(b["tekst"])[:400])
                    if wav:
                        self.ctx["announce"](wav)
                if b.get("lyd"):
                    self.ctx["announce"](str(b["lyd"]))
                self.sleep(max(0.0, min(300.0, float(b.get("sekunder") or 0))))
            finally:
                if v0 and self.ctx["get_volume"]() == ned:     # ikke overstyr om noen har skrudd selv
                    self._fade(ned, v0)
        return {"ok": True, "fra": v0, "til": ned}

    def _telefon(self, b, db):
        """Telefonen ringer/er i samtale: hold musikken nede til appen sier «slutt» (maks 30 min)."""
        if b.get("slutt"):
            if self._call:
                v0, ned = self._call
                self._call = None
                if self.ctx["get_volume"]() == ned:
                    self._fade(ned, v0)
            return {"ok": True, "løftet": True}
        if self._call:
            return {"ok": True, "allerede": True}
        v0 = self.ctx["get_volume"]()
        ned = ducked_volume(v0, db)
        self._call = (v0, ned)
        if v0:
            self._fade(v0, ned, steg=3, tid=0.4)

        def tidsavbrudd(tok=self._call):
            self.sleep(1800)
            if self._call is tok:
                self._telefon({"slutt": True}, db)
        threading.Thread(target=tidsavbrudd, daemon=True).start()
        return {"ok": True, "fra": v0, "til": ned}


def http_post(url, body, timeout=4):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status
