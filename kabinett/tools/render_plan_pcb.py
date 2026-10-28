#!/usr/bin/env python3
"""2D-plantegning ovenfra av innsiden: hvor hvert kort skal ligge."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

W, D = 200, 195
fig, ax = plt.subplots(figsize=(10, 10))
ax.add_patch(FancyBboxPatch((-W/2, -D/2), W, D, boxstyle="round,pad=0,rounding_size=6", fc="#2c2d30", ec="#111", lw=2))
ax.add_patch(FancyBboxPatch((-W/2+2.7, -D/2+2.7), W-5.4, D-5.4, boxstyle="round,pad=0,rounding_size=3.3", fc="#3a3b3f", ec="#555", lw=1))
for sx in (-1, 1):
    for sy in (-1, 1):
        ax.add_patch(Circle((sx*90, sy*50), 4, fc="#4a4b50", ec="#222")); ax.add_patch(Circle((sx*90, sy*50), 1.7, fc="#c9a227", ec="#555"))

def box(x, y, w, d, name, color, txt="white", tag=None):
    ax.add_patch(Rectangle((x-w/2, y-d/2), w, d, fc=color, ec="#222", lw=1.2, alpha=0.92))
    ax.text(x, y, name, ha="center", va="center", fontsize=9, color=txt, fontweight="bold")
    if tag: ax.text(x-w/2+2, y+d/2-2, tag, ha="left", va="top", fontsize=11, color=txt, fontweight="bold")

box(0, 36.8, 150, 100, "KI hovedkort rev A  (150 × 100)\nforsterker · DAC · PGA2311 · buck · relé · LED-drivere", "#2f6fb5", tag="A")
for x,n in [(-61,"24V"),(-37,"F1"),(-5,"C1"),(33,"SPK L"),(47,"AUX"),(59,"SPK R")]: ax.text(x, 80, n, ha="center", va="center", fontsize=6, color="white")
for x,n in [(-51,"KNAPPER"),(-31,"ENC"),(-13,"5V PI"),(9,"OLED"),(43,"LED")]: ax.text(x, -7, n, ha="center", va="center", fontsize=6, color="white")
ax.text(-68, 36, "Pi 40", rotation=90, ha="center", va="center", fontsize=6, color="white")
box(-28, -45, 85, 56, "Raspberry Pi 4 B\n(porter mot høyre, USB-C/HDMI mot bak)", "#2e8b57", tag="B")
box(-30, -D/2+6, 70, 12, "OLED-kort (bak vinduet)", "#223", tag="H")
box(70, -D/2+13, 26, 26, "Enc.", "#3a7")
ax.annotate("", (-68, 20), (-62, -30), arrowprops=dict(arrowstyle="<->", color="#f0c040", lw=1.5)); ax.text(-80, -5, "40-pin\nflatkabel", fontsize=7, color="#f0c040", ha="center")
# front/bak-elementer
for x, n in [(-80, "PWR"), (20, "AIR"), (37, "BT"), (70, "VOL")]:
    ax.add_patch(Circle((x, -D/2-7), 5, fc="#1d1d20", ec="#777")); ax.text(x, -D/2-7, n, ha="center", va="center", fontsize=6, color="white")
ax.text(-30, -D/2-7, "OLED-vindu", ha="center", va="center", fontsize=8, color="#333")
for x, n in [(86, "KCD1"), (68, "DC"), (44, "RJ45"), (14, "USB-C"), (-6, "AUX"), (-31, "R +/−"), (-66, "L +/−")]:
    ax.text(x, D/2+7, n, ha="center", va="center", fontsize=8, color="#333", bbox=dict(boxstyle="round,pad=0.2", fc="#ddd", ec="#888"))
ax.text(0, -D/2-16, "FRONT", ha="center", fontsize=11, fontweight="bold", color="#555")
ax.text(0, D/2+16, "BAK", ha="center", fontsize=11, fontweight="bold", color="#555")
ax.annotate("", (44, D/2), (16, -45), arrowprops=dict(arrowstyle="->", color="#2e8b57", lw=1.5, ls="--")); ax.annotate("", (14, D/2), (-40, -20), arrowprops=dict(arrowstyle="->", color="#2e8b57", lw=1.2, ls="--"))
ax.set_xlim(-115, 115); ax.set_ylim(-118, 118); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("PCB-variant (kasse 200 × 195): hovedkortet bak på fire M3-stolper, Pi 4 foran. Panelkontakter bak kobles til kortets skruterminaler/JST.", fontsize=9)
fig.savefig("guide_04_inni_pcb.png", dpi=120, bbox_inches="tight"); print("ok")
