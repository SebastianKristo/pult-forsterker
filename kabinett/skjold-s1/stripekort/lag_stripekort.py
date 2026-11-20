"""Skjold S1 rev F: koblingskortet for knappene, LED-ringene og volumhjulet på et stripekort (stripene vannrett).

Kortet samler ledningene fra frontpanelet i JST XH-kontakter og har en ULN2803A som slår LED-ringene (24 V) av og på
fra Pi-ens GPIO-er. ULN2803A har motstand (2,7 kΩ) og transistor (darlington) for hver kanal innebygd, så det trengs
ingen egne motstander eller transistorer. Knappene og volumhjulet går rett gjennom kortet til Pi-en.

Skriptet sjekker koblingene (hvilke hull som henger sammen via stripene, kuttene og lusene) mot nettlista under, at
XH-husene, sokkelen, stiftene og lusene ikke står i veien for hverandre, og tegner kortet fra begge sider:  python3 lag_stripekort.py  → stripekort.svg / stripekort.png
"""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
W, H = 24, 12           # hull (x) × striper (y): 61 × 30 mm – smalt, står på høykant i S1
# Skinner: stripe 0 = GND, 1 = +24 V, 11 = GND (hele lengden). Stripe 2–10 er delt opp med kutt.
# komponenter: navn → {pinne: (x, y)}
ULN = {i + 1: (11, 2 + i) for i in range(9)} | {18 - i: (14, 2 + i) for i in range(9)}
DEL = {
    "J0": {"GND": (1, 0), "+24V": (1, 1)},
    "J4": {"A": (1, 3), "B": (1, 4), "SW": (1, 5), "GND": (1, 6)},
    "J2": {"GND": (6, 11), "BT": (6, 10), "AUX": (6, 9), "RADIO": (6, 8), "USB": (6, 7)},   # snudd: pinne 1 nederst
    "J1": {"+24V": (17, 1), "BT −": (17, 2), "AUX −": (17, 3), "RADIO −": (17, 4), "USB −": (17, 5)},
    "J3": {"LED −": (20, 6), "LED +": (20, 7), "BRYTER": (20, 8), "GND": (20, 9)},
    "U1": ULN,
    "PI": {"LED BT": (9, 2), "LED AUX": (9, 3), "LED RADIO": (9, 4), "LED USB": (9, 5), "LED POWER": (9, 6), "GND": (13, 11),
           "KNAPP BT": (8, 10), "KNAPP AUX": (8, 9), "KNAPP RADIO": (8, 8), "KNAPP USB": (8, 7),
           "HJUL A": (3, 3), "HJUL B": (3, 4), "HJUL SW": (3, 5), "KNAPP POWER": (22, 8)},
}
KUTT = [(4, y) for y in range(3, 7)] + [(9, y) for y in range(7, 11)] + [(12, y) for y in range(2, 11)]
LUS = [((4, 0), (4, 11)), ((3, 6), (3, 11)), ((10, 10), (10, 11)), ((23, 7), (23, 1)), ((23, 9), (23, 11))]
# XH-husene: hvor de står (x, første og siste stripe) – sjekkes mot hverandre, sokkelen og stiftene
XH = {"J0": (1, 0, 1), "J4": (1, 3, 6), "J2": (6, 7, 11), "J1": (17, 1, 5), "J3": (20, 6, 9)}
# GPIO-ene fra Pinne-verktøyet på din S1 (endres i web-UI → Pinner); power-lyset er standard (pinne 5)
GPIO = {"LED BT": 24, "LED AUX": 25, "LED RADIO": 22, "LED USB": 23, "LED POWER": 3, "KNAPP BT": 5, "KNAPP AUX": 2,
        "KNAPP RADIO": 8, "KNAPP USB": 7, "KNAPP POWER": 17, "HJUL A": 9, "HJUL B": 10, "HJUL SW": 11}
FYS = {24: 18, 25: 22, 22: 15, 23: 16, 3: 5, 5: 29, 2: 3, 8: 24, 7: 26, 17: 11, 9: 21, 10: 19, 11: 23}
NETT = {
    "+24V": ["J0.+24V", "J1.+24V", "J3.LED +", "U1.13"],
    "GND": ["J0.GND", "J2.GND", "J4.GND", "J3.GND", "PI.GND", "U1.9", "U1.11"],
    "LED BT −": ["U1.18", "J1.BT −"], "LED AUX −": ["U1.17", "J1.AUX −"], "LED RADIO −": ["U1.16", "J1.RADIO −"],
    "LED USB −": ["U1.15", "J1.USB −"], "LED POWER −": ["U1.14", "J3.LED −"],
    "LED BT": ["PI.LED BT", "U1.1"], "LED AUX": ["PI.LED AUX", "U1.2"], "LED RADIO": ["PI.LED RADIO", "U1.3"],
    "LED USB": ["PI.LED USB", "U1.4"], "LED POWER": ["PI.LED POWER", "U1.5"],
    "KNAPP POWER": ["J3.BRYTER", "PI.KNAPP POWER", "U1.12"],
    "KNAPP BT": ["J2.BT", "PI.KNAPP BT"], "KNAPP AUX": ["J2.AUX", "PI.KNAPP AUX"], "KNAPP RADIO": ["J2.RADIO", "PI.KNAPP RADIO"],
    "KNAPP USB": ["J2.USB", "PI.KNAPP USB"], "HJUL A": ["J4.A", "PI.HJUL A"], "HJUL B": ["J4.B", "PI.HJUL B"], "HJUL SW": ["J4.SW", "PI.HJUL SW"],
    "U1.6": ["U1.6"], "U1.7": ["U1.7"], "U1.8": ["U1.8"], "U1.10 COM": ["U1.10"],
}


def pinner():
    for d, p in DEL.items():
        for n, xy in p.items():
            yield f"{d}.{n}", xy


def sjekk():
    """Union-find over hullene: stripene (delt av kutt) og lusene. Gir liste over feil (tom = alt stemmer)."""
    far = {}
    def finn(a):
        far.setdefault(a, a)
        while far[a] != a:
            far[a] = far[far[a]]; a = far[a]
        return a
    def slå(a, b): far[finn(a)] = finn(b)
    kutt = set(KUTT)
    for y in range(H):
        for x in range(W - 1):
            if (x, y) not in kutt and (x + 1, y) not in kutt:
                slå((x, y), (x + 1, y))
    for a, b in LUS:
        slå(a, b)
    feil, brukt = [], {}
    for p, xy in pinner():
        if xy in brukt:
            feil.append(f"{p} og {brukt[xy]} i samme hull {xy}")
        brukt[xy] = p
        if xy in kutt:
            feil.append(f"{p} står i et kutt {xy}")
    for a, b in LUS:
        for e in (a, b):
            if e in brukt: feil.append(f"lus i hull med {brukt[e]} {e}")
    # XH-hus: 2,45 mm forbi ytterpinnene langs raden og 5,75 mm bredt; sokkelen DIP-18: 25 × 10 mm
    mm = 2.54
    bokser = {d: (x*mm - 2.9, y0*mm - 2.45, x*mm + 2.9, y1*mm + 2.45) for d, (x, y0, y1) in XH.items()}
    bokser["U1"] = (11*mm - 1.3, 2*mm - 2.3, 14*mm + 1.3, 10*mm + 2.3)
    nav = list(bokser)
    for i, a in enumerate(nav):
        for b in nav[i + 1:]:
            A, B = bokser[a], bokser[b]
            if A[0] < B[2] and B[0] < A[2] and A[1] < B[3] and B[1] < A[3]:
                feil.append(f"husene til {a} og {b} kolliderer")
    for p, (x, y) in pinner():
        if p.startswith("PI."):
            for d, A in bokser.items():
                if A[0] < x*mm < A[2] and A[1] < y*mm < A[3]: feil.append(f"stiften {p} står under {d}")
    for a2, b2 in LUS:
        for e in (a2, b2):
            for d, A in bokser.items():
                if A[0] < e[0]*mm < A[2] and A[1] < e[1]*mm < A[3] and d != "U1": feil.append(f"lus-enden {e} står under {d}")
    hvor = dict(pinner())
    nett_av = {p: n for n, l in NETT.items() for p in l}
    for p in hvor:
        if p not in nett_av: feil.append(f"{p} mangler i nettlista")
    for n, l in NETT.items():
        if len({finn(hvor[p]) for p in l}) != 1: feil.append(f"{n} henger ikke sammen")
    navn = list(NETT)
    for i, a in enumerate(navn):
        for b in navn[i + 1:]:
            if finn(hvor[NETT[a][0]]) == finn(hvor[NETT[b][0]]): feil.append(f"kortslutning: {a} og {b}")
    return feil


FARGE = {"+24V": "#d23b2b", "GND": "#222", "J1": "#2f7fd0", "J3": "#8a4fd0", "J2": "#2f9e5a", "J4": "#c98a1e", "PI": "#d06a2f", "U1": "#333"}


def tegn(speil: bool, ox: float, oy: float, P: float, s: list):
    """Kortet sett ovenfra (komponentsiden) eller nedenfra (kobbersiden, speilvendt)."""
    X = (lambda x: ox + (W - 1 - x) * P) if speil else (lambda x: ox + x * P)
    Y = lambda y: oy + y * P
    s.append(f'<rect x="{ox - P*0.7}" y="{oy - P*0.7}" width="{(W - 1 + 1.4)*P}" height="{(H - 1 + 1.4)*P}" rx="6" fill="#e8d3a6" stroke="#b89a62"/>')
    for y in range(H):   # stripene
        s.append(f'<rect x="{min(X(0), X(W-1)) - P*0.42}" y="{Y(y) - P*0.36}" width="{(W - 1)*P + P*0.84}" height="{P*0.72}" rx="3" fill="#d58b4e" opacity="{0.95 if speil else 0.28}"/>')
    for y in range(H):
        for x in range(W):
            s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{P*0.13}" fill="#5a3a1a" opacity="{0.9 if speil else 0.45}"/>')
    for x, y in (KUTT if speil else []):
        s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{P*0.42}" fill="#e8d3a6" stroke="#c0392b" stroke-width="2.4"/>'
                 f'<path d="M{X(x)-P*0.25},{Y(y)-P*0.25} L{X(x)+P*0.25},{Y(y)+P*0.25} M{X(x)+P*0.25},{Y(y)-P*0.25} L{X(x)-P*0.25},{Y(y)+P*0.25}" stroke="#c0392b" stroke-width="2.4"/>')
    if speil:
        for p, (x, y) in pinner():
            s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{P*0.24}" fill="#c9c9c4" stroke="#777"/>')
        return
    for a, b in LUS:   # lus (isolert ledning) på komponentsiden
        s.append(f'<path d="M{X(a[0])},{Y(a[1])} L{X(b[0])},{Y(b[1])}" stroke="#2a6fb8" stroke-width="{P*0.22}" stroke-linecap="round" opacity=".85"/>')
    # ULN2803A (hakket mot stripe 2 = pinne 1)
    s.append(f'<rect x="{X(11) - P*0.45}" y="{Y(2) - P*0.6}" width="{3*P + P*0.9}" height="{8*P + P*1.2}" rx="4" fill="#2b2b2d"/>'
             f'<path d="M{X(12.5) - P*0.4},{Y(2) - P*0.6} a{P*0.4},{P*0.4} 0 0 0 {P*0.8},0" fill="#e8d3a6"/>'
             f'<text x="{X(12.5)}" y="{Y(6)}" fill="#f2f2ee" font-size="{P*0.55}" font-weight="700" text-anchor="middle" transform="rotate(90 {X(12.5)} {Y(6)})">ULN2803A</text>')
    TITTEL = {"J0": ("J0 24 V inn", "v"), "J4": ("J4 volumhjul", "v"), "J2": ("J2 knapper", "n"), "J1": ("J1 LED-ringer", "h"), "J3": ("J3 av/på-knapp", "h")}
    for d, (x0, y0, y1) in XH.items():
        f = FARGE.get(d, "#444"); tekst, side = TITTEL[d]
        s.append(f'<rect x="{X(x0) - P*0.62}" y="{Y(y0) - P*0.55}" width="{P*1.25}" height="{(y1 - y0)*P + P*1.1}" rx="3" fill="#ffffff55" stroke="{f}" stroke-width="2.5"/>')
        ym = Y((y0 + y1)/2)
        if side == "v":
            tx = X(0) - P*1.0
            s.append(f'<text x="{tx}" y="{ym + 5}" fill="{f}" font-size="{P*0.46}" font-weight="700" text-anchor="end">{tekst}</text>'
                     f'<path d="M{tx + P*0.2},{ym} L{X(x0) - P*0.7},{ym}" stroke="{f}" stroke-width="1.2" stroke-dasharray="3 3"/>')
        elif side == "h":
            tx = X(W - 1) + P*1.0
            s.append(f'<text x="{tx}" y="{ym + 5}" fill="{f}" font-size="{P*0.46}" font-weight="700">{tekst}</text>'
                     f'<path d="M{tx - P*0.2},{ym} L{X(x0) + P*0.7},{ym}" stroke="{f}" stroke-width="1.2" stroke-dasharray="3 3"/>')
        else:
            s.append(f'<text x="{X(x0)}" y="{Y(H - 1) + P*1.6}" fill="{f}" font-size="{P*0.46}" font-weight="700" text-anchor="middle">{tekst}</text>')
    for p, (x, y) in pinner():
        d, n = p.split(".", 1)
        if d == "U1":
            s.append(f'<rect x="{X(x) - P*0.2}" y="{Y(y) - P*0.2}" width="{P*0.4}" height="{P*0.4}" fill="#bbb"/>')
            s.append(f'<text x="{X(x) + (-P*0.55 if x == 8 else P*0.55)}" y="{Y(y) + 3}" font-size="{P*0.3}" fill="#f2f2ee" text-anchor="middle">{n}</text>' if False else "")
            continue
        f = FARGE.get(d, "#444")
        if d == "PI":
            nr = list(DEL["PI"]).index(n) + 1
            s.append(f'<rect x="{X(x) - P*0.36}" y="{Y(y) - P*0.36}" width="{P*0.72}" height="{P*0.72}" rx="3" fill="{f}"/>'
                     f'<text x="{X(x)}" y="{Y(y) + P*0.16}" font-size="{P*0.42}" font-weight="700" fill="#fff" text-anchor="middle">{nr}</text>')
        else:
            s.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="{P*0.3}" fill="#fff" stroke="{f}" stroke-width="2.6"/>'
                     f'<text x="{X(x)}" y="{Y(y) + P*0.14}" font-size="{P*0.34}" font-weight="700" fill="{f}" text-anchor="middle">{list(DEL[d]).index(n) + 1}</text>')


def svg():
    P = 34
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1760 1060" width="1760" height="1060" font-family="Sora, Arial, sans-serif">',
         '<rect width="100%" height="100%" fill="#f7f6f2"/>',
         '<text x="40" y="54" font-size="30" font-weight="700" fill="#1d1d1f">Skjold S1 rev F: koblingskort for knapper, LED-ringer og volumhjul</text>',
         '<text x="40" y="86" font-size="16" fill="#55554f">Stripekort 2,54 mm, 24 × 12 hull (61 × 30 mm) skåret av 6,5 × 14,5 cm-kortet, stripene på langs. Står på høykant i S1. ULN2803A slår 24 V-ringene av og på – motstand og transistor er innebygd.</text>']
    s.append('<text x="40" y="140" font-size="20" font-weight="700" fill="#1d1d1f">Komponentsiden (ovenfra) – tallene i ringene er pinnenummeret i kontakten</text>')
    tegn(False, 240, 190, P, s)
    yk = 190 + (H - 1) * P + 110
    s.append(f'<text x="40" y="{yk}" font-size="20" font-weight="700" fill="#1d1d1f">Kobbersiden (kortet snudd som en side i en bok: venstre ↔ høyre) – kutt ×</text>')
    tegn(True, 240, yk + 40, P * 0.62, s)
    y = 140
    rader = [("✕ Kutt (17)", "3,5 mm bor, vridd for hånd: én rad under ULN2803A", "#c0392b"),
             ("", "(mellom pinneradene), og to rader ved J4 og J2.", "#55554f"),
             ("— Lus (5)", "Isolert ledning på oversiden, loddet bare i endene:", "#2a6fb8"),
             ("", "GND-skinnene, +24 V og GND til J3, GND til J4.", "#55554f"),
             ("Skinner", "Stripe 1 = GND, 2 = +24 V, nederste = GND.", "#33332f"),
             ("■ Til Pi-en", "Stiftlist (1 stift per hull), nummerert – se tabellen.", "#d06a2f"),
             ("ULN2803A", "Hakket mot +24 V-skinnen. Sokkel DIP-18.", "#333"),
             ("Ubrukt", "Kanal 6–8 står åpne. COM alene – aldri til GND!", "#55554f")]
    for i, (a, b) in enumerate(((r[0], r[1]) for r in rader)):
        f = rader[i][2]
        s.append(f'<text x="1180" y="{y + 40 + i*30}" font-size="16" font-weight="700" fill="{f}">{a}</text><text x="1300" y="{y + 40 + i*30}" font-size="15" fill="#33332f">{b}</text>')
    y += 40 + len(rader) * 30 + 30
    s.append(f'<text x="1180" y="{y}" font-size="18" font-weight="700" fill="#1d1d1f">Kontaktene (JST XH 2,54 mm)</text>')
    kont = [("J0 24 V inn (2 p)", "GND · +24 V (fra «+24 V etter bryteren»)"), ("J4 volumhjul (4 p)", "A · B · trykk (SW) · GND (C + andre SW)"),
            ("J2 knapper (5 p)", "GND · BT · AUX · RADIO · USB (pinne 1 nederst)"), ("J1 LED-ringer (5 p)", "+24 V · BT − · AUX − · RADIO − · USB −"),
            ("J3 av/på-knapp (4 p)", "LED − · LED + · bryter · GND")]
    for i, (a, b) in enumerate(kont):
        s.append(f'<text x="1180" y="{y + 30 + i*28}" font-size="15" font-weight="700" fill="#33332f">{a}</text><text x="1360" y="{y + 30 + i*28}" font-size="14" fill="#33332f">{b}</text>')
    y2 = y + 30 + len(kont) * 28 + 40
    s.append(f'<text x="1180" y="{y2}" font-size="18" font-weight="700" fill="#1d1d1f">Stiftene til Pi-en (■) – se pi_kabler.png</text>')
    for i, n in enumerate(DEL["PI"]):
        g = GPIO.get(n); kol, rad = divmod(i, 7)
        tx, ty = 1180 + kol * 290, y2 + 32 + rad * 27
        s.append(f'<rect x="{tx}" y="{ty - 16}" width="21" height="21" rx="3" fill="#d06a2f"/><text x="{tx + 10.5}" y="{ty}" font-size="13" font-weight="700" fill="#fff" text-anchor="middle">{i + 1}</text>'
                 f'<text x="{tx + 29}" y="{ty}" font-size="13.5" fill="#33332f"><tspan font-weight="700">{n}</tspan> · ' + (f"pinne {FYS[g]}" if g is not None else "GND") + '</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    f = sjekk()
    if f:
        print("FEIL:\n  " + "\n  ".join(f)); sys.exit(1)
    print(f"Koblingene stemmer: {len(NETT)} nett, {len(KUTT)} kutt, {len(LUS)} lus")
    ut = os.path.join(HER, "stripekort")
    open(ut + ".svg", "w").write(svg())
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if os.path.exists("/opt/pw-browsers/chromium") else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1760, "height": 1060})
        pg.goto("file://" + ut + ".svg"); pg.screenshot(path=ut + ".png"); b.close()
    print(ut + ".png")
