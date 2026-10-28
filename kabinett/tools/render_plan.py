#!/usr/bin/env python3
"""2D-plantegning ovenfra av innsiden: hvor hvert kort skal ligge."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

W, D = 200, 120
fig, ax = plt.subplots(figsize=(11, 7))
ax.add_patch(FancyBboxPatch((-W/2, -D/2), W, D, boxstyle="round,pad=0,rounding_size=6", fc="#2c2d30", ec="#111", lw=2))
ax.add_patch(FancyBboxPatch((-W/2+2.7, -D/2+2.7), W-5.4, D-5.4, boxstyle="round,pad=0,rounding_size=3.3", fc="#3a3b3f", ec="#555", lw=1))
for sx in (-1, 1):
    for sy in (-1, 1):
        ax.add_patch(Circle((sx*90, sy*50), 4, fc="#4a4b50", ec="#222")); ax.add_patch(Circle((sx*90, sy*50), 1.7, fc="#c9a227", ec="#555"))

def box(x, y, w, d, name, color, txt="white", tag=None):
    ax.add_patch(Rectangle((x-w/2, y-d/2), w, d, fc=color, ec="#222", lw=1.2, alpha=0.92))
    ax.text(x, y, name, ha="center", va="center", fontsize=9, color=txt, fontweight="bold")
    if tag: ax.text(x-w/2+2, y+d/2-2, tag, ha="left", va="top", fontsize=11, color=txt, fontweight="bold")

box(55, 15, 72, 57, "Forsterker\nXH-M562", "#2f6fb5", tag="A")
box(-55, 22, 65, 30, "Pi Zero 2 W\n(USB-porter mot bak)", "#2e8b57", tag="B")
box(-55, -8, 32, 17, "DAC", "#7b3fa0", tag="C")
box(-85, 45, 20, 11, "Buck", "#555", tag="D")
box(0, 42, 75, 28, "Relékort 4-ch", "#b03030", tag="E")
box(55, -38, 60, 28, "MOSFET-kort × 2 (stablet)", "#1b1b1b", tag="F")
box(5, -3, 22, 12, "X9C ×2", "#3a7", tag="G")
box(-30, -50, 70, 14, "OLED-kort (bak vinduet)", "#223", tag="H")
# front/bak-elementer
for x, n in [(-80, "PWR"), (20, "AIR"), (37, "BT"), (70, "VOL")]:
    ax.add_patch(Circle((x, -D/2-7), 5, fc="#1d1d20", ec="#777")); ax.text(x, -D/2-7, n, ha="center", va="center", fontsize=6, color="white")
ax.text(-30, -D/2-7, "OLED-vindu", ha="center", va="center", fontsize=8, color="#333")
for x, n in [(76, "KCD1"), (54, "DC"), (36, "USB-C"), (20, "AUX"), (-37, "R +/−"), (-72, "L +/−")]:
    ax.text(x, D/2+7, n, ha="center", va="center", fontsize=8, color="#333", bbox=dict(boxstyle="round,pad=0.2", fc="#ddd", ec="#888"))
ax.text(0, -D/2-16, "FRONT", ha="center", fontsize=11, fontweight="bold", color="#555")
ax.text(0, D/2+16, "BAK", ha="center", fontsize=11, fontweight="bold", color="#555")
ax.annotate("", (36, D/2), (-50, 37), arrowprops=dict(arrowstyle="->", color="#2e8b57", lw=1.5, ls="--")); ax.text(-5, 58, "micro-USB-kabel", fontsize=7, color="#2e8b57")
ax.set_xlim(-115, 115); ax.set_ylim(-80, 80); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Innvendig plassering sett ovenfra (lokket av). A/B på stolper, C–G med VHB-tape, H på M2-avstandsstykker.", fontsize=9)
fig.savefig("guide_04_inni.png", dpi=120, bbox_inches="tight"); print("ok")
