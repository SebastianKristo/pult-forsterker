#!/usr/bin/env python3
"""Ledningsføringen i bunnen av fjernkontrollen (hullkort-utgaven), sett ovenfra i målestokk: delene på gulvet,
stolpene, hullkortet (stiplet) og hvilken vei hver bunt skal ligge. Lager fjernkontroll_hullkort_kabelvei.svg."""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import hullkort as hk  # noqa: E402

S = 6.6
OX, OY = 90, 150
W, L = hk.W, hk.L
CX = hk.CX
CW, CH = 1800, 1560


def p(x, n):
    return OX + x * S, OY + n * S


o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}" font-family="Sora, Arial, sans-serif">',
     '<rect width="100%" height="100%" fill="#f7f6f2"/>',
     '<style>.s{font-size:15px;fill:#55554f}.l{font-size:15px;font-weight:600;fill:#1d1d1f}.h{font-size:22px;font-weight:700;fill:#1d1d1f}</style>',
     '<text x="40" y="58" font-size="32" font-weight="700" fill="#1d1d1f">Skjold Fjernkontroll (hullkort) – slik legges ledningene i bunnen</text>',
     '<text x="40" y="90" class="s">Bunnen sett ovenfra, i målestokk (55 × 202,5 mm). Delene ligger på gulvet på tynn dobbeltsidig tape; hullkortet (stiplet) legges oppå til slutt.</text>']


def rekt(x0, x1, n0, n1, fill, stroke, tekst="", sub="", tc="#1d1d1f", fs=15, rx=4):
    a, b = p(x0, n0); c, d = p(x1, n1)
    o.append(f'<rect x="{a}" y="{b}" width="{c - a}" height="{d - b}" rx="{rx}" fill="{fill}" stroke="{stroke}" stroke-width="2.5"/>')
    if tekst:
        o.append(f'<text x="{(a + c) / 2}" y="{(b + d) / 2 + (0 if sub else 5)}" text-anchor="middle" font-size="{fs}" font-weight="700" fill="{tc}">{tekst}</text>')
    if sub:
        o.append(f'<text x="{(a + c) / 2}" y="{(b + d) / 2 + 18}" text-anchor="middle" font-size="12" fill="{tc}">{sub}</text>')


def bunt(pts, c, w=6, dash=""):
    o.append(f'<polyline points="{" ".join("%.1f,%.1f" % p(x, n) for x, n in pts)}" fill="none" stroke="{c}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round" {dash}/>')


# esken
a, b = p(0, 0); c, d = p(W, L)
o.append(f'<rect x="{a}" y="{b}" width="{c - a}" height="{d - b}" rx="{14 * S}" fill="#e7e5de" stroke="#8b8a83" stroke-width="4"/>')
o.append(f'<text x="{(a + c) / 2}" y="{b - 14}" text-anchor="middle" class="s">▲ nesen (IR-vinduet)</text>')
o.append(f'<text x="{(a + c) / 2}" y="{d + 26}" text-anchor="middle" class="s">▼ halen (USB-C)</text>')
# deler
rekt(W / 2 - 17, W / 2 + 17, 4.5, 10.5, "#3fae6a", "#1f6e3e", "IR-kortet", tc="#fff", fs=13)
rekt(W / 2 - 17, W / 2 + 17, 12, 62, "#b9c0c7", "#58616b", "LiPo 603450", "i lomma · 1 mm skumtape")
for ref, navn, x0, x1, n0, n1, *_ in hk.GULV:
    if "(kort)" in navn or ref == "USBC":
        farge = {"U1": ("#4a4a4c", "#111", "#fff"), "U2": ("#9c86c9", "#4a3680", "#fff"), "A1": ("#e3c79c", "#9b6a2a", "#1d1d1f"),
                 "A2": ("#e3c79c", "#9b6a2a", "#1d1d1f"), "USBC": ("#9a988f", "#555", "#1d1d1f")}[ref]
        tekst = {"U1": "XIAO", "U2": "MCP23017", "A1": "FPC 18p", "A2": "FPC 6p", "USBC": ""}[ref]
        sub = {"U1": "USB-C ut i halen", "U2": "modul", "A1": "skjerm", "A2": "berøring", "USBC": ""}[ref]
        rekt(x0, x1, n0, n1, farge[0], farge[1], tekst, sub, farge[2], 15)
rekt(37.2, 43.2, 149, 169, "#8b8b86", "#444", "pogo", tc="#fff", fs=12)
# stolper og pinner
for x, n in hk.STOLPER + hk.PINNER:
    cx, cy = p(x, n)
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{2.2 * S}" fill="#6b6a64" stroke="#333" stroke-width="2"/>')
# hullkortet (stiplet)
pts = " ".join("%.1f,%.1f" % p(x, n) for x, n in hk.omriss())
o.append(f'<polygon points="{pts}" fill="none" stroke="#7a5a20" stroke-width="3" stroke-dasharray="12 8"/>')
# bunter
FARGE = {"ir": "#2bb3a8", "bat": "#d23a2c", "tast": "#e3b82b", "i2c": "#2f6fd0", "skjerm": "#2f9a52", "pogo": "#8a4fc0", "flex": "#c9a227"}
bunt(hk.BUNTER["IR"], FARGE["ir"], 9)
bunt(hk.BUNTER["batteri"], FARGE["bat"], 8)
# tasteledningene: fra hullkortets kobberside ned til MCP-modulen (vifte inn mot modulens pinner)
for x in (6.0, 10.0, 14.0, 22.0, 30.0, 36.0):
    bunt([(x, 125.5), (min(max(x, 10.0), 28.0), 131.5)], FARGE["tast"], 4, 'stroke-dasharray="3 6"')
bunt([(30.5, 157.0), (30.5, 166.0), (CX - 4.0, 176.0)], FARGE["i2c"], 7)
bunt([(CX + 3.0, 177.0), (33.5, 168.0), (33.5, 126.0), (30.0, 124.5)], FARGE["skjerm"], 7)
bunt([(38.0, 145.0), (38.0, 106.0)], "#e06a5c", 5)
bunt([(40.2, 169.0), (40.2, 175.0), (CX + 6.0, 180.0)], FARGE["pogo"], 6)
bunt([(37.2, 156.0), (29.75, 156.0)], FARGE["pogo"], 4)
# flatkablene fra skjermen (ovenfra)
for x, n in ((26.3, 106.0), (35.5, 91.0)):
    cx, cy = p(x, n)
    o.append(f'<path d="M{cx} {cy - 50} L{cx} {cy - 4}" stroke="{FARGE["flex"]}" stroke-width="10" marker-end=""/><path d="M{cx - 9} {cy - 14} L{cx} {cy - 2} L{cx + 9} {cy - 14}" fill="none" stroke="#7a5a20" stroke-width="3"/>')
# nummer på buntene
num = [((4.0, 40.0), "1"), ((45.5, 120.0), "2"), ((14.0, 124.0), "3"), ((30.5, 162.0), "4"), ((33.5, 140.0), "5"), ((40.2, 172.0), "6"), ((26.3, 98.0), "7")]
for (x, n), t in num:
    cx, cy = p(x, n)
    o.append(f'<circle cx="{cx}" cy="{cy}" r="15" fill="#1d1d1f"/><text x="{cx}" y="{cy + 5}" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">{t}</text>')
# forklaring til høyre
X = 560; Y = 160
o.append(f'<text x="{X}" y="{Y}" class="h">Buntene</text>')
rader = [
    ("1", FARGE["ir"], "IR-bunten (5 ledninger, 200 mm)", "TX, RX, BAT+, GND og IR-strøm. Fra IR-kortet i nesen rett ned langs VENSTRE sidevegg (kanalen på gulvet), forbi batteriet og MCP-en, og inn til XIAO-en i halen. Tvinn dem løst sammen."),
    ("2", FARGE["bat"], "Batteriet (rød + sort, 150 mm)", "Ut fra bakkanten av batteriet, langs HØYRE sidevegg, forbi stolpen, og inn til BAT+ / BAT− på baksiden av XIAO-en. Lodd dem på XIAO-en før den tapes ned."),
    ("3", FARGE["tast"], "Tasteledningene (14 + GND, 30–120 mm)", "Fra hullene på kobbersiden av hullkortet rett ned til MCP-modulens pinner. Ingen bunt: hver ledning så kort som mulig, de henger fritt mellom kortet og MCP-en."),
    ("4", FARGE["i2c"], "MCP → XIAO (5 ledninger, 70 mm)", "SDA, SCL, INTA, 3V3 og GND fra MCP-modulens nedre kant til XIAO-en."),
    ("5", FARGE["skjerm"], "Skjermbunten (XIAO → 18p/6p, 90 mm)", "SCK, MOSI, D/C, RESET og baklys fra XIAO-en opp mellom MCP-en og pogo-kontakten til 18p-adapteren; videre 50 mm til 6p-adapteren. Den røde/svarte (3V3/GND) fra MCP til adapterne følger samme vei."),
    ("6", FARGE["pogo"], "Dokken (pogo)", "+ via 1N5819 til XIAO 5V, og via 68 kΩ til MCP GPB7; − til MCP GND. Korte ledninger, rett mot XIAO-en og MCP-en."),
    ("7", FARGE["flex"], "Flatkablene fra skjermen", "Kommer ovenfra (skjermen ligger i toppen) ned bak glasset, inn i FPC-adapterne med kontaktene ned. Kobles helt til slutt, før hullkortet legges på."),
]
y = Y + 40
for t, c, tit, txt in rader:
    o.append(f'<circle cx="{X + 15}" cy="{y}" r="15" fill="#1d1d1f"/><text x="{X + 15}" y="{y + 5}" text-anchor="middle" font-size="15" font-weight="700" fill="#fff">{t}</text>')
    o.append(f'<line x1="{X + 40}" y1="{y}" x2="{X + 90}" y2="{y}" stroke="{c}" stroke-width="8" stroke-linecap="round"/>')
    o.append(f'<text x="{X + 105}" y="{y + 6}" class="l">{tit}</text>')
    # bryt teksten
    ord_, linje, ly = txt.split(), "", y + 30
    for w in ord_:
        if len(linje) + len(w) > 110:
            o.append(f'<text x="{X + 105}" y="{ly}" class="s">{linje}</text>'); ly += 20; linje = ""
        linje += (" " if linje else "") + w
    o.append(f'<text x="{X + 105}" y="{ly}" class="s">{linje}</text>')
    y = ly + 42
o.append(f'<text x="{X}" y="{y + 10}" class="h">Regler</text>')
regler = ["Alt under hullkortet må ligge flatt: det er bare ca. 0,5 mm luft mellom delene på gulvet og bryterbeina.",
          "Legg ledningene langs sideveggene og i kanalene, aldri over XIAO-ens USB-C eller oppå MCP-brikken.",
          "Hold ledningene unna de grå stolpene og pinnene: de klemmer hullkortet fast og må gå klar.",
          "Klipp bryterbeina til 0,8 mm under kortet, og legg krympestrømpe på alle småkomponentene.",
          "Fest buntene med en stripe kaptontape eller en dråpe lim, så de ikke flytter seg når toppen skrus på.",
          "Gjør gjennomgangstesten med multimeter før batteriet kobles til."]
for i, r in enumerate(regler):
    o.append(f'<text x="{X}" y="{y + 45 + i * 28}" class="s">• {r}</text>')
o.append('</svg>')
open(os.path.join(HER, "fjernkontroll_hullkort_kabelvei.svg"), "w").write("\n".join(o))
print("skrev fjernkontroll_hullkort_kabelvei.svg")
