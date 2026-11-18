"""Innlogginger til musikktjenester delt mellom Skjold-enhetene i hjemmet (S1, Node, Touch, Core …).

Logger du inn (eller ut) på YouTube Music, Navidrome, Plex, Music Assistant eller SUB/WAVE på én enhet, skal det
gjelde på alle. Hver tjeneste har et tidsstempel for når innloggingen sist ble endret på en enhet. Ved endring sendes
den nye innloggingen til de andre med en gang, og hvert 5. minutt sammenligner enhetene med hverandre: den nyeste
vinner. Da får også en enhet som var av eller frakoblet da du logget inn, den nye innloggingen når den kommer tilbake.

GET  /api/delt → {tjeneste: {ts, data}}   (bare på hjemmenettet, som /api/settings)
POST /api/delt  {tjeneste: {ts, data}}    → tar imot det som er nyere enn det enheten har

Daemonen gir modulen funksjoner for å lese og skrive dataene (les/skriv), og for å finne de andre enhetene (peers).
"""
from __future__ import annotations

import json
import os
import threading
import time
import urllib.request

# tjeneste → (nøklene i innstillingene, nøkkelen som sier om den er satt opp)
INNSTILLINGER = {
    "ytm": (("ytmEn", "ytmUser", "ytmCookie"), "ytmCookie"),
    "nd": (("ndEn", "ndUrl", "ndUser", "ndPass"), "ndUrl"),
    "plex": (("plexEn", "plexUrl", "plexToken"), "plexUrl"),
    "ma": (("maEn", "maUrl", "maToken"), "maUrl"),
    "esphome": (("esphomeKey",), "esphomeKey"),
}
# tjenester som er plugins (oppsettet ligger i plugin-konfigurasjonen)
PLUGINS = {"subwave": (("enabled", "url", "user", "password", "name", "image", "extra"), "url")}
TJENESTER = tuple(INNSTILLINGER) + tuple(PLUGINS)
INTERVALL_S = 300


def tjenester_for(nokler) -> set:
    """Hvilke tjenester berøres av en endring i disse innstillingsnøklene?"""
    nokler = set(nokler)
    return {t for t, (ks, _) in INNSTILLINGER.items() if nokler & set(ks)}


def satt_opp(tjeneste: str, data: dict) -> bool:
    hoved = (INNSTILLINGER.get(tjeneste) or PLUGINS.get(tjeneste))[1]
    return bool((data or {}).get(hoved))


def flett(mine: dict, deres: dict) -> tuple[dict, set]:
    """Sammenligner to enheters innlogginger ({tjeneste: {ts, data}}).

    Gir (ta_imot, send): ta_imot = {tjeneste: {ts, data}} som denne enheten skal bruke, send = tjenestene der denne
    enheten har den nyeste og den andre bør få den. Nyest tidsstempel vinner. Uten tidsstempel (ts = 0, fra før
    delingen fikk tidsstempler) brukes det den andre har bare når denne enheten ikke er satt opp for tjenesten."""
    ta_imot, send = {}, set()
    for t in TJENESTER:
        m, d = mine.get(t) or {}, deres.get(t) or {}
        mt, dt = float(m.get("ts") or 0), float(d.get("ts") or 0)
        mdata, ddata = m.get("data") or {}, d.get("data") or {}
        if dt > mt:
            ta_imot[t] = {"ts": dt, "data": ddata}
        elif mt > dt:
            send.add(t)
        elif not mt and not dt:   # ingen vet når: fyll inn der det mangler
            if satt_opp(t, ddata) and not satt_opp(t, mdata):
                ta_imot[t] = {"ts": 0.0, "data": ddata}
            elif satt_opp(t, mdata) and not satt_opp(t, ddata):
                send.add(t)
    return ta_imot, send


class Deling:
    def __init__(self, fil: str, les, skriv, peers, own_id, aktiv=True, clock=time.time):
        """les(tjeneste) -> data, skriv(tjeneste, data) bruker dataene uten å dele dem videre,
        peers() -> [{id, navn, base}], own_id() -> denne enhetens id."""
        self.fil, self.les, self.skriv, self.peers, self.own_id, self.aktiv, self.clock = fil, les, skriv, peers, own_id, aktiv, clock
        self.lock = threading.RLock()
        self.ts: dict[str, float] = {}
        try:
            with open(fil) as fh:
                self.ts = {k: float(v) for k, v in (json.load(fh) or {}).items() if k in TJENESTER}
        except Exception:
            pass

    def _lagre(self):
        try:
            os.makedirs(os.path.dirname(self.fil), exist_ok=True)
            with open(self.fil + ".tmp", "w") as fh:
                json.dump(self.ts, fh)
            os.replace(self.fil + ".tmp", self.fil)
        except Exception as e:
            print("Delte innlogginger: fikk ikke lagret tidsstemplene:", e, flush=True)

    def alle(self) -> dict:
        with self.lock:
            return {t: {"ts": self.ts.get(t, 0.0), "data": self.les(t)} for t in TJENESTER}

    # --- endret her (fra appen, nettleseren eller skjermen)
    def endret(self, tjenester):
        tjenester = [t for t in tjenester if t in TJENESTER]
        if not tjenester:
            return
        with self.lock:
            nå = self.clock()
            for t in tjenester:
                self.ts[t] = nå
            self._lagre()
        if self.aktiv:
            threading.Thread(target=self._send_alle, args=(set(tjenester),), daemon=True).start()

    # --- mottatt fra en annen enhet
    def ta_imot(self, deres: dict) -> list:
        """POST /api/delt: bruk det som er nyere. Gir tjenestene som ble tatt i bruk."""
        with self.lock:
            nye, _ = flett(self.alle(), deres or {})
            for t, v in nye.items():
                self.skriv(t, v["data"])
                if v["ts"]:
                    self.ts[t] = v["ts"]
            if nye:
                self._lagre()
        if nye:
            print("Delte innlogginger: tok imot", ", ".join(sorted(nye)), flush=True)
        return sorted(nye)

    # --- nett
    def _post(self, base, data):
        req = urllib.request.Request(base.rstrip("/") + "/api/delt", data=json.dumps(data).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-Skjold-Peer": self.own_id()})
        urllib.request.urlopen(req, timeout=6).read()

    def _send_alle(self, tjenester):
        alle = self.alle()
        data = {t: alle[t] for t in tjenester}
        for p in self.peers():
            if p.get("id") == self.own_id():
                continue
            try:
                self._post(p["base"], data)
            except Exception as e:
                print("Delte innlogginger: fikk ikke sendt til", p.get("navn") or p["base"], "–", e, flush=True)

    def synk_en(self, p):
        """Sammenlign med én enhet: ta imot det som er nyere der, send det som er nyere her."""
        with urllib.request.urlopen(p["base"].rstrip("/") + "/api/delt", timeout=6) as r:
            deres = json.loads(r.read() or b"{}")
        self.ta_imot(deres)
        _, send = flett(self.alle(), deres)
        if send:
            alle = self.alle()
            self._post(p["base"], {t: alle[t] for t in send})

    def synk(self):
        for p in self.peers():
            if p.get("id") == self.own_id():
                continue
            try:
                self.synk_en(p)
            except Exception:
                pass   # av, eller en eldre Skjold uten /api/delt

    def lokke(self, forste=45):
        time.sleep(forste)   # la LAN-oppdagelsen finne de andre først
        while True:
            if self.aktiv:
                try:
                    self.synk()
                except Exception as e:
                    print("Delte innlogginger:", e, flush=True)
            time.sleep(INTERVALL_S)
