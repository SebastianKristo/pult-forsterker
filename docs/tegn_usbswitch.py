#!/usr/bin/env python3
"""Koblingstegning: Pi styrer knappen på Ugreen USB-switch via PC817 -> docs/bilder/usbswitch_knapp.svg/.png"""
import os
import cairosvg

W, H = 1500, 930
o = []
A = o.append
RED, BLUE, YEL, GRN, PUR, GREY = "#c0392b", "#1f4fa0", "#e0a800", "#16a085", "#8e44ad", "#555"
A(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
A(f'<rect width="{W}" height="{H}" fill="#f4f2ec"/>')
A('<text x="30" y="46" font-size="26" font-weight="700" fill="#1b1c20">USB-switch: Pi-en trykker knappen via optokobler (PC817)</text>')
A('<text x="30" y="74" font-size="15" fill="#555">Optokobleren holder Pi-en og switchen elektrisk adskilt. Pi-en gir en puls på 150 ms = ett trykk på knappen.</text>')


def wire(pts, col, w=4):
    A(f'<polyline points="{" ".join(f"{x},{y}" for x, y in pts)}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>')


def dot(x, y, col, r=6):
    A(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{col}"/>')


def label(x, y, t, size=14, col="#1b1c20", weight="400", anchor="start"):
    A(f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{col}" text-anchor="{anchor}">{t}</text>')


# ---------- Pi-header (utsnitt, pinne 17–24)
PX, PY, P = 120, 200, 46
A(f'<rect x="{PX-30}" y="{PY-34}" width="{P+60}" height="{3*P+68}" rx="8" fill="#1f6b3a"/>')
label(PX + P / 2, PY - 46, "Raspberry Pi 4 (utsnitt)", 15, weight="700", anchor="middle")
pins = {17: ("3V3", "#999"), 18: ("GPIO24", "#999"), 19: ("GPIO10", "#999"), 20: ("GND", "#222"),
        21: ("GPIO9", "#999"), 22: ("GPIO25", YEL), 23: ("GPIO11", "#999"), 24: ("GPIO8", "#999")}
pos = {}
for n, (nm, col) in pins.items():
    r, c = (n - 17) // 2, (n - 17) % 2
    x, y = PX + c * P, PY + r * P
    pos[n] = (x, y)
    hl = n in (20, 22)
    A(f'<rect x="{x-12}" y="{y-12}" width="24" height="24" rx="3" fill="{col if hl else "#e8e6df"}" stroke="#0b3d20"/>')
    A(f'<text x="{x}" y="{y+4}" font-size="11" font-weight="700" text-anchor="middle" fill="{"#fff" if hl else "#555"}">{n}</text>')
    if c == 0:
        label(x - 22, y + 5, nm, 12, "#333", "400", "end")
    elif hl:
        label(x + 22, y - 10, nm, 12, "#000", "700")
    else:
        label(x + 22, y + 5, nm, 12, "#333", "400")

# ---------- motstand 330 Ω
RX, RY = 420, 246
wire([pos[22], (pos[22][0] + 110, pos[22][1]), (pos[22][0] + 110, RY), (RX, RY)], YEL)
A(f'<rect x="{RX}" y="{RY-10}" width="70" height="20" rx="4" fill="#d9c7a1" stroke="#8a7a55" stroke-width="1.5"/>')
for i, c in enumerate(("#ff7f00", "#ff7f00", "#8b4513")):   # oransje-oransje-brun = 330
    A(f'<rect x="{RX+14+i*12}" y="{RY-10}" width="6" height="20" fill="{c}"/>')
label(RX + 35, RY - 18, "330 Ω", 14, weight="700", anchor="middle")

# ---------- PC817 (sett ovenfra, prikk = pinne 1)
CX, CY, CW, CH = 600, 200, 130, 130
A(f'<rect x="{CX}" y="{CY}" width="{CW}" height="{CH}" rx="8" fill="#2b2b2b"/>')
A(f'<circle cx="{CX+22}" cy="{CY+22}" r="7" fill="#777"/>')
label(CX + CW / 2, CY + CH / 2 - 4, "PC817", 18, "#fff", "700", "middle")
label(CX + CW / 2, CY + CH / 2 + 18, "sett ovenfra", 11, "#bbb", anchor="middle")
cp = {1: (CX - 18, CY + 30), 2: (CX - 18, CY + CH - 30), 3: (CX + CW + 18, CY + CH - 30), 4: (CX + CW + 18, CY + 30)}
for n, (x, y) in cp.items():
    side = -1 if n <= 2 else 1
    A(f'<rect x="{min(x, x - side*18)}" y="{y-5}" width="18" height="10" fill="#c9c9c9"/>')
names = {1: "1 anode (+)", 2: "2 katode (−)", 3: "3 emitter → bein på 0 V", 4: "4 kollektor → bein med spenning"}
for n, (x, y) in cp.items():
    label(x + (-8 if n <= 2 else 8), y - 12, names[n], 13, "#333", "700", "end" if n <= 2 else "start")
wire([(RX + 70, RY), (cp[1][0] - 20, RY), (cp[1][0] - 20, cp[1][1]), cp[1]], YEL)
# pinne 2 til Pi GND
wire([cp[2], (cp[2][0] - 40, cp[2][1]), (cp[2][0] - 40, 420), (pos[20][0] + 60, 420), (pos[20][0] + 60, pos[20][1]), pos[20]], "#222")
label(CX - 60, 445, "Pi GND (pinne 20)", 13, "#222", "700", "end")
# skillelinje
for y0, y1 in ((CY - 60, CY - 8), (CY + CH + 8, CY + CH + 250)):
    A(f'<line x1="{CX+CW/2}" y1="{y0}" x2="{CX+CW/2}" y2="{y1}" stroke="#999" stroke-width="2" stroke-dasharray="8 6"/>')
label(CX + CW / 2 - 12, CY + CH + 248, "Pi-siden", 13, GREY, anchor="end")
label(CX + CW / 2 + 12, CY + CH + 248, "switch-siden", 13, GREY)

# ---------- Ugreen-knappen (6 × 6, 4 bein) sett fra undersiden av kortet
KX, KY, KS = 1050, 175, 180
A(f'<rect x="{KX-60}" y="{KY-60}" width="{KS+120}" height="{KS+150}" rx="10" fill="#14365e"/>')
label(KX + KS / 2, KY - 72, "Ugreen-kortet, UNDERSIDEN under knappen", 15, weight="700", anchor="middle")
A(f'<rect x="{KX+30}" y="{KY+30}" width="{KS-60}" height="{KS-60}" rx="6" fill="none" stroke="#7fa6d6" stroke-width="2" stroke-dasharray="6 5"/>')
label(KX + KS / 2, KY + KS / 2 + 5, "knappen (på oversiden)", 12, "#cfe0f5", anchor="middle")
legs = {"A1": (KX, KY), "A2": (KX + KS, KY), "B1": (KX, KY + KS), "B2": (KX + KS, KY + KS)}
for k, (x, y) in legs.items():
    A(f'<circle cx="{x}" cy="{y}" r="14" fill="#c0c0c0" stroke="#e8e8e8" stroke-width="3"/>')
    A(f'<circle cx="{x}" cy="{y}" r="5" fill="#8a8a8a"/>')
# interne forbindelser
A(f'<line x1="{KX+14}" y1="{KY}" x2="{KX+KS-14}" y2="{KY}" stroke="#ffb347" stroke-width="3" stroke-dasharray="5 4"/>')
A(f'<line x1="{KX+14}" y1="{KY+KS}" x2="{KX+KS-14}" y2="{KY+KS}" stroke="#7fd6a6" stroke-width="3" stroke-dasharray="5 4"/>')
label(KX + KS / 2, KY - 14, "A1–A2 henger sammen", 12, "#ffb347", anchor="middle")
label(KX + KS / 2, KY + KS + 28, "B1–B2 henger sammen", 12, "#7fd6a6", anchor="middle")
label(KX + KS / 2, KY + KS + 60, "trykk = A kobles til B", 13, "#fff", "700", "middle")
# lodding
dot(*legs["A1"], RED, 7); dot(*legs["B1"], BLUE, 7)
label(KX - 32, KY + 32, "lodd her", 13, "#ff8a7a", "700")
label(KX - 32, KY + KS - 22, "lodd her", 13, "#8ab4ff", "700")
wire([cp[4], (cp[4][0] + 228, cp[4][1]), (cp[4][0] + 228, KY), legs["A1"]], RED)
wire([cp[3], (cp[3][0] + 228, cp[3][1]), (cp[3][0] + 228, KY + KS), legs["B1"]], BLUE)


# ---------- målesteg + liste
BX, BY = 60, 590
A(f'<rect x="{BX-20}" y="{BY-36}" width="{W-80}" height="{H-BY+10}" rx="12" fill="#fff" stroke="#d6d3cb"/>')
label(BX, BY, "Slik gjør du det", 18, weight="700")
steps = [
    "1. Finn de to beina: koble switchen til en PC (lampen lyser). Sett multimeterets svarte probe på skjermen til en USB-port (= GND).",
    "    Mål de fire beina under knappen med rød probe: to av dem viser 0 V (B-paret), to viser ca. 3,3–5 V (A-paret). Bein på samme side henger sammen.",
    "2. Lodd en tynn ledning (26–30 AWG) på ett bein med spenning (rødt) og ett bein med 0 V (blått). Ikke kortslutt mot nabopunktene. Krymp eller tape.",
    "3. PC817 pinne 4 (kollektor) → rødt bein.  PC817 pinne 3 (emitter) → blått bein.  Snus disse, virker det ikke (men ingenting blir ødelagt).",
    "4. Pi pinne 22 (GPIO 25) → 330 Ω → PC817 pinne 1 (prikken).  PC817 pinne 2 → Pi pinne 20 (GND).",
    "5. Test: sett KI_AMP_USBSW_PULSE=25 i /etc/ki-amp.env, sudo systemctl restart ki-amp, og",
    "    curl -X POST localhost:8765/api/usbsw -d '{\"toggle\":true}'   → lampen på switchen skal hoppe til den andre PC-en.",
    "Deler: 1 × PC817 (DIP-4), 1 × 330 Ω, tynn ledning, krympestrømpe. Knappen på switchen virker som før.",
]
for i, t in enumerate(steps):
    label(BX, BY + 34 + i * 30, t.replace("<", "&lt;").replace(">", "&gt;"), 15, "#333" if i < 7 else GREY,
          "700" if t[:2].strip().rstrip(".").isdigit() and False else "400")
A('</svg>')

here = os.path.dirname(os.path.abspath(__file__))
svg = "\n".join(o)
open(os.path.join(here, "bilder", "usbswitch_knapp.svg"), "w").write(svg)
cairosvg.svg2png(bytestring=svg.encode(), write_to=os.path.join(here, "bilder", "usbswitch_knapp.png"), output_width=W * 2, output_height=H * 2)
print("ok")
