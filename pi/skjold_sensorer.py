"""Skjold Sensor (esphome/skjold-sensor*.yaml) i Skjold: finner sensorene på nettet og følger verdiene deres.

Sensorene annonserer seg med mDNS (_esphomelib._tcp, TXT project_name=skjold.sensor). For hver sensor holder Skjold
en åpen hendelsesstrøm mot ESPHome-webserveren (GET /events, server-sent events), så bevegelse og andre endringer
kommer med en gang. Første melding etter oppkobling har alle verdiene med navn («Temperatur»); senere endringer har
bare id («sensor/Temperatur» eller eldre «sensor-temperatur»).

GET /api/sensorer i daemonen gir {enheter: {mac: {navn, ip, tilkoblet, sist, verdier: {Temperatur: 21.4, …}}}}, som
Home Assistant-integrasjonen viser som egne Skjold Sensor-enheter.
"""
from __future__ import annotations

import http.client
import json
import re
import subprocess
import threading
import time
import urllib.parse

PROSJEKT = "skjold.sensor"
# Innstillinger som kan endres utenfra: navn i ESPHome → domene (POST /number/<navn>/set?value= eller /switch/<navn>/turn_on|off)
INNSTILLINGER = {"Oppdateringsintervall": "number", "Bevegelse av etter": "number",
                 "Tilstedeværelse av etter": "number", "Status-LED": "switch",
                 "Fastvare": "update"}   # ny fastvare fra skjold-lab.com (bare i de ferdige byggene)


def sti_for(navn: str, verdi) -> str:
    """REST-stien i ESPHome-webserveren som setter innstillingen `navn` til `verdi`."""
    domene = INNSTILLINGER.get(navn)
    if not domene:
        raise ValueError(f"ukjent innstilling: {navn}")
    n = urllib.parse.quote(navn, safe="")
    if domene == "update":
        return f"/update/{n}/install"
    if domene == "switch":
        return f"/switch/{n}/{'turn_on' if verdi in (True, 1, 'on', 'ON', 'true') else 'turn_off'}"
    return f"/number/{n}/set?value={float(verdi):g}"
SOK_S = 60


def parse_avahi(tekst: str) -> dict[str, dict]:
    """`avahi-browse -rpt _esphomelib._tcp` → {mac: {navn, ip, port}} for Skjold Sensor (project_name=skjold.sensor)."""
    ut: dict[str, dict] = {}
    for linje in tekst.splitlines():
        if not linje.startswith("="):
            continue
        f = linje.split(";")
        if len(f) < 10:
            continue
        ip, port, txt = f[7], f[8], ";".join(f[9:])
        kv = dict(re.findall(r'"([^"=]+)=([^"]*)"', txt))
        if kv.get("project_name") != PROSJEKT or ":" in ip:   # bare IPv4
            continue
        mac = (kv.get("mac") or f[3]).lower()
        ut[mac] = {"navn": kv.get("friendly_name") or f[3].replace("\\032", " "), "ip": ip, "port": 80}
    return ut


def ent_navn(o: dict) -> str:
    if o.get("name"):
        return str(o["name"])
    i = str(o.get("id") or "")
    return i.split("/")[-1] if "/" in i else re.sub(r"^[a-z_]+-", "", i)


def verdi(o: dict):
    if "current_version" in o or str(o.get("id", "")).startswith("update"):   # «Fastvare» (update)
        return {"installert": o.get("current_version"), "siste": o.get("latest_version") or o.get("value"),
                "tilstand": o.get("state")}
    v = o.get("value", o.get("state"))
    if isinstance(v, str):
        if v in ("ON", "on", "true"):
            return True
        if v in ("OFF", "off", "false"):
            return False
    if isinstance(v, float) and v != v:   # NaN
        return None
    return v


def les_sse(linjer, ved_verdi) -> None:
    """Leser server-sent events (linjer uten linjeskift, \\r fjernet) og kaller ved_verdi(navn, verdi) for state-meldinger."""
    ev, data = "message", ""
    for linje in linjer:
        linje = linje.rstrip("\r")
        if linje == "":
            if ev == "state" and data:
                try:
                    o = json.loads(data)
                    ved_verdi(ent_navn(o), verdi(o))
                except ValueError:
                    pass
            ev, data = "message", ""
        elif linje.startswith("event:"):
            ev = linje[6:].strip()
        elif linje.startswith("data:"):
            data += linje[5:].strip()


class Sensorer:
    def __init__(self, ctx: dict | None = None):
        self.ctx = ctx or {}
        self.lock = threading.Lock()
        self.enheter: dict[str, dict] = {}
        self._traader: dict[str, threading.Thread] = {}

    def start(self):
        threading.Thread(target=self._sok_lokke, daemon=True).start()

    # --- søk ---
    def _sok_lokke(self):
        while True:
            try:
                r = subprocess.run(["avahi-browse", "-rpt", "_esphomelib._tcp"], capture_output=True, text=True, timeout=20)
                self.oppdater(parse_avahi(r.stdout))
            except FileNotFoundError:
                return   # uten avahi (f.eks. i tester): ingen søk
            except Exception as e:
                print("Skjold Sensor: søk feilet:", repr(e), flush=True)
            time.sleep(SOK_S)

    def oppdater(self, funnet: dict[str, dict]):
        with self.lock:
            for mac, f in funnet.items():
                e = self.enheter.setdefault(mac, {"verdier": {}, "tilkoblet": False, "sist": 0})
                e.update(navn=f["navn"], ip=f["ip"], port=f.get("port", 80))
                t = self._traader.get(mac)
                if not t or not t.is_alive():
                    t = threading.Thread(target=self._folg, args=(mac,), daemon=True)
                    self._traader[mac] = t
                    t.start()

    # --- hendelsesstrømmen per sensor ---
    def _folg(self, mac: str):
        while True:
            with self.lock:
                e = self.enheter.get(mac) or {}
                ip, port = e.get("ip"), e.get("port", 80)
            if not ip:
                return
            try:
                c = http.client.HTTPConnection(ip, port, timeout=60)   # ESPHome sender ping hvert ~10. s
                c.request("GET", "/events", headers={"Accept": "text/event-stream"})
                r = c.getresponse()
                if r.status != 200:
                    raise OSError(f"svarte {r.status}")
                with self.lock:
                    self.enheter[mac]["tilkoblet"] = True

                def linjer():
                    while True:
                        b = r.readline()
                        if not b:
                            return
                        yield b.decode("utf-8", "replace").rstrip("\n")

                les_sse(linjer(), lambda n, v: self._sett(mac, n, v))
            except Exception:
                pass
            with self.lock:
                if mac in self.enheter:
                    self.enheter[mac]["tilkoblet"] = False
            time.sleep(10)

    def _sett(self, mac: str, navn: str, v):
        with self.lock:
            e = self.enheter.get(mac)
            if e is None:
                return
            if e["verdier"].get(navn) != v:
                e["verdier"][navn] = v
                e["sist"] = time.time()
                endret = True
            else:
                endret = False
        if endret and navn in ("Bevegelse", "Tilstedeværelse") and self.ctx.get("changed"):
            self.ctx["changed"]()

    def sett(self, mac: str, navn: str, verdi) -> None:
        """Endrer en innstilling på sensoren (se INNSTILLINGER). Den nye verdien kommer tilbake i hendelsesstrømmen."""
        sti = sti_for(navn, verdi)
        with self.lock:
            e = self.enheter.get(mac) or {}
            ip, port = e.get("ip"), e.get("port", 80)
        if not ip:
            raise LookupError("fant ikke sensoren")
        c = http.client.HTTPConnection(ip, port, timeout=8)
        try:
            c.request("POST", sti, headers={"Content-Length": "0"})
            r = c.getresponse()
            r.read()
            if not 200 <= r.status < 300:
                raise OSError(f"sensoren svarte {r.status}")
        finally:
            c.close()
        if INNSTILLINGER[navn] != "update":   # oppdateringen melder fra selv i hendelsesstrømmen
            self._sett(mac, navn, (verdi in (True, 1, "on", "ON", "true")) if INNSTILLINGER[navn] == "switch" else float(verdi))

    def status(self) -> dict:
        with self.lock:
            return {"enheter": {m: {k: (dict(v) if isinstance(v, dict) else v) for k, v in e.items()} for m, e in self.enheter.items()}}
