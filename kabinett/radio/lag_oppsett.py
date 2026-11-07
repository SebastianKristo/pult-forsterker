"""Tegn oppsettet inni Skjold Radio som et merket diagram: render/10_oppsett.png.

Leser STL-ene i montert stilling (asm/) og de kjøpte delene (ref/), så tegningen alltid følger modellen.
To visninger: sett bakfra med bakplata av (x speilvendt, slik du ser det når du står bak radioen), og sett ovenfra
(fronten nede). Hver del får et nummer og en farge; forklaringen står til høyre med festet.

Bruk:  python3 lag_oppsett.py   (kjøres av lag_render.sh etter lag_stl.sh)"""
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

HER = os.path.dirname(os.path.abspath(__file__))
W, D, H, T = 240, 115, 137, 3.0
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# (fil, navn, feste, farge) – nummereres i denne rekkefølgen
DELER = [
    ("asm/kammer", "Lydkammer + lokk", "4 × M3 × 10 nedenfra i ørene, lokk 6 × M3 × 8", "#8d8a86"),
    ("ref/element", "Høyttaler RS75-4", "4 × M3 × 10 selvgj. i baffelen", "#4a4a4c"),
    ("ref/skjermmodul", "Skjermmodul 4,3″ DSI", "i lomma, klemt av braketten", "#202024"),
    ("asm/brakett", "Skjermbrakett", "4 × M2,5 × 6 selvgj.", "#b5b2ad"),
    ("ref/pi", "Raspberry Pi 4", "4 × M2,5 × 6 på braketten", "#2f7a46"),
    ("ref/favkort", "Favorittkort 1–6 (110 × 16)", "2 × M2,5 × 6 i tårn, 6 taktbrytere", "#1e6b3a"),
    ("ref/pwkort", "Av/på-kort (30 × 16)", "2 × M2,5 × 6 i tårn", "#2b8a4f"),
    ("ref/ec_volum", "Volum EC11 (kort 20 × 34)", "2 × M2,5 × 6 i tårn", "#c9a245"),
    ("ref/ec_hjul", "Hjul EC11 (kort 20 × 34)", "2 × M2,5 × 6 i tårn", "#d9b24f"),
    ("ref/dac", "DAC PCM5102A (32 × 17)", "4 stolper + strips", "#7a3fb0"),
    ("ref/forsterker", "Forsterker TPA3116D2 (83 × 50)", "4 × M3 × 8 selvgj. i stolper, over spaltene", "#2c66c9"),
    ("ref/nedtrapper", "Nedtrapper 5 V / 5 A (54 × 23)", "hjørneholdere på bakplata + strips", "#1d3f8f"),
    ("ref/rele", "Relé 1-kanal (50 × 26)", "hjørneholdere på bakplata + strips", "#3b78e7"),
    ("ref/kontakter", "DC-022 · 3,5 mm · USB-C", "mutter / 2 × M3 × 8 i bakplata", "#8f9399"),
]
PANEL = {"ref/nedtrapper", "ref/rele", "ref/kontakter"}   # sitter på bakplata


def last(f):
    return trimesh.load(os.path.join(HER, f + ".stl"))


def main():
    M = [(f, n, fe, c, last(f)) for f, n, fe, c in DELER]
    kropp = last("asm/kropp")
    s = 3.6                       # px per mm
    pad = 40
    vw, vh = int(W * s), int(H * s)
    th = int(D * s)
    leg_w = 760
    img = Image.new("RGB", (pad * 3 + vw + leg_w, pad * 4 + vh + th + 100), "#f7f6f3")
    d = ImageDraw.Draw(img, "RGBA")
    ft, fb, fs = ImageFont.truetype(F, 22), ImageFont.truetype(FB, 26), ImageFont.truetype(F, 18)

    def rr(box, **kw):
        d.rounded_rectangle(box, radius=10, **kw)

    def nummer(xy, i, col):
        x, y = xy
        d.ellipse([x - 15, y - 15, x + 15, y + 15], fill="#ffffff", outline=col, width=3)
        tw = d.textlength(str(i), font=fs)
        d.text((x - tw / 2, y - 11), str(i), fill="#1c1b1a", font=fs)

    # --- sett bakfra (x speilvendt: venstre i bildet = høyre side av radioen) ---
    ox, oy = pad, pad + 40
    d.text((ox, pad), "Sett bakfra, bakplata av (kortene på bakplata stiplet)", fill="#1c1b1a", font=fb)

    def pb(x, z):
        return ox + (W - x) * s, oy + (H - z) * s
    rr([ox, oy, ox + vw, oy + vh + T * s], outline="#6f6a63", width=3, fill="#ece9e3")
    # dybdesortert: det som er nærmest fronten først
    order = sorted(range(len(M)), key=lambda i: M[i][4].bounds[0][1])
    for i in order:
        f, n, fe, c, m = M[i]
        (x0, _, z0), (x1, _, z1) = m.bounds
        a, b = pb(x1, z1), pb(x0, z0)
        if f in PANEL:
            d.rectangle([a, b], outline=c, width=3)
            for k in range(int(a[0]), int(b[0]), 14):
                d.line([k, a[1], min(k + 7, b[0]), a[1]], fill="#f7f6f3", width=3)
        else:
            d.rectangle([a, b], fill=c + "d0", outline="#1c1b1a40", width=1)
        nummer((a[0] + 22, a[1] + 22) if f in PANEL else ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), i + 1, c)
    for x, lab in ((W - 60, "← radioens høyre side"), (60, "venstre side →")):
        d.text((pb(x, 0)[0] - 80, oy + vh + T * s + 8), lab, fill="#6f6a63", font=fs)

    # --- sett ovenfra (fronten nede) ---
    oy2 = oy + vh + T * s + 100
    d.text((ox, oy2 - 40), "Sett ovenfra (fronten nede, x som sett bakfra)", fill="#1c1b1a", font=fb)

    def pt(x, y):
        return ox + (W - x) * s, oy2 + (D - y) * s
    rr([ox, oy2, ox + vw, oy2 + th], outline="#6f6a63", width=3, fill="#ece9e3")
    d.line([pt(W, 0), pt(0, 0)], fill="#1c1b1a", width=5)
    d.text((pt(W / 2, 0)[0] - 30, pt(0, 0)[1] + 6), "FRONT", fill="#1c1b1a", font=fs)
    order = sorted(range(len(M)), key=lambda i: M[i][4].bounds[0][2])
    for i in order:
        f, n, fe, c, m = M[i]
        (x0, y0, _), (x1, y1, _) = m.bounds
        a, b = pt(x1, min(y1, D)), pt(x0, max(y0, 0))      # akslene foran fronten tegnes ikke
        d.rectangle([a, b], fill=c + ("70" if f in PANEL else "c0"), outline="#1c1b1a40")
        nummer(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2), i + 1, c)
    # luftespalter i gulvet og strips-fester
    for k in range(9):
        x = 136 + 8 * k
        d.rectangle([pt(x + 3, 86), pt(x, 40)], outline="#1c1b1a60", width=1)
    for x, y in ((134, 9.5), (220, 30), (220, 60), (220, 95)):
        a = pt(x, y)
        d.rectangle([a[0] - 4 * s, a[1] - 2.5 * s, a[0] + 4 * s, a[1] + 2.5 * s], outline="#b8862f", width=3)

    # --- forklaring ---
    lx = ox + vw + pad
    d.text((lx, pad), "Delene og festene", fill="#1c1b1a", font=fb)
    y = pad + 50
    for i, (f, n, fe, c, m) in enumerate(M):
        nummer((lx + 16, y + 14), i + 1, c)
        d.text((lx + 42, y), n, fill="#1c1b1a", font=ft)
        d.text((lx + 42, y + 28), fe, fill="#6f6a63", font=fs)
        y += 62
    d.rectangle([lx, y + 8, lx + 28, y + 24], outline="#b8862f", width=3)
    d.text((lx + 42, y + 2), "strips-feste i gulvet", fill="#1c1b1a", font=fs)
    y += 34
    d.text((lx, y), "Mål i mm. Kortmålene er vanlige mål;", fill="#6f6a63", font=fs)
    d.text((lx, y + 24), "mål dine egne og juster i skjold_radio.scad.", fill="#6f6a63", font=fs)
    out = os.path.join(HER, "render", "10_oppsett.png")
    img.save(out, optimize=True)
    print("skrev", out)


if __name__ == "__main__":
    main()
