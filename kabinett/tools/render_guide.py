#!/usr/bin/env python3
"""Rendrer veiledningsbilder av kabinett v2 med nummererte merkelapper (matplotlib, uten GPU)."""
import struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from mpl_toolkits.mplot3d import proj3d

SHELL, FRONT, INK, ACCENT = "#2c2d30", "#37383c", "#111", "#e8562a"


def load(p):
    d = open(p, "rb").read(); n = struct.unpack("<I", d[80:84])[0]
    return np.frombuffer(d[84:], dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")], count=n)["v"]


def shade(v, light=(0.4, -0.6, 0.7), base=(0.17, 0.18, 0.19)):
    n = np.cross(v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    l = np.asarray(light) / np.linalg.norm(light); k = 0.85 + 1.6 * np.clip(n @ l, 0, 1)
    return np.clip(np.outer(k, base), 0, 1)


def mesh(ax, v, base=(0.17, 0.18, 0.19), alpha=1.0, lw=0.05):
    ax.add_collection3d(Poly3DCollection(v, facecolors=shade(v, base=base), edgecolor="none", linewidth=0, alpha=alpha))


def label(ax, xyz, text, dxy=(30, 18), size=9):
    x, y, _ = proj3d.proj_transform(*xyz, ax.get_proj())
    ax.annotate(text, (x, y), xytext=dxy, textcoords="offset points", fontsize=size, fontweight="bold", color="white",
                bbox=dict(boxstyle="round,pad=0.3", fc=ACCENT, ec="none"), arrowprops=dict(arrowstyle="-", color=ACCENT, lw=1.2), zorder=10)


def setup(ax, el, az, lim=120):
    ax.set_xlim(-lim, lim); ax.set_ylim(-lim, lim); ax.set_zlim(-lim * 0.5, lim * 0.5)
    ax.view_init(el, az); ax.set_axis_off(); ax.set_box_aspect((1, 1, 0.5))


body, front, lid = load("v2_body.stl"), load("v2_frontplate.stl"), load("v2_lid.stl")
fz = 24

# ---------- 1. Deler (eksplodert) ----------
fig = plt.figure(figsize=(11, 7)); ax = fig.add_subplot(projection="3d")
mesh(ax, body); mesh(ax, lid + np.array([0, 0, 75]), base=(0.17, 0.18, 0.19))
fr = front.copy(); fr = np.stack([fr[:, :, 0], -fr[:, :, 2] - 60 - 60, fr[:, :, 1] + fz], axis=2)
mesh(ax, fr, base=(0.22, 0.22, 0.24))
setup(ax, 28, -55, 135)
label(ax, (0, 0, 100), "Lokk (v2_lid.stl) – skrus i pulten", (-60, 30))
label(ax, (90, 50, 48), "4 skruetårn med M3-innsats", (40, 30))
label(ax, (0, -122, 30), "Frontplate (v2_frontplate.stl)", (-10, -40))
label(ax, (-60, -40, 10), "Kasse (v2_body.stl)", (-70, -30))
fig.savefig("guide_01_deler.png", dpi=110, bbox_inches="tight"); plt.close(fig)

# ---------- 2. Bakvegg ----------
fig = plt.figure(figsize=(11, 5)); ax = fig.add_subplot(projection="3d")
mesh(ax, body); setup(ax, 8, 90, 125)
for x, t, d in [(76, "1  KCD1 hovedbryter", (0, 60)), (54, "2  DC-099 24 V inn", (0, -55)), (36, "3  USB-C (PC)", (0, 60)),
                (20, "4  AUX 3,5 mm", (0, -55)), (-37, "5  Høyre høyttaler  + −", (0, 60)), (-72, "6  Venstre høyttaler  + −", (0, -55))]:
    label(ax, (x, 60, fz), t, d)
fig.savefig("guide_02_bak.png", dpi=110, bbox_inches="tight"); plt.close(fig)

# ---------- 3. Front ----------
fig = plt.figure(figsize=(11, 5)); ax = fig.add_subplot(projection="3d")
fr = np.stack([front[:, :, 0], -front[:, :, 2] - 62, front[:, :, 1] + fz], axis=2)
mesh(ax, body); mesh(ax, fr, base=(0.22, 0.22, 0.24)); setup(ax, 8, -90, 125)
for x, z, t, d in [(-80, fz, "1  POWER 16 mm", (-20, 60)), (-30, fz, "2  OLED 2,42\" bak akryl", (0, -60)),
                   (20, fz + 8.5, "3  AIRPLAY", (-10, 70)), (37, fz + 8.5, "4  BT", (30, 70)),
                   (20, fz - 8.5, "5  AUX", (-10, -70)), (37, fz - 8.5, "6  USB", (30, -70)), (70, fz, "7  Volum / mute", (30, 60))]:
    label(ax, (x, -62, z), t, d)
fig.savefig("guide_03_front.png", dpi=110, bbox_inches="tight"); plt.close(fig)

# ---------- 4. Innvendig plassering (ovenfra) ----------
fig = plt.figure(figsize=(11, 7.5)); ax = fig.add_subplot(projection="3d")
mesh(ax, body, alpha=0.55); setup(ax, 90, -90, 115)


def board(cx, cy, w, d, h, color, name, dxy):
    x0, x1, y0, y1 = cx - w / 2, cx + w / 2, cy - d / 2, cy + d / 2
    top = np.array([[[x0, y0, h], [x1, y0, h], [x1, y1, h], [x0, y1, h]]])
    ax.add_collection3d(Poly3DCollection(top, facecolor=color, edgecolor="#222", linewidth=0.6, alpha=0.95))
    label(ax, (cx, cy, h), name, dxy, 8)


board(55, 15, 72, 57, 8, "#2f6fb5", "A  Forsterker XH-M562", (10, 40))
board(-55, 20, 65, 30, 8, "#2e8b57", "B  Pi Zero 2 W", (-40, 40))
board(-55, -8, 32, 17, 7, "#7b3fa0", "C  DAC PCM5102A", (-70, -30))
board(-85, 45, 22, 12, 6, "#555", "D  Buck 24→5 V", (-70, 30))
board(0, 40, 75, 55, 8, "#b03030", "E  Relékort 4-ch", (0, 55))
board(55, -35, 60, 48, 8, "#1b1b1b", "F  MOSFET-kort × 2 (stablet)", (40, -45))
board(0, -5, 20, 12, 5, "#3a7", "G  X9C × 2", (-5, -45))
board(-30, -50, 70, 40, 10, "#223", "H  OLED (mot fronten)", (-60, -45))
label(ax, (54, 60, fz), "DC-099", (40, 20)); label(ax, (-80, -60, fz), "POWER", (-40, -20))
fig.savefig("guide_04_inni.png", dpi=110, bbox_inches="tight"); plt.close(fig)
print("ok")
