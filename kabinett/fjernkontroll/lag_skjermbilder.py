"""Skjermbilder av brukerflaten på Skjold Fjernkontroll (240 × 320, tegnet i 3× oppløsning) til render/ og 3D-siden.

Bildene følger oppsettet i esphome/skjold-fjernkontroll.yaml (LVGL): «Styrer»-brikken og batteriet øverst, innhold,
og fire faner nederst (Start · Enhet · Hjem · Mer). De er tegnet med Pillow, ikke tatt fra en ekte skjerm – fargene,
skriften (Sora), målene og plasseringen er de samme som i fastvaren, men detaljer kan avvike. Appnavn, titler og
lys er eksempler.

Bruk:  python3 lag_skjermbilder.py      → render/skjerm-1-start.png … skjerm-9-dokk.png"""
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


def status(d, enhet="Apple TV", ik="spill", bat=87, lader=False):
    """«Styrer»-brikken (enheten tastene virker på) og batteriet."""
    r(d, (6, 4, 166, 28), 12, fill=KORT)
    ikon(d, ik, 17, 16, GULL, 0.55)
    tekst(d, (28, 9), enhet, font("semi", 11), GULL)
    d.line([(152 * S, 14 * S), (156 * S, 18 * S), (160 * S, 14 * S)], fill=GRAA, width=int(1.4 * S))
    if lader:
        d.polygon([(184 * S, 10 * S), (180 * S, 17 * S), (184 * S, 17 * S), (182 * S, 23 * S), (188 * S, 15 * S), (184 * S, 15 * S)], fill=GULL)
    r(d, (194, 11, 214, 21), 2, outline=HVIT, width=1)
    r(d, (196, 13, 196 + 16 * bat / 100, 19), 1, fill=HVIT)
    d.rectangle([215 * S, 14 * S, 217 * S, 18 * S], fill=HVIT)
    tekst(d, (232, 11), f"{bat}", font("semi", 8), HVIT, "ra")


FANER = [("hus", "Start"), ("rutenett", "Enhet"), ("lys", "Hjem"), ("tannhjul", "Mer")]


def faner(d, aktiv):
    d.line([0, 288 * S, W * S, 288 * S], fill=(44, 44, 48), width=S)
    for i, (ik, navn) in enumerate(FANER):
        x = 30 + i * 60
        on = i == aktiv
        ikon(d, ik, x, 298, GULL if on else GRAA, 0.8)
        tekst(d, (x, 309), navn, font("semi" if on else "reg", 8), GULL if on else GRAA, "ma")


def knapp(d, box, tekst_, valgt=False, f=None, fill=None, farge=None):
    r(d, box, 12, fill=fill or ((52, 44, 30) if valgt else KORT), outline=GULL if valgt else None, width=1)
    x0, y0, x1, y1 = box
    tekst(d, ((x0 + x1) / 2, (y0 + y1) / 2), tekst_, f or font("semi", 10), farge or (GULL if valgt else HVIT), "mm")


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
    elif navn == "rutenett":
        for dx in (-4, 4):
            for dy in (-4, 4):
                d.rounded_rectangle([X + (dx - 3) * u, Y + (dy - 3) * u, X + (dx + 3) * u, Y + (dy + 3) * u], 1 * u, outline=c, width=w)
    elif navn == "tannhjul":
        d.ellipse([X - 5 * u, Y - 5 * u, X + 5 * u, Y + 5 * u], outline=c, width=w)
        for a in range(0, 360, 60):
            ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
            d.line([X + 5 * u * ca, Y + 5 * u * sa, X + 8 * u * ca, Y + 8 * u * sa], fill=c, width=int(w * 1.6))
    elif navn == "pause":
        d.rectangle([X - 4 * u, Y - 6 * u, X - 1 * u, Y + 6 * u], fill=c)
        d.rectangle([X + 1 * u, Y - 6 * u, X + 4 * u, Y + 6 * u], fill=c)
    elif navn == "hake":
        d.line([X - 5 * u, Y, X - 1.5 * u, Y + 4 * u, X + 6 * u, Y - 5 * u], fill=c, width=w, joint="curve")
    elif navn == "pil":
        d.polygon([(X - 3 * u, Y - 5 * u), (X - 3 * u, Y + 5 * u), (X + 4 * u, Y)], fill=c)
    elif navn == "skjold":
        d.polygon([(X - 6 * u, Y - 7 * u), (X + 6 * u, Y - 7 * u), (X + 6 * u, Y), (X, Y + 8 * u), (X - 6 * u, Y)], outline=c, width=w)




def cover(size):
    """Et enkelt, oppdiktet omslag (gradient og sirkler) – ikke et ekte omslag."""
    c = Image.new("RGB", (size, size))
    p = c.load()
    for yy in range(size):
        for xx in range(size):
            t = (xx + yy) / (2 * size)
            p[xx, yy] = (int(40 + 150 * t), int(70 + 60 * (1 - t)), int(110 + 80 * (1 - t)))
    dd = ImageDraw.Draw(c)
    for rad in (0.42, 0.30, 0.18):
        rr = rad * size
        dd.ellipse([size * 0.62 - rr, size * 0.40 - rr, size * 0.62 + rr, size * 0.40 + rr], outline=(240, 220, 170), width=max(2, size // 60))
    return c


# samme farger og initialer som skjold_ui.h (flisfarge, initialer)
PALETT = [0x7A2E2E, 0x2E4F7A, 0x2E6B4F, 0x6B4F2E, 0x5A2E6B, 0x2E6468, 0x6B2E52, 0x46572E, 0x3B3B6E, 0x6E4A2E]


def flisfarge(navn):
    h = 2166136261
    for c in navn.encode():
        h = ((h ^ c) * 16777619) & 0xFFFFFFFF
    v = PALETT[h % 10]
    return (v >> 16, (v >> 8) & 255, v & 255)


def initialer(navn):
    ord_ = navn.split()
    if len(ord_) >= 2:
        return ord_[0][0] + ord_[1][0]
    return ord_[0][0] + (ord_[0][1].lower() if len(ord_[0]) > 1 and ord_[0][1].isupper() else ord_[0][1:2])


def flis(d, x, y, navn, w=68, h=58, fav=False):
    r(d, (x, y, x + w, y + h), 14, fill=flisfarge(navn), outline=GULL if fav else None, width=2 if fav else 1)
    tekst(d, (x + w / 2, y + 7), initialer(navn), font("semi", 19), HVIT, "ma")
    tekst(d, (x + w / 2, y + h - 6), navn, font("reg", 9), (218, 215, 207), "md")


def bar(d, x, y, w, h, andel):
    r(d, (x, y, x + w, y + h), h / 2, fill=(52, 52, 56))
    r(d, (x, y, x + max(h, w * andel), y + h), h / 2, fill=GULL)


AKT = [("tv", "Se TV"), ("spill", "Apple TV"), ("film", "Film"), ("note", "Musikk"), ("maane", "God natt"), ("av", "Alt av")]


def start():
    im, d = ny()
    status(d)
    r(d, (8, 34, 232, 118), 16, fill=(26, 26, 29))
    tekst(d, (22, 42), "Slow Horses", font("semi", 17))
    tekst(d, (22, 70), "Apple TV+ · Spiller", font("reg", 10), GRAA)
    tekst(d, (22, 87), "31:12 / 49:40", font("reg", 9), (110, 108, 104))
    bar(d, 22, 104, 196, 4, 0.63)
    d.ellipse([174 * S, 48 * S, 218 * S, 92 * S], fill=GULL)
    ikon(d, "pause", 196, 70, BG, 1.0)
    tekst(d, (12, 126), "Aktiviteter", font("semi", 11), GRAA)
    for i, (ik, n) in enumerate(AKT):
        x = 8 + (i % 2) * 114
        y = 146 + (i // 2) * 44
        valgt = n == "Apple TV"
        r(d, (x, y, x + 110, y + 40), 12, fill=(52, 44, 30) if valgt else KORT, outline=GULL if valgt else None, width=1)
        ikon(d, ik, x + 17, y + 20, (217, 119, 106) if ik == "av" else (GULL if valgt else HVIT), 0.7)
        tekst(d, (x + 32, y + 20), n, font("semi", 10.5), GULL if valgt else HVIT, "lm")
    faner(d, 0)
    return im


def velger():
    im = start()
    d = ImageDraw.Draw(im, "RGBA")
    d.rectangle([0, 30 * S, W * S, 287 * S], fill=(0, 0, 0, 120))
    r(d, (6, 32, 178, 188), 14, fill=(24, 24, 27), outline=(52, 52, 56), width=1)
    for i, (ik, n) in enumerate([("tv", "Stue-TV"), ("spill", "Apple TV"), ("note", "Skjold"), ("film", "Projektor")]):
        y = 38 + i * 36
        valgt = i == 1
        r(d, (12, y, 170, y + 32), 12, fill=(52, 44, 30) if valgt else KORT, outline=GULL if valgt else None, width=1)
        ikon(d, ik, 26, y + 16, GULL if valgt else HVIT, 0.65)
        tekst(d, (42, y + 16), n, font("semi", 10.5), GULL if valgt else HVIT, "lm")
    r(d, (40, 196, 200, 216), 10, fill=(32, 32, 35))
    tekst(d, (120, 206), "Sveip på brikken for å bytte", font("reg", 9), (200, 198, 192), "mm")
    return im


APPER = ["Netflix", "YouTube", "NRK TV", "Disney+", "Apple TV+", "Plex", "Max", "TV 2 Play", "Spotify", "Viaplay", "Prime Video", "Arcade"]


def apper():
    im, d = ny()
    status(d)
    r(d, (8, 34, 232, 90), 14, fill=(26, 26, 29))
    r(d, (14, 40, 58, 84), 10, fill=flisfarge("Apple TV+"))
    tekst(d, (36, 62), initialer("Apple TV+"), font("semi", 13), HVIT, "mm")
    tekst(d, (66, 40), "Slow Horses", font("semi", 11.5))
    tekst(d, (66, 57), "Apple TV+ · Spiller", font("reg", 9), GRAA)
    tekst(d, (66, 71), "31:12 / 49:40", font("reg", 8), (110, 108, 104))
    bar(d, 66, 84, 118, 3, 0.63)
    d.ellipse([190 * S, 44 * S, 226 * S, 80 * S], fill=GULL)
    ikon(d, "pause", 208, 62, BG, 0.8)
    for i, n in enumerate(APPER[:9]):
        x = 8 + (i % 3) * 78
        y = 96 + (i // 3) * 66
        flis(d, x, y, n, fav=i < 4)
    faner(d, 1)
    return im


def innganger():
    im, d = ny()
    status(d, "Stue-TV", "tv")
    tekst(d, (10, 34), "Stue-TV", font("semi", 19))
    r(d, (186, 32, 232, 60), 12, fill=KORT)
    ikon(d, "av", 209, 47, HVIT, 0.6)
    k = [("HDMI 1", None, False), ("HDMI 2", None, True), ("HDMI 3", None, False), ("HDMI 4", None, False),
         ("TV", None, False), ("Apple TV", "HDMI 2", True), ("Skjold", "lyden", False)]
    for i, (n, under, valgt) in enumerate(k):
        x = 8 + (i % 2) * 114
        y = 68 + (i // 2) * 46
        r(d, (x, y, x + 110, y + 40), 12, fill=(52, 44, 30) if valgt else KORT, outline=GULL if valgt else None, width=1)
        if under:
            tekst(d, (x + 55, y + 14), n, font("semi", 10.5), GULL if valgt else HVIT, "mm")
            tekst(d, (x + 55, y + 29), under, font("reg", 8.5), GRAA, "mm")
        else:
            tekst(d, (x + 55, y + 20), n, font("semi", 10.5), GULL if valgt else HVIT, "mm")
    r(d, (122, 206, 232, 246), 12, fill=(52, 44, 30))
    tekst(d, (177, 226), "Lær IR", font("semi", 10.5), GULL, "mm")
    tekst(d, (10, 258), "Styres gjennom Home Assistant", font("reg", 9), (110, 108, 104))
    faner(d, 1)
    return im


def aktivitet():
    im, d = ny()
    status(d)
    tekst(d, (12, 36), "Film", font("semi", 19))
    d.arc([200 * S, 34 * S, 226 * S, 60 * S], 0, 360, fill=(52, 52, 56), width=3 * S)
    d.arc([200 * S, 34 * S, 226 * S, 60 * S], 300, 20, fill=GULL, width=3 * S)
    steg = [("Slår på Projektor", "ok"), ("Vekker Apple TV", "ok"), ("Åpner Plex …", "går"), ("Skjold: aux …", ""),
            ("Scene kino …", ""), ("Slår av Stue-TV …", "")]
    for i, (t, st) in enumerate(steg):
        y = 76 + i * 26
        if st == "ok":
            ikon(d, "hake", 22, y + 8, GULL, 0.8)
            tekst(d, (40, y), t, font("semi", 12), (180, 177, 170))
        elif st == "går":
            ikon(d, "pil", 22, y + 8, GULL, 0.8)
            tekst(d, (40, y), t, font("semi", 12), HVIT)
        else:
            tekst(d, (40, y), t, font("semi", 12), (110, 108, 104))
    faner(d, 0)
    return im


def spiller():
    im, d = ny()
    status(d, "Skjold", "note")
    r(d, (8, 32, 158, 58), 12, fill=KORT)
    tekst(d, (18, 45), "Stue", font("semi", 10.5), GULL, "lm")
    ikon(d, "pil", 148, 45, GRAA, 0.5)
    knapp(d, (164, 32, 232, 58), "Kilder")
    cv = cover(110 * S)
    m = Image.new("L", cv.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cv.size[0], cv.size[1]], 12 * S, fill=255)
    im.paste(cv, (65 * S, 64 * S), m)
    d = ImageDraw.Draw(im)
    tekst(d, (120, 180), "Morgenklassisk", font("semi", 15), anchor="ma")
    tekst(d, (120, 203), "NRK P2 · radio", font("reg", 10), GRAA, "ma")
    for x, k in ((62, "forrige"), (120, "pause"), (178, "neste")):
        if k == "pause":
            d.ellipse([(x - 21) * S, 220 * S, (x + 21) * S, 262 * S], fill=GULL)
            ikon(d, "pause", x, 241, BG, 1.0)
        else:
            s = -1 if k == "forrige" else 1
            d.polygon([((x - 5 * s) * S, 234 * S), ((x - 5 * s) * S, 248 * S), ((x + 4 * s) * S, 241 * S)], fill=HVIT)
            d.rectangle([min((x + 4 * s) * S, (x + 6 * s) * S), 234 * S, max((x + 4 * s) * S, (x + 6 * s) * S), 248 * S], fill=HVIT)
    tekst(d, (14, 268), "Vol", font("reg", 9), GRAA)
    bar(d, 38, 272, 158, 6, 0.38)
    d.ellipse([(38 + 158 * 0.38 - 6) * S, 269 * S, (38 + 158 * 0.38 + 6) * S, 281 * S], fill=HVIT)
    tekst(d, (228, 266), "38", font("semi", 11), HVIT, "ra")
    faner(d, 1)
    return im


def hjem():
    im, d = ny()
    status(d)
    lys = [("Stue", True, 0.4), ("Kjøkken", False, 0.7), ("Gang", False, 0.3), ("Soverom", True, 0.15)]
    for i, (n, on, b) in enumerate(lys):
        y = 34 + i * 42
        tekst(d, (12, y + 2), n, font("semi", 12))
        r(d, (186, y, 230, y + 22), 11, fill=GULL if on else (52, 52, 56))
        cx = 219 if on else 197
        d.ellipse([(cx - 9) * S, (y + 2) * S, (cx + 9) * S, (y + 20) * S], fill=HVIT)
        bar(d, 14, y + 28, 210, 5, b)
    tekst(d, (12, 204), "Scener", font("semi", 11), GRAA)
    for i, n in enumerate(["Kino", "Middag", "Lesing", "Alt av"]):
        x = 8 + (i % 2) * 114
        y = 222 + (i // 2) * 32
        knapp(d, (x, y, x + 110, y + 28), n)
    faner(d, 2)
    return im


def mer():
    im, d = ny()
    status(d, lader=True, bat=64)
    tekst(d, (10, 34), "Mer", font("semi", 19))
    tekst(d, (12, 66), "Lysstyrke", font("reg", 10), GRAA)
    bar(d, 90, 70, 136, 5, 0.8)
    d.ellipse([(90 + 136 * 0.8 - 6) * S, 66 * S, (90 + 136 * 0.8 + 6) * S, 78 * S], fill=HVIT)
    tekst(d, (12, 92), "Søvn etter", font("reg", 10), GRAA)
    bar(d, 90, 96, 96, 5, 0.15)
    d.ellipse([(90 + 96 * 0.15 - 6) * S, 92 * S, (90 + 96 * 0.15 + 6) * S, 104 * S], fill=HVIT)
    tekst(d, (228, 90), "40 s", font("semi", 11), HVIT, "ra")
    tekst(d, (12, 118), "Tasteoppsett (toppen du har printet)", font("reg", 9.5), GRAA)
    for i, n in enumerate("ABC"):
        knapp(d, (8 + i * 76, 136, 80 + i * 76, 164), n, valgt=i == 0)
    knapp(d, (8, 172, 118, 204), "Lær IR", fill=(52, 44, 30), farge=GULL)
    knapp(d, (122, 172, 232, 204), "Skjold-rom")
    knapp(d, (8, 210, 232, 240), "Hold våken (for oppdatering)")
    tekst(d, (12, 248), "Wi-Fi −58 dBm · 192.168.1.60", font("reg", 9.5), (110, 108, 104))
    tekst(d, (12, 263), "Batteri 3,92 V · 64 % · lader", font("reg", 9.5), (110, 108, 104))
    faner(d, 3)
    return im


def dokk():
    """I dokken: stor klokke, dato, lading og nå-kortet (her Skjold med cover)."""
    im, d = ny()
    status(d, "Skjold", "note", bat=64, lader=True)
    tekst(d, (120, 40), "21:47", font("lett", 64), HVIT, "ma")
    tekst(d, (120, 114), "søndag 8. november", font("semi", 11), GRAA, "ma")
    d.polygon([(98 * S, 141 * S), (93 * S, 151 * S), (98 * S, 151 * S), (95 * S, 160 * S), (104 * S, 147 * S), (99 * S, 147 * S), (102 * S, 141 * S)], fill=GULL)
    tekst(d, (110, 139), "64 %", font("semi", 17), HVIT)
    tekst(d, (120, 166), "lader", font("reg", 10), (110, 108, 104), "ma")
    r(d, (8, 190, 232, 276), 16, fill=(26, 26, 29))
    cv = cover(56 * S)
    m = Image.new("L", cv.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, cv.size[0], cv.size[1]], 12 * S, fill=255)
    im.paste(cv, (20 * S, 205 * S), m)
    d = ImageDraw.Draw(im)
    f = font("semi", 12)
    t = "Morgenklassisk"
    while d.textlength(t, font=f) > 92 * S:   # som long_mode: DOT i fastvaren (92 px bred)
        t = t[:-2] + "…"
    tekst(d, (86, 207), t, f)
    tekst(d, (86, 227), "NRK P2 · radio", font("reg", 9.5), GRAA)
    bar(d, 86, 252, 132, 4, 0.42)
    d.ellipse([184 * S, 208 * S, 220 * S, 244 * S], fill=GULL)
    ikon(d, "pause", 202, 226, BG, 0.8)
    faner(d, 0)
    return im


SIDER = [("start", start), ("velger", velger), ("apper", apper), ("innganger", innganger), ("aktivitet", aktivitet),
         ("spiller", spiller), ("hjem", hjem), ("mer", mer), ("dokk", dokk)]


def main():
    mappe = os.path.join(HER, "render")
    os.makedirs(mappe, exist_ok=True)
    for f in os.listdir(mappe):
        if f.startswith("skjerm-") and f.endswith(".png"):
            os.remove(os.path.join(mappe, f))
    for i, (navn, f) in enumerate(SIDER, 1):
        fn = os.path.join(mappe, f"skjerm-{i}-{navn}.png")
        f().save(fn, optimize=True)
        print("skrev", os.path.relpath(fn, HER))
    # alle sidene i ett bilde (LES_MEG)
    ark = Image.new("RGB", (5 * 250 * 2 + 10, 2 * 330 * 2 + 10), (232, 230, 224))
    for i, (navn, f) in enumerate(SIDER):
        b = Image.open(os.path.join(mappe, f"skjerm-{i + 1}-{navn}.png")).resize((480, 640), Image.LANCZOS)
        ark.paste(b, (10 + (i % 5) * 500, 10 + (i // 5) * 660))
    ark.save(os.path.join(mappe, "skjerm-oversikt.png"), optimize=True)
    print("skrev render/skjerm-oversikt.png")


if __name__ == "__main__":
    main()
