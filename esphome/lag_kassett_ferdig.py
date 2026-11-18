#!/usr/bin/env python3
"""Ferdig Skjold Kassett-fastvare for nettleserflashing (skjold-lab.com/flasher/kassett/ og Skjold Flasher).

Tar esphome/skjold-kassett.yaml og lager en utgave uten egne hemmeligheter:
  * Wi-Fi settes rett etter flashingen (Improv over USB i nettleseren), eller via nettet «Skjold Kassett» (captive portal),
  * API uten egen krypteringsnøkkel (Home Assistant legger den til uten nøkkel; bygg selv for kryptert API),
  * Skjold-adressen fylles inn av Skjold (pi/skjold_esphome.py).
Bygges av GitHub (skjold-release.yml):  python3 esphome/lag_kassett_ferdig.py ut/  &&  esphome compile ut/skjold-kassett.yaml
"""
import json
import os
import re
import sys

HER = os.path.dirname(os.path.abspath(__file__))


def lag(kilde: str) -> str:
    s = kilde
    # api: kryptering med !secret → uten nøkkel
    s, n = re.subn(r"^api:\n  encryption:\n    key: !secret \w+\n", "api:\n", s, flags=re.M)
    if n != 1:
        raise SystemExit("fant ikke api/encryption-blokken i skjold-kassett.yaml")
    # wifi: !secret → bare tilgangspunkt + Improv (nettleseren gir Wi-Fi etter flashing)
    s, n = re.subn(r"^wifi:\n(?:  .*\n)+", 'wifi:\n  ap: { ssid: "Skjold Kassett" }\n\nimprov_serial:\n', s, flags=re.M)
    if n != 1:
        raise SystemExit("fant ikke wifi-blokken i skjold-kassett.yaml")
    if "!secret" in s:
        raise SystemExit("ferdig-utgaven har fortsatt !secret: " + ", ".join(sorted(set(re.findall(r"!secret (\w+)", s)))))
    from lag_ferdig import med_oppdatering
    s = med_oppdatering(s, "skjold-kassett", os.environ.get("VERSJON", "dev"))
    return "# LAGET AV lag_kassett_ferdig.py – ikke rediger (kilde: esphome/skjold-kassett.yaml)\n" + s


def manifest(versjon: str) -> dict:
    return {"name": "Skjold Kassett", "version": versjon, "new_install_prompt_erase": True,
            "builds": [{"chipFamily": "ESP32-S3", "improv": True,
                        "parts": [{"path": "skjold-kassett-firmware.bin", "offset": 0}]}]}


if __name__ == "__main__":
    ut = sys.argv[1] if len(sys.argv) > 1 else "ut"
    os.makedirs(ut, exist_ok=True)
    with open(os.path.join(HER, "skjold-kassett.yaml"), encoding="utf-8") as fh:
        y = lag(fh.read())
    with open(os.path.join(ut, "skjold-kassett.yaml"), "w", encoding="utf-8") as fh:
        fh.write(y)
    with open(os.path.join(ut, "skjold-kassett-manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest(os.environ.get("VERSJON", "dev")), fh, ensure_ascii=False, indent=2)
    print("Laget", os.path.join(ut, "skjold-kassett.yaml"))
