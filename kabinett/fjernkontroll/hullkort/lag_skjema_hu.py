"""Koblingsskjema for hullkort-utgaven (skjema.pdf, 2 sider), tegnet med schemdraw fra hullkort.py.

Side 1: XIAO ESP32S3, MCP23017-modulen, tastene, batteriet, batterimålingen og dokken.
Side 2: skjermadapterne (FPC 18 p og 6 p → 2,54 mm), baklyset og IR-kortet i nesen.
Samme nettnavn = samme ledning. Ledningsfargene står i hullkort/koblinger.csv og på tegningen.

Bruk:  python3 hullkort/lag_skjema_hu.py      (krever schemdraw og cairosvg; pdfunite fra poppler)"""
import os
import subprocess
import sys

import schemdraw
import schemdraw.elements as elm

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import hullkort as hk  # noqa: E402

schemdraw.use("svg")
FONT = "DejaVu Sans"


def tag(d, punkt, nett, retning="right", lengde=1.0):
    linje = getattr(elm.Line().at(punkt), retning)(lengde)
    d.add(linje)
    if nett == "GND" and retning in ("up", "down"):
        d.add(elm.Ground().at(linje.end))
    elif not nett:
        d.add(elm.Label().at(linje.end).label("NC", fontsize=8, color="gray"))
    elif retning in ("up", "down"):
        d.add(elm.Label().at(linje.end).label(nett, fontsize=9, valign="bottom" if retning == "up" else "top"))
    else:
        tekst = nett + (f" ({hk.farge(nett)[0]})" if nett in hk.FARGE or nett.startswith("K_") else "")
        d.add(elm.Tag(width=max(1.1, 0.16 * len(tekst) + 0.4)).at(linje.end).theta(180 if retning == "left" else 0).label(tekst, fontsize=8))


def boks(d, x, y, tittel, venstre, hoyre, bredde=4.0, ps=0.7):
    """Modul som boks; venstre/høyre = [(pinnenavn, nett)] ovenfra og ned."""
    pins = [elm.IcPin(name=n, side="left", anchorname=f"v{i}") for i, (n, _) in enumerate(venstre)][::-1] + \
           [elm.IcPin(name=n, side="right", anchorname=f"h{i}") for i, (n, _) in enumerate(hoyre)][::-1]
    b = elm.Ic(pins=pins, size=(bredde, ps * max(len(venstre), len(hoyre)) + 0.6), pinspacing=ps, plblsize=9).at((x, y)).theta(0) \
        .label(tittel, loc="top", fontsize=10)
    d.add(b)
    for i, (_, nett) in enumerate(venstre):
        tag(d, getattr(b, f"v{i}"), nett, "left", 1.0)
    for i, (_, nett) in enumerate(hoyre):
        tag(d, getattr(b, f"h{i}"), nett, "right", 1.0)
    return b


def to_pol(d, ref, verdi, a, b, x, y, el=elm.Resistor, hvor=""):
    vdd = elm.Line().at((x, y)).up(0.4)
    d.add(vdd)
    e = el().at((x, y)).down(2.0)
    d.add(e)
    d.add(elm.Label().at((x + 0.45, y - 1.0)).label(f"{ref}\n{verdi}", fontsize=8, halign="left"))
    if hvor:
        d.add(elm.Label().at((x - 0.3, y - 2.9)).label(hvor, fontsize=7, halign="left", color="#555"))
    tag(d, vdd.end, a, "up", 0.3)
    tag(d, e.end, b, "down", 0.4)


def side1():
    d = schemdraw.Drawing(show=False, fontsize=10, font=FONT)
    d.add(elm.Label().at((0, 2.5)).label("Skjold Fjernkontroll – hullkort-utgaven, side 1: XIAO, MCP23017-modulen, tastene, batteri og dokk",
                                         fontsize=14, halign="left"))
    xv = [(f"{p} GPIO{hk.GPIO[p]}", hk.XIAO[p]) for p in ("D0", "D1", "D2", "D3", "D4", "D5", "D6")]
    xh = [("5V", "VBUS"), ("GND", "GND"), ("3V3", "3V3")] + [(f"{p} GPIO{hk.GPIO[p]}", hk.XIAO[p]) for p in ("D10", "D9", "D8", "D7")]
    boks(d, 3, -7, "U1 Seeed XIAO ESP32S3\n(BAT+ / BAT− på baksiden)", xv, xh, 6.5)
    bat = boks(d, 3, -14.5, "BAT-putene (baksiden)", [], [("BAT+", "VBAT"), ("BAT−", "GND")], 3.2)
    mv = [("VCC", "3V3"), ("GND", "GND"), ("SDA", "SDA"), ("SCL", "SCL"), ("INTA", "INT"), ("INTB", ""), ("RESET", ""), ("A0–A2", "GND")]
    mh = [(hk.mcp_pinne(p), hk.MCP.get(hk.mcp_pinne(p), "")) for p in range(16)]
    boks(d, 3, -30, "U2 MCP23017-modul (CJMCU-2317)\n10 kΩ pull-up på SDA/SCL/RESET, A0–A2 nede = 0x20", mv, mh, 7.5, 0.62)
    d.add(elm.Label().at((0.5, -31.6)).label("Pinnene er merket på modulen (rekkefølgen varierer mellom selgere): koble etter navn. "
                                              "RESET og A0–A2 har motstander på modulen.", fontsize=8, halign="left", color="#555"))
    # tastene
    d.add(elm.Label().at((25, -1.5)).label("Tastene (6 × 6 × 4,3 mm, på hullkortet): hver mellom sin MCP-pinne og GND (interne pull-ups)",
                                          fontsize=10, halign="left"))
    for i, b in enumerate(hk.BRYTERE):
        x, y = 26 + (i % 5) * 3.6, -4.5 - (i // 5) * 5.0
        sw = elm.Switch().at((x, y)).down(1.4)
        d.add(sw)
        d.add(elm.Label().at((x + 0.35, y - 0.7)).label(f"{b[0]}\n{hk.mcp_pinne(b[3])}", fontsize=7, halign="left"))
        tag(d, sw.start, "K_" + b[0].upper(), "up", 0.4)
        tag(d, sw.end, "GND", "down", 0.3)
    # batterimåling, INT-pull-up og dokken
    d.add(elm.Label().at((25, -17.5)).label("Småkomponenter (loddes fritt på pinnene, krympestrømpe over):", fontsize=10, halign="left"))
    for i, (ref, verdi, a, b, hvor, _) in enumerate([s for s in hk.SMADELER if s[0] in ("R3", "R9", "R10", "C3", "R11", "R12")]):
        to_pol(d, ref, verdi, a, b, 26 + i * 3.6, -19.5, elm.Capacitor if ref.startswith("C") else elm.Resistor, hvor)
    x0, y0 = 26, -27.5
    d.add(elm.Label().at((x0, y0 + 1.2)).label("Dokken: pogo-kontakten (hunndelen) i bunnen", fontsize=10, halign="left"))
    p = elm.Dot(open=True).at((x0 + 1, y0 - 1)).label("Pogo +", loc="left", fontsize=9)
    d.add(p)
    l1 = elm.Line().at(p.center).right(1.0)
    d.add(l1)
    d1 = elm.Schottky().at(l1.end).right(2.4)
    d.add(d1)
    d.add(elm.Label().at((l1.end[0] + 1.2, l1.end[1] + 0.7)).label("D1 1N5819 (ved XIAO-en)", fontsize=8))
    tag(d, d1.end, "VBUS", "right", 0.6)
    tag(d, l1.end, "POGO", "down", 0.5)
    q = elm.Dot(open=True).at((x0 + 13, y0 - 1)).label("Pogo −", loc="left", fontsize=9)
    d.add(q)
    tag(d, q.center, "GND", "down", 0.6)
    d.add(elm.Label().at((x0, y0 - 4.5)).label("Batteri: LiPo 603450 1200 mAh, JST-PH 2,0 → BAT+ (rød) / BAT− (svart) på XIAO-en. "
                                                "XIAO-en lader det (ca. 100 mA).", fontsize=8, halign="left"))
    return d


def side2():
    d = schemdraw.Drawing(show=False, fontsize=10, font=FONT)
    d.add(elm.Label().at((0, 2.5)).label("Side 2: skjermadapterne, baklyset og IR-kortet i nesen", fontsize=14, halign="left"))
    a1 = [(f"{p} {hk.A1_FUNK[str(p)]}", hk.A1.get(str(p), "")) for p in range(1, 19)]
    boks(d, 3, -14, "A1 FPC 18 p 0,5 mm → 2,54 mm (skjermen HP28030)\nANTATT pinnerekkefølge – sjekk mot selgerens tegning", [], a1, 5.5, 0.7)
    a2 = [(f"{p} {hk.A2_FUNK[str(p)]}", hk.A2.get(str(p), "")) for p in range(1, 7)]
    boks(d, 20, -6, "A2 FPC 6 p → 2,54 mm (berøring, I²C 0x38)\nANTATT – sjekk", [], a2, 5.5, 0.7)
    # baklys
    x, y = 20, -11
    d.add(elm.Label().at((x, y)).label("Baklys (på A1, loddet fritt):", fontsize=10, halign="left"))
    q2 = elm.NFet().at((x + 6, y - 3.5)).anchor("gate").theta(0)
    d.add(q2)
    d.add(elm.Label().at((x + 7.2, y - 3.5)).label("Q2 AO3400A\n(SOT-23-adapter)", fontsize=8, halign="left"))
    tag(d, q2.drain, "LED_K", "up", 0.6)
    ls = elm.Line().at(q2.source).down(0.6)
    d.add(ls)
    d.add(elm.Ground().at(ls.end))
    lg = elm.Line().at(q2.gate).left(2.8)
    d.add(lg)
    d.add(elm.Dot().at(lg.end))
    r6 = elm.Resistor().at(lg.end).left(2.2)
    d.add(r6)
    d.add(elm.Label().at((lg.end[0] - 1.1, lg.end[1] + 0.7)).label("R6 100 Ω", fontsize=8))
    tag(d, r6.end, "LCD_BL", "left", 0.5)
    r7 = elm.Resistor().at(lg.end).down(2.0)
    d.add(r7)
    d.add(elm.Label().at((lg.end[0] - 0.4, lg.end[1] - 1.0)).label("R7\n100 kΩ", fontsize=8, halign="right"))
    d.add(elm.Ground().at(r7.end))
    for i, (ref, verdi, a, b, hvor, _) in enumerate([s for s in hk.SMADELER if s[0] in ("R8", "R16")]):
        to_pol(d, ref, verdi, a, b, x + 13 + i * 4.0, y - 2.0, elm.Resistor, hvor)
    # IR-kortet
    x, y = 20, -20
    d.add(elm.Label().at((x, y)).label("IR-kortet i nesen (hullkortstripe 34 × 6 mm, står i sporet bak IR-vinduet):", fontsize=10, halign="left"))
    tag(d, (x + 1.5, y - 2), "VBAT", "left", 0.5)
    r15 = elm.Resistor().at((x + 1.5, y - 2)).right(2.0)
    d.add(r15)
    d.add(elm.Label().at((x + 2.5, y - 1.3)).label("R15 6,8 Ω", fontsize=8))
    l1 = elm.LED().at(r15.end).right(2.0)
    d.add(l1)
    l2 = elm.LED().at(l1.end).right(2.0)
    d.add(l2)
    d.add(elm.Label().at((r15.end[0] + 2.0, y - 1.0)).label("LED1, LED2 940 nm", fontsize=8))
    lk = elm.Line().at(l2.end).right(0.8)
    d.add(lk)
    lk = elm.Line().at(lk.end).down(1.6)
    d.add(lk)
    q3 = elm.NFet().at(lk.end).anchor("drain").theta(0)
    d.add(q3)
    d.add(elm.Label().at((lk.end[0] + 1.3, lk.end[1] - 1.2)).label("Q3 AO3400A\n(SOT-23-adapter)", fontsize=8, halign="left"))
    ls = elm.Line().at(q3.source).down(0.5)
    d.add(ls)
    d.add(elm.Ground().at(ls.end))
    lg = elm.Line().at(q3.gate).left(2.6)
    d.add(lg)
    d.add(elm.Dot().at(lg.end))
    r13 = elm.Resistor().at(lg.end).left(2.2)
    d.add(r13)
    d.add(elm.Label().at((lg.end[0] - 1.1, lg.end[1] + 0.7)).label("R13 100 Ω", fontsize=8))
    tag(d, r13.end, "IR_TX", "left", 0.5)
    r14 = elm.Resistor().at(lg.end).down(1.8)
    d.add(r14)
    d.add(elm.Label().at((lg.end[0] - 0.4, lg.end[1] - 0.9)).label("R14\n100 kΩ", fontsize=8, halign="right"))
    d.add(elm.Ground().at(r14.end))
    c4 = elm.Capacitor(polar=True).at((x + 1.5, y - 2)).down(1.3)
    d.add(c4)
    d.add(elm.Label().at((x + 0.9, y - 2.7)).label("C4 100 µF", fontsize=8, halign="right"))
    d.add(elm.Ground().at(c4.end))
    vs = boks(d, x + 2, y - 11.5, "U3 VS1838B", [], [("OUT", "IR_RX"), ("GND", "GND"), ("VCC", "IR_STROM")], 2.4, 0.8)
    d.add(elm.Label().at((x + 7.5, y - 13.4)).label("IR_STROM = MCP GPB6 (høy = på): mottakeren har strøm bare når ESP-en er våken",
                                                    fontsize=8, halign="left", color="#555"))
    return d


def main():
    import cairosvg
    sider = []
    for i, f in enumerate((side1, side2), 1):
        svg = os.path.join(HER, f".skjema-{i}.svg")
        open(svg, "wb").write(f().get_imagedata("svg"))
        pdf = os.path.join(HER, f".skjema-{i}.pdf")
        cairosvg.svg2pdf(url=svg, write_to=pdf)
        cairosvg.svg2png(url=svg, write_to=os.path.join(HER, f"skjema-side{i}.png"), output_width=2000, background_color="white")
        sider.append(pdf)
        os.remove(svg)
    subprocess.run(["pdfunite"] + sider + [os.path.join(HER, "skjema.pdf")], check=True)
    for p in sider:
        os.remove(p)
    print("skrev hullkort/skjema.pdf (2 sider) og skjema-side1/2.png")


if __name__ == "__main__":
    main()
