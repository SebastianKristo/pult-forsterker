"""Legg OLED-bildet (render/oled.png, 128 × 64, laget av lag_oled.py) inn på skjermen i OpenSCAD-bildene av Skjold Røst.
(Samme metode som kabinett/radio/skjerm_i_render.py.)

OpenSCAD kan ikke legge en tekstur på en flate. lag_render.sh tegner derfor det aktive området på skjermen i ren magenta
(skjerm="nokkel"), og i tillegg bare det aktive området alene med samme kamera (part="skjermflate"). Fra det siste finner
vi de fire hjørnene (perspektivet), fra det første hvilke piksler som faktisk synes (vinduskanten skygger litt skrått fra).
Skjermbildet vrenges perspektivisk inn i hjørnene og legges bare der magentaen synes, med en svak glassrefleks.

Bruk:  python3 skjerm_i_render.py <bilde.png> <skjermflate.png> [skjermbilde.png]"""
import sys

import numpy as np
from PIL import Image, ImageFilter


def key_mask(img):
    a = np.asarray(img.convert("RGB")).astype(int)
    return (a[..., 0] > 45) & (a[..., 2] > 45) & (a[..., 1] < 0.35 * a[..., 0]) & (np.abs(a[..., 0] - a[..., 2]) < 0.25 * a[..., 0] + 6)


def corners(mask):
    ys, xs = np.nonzero(mask)
    s, d = xs + ys, xs - ys
    tl, br = (xs[s.argmin()], ys[s.argmin()]), (xs[s.argmax()], ys[s.argmax()])
    tr, bl = (xs[d.argmax()], ys[d.argmax()]), (xs[d.argmin()], ys[d.argmin()])
    # hjørnepikslene er sentre; utvid en halv piksel utover
    return [(tl[0] - .5, tl[1] - .5), (tr[0] + .5, tr[1] - .5), (br[0] + .5, br[1] + .5), (bl[0] - .5, bl[1] + .5)]


def perspective_coeffs(dst, src):
    """Koeffisienter for Image.transform(PERSPECTIVE): punkt i ut-bildet (dst) → punkt i kilden (src)."""
    m, b = [], []
    for (x, y), (u, v) in zip(dst, src):
        m.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.append(u)
        m.append([0, 0, 0, x, y, 1, -v * x, -v * y]); b.append(v)
    return np.linalg.solve(np.array(m, float), np.array(b, float)).tolist()


def main(render, flate, shot="render/oled.png"):
    img = Image.open(render).convert("RGB")
    vis = key_mask(img)
    q = key_mask(Image.open(flate))
    if vis.sum() < 50 or q.sum() < 50:
        print(f"{render}: ingen synlig skjerm, uendret")
        return
    sc = Image.open(shot).convert("RGB")
    sc = sc.resize((sc.size[0] * 8, sc.size[1] * 8), Image.NEAREST)   # skarpe piksler
    w, h = sc.size
    c = corners(q)
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
