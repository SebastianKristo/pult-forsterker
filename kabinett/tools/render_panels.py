#!/usr/bin/env python3
"""2D-oppriss av front (frontplate) og bakvegg med nummererte hull og mål."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle

ACC = "#e8562a"

def tag(ax, x, y, n, text, dx=0, dy=22):
    ax.annotate(f"{n}  {text}", (x, y), xytext=(dx, dy), textcoords="offset points", ha="center", fontsize=9, fontweight="bold",
                color="white", bbox=dict(boxstyle="round,pad=0.3", fc=ACC, ec="none"), arrowprops=dict(arrowstyle="-", color=ACC, lw=1.2))

# ---------- FRONT ----------
fig, ax = plt.subplots(figsize=(12, 4.6))
ax.add_patch(FancyBboxPatch((-100, -24), 200, 48, boxstyle="round,pad=0,rounding_size=6", fc="#2c2d30", ec="#111", lw=2))
ax.add_patch(FancyBboxPatch((-94, -23), 188, 46, boxstyle="round,pad=0,rounding_size=3", fc="#37383c", ec="#111", lw=1.2))
ax.add_patch(FancyBboxPatch((-65, -19), 70, 38, boxstyle="round,pad=0,rounding_size=2", fc="#060708", ec="#333"))
ax.add_patch(Rectangle((-57.5, -13.75), 55, 27.5, fc="#000", ec="#2a3036", lw=0.8))
ax.text(-30, 4, "AIR  BT  AUX  USB", ha="center", color="#eef6ff", fontsize=6, family="monospace")
ax.text(-30, -4, "VOL ▮▮▮▮▮▮▮▮▮▯▯▯  42", ha="center", color="#eef6ff", fontsize=6, family="monospace")
for x, z, n in [(20, 8.5, "AIRPLAY"), (37, 8.5, "BT"), (20, -8.5, "AUX"), (37, -8.5, "USB")]:
    ax.add_patch(Circle((x, z), 6.2, fc="#1d1d20", ec="#777", lw=1.5)); ax.add_patch(Circle((x, z), 4.6, fc="none", ec="#e8f0ff", lw=1))
    ax.text(x, z - 11, n, ha="center", fontsize=5.5, color="#a3a29d")
ax.add_patch(Circle((-80, 0), 8.2, fc="#1d1d20", ec="#777", lw=1.5)); ax.add_patch(Circle((-80, 0), 6.2, fc="none", ec="#e8f0ff", lw=1))
ax.add_patch(Circle((-80, 0), 2.6, fc="none", ec="#e8f0ff", lw=1)); ax.plot([-80, -80], [0, 3.2], color="#e8f0ff", lw=1)
ax.text(-80, -14, "POWER", ha="center", fontsize=5.5, color="#a3a29d")
ax.add_patch(Circle((70, 0), 15, fc="#18181a", ec="#444", lw=1.5)); ax.add_patch(Circle((70, 0), 3.7, fc="#555", ec="#333")); ax.plot([70, 70], [8, 13.5], color="#eee", lw=1.5)
ax.text(70, -20, "VOL · PUSH MUTE", ha="center", fontsize=5.5, color="#a3a29d")
for sx in (-1, 1):
    for sz in (-1, 1): ax.add_patch(Circle((sx*88, sz*17), 1.7, fc="#1d1d20", ec="#555"))
tag(ax, -80, 8, 1, "POWER Ø16,4 ved x −80", 0, 38)
tag(ax, -30, 19, 2, "Akryl 70×38 i forsenkning · OLED bak", 0, 38)
tag(ax, 20, 14.7, 3, "AIRPLAY", -30, 38); tag(ax, 37, 14.7, 4, "BT", 30, 38)
tag(ax, 20, -14.7, 5, "AUX", -30, -42); tag(ax, 37, -14.7, 6, "USB", 30, -42)
tag(ax, 70, 15, 7, "Encoder Ø7,4 ved x 70 · knott 30 mm", 0, 38)
tag(ax, 88, -17, 8, "4 × M3 senkskrue → vegg", 0, -42)
ax.set_xlim(-108, 108); ax.set_ylim(-45, 45); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Front: frontplate 188 × 46 mm montert på kassen (mål i mm fra senter)", fontsize=10)
fig.savefig("guide_03_front.png", dpi=120, bbox_inches="tight"); plt.close(fig)

# ---------- BAK ----------
fig, ax = plt.subplots(figsize=(12, 4.6))
ax.add_patch(FancyBboxPatch((-100, -24), 200, 48, boxstyle="round,pad=0,rounding_size=6", fc="#2c2d30", ec="#111", lw=2))
ax.add_patch(Rectangle((76 - 9.7, -6.5), 19.4, 13, fc="#141415", ec="#777", lw=1.2)); ax.text(76, 0, "I  O", ha="center", va="center", color="#ddd", fontsize=7)
ax.add_patch(Circle((54, 0), 5.7, fc="#141415", ec="#bbb", lw=1.5)); ax.add_patch(Circle((54, 0), 2.6, fc="#333", ec="#777"))
ax.add_patch(Rectangle((36 - 4.8, -1.9), 9.6, 3.8, fc="#141415", ec="#bbb", lw=1.2))
for s in (-1, 1): ax.add_patch(Circle((36 + s*8.5, 0), 1.3, fc="#333", ec="#999"))
ax.add_patch(Circle((20, 0), 3.2, fc="#141415", ec="#bbb", lw=1.5))
for x, c in [(-30, "#a3261d"), (-45, "#141415"), (-65, "#a3261d"), (-80, "#141415")]:
    ax.add_patch(Circle((x, 0), 5.5, fc="#c9a227", ec="#8a6d12", lw=1.5)); ax.add_patch(Circle((x, 0), 2.2, fc=c, ec="none"))
ax.text(-37.5, -11, "R", ha="center", fontsize=7, color="#a3a29d"); ax.text(-72.5, -11, "L", ha="center", fontsize=7, color="#a3a29d")
tag(ax, 76, 6.5, 1, "KCD1 hovedbryter 19,4×13 · x 76", -30, 70)
tag(ax, 54, -5.7, 2, "DC-099 24 V Ø11,4 · x 54", 20, -62)
tag(ax, 36, 1.9, 3, "USB-C 9,6×3,8 + 2×Ø2,7 (c/c 17) · x 36", -40, 36)
tag(ax, 20, -3.2, 4, "AUX PJ392 Ø6,4 · x 20", -50, -36)
tag(ax, -37.5, 5.5, 5, "Høyre: rød + / svart −  (x −30 / −45)", -20, 36)
tag(ax, -72.5, -5.5, 6, "Venstre: rød + / svart −  (x −65 / −80)", 0, -36)
ax.set_xlim(-108, 112); ax.set_ylim(-50, 62); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("Bakvegg sett bakfra (mål i mm fra senter, alle i høyde z = 24)", fontsize=10)
fig.savefig("guide_02_bak.png", dpi=120, bbox_inches="tight"); print("ok")
