"""Tegning: slik måler du motstanden i et B50K-potensiometer (Lepy LP-808) med multimeter.
Lager ../pot_maling.svg og ../pot_maling.png (PNG via Playwright/Chromium).   python3 lag_pot_maling.py"""
import os

HER = os.path.dirname(os.path.abspath(__file__))
UT = os.path.join(HER, "..", "pot_maling")
INK, GRA, BG, KORT, LINJE = "#1d1d1f", "#55554f", "#f7f6f2", "#ffffff", "#d6d4cc"
ROD, SVART, BLA, GRONN, ORANSJE = "#d93a2b", "#2b2b2b", "#7fb2ff", "#2f9e5a", "#e08a1e"
s = []


def t(x, y, txt, size=18, w=400, fill=INK, anchor="start"):
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{txt}</text>')


def panel(x, y, w, h, tittel):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{KORT}" stroke="{LINJE}" stroke-width="2"/>')
    t(x + 24, y + 40, tittel, 24, 700)


def pot(cx, cy, vinkel=None, lav=False):
    """Poten sett ovenfra med 3 bein (én rad) nedover. Returnerer beinenes spisser."""
    s.append(f'<rect x="{cx-90}" y="{cy-60}" width="180" height="110" rx="12" fill="#3a3a3c"/>')
    s.append(f'<circle cx="{cx}" cy="{cy-5}" r="34" fill="#8b8b86"/>')
    if vinkel is not None:
        import math
        a = math.radians(vinkel)
        s.append(f'<line x1="{cx}" y1="{cy-5}" x2="{cx + 30*math.sin(a):.1f}" y2="{cy-5 - 30*math.cos(a):.1f}" stroke="#fff" stroke-width="5" stroke-linecap="round"/>')
    t(cx, cy + 40, "B50K", 14, 700, "#fff", "middle")
    spisser = []
    for i, dx in enumerate((-55, 0, 55)):
        x = cx + dx
        s.append(f'<rect x="{x-5}" y="{cy+50}" width="10" height="70" fill="#b9b9b4"/>')
        s.append(f'<circle cx="{x}" cy="{cy+132}" r="16" fill="{BLA}" stroke="{INK}" stroke-width="3"/>')
        t(x, cy + 138, str(i + 1), 16, 700, INK, "middle")
        spisser.append((x, cy + 148))
    return spisser


def probe(x0, y0, x1, y1, farge):
    s.append(f'<path d="M{x0},{y0} C{x0},{y0+70} {x1},{y1+60} {x1},{y1+10}" fill="none" stroke="{farge}" stroke-width="5"/>')
    s.append(f'<line x1="{x1}" y1="{y1+12}" x2="{x1}" y2="{y1-6}" stroke="{farge}" stroke-width="9" stroke-linecap="round"/>')
    s.append(f'<line x1="{x1}" y1="{y1-6}" x2="{x1}" y2="{y1-16}" stroke="#999" stroke-width="3"/>')


def display(x, y, verdi, farge=INK):
    s.append(f'<rect x="{x}" y="{y}" width="150" height="56" rx="8" fill="#cfd8c4" stroke="{INK}" stroke-width="3"/>')
    t(x + 75, y + 38, verdi, 26, 700, farge, "middle")


s.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1060" width="1600" height="1060" font-family="Sora, Arial, sans-serif">')
s.append(f'<rect width="100%" height="100%" fill="{BG}"/>')
t(40, 60, "Slik måler du motstanden i B50K-poten", 34, 700)
t(40, 96, "B50K = lineær 50 kΩ, dobbel: to rader med 3 bein (én per kanal). Bein 1 og 3 er endene, bein 2 (midten) er glideren.", 18, 400, GRA)

# 1 multimeteret
panel(40, 130, 740, 430, "1 · Gjør klart multimeteret")
mx, my = 110, 190
s.append(f'<rect x="{mx}" y="{my}" width="220" height="340" rx="22" fill="#f2c230" stroke="{INK}" stroke-width="3"/>')
display(mx + 35, my + 25, "000.0")
s.append(f'<circle cx="{mx+110}" cy="{my+170}" r="62" fill="#3a3a3c"/>')
s.append(f'<line x1="{mx+110}" y1="{my+170}" x2="{mx+150}" y2="{my+122}" stroke="#fff" stroke-width="8" stroke-linecap="round"/>')
t(mx + 150, my + 100, "Ω 200k", 15, 700, INK)
t(mx + 30, my + 112, "V", 15, 700, GRA); t(mx + 22, my + 240, "A", 15, 700, GRA)
for i, (lab, farge) in enumerate((("COM", SVART), ("VΩ", ROD))):
    cx = mx + 70 + i*80
    s.append(f'<circle cx="{cx}" cy="{my+290}" r="16" fill="{farge}" stroke="{INK}" stroke-width="2"/>')
    t(cx, my + 326, lab, 14, 700, INK, "middle")
x0 = 380
for i, linje in enumerate((
        ("1.", "Strømmen AV, og trekk ut kontakten.", True),
        ("", "Motstand måles alltid uten strøm.", False),
        ("2.", "Velg Ω, område 200k (eller auto).", True),
        ("3.", "Rød ledning i VΩ, svart i COM.", True),
        ("4.", "Hold probene mot hverandre:", True),
        ("", "skjermen skal vise ca. 0 Ω.", False))):
    t(x0, 220 + i*44, linje[0], 20, 700, ROD if i == 0 else INK)
    t(x0 + 30, 220 + i*44, linje[1], 20, 700 if linje[2] else 400, INK if linje[2] else GRA)

# 2 endene
panel(820, 130, 740, 430, "2 · Mål bein 1 og 3 (endene)")
sp = pot(1010, 250, vinkel=-60)
probe(870, 470, sp[0][0], sp[0][1] + 18, SVART)
probe(1150, 470, sp[2][0], sp[2][1] + 18, ROD)
display(1290, 230, "50.0 kΩ", GRONN)
t(1250, 330, "Alltid ca. 50 kΩ (40–60),", 20, 700)
t(1250, 360, "uansett hvor knappen står.", 20, 400, GRA)
t(1250, 410, "Viser den uendelig (1 / OL):", 20, 700)
t(1250, 440, "banen er brutt, poten er ødelagt.", 20, 400, GRA)
t(1250, 490, "Gjør det samme på", 20, 700); t(1250, 520, "den andre raden.", 20, 400, GRA)

# 3 glideren
panel(40, 590, 740, 440, "3 · Mål glideren (bein 2) mot hver ende")
sp = pot(200, 700, vinkel=30)
probe(80, 930, sp[0][0], sp[0][1] + 18, SVART)
probe(330, 930, sp[1][0], sp[1][1] + 18, ROD)
display(400, 660, "30.0 kΩ", GRONN)
t(400, 750, "Bein 1–2: endrer seg når du vrir", 20, 700)
t(400, 780, "Bein 2–3: det motsatte", 20, 700)
t(400, 820, "Eksempel, knappen 60 % mot høyre:", 18, 400, GRA)
bx, by, bw = 400, 845, 340
s.append(f'<rect x="{bx}" y="{by}" width="{bw*0.6:.0f}" height="34" fill="{BLA}" stroke="{INK}" stroke-width="2"/>')
s.append(f'<rect x="{bx + bw*0.6:.0f}" y="{by}" width="{bw*0.4:.0f}" height="34" fill="{ORANSJE}" stroke="{INK}" stroke-width="2"/>')
t(bx + bw*0.3, by + 24, "1–2 ≈ 30 kΩ", 16, 700, INK, "middle")
t(bx + bw*0.8, by + 24, "2–3 ≈ 20 kΩ", 16, 700, INK, "middle")
t(bx, by + 64, "1–2 + 2–3 = ca. 50 kΩ (alltid)", 18, 700)
t(bx, by + 94, "Ved 60 %: 10 og 40 kΩ? Da er den A50K", 16, 400, GRA)
t(bx, by + 116, "(logaritmisk), ikke B.", 16, 400, GRA)

# 4 i kretsen
panel(820, 590, 740, 440, "4 · Sitter poten i kortet? Løft ett bein")
s.append(f'<rect x="860" y="842" width="380" height="36" fill="#2e7d4f" stroke="{INK}" stroke-width="2"/>')
t(1180, 866, "kretskortet", 16, 700, "#fff", "middle")
sp = pot(1050, 700)
# bein 2 løftet: en gul «lodde-løs»-markering
s.append(f'<circle cx="{sp[1][0]}" cy="{sp[1][1]-16}" r="26" fill="none" stroke="{ORANSJE}" stroke-width="5" stroke-dasharray="8 6"/>')
t(1270, 690, "De andre delene på kortet", 20, 700)
t(1270, 720, "måles med, så tallene blir", 20, 400, GRA)
t(1270, 750, "for lave.", 20, 400, GRA)
t(1270, 800, "Lodd løs midtbeinet (2), eller", 20, 700)
t(1270, 830, "løft ut hele poten, før du", 20, 400, GRA)
t(1270, 860, "måler.", 20, 400, GRA)
t(860, 930, "Bytte til faste motstander: vri knappen dit du vil ha den, løft ut poten", 18, 700)
t(860, 958, "uten å vri, og mål 1–2 og 2–3. Det er motstandene du lodder inn", 18, 400, GRA)
t(860, 986, "(nærmeste standardverdi), på begge radene.", 18, 400, GRA)
t(1555, 1015, "Se også lepy_pot_bytte.png.", 14, 400, GRA, "end")
s.append("</svg>")

open(UT + ".svg", "w").write("\n".join(s))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/opt/pw-browsers/chromium') if os.path.exists('/opt/pw-browsers/chromium') else p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 1060}, device_scale_factor=1)
    pg.goto("file://" + os.path.abspath(UT + ".svg"))
    pg.screenshot(path=UT + ".png")
    b.close()
print(UT + ".png")
