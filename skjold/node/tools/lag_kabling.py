#!/usr/bin/env python3
"""Lager node/kabling_node.svg og node/kabelliste.csv fra config/node_pins.json.

Kjør: python3 tools/lag_kabling.py   (fra skjold/node/)
Endre aldri SVG/CSV for hånd – endre node_pins.json og kjør dette på nytt.

Lengder: 3D-avstand fra Pi-headeren (bunnen) til komponenten (lokket), målt
fra kassens nullpunkt (se design/node/params.json og cad/generate_node.js),
+ 60 mm slakk så lokket kan vippes opp, rundet opp til nærmeste 10 mm.
"""
import csv, json, math, os, re
from xml.sax.saxutils import escape

HER = os.path.dirname(os.path.abspath(__file__))
ROT = os.path.dirname(HER)
PINS = json.load(open(os.path.join(ROT, "config", "node_pins.json"), encoding="utf-8"))
FARGE = PINS["fargekoder"]
SLAKK = 60

# --- geometri (mm, kassens koordinater) ---------------------------------
# Pi: hull x -39..19, y ±24.5. Headeren ligger langs +y-kanten (mot brukeren),
# pinne 1 i enden borte fra USB (−x). Topp av stiftene z ≈ 18.
def header_xyz(pin):
    return (-35.4 + ((pin - 1) // 2) * 2.54, 23.3 if pin % 2 else 25.8, 18.0)

SKJERM_XYZ = (-9.0, 6.0, 28.0)      # loddeøyene på skjerm-PCB [bekreft hvilken ende]
Q1_XYZ = (-4.0, 0.0, 26.0)           # transistor krympet inn ved skjermen
ENC = PINS["encoder"]
ENC_XYZ = (-27.0, 7.0, 24.0)
KNAPP_XYZ = {k["id"]: (k["kasse_x"], k["kasse_y"], 17.0) for k in PINS["knapper"]["liste"]}


def lengde(a, b):
    d = math.dist(a, b)
    return int(math.ceil((d + SLAKK) / 10.0) * 10)


def plugg(l):
    if l <= 100:
        return "Dupont hunn 10 cm, kuttet – hunn på Pi, loddet på komponent"
    if l <= 150:
        return "Dupont hunn 15 cm, kuttet – hunn på Pi, loddet på komponent"
    return "Dupont hunn 20 cm, kuttet – hunn på Pi, loddet på komponent"


# --- ledningsliste ---------------------------------------------------------
# (id, pi-pinne, komponent, terminal, nett, farge, xyz, merknad)
ledninger = []
sk = PINS["skjerm"]["pinner"]
def add(pin, komp, term, nett, farge, xyz, merk=""):
    ledninger.append(dict(pin=pin, komp=komp, term=term, nett=nett, farge=farge, xyz=xyz, merk=merk))

add(sk["VCC"]["pin"], "TFT", "VCC", "3V3", "rod", SKJERM_XYZ)
add(sk["GND"]["pin"], "TFT", "GND", "GND", "sort", SKJERM_XYZ)
for t in ["SCK", "SDA", "CS", "A0", "RESET"]:
    add(sk[t]["pin"], "TFT", t, sk[t]["nett"], "gul", SKJERM_XYZ)
add(1, "Q1", "S (source)", "3V3", "rod", Q1_XYZ, "Q1 AO3401: 10 kΩ S→G. D→TFT LED (15 mm, loddet)")
add(sk["LED"]["pin"], "Q1", "G (gate)", "GPIO%d" % sk["LED"]["gpio"], "oransje", Q1_XYZ, "1 kΩ i serie, krympet inn")
for t in ["A", "B", "SW"]:
    add(ENC[t]["pin"], "ENC", t, "GPIO%d" % ENC[t]["gpio"], "bla", ENC_XYZ)
add(ENC["C"]["pin"], "ENC", "C", "GND", "sort", ENC_XYZ, "SW-pinne 2 brokobles til C (15 mm)")
for k in PINS["knapper"]["liste"]:
    add(k["pin"], "KNAPP " + k["etikett"], "NO", "GPIO%d" % k["gpio"], "gronn", KNAPP_XYZ[k["id"]])
add(PINS["knapper"]["gnd_pin"], "KNAPP RADIO", "C", "GND", "sort", KNAPP_XYZ["radio"], "C-pinnene på alle 4 knappene lenkes med 20 mm broer")
navn = {k["id"]: k["etikett"] for k in PINS["knapper"]["liste"]}
r = PINS["leds"]["seriemotstand_ohm_direkte"]
for l in PINS["leds"]["liste"]:
    add(l["pin"], "LED " + navn[l["for"]], "LED+", "GPIO%d" % l["gpio"], "oransje", KNAPP_XYZ[l["for"]], "%d Ω i serie, krympet inn (valgfri)" % r)
add(PINS["leds"]["gnd_pin"], "LED RADIO", "LED−", "GND", "sort", KNAPP_XYZ["radio"], "LED− på alle 4 lenkes med 20 mm broer (valgfri)")

ledninger.sort(key=lambda w: w["pin"])
for i, w in enumerate(ledninger, 1):
    w["id"] = "W%02d" % i
    w["mm"] = lengde(header_xyz(w["pin"]), w["xyz"])

FARGENAVN = {"rod": "rød", "sort": "sort", "gul": "gul", "bla": "blå", "gronn": "grønn", "oransje": "oransje"}

with open(os.path.join(ROT, "kabelliste.csv"), "w", newline="", encoding="utf-8") as f:
    cw = csv.writer(f)
    cw.writerow(["id", "fra", "til", "nett", "farge", "lengde_mm", "pluggtype", "merknad"])
    for w in ledninger:
        cw.writerow([w["id"], "Pi pinne %d" % w["pin"], "%s %s" % (w["komp"], w["term"]), w["nett"],
                     FARGENAVN[w["farge"]], w["mm"], plugg(w["mm"]), w["merk"]])

# --- SVG -----------------------------------------------------------------
PIN_NAVN = {1: "3V3", 2: "5V", 3: "GPIO2", 4: "5V", 5: "GPIO3", 7: "GPIO4", 8: "GPIO14", 10: "GPIO15", 11: "GPIO17",
            12: "GPIO18", 13: "GPIO27", 15: "GPIO22", 16: "GPIO23", 17: "3V3", 18: "GPIO24", 19: "GPIO10", 21: "GPIO9",
            22: "GPIO25", 23: "GPIO11", 24: "GPIO8", 26: "GPIO7", 27: "ID_SD", 28: "ID_SC", 29: "GPIO5", 31: "GPIO6",
            32: "GPIO12", 33: "GPIO13", 35: "GPIO19", 36: "GPIO16", 37: "GPIO26", 38: "GPIO20", 40: "GPIO21"}
for g in PINS["gnd_pinner"]:
    PIN_NAVN[g] = "GND"

W, H = 1180, 880
OX, EX, Y0, DY = 470, 540, 110, 26  # oddetall-kolonne, partall-kolonne
def py(pin): return Y0 + ((pin - 1) // 2) * DY
def px(pin): return OX if pin % 2 else EX

out = []
o = out.append
o('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" font-family="Helvetica, Arial, sans-serif">' % (W, H, W, H))
o('<rect width="100%" height="100%" fill="#ffffff"/>')
o('<text x="24" y="38" font-size="22" font-weight="bold">Skjold Node – kabling (rev %s)</text>' % escape(PINS["revisjon"]))
o('<text x="24" y="60" font-size="12" fill="#555">Generert fra config/node_pins.json av tools/lag_kabling.py. BCM-numre. Pi sett ovenfra, pinne 1 nærmest SD-kortet. Alle innganger: intern pull-up, aktiv lav.</text>')

# header
o('<rect x="%d" y="%d" width="%d" height="%d" rx="6" fill="#20232a"/>' % (OX - 16, Y0 - 18, EX - OX + 32, 19 * DY + 36))
o('<text x="%d" y="%d" font-size="12" text-anchor="middle" font-weight="bold">Pi 40-pins header</text>' % ((OX + EX) / 2, Y0 - 26))
brukt = {w["pin"] for w in ledninger}
for pin in range(1, 41):
    x, y = px(pin), py(pin)
    fill = "#d4af37" if pin in brukt else "#6b6f78"
    o('<circle cx="%d" cy="%d" r="6" fill="%s" stroke="#000" stroke-width="0.8"/>' % (x, y, fill))
    o('<text x="%d" y="%d" font-size="8" fill="#fff" text-anchor="middle">%d</text>' % ((OX + EX) / 2 + (-14 if pin % 2 else 14), y + 3, pin))

# komponentbokser og terminaler
komp_bokser = {}
def boks(navn, x, y, w, h, terms, side):
    """terms: liste av terminalnavn; side 'L' = terminaler på venstre kant, 'R' høyre."""
    o('<rect x="%d" y="%d" width="%d" height="%d" rx="6" fill="#f4f1ea" stroke="#333" stroke-width="1.2"/>' % (x, y, w, h))
    o('<text x="%d" y="%d" font-size="12" font-weight="bold" text-anchor="middle">%s</text>' % (x + w / 2, y + 16, escape(navn)))
    pos = {}
    for i, t in enumerate(terms):
        ty = y + 32 + i * 22
        tx = x if side == "L" else x + w
        o('<circle cx="%d" cy="%d" r="4" fill="#fff" stroke="#333"/>' % (tx, ty))
        o('<text x="%d" y="%d" font-size="10" text-anchor="%s">%s</text>' % (tx + (8 if side == "L" else -8), ty + 3, "start" if side == "L" else "end", escape(t)))
        pos[t] = (tx, ty)
    komp_bokser[navn] = pos

# venstre side (oddetallspinner): encoder + knapper
boks("ENC", 120, 170, 120, 120, ["C", "A", "B", "SW"], "R")
for i, k in enumerate(PINS["knapper"]["liste"]):
    boks("KNAPP " + k["etikett"], 120, 400 + i * 90 if False else 380 + i * 82, 120, 62, ["NO", "C"] if k["id"] == "radio" else ["NO"], "R")
# høyre side: Q1, TFT, LED-ringer
boks("Q1", 860, 92, 110, 66, ["S (source)", "G (gate)"], "L")
boks("TFT", 860, 190, 130, 172, ["VCC", "GND", "SCK", "SDA", "CS", "A0", "RESET", "LED ← Q1 D"], "L")
for i, l in enumerate(PINS["leds"]["liste"]):
    n = "LED " + navn[l["for"]]
    boks(n, 860, 420 + i * 72, 130, 58 if l["for"] == "radio" else 40, ["LED+", "LED−"] if l["for"] == "radio" else ["LED+"], "L")

# Q1 drain → TFT LED (kort bro)
q, t = komp_bokser["Q1"], komp_bokser["TFT"]
o('<path d="M970,125 H1010 V%d H990" fill="none" stroke="%s" stroke-width="3"/>' % (t["LED ← Q1 D"][1], FARGE["oransje"]))
o('<text x="1014" y="140" font-size="10">D → LED</text>')
o('<text x="1014" y="153" font-size="10">(bro 15 mm)</text>')
o('<text x="1000" y="104" font-size="10" text-anchor="middle">AO3401</text>')
o('<text x="1000" y="115" font-size="9" text-anchor="middle" fill="#555">10k S–G</text>')

lane_l, lane_r, lane_gap, bunn = 0, 0, 0, 0
for w in ledninger:
    pin = w["pin"]
    x0, y0 = px(pin), py(pin)
    x1, y1 = komp_bokser[w["komp"]][w["term"]]
    c = FARGE[w["farge"]]
    if x1 < OX:  # mål til venstre – bare oddetall
        lx = 420 - lane_l * 11; lane_l += 1
        d = "M%d,%d H%d V%d H%d" % (x0, y0, lx, y1, x1)
        lab = (lx - 4, y1 - 4, "end")
    elif pin % 2 == 0:  # partall → høyre
        lx = 620 + lane_r * 13; lane_r += 1
        d = "M%d,%d H%d V%d H%d" % (x0, y0, lx, y1, x1)
        lab = (x1 - 6, y1 - 4, "end")
    else:  # oddetall → høyre: ned gjennom gapet, under headeren, opp på høyre side
        gx = OX + 14 + lane_gap * 9; lane_gap += 1
        by = Y0 + 19 * DY + 40 + bunn * 10; bunn += 1
        lx = 800 - (bunn - 1) * 12
        d = "M%d,%d H%d V%d H%d V%d H%d" % (x0, y0, gx, by, lx, y1, x1)
        lab = (x1 - 6, y1 - 4, "end")
    o('<path d="%s" fill="none" stroke="%s" stroke-width="3" stroke-linejoin="round"/>' % (d, c))
    o('<text x="%d" y="%d" font-size="9" font-weight="bold" text-anchor="%s" fill="#000">%s · %d mm</text>' % (lab[0], lab[1], lab[2], w["id"], w["mm"]))
    m = re.search(r"(\d+ ?k?)Ω i serie", w["merk"])
    if m:
        ohm = m.group(1).replace(" ", "")
        mx = x1 - 40
        o('<rect x="%d" y="%d" width="22" height="9" fill="#fff" stroke="#000"/>' % (mx - 11, y1 - 4))
        o('<text x="%d" y="%d" font-size="8" text-anchor="middle">%s</text>' % (mx + 26, y1 + 8, ohm + "Ω"))

# pinnenavn sist, med hvit kant så de leses over ledningene
HALO = 'stroke="#fff" stroke-width="3" paint-order="stroke"'
for pin in range(1, 41):
    lab, y = PIN_NAVN.get(pin, ""), py(pin)
    if pin % 2:
        o('<text x="%d" y="%d" font-size="10" text-anchor="end" fill="#333" %s>%s</text>' % (OX - 20, y + 3, HALO, lab))
    else:
        o('<text x="%d" y="%d" font-size="10" fill="#333" %s>%s</text>' % (EX + 20, y + 3, HALO, lab))

# forklaring
ly = 800
for i, (k, t) in enumerate([("rod", "3V3"), ("sort", "GND"), ("gul", "SPI / skjerm"), ("bla", "encoder"), ("gronn", "knapper"), ("oransje", "LED / bakgrunnslys")]):
    x = 24 + i * 150
    o('<line x1="%d" y1="%d" x2="%d" y2="%d" stroke="%s" stroke-width="4"/>' % (x, ly, x + 30, ly, FARGE[k]))
    o('<text x="%d" y="%d" font-size="11">%s</text>' % (x + 36, ly + 4, t))
o('<text x="24" y="830" font-size="11" fill="#333">Knapper og LED-ringer: C/LED− lenkes med 20 mm broer mellom knappene; én GND-ledning fra RADIO. LED-ringer er valgfrie (3–6 V-variant, %d Ω i serie). Encoder: SW pinne 2 broes til C.</text>' % r)
o('<text x="24" y="848" font-size="11" fill="#333">Lengder = 3D-avstand Pi→lokk + %d mm slakk for å vippe lokket. Ingen ledninger på GPIO2/3 (I²C), 14/15 (UART), 18/19 (reservert I²S).</text>' % SLAKK)
o('</svg>')
open(os.path.join(ROT, "kabling_node.svg"), "w", encoding="utf-8").write("\n".join(out) + "\n")
print("skrev kabling_node.svg og kabelliste.csv (%d ledninger)" % len(ledninger))
