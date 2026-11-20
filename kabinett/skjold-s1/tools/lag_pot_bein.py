"""Tegning: beina på en dobbel B50K-pot (6 bein) – hvordan den holdes, og hvilket bein som er hvilket,
sett forfra, ovenfra (komponentsiden) og nedenfra (loddesiden, speilvendt).
Lager ../pot_bein.svg og ../pot_bein.png.   python3 lag_pot_bein.py"""
import os

HER = os.path.dirname(os.path.abspath(__file__))
UT = os.path.join(HER, "..", "pot_bein")
INK, GRA, BG, KORT, LINJE = "#1d1d1f", "#55554f", "#f7f6f2", "#ffffff", "#d6d4cc"
FORAN, BAK, GLID, KROPP, METALL = "#7fb2ff", "#f2b25c", "#2f9e5a", "#3a3a3c", "#b9b9b4"
s = []


def t(x, y, txt, size=18, w=400, fill=INK, anchor="start"):
    s.append(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" fill="{fill}" text-anchor="{anchor}">{txt}</text>')


def panel(x, y, w, h, tittel, under=""):
    s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{KORT}" stroke="{LINJE}" stroke-width="2"/>')
    t(x + 24, y + 40, tittel, 24, 700)
    if under:
        t(x + 24, y + 68, under, 16, 400, GRA)


def bein(x, y, n, farge, r=17):
    s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{farge}" stroke="{INK}" stroke-width="3"/>')
    t(x, y + 6, str(n), 17, 700, INK, "middle")
    if n in (2, 5):
        s.append(f'<circle cx="{x}" cy="{y}" r="{r+6}" fill="none" stroke="{GLID}" stroke-width="3" stroke-dasharray="5 4"/>')


s.append('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 1060" width="1600" height="1060" font-family="Sora, Arial, sans-serif">')
s.append(f'<rect width="100%" height="100%" fill="{BG}"/>')
t(40, 60, "B50K med 6 bein: hvilket bein er hvilket", 34, 700)
t(40, 96, "To potmetre på samme aksel: rad 1–2–3 (nærmest akselen) og rad 4–5–6 (bak). Midtbeinet i hver rad (2 og 5) er glideren.", 18, 400, GRA)

# A forfra
panel(40, 130, 500, 560, "A · Forfra", "Akselen peker mot deg, beina ned")
cx = 290
s.append(f'<rect x="{cx-120}" y="250" width="240" height="190" rx="14" fill="{KROPP}"/>')
s.append(f'<circle cx="{cx}" cy="345" r="62" fill="#5b5b5e" stroke="#888" stroke-width="3"/>')
s.append(f'<circle cx="{cx}" cy="345" r="30" fill="#c9c9c4" stroke="{INK}" stroke-width="2"/>')
s.append(f'<rect x="{cx-4}" y="318" width="8" height="54" fill="{INK}"/>')
t(cx, 285, "B50K", 16, 700, "#fff", "middle")
for i, dx in enumerate((-70, 0, 70)):
    x = cx + dx
    s.append(f'<rect x="{x-6}" y="440" width="12" height="110" fill="{METALL}"/>')
    bein(x, 572, i + 1, FORAN)
t(cx, 626, "Rad bak (4 – 5 – 6) står rett bak 1 – 2 – 3", 16, 400, GRA, "middle")
t(cx, 652, "1 står bak 4, 2 bak 5, 3 bak 6", 16, 400, GRA, "middle")
# pil for med klokka
s.append(f'<path d="M{cx+80},{280} A95,95 0 0 1 {cx+105},{390}" fill="none" stroke="{GLID}" stroke-width="4" marker-end="url(#pil)"/>')
s.append(f'<defs><marker id="pil" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{GLID}"/></marker></defs>')
t(cx + 150, 330, "med", 15, 700, GLID); t(cx + 150, 350, "klokka", 15, 700, GLID)

# B ovenfra
panel(560, 130, 500, 560, "B · Ovenfra (komponentsiden)", "Akselen peker ned i bildet, mot fronten")
cx = 810
s.append(f'<rect x="{cx-130}" y="230" width="260" height="250" rx="14" fill="{KROPP}" opacity="0.92"/>')
s.append(f'<rect x="{cx-22}" y="480" width="44" height="120" fill="#c9c9c4" stroke="{INK}" stroke-width="2"/>')
t(cx, 630, "aksel / knapp (front)", 16, 700, INK, "middle")
for i, dx in enumerate((-70, 0, 70)):
    bein(cx + dx, 420, i + 1, FORAN)
    bein(cx + dx, 300, i + 4, BAK)
t(cx - 150, 425, "foran", 15, 700, GRA, "end"); t(cx - 150, 305, "bak", 15, 700, GRA, "end")
t(cx, 362, "beina sett gjennom huset", 14, 400, "#ddd", "middle")

# C nedenfra
panel(1080, 130, 480, 560, "C · Nedenfra (loddesiden)", "SPEILVENDT: 1 og 3 bytter side")
cx = 1320
s.append(f'<rect x="{cx-130}" y="230" width="260" height="250" rx="14" fill="#e9e7e0" stroke="{INK}" stroke-width="2" stroke-dasharray="8 6"/>')
s.append(f'<rect x="{cx-22}" y="480" width="44" height="120" fill="#c9c9c4" stroke="{INK}" stroke-width="2"/>')
t(cx, 630, "aksel / knapp (front)", 16, 700, INK, "middle")
for i, dx in enumerate((70, 0, -70)):
    bein(cx + dx, 420, i + 1, FORAN)
    bein(cx + dx, 300, i + 4, BAK)
t(cx, 362, "loddepunktene på kortet", 14, 400, GRA, "middle")

# D slik sjekker du
panel(40, 710, 760, 320, "D · Sjekk det med multimeteret")
rader = [("Mellom", "Hva du ser"),
         ("1–3 og 4–6", "ca. 42–50 kΩ, endrer seg ikke når du vrir (endene)"),
         ("1–2 og 4–5", "øker når du vrir med klokka (sett forfra)"),
         ("2–3 og 5–6", "minker når du vrir med klokka"),
         ("1–4, 2–5 …", "ingen kontakt (OL) – to separate potmetre")]
for i, (a, b) in enumerate(rader):
    y = 795 + i*44
    t(70, y, a, 19, 700, INK if i else GRA)
    t(250, y, b, 19, 400 if i else 700, INK if i else GRA)
t(70, 1012, "Går 1–2 ned når du vrir med klokka, er 1 og 3 byttet om på din pot – bare bytt navn på dem.", 16, 400, GRA)

# E i Lepy-en
panel(820, 710, 740, 320, "E · I Lepy LP-808")
for i, linje in enumerate((
        ("Akselen går ut gjennom frontpanelet,", True),
        ("så rad 1–2–3 er nærmest fronten.", False),
        ("Én rad er venstre kanal, den andre høyre.", True),
        ("Hvilken som er hvilken spiller ingen rolle", False),
        ("så lenge begge radene får like motstander.", False),
        ("Ta bilde av kortet og merk bein 1 med tusj før du lodder.", True))):
    t(850, 800 + i*38, linje[0], 19, 700 if linje[1] else 400, INK if linje[1] else GRA)
s.append("</svg>")

open(UT + ".svg", "w").write("\n".join(s))
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if os.path.exists("/opt/pw-browsers/chromium") else p.chromium.launch()
    pg = b.new_page(viewport={"width": 1600, "height": 1060}, device_scale_factor=1)
    pg.goto("file://" + os.path.abspath(UT + ".svg"))
    pg.screenshot(path=UT + ".png")
    b.close()
print(UT + ".png")
