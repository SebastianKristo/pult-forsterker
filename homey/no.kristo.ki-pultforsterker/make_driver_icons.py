"""Skjold-driverikoner (Homey): enkel strektegning, 960×960, svart strek, gjennomsiktig bakgrunn."""
# Kjør: python3 make_driver_icons.py drivers
import sys, os
OUT = sys.argv[1]
SW = 22
HEAD = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 960" fill="none" stroke="#000" stroke-width="%d" stroke-linecap="round" stroke-linejoin="round">\n' % SW
f = lambda v: ("%.1f" % v).rstrip("0").rstrip(".")

def rect(x, y, w, h, r=0, sw=None):
    a = f' stroke-width="{f(sw)}"' if sw else ''
    return f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}" rx="{f(r)}"{a}/>\n'
def circ(cx, cy, r, sw=None, fill=False):
    a = (f' stroke-width="{f(sw)}"' if sw else '') + (' fill="#000" stroke="none"' if fill else '')
    return f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(r)}"{a}/>\n'
def line(x1, y1, x2, y2, sw=None):
    a = f' stroke-width="{f(sw)}"' if sw else ''
    return f'<path d="M{f(x1)} {f(y1)}L{f(x2)} {f(y2)}"{a}/>\n'

def s1():
    # Front 190 × 48 mm: rund POWER-knapp til venstre, skjermvindu i midten, 2×2 knapper og stor volumknott til høyre
    s = 880 / 190; X = lambda x: 480 + x * s; Y = lambda y: 480 + y * s
    g = rect(X(-95), Y(-24), 190 * s, 48 * s, 5 * s)
    # strømknapp + symbol
    g += circ(X(-78), Y(0), 12 * s)
    r = 6.6 * s; cx, cy = X(-78), Y(0)
    g += f'<path d="M{f(cx - r * .64)} {f(cy - r * .77)}A{f(r)} {f(r)} 0 1 0 {f(cx + r * .64)} {f(cy - r * .77)}" stroke-width="16"/>\n' + line(cx, cy - r - 4, cx, cy - 4, 16)
    # skjermvindu med to tekstlinjer (antydning av «spiller nå»)
    g += rect(X(-60), Y(-17), 66 * s, 34 * s, 2 * s)
    g += line(X(-52), Y(-5), X(-22), Y(-5), 16) + line(X(-52), Y(5), X(-34), Y(5), 16)
    # 2×2 knapper
    for bx in (20, 37):
        for by in (-8.5, 8.5):
            g += circ(X(bx), Y(by), 6 * s, 18)
    # volumknott med markering
    g += circ(X(70), Y(0), 18 * s)
    g += line(X(70) + 0, Y(-14), X(70) + 0, Y(-8), 22)
    return g

def node():
    # Lokket sett ovenfra (91 × 74 mm) + forsiden (34 mm, forkortet) under: OLED-stripe, 4 runde knapper og potmeterknott
    s = 8.4; W, D, H = 91 * s, 74 * s, 34 * s * 0.42
    x0 = 480 - W / 2; y0 = 480 - (D + H) / 2
    X = lambda x: 480 + x * s; Y = lambda y: y0 + D / 2 + y * s
    g = rect(x0, y0, W, D + H, 5 * s)
    g += line(x0, y0 + D, x0 + W, y0 + D)   # kant mellom lokk og forside
    # liten OLED-stripe øverst til venstre
    g += rect(X(-36), Y(-24), 40 * s, 11 * s, 1.5 * s)
    g += line(X(-31), Y(-18.5), X(-14), Y(-18.5), 14)
    # potmeterknott øverst til høyre
    g += circ(X(25), Y(-14), 12.5 * s)
    g += line(X(25), Y(-23), X(25), Y(-17.5), 20)
    # 4 knapper på rad foran
    for bx in (-30, -10, 10, 30):
        g += circ(X(bx), Y(17), 7 * s, 20)
    return g

def core():
    # Raspberry Pi 4-kort (85 × 56 mm) uten logo: 40-pinners header, SoC, USB/Ethernet til høyre, USB-C/HDMI/lyd foran
    s = 9.4; W, D = 85 * s, 56 * s
    x0 = 480 - (W + 3 * s) / 2; y0 = 480 - (D + 3 * s) / 2
    X = lambda x: x0 + x * s; Y = lambda y: y0 + y * s
    g = rect(X(0), Y(0), W, D, 3 * s)
    for hx in (3.5, 61.5):
        for hy in (3.5, 52.5):
            g += circ(X(hx), Y(hy), 1.6 * s, 12)
    # 40-pinners header (2 × 20)
    g += rect(X(7.6), Y(1), 50.8, 5.1 * s, 0, 16).replace(f'width="{f(50.8)}"', f'width="{f(50.8 * s)}"')
    for i in range(20):
        for j in range(2):
            g += circ(X(8.9 + i * 2.54), Y(2.27 + j * 2.54), 0.62 * s, fill=True)
    # SoC og RAM
    g += rect(X(22), Y(25), 15 * s, 15 * s, 1 * s, 18)
    g += rect(X(41), Y(28), 10 * s, 12 * s, 1 * s, 16)
    # USB ×2 og Ethernet stikker ut på høyre side
    g += rect(X(69), Y(2.5), 18.5 * s, 13.5 * s, 1 * s, 18) + rect(X(69), Y(20.5), 18.5 * s, 13.5 * s, 1 * s, 18)
    g += rect(X(66), Y(38.5), 21.5 * s, 16 * s, 1 * s, 18)
    for yy in (9.25, 27.25):
        g += line(X(72.5), Y(yy), X(84.5), Y(yy), 12)
    g += rect(X(72), Y(43), 9 * s, 7 * s, 0.6 * s, 12)
    # USB-C, 2 × micro-HDMI og lydjack langs forkanten
    g += rect(X(7.2), Y(49.5), 9 * s, 8 * s, 1.5 * s, 16)
    g += rect(X(22.5), Y(50.5), 7.5 * s, 7 * s, 1 * s, 16) + rect(X(36), Y(50.5), 7.5 * s, 7 * s, 1 * s, 16)
    g += circ(X(54), Y(53.5), 3.4 * s, 16)
    return g

for name, fn in (("s1", s1), ("node", node), ("core", core)):
    svg = HEAD + fn() + '</svg>\n'
    p = os.path.join(OUT, name, "assets", "icon.svg")
    open(p, "w").write(svg)
    print(p, len(svg))
