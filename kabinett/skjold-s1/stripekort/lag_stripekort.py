"""Skjold S1 rev F: koblingskortet for knappene, LED-ringene og volumhjulet på et stripekort (stripene vannrett).

Kortet samler ledningene fra frontpanelet i JST XH-kontakter og har en ULN2803A som slår LED-ringene (24 V) av og på
fra Pi-ens GPIO-er. ULN2803A har motstand (2,7 kΩ) og transistor (darlington) for hver kanal innebygd, så det trengs
ingen egne motstander eller transistorer. Knappene og volumhjulet går rett gjennom kortet til Pi-en.

Skriptet sjekker koblingene (hvilke hull som henger sammen via stripene, kuttene og lusene) mot nettlista under, og
tegner kortet fra begge sider:  python3 lag_stripekort.py  → stripekort.svg / stripekort.png
"""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
W, H = 21, 21           # hull (x) × striper (y): 53 × 53 mm, skjæres av det store kortet
# komponenter: navn → {pinne: (x, y)}
ULN = {i + 1: (8, 3 + i) for i in range(9)} | {18 - i: (11, 3 + i) for i in range(9)}
DEL = {
    "J0": {"GND": (1, 1), "+24V": (1, 2)},
    "J1": {"+24V": (15, 2), "BT −": (15, 3), "AUX −": (15, 4), "RADIO −": (15, 5), "USB −": (15, 6)},
    "J3": {"LED −": (15, 7), "LED +": (15, 8), "BRYTER": (15, 9), "GND": (15, 10)},
    "J2": {"GND": (1, 11), "BT": (1, 12), "AUX": (1, 13), "RADIO": (1, 14), "USB": (1, 15)},
    "J4": {"A": (1, 16), "B": (1, 17), "SW": (1, 18), "GND": (1, 19)},
    "U1": ULN,
    "PI": {"LED BT": (4, 3), "LED AUX": (4, 4), "LED RADIO": (4, 5), "LED USB": (4, 6), "LED POWER": (4, 7), "GND": (4, 11),
           "KNAPP BT": (4, 12), "KNAPP AUX": (4, 13), "KNAPP RADIO": (4, 14), "KNAPP USB": (4, 15),
           "HJUL A": (4, 16), "HJUL B": (4, 17), "HJUL SW": (4, 18), "KNAPP POWER": (18, 9)},
}
KUTT = [(10, y) for y in range(3, 12)] + [(12, 11)]        # under ULN2803A, og COM (pinne 10) isolert
LUS = [((17, 2), (17, 8)), ((2, 1), (2, 11)), ((3, 11), (3, 19)), ((6, 11), (17, 10))]   # isolerte ledningsbiter
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
    # ULN2803A
    s.append(f'<rect x="{X(8) - P*0.45}" y="{Y(3) - P*0.6}" width="{3*P + P*0.9}" height="{8*P + P*1.2}" rx="4" fill="#2b2b2d"/>'
             f'<path d="M{X(9.5) - P*0.4},{Y(3) - P*0.6} a{P*0.4},{P*0.4} 0 0 0 {P*0.8},0" fill="#e8d3a6"/>'
             f'<text x="{X(9.5)}" y="{Y(7)}" fill="#f2f2ee" font-size="{P*0.55}" font-weight="700" text-anchor="middle" transform="rotate(90 {X(9.5)} {Y(7)})">ULN2803A</text>')
    for d, (x0, y0, y1, tekst) in {"J0": (1, 1, 2, "J0 24 V inn"), "J1": (15, 2, 6, "J1 LED-ringer"), "J3": (15, 7, 10, "J3 av/på-knapp"),
                                   "J2": (1, 11, 15, "J2 knapper"), "J4": (1, 16, 19, "J4 volumhjul")}.items():
        f = FARGE.get(d, "#444")
        s.append(f'<rect x="{X(x0) - P*0.55}" y="{Y(y0) - P*0.5}" width="{P*1.25}" height="{(y1 - y0)*P + P}" rx="3" fill="none" stroke="{f}" stroke-width="2.5"/>')
        tx = X(W - 1) + P*1.0 if d in ("J1", "J3") else X(0) - P*1.0
        s.append(f'<text x="{tx}" y="{Y((y0 + y1)/2) + 5}" fill="{f}" font-size="{P*0.5}" font-weight="700" text-anchor="{"start" if d in ("J1", "J3") else "end"}">{tekst}</text>')
        s.append(f'<path d="M{tx + (-P*0.2 if d in ("J1", "J3") else P*0.2)},{Y((y0 + y1)/2)} L{X(x0) + (P*0.75 if d in ("J1", "J3") else -P*0.6)},{Y((y0 + y1)/2)}" stroke="{f}" stroke-width="1.2" stroke-dasharray="3 3"/>')
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
    P = 30
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1760 1110" width="1760" height="1110" font-family="Sora, Arial, sans-serif">',
         '<rect width="100%" height="100%" fill="#f7f6f2"/>',
         '<text x="40" y="54" font-size="30" font-weight="700" fill="#1d1d1f">Skjold S1 rev F: koblingskort for knapper, LED-ringer og volumhjul</text>',
         '<text x="40" y="86" font-size="16" fill="#55554f">Stripekort 2,54 mm, 21 × 21 hull (ca. 53 × 53 mm) skåret av 6,5 × 14,5 cm-kortet. Stripene går vannrett. ULN2803A slår 24 V-ringene av og på – motstand og transistor er innebygd.</text>']
    s.append('<text x="40" y="140" font-size="20" font-weight="700" fill="#1d1d1f">Komponentsiden (ovenfra) – tallene i ringene er pinnenummeret i kontakten</text>')
    tegn(False, 260, 175, P, s)
    s.append('<text x="1120" y="140" font-size="20" font-weight="700" fill="#1d1d1f">Kobbersiden (kortet snudd) – kutt ×</text>')
    tegn(True, 1140, 175, P * 0.6, s)
    y = 175 + 20 * P * 0.6 + 60
    rader = [("✕ Kutt (10)", "3,5 mm bor, vridd for hånd: én rad under ULN2803A", "#c0392b"),
             ("", "(mellom pinneradene) og ett ved COM (pinne 10).", "#55554f"),
             ("— Lus (4)", "Isolert ledning på oversiden: +24 V til av/på-ringen,", "#2a6fb8"),
             ("", "GND til J0, J4 og J3. Loddes bare i endene.", "#55554f"),
             ("■ Til Pi-en", "Stiftlist (1 stift per hull), nummerert – se tabellen.", "#d06a2f"),
             ("ULN2803A", "Hakket opp, pinne 1 øverst til venstre. Sokkel DIP-18.", "#333"),
             ("Ubrukt", "Kanal 6–8 står åpne. COM alene – aldri til GND!", "#55554f")]
    for i, (a, b, f) in enumerate(rader):
        s.append(f'<text x="1120" y="{y + i*30}" font-size="16" font-weight="700" fill="{f}">{a}</text><text x="1240" y="{y + i*30}" font-size="15" fill="#33332f">{b}</text>')
    y += len(rader) * 30 + 30
    s.append(f'<text x="1120" y="{y}" font-size="18" font-weight="700" fill="#1d1d1f">Kontaktene (JST XH 2,54 mm, sett ovenfra, pinne 1 øverst)</text>')
    kont = [("J0 24 V inn (2 p)", "GND · +24 V (fra «+24 V etter bryteren»)"), ("J1 LED-ringer (5 p)", "+24 V · BT − · AUX − · RADIO − · USB −"),
            ("J3 av/på-knapp (4 p)", "LED − · LED + · bryter · GND"), ("J2 knapper (5 p)", "GND · BT · AUX · RADIO · USB"),
            ("J4 volumhjul (4 p)", "A · B · trykk (SW) · GND (C og den andre SW-pinnen)")]
    for i, (a, b) in enumerate(kont):
        s.append(f'<text x="1120" y="{y + 30 + i*28}" font-size="15" font-weight="700" fill="#33332f">{a}</text><text x="1310" y="{y + 30 + i*28}" font-size="15" fill="#33332f">{b}</text>')
    y2 = 175 + 20 * P + 70
    s.append(f'<text x="40" y="{y2}" font-size="18" font-weight="700" fill="#1d1d1f">Stiftene til Pi-en (■): Dupont-ledning hun–hun til GPIO-pinnene</text>')
    for i, n in enumerate(DEL["PI"]):
        g = GPIO.get(n); kol, rad = divmod(i, 7)
        tx, ty = 40 + kol * 470, y2 + 34 + rad * 28
        s.append(f'<rect x="{tx}" y="{ty - 17}" width="22" height="22" rx="3" fill="#d06a2f"/><text x="{tx + 11}" y="{ty}" font-size="14" font-weight="700" fill="#fff" text-anchor="middle">{i + 1}</text>'
                 f'<text x="{tx + 32}" y="{ty}" font-size="15" fill="#33332f"><tspan font-weight="700">{n[0] + n[1:].lower() if n.startswith(('KNAPP', 'HJUL')) else n}</tspan> → ' + (f"GPIO{g} (fysisk pinne {FYS[g]})" if g is not None else "GND (fysisk pinne 6, 9, 14 …)") + '</text>')
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
        pg = b.new_page(viewport={"width": 1760, "height": 1110})
        pg.goto("file://" + ut + ".svg"); pg.screenshot(path=ut + ".png"); b.close()
    print(ut + ".png")
