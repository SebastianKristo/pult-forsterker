"""Skjermbilder av brukerflaten på Skjold Fjernkontroll (240 × 320, tegnet i 3× oppløsning) til render/ og 3D-siden.

Bildene følger oppsettet i esphome/skjold-fjernkontroll.yaml (LVGL): statuslinje øverst, innhold, og fire faner nederst
(Aktiviteter · Spiller · Kilder · Hjem). De er tegnet med Pillow, ikke tatt fra en ekte skjerm – fargene, skriften (Sora)
og plasseringen er de samme som i fastvaren, men detaljer kan avvike.

Bruk:  python3 lag_skjermbilder.py      → render/skjerm-1-aktiviteter.png … skjerm-5-laer.png"""
import math
import os

from PIL import Image, ImageDraw, ImageFont

S = 3
W, H = 240, 320
HER = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HER, "..", "..", "skjold", "ios", "Skjold", "Fonts")
BG = (16, 16, 18)
KORT = (32, 32, 35)
KANT = (52, 52, 56)
GULL = (232, 180, 80)
HVIT = (240, 238, 232)
GRAA = (150, 148, 142)


def font(vekt, size):
    fn = {"semi": "Sora-SemiBold.ttf", "reg": "Sora-Regular.ttf", "lett": "Sora-Light.ttf"}[vekt]
    try:
        return ImageFont.truetype(os.path.join(FONTS, fn), size * S)
    except OSError:
        return ImageFont.truetype("DejaVuSans.ttf", size * S)


def ny():
    im = Image.new("RGB", (W * S, H * S), BG)
    return im, ImageDraw.Draw(im)


def r(d, box, rad, fill=None, outline=None, width=1):
    x0, y0, x1, y1 = box
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], rad * S, fill=fill, outline=outline, width=width * S)


def tekst(d, xy, s, f, fill=HVIT, anchor="la"):
    d.text((xy[0] * S, xy[1] * S), s, font=f, fill=fill, anchor=anchor)


def status(d, rom="Stue", bat=87):
    tekst(d, (10, 9), rom, font("semi", 11), GULL)
    # Wi-Fi-buer og batteri til høyre
    cx, cy = 186, 18
    for i, rad in enumerate((3, 6, 9)):
        d.arc([(cx - rad) * S, (cy - rad) * S, (cx + rad) * S, (cy + rad) * S], 225, 315, fill=HVIT, width=int(1.6 * S))
    r(d, (198, 10, 220, 20), 2, outline=HVIT, width=1)
    r(d, (200, 12, 200 + 18 * bat / 100, 18), 1, fill=HVIT)
    d.rectangle([221 * S, 13 * S, 223 * S, 17 * S], fill=HVIT)


FANER = ["Aktiviteter", "Spiller", "Kilder", "Hjem"]


def faner(d, aktiv):
    d.line([0, 288 * S, W * S, 288 * S], fill=KANT, width=S)
    for i, navn in enumerate(FANER):
        x = 30 + i * 60
        on = i == aktiv
        ikon(d, ["liste", "spill", "radio", "hus"][i], x, 299, GULL if on else GRAA, 1.0)
        tekst(d, (x, 309), navn, font("semi" if on else "reg", 8), GULL if on else GRAA, "ma")


def ikon(d, navn, x, y, c, k=1.0):
    """Små strekikoner (samme som i fastvaren, der de er tegnet med LVGL-symboler)."""
    w = max(1, int(1.8 * S * k))
    X, Y = x * S, y * S
    u = S * k
    if navn == "tv":
        d.rounded_rectangle([X - 8 * u, Y - 6 * u, X + 8 * u, Y + 5 * u], 2 * u, outline=c, width=w)
        d.line([X - 4 * u, Y + 8 * u, X + 4 * u, Y + 8 * u], fill=c, width=w)
    elif navn == "note":
        d.ellipse([X - 7 * u, Y + 2 * u, X - 1 * u, Y + 7 * u], fill=c)
        d.line([X - 1.5 * u, Y + 5 * u, X - 1.5 * u, Y - 7 * u], fill=c, width=w)
        d.line([X - 1.5 * u, Y - 7 * u, X + 6 * u, Y - 4 * u], fill=c, width=w)
    elif navn == "sol":
        d.ellipse([X - 4 * u, Y - 4 * u, X + 4 * u, Y + 4 * u], outline=c, width=w)
        for a in range(0, 360, 45):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            d.line([X + 6.5 * u * ca, Y + 6.5 * u * sa, X + 9 * u * ca, Y + 9 * u * sa], fill=c, width=w)
    elif navn == "film":
        d.rounded_rectangle([X - 8 * u, Y - 6 * u, X + 8 * u, Y + 6 * u], 2 * u, outline=c, width=w)
        d.polygon([(X - 2 * u, Y - 3.5 * u), (X - 2 * u, Y + 3.5 * u), (X + 4 * u, Y)], fill=c)
    elif navn == "maane":
        d.ellipse([X - 7 * u, Y - 7 * u, X + 7 * u, Y + 7 * u], fill=c)
        d.ellipse([X - 3 * u, Y - 9 * u, X + 9 * u, Y + 3 * u], fill=KORT)
    elif navn == "av":
        d.arc([X - 7 * u, Y - 7 * u, X + 7 * u, Y + 7 * u], 300, 240, fill=c, width=w)
        d.line([X, Y - 9 * u, X, Y - 1 * u], fill=c, width=w)
    elif navn == "liste":
        for dy in (-4, 0, 4):
            d.line([X - 6 * u, Y + dy * u, X + 6 * u, Y + dy * u], fill=c, width=w)
    elif navn == "spill":
        d.polygon([(X - 4 * u, Y - 6 * u), (X - 4 * u, Y + 6 * u), (X + 6 * u, Y)], fill=c)
    elif navn == "radio":
        d.rounded_rectangle([X - 8 * u, Y - 4 * u, X + 8 * u, Y + 6 * u], 2 * u, outline=c, width=w)
        d.line([X - 5 * u, Y - 4 * u, X + 4 * u, Y - 9 * u], fill=c, width=w)
        d.ellipse([X + 1 * u, Y - 1 * u, X + 5 * u, Y + 3 * u], outline=c, width=w)
    elif navn == "hus":
        d.line([X - 8 * u, Y - 1 * u, X, Y - 8 * u, X + 8 * u, Y - 1 * u], fill=c, width=w, joint="curve")
        d.rectangle([X - 5.5 * u, Y - 2 * u, X + 5.5 * u, Y + 7 * u], outline=c, width=w)
    elif navn == "lys":
        d.ellipse([X - 5 * u, Y - 8 * u, X + 5 * u, Y + 2 * u], outline=c, width=w)
        d.line([X - 3 * u, Y + 5 * u, X + 3 * u, Y + 5 * u], fill=c, width=w)
    elif navn == "skjold":
        d.polygon([(X - 6 * u, Y - 7 * u), (X + 6 * u, Y - 7 * u), (X + 6 * u, Y), (X, Y + 8 * u), (X - 6 * u, Y)], outline=c, width=w)


def aktiviteter():
    im, d = ny()
    status(d)
    tekst(d, (10, 30), "Aktiviteter", font("semi", 17))
    rader = [("tv", "Se TV", "TV · Skjold · Stuelys 40 %", True), ("note", "Musikk", "Skjold · P2 Klassisk", False),
             ("film", "Film", "Projektor · Kinolys", False), ("sol", "God morgen", "Radio · Lys 70 %", False),
             ("maane", "God natt", "Alt av om 20 min", False)]
    y = 58
    for ik, navn, under, aktiv in rader:
        r(d, (8, y, 232, y + 40), 10, fill=KORT, outline=GULL if aktiv else None, width=1 if aktiv else 0)
        d.ellipse([16 * S, (y + 6) * S, 44 * S, (y + 34) * S], fill=(52, 44, 30) if aktiv else (44, 44, 48))
        ikon(d, ik, 30, y + 20, GULL if aktiv else HVIT, 0.85)
        tekst(d, (54, y + 7), navn, font("semi", 12))
        tekst(d, (54, y + 24), under, font("reg", 8.5), GRAA)
        if aktiv:
            tekst(d, (224, y + 13), "PÅ", font("semi", 8), GULL, "ra")
        y += 45
    faner(d, 0)
    return im


def cover(size):
    """Et enkelt, oppdiktet omslag (gradient og sirkler) – ikke et ekte albumomslag."""
    c = Image.new("RGB", (size, size))
    p = c.load()
    for yy in range(size):
        for xx in range(size):
            t = (xx + yy) / (2 * size)
            p[xx, yy] = (int(40 + 150 * t), int(70 + 60 * (1 - t)), int(110 + 80 * (1 - t)))
    dd = ImageDraw.Draw(c)
    for i, rad in enumerate((0.42, 0.30, 0.18)):
        rr = rad * size
        dd.ellipse([size * 0.62 - rr, size * 0.40 - rr, size * 0.62 + rr, size * 0.40 + rr], outline=(240, 220, 170), width=max(2, size // 60))
    return c


def spiller():
    im, d = ny()
    status(d, "Stue · Skjold Radio")
    cv = cover(132 * S)
    m = Image.new("L", cv.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cv.size[0], cv.size[1]], 12 * S, fill=255)
    im.paste(cv, (54 * S, 34 * S), m)
    d = ImageDraw.Draw(im)
    tekst(d, (120, 174), "Morgenklassisk", font("semi", 14), anchor="ma")
    tekst(d, (120, 194), "NRK P2 · Radio", font("reg", 10), GRAA, "ma")
    # transport
    for x, k in ((66, "forrige"), (120, "pause"), (174, "neste")):
        if k == "pause":
            d.ellipse([(x - 17) * S, 213 * S, (x + 17) * S, 247 * S], fill=GULL)
            d.rectangle([(x - 6) * S, 223 * S, (x - 2) * S, 237 * S], fill=BG)
            d.rectangle([(x + 2) * S, 223 * S, (x + 6) * S, 237 * S], fill=BG)
        else:
            s = -1 if k == "forrige" else 1
            d.polygon([((x - 5 * s) * S, 223 * S), ((x - 5 * s) * S, 237 * S), ((x + 4 * s) * S, 230 * S)], fill=HVIT)
            d.rectangle([min((x + 4 * s) * S, (x + 6 * s) * S), 223 * S, max((x + 4 * s) * S, (x + 6 * s) * S), 237 * S], fill=HVIT)
    # volum
    tekst(d, (14, 260), "Volum", font("reg", 9), GRAA)
    r(d, (60, 262, 200, 268), 3, fill=KANT)
    r(d, (60, 262, 60 + 140 * 0.38, 268), 3, fill=GULL)
    d.ellipse([(60 + 140 * 0.38 - 6) * S, 259 * S, (60 + 140 * 0.38 + 6) * S, 271 * S], fill=HVIT)
    tekst(d, (226, 260), "38", font("semi", 10), HVIT, "ra")
    faner(d, 1)
    return im


def kilder():
    im, d = ny()
    status(d)
    tekst(d, (10, 30), "Kilder", font("semi", 17))
    k = [("Radio", True), ("AirPlay", False), ("Bluetooth", False), ("Spotify", False)]
    for i, (n, a) in enumerate(k):
        x = 8 + (i % 2) * 114
        y = 58 + (i // 2) * 34
        r(d, (x, y, x + 110, y + 28), 8, fill=(52, 44, 30) if a else KORT, outline=GULL if a else None, width=1)
        tekst(d, (x + 55, y + 14), n, font("semi", 10), GULL if a else HVIT, "mm")
    tekst(d, (10, 134), "Radiofavoritter", font("semi", 11), GRAA)
    fav = ["NRK P1", "NRK P2", "P3 Musikk", "Radio Norge", "NRK Klassisk", "Jazz"]
    for i, n in enumerate(fav):
        x = 8 + (i % 2) * 114
        y = 154 + (i // 2) * 42
        r(d, (x, y, x + 110, y + 36), 8, fill=KORT, outline=GULL if i == 1 else None, width=1)
        d.ellipse([(x + 6) * S, (y + 6) * S, (x + 30) * S, (y + 30) * S], fill=(44, 44, 48))
        tekst(d, (x + 18, y + 18), str(i + 1), font("semi", 10), GULL, "mm")
        tekst(d, (x + 36, y + 12), n, font("semi", 9), HVIT)
    faner(d, 2)
    return im


def hjem():
    im, d = ny()
    status(d)
    tekst(d, (10, 30), "Hjem", font("semi", 17))
    rom = [("Stue", "Taklys 40 %", True), ("Kjøkken", "Av", False), ("Gang", "Av", False), ("Soverom", "Nattlys", True)]
    for i, (n, s, on) in enumerate(rom):
        x = 8 + (i % 2) * 114
        y = 58 + (i // 2) * 62
        r(d, (x, y, x + 110, y + 56), 10, fill=(52, 44, 30) if on else KORT)
        ikon(d, "lys", x + 18, y + 20, GULL if on else GRAA, 0.9)
        tekst(d, (x + 10, y + 32), n, font("semi", 10.5), HVIT)
        tekst(d, (x + 10, y + 45), s, font("reg", 8), GRAA)
    tekst(d, (10, 190), "Scener", font("semi", 11), GRAA)
    sc = ["Kino", "Middag", "Lesing", "Alt av"]
    for i, n in enumerate(sc):
        x = 8 + (i % 2) * 114
        y = 210 + (i // 2) * 36
        r(d, (x, y, x + 110, y + 30), 8, fill=KORT)
        tekst(d, (x + 55, y + 15), n, font("semi", 10), HVIT, "mm")
    faner(d, 3)
    return im


def laer():
    im, d = ny()
    status(d)
    tekst(d, (10, 30), "Lær IR-kode", font("semi", 17))
    r(d, (8, 60, 232, 150), 12, fill=KORT, outline=GULL, width=1)
    ikon(d, "tv", 120, 86, GULL, 1.3)
    tekst(d, (120, 108), "Pek den gamle fjernkontrollen", font("reg", 9.5), HVIT, "ma")
    tekst(d, (120, 122), "mot nesen og trykk «Volum +»", font("reg", 9.5), HVIT, "ma")
    tekst(d, (16, 168), "Tast", font("reg", 9), GRAA)
    tekst(d, (224, 168), "Volum +", font("semi", 10), GULL, "ra")
    tekst(d, (16, 188), "Enhet", font("reg", 9), GRAA)
    tekst(d, (224, 188), "TV", font("semi", 10), HVIT, "ra")
    tekst(d, (16, 208), "Mottatt", font("reg", 9), GRAA)
    tekst(d, (224, 208), "NEC 0x04 / 0x02", font("semi", 10), HVIT, "ra")
    r(d, (8, 236, 116, 266), 8, fill=KORT)
    tekst(d, (62, 251), "Avbryt", font("semi", 10), HVIT, "mm")
    r(d, (124, 236, 232, 266), 8, fill=GULL)
    tekst(d, (178, 251), "Lagre", font("semi", 10), BG, "mm")
    faner(d, 3)
    return im


def main():
    os.makedirs(os.path.join(HER, "render"), exist_ok=True)
    for i, (navn, f) in enumerate([("aktiviteter", aktiviteter), ("spiller", spiller), ("kilder", kilder), ("hjem", hjem), ("laer", laer)], 1):
        fn = os.path.join(HER, "render", f"skjerm-{i}-{navn}.png")
        f().save(fn, optimize=True)
        print("skrev", os.path.relpath(fn, HER))


if __name__ == "__main__":
    main()
