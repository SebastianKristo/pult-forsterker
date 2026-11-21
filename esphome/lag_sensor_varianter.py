#!/usr/bin/env python3
"""Lager de enklere Skjold Sensor-fastvarene fra skjold-sensor.yaml og skjold-sensor-d1mini.yaml.

    python3 esphome/lag_sensor_varianter.py

  skjold-sensor-lys[-d1mini].yaml        temperatur, fukt og lys (uten bevegelse)
  skjold-sensor-klima[-d1mini].yaml      bare temperatur og fukt
  skjold-sensor-bevegelse[-d1mini].yaml  temperatur, fukt og bevegelse (uten lys)
Sensorene som ikke er med, og alt som regnes ut fra dem (Mørkt, Lysnivå, Tilstedeværelse, Bevegelser …), tas ut,
så Home Assistant og Homey bare viser det sensoren faktisk har. Rediger hovedfilene, og kjør denne etterpå."""
import os
import re

HER = os.path.dirname(os.path.abspath(__file__))
# variant → (navn, visningsnavn, uten lys, uten bevegelse)
VARIANTER = {"lys": ("Skjold Sensor Lys", False, True), "klima": ("Skjold Sensor Klima", True, True),
             "bevegelse": ("Skjold Sensor Bevegelse", True, False)}
LYS = [r"id: lys\b", r"name: Mørkt\b", r"name: Lysnivå\b"]
BEV = [r"id: pir\b", r"id: bevegelse\b", r"id: tilstede\b", r"name: Bevegelser\b", r"name: Minutter siden bevegelse\b",
       r"id: bev_av\b", r"id: tils_av\b"]


def blokker(linjer):
    """Deler fila i toppnivå-seksjoner, og listeseksjonene i elementer («  - »)."""
    ut, i = [], 0
    while i < len(linjer):
        j = i + 1
        while j < len(linjer) and not re.match(r"^[A-Za-z_]", linjer[j]):
            j += 1
        ut.append(linjer[i:j]); i = j
    return ut


def fjern_elementer(seksjon, mønstre):
    hode, rest = [seksjon[0]], seksjon[1:]
    elem, cur = [], []
    for l in rest:
        if re.match(r"^  - ", l) and cur:
            elem.append(cur); cur = []
        cur.append(l)
    if cur:
        elem.append(cur)
    behold = [e for e in elem if not any(re.search(m, "".join(e)) for m in mønstre)]
    # kommentarlinjer rett før et fjernet element («# --- lys: …») står igjen som kommentarer; det er ufarlig
    return hode + [l for e in behold for l in e], len(elem) - len(behold)


def lag(kilde, variant):
    navn, uten_lys, uten_bev = VARIANTER[variant]
    s = open(os.path.join(HER, kilde), encoding="utf-8").read()
    mønstre = (LYS if uten_lys else []) + (BEV if uten_bev else [])
    ut = []
    for b in blokker(s.splitlines(keepends=True)):
        nøkkel = b[0].split(":")[0]
        if uten_bev and nøkkel in ("globals", "script"):
            continue
        if nøkkel in ("sensor", "binary_sensor", "text_sensor", "number"):
            b, _ = fjern_elementer(b, mønstre)
        ut.append(b)
    s = "".join(l for b in ut for l in b)
    if uten_lys:
        s = re.sub(r"^ *id\(lys\)\.update\(\);\n", "", s, flags=re.M)
    if uten_bev:
        s = re.sub(r"^  bevegelse_av: .*\n", "", s, flags=re.M)
        s = re.sub(r"^  tilstede_av: .*\n", "", s, flags=re.M)
    if uten_lys:
        s = re.sub(r"^  mork_lux: .*\n", "", s, flags=re.M)
    base = "skjold-sensor-" + variant
    s = re.sub(r"^  name: skjold-sensor\b.*$", f"  name: {base}", s, count=1, flags=re.M)
    s = re.sub(r"^  friendly_name: .*$", f"  friendly_name: {navn}", s, count=1, flags=re.M)
    s = re.sub(r'ap: \{ ssid: "Skjold Sensor[^"]*" \}', f'ap: {{ ssid: "{navn}" }}', s)
    hva = {"lys": "temperatur, luftfuktighet og lys", "klima": "temperatur og luftfuktighet", "bevegelse": "temperatur, luftfuktighet og bevegelse"}[variant]
    return f"# LAGET AV lag_sensor_varianter.py fra {kilde} – ikke rediger. {navn}: {hva}.\n" + s


if __name__ == "__main__":
    for v in VARIANTER:
        for kilde, hale in (("skjold-sensor.yaml", ""), ("skjold-sensor-d1mini.yaml", "-d1mini")):
            fil = f"skjold-sensor-{v}{hale}.yaml"
            open(os.path.join(HER, fil), "w", encoding="utf-8").write(lag(kilde, v))
            print("skrev", fil)
