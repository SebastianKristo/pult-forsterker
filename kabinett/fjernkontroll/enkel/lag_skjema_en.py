"""Koblingsskjema for Skjold Fjernkontroll Enkel (skjema.pdf), tegnet med schemdraw fra nettlista i kretser_en.py.

Tre sider: 1) XIAO ESP32S3, MCP23017 og tastene, 2) strøm, batteri, skjerm og berøring, 3) IR og dokken.
Hver ledning som går mellom delene har et nettnavn i en etikett; samme navn = samme ledning (som i et KiCad-skjema).
Skjemaet tegnes fra kretser_en.py, så det kan ikke komme ut av takt med kortet.

Bruk:  python3 enkel/lag_skjema_en.py      (krever schemdraw og cairosvg; pdfunite fra poppler)"""
import os
import subprocess
import sys

import schemdraw
import schemdraw.elements as elm

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import kretser_en  # noqa: E402

K = {r: (fp, v, p) for r, fp, v, side, x, n, rot, p in kretser_en.KOMP}
schemdraw.use("svg")
FONT = "DejaVu Sans"
STROM = {"3V3": "3V3", "3V3_SW": "3V3_SW", "VBAT": "VBAT", "VBUS": "VBUS"}


def etikett(d, punkt, nett, retning, lengde=1.0, symbol=True):
    """En kort ledning fra pinnen og nettnavnet (jord-/forsyningssymbol på de små delene, etikett på brikkene)."""
    linje = getattr(elm.Line().at(punkt), retning)(lengde)
    d.add(linje)
    if nett == "GND" and symbol:
        d.add(elm.Ground().at(linje.end))
    elif nett in STROM and symbol:
        d.add(elm.Vdd().at(linje.end).label(nett, fontsize=10))
    elif nett and retning in ("up", "down"):
        d.add(elm.Label().at(linje.end).label(nett, fontsize=9, valign="bottom" if retning == "up" else "top"))
    elif nett:
        d.add(elm.Tag(width=max(1.1, 0.17 * len(nett) + 0.4)).at(linje.end).theta(180 if retning == "left" else 0).label(nett, fontsize=9))
    else:
        d.add(elm.Label().at(linje.end).label("NC", fontsize=8, color="gray"))


def ic(d, ref, pinner_v, pinner_h, x, y, tittel, bredde=4.5):
    """Brikke/modul som boks; pinner_v/h = [(pinne, navn)] på venstre/høyre side."""
    nett = K[ref][2]
    pins = [elm.IcPin(name=n, pin=p, side="left", anchorname="p" + p) for p, n in reversed(pinner_v)] + \
           [elm.IcPin(name=n, pin=p, side="right", anchorname="p" + p) for p, n in reversed(pinner_h)]
    boks = elm.Ic(pins=pins, size=(bredde, 0.6 * max(len(pinner_v), len(pinner_h)) + 0.8), pinspacing=0.6,
                  edgepadH=0.4, plblsize=9, lblsize=11).at((x, y)).label(f"{ref}\n{tittel}", loc="top", fontsize=11)
    d.add(boks)
    for p, n in pinner_v:
        etikett(d, getattr(boks, "p" + p), nett.get(p, ""), "left", 1.2, False)
    for p, n in pinner_h:
        etikett(d, getattr(boks, "p" + p), nett.get(p, ""), "right", 1.2, False)
    return boks


def to_pol(d, ref, x, y, vertikal=True, symbol=None):
    """Motstand/kondensator/diode mellom pinne 1 og 2, med nettnavn i begge ender."""
    fp, verdi, p = K[ref]
    el = (symbol or (elm.Capacitor if ref.startswith("C") else elm.Resistor))()
    el = el.at((x, y))
    el = el.down(1.6) if vertikal else el.right(1.6)
    el = el.label(f"{ref}\n{verdi}", fontsize=9, loc="bottom" if not vertikal else "top")
    d.add(el)
    etikett(d, el.start, p.get("1", ""), "up" if vertikal else "left", 0.6)
    etikett(d, el.end, p.get("2", ""), "down" if vertikal else "right", 0.6)


def tittel(d, tekst, x=0, y=1.5):
    d.add(elm.Label().at((x, y)).label(tekst, fontsize=15, halign="left"))


def side1():
    d = schemdraw.Drawing(show=False, fontsize=10, font=FONT)
    tittel(d, "Skjold Fjernkontroll Enkel – side 1: XIAO ESP32S3, MCP23017 og tastene", 0, 2)
    navn = {"1": "D0 GPIO1/A0", "2": "D1 GPIO2", "3": "D2 GPIO3", "4": "D3 GPIO4", "5": "D4 GPIO5/SDA", "6": "D5 GPIO6/SCL",
            "7": "D6 GPIO43/TX", "8": "D7 GPIO44/RX", "9": "D8 GPIO7/SCK", "10": "D9 GPIO8", "11": "D10 GPIO9/MOSI",
            "12": "3V3", "13": "GND", "14": "5V"}
    ic(d, "U1", [(str(i), navn[str(i)]) for i in range(1, 8)], [(str(i), navn[str(i)]) for i in (14, 13, 12, 11, 10, 9, 8)], 3, -5,
       "Seeed XIAO ESP32S3 (BAT+/BAT− på baksiden → batteriet)", 7)
    mn = {str(21 + i): f"GPA{i}" for i in range(8)}
    mn.update({str(1 + i): f"GPB{i}" for i in range(8)})
    mn.update({"9": "VDD", "10": "VSS", "12": "SCK", "13": "SDA", "15": "A0", "16": "A1", "17": "A2", "18": "RESET", "20": "INTA"})
    venstre = [(p, mn[p]) for p in ("9", "10", "12", "13", "15", "16", "17", "18", "20")]
    hoyre = [(p, mn[p]) for p in [str(21 + i) for i in range(8)] + [str(1 + i) for i in range(8)]]
    ic(d, "U2", venstre, hoyre, 3, -17, "MCP23017-E/SO (0x20)", 5)
    # pull-ups og avkobling
    for i, ref in enumerate(("R1", "R2", "R3", "R4", "C1")):
        to_pol(d, ref, 17 + i * 3.0, -4)
    # tastene
    d.add(elm.Label().at((16.5, -10.5)).label("Tastene (oppsett A), hver mellom sin MCP-pinne og GND:", fontsize=11, halign="left"))
    for i, (f, x, n, p) in enumerate(kretser_en.TASTER):
        rx, ry = 17 + (i % 5) * 3.4, -13 - (i // 5) * 5.2
        sw = elm.Switch().at((rx, ry)).down(1.4).label(f"SW{p + 1}\n{f}", fontsize=8, loc="top", ofst=0.1)
        d.add(sw)
        etikett(d, sw.start, f"K_{f.upper()}", "up", 0.5)
        etikett(d, sw.end, "GND", "down", 0.3)
    return d


def vdd(d, punkt, nett):
    d.add(elm.Vdd().at(punkt).label(nett, fontsize=10))


def jord(d, punkt):
    d.add(elm.Ground().at(punkt))


def merk(d, punkt, nett, retning="right", lengde=0.6):
    """Ledning ut til en nettetikett (samme navn = samme ledning på de andre sidene)."""
    etikett(d, punkt, nett, retning, lengde, False)


def del_(d, ref, el, retning, lengde, side="right"):
    """Tegner en topol og skriver «ref verdi» ved siden av (høyre/venstre for loddrette, over/under for vannrette)."""
    fp, verdi, p = K[ref]
    e = getattr(el, retning)(lengde)
    d.add(e)
    (x1, y1), (x2, y2) = e.start, e.end
    cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
    tekst = f"{ref}\n{verdi}"
    if retning in ("up", "down"):
        if side == "left":
            d.add(elm.Label().at((cx - 0.45, cy)).label(tekst, fontsize=9, halign="right"))
        else:
            d.add(elm.Label().at((cx + 0.45, cy)).label(tekst, fontsize=9, halign="left"))
    else:
        d.add(elm.Label().at((cx, cy + (-0.7 if side == "bottom" else 0.7))).label(f"{ref} {verdi}", fontsize=9, halign="center"))
    return e


def seksjon(d, x, y, tekst):
    d.add(elm.Label().at((x, y)).label(tekst, fontsize=11, halign="left", color="#333"))


def side2():
    d = schemdraw.Drawing(show=False, fontsize=10, font=FONT)
    tittel(d, "Side 2: batteri og batterimåling, skjermstrøm, baklys, skjerm og berøring", 0, 2)
    # --- batteri og spenningsdeler ---
    seksjon(d, 0, 0, "Batteri (J1) og batterimåling")
    j1 = elm.Ic(pins=[elm.IcPin(name="2 −", pin="", side="right", anchorname="p2"), elm.IcPin(name="1 +", pin="", side="right", anchorname="p1")],
                size=(2.2, 1.8), pinspacing=0.8, plblsize=9).at((0, -3.2)).theta(0).label("J1\nJST-PH 2p\nbatteri", loc="left", fontsize=9)
    d.add(j1)
    l = elm.Line().at(j1.p2).right(1.2); d.add(l); l = elm.Line().at(l.end).down(0.6); d.add(l); jord(d, l.end)
    l = elm.Line().at(j1.p1).right(1.2); d.add(l); vdd(d, l.end, "VBAT")
    d.add(elm.Label().at((0.2, -5.2)).label("TP1 BAT+ / TP2 BAT− → XIAO BAT-puter", fontsize=8, halign="left", color="gray"))
    vdd(d, (6, -1.4), "VBAT")
    r9 = del_(d, "R9", elm.Resistor().at((6, -1.4)), "down", 2.2)
    d.add(elm.Dot().at(r9.end))
    r10 = del_(d, "R10", elm.Resistor().at(r9.end), "down", 2.2, "left")
    jord(d, r10.end)
    l = elm.Line().at(r9.end).right(2.4); d.add(l); d.add(elm.Dot().at(l.end))
    c3 = del_(d, "C3", elm.Capacitor().at(l.end), "down", 2.2)
    jord(d, c3.end)
    merk(d, l.end, "VBAT_ADC (D0)", "right", 1.6)
    vdd(d, (19.5, -1.4), "3V3")
    r16 = del_(d, "R16", elm.Resistor().at((19.5, -1.4)), "down", 2.2)
    merk(d, r16.end, "LCD_RES", "down", 0.6)
    d.add(elm.Label().at((17.2, -5.4)).label("holder berøringens RST høy i dyp søvn", fontsize=8, halign="left", color="gray"))
    # --- skjermstrøm Q1 ---
    seksjon(d, 0, -8.5, "Skjermstrøm: Q1 kobler 3V3 → 3V3_SW (SKJ lav = på)")
    q1 = elm.PFet().at((5, -12.5)).theta(0).anchor("gate").label("Q1\nAO3401A", fontsize=9, loc="right", ofst=(0.3, 0))
    d.add(q1)
    vdd(d, q1.source, "3V3")
    l = elm.Line().at(q1.drain).down(0.8); d.add(l); d.add(elm.Dot().at(l.end))
    merk(d, l.end, "3V3_SW", "right", 2.6)
    c2 = del_(d, "C2", elm.Capacitor().at(l.end), "down", 1.8, "left")
    jord(d, c2.end)
    l = elm.Line().at(q1.gate).left(2.4); d.add(l); d.add(elm.Dot().at(l.end))
    merk(d, l.end, "SKJ (MCP GPB6)", "left", 0.6)
    r5 = del_(d, "R5", elm.Resistor().at(l.end), "up", 1.8)
    vdd(d, r5.end, "3V3")
    # --- baklys Q2 ---
    seksjon(d, 0, -18.5, "Baklys: Q2 trekker LED_K til GND (PWM fra D9)")
    q2 = elm.NFet().at((7, -22)).theta(0).anchor("gate").label("Q2\nAO3400A", fontsize=9, loc="right", ofst=(0.3, 0))
    d.add(q2)
    merk(d, q2.drain, "LED_K", "up", 0.6)
    l = elm.Line().at(q2.source).down(0.6); d.add(l); jord(d, l.end)
    l = elm.Line().at(q2.gate).left(2.8); d.add(l); d.add(elm.Dot().at(l.end))
    r6 = del_(d, "R6", elm.Resistor().at(l.end), "left", 2.2, "top")
    merk(d, r6.end, "LCD_BL (D9)", "left", 0.6)
    r7 = del_(d, "R7", elm.Resistor().at(l.end), "down", 2.0, "left")
    jord(d, r7.end)
    vdd(d, (13, -20.5), "3V3_SW")
    r8 = del_(d, "R8", elm.Resistor().at((13, -20.5)), "down", 2.2)
    merk(d, r8.end, "LED_A", "down", 0.6)
    # --- skjerm J2 ---
    funk = {"1": "GND", "2": "RESET", "3": "SCL/SCK", "4": "D/C", "5": "CS", "6": "SDA/MOSI", "7": "SDO (ikke brukt)", "8": "GND",
            "9": "VDD", "10": "VDD", "11": "LED-A", "12": "LED-K1", "13": "LED-K2", "14": "LED-K3", "15": "LED-K4", "16": "GND",
            "17": "NC", "18": "GND"}
    nett = K["J2"][2]
    pins = [elm.IcPin(name=f"{funk[str(i)]}", pin=str(i), side="right", anchorname=f"p{i}") for i in range(18, 0, -1)]
    j2 = elm.Ic(pins=pins, size=(3.6, 0.7 * 18 + 0.6), pinspacing=0.7, plblsize=9, lblsize=10).at((20, -22)).theta(0).label(
        "J2  FPC 18p 0,5 mm\nskjerm HP28030\n(ANTATT pinnerekkefølge – sjekk\nmot databladet før bestilling)", loc="top", fontsize=9)
    d.add(j2)
    for i in range(1, 19):
        n = nett.get(str(i), "")
        etikett(d, getattr(j2, f"p{i}"), n, "right", 1.0, False)
    # --- berøring J3 ---
    nett = K["J3"][2]
    funk = {"1": "VDD", "2": "GND", "3": "SDA", "4": "SCL", "5": "INT (ikke brukt)", "6": "RST"}
    pins = [elm.IcPin(name=funk[str(i)], pin=str(i), side="right", anchorname=f"p{i}") for i in range(6, 0, -1)]
    j3 = elm.Ic(pins=pins, size=(3.6, 0.7 * 6 + 0.6), pinspacing=0.7, plblsize=9).at((31, -15)).theta(0).label(
        "J3  FPC 6p 0,5 mm\nberøring (I²C 0x38)\nANTATT – sjekk", loc="top", fontsize=9)
    d.add(j3)
    for i in range(1, 7):
        etikett(d, getattr(j3, f"p{i}"), nett.get(str(i), ""), "right", 1.0, False)
    d.add(elm.Label().at((31, -16.2)).label("J2 MP / J3 MP (festeører) → GND", fontsize=8, halign="left", color="gray"))
    return d


def side3():
    d = schemdraw.Drawing(show=False, fontsize=10, font=FONT)
    tittel(d, "Side 3: IR-sender og -mottaker (kortet i nesen) og dokken", 0, 2)
    # --- IR-driver på hovedkortet ---
    seksjon(d, 0, 0, "IR-driver på kortet: Q3 slår av/på 38 kHz fra D6, strømmen går rett fra batteriet")
    vdd(d, (2.5, -1.6), "VBAT")
    l = elm.Line().at((2.5, -1.6)).down(0.8); d.add(l); d.add(elm.Dot().at(l.end))
    c4 = del_(d, "C4", elm.Capacitor(polar=True).at(l.end), "down", 2.0, "left")
    jord(d, c4.end)
    l2 = elm.Line().at(l.end).right(2.5); d.add(l2)
    r15 = del_(d, "R15", elm.Resistor().at(l2.end), "down", 2.2)
    merk(d, r15.end, "IR_A", "right", 1.2)
    q3 = elm.NFet().at((12.5, -6.5)).theta(0).anchor("gate").label("Q3\nAO3400A", fontsize=9, loc="right", ofst=(0.3, 0))
    d.add(q3)
    merk(d, q3.drain, "IR_K", "up", 0.6)
    l = elm.Line().at(q3.source).down(0.6); d.add(l); jord(d, l.end)
    l = elm.Line().at(q3.gate).left(2.8); d.add(l); d.add(elm.Dot().at(l.end))
    r13 = del_(d, "R13", elm.Resistor().at(l.end), "left", 2.2, "top")
    merk(d, r13.end, "IR_TX (D6)", "left", 0.6)
    r14 = del_(d, "R14", elm.Resistor().at(l.end), "down", 2.0, "left")
    jord(d, r14.end)
    # --- J4 ---
    nett = K["J4"][2]
    pins = [elm.IcPin(name=f"{i}", pin="", side="right", anchorname=f"p{i}") for i in range(5, 0, -1)]
    j4 = elm.Ic(pins=pins, size=(1.6, 0.8 * 5 + 0.4), pinspacing=0.8, plblsize=9).at((20, -7)).theta(0).label(
        "J4 JST-SH 5p\n→ IR-kortet", loc="top", fontsize=9)
    d.add(j4)
    for i in range(1, 6):
        etikett(d, getattr(j4, f"p{i}"), nett.get(str(i), ""), "right", 1.0, False)
    # --- IR-kortet ---
    seksjon(d, 0, -12, "IR-kortet i nesen (hullkort, kobles med 5-leder JST-SH-kabel)")
    merk(d, (1.5, -14), "IR_A", "left", 0.5)
    l1 = elm.LED().at((1.5, -14)).right(2.4).label("LED1 940 nm", fontsize=8, loc="top")
    d.add(l1)
    l2 = elm.LED().at(l1.end).right(2.4).label("LED2 940 nm", fontsize=8, loc="top")
    d.add(l2)
    merk(d, l2.end, "IR_K", "right", 0.6)
    d.add(elm.Label().at((0.2, -15.4)).label("i serie: ~2,6 V over to dioder, ~0,2 A topp via R15 6,8 Ω", fontsize=8, halign="left", color="gray"))
    vs = elm.Ic(pins=[elm.IcPin(name="OUT", pin="1", side="right", anchorname="o"), elm.IcPin(name="GND", pin="2", side="right", anchorname="g"),
                      elm.IcPin(name="VCC", pin="3", side="right", anchorname="v")], size=(2.0, 2.6), pinspacing=0.8, plblsize=9
                 ).at((12, -17.4)).theta(0).label("U3 VS1838B\n38 kHz mottaker", loc="top", fontsize=9)
    d.add(vs)
    etikett(d, vs.o, "IR_RX (D7)", "right", 1.0, False)
    etikett(d, vs.g, "GND", "right", 1.0, False)
    etikett(d, vs.v, "3V3_SW", "right", 1.0, False)
    # --- dokken ---
    seksjon(d, 0, -20.5, "Dokken: pogo-puter på baksiden; 5 V via Schottky til XIAO 5V-puten (den lader batteriet)")
    t3 = elm.Dot(open=True).at((1.5, -23)).label("TP3 POGO+", fontsize=9, loc="left")
    d.add(t3)
    l = elm.Line().at(t3.center).right(1.2); d.add(l); d.add(elm.Dot().at(l.end))
    d1 = del_(d, "D1", elm.Schottky().at(l.end), "right", 2.4, "top")
    merk(d, d1.end, "VBUS (XIAO 5V)", "right", 0.6)
    r11 = del_(d, "R11", elm.Resistor().at(l.end), "down", 2.0, "left")
    d.add(elm.Dot().at(r11.end))
    merk(d, r11.end, "DOKK (MCP GPB7)", "right", 2.6)
    r12 = del_(d, "R12", elm.Resistor().at(r11.end), "down", 2.0, "left")
    jord(d, r12.end)
    t4 = elm.Dot(open=True).at((15, -23)).label("TP4 POGO−", fontsize=9, loc="left")
    d.add(t4)
    l = elm.Line().at(t4.center).down(0.6); d.add(l); jord(d, l.end)
    return d


def main():
    sider = []
    for i, f in enumerate((side1, side2, side3), 1):
        d = f()
        svg = os.path.join(HER, f".skjema-{i}.svg")
        open(svg, "wb").write(d.get_imagedata("svg"))
        pdf = os.path.join(HER, f".skjema-{i}.pdf")
        import cairosvg
        cairosvg.svg2pdf(url=svg, write_to=pdf)
        if i == 1:
            cairosvg.svg2png(url=svg, write_to=os.path.join(HER, "skjema-side1.png"), output_width=1800, background_color="white")
        sider.append(pdf)
        os.remove(svg)
    subprocess.run(["pdfunite"] + sider + [os.path.join(HER, "skjema.pdf")], check=True)
    for p in sider:
        os.remove(p)
    print("skrev enkel/skjema.pdf (3 sider) og skjema-side1.png")


if __name__ == "__main__":
    main()
