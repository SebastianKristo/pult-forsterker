#!/usr/bin/env python3
"""Hullkortet (kobbersiden, speilvendt) i stor skala: stripene, bryterbeina, kuttene, GND-lenkene og hver ledning fra
loddehullet ut til MCP-modulen, og MCP ↔ XIAO. Lager fjernkontroll_hullkort_kort.svg (python3 lag_kortkobling.py)."""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import hullkort as hk  # noqa: E402

S = 11.0                                   # px per mm
W, H = 2100, 1720
BX = 785                                   # kortets venstre kant (speilvendt: kolonne S til venstre)
BY = 170
X0, X1 = hk.KANT_X0, hk.KANT_X1
N0 = hk.KANT_N0
BW = (X1 - X0) * S
HALV = hk.P * S / 2            # en halv hullavstand i px


def px(k, j):
    x, n = hk.hull_xy(k, j)
    return BX + (X1 - x) * S, BY + (n - N0) * S   # speilvendt i x (sett nedenfra)


BOKST = "ABCDEFGHIJKLMNOPQRS"
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Sora, Arial, sans-serif">',
     '<rect width="100%" height="100%" fill="#f7f6f2"/>',
     '<style>.m{font-family:IBM Plex Mono,monospace;font-size:14px;fill:#1d1d1f}.s{font-size:15px;fill:#55554f}.t{font-size:17px;font-weight:700;fill:#1d1d1f}</style>',
     '<text x="40" y="58" font-size="34" font-weight="700" fill="#1d1d1f">Skjold Fjernkontroll – hullkortet, kobbersiden (sett nedenfra)</text>',
     '<text x="40" y="92" class="s">Bryterne står på oppsiden; her ser du loddesiden. Hver farget ledning loddes i hullet med prikken og går til MCP-pinnen på merkelappen. Rødt × = kutt stripa (3,5 mm bor).</text>']
h = hk.hullkart()
kutt, seg = hk.kutt_og_segmenter(h)
led = hk.ledninger_paa_kortet()
# omriss + striper
pts = " ".join(f"{BX + (X1 - x) * S:.1f},{BY + (n - N0) * S:.1f}" for x, n in hk.omriss())
o.append(f'<polygon points="{pts}" fill="#d9a26a" stroke="#6b4a26" stroke-width="3"/>')
for k in range(hk.K_MIN, hk.K_MAX + 1):
    js = [j for j in range(hk.J_MIN, hk.J_MAX + 1) if hk.paa_kortet(k, j)]
    if not js:
        continue
    x, y0 = px(k, js[0]); _, y1 = px(k, js[-1])
    o.append(f'<rect x="{x - 9}" y="{y0 - 12}" width="18" height="{y1 - y0 + 24}" rx="3" fill="#e9b97e"/>')
    o.append(f'<text x="{x}" y="{BY - 14}" text-anchor="middle" class="m" font-weight="700">{BOKST[k - hk.K_MIN]}</text>')
for j in range(hk.J_MIN, hk.J_MAX + 1, 5):
    _, y = px(0, j)
    o.append(f'<text x="{BX + BW + 14}" y="{y + 5}" class="m" fill="#8b8b86">{j - hk.J_MIN + 1}</text>')
# hull
for k in range(hk.K_MIN, hk.K_MAX + 1):
    for j in range(hk.J_MIN, hk.J_MAX + 1):
        if hk.paa_kortet(k, j):
            x, y = px(k, j)
            o.append(f'<circle cx="{x}" cy="{y}" r="4.2" fill="#f7f6f2"/>')
# brytere (omriss, sett gjennom kortet) og bein
for b in hk.BRYTERE:
    bein = hk.bein(b)
    xs = [px(k, j)[0] for k, j, _ in bein]; ys = [px(k, j)[1] for k, j, _ in bein]
    o.append(f'<rect x="{min(xs) - 14}" y="{min(ys) - 10}" width="{max(xs) - min(xs) + 28}" height="{max(ys) - min(ys) + 20}" rx="6" fill="none" stroke="#5a4a3a" stroke-width="1.5" stroke-dasharray="5 4"/>')
    for k, j, nett in bein:
        x, y = px(k, j)
        c = "#1d1d1f" if nett == "GND" else hk.farge(nett)[1]
        o.append(f'<circle cx="{x}" cy="{y}" r="7" fill="{c}" stroke="#fff" stroke-width="1.5"/>')
# kutt
for k, j, typ in kutt:
    if typ == "hull":
        x, y = px(k, j)
        o.append(f'<path d="M{x - 9} {y - 9} L{x + 9} {y + 9} M{x + 9} {y - 9} L{x - 9} {y + 9}" stroke="#e5312b" stroke-width="4"/>')
    else:
        x, y = px(k, j)
        o.append(f'<line x1="{x - 11}" y1="{y}" x2="{x + 11}" y2="{y}" stroke="#e5312b" stroke-width="4"/>')
# ledninger: GND-lenker på kortet, tasteledninger ut til merkelapper
venstre, hoyre = [], []
for nett, (k, j), maal, beskr in led:
    x, y = px(k, j)
    c = "#1d1d1f" if nett == "GND" else hk.farge(nett)[1]
    if isinstance(maal, tuple):
        x2, y2 = px(*maal)
        ym = max(y, y2) + HALV * 0.5   # i mellomrommet under hullraden, ikke over andre hull
        o.append(f'<path d="M{x} {y} L{x} {ym} L{x2} {ym} L{x2} {y2}" stroke="#1d1d1f" stroke-width="4" fill="none"/>')
        o.append(f'<circle cx="{x}" cy="{y}" r="6" fill="#1d1d1f"/><circle cx="{x2}" cy="{y2}" r="6" fill="#1d1d1f"/>')
        continue
    fargenavn = "svart" if nett == "GND" else hk.farge(nett)[0]
    tekst = beskr.split(" → ")[0].replace("_", " ")
    (venstre if x < BX + BW / 2 else hoyre).append((y, x, c, f"{tekst} → {maal} ({fargenavn})", (k, j)))


BRUKT = set()


def kanal(y, side):
    """En vannrett bane i mellomrommet mellom to hullrader (ikke gjennom andre hull); ledig for denne siden."""
    for d in (HALV, -HALV, 3 * HALV, -3 * HALV, 5 * HALV, -5 * HALV):
        if (side, round(y + d)) not in BRUKT:
            BRUKT.add((side, round(y + d)))
            return y + d
    return y + HALV


def merk(liste, side):
    liste.sort()
    sist = -99
    for y, x, c, tekst, (k, j) in liste:
        ly = max(y, sist + 36); sist = ly
        hull = f"{BOKST[k - hk.K_MIN]}{j - hk.J_MIN + 1}"
        yk = kanal(y, side)
        if side == "v":
            ex = BX - 40
            o.append(f'<path d="M{x} {y} L{x} {yk} L{BX - 10} {yk} L{ex} {ly} L{ex - 30} {ly}" stroke="{c}" stroke-width="5" fill="none" stroke-linejoin="round"/>')
            o.append(f'<text x="{ex - 38}" y="{ly + 5}" text-anchor="end" font-size="16" fill="#1d1d1f"><tspan font-weight="700">{hull}</tspan> {tekst}</text>')
        else:
            ex = BX + BW + 70
            o.append(f'<path d="M{x} {y} L{x} {yk} L{BX + BW + 10} {yk} L{ex} {ly} L{ex + 30} {ly}" stroke="{c}" stroke-width="5" fill="none" stroke-linejoin="round"/>')
            o.append(f'<text x="{ex + 38}" y="{ly + 5}" font-size="16" fill="#1d1d1f"><tspan font-weight="700">{hull}</tspan> {tekst}</text>')
        o.append(f'<circle cx="{x}" cy="{y}" r="8" fill="{c}" stroke="#fff" stroke-width="2.5"/>')


merk(venstre, "v")
merk(hoyre, "h")
# forklaring + MCP ↔ XIAO
yy = 1560
o.append(f'<circle cx="60" cy="{yy}" r="7" fill="#2f6fd0"/><text x="76" y="{yy + 5}" class="s">farget bein = tastens side</text>')
o.append(f'<circle cx="320" cy="{yy}" r="7" fill="#1d1d1f"/><text x="336" y="{yy + 5}" class="s">sort bein = GND-siden (stripene E, I, O)</text>')
o.append(f'<path d="M640 {yy - 9} L658 {yy + 9} M658 {yy - 9} L640 {yy + 9}" stroke="#e5312b" stroke-width="4"/><text x="670" y="{yy + 5}" class="s">kutt stripa</text>')
o.append(f'<line x1="800" y1="{yy}" x2="840" y2="{yy}" stroke="#1d1d1f" stroke-width="4"/><text x="850" y="{yy + 5}" class="s">GND-lenke på kobbersiden</text>')
o.append(f'<text x="40" y="{yy + 50}" class="t">Videre fra MCP-modulen til XIAO ESP32S3:</text>')
o.append(f'<text x="40" y="{yy + 80}" class="s">VCC → 3V3 (rød) · GND → GND (svart) · SDA → D4 (blå) · SCL → D5 (gul) · INTA → D1 (hvit) · GPB6 → IR-mottakerens VCC · GPB7 ← dokken (68 k / 100 k).</text>')
o.append('</svg>')
open(os.path.join(HER, "fjernkontroll_hullkort_kort.svg"), "w").write("\n".join(o))
print("skrev fjernkontroll_hullkort_kort.svg")
