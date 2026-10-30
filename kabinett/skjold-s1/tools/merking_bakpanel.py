#!/usr/bin/env python3
"""Tilpasser designpakkens merkefil for bakpanelet (../marking/skjold_s1_merking_bakpanel.dxf) til kortet rev B:
hullet merket «BT» (SMA i designet) er AUX 2, og «AUX» er AUX 1, og all tekst gjøres mindre (versalhøyde CAP mm, som på fronten). Skriver ../marking/skjold_s1_merking_bakpanel_revb.dxf + .png.
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
CAP = 1.6   # minste teksthøyde lasermerking klarer


def clusters(polys, gap=1.6):
    """Grupper polygoner som hører til samme tekst (nær hverandre i x, overlappende i y)."""
    boxes = [(min(q[0] for q in p), max(q[0] for q in p), min(q[1] for q in p), max(q[1] for q in p), p) for p in polys]
    boxes.sort(key=lambda b: b[0]); groups = []
    for b in boxes:
        for g in groups:
            if b[0] - g["x1"] < gap and b[2] < g["y1"] + 0.6 and b[3] > g["y0"] - 0.6:
                g["x1"] = max(g["x1"], b[1]); g["y0"] = min(g["y0"], b[2]); g["y1"] = max(g["y1"], b[3]); g["p"].append(b[4]); break
        else:
            groups.append({"x0": b[0], "x1": b[1], "y0": b[2], "y1": b[3], "p": [b[4]]})
    return groups


def shrink(polys, cap):
    """Skaler hver tekstgruppe om sitt eget senter slik at versalhøyden blir cap (nederste linje beholdes)."""
    out = []
    for g in clusters(polys):
        h = g["y1"] - g["y0"]; k = cap / h if h > cap else 1.0
        cx, y0 = (g["x0"] + g["x1"]) / 2, g["y0"]
        for p in g["p"]:
            out.append([(cx + (x - cx) * k, y0 + (y - y0) * k) for x, y in p])
    return out


layers["MARKING"] = shrink(layers["MARKING"], CAP)
font = TypefaceFont(HELV_BOLD)
for t, x in (("AUX 1", 14.0), ("AUX 2", 26.0)):
    new, _ = font.text(t, CAP, x, 32.6 + CAP / 2, tracking=0.1); layers["MARKING"] += new
order = [("OUTLINE", layers.get("OUTLINE", [])), ("HOLES", layers.get("HOLES", [])), ("MARKING", layers["MARKING"])]
with open(os.path.join(M, "skjold_s1_merking_bakpanel_revb.dxf"), "w") as fh:
    fh.write(dxf(order))
preview(os.path.join(M, "skjold_s1_merking_bakpanel_revb.png"), (190.6, 48), order)
print("skrev skjold_s1_merking_bakpanel_revb.dxf/.png")
