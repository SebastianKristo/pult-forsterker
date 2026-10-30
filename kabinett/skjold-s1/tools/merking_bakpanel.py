#!/usr/bin/env python3
"""Tilpasser designpakkens merkefil for bakpanelet (../marking/skjold_s1_merking_bakpanel.dxf) til kortet rev B:
hullet merket «BT» (SMA i designet) er AUX 2, og «AUX» er AUX 1. Skriver ../marking/skjold_s1_merking_bakpanel_revb.dxf + .png.
Sett bakfra (x speilvendt i forhold til kassen), som originalen."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dxfkit import TypefaceFont, HELV_BOLD, read_dxf_polys, dxf, preview   # noqa: E402

M = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "marking")
polys = read_dxf_polys(os.path.join(M, "skjold_s1_merking_bakpanel.dxf"))
# fjern tekstene over AUX (x 11–17) og BT (x 24–28) – begge ligger på y 32,5–34,6
def drop(p):
    xs = [q[0] for q in p]; ys = [q[1] for q in p]
    return 32 < min(ys) and max(ys) < 35 and ((11 < min(xs) and max(xs) < 17) or (24 < min(xs) and max(xs) < 28))
layers = {}
for lay, p in polys:
    if lay == "MARKING" and drop(p):
        continue
    layers.setdefault(lay, []).append(p)
font = TypefaceFont(HELV_BOLD)
for t, x in (("AUX 1", 14.0), ("AUX 2", 26.0)):
    new, _ = font.text(t, 1.9, x, 33.55, tracking=0.1); layers["MARKING"] += new
order = [("OUTLINE", layers.get("OUTLINE", [])), ("HOLES", layers.get("HOLES", [])), ("MARKING", layers["MARKING"])]
with open(os.path.join(M, "skjold_s1_merking_bakpanel_revb.dxf"), "w") as fh:
    fh.write(dxf(order))
preview(os.path.join(M, "skjold_s1_merking_bakpanel_revb.png"), (190.6, 48), order)
print("skrev skjold_s1_merking_bakpanel_revb.dxf/.png")
