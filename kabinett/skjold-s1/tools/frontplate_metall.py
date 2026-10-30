#!/usr/bin/env python3
"""Frontplate i aluminium (PCBWay sheet metal, 3 mm 5052, bead blast + sort eloksering) med lasermerking.

Lager i ../platemetall/skjold_s1_avrundet/:
  skjold_s1_frontplate_alu[_tft].dxf       kuttefil (lag CUT): omriss 178 × 46 R3, skjermvindu, knapper, encoder, jack, stud-hull
  skjold_s1_frontplate_alu_merking.dxf     lasermerking (lag MARKING: BT, RADIO, AUX, USB (små), ramme rundt vinduet, hodetelefon-ikon,
                                           SKJOLD-logo under volumknotten)
                                           + omriss/hull til plassering (lag OUTLINE/HOLES). Sett forfra.
  skjold_s1_frontplate_alu.png             forhåndsvisning
Ingen tekst ved POWER-knappen og intet navn på fronten (navn og logo er på bunnplaten, se ../marking/).
Platen festes innenfra med 6 selvklinkende studs FH-M3-8 presset inn fra baksiden (hull Ø3,0), gjennom Ø3,4-hullene i frontpanelet,
M3-mutter innenfor. Hodetelefonkontakten PJ-392 skrus rett inn i et gjenget hull M6×0,5 (gjengebor Ø5,5) og ligger plant med forsiden –
ingen mutter foran (Loctite 222). Gjengelengden på kontakten er 4,4 mm, platen 3 mm, så 1,4 mm gjenge stikker ut bak; huset Ø8 går
gjennom et åpent spor i frontpanelet (se generate_sheet_round.js). Akryl 2 mm røyksort kuttes til vinduet (61,6 × 37,6) og limes inn fra baksiden, 1 mm forsenket.
Koordinater: (x, y) med origo i platens senter, y opp – samme som kassens (x, z − 24). Font: Helvetiker Bold (som designpakkens merkefiler).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxfkit import TypefaceFont, HELV_BOLD, rrect, circle, hp_icon, dxf, preview, read_dxf_polys   # noqa: E402

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "platemetall", "skjold_s1_avrundet")
PW, PH, PR = 178.0, 46.0, 3.0
VIEW = (62.0, 38.0, 1.5); DX = -27.0                              # ett vindu for OLED og TFT (dispCut i revb_features.js)
HOLES = [(-76, 0, 16.4), (22, 8.5, 12.4), (38, 8.5, 12.4), (22, -8.5, 12.4), (38, -8.5, 12.4), (66, 0, 7.4), (-76, -16, 5.5)]   # siste: Ø5,5 gjengebor, gjenges M6×0,5 (PJ-392 skrus rett i platen)
STUDS = [(-83, -17), (-83, 17), (83, -17), (83, 17), (12, -15.5), (12, 15.5)]   # FH-M3: hull Ø3,0
# knappene: oppe BT (AirPlay + Bluetooth) og RADIO, nede AUX og USB
LABELS = [("BT", 22, 16.4), ("RADIO", 38, 16.4), ("AUX", 22, -16.4), ("USB", 38, -16.4)]
LABEL_CAP = 1.8   # versalhøyde mm (lasermerking klarer ned til 1,6)
LOGO_SRC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "marking", "skjold_s1_merking_frontplate.dxf")   # designpakkens logo under volumknotten

font = TypefaceFont(HELV_BOLD)
outline = [rrect(0, 0, PW, PH, PR)]
holes = [rrect(DX, 0, *VIEW)] + [circle(x, y, d / 2) for x, y, d in HOLES] + [circle(x, y, 1.5) for x, y in STUDS]
mark = []
for t, x, y in LABELS:
    polys, _ = font.text(t, LABEL_CAP, x, y); mark += polys
vw, vh, vr = VIEW
mark.append(rrect(DX, 0, vw + 4, vh + 4, vr + 2) + rrect(DX, 0, vw + 1.2, vh + 1.2, vr + 0.6)[::-1])   # ramme 1,4 mm rundt vinduet
mark += hp_icon(-68.6, -16)
# logo (merke + SKJOLD) under volumknotten, hentet fra designpakkens frontplate-merking (samme koordinatsystem)
mark += [p for lay, p in read_dxf_polys(LOGO_SRC) if lay == "MARKING" and min(q[0] for q in p) > 50]

for sfx in ("", "_tft"):
    with open(os.path.join(OUT, f"skjold_s1_frontplate_alu{sfx}.dxf"), "w") as fh:
        fh.write(dxf([("CUT", outline + holes)]))
with open(os.path.join(OUT, "skjold_s1_frontplate_alu_merking.dxf"), "w") as fh:
    fh.write(dxf([("OUTLINE", outline), ("HOLES", holes), ("MARKING", mark)]))
preview(os.path.join(OUT, "skjold_s1_frontplate_alu.png"), (PW, PH), [("OUTLINE", outline), ("HOLES", holes), ("MARKING", mark)])
print("skrev skjold_s1_frontplate_alu*.dxf + merking")
