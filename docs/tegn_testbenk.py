#!/usr/bin/env python3
"""Tegner breadboard-oppsettet for testbenken (KI_AMP_BOARD=test) -> docs/bilder/testbenk_breadboard.svg/.png
Hver ledning ender i en merkelapp «Pi pinne N» i stedet for å trekkes helt til headeren, så bildet er lett å følge."""
import os
import cairosvg

W, H = 1720, 1120
o = []
A = o.append
A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
A(f'<rect width="{W}" height="{H}" fill="#f4f2ec"/>')
A('<text x="30" y="44" font-size="26" font-weight="700" fill="#1b1c20">Pultforsterker – testbenk på breadboard</text>')
A('<text x="30" y="70" font-size="15" fill="#555">Raspberry Pi 4 · KI_AMP_BOARD=test · KI_AMP_POT=rc:24 · koble med strømmen av · pinne 1 = hjørnet nærmest SD-kortet</text>')

RED, BLUE = "#c0392b", "#1f4fa0"
COL = {"AIRPLAY": "#e0a800", "BT": "#2e86de", "AUX": "#27ae60", "USB": "#8e44ad", "POWER": "#e67e22", "SDA": "#16a085", "SCK": "#5d6d7e", "POT": "#d35400"}

# ---------------- Pi-header med funksjon på hver brukt pinne
FN = {1: ("3V3", "→ +skinne", RED), 6: ("GND", "→ –skinne", BLUE), 39: ("GND", "→ –skinne", BLUE), 17: ("3V3", "(reserve)", "#999"),
      3: ("GPIO2 SDA", "OLED SDA", COL["SDA"]), 5: ("GPIO3 SCL", "OLED SCK", COL["SCK"]),
      11: ("GPIO17", "encoder CLK", "#777"), 13: ("GPIO27", "encoder DT", "#777"), 15: ("GPIO22", "encoder SW", "#777"),
      16: ("GPIO23", "LED POWER", COL["POWER"]), 18: ("GPIO24", "POTMETER", COL["POT"]),
      29: ("GPIO5", "knapp AIRPLAY", COL["AIRPLAY"]), 31: ("GPIO6", "knapp BT", COL["BT"]), 33: ("GPIO13", "knapp AUX", COL["AUX"]),
      35: ("GPIO19", "knapp USB", COL["USB"]), 37: ("GPIO26", "knapp POWER", COL["POWER"]),
      36: ("GPIO16", "LED AIRPLAY", COL["AIRPLAY"]), 38: ("GPIO20", "LED BT", COL["BT"]), 40: ("GPIO21", "LED AUX", COL["AUX"]),
      32: ("GPIO12", "LED USB", COL["USB"]), 30: ("GND", "", BLUE), 34: ("GND", "", BLUE), 9: ("GND", "", BLUE), 14: ("GND", "", BLUE),
      20: ("GND", "", BLUE), 25: ("GND", "", BLUE), 2: ("5V", "ikke bruk", RED), 4: ("5V", "ikke bruk", RED)}
HX, HY, P = 300, 150, 36
A(f'<rect x="{HX-22}" y="{HY-24}" width="{P+44}" height="{19*P+48}" rx="8" fill="#1f6b3a"/>')
A(f'<text x="{HX+P/2}" y="{HY-36}" font-size="15" font-weight="700" text-anchor="middle">Pi 4 GPIO-header</text>')
for n in range(1, 41):
    r, c = (n - 1) // 2, (n - 1) % 2
    x, y = HX + c * P, HY + r * P
    name, fn, col = FN.get(n, ("", "", None))
    fill = "#e8e6df" if col is None else ("#222" if name == "GND" else RED if name in ("3V3", "5V") else col)
    A(f'<rect x="{x-11}" y="{y-11}" width="22" height="22" rx="3" fill="{fill}" stroke="#0b3d20"/>')
    A(f'<text x="{x}" y="{y+4}" font-size="10" font-weight="700" text-anchor="middle" fill="{"#333" if col is None else "#fff"}">{n}</text>')
    if name:
        tc = col if col not in (BLUE, RED) else "#333"
        if c == 0:
            A(f'<text x="{x-32}" y="{y-1}" font-size="11.5" text-anchor="end" fill="#333">{name}</text>')
            if fn: A(f'<text x="{x-32}" y="{y+12}" font-size="11" font-weight="700" text-anchor="end" fill="{tc}">{fn}</text>')
        else:
            A(f'<text x="{x+32}" y="{y-1}" font-size="11.5" fill="#333">{name}</text>')
            if fn: A(f'<text x="{x+32}" y="{y+12}" font-size="11" font-weight="700" fill="{tc}">{fn}</text>')

# ---------------- breadboard
BX, BY, BW, BH = 540, 130, 1150, 700
A(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" rx="12" fill="#fff" stroke="#c9c6bd" stroke-width="2"/>')
TOP_P, TOP_G, BOT_G = BY + 28, BY + 56, BY + BH - 30
def rail(y, col, label):
    A(f'<line x1="{BX+20}" y1="{y}" x2="{BX+BW-20}" y2="{y}" stroke="{col}" stroke-width="3"/>')
    for i in range(57):
        A(f'<circle cx="{BX+32+i*19.6}" cy="{y+9}" r="2.3" fill="#bbb"/>')
    A(f'<text x="{BX+BW-24}" y="{y-5}" font-size="12" font-weight="700" text-anchor="end" fill="{col}">{label}</text>')
rail(TOP_P, RED, "+ 3,3 V")
rail(TOP_G, BLUE, "– GND")
rail(BOT_G, BLUE, "– GND")
MID = BY + 430
A(f'<rect x="{BX+20}" y="{MID-7}" width="{BW-40}" height="14" fill="#eceae4"/>')

def wire(pts, col, w=4):
    A(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>')
def dot(x, y, col): A(f'<circle cx="{x}" cy="{y}" r="5" fill="{col}"/>')
def tag(x, y, text, col, anchor="middle"):
    w = 9 + len(text) * 7.2
    x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
    A(f'<rect x="{x0}" y="{y-11}" width="{w}" height="22" rx="11" fill="{col}"/>')
    A(f'<text x="{x0+w/2}" y="{y+4.5}" font-size="12" font-weight="700" text-anchor="middle" fill="#fff">{text}</text>')

# strøm inn på skinnene
wire([(BX+50, TOP_P+9), (BX+50, BY-20)], RED); dot(BX+50, TOP_P+9, RED); tag(BX+50, BY-20, "Pi pinne 1 (3V3)", RED)
wire([(BX+210, TOP_G+9), (BX+210, BY-20)], BLUE); dot(BX+210, TOP_G+9, BLUE); tag(BX+210, BY-20, "Pi pinne 6 (GND)", BLUE)
wire([(BX+50, BOT_G+9), (BX+50, BY+BH+30)], BLUE); dot(BX+50, BOT_G+9, BLUE); tag(BX+50, BY+BH+30, "Pi pinne 39 (GND)", BLUE)

# ---------------- OLED
OX, OY = BX + 40, BY + 110
A(f'<rect x="{OX}" y="{OY}" width="170" height="64" rx="6" fill="#1d3f7a"/><rect x="{OX+12}" y="{OY+10}" width="146" height="30" fill="#000"/>')
A(f'<text x="{OX+85}" y="{OY+30}" font-size="12" fill="#cfe6ff" text-anchor="middle">0,91" OLED 128×32</text>')
labs = [("GND", BLUE), ("VCC", RED), ("SCK", COL["SCK"]), ("SDA", COL["SDA"])]
for i, (lab, col) in enumerate(labs):
    x = OX + 34 + i * 34
    A(f'<rect x="{x-5}" y="{OY+48}" width="10" height="12" fill="#c9a227"/><text x="{x}" y="{OY+76}" font-size="11" font-weight="700" text-anchor="middle">{lab}</text>')
wire([(OX+34, OY+48), (OX+34, TOP_G+9)], BLUE, 3); dot(OX+34, TOP_G+9, BLUE)
wire([(OX+68, OY+48), (OX+68, OY+40), (OX+60, OY+30), (OX+60, TOP_P+9)], RED, 3); dot(OX+60, TOP_P+9, RED)
wire([(OX+102, OY+60), (OX+102, OY+110)], COL["SCK"], 3); tag(OX+102, OY+124, "Pi 5", COL["SCK"])
wire([(OX+136, OY+60), (OX+136, OY+110)], COL["SDA"], 3); tag(OX+148, OY+152, "Pi 3", COL["SDA"])
wire([(OX+136, OY+110), (OX+148, OY+140)], COL["SDA"], 3)

# ---------------- 5 knapper med LED
BTN = [("AIRPLAY", 29, 36), ("BT", 31, 38), ("AUX", 33, 40), ("USB", 35, 32), ("POWER", 37, 16)]
for i, (name, bpin, lpin) in enumerate(BTN):
    cx = BX + 300 + i * 120
    col = COL[name]
    # knapp over midtrennen: øvre ben -> GPIO-merke, nedre ben -> GND
    A(f'<rect x="{cx-20}" y="{MID-20}" width="40" height="40" rx="4" fill="#333"/><circle cx="{cx}" cy="{MID}" r="11" fill="#111" stroke="#888"/>')
    A(f'<text x="{cx}" y="{MID-30}" font-size="14" font-weight="700" text-anchor="middle">{name}</text>')
    wire([(cx-15, MID+16), (cx-15, MID+70)], col, 4); tag(cx-15, MID+84, f"Pi {bpin}", col)
    wire([(cx+15, MID+16), (cx+15, BOT_G+9)], BLUE, 3); dot(cx+15, BOT_G+9, BLUE)
    # LED + 330 Ω
    ly = BY + 260
    A(f'<circle cx="{cx}" cy="{ly}" r="11" fill="{col}" stroke="#333" stroke-width="1.5"/><text x="{cx+16}" y="{ly-8}" font-size="10" fill="#555">+</text>')
    wire([(cx, ly-11), (cx, ly-50)], col, 3); tag(cx, ly-62, f"Pi {lpin}", col)
    wire([(cx, ly+11), (cx, ly+24)], "#666", 2)
    A(f'<rect x="{cx-5}" y="{ly+24}" width="10" height="34" rx="2" fill="#d9c7a1" stroke="#8a7a55"/><text x="{cx+9}" y="{ly+46}" font-size="10" fill="#555">330 Ω</text>')
    wire([(cx, ly+58), (cx, ly+72), (cx+34, ly+72), (cx+34, TOP_G+9)], BLUE, 2); dot(cx+34, TOP_G+9, BLUE)

# ---------------- potmeter (RC) på høyre side
PX, PY = BX + BW - 170, BY + 200
A(f'<text x="{PX}" y="{PY-56}" font-size="15" font-weight="700" text-anchor="middle">Potmeter = volum</text>')
A(f'<rect x="{PX-48}" y="{PY-42}" width="96" height="70" rx="6" fill="#1d4fa0"/><circle cx="{PX}" cy="{PY-8}" r="22" fill="#2c3e50" stroke="#95a5a6" stroke-width="3"/>')
pp = {"GND": PX - 28, "VCC": PX, "OUT": PX + 28}
for lab, x in pp.items():
    A(f'<rect x="{x-4}" y="{PY+28}" width="8" height="12" fill="#c9a227"/><text x="{x}" y="{PY+54}" font-size="11" font-weight="700" text-anchor="middle">{lab}</text>')
A(f'<text x="{PX-28}" y="{PY+68}" font-size="10" text-anchor="middle" fill="{RED}">ikke koblet</text>')
wire([(PX, PY+28), (PX, PY+18), (PX+70, PY+18), (PX+70, TOP_P+9)], RED, 3); dot(PX+70, TOP_P+9, RED)
NODE = (PX + 28, PY + 120)
wire([(PX+28, PY+40), NODE], COL["POT"], 4); dot(*NODE, COL["POT"])
A(f'<text x="{NODE[0]+10}" y="{NODE[1]-6}" font-size="11" fill="#555">felles rad</text>')
# kondensator node -> GND
cx_ = NODE[0] + 60
wire([NODE, (cx_, NODE[1]), (cx_, NODE[1]+40)], COL["POT"], 3)
A(f'<rect x="{cx_-12}" y="{NODE[1]+40}" width="24" height="36" rx="5" fill="#2c3e50"/><text x="{cx_}" y="{NODE[1]+62}" font-size="9" fill="#fff" text-anchor="middle">C</text>')
A(f'<text x="{cx_+16}" y="{NODE[1]+52}" font-size="11" fill="#333">1–10 µF</text><text x="{cx_+16}" y="{NODE[1]+66}" font-size="11" fill="#333">(– til GND)</text>')
wire([(cx_, NODE[1]+76), (cx_, BOT_G+9)], BLUE, 3); dot(cx_, BOT_G+9, BLUE)
# 220 Ω node -> GPIO24
rx = NODE[0] - 60
wire([NODE, (NODE[0]-30, NODE[1])], COL["POT"], 3)
A(f'<rect x="{rx}" y="{NODE[1]-6}" width="30" height="12" rx="2" fill="#d9c7a1" stroke="#8a7a55"/><text x="{rx+15}" y="{NODE[1]-12}" font-size="11" text-anchor="middle">220 Ω</text>')
wire([(rx, NODE[1]), (rx-30, NODE[1]), (rx-30, NODE[1]+110)], COL["POT"], 4); tag(rx-30, NODE[1]+124, "Pi 18 (GPIO24)", COL["POT"])

# ---------------- forklaring under brettet
LX, LY = BX + 200, BY + BH + 100
txt = [
    "Merkelappene «Pi N» = fysisk pinne på headeren til venstre. Bruk hunn–hann-jumpere fra Pi-en til brettet.",
    "Knapp: ett bein til GPIO, det andre til GND (Pi-en har intern pull-up). LED: langt bein til GPIO, kort bein via 330 Ω til GND.",
    "Knapper med innebygd LED-ring: ringens + til LED-pinnen, – til GND (motstanden sitter i knappen).",
    "OLED: VCC på 3,3 V – aldri 5 V. SCK = SCL.",
    "Potmeter: Pi-en har ingen analog inngang, så den måler hvor fort kondensatoren lades. Vri helt rundt én gang etter start (kalibrering).",
    "Encoder (valgfri): CLK pinne 11, DT 13, SW 15, + til 3,3 V, GND til GND.",
]
for i, t in enumerate(txt):
    A(f'<text x="{30}" y="{LY+i*22}" font-size="14" fill="#333">• {t}</text>')
A('</svg>')

here = os.path.dirname(os.path.abspath(__file__))
svg = "\n".join(o)
open(os.path.join(here, "bilder", "testbenk_breadboard.svg"), "w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(here, "bilder", "testbenk_breadboard.png"), output_width=W * 2, output_height=H * 2)
print("ok")
