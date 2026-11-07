"""Legg skjermbildet (render/skjerm-1-aktiviteter.png, laget av lag_skjermbilder.py) inn på skjermen i OpenSCAD-bildene.

OpenSCAD kan ikke legge en tekstur på en flate. lag_render.sh tegner derfor det aktive området på skjermen i ren magenta
(skjerm="nokkel"), og i tillegg bare det aktive området alene med samme kamera (part="skjermflate"), delt i fire fargede
kvadranter (rød, grønn, blå, gul med klokka fra øverst til venstre). Hjørnet i hver kvadrant regnes ut fra tyngdepunktene
(se corners), så hjørnene blir riktige uansett hvordan fjernkontrollen er dreid og vippet i bildet. Fra det første bildet tar vi hvilke piksler
som faktisk synes (vinduskanten skygger litt skrått fra).
Skjermbildet vrenges perspektivisk inn i hjørnene og legges bare der magentaen synes, med en svak glassrefleks.

Bruk:  python3 skjerm_i_render.py <bilde.png> <skjermflate.png> [skjermbilde.png]"""
import sys

import numpy as np
from PIL import Image, ImageFilter


def key_mask(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    return (a[..., 0] > 45) & (a[..., 2] > 45) & (a[..., 1] < 0.35 * a[..., 0]) & (np.abs(a[..., 0] - a[..., 2]) < 0.25 * a[..., 0] + 6)


def kvadranter(img):
    """Masker for de fire fargede kvadrantene (rød, grønn, blå, gul) i part="skjermflate"-bildet."""
    a = np.asarray(img.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = max(1, a.max())
    lys = a.max(axis=2) > 40
    return [lys & (r > 2.2 * g) & (r > 2.2 * b), lys & (g > 2.2 * r) & (g > 2.2 * b),
            lys & (b > 2.2 * r) & (b > 2.2 * g), lys & (r > 2.2 * b) & (g > 2.2 * b) & (np.abs(r - g) < 0.35 * np.maximum(r, g))]


def corners(qs):
    """Ytterhjørnet i hver kvadrant. For et parallellogram er hjørnet = 2 × kvadrantens tyngdepunkt − midtpunktet,
    der midtpunktet er snittet av de fire tyngdepunktene. Det gjelder også når skjermen sees svært skrått (der
    «pikselen lengst fra midten» bommer). Perspektivet gjør det ikke helt eksakt, så vi tar til slutt den
    pikselen i kvadranten som ligger nærmest det beregnede punktet."""
    cen = [np.array([np.nonzero(q)[1].mean(), np.nonzero(q)[0].mean()]) for q in qs]
    c = np.mean(cen, axis=0)
    out = []
    for q, m in zip(qs, cen):
        p = 2 * m - c
        ys, xs = np.nonzero(q)
        i = ((xs - p[0]) ** 2 + (ys - p[1]) ** 2).argmin()
        # hjørnepikselen er et senter; flytt en halv piksel utover fra midten
        dx, dy = np.sign(xs[i] - c[0]) * 0.5, np.sign(ys[i] - c[1]) * 0.5
        out.append((xs[i] + dx, ys[i] + dy))
    return out


def perspective_coeffs(dst, src):
    """Koeffisienter for Image.transform(PERSPECTIVE): punkt i ut-bildet (dst) → punkt i kilden (src)."""
    m, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(m, float), np.array(b, float)).tolist()


def main(render, flate, shot="render/skjerm-1-aktiviteter.png"):
    img = Image.open(render).convert("RGB")
    vis = key_mask(img)
    qs = kvadranter(Image.open(flate))
    if vis.sum() < 50 or min(q.sum() for q in qs) < 10:
        print(f"{render}: ingen synlig skjerm, uendret")
        return
    sc = Image.open(shot).convert("RGB")
    w, h = sc.size
    c = corners(qs)
    warped = sc.transform(img.size, Image.PERSPECTIVE, perspective_coeffs(c, [(0, 0), (w, 0), (w, h), (0, h)]), Image.BICUBIC)
    # glass: litt mørkere og en svak skrå refleks over øvre venstre del
    arr = np.asarray(warped).astype(float) * 0.92
    yy, xx = np.mgrid[0:img.size[1], 0:img.size[0]]
    x0, y0 = c[0]; x1, y1 = c[2]
    t = ((xx - x0) / max(1, x1 - x0) + (yy - y0) / max(1, y1 - y0)) / 2
    arr += (np.clip(1 - t * 2.2, 0, 1) ** 2 * 22)[..., None]
    warped = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    m = Image.fromarray((vis * 255).astype(np.uint8)).filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.GaussianBlur(0.6))
    img.paste(warped, (0, 0), m)
    img.save(render)
    print(f"{render}: skjermbilde lagt inn ({int(vis.sum())} piksler)")


if __name__ == "__main__":
    main(*sys.argv[1:])
