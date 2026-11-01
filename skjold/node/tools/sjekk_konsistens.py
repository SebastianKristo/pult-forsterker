#!/usr/bin/env python3
"""Sjekker at node_pins.json (schema 2, OLED + ADS1115), kabelliste.csv, kabling_node.svg og config.txt.node stemmer overens.
Kjør fra skjold/node/: python3 tools/sjekk_konsistens.py   (exit 1 ved feil)"""
import csv, json, os, re, sys
import xml.etree.ElementTree as ET

ROT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = json.load(open(os.path.join(ROT, "config", "node_pins.json"), encoding="utf-8"))
feil = []

# BCM → fysisk pinne (Pi 3/4, 40-pins)
BCM = {2: 3, 3: 5, 4: 7, 17: 11, 27: 13, 22: 15, 10: 19, 9: 21, 11: 23, 0: 27, 5: 29, 6: 31, 13: 33, 19: 35, 26: 37,
       14: 8, 15: 10, 18: 12, 23: 16, 24: 18, 25: 22, 8: 24, 7: 26, 1: 28, 12: 32, 16: 36, 20: 38, 21: 40}
GND = {6, 9, 14, 20, 25, 30, 34, 39}

# forventede ledninger fra json: pin -> (nett/gpio)
forv = {}
def f(pin, gpio, hva):
    if pin in forv: feil.append("pinne %d brukt to ganger (%s og %s)" % (pin, forv[pin], hva))
    forv[pin] = hva
    if gpio is not None and BCM.get(gpio) != pin:
        feil.append("%s: GPIO%s er pinne %s, ikke %s" % (hva, gpio, BCM.get(gpio), pin))
if P.get("schema") != 2: feil.append("node_pins.json schema er %r, forventet 2" % P.get("schema"))
for t, v in P["skjerm"]["pinner"].items():
    f(v["pin"], v["gpio"], "OLED " + t)
for t in ("VDD", "GND"):
    v = P["adc"]["pinner"][t]; f(v["pin"], v["gpio"], "ADC " + t)
for t in ("SDA", "SCL"):   # ADS1115 deler bussen med OLED-en (kjedet), samme GPIO
    if P["adc"]["pinner"][t]["gpio"] != P["skjerm"]["pinner"][t]["gpio"]: feil.append("ADS1115 %s er ikke på samme GPIO som OLED %s" % (t, t))
for k in P["knapper"]["liste"]:
    f(k["pin"], k["gpio"], "KNAPP " + k["id"])
f(P["knapper"]["gnd_pin"], None, "KNAPP GND")
for l in P["leds"]["liste"]:
    f(l["pin"], l["gpio"], "LED " + l["for"])
f(P["leds"]["gnd_pin"], None, "LED GND")
for pin, hva in forv.items():
    if hva.endswith("GND") and pin not in GND: feil.append("%s på pinne %d, som ikke er GND" % (hva, pin))
    if hva.endswith(("VCC", "VDD")) and pin not in (1, 17): feil.append("%s på pinne %d, som ikke er 3V3" % (hva, pin))
brukte_gpio = {g for g, p in BCM.items() if p in forv}
for g in brukte_gpio & {0, 1, 14, 15, 18, 19}:
    feil.append("GPIO%d er reservert men brukt" % g)
i2c_gpio = {2, 3}
knapp_led = {k["gpio"] for k in P["knapper"]["liste"]} | {l["gpio"] for l in P["leds"]["liste"]}
if knapp_led & i2c_gpio: feil.append("knapp/LED på I²C-pinne %s" % sorted(knapp_led & i2c_gpio))
if P["adc"]["adresse"].lower() == P["skjerm"]["adresse"].lower(): feil.append("OLED og ADS1115 har samme I²C-adresse")

# CSV
rader = list(csv.DictReader(open(os.path.join(ROT, "kabelliste.csv"), encoding="utf-8")))
pi_rader = [r for r in rader if r["fra"].startswith("Pi pinne")]
csv_pins = {int(r["fra"].split()[-1]) for r in pi_rader}
if csv_pins != set(forv):
    feil.append("CSV-pinner avviker: mangler %s, ekstra %s" % (sorted(set(forv) - csv_pins), sorted(csv_pins - set(forv))))
for r in pi_rader:
    m = re.match(r"GPIO(\d+)", r["nett"])
    if m and BCM.get(int(m.group(1))) != int(r["fra"].split()[-1]):
        feil.append("CSV %s: %s på feil pinne" % (r["id"], r["nett"]))

# SVG: alle ledning-id-er og komponentnavn må stå i tegningen
tekst = " ".join("".join(e.itertext()) for e in ET.parse(os.path.join(ROT, "kabling_node.svg")).iter() if e.tag.endswith("text"))
for r in rader:
    if r["id"] + " · " + r["lengde_mm"] + " mm" not in tekst: feil.append("SVG mangler %s/%s mm" % (r["id"], r["lengde_mm"]))
    if r["til"].rsplit(" ", 1)[0].split(" ")[0] not in tekst: feil.append("SVG mangler komponent for %s" % r["id"])

# config.txt.node
cfg = open(os.path.join(ROT, "config", "config.txt.node"), encoding="utf-8").read()
aktive = [l.strip() for l in cfg.splitlines() if l.strip() and not l.lstrip().startswith("#")]
for linje in P["config_txt"]["pakrevd"]:
    if linje not in aktive: feil.append("config.txt.node mangler '%s'" % linje)
inn = sorted(k["gpio"] for k in P["knapper"]["liste"])
ut = sorted(l["gpio"] for l in P["leds"]["liste"])
cfg_inn = sorted(int(x) for l in aktive if l.endswith("=ip,pu") for x in l[5:].split("=")[0].split(","))
cfg_ut = sorted(int(x) for l in aktive if re.search(r"=op,d[lh]$", l) for x in l[5:].split("=")[0].split(","))
if inn != cfg_inn: feil.append("config gpio inn %s != json %s" % (cfg_inn, inn))
if ut != cfg_ut: feil.append("config gpio ut %s != json %s" % (cfg_ut, ut))
if any(l.startswith("dtoverlay=") for l in aktive): feil.append("config.txt.node har aktiv dtoverlay (knapper/skjerm skal ikke ha overlay)")
if "dtparam=spi=on" in aktive or "dtparam=spi=off" not in aktive:
    feil.append("SPI må være AV (GPIO7 = SPI0 CE1 er knappen ▶▶)")
for t in ("ADS1115 SDA", "ADS1115 SCL", "POT pinne 1", "POT pinne 2", "POT pinne 3"):
    if not any(r["til"] == t for r in rader): feil.append("CSV mangler ledning til %s" % t)

if feil:
    print("FEIL:"); [print("  -", x) for x in feil]; sys.exit(1)
print("OK: %d ledninger, json/csv/svg/config stemmer" % len(rader))
