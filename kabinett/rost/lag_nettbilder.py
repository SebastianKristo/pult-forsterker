"""Lag bildene av Røst til nettsiden (skjold/nettside/assets/img/0?-rost*.png/.webp, 924 × 540 på beige) fra renderne i render/.

Bakgrunnen i OpenSCAD-bildene (Tomorrow, 248,248,248) fylles fra kantene og byttes med nettsidens beige; delen beskjæres
og skaleres inn i rammen. Kjøres etter lag_render.sh:  python3 lag_nettbilder.py"""
import numpy as np
from PIL import Image
from scipy import ndimage

BEIGE = (233, 231, 226)
UT = "../../skjold/nettside/assets/img/"
# nettbilde: (render, høyde i rammen (andel av 540))
BILDER = {
    "01-rost": ("01_rost", 0.92),          # skrått forfra
    "02-rost": ("06_knapper_skjerm", 0.95),  # toppen med skjerm, knapper og volumhjul
    "03-rost": ("04_side", 0.92),           # fra siden
    "04-rost": ("03_bak", 0.92),            # bakfra
    "05-rost-m": ("02_eksplodert", 0.94),   # delt opp
}

for navn, (kilde, h) in BILDER.items():
    a = np.asarray(Image.open(f"render/{kilde}.png").convert("RGB")).astype(np.int16)
    bg = np.all(np.abs(a - 248) <= 3, axis=2)
    lab, _ = ndimage.label(bg)
    kant = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    maske = np.isin(lab, list(kant))
    a[maske] = BEIGE
    ys, xs = np.nonzero(~maske)
    bilde = Image.fromarray(a.astype(np.uint8)).crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    s = min(540 * h / bilde.height, 900 / bilde.width)
    bilde = bilde.resize((round(bilde.width * s), round(bilde.height * s)), Image.LANCZOS)
    ramme = Image.new("RGB", (924, 540), BEIGE)
    nede = ys.max() == a.shape[0] - 1   # delen går ut av bildet nederst: legg den mot underkanten
    ramme.paste(bilde, ((924 - bilde.width) // 2, 540 - bilde.height if nede else (540 - bilde.height) // 2))
    ramme.save(UT + navn + ".png", optimize=True)
    ramme.save(UT + navn + ".webp", quality=82, method=6)
    print("skrev", UT + navn)
