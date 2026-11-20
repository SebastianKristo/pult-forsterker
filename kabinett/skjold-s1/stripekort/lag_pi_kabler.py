"""Skjold S1 rev F: Dupont-ledningene fra koblingskortet (stripekort.png) til Raspberry Pi-ens 40-pinners list.
Henter stiftene og GPIO-ene fra lag_stripekort.py.   python3 lag_pi_kabler.py → pi_kabler.svg / pi_kabler.png"""
import os

import lag_stripekort as K

HER = os.path.dirname(os.path.abspath(__file__))
# andre ting på listen i S1 rev F (pi/S1F.md), så du ser hva som er opptatt
ANDRE = {1: "3,3 V → PCM5102 VIN", 12: "PCM5102 BCK", 35: "PCM5102 LRCK", 40: "PCM5102 DIN", 39: "PCM5102 GND/SCK",
         13: "Relé IN (GPIO27)", 8: "USB-switch (GPIO14)", 10: "Hodetelefon-detekt (GPIO15)", 2: "5 V", 4: "5 V", 17: "3,3 V"}
GND_P = {6, 9, 14, 20, 25, 30, 34, 39}
BCM = {3: 2, 5: 3, 7: 4, 8: 14, 10: 15, 11: 17, 12: 18, 13: 27, 15: 22, 16: 23, 18: 24, 19: 10, 21: 9, 22: 25, 23: 11, 24: 8,
       26: 7, 27: 0, 28: 1, 29: 5, 31: 6, 32: 12, 33: 13, 35: 19, 36: 16, 37: 26, 38: 20, 40: 21}
FARGE = {"LED": "#2f7fd0", "KNAPP": "#2f9e5a", "HJUL": "#c98a1e", "GND": "#222"}


def svg():
    s = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1500 1060" width="1500" height="1060" font-family="Sora, Arial, sans-serif">',
         '<rect width="100%" height="100%" fill="#f7f6f2"/>',
         '<text x="40" y="54" font-size="30" font-weight="700" fill="#1d1d1f">Skjold S1 rev F: ledningene fra koblingskortet til Pi-en</text>',
         '<text x="40" y="86" font-size="16" fill="#55554f">14 Dupont-ledninger hun–hun (20 cm). Stift 1–14 på kortet → pinnene på Pi-ens 40-pinners list. Pinne 1 er hjørnet nærmest SD-kortet (firkantet loddeøye under).</text>']
    pins = list(K.DEL["PI"])
    # kortets stifter til venstre
    sx, sy, dy = 150, 150, 54
    s.append(f'<rect x="{sx - 110}" y="{sy - 40}" width="250" height="{len(pins)*dy + 30}" rx="14" fill="#e8d3a6" stroke="#b89a62"/>'
             f'<text x="{sx + 15}" y="{sy - 14}" font-size="16" font-weight="700" fill="#5a3a1a" text-anchor="middle">Koblingskortet</text>')
    mål = {}
    for i, n in enumerate(pins):
        g = K.GPIO.get(n); fys = K.FYS[g] if g is not None else 6
        mål[n] = fys
    # Pi-listen til høyre: to kolonner (odde til venstre, partall til høyre)
    px, py, pd = 860, 160, 40
    s.append(f'<rect x="{px - 50}" y="{py - 48}" width="640" height="{20*pd + 50}" rx="16" fill="#1f6b3a"/>'
             f'<text x="{px - 30}" y="{py - 18}" font-size="16" font-weight="700" fill="#e9f5ec">Raspberry Pi 4 – GPIO-listen (sett ovenfra, pinne 1 øverst)</text>')
    pos = {}
    def navn(p):
        hvem = [n for n, v in mål.items() if v == p]
        if hvem: return hvem[0] + (f" (GPIO{BCM[p]})" if p in BCM else ""), True
        return ("GND" if p in GND_P else ANDRE.get(p) or (f"GPIO{BCM[p]}" if p in BCM else "")), False
    for p in range(1, 41):
        r, c = (p - 1) // 2, (p - 1) % 2
        x, y = px + c * 46, py + r * pd
        pos[p] = (x, y)
        brukt = p in mål.values()
        f = "#f2c230" if brukt else "#cfd6d1" if p in ANDRE or p in GND_P else "#8fa597"
        s.append(f'<rect x="{x - 14}" y="{y - 14}" width="28" height="28" rx="{2 if p == 1 else 14}" fill="{f}" stroke="#0e3a1f" stroke-width="2"/>'
                 f'<text x="{x}" y="{y + 5}" font-size="12" font-weight="700" fill="#1d1d1f" text-anchor="middle">{p}</text>')
        if c == 1:   # én tekstlinje per rad: venstre pinne · høyre pinne
            (ta, ba), (tb, bb) = navn(p - 1), navn(p)
            s.append(f'<text x="{x + 30}" y="{y + 5}" font-size="12.5"><tspan fill="{"#fff" if ba else "#b7d3bf"}" font-weight="{700 if ba else 400}">{p - 1}: {ta}</tspan>'
                     f'<tspan x="{x + 290}" fill="{"#fff" if bb else "#b7d3bf"}" font-weight="{700 if bb else 400}">{p}: {tb}</tspan></text>')
    for i, n in enumerate(pins):
        y = sy + i * dy + 10
        grp = n.split(" ")[0]
        f = FARGE.get(grp, "#222")
        s.append(f'<rect x="{sx - 12}" y="{y - 12}" width="24" height="24" rx="3" fill="#d06a2f"/><text x="{sx}" y="{y + 5}" font-size="13" font-weight="700" fill="#fff" text-anchor="middle">{i + 1}</text>'
                 f'<text x="{sx - 22}" y="{y + 5}" font-size="13" font-weight="700" fill="{f}" text-anchor="end">{n}</text>')
        p = mål[n]; x2, y2 = pos[p]
        ende = x2 - 14 if p % 2 == 1 else x2 + 14
        via = px - 200 + (i % 7) * 12
        if p % 2 == 1:
            d = f"M{sx + 12},{y} C{sx + 200},{y} {via},{y} {via},{(y + y2)/2} S{x2 - 150},{y2} {ende},{y2}"
        else:
            d = f"M{sx + 12},{y} C{sx + 200},{y} {via},{y} {via},{(y + y2)/2} S{x2 - 150},{y2 - 18} {x2},{y2 - 16}"
        s.append(f'<path d="{d}" fill="none" stroke="{f}" stroke-width="3.2" opacity=".85" stroke-linecap="round"/>')
        if p % 2 == 0:
            s.append(f'<circle cx="{x2}" cy="{y2 - 16}" r="4" fill="{f}"/>')
    s.append('<text x="40" y="1008" font-size="15" fill="#33332f"><tspan font-weight="700">Gult</tspan> = ledninger fra koblingskortet. <tspan font-weight="700">Lys grå</tspan> = brukt av noe annet i S1 (lydkort, relé, USB-switch, hodetelefon, strøm). GND: hvilken som helst GND-pinne.</text>')
    s.append('<text x="40" y="1034" font-size="15" fill="#33332f">GPIO-ene er de Pinne-verktøyet fant på din S1. Flytter du en ledning, endre pinnen i web-UI → Pinner, så følger Skjold etter.</text>')
    s.append("</svg>")
    return "\n".join(s)


if __name__ == "__main__":
    ut = os.path.join(HER, "pi_kabler")
    open(ut + ".svg", "w").write(svg())
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if os.path.exists("/opt/pw-browsers/chromium") else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1500, "height": 1060})
        pg.goto("file://" + ut + ".svg"); pg.screenshot(path=ut + ".png"); b.close()
    print(ut + ".png")
