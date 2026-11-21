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
    "sensor": {"filer": ["skjold-sensor.yaml", "skjold-sensor-d1mini.yaml"]
                        + [f"skjold-sensor-{v}{h}.yaml" for v in ("lys", "klima", "bevegelse") for h in ("", "-d1mini")], "kopier": [],
               "manifest": {"skjold-sensor-manifest.json": ("Skjold Sensor", [("ESP32", "skjold-sensor-esp32-firmware.bin"),
                                                                             ("ESP8266", "skjold-sensor-d1mini-firmware.bin")]),
                            **{f"skjold-sensor-{v}-manifest.json": (f"Skjold Sensor {n}", [("ESP32", f"skjold-sensor-{v}-esp32-firmware.bin"),
                                                                                           ("ESP8266", f"skjold-sensor-{v}-d1mini-firmware.bin")])
                               for v, n in (("lys", "Lys"), ("klima", "Klima"), ("bevegelse", "Bevegelse"))}}},
    "bryter": {"filer": ["skjold-bryter.yaml", "skjold-bryter-d1mini.yaml"], "kopier": [],
               "manifest": {"skjold-bryter-manifest.json": ("Skjold Bryter", [("ESP32", "skjold-bryter-esp32-firmware.bin"),
                                                                             ("ESP8266", "skjold-bryter-d1mini-firmware.bin")])}},
    "ir": {"filer": ["skjold-ir.yaml"], "kopier": ["skjold-ir-d1mini.yaml", "skjold-dokk.yaml"],
           "manifest": {"skjold-ir-manifest.json": ("Skjold IR", [("ESP32-C3", "skjold-ir-c3-firmware.bin"),
                                                                 ("ESP8266", "skjold-ir-d1mini-firmware.bin")]),
                        "skjold-dokk-manifest.json": ("Skjold Dokk (IR)", [("ESP32-C3", "skjold-dokk-firmware.bin")])}},
}


# Fastvareoppdatering fra nettsiden: «Fastvare» (update) i Home Assistant og Homey. Bare i de ferdige byggene: en
# fastvare du har bygget selv (med Wi-Fi i secrets.yaml) skal ikke byttes ut med en som mangler Wi-Fi-oppsettet.
NETT = "https://skjold-lab.com/flasher"
KILDE = {"skjold-sensor": f"{NETT}/sensor/manifest.json", "skjold-sensor-lys": f"{NETT}/sensor/lys/manifest.json",
         "skjold-sensor-klima": f"{NETT}/sensor/klima/manifest.json", "skjold-sensor-bevegelse": f"{NETT}/sensor/bevegelse/manifest.json", "skjold-bryter": f"{NETT}/bryter/manifest.json",
         "skjold-ir": f"{NETT}/ir/manifest.json", "skjold-kassett": f"{NETT}/kassett/manifest.json"}


def med_oppdatering(s: str, navn: str, versjon: str) -> str:
    """Legger til OTA fra nettsiden (http_request) og en «Fastvare»-oppdatering som sjekker manifestet hver 6. time.
    Prosjektversjonen settes til utgivelsen (skjold-v…), så oppdateringen vet hva som er installert."""
    kilde = KILDE[max((k for k in KILDE if navn.startswith(k + "-") or navn.startswith(k + ".")), key=len)]   # mest presise (sensor-lys før sensor)
    tls = "false" if re.search(r"^esp8266:", s, flags=re.M) else "true"   # ESP8266 kan ikke sjekke sertifikatet
    s, n = re.subn(r"^substitutions:\n", f'substitutions:\n  fastvare_kilde: {kilde}\n  fastvare_tls: "{tls}"\n', s, count=1, flags=re.M)
    if n != 1:
        raise SystemExit(f"fant ikke substitutions i {navn}")
    if re.search(r"^  project:.*\n    name: .+\n    version: .+\n", s, flags=re.M):
        s = re.sub(r"^(  project:.*\n    name: .+\n    version: ).+\n", lambda m: f'{m.group(1)}"{versjon}"\n', s, count=1, flags=re.M)
    else:
        s, n = re.subn(r"^(esphome:\n  name: .+\n  friendly_name: .+\n)",
                       lambda m: m.group(1) + f'  project:\n    name: {navn.replace("-", ".", 1)}\n    version: "{versjon}"\n', s, count=1, flags=re.M)
        if n != 1:
            raise SystemExit(f"fant ikke esphome-blokken i {navn}")
    s, n = re.subn(r"^ota:\n  - platform: esphome\n", "ota:\n  - platform: esphome\n  - platform: http_request\n", s, count=1, flags=re.M)
    if n != 1:
        raise SystemExit(f"fant ikke ota-blokken i {navn}")
    if not re.search(r"^http_request:", s, flags=re.M):
        s += "\nhttp_request:\n  verify_ssl: ${fastvare_tls}\n  timeout: 20s\n"
    s += ("\n# Ny fastvare fra skjold-lab.com: vises som «Fastvare» med Installer-knapp i Home Assistant og Homey\n"
          "update:\n  - platform: http_request\n    name: Fastvare\n    id: fastvare\n    source: ${fastvare_kilde}\n"
          "    update_interval: 6h\n")
    return s


def lag(kilde: str, navn: str) -> str:
    s, n = re.subn(r"^api:\n  encryption:\n    key: !secret \w+\n", "api:\n", kilde, flags=re.M)
    if n != 1:
        raise SystemExit(f"fant ikke api/encryption-blokken i {navn}")
    s, n = re.subn(r"^  ssid: !secret wifi_ssid\n  password: !secret wifi_password\n", "", s, flags=re.M)
    if n != 1:
        raise SystemExit(f"fant ikke wifi-hemmelighetene i {navn}")
    if "!secret" in s:
        raise SystemExit(f"{navn} har fortsatt !secret: " + ", ".join(sorted(set(re.findall(r"!secret (\w+)", s)))))
    s = med_oppdatering(s, navn, os.environ.get("VERSJON", "dev"))
    return f"# LAGET AV lag_ferdig.py – ikke rediger (kilde: esphome/{navn})\n" + s


def manifest(navn: str, builds, versjon: str) -> dict:
    return {"name": navn, "version": versjon, "new_install_prompt_erase": True,
            "builds": [{"chipFamily": chip, "improv": True, "parts": [{"path": fil, "offset": 0}]} for chip, fil in builds]}


def ota(ut: str) -> None:
    """Etter kompileringen: legger OTA-fila (skjold-…-ota.bin) og MD5-summen inn i manifestene, så «Fastvare» kan
    hente den. Nettleserflashingen bruker fortsatt hele fila (…-firmware.bin)."""
    import hashlib
    for mf in sorted(f for f in os.listdir(ut) if f.endswith("-manifest.json")):
        sti = os.path.join(ut, mf)
        m = json.load(open(sti, encoding="utf-8"))
        for b in m["builds"]:
            fil = b["parts"][0]["path"].replace("-firmware.bin", "-ota.bin")
            if os.path.exists(os.path.join(ut, fil)):
                md5 = hashlib.md5(open(os.path.join(ut, fil), "rb").read()).hexdigest()
                b["ota"] = {"path": fil, "md5": md5, "summary": f"{m['name']} {m['version']}",
                            "release_url": f"https://github.com/SebastianKristo/pult-forsterker/releases/tag/{m['version']}"}
        json.dump(m, open(sti, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        print(mf, "OTA:", ", ".join(b.get("ota", {}).get("path", "–") for b in m["builds"]))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "ota":
        ota(sys.argv[2] if len(sys.argv) > 2 else "ut")
        raise SystemExit(0)
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
