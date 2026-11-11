#!/usr/bin/env python3
"""Frilegger produktbilder: den ensfargede bakgrunnen (lys studiobakgrunn fra OpenSCAD/three-renderne) blir gjennomsiktig,
så bildene kan stå rett på den mørke siden uten en synlig boks rundt.

Bakgrunnen finnes ved å fylle fra bildekanten (bare det som henger sammen med kanten fjernes – lyse flater inne i
produktet beholdes). Kanten får myk overgang, og fargen i overgangen renses for bakgrunnsfargen (ingen lys glorie).
Bildet beskjæres til produktet med litt luft.

    python3 tools/frilegg.py assets/img/touch-skraa.jpg [flere …]      → assets/img/touch-skraa-fri.webp + .png
Krever Pillow, numpy og scipy."""
import sys
import numpy as np
from PIL import Image
from scipy import ndimage


def frilegg(sti, tol=None, luft=0.04, maks=1800):
    im = Image.open(sti).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    kant = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
    bg = np.median(kant, axis=0)
    tol = tol or (14 if sti.lower().endswith((".jpg", ".jpeg")) else 6)   # JPEG har støy rundt kantene
    d = np.abs(a - bg).max(axis=2)
    lik = d <= tol
    lab, _ = ndimage.label(lik)
    ytre = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    bak = np.isin(lab, list(ytre))
    # myk kant: i en smal sone inn mot produktet avgjør avstanden til bakgrunnsfargen hvor gjennomsiktig pikselen er
    sone = ndimage.binary_dilation(bak, iterations=2) & ~bak
    alfa = np.where(bak, 0.0, 1.0).astype(np.float32)
    alfa[sone] = np.clip((d[sone] - tol) / 40.0, 0.0, 1.0)
    alfa = np.maximum(alfa, ndimage.uniform_filter(alfa, 3) * (~bak))   # litt utjevning, aldri inn i bakgrunnen
    # rens fargen i overgangen: P = a·C + (1 − a)·bg  →  C = (P − (1 − a)·bg) / a
    al = alfa[..., None]
    c = np.where(al > 0.02, (a - (1 - al) * bg) / np.maximum(al, 0.02), a)
    rgba = np.dstack([np.clip(c, 0, 255), alfa * 255]).astype(np.uint8)
    ys, xs = np.nonzero(alfa > 0.02)
    m = int(max(h, w) * luft)
    y0, y1, x0, x1 = max(0, ys.min() - m), min(h, ys.max() + 1 + m), max(0, xs.min() - m), min(w, xs.max() + 1 + m)
    ut = Image.fromarray(rgba, "RGBA").crop((x0, y0, x1, y1))
    if max(ut.size) > maks:
        s = maks / max(ut.size)
        ut = ut.resize((round(ut.width * s), round(ut.height * s)), Image.LANCZOS)
    return ut


if __name__ == "__main__":
    for sti in sys.argv[1:]:
        ut = frilegg(sti)
        base = sti.rsplit(".", 1)[0] + "-fri"
        ut.save(base + ".webp", quality=88, method=6)
        ut.save(base + ".png", optimize=True)
        print(f"{base}.webp  {ut.width} × {ut.height}")
