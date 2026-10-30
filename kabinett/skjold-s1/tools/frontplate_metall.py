#!/usr/bin/env python3
"""Frontplate i aluminium (PCBWay sheet metal, 3 mm 5052, bead blast + sort eloksering) med lasergravert tekst.

Lager i ../platemetall/skjold_s1_avrundet/:
  skjold_s1_frontplate_alu[_tft].dxf            kuttefil (lag CUT): omriss 178 × 46 R3, skjermvindu, knapper, encoder, jack, stud-hull
  skjold_s1_frontplate_alu_gravering.dxf        gravering (lag ENGRAVE) + omriss/hull til plassering (lag REF), sett forfra
  skjold_s1_frontplate_alu.png                  forhåndsvisning
Platen festes innenfra med 6 selvklinkende studs FH-M3-8 presset inn fra baksiden (hull Ø3,0), gjennom Ø3,4-hullene i frontpanelet,
M3-mutter innenfor. Akryl 2 mm røyksort kuttes til vinduet (61,6 × 37,6) og limes inn fra baksiden, flush med 1 mm forsenkning.
Koordinater: (x, y) med origo i platens senter, y opp – samme som kassens (x, z − 24). Fonter fra npm (@fontsource/sora).
"""
import math, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gravering import Face, rrect, circle, dxf, SORA6, SORA4, OUT   # noqa: E402  (gravering.py skriver også sine filer ved import – det er greit)

PW, PH, PR, T = 178.0, 46.0, 3.0, 3.0
VIEW = {"oled": (62.0, 38.0, 1.5), "tft": (62.0, 38.0, 1.5)}   # ett vindu for begge skjermene (som dispCut i revb_features.js)
DX = -27.0                                                     # skjermsenter
HOLES = [(-76, 0, 16.4), (22, 8.5, 12.4), (38, 8.5, 12.4), (22, -8.5, 12.4), (38, -8.5, 12.4), (66, 0, 7.4), (-76, -16, 6.4)]
STUDS = [(-83, -17), (-83, 17), (83, -17), (83, 17), (12, -15.5), (12, 15.5)]   # FH-M3: hull Ø3,0
LABELS = [("AIRPLAY", 22, 17.6), ("BT", 38, 17.6), ("AUX", 22, -17.6), ("USB", 38, -17.6), ("POWER", -76, 12.0), ("PULTFORSTERKER", 64, -19.6, 2.2)]

sora6, sora4 = Face(SORA6), Face(SORA4)


def hp_icon(cx, cy, s=0.9):
    """Hodetelefon-ikon: bøyle (halvring) + to øreklokker."""
    outer = [(cx + 2 * s * math.cos(a), cy + 2 * s * math.sin(a)) for a in [math.pi * i / 16 for i in range(17)]]
    inner = [(cx + 1.4 * s * math.cos(a), cy + 1.4 * s * math.sin(a)) for a in [math.pi * (16 - i) / 16 for i in range(17)]]
    polys = [outer + inner]
    for sx in (-1, 1):
        polys.append(rrect(cx + sx * 1.7 * s, cy - 0.6 * s, 1.1 * s, 1.9 * s, 0.3 * s))
    return polys


def build(variant):
    vw, vh, vr = VIEW[variant]
    cut = [rrect(0, 0, PW, PH, PR), rrect(DX, 0, vw, vh, vr)] + [circle(x, y, d / 2) for x, y, d in HOLES] + [circle(x, y, 1.5) for x, y in STUDS]
    eng = []
    for t, x, y, *sz in LABELS:
        polys, _ = sora6.text(t, sz[0] if sz else 2.6, x, y); eng += polys
    frame_o, frame_i = rrect(DX, 0, vw + 4, vh + 4, vr + 2), rrect(DX, 0, vw + 1.2, vh + 1.2, vr + 0.6)   # ramme 1,4 mm rundt vinduet
    eng.append(frame_o + frame_i[::-1])
    eng += hp_icon(-68.6, -16)
    return cut, eng


for variant in ("oled", "tft"):
    cut, eng = build(variant)
    sfx = "" if variant == "oled" else "_tft"
    with open(os.path.join(OUT, f"skjold_s1_frontplate_alu{sfx}.dxf"), "w") as fh:
        fh.write(dxf([("CUT", cut)]))
    if variant == "oled":
        with open(os.path.join(OUT, "skjold_s1_frontplate_alu_gravering.dxf"), "w") as fh:
            fh.write(dxf([("ENGRAVE", eng), ("REF", cut)]))
        try:
            from PIL import Image, ImageDraw
            import numpy as np
            S = 6; img = Image.new("RGB", (int(PW * S) + 40, int(PH * S) + 40), (26, 26, 28)); d = ImageDraw.Draw(img)
            tr = lambda p: (20 + (p[0] + PW / 2) * S, 20 + (PH / 2 - p[1]) * S)
            for p in cut:
                d.line([tr(q) for q in p] + [tr(p[0])], fill=(110, 110, 114), width=2)
            acc = np.zeros((img.size[1], img.size[0]), dtype=np.int32)
            for p in eng:
                m = Image.new("L", img.size, 0); ImageDraw.Draw(m).polygon([tr(q) for q in p], fill=1); acc += np.array(m, dtype=np.int32)
            px = np.array(img); px[acc % 2 == 1] = (210, 212, 215); Image.fromarray(px).save(os.path.join(OUT, "skjold_s1_frontplate_alu.png"))
        except ImportError:
            pass
print("skrev skjold_s1_frontplate_alu*.dxf + gravering")
