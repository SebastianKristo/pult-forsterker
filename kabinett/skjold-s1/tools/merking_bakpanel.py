#!/usr/bin/env python3
"""Lasermerking for bakpanelet, generert fra samme posisjoner som revb_features.js (kortet rev B: to AUX, ingen SMA).
Erstatter designpakkens skjold_s1_merking_bakpanel.dxf (som har gamle posisjoner). Sett bakfra: x_view = −kasse-x, y = z.
Skriver ../marking/skjold_s1_merking_bakpanel_revb.dxf + .png. Lag: OUTLINE, HOLES (til plassering), MARKING (graveres)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxfkit import TypefaceFont, HELV_BOLD, HELV_REG, rrect, circle, dxf, preview   # noqa: E402

M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "marking")
CAP = 1.6          # versalhøyde (minste lasermerking klarer)
bold, reg = TypefaceFont(HELV_BOLD), TypefaceFont(HELV_REG)
V = lambda x: -x   # kasse-x -> sett bakfra

# geometri fra revb_features.js (kasse-x, z)
POSTS = [(-82.8, "L +"), (-63.8, "L -"), (-44.8, "R +"), (-25.8, "R -")]
AUX = [(-11, "AUX 2"), (-1, "AUX 1")]
USBC_X, USBC_Z = 15, (34, 24, 14); USBC_LBL = ("PC 1", "PC 2", "SERV")
RJ45, DC, GND, ROCKER = (44, 13.5), (44, 34), (62, 40), (78, 24)

outline = [rrect(0, 24.0, 186.6, 41.8, 7.3)]   # panelets flate del: x ±93,3, z 4,5 … 46,3
holes = [circle(V(x), 24, 4.25) for x, _ in POSTS] + [circle(V(x), 24, 3.2) for x, _ in AUX]
for z in USBC_Z:
    holes += [rrect(V(USBC_X), z, 9.6, 3.8, 1.9), rrect(V(USBC_X - 9.5), z, 5.4, 3.2, 1.6), rrect(V(USBC_X + 9.5), z, 5.4, 3.2, 1.6)]
holes += [rrect(V(RJ45[0]), RJ45[1], 17, 15.6, 0.5), rrect(V(RJ45[0] - 13), RJ45[1], 5.3, 3.3, 1.6), rrect(V(RJ45[0] + 13), RJ45[1], 5.3, 3.3, 1.6),
          circle(V(DC[0]), DC[1], 5.7), circle(V(GND[0]), GND[1], 1.7), rrect(V(ROCKER[0]), ROCKER[1], 19.4, 13, 0.5)]

mark = []
def T(font, txt, x, y, cap=CAP, tracking=0.1):
    polys, _ = font.text(txt, cap, x, y, tracking=tracking); mark.extend(polys)

for x, lbl in POSTS: T(bold, lbl, V(x), 36.3)                     # over polene (ring Ø19 -> topp z 33,5)
T(bold, "L", V(-73.3), 42.5, cap=2.2); T(bold, "R", V(-35.3), 42.5, cap=2.2)
for x, lbl in AUX: T(bold, lbl, V(x), 31.6)                       # over 3,5 mm-jackene (mutter Ø8 -> topp 28)
T(bold, "USB-C", V(USBC_X), 40.5)
for z, lbl in zip(USBC_Z, USBC_LBL): T(bold, lbl, V(USBC_X + 9.5 + 7.5), z)   # til venstre for hver kontakt (bakfra)
T(bold, "LAN", V(RJ45[0]), 24.6)                                  # mellom RJ45 (topp 21,3) og DC (bunn 28,3)
T(bold, "DC 19-24 V", V(DC[0]), 42.0)                             # over DC (topp 39,7)
T(bold, "GND", V(GND[0]), 44.3)                                   # over jordpunktet
T(bold, "I / O", V(ROCKER[0]), 33.6)                              # over vippebryteren (topp 30,5)

layers = [("OUTLINE", outline), ("HOLES", holes), ("MARKING", mark)]
with open(os.path.join(M, "skjold_s1_merking_bakpanel_revb.dxf"), "w") as fh:
    fh.write(dxf(layers))
preview(os.path.join(M, "skjold_s1_merking_bakpanel_revb.png"), (186.6, 41.8), layers)
print("skrev skjold_s1_merking_bakpanel_revb.dxf/.png")
