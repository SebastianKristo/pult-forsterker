"""Tegn innmaten i Skjold Fjernkontroll som merkede diagrammer.

render/13_oppsett.png    ovenfra (bunnen med alle kjøpte deler, tastekortet som stiplet omriss) og et snitt fra siden
render/14_koblinger.png  koblingsskjema: hvilke ledninger går hvor, med lengde og tykkelse
(full variant: 13_oppsett_full.png)

Leser STL-ene i montert stilling (asm/ og asm_full/), så tegningen alltid følger modellen.
Bruk:  python3 lag_oppsett.py   (kjøres av lag_render.sh etter lag_stl.sh)"""
import os

import numpy as np
import trimesh
from PIL import Image, ImageDraw, ImageFont

import taster

HER = os.path.dirname(os.path.abspath(__file__))
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
W = 55.0

# (fil, navn, feste, farge) – nummereres i denne rekkefølgen
DELER = [
    ("batteri", "LiPo 603450, 1200 mAh (34 × 50 × 6 mm)", "lomma under skjermen, 0,5 mm klaring; skumtape over", "#8f959c"),
    ("mcu", "ESP32-S3 SuperMini (18 × 22,6 mm)", "1 mm hylle i lomma, USB-C mot nesen, antenne mot halen", "#26262b"),
    ("lader", "TP4056 USB-C med vern (17 × 28 mm)", "lomma i halen, USB-C i forsenkningen; en dråpe lim", "#2c55b0"),
    ("ir", "IR-kort 34 × 6 mm: 3 × IR-diode, VS1838B, AO3400", "står i sporet i nesen, diodene mot vinduet", "#2f7a46"),
    ("vib", "Vibrasjonsbryter SW-18010P (Ø5 × 12 mm)", "i de to vuggene; en dråpe lim", "#b8b8c0"),
    ("motor", "Vibrasjonsmotor 1027 (Ø10 × 2,7 mm)", "i ringen, selvklebende bakside", "#9aa0a6"),
    ("ledninger", "Ledningsbunter, 30 AWG silikon", "i kanalene langs gulvet (1,5 mm)", "#d0392b"),
    ("flex", "Flatkabler: skjerm 18p, berøring 6p", "ned bak glasset, inn i J1/J2 under tastekortet", "#d9902a"),
    ("kort", "Tastekort 1,0 mm: brytere, TCA9555, J1, J2", "i toppen, klemt av pinnene og midtskruen", "#1a5c33"),
]


def last(asm, n):
    return trimesh.load(os.path.join(HER, asm, n + ".stl"))


def tegn_flate(d, mesh, til_px, farge, alpha=255, akse=(0, 1)):
    """Fyll alle trekantene projisert ned på planet gitt av akse (indekser i xyz)."""
    v = mesh.vertices[:, list(akse)]
    rgb = tuple(int(farge[i:i + 2], 16) for i in (1, 3, 5)) + (alpha,)
    for f in mesh.faces:
        p = [til_px(*v[i]) for i in f]
        d.polygon(p, fill=rgb)


def nummer(d, xy, i, col, f):
    x, y = xy
    d.ellipse([x - 15, y - 15, x + 15, y + 15], fill="#ffffff", outline=col, width=3)
    d.text((x, y), str(i), fill="#202020", font=f, anchor="mm")


def oppsett(variant):
    taster.bruk(variant)
    L = taster.L
    asm = "asm" if variant == "kort" else "asm_full"
    M = {n: last(asm, n) for n, *_ in DELER}
    M["skjerm"] = last(asm, "skjerm")
    bunn = last(asm, "bunn")
    s, pad, top = 7.0, 50, 90
    vw, vh = int(L * s), int(W * s)
    zs = 2.0 * s   # snittet: loddrett skala 2:1
    sh = int(13.5 * zs)
    leg_h = 34 * len(DELER) + 60
    img = Image.new("RGB", (vw + 2 * pad, top + vh + 60 + sh + 70 + leg_h), "#f7f6f3")
    d = ImageDraw.Draw(img, "RGBA")
    ft, fb, fs = ImageFont.truetype(F, 20), ImageFont.truetype(FB, 26), ImageFont.truetype(F, 17)
    navn = "standard" if variant == "kort" else "full variant"
    d.text((pad, 24), f"Skjold Fjernkontroll ({navn}, {W:.0f} × {L:.0f} mm): innmaten sett ovenfra, nesen til venstre",
           fill="#202020", font=fb)

    # ovenfra: bildets x = n (avstand fra nesen), bildets y = x (venstre side øverst)
    def px(x, y):
        return (pad + (L - y) * s, top + x * s)

    tegn_flate(d, bunn, px, "#d7d3cc")
    for i, (n, nv, fe, col) in enumerate(DELER, 1):
        if n == "kort":
            continue
        tegn_flate(d, M[n], px, col, 235)
    # tastekortet og skjermen som stiplede omriss
    for n, col in (("kort", "#1a5c33"), ("skjerm", "#5a5a66")):
        (x0, y0, _), (x1, y1, _) = M[n].bounds
        a, b = px(x0, y1), px(x1, y0)
        for k in range(int(a[0]), int(b[0]), 14):
            d.line([(k, a[1]), (min(k + 7, b[0]), a[1])], fill=col, width=2)
            d.line([(k, b[1]), (min(k + 7, b[0]), b[1])], fill=col, width=2)
        for k in range(int(a[1]), int(b[1]), 14):
            d.line([(a[0], k), (a[0], min(k + 7, b[1]))], fill=col, width=2)
            d.line([(b[0], k), (b[0], min(k + 7, b[1]))], fill=col, width=2)
    d.text(px(W - 4, M["skjerm"].bounds[1][1] - 2), "skjermen (i toppen)", fill="#5a5a66", font=fs, anchor="lm")
    kb = M["kort"].bounds
    d.text(px(W - 4, kb[1][1] - 2), "tastekortet (i toppen)", fill="#1a5c33", font=fs, anchor="lm")
    # skruer
    for sx, sy in [(7.5, L - 5.5), (W - 7.5, L - 5.5), (4.9, 8), (W - 4.9, 8), (W - 7, L - 95)]:
        x, y = px(sx, sy)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], outline="#202020", width=2)
        d.line([(x - 4, y - 4), (x + 4, y + 4)], fill="#202020", width=2)
    # nummer på hver del
    for i, (n, *_r, col) in enumerate(DELER, 1):
        c = M[n].bounds.mean(axis=0)
        if n == "ledninger":
            c = [3.75, L - 60, 0]
        if n == "kort":
            c = [W - 6, kb[0][1] + 12, 0]
        nummer(d, px(c[0], c[1]), i, col, fs)
    # mål
    d.text((pad, top + vh + 8), "← nesen (IR)", fill="#555", font=fs)
    d.text((pad + vw, top + vh + 8), "halen (USB-C) →", fill="#555", font=fs, anchor="ra")
    for nn in range(0, int(L) + 1, 20):
        x = pad + nn * s
        d.line([(x, top + vh + 30), (x, top + vh + 38)], fill="#888", width=1)
        d.text((x, top + vh + 40), f"{nn}", fill="#888", font=ImageFont.truetype(F, 13), anchor="ma")

    # snitt fra siden gjennom SuperMini-en (x = 13,5 mm)
    y0 = top + vh + 70
    d.text((pad, y0 - 4), "Snitt gjennom ESP-en (x = 13,5 mm), loddrett skala 2:1", fill="#202020", font=ft)
    y0 += 26

    def ps(y, z):
        return (pad + (L - y) * s, y0 + (13.5 - z) * zs)

    for n, col in [("bunn", "#bdb8b0"), ("topp", "#e4e0d8"), ("kort", "#1a5c33"), ("skjerm", "#33333a"),
                   ("batteri", "#8f959c"), ("mcu", "#26262b"), ("lader", "#2c55b0"), ("ir", "#2f7a46"), ("hetter", "#3a3a40")]:
        m = M[n] if n in M else last(asm, n)
        sec = m.section(plane_origin=[13.5, 0, 0], plane_normal=[1, 0, 0])
        if sec is None:
            continue
        rgb = tuple(int(col[i:i + 2], 16) for i in (1, 3, 5))
        for poly in sec.discrete:
            p = [ps(q[1], q[2]) for q in poly]
            if len(p) > 2:
                d.polygon(p, fill=rgb + (230,), outline=(40, 40, 40, 120))
    for txt, y, z in (("skjerm", L - 40, 10.2), ("batteri", L - 37, 4.5), ("tastekort", L - 105, 9.9),
                      ("ESP på hylla, USB-C mot nesen", L - 112, 3.2), ("IR", L - 5, 9.5)):
        d.text(ps(y, z), txt, fill="#ffffff" if txt == "batteri" else "#202020", font=fs, anchor="mm")

    # forklaring
    y = y0 + sh + 30
    d.text((pad, y), "Del", fill="#202020", font=ft)
    d.text((pad + 620, y), "Hvor og hvordan den sitter", fill="#202020", font=ft)
    y += 32
    for i, (n, nv, fe, col) in enumerate(DELER, 1):
        nummer(d, (pad + 15, y + 12), i, col, fs)
        bb = M[n].bounds
        nn = f"  (n {L - bb[1][1]:.0f}–{L - bb[0][1]:.0f} mm)" if n not in ("ledninger", "flex") else ""
        d.text((pad + 42, y + 2), nv + nn, fill="#202020", font=fs)
        d.text((pad + 620, y + 2), fe, fill="#404040", font=fs)
        y += 34
    ut = os.path.join(HER, "render", "13_oppsett.png" if variant == "kort" else "13_oppsett_full.png")
    img.save(ut)
    print("skrev", os.path.relpath(ut, HER))


# ---------- koblingsskjema ----------
# (fra, til, signal, lengde mm, tråd)
LEDNINGER = [
    ("Batteri +", "TP4056 B+", "BAT+", 115, "batteriets egen ledning (26–28 AWG), kuttet"),
    ("Batteri −", "TP4056 B−", "BAT−", 115, "batteriets egen ledning, kuttet"),
    ("TP4056 OUT+", "SuperMini 5V", "VBAT", 60, "30 AWG silikon, rød"),
    ("TP4056 OUT−", "SuperMini GND", "GND", 60, "30 AWG silikon, sort"),
    ("TP4056 OUT+", "Tastekort P15", "VBAT", 75, "30 AWG silikon, rød"),
    ("TP4056 OUT−", "Tastekort P16", "GND", 75, "30 AWG silikon, sort"),
    ("TP4056 CHRG", "Tastekort P17", "CHRG", 75, "30 AWG silikon"),
    ("SuperMini 3V3", "Tastekort P1", "3V3", 60, "30 AWG silikon"),
    ("SuperMini GND", "Tastekort P2", "GND", 60, "30 AWG silikon"),
    ("SuperMini GPIO5 / 6", "Tastekort P3 / P4", "SDA / SCL", 60, "30 AWG silikon, tvunnet par"),
    ("SuperMini GPIO2", "Tastekort P5", "INT", 60, "30 AWG silikon"),
    ("SuperMini GPIO9 / 10", "Tastekort P6 / P7", "SCK / MOSI", 60, "30 AWG silikon"),
    ("SuperMini GPIO11 / 12 / 13", "Tastekort P8 / P9 / P10", "DC / RES / BL", 60, "30 AWG silikon"),
    ("SuperMini GPIO8 / 3 / 7", "Tastekort P11 / P12 / P13", "T_SDA / T_SCL / T_INT", 60, "30 AWG silikon"),
    ("SuperMini GPIO1", "Tastekort P14", "VSENSE (220k/220k på kortet)", 60, "30 AWG silikon"),
    ("Tastekort P18 / P19", "Motor rød / sort", "MOT+ / MOT−", 50, "motorens egne ledninger"),
    ("SuperMini GPIO4", "Vibrasjonsbryter ben 1", "VIB (1 MΩ til GND ved ESP)", 50, "30 AWG silikon"),
    ("SuperMini 3V3", "Vibrasjonsbryter ben 2", "3V3", 50, "30 AWG silikon"),
    ("SuperMini GPIO43", "IR-kort G", "IR_TX (1 kΩ på IR-kortet)", 135, "30 AWG silikon, i venstre kanal"),
    ("SuperMini GPIO44", "IR-kort OUT", "IR_RX", 135, "30 AWG silikon, i venstre kanal"),
    ("Tastekort P15", "IR-kort +", "VBAT (IR-diodene)", 145, "30 AWG silikon, i venstre kanal"),
    ("Tastekort P20", "IR-kort VS", "3V3_SW (VS1838B)", 145, "30 AWG silikon, i venstre kanal"),
    ("Tastekort P2", "IR-kort −", "GND", 145, "30 AWG silikon, i venstre kanal"),
]


def koblinger():
    img = Image.new("RGB", (1900, 1100), "#f7f6f3")
    d = ImageDraw.Draw(img, "RGBA")
    ft, fb, fs, fx = (ImageFont.truetype(F, 19), ImageFont.truetype(FB, 24), ImageFont.truetype(F, 16),
                      ImageFont.truetype(FB, 18))
    d.text((40, 24), "Skjold Fjernkontroll: koblingsskjema (standard; full variant er lik, med tre TCA9555)", fill="#202020", font=fb)

    def boks(x, y, w, h, tittel, col, linjer=()):
        d.rounded_rectangle([x, y, x + w, y + h], radius=12, fill=col + "22", outline=col, width=3)
        d.text((x + 12, y + 8), tittel, fill="#202020", font=fx)
        for i, l in enumerate(linjer):
            d.text((x + 12, y + 36 + 21 * i), l, fill="#303030", font=fs)

    B = {
        "bat": (40, 90, 300, 120, "Batteri 603450", "#8f959c", ["JST-PH 2.0: rød +, sort −", "sjekk polariteten!"]),
        "lad": (40, 290, 300, 160, "TP4056 USB-C (halen)", "#2c55b0", ["B+  B−  (batteriet)", "OUT+  OUT−  (VBAT, GND)", "CHRG (rød LED, katode)", "USB-C: bare lading"]),
        "esp": (520, 90, 380, 520, "ESP32-S3 SuperMini", "#26262b",
                ["5V   ← VBAT (OUT+)", "GND  ← OUT−", "3V3  → tastekort P1, vib.bryter", "GPIO1  ← VSENSE", "GPIO2  ← INT (alle TCA9555)",
                 "GPIO3  → T_SCL", "GPIO4  ← vibrasjonsbryter", "GPIO5 / 6  ↔ SDA / SCL", "GPIO7  ← T_INT", "GPIO8  ↔ T_SDA",
                 "GPIO9 / 10  → SCK / MOSI", "GPIO11 / 12  → DC / RES", "GPIO13  → BL (PWM)", "GPIO43  → IR_TX", "GPIO44  ← IR_RX",
                 "", "USB-C (mot nesen): bare for", "første flashing, batteriet frakoblet"]),
        "kort": (1080, 90, 420, 560, "Tastekort (loddepunkter P1–P20)", "#1a5c33",
                 ["P1 3V3   P2 GND", "P3 SDA   P4 SCL   P5 INT", "P6 SCK   P7 MOSI", "P8 DC   P9 RES   P10 BL", "P11 T_SDA  P12 T_SCL  P13 T_INT",
                  "P14 VSENSE   P15 VBAT   P16 GND", "P17 CHRG   P18 MOT+   P19 MOT−", "P20 3V3_SW", "",
                  "på kortet: 2 × TCA9555 (0x20, 0x21),", "15 brytere, AO3401 (3V3_SW),", "AO3400 + 1N4148 (motor),",
                  "VBAT-deler 220k/220k + 100 nF,", "10k pull-up SDA/SCL/INT, 100 nF ×2", "", "J1 18p 0,8 mm ← skjermens FPC", "J2 6p 0,5 mm ← berøringens FPC"]),
        "skj": (1600, 90, 260, 160, "2,8″ skjerm", "#5a5a66", ["ST7789 + FT6336U", "FPC 18p → J1", "FPC 6p → J2"]),
        "ir": (520, 760, 380, 200, "IR-kort (nesen)", "#2f7a46", ["+ : VBAT → 3 × (IR-diode + 10 Ω)", "G : 1 kΩ → AO3400 gate, 100 kΩ til −", "OUT : VS1838B", "VS : 3V3_SW (VS1838B VCC)", "− : GND"]),
        "vib": (40, 560, 300, 110, "Vibrasjonsbryter", "#8a8a96", ["ben 1 → GPIO4", "ben 2 → 3V3"]),
        "mot": (1080, 760, 420, 110, "Vibrasjonsmotor 1027", "#9aa0a6", ["rød → P18 (MOT+)", "sort → P19 (MOT−)"]),
    }
    for k, (x, y, w, h, t, c, ll) in B.items():
        boks(x, y, w, h, t, c, ll)

    def pil(pkt, col, txt="", tp=None):
        d.line(pkt, fill=col, width=4, joint="curve")
        if txt:
            d.text(tp, txt, fill=col, font=fs)

    pil([(190, 210), (190, 290)], "#c0392b", "BAT+ / BAT− 115 mm", (200, 238))
    pil([(340, 320), (430, 320), (430, 130), (520, 130)], "#c0392b", "VBAT, GND", (350, 292))
    pil([(340, 320), (430, 320), (430, 130), (520, 130)], "#c0392b", "60 mm", (440, 220))
    pil([(340, 430), (460, 430), (460, 700), (1000, 700), (1000, 560), (1080, 560)], "#c0392b", "VBAT, GND, CHRG 75 mm", (640, 672))
    pil([(900, 300), (1080, 300)], "#205080", "14 tråder", (930, 270))
    pil([(900, 300), (1080, 300)], "#205080", "60 mm", (950, 308))
    pil([(340, 615), (480, 615), (480, 540), (520, 540)], "#606060", "50 mm", (360, 588))
    pil([(1500, 170), (1600, 170)], "#d9902a", "FPC", (1520, 140))
    pil([(710, 610), (710, 760)], "#2f7a46", "IR_TX, IR_RX 135 mm", (720, 620))
    pil([(1080, 620), (1040, 620), (1040, 860), (900, 860)], "#2f7a46", "VBAT, 3V3_SW,", (915, 800))
    pil([(1080, 620), (1040, 620), (1040, 860), (900, 860)], "#2f7a46", "GND 145 mm", (915, 822))
    pil([(1290, 650), (1290, 760)], "#606060", "50 mm", (1300, 690))

    # tabell over ledningene
    y = 990
    d.text((40, y), "Lengdene er målt i modellen langs kanalene, med 10–15 mm ekstra for bøy og for å kunne løfte toppen av.", fill="#404040", font=fs)
    d.text((40, y + 26), "30 AWG silikon overalt (myk og tynn, 0,6 mm ytre); batteriets egne ledninger til B+/B−; lakktråd 0,2 mm bare på bryterbrettet (variant B).",
           fill="#404040", font=fs)
    d.text((40, y + 52), "Rekkefølge: 1 tastekort → 2 IR-kort → 3 flash ESP via USB-C → 4 ESP-ledninger → 5 TP4056 → 6 batteri sist (se LES_MEG).",
           fill="#404040", font=fs)
    ut = os.path.join(HER, "render", "14_koblinger.png")
    img.save(ut)
    print("skrev", os.path.relpath(ut, HER))


if __name__ == "__main__":
    oppsett("kort")
    oppsett("full")
    koblinger()
