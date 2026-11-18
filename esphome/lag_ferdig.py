#!/usr/bin/env python3
"""Ferdige fastvarer for nettleserflashing (skjold-lab.com/flasher/<produkt>/ og Skjold Flasher), uten egne hemmeligheter.

    python3 esphome/lag_ferdig.py sensor ut/   → skjold-sensor.yaml, skjold-sensor-d1mini.yaml, skjold-sensor-manifest.json
    python3 esphome/lag_ferdig.py bryter ut/   → skjold-bryter.yaml, skjold-bryter-d1mini.yaml, skjold-bryter-manifest.json
    python3 esphome/lag_ferdig.py ir ut/       → skjold-ir.yaml, skjold-ir-d1mini.yaml, skjold-dokk.yaml,
                                                 skjold-ir-manifest.json, skjold-dokk-manifest.json
Wi-Fi settes rett etter flashingen (Improv over USB i nettleseren) eller via tilgangspunktet. API-et er uten egen
krypteringsnøkkel (Home Assistant legger enheten til uten nøkkel; bygg selv for kryptert API). Ett manifest dekker
både ESP32-varianten og D1 mini (ESP8266): nettleseren velger fila etter brikken den finner.
Bygges av GitHub (skjold-release.yml).
"""
import json
import os
import re
import shutil
import sys

HER = os.path.dirname(os.path.abspath(__file__))

PRODUKT = {
    "sensor": {"filer": ["skjold-sensor.yaml", "skjold-sensor-d1mini.yaml"], "kopier": [],
               "manifest": {"skjold-sensor-manifest.json": ("Skjold Sensor", [("ESP32", "skjold-sensor-esp32-firmware.bin"),
                                                                             ("ESP8266", "skjold-sensor-d1mini-firmware.bin")])}},
    "bryter": {"filer": ["skjold-bryter.yaml", "skjold-bryter-d1mini.yaml"], "kopier": [],
               "manifest": {"skjold-bryter-manifest.json": ("Skjold Bryter", [("ESP32", "skjold-bryter-esp32-firmware.bin"),
                                                                             ("ESP8266", "skjold-bryter-d1mini-firmware.bin")])}},
    "ir": {"filer": ["skjold-ir.yaml"], "kopier": ["skjold-ir-d1mini.yaml", "skjold-dokk.yaml"],
           "manifest": {"skjold-ir-manifest.json": ("Skjold IR", [("ESP32-C3", "skjold-ir-c3-firmware.bin"),
                                                                 ("ESP8266", "skjold-ir-d1mini-firmware.bin")]),
                        "skjold-dokk-manifest.json": ("Skjold Dokk (IR)", [("ESP32-C3", "skjold-dokk-firmware.bin")])}},
}


def lag(kilde: str, navn: str) -> str:
    s, n = re.subn(r"^api:\n  encryption:\n    key: !secret \w+\n", "api:\n", kilde, flags=re.M)
    if n != 1:
        raise SystemExit(f"fant ikke api/encryption-blokken i {navn}")
    s, n = re.subn(r"^  ssid: !secret wifi_ssid\n  password: !secret wifi_password\n", "", s, flags=re.M)
    if n != 1:
        raise SystemExit(f"fant ikke wifi-hemmelighetene i {navn}")
    if "!secret" in s:
        raise SystemExit(f"{navn} har fortsatt !secret: " + ", ".join(sorted(set(re.findall(r"!secret (\w+)", s)))))
    return f"# LAGET AV lag_ferdig.py – ikke rediger (kilde: esphome/{navn})\n" + s


def manifest(navn: str, builds, versjon: str) -> dict:
    return {"name": navn, "version": versjon, "new_install_prompt_erase": True,
            "builds": [{"chipFamily": chip, "improv": True, "parts": [{"path": fil, "offset": 0}]} for chip, fil in builds]}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in PRODUKT:
        raise SystemExit("bruk: lag_ferdig.py sensor|bryter|ir [ut]")
    p, ut = PRODUKT[sys.argv[1]], sys.argv[2] if len(sys.argv) > 2 else "ut"
    os.makedirs(ut, exist_ok=True)
    for f in p["filer"]:
        with open(os.path.join(HER, f), encoding="utf-8") as fh:
            y = lag(fh.read(), f)
        with open(os.path.join(ut, f), "w", encoding="utf-8") as fh:
            fh.write(y)
    for f in p["kopier"]:   # tynne filer som tar inn en ferdig fil med packages
        shutil.copy(os.path.join(HER, f), os.path.join(ut, f))
    for mf, (navn, builds) in p["manifest"].items():
        with open(os.path.join(ut, mf), "w", encoding="utf-8") as fh:
            json.dump(manifest(navn, builds, os.environ.get("VERSJON", "dev")), fh, ensure_ascii=False, indent=2)
    print("Laget", ", ".join(p["filer"] + p["kopier"] + list(p["manifest"])), "i", ut)
