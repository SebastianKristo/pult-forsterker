#!/usr/bin/env python3
"""3D-visning av USB-switch-varianten med testfronten -> ../3d-usbsw/usbsw.json (glTF med innebygd buffer)."""
import json
import math
import os
import numpy as np
import trimesh
import build_usbsw as u
import build_stl as b

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "3d-usbsw")
os.makedirs(OUT, exist_ok=True)
sc = trimesh.Scene()


def tm(man):
    m = man.to_mesh()
    return trimesh.Trimesh(np.asarray(m.vert_properties)[:, :3], np.asarray(m.tri_verts), process=False)


_n = {}


def add(mesh, col, name, T=None):
    _n[name] = _n.get(name, 0) + 1                      # unike nodenavn (ellers overskriver trimesh like navn)
    name = name if _n[name] == 1 else f"{name}_{_n[name]}"
    if T is not None:
        mesh = mesh.copy(); mesh.apply_transform(T)
    c = trimesh.visual.color.hex_to_rgba(col)
    mesh.visual = trimesh.visual.ColorVisuals(mesh, face_colors=np.tile(c, (len(mesh.faces), 1)))
    sc.add_geometry(mesh, node_name=name, geom_name=name)


def box(x0, x1, y0, y1, z0, z1, col, name):
    add(trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0],
        transform=trimesh.transformations.translation_matrix([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])), col, name)


HD, fz = b.D / 2, b.H / 2
# plate-koordinater (x, y opp, z tykkelse, front på z=T) -> verden (x, y = −HD − z, z = fz + y)
P = np.array([[1, 0, 0, 0], [0, 0, -1, -HD], [0, 1, 0, fz], [0, 0, 0, 1]], float)

add(tm(u.body_usbsw()), "#2c2d30", "kasse")
lid = tm(b.lid(ears=False)); add(lid, "#2c2d30", "lokk", trimesh.transformations.translation_matrix([0, 0, b.H + b.lip]))
add(tm(u.frontplate_test()), "#37383c", "testfront", P)
real = tm(b.frontplate()); add(real, "#37383c", "frontplate_ekte", P)
# innmat
f = b.floor_t
box(u.UG["x0"], u.UG["x1"], -50, 50, f, f + 16, "#d9d9de", "ugreen")
for dy in (-24, -8, 8, 24):
    box(u.UG["x0"] - 0.1, u.UG["x0"] + 1.0, dy - 6.2, dy + 6.2, f + 5.5, f + 10.5, "#1b1b1b", "ugreen_usb_a")
box(u.PI_X0, u.PI_X1, -28, 28, f + 4, f + 5.6, "#1f7a3a", "pi4")
box(u.PI_X1 - 21, u.PI_X1 + 3, -26, 26, f + 5.6, f + 21.6, "#b8bcc2", "pi4_porter")
box(u.PCB_X0, u.PCB_X1, b.pcb_pos[1] - 50, b.pcb_pos[1] + 50, f + 25, f + 26.6, "#1d4fa0", "hovedkort")
# testdeler i testfronten (plate-koordinater, så transformert)
T = 10.0
for x, y in [(x, s * b.btn_dz) for s in (1, -1) for x in b.btn_x] + [(b.pwr_x, 0.0)]:
    add(trimesh.creation.box(extents=[12, 12, 3.6], transform=trimesh.transformations.translation_matrix([x, y, 6.2 - 1.8])), "#1a1a1a", "tact", P)
    cap = trimesh.creation.cylinder(radius=6.0, height=6.5, sections=40); cap.apply_translation([x, y, 6.2 + 3.25])
    add(cap, {20.0: "#e8e8e8", 37.0: "#d0342c", b.pwr_x: "#2f6fd0"}.get(x, "#ddd"), "tact_hette", P)
    ly = (y + 10.5) if y >= 0 else (y - 10.5)
    led = trimesh.creation.cylinder(radius=2.5, height=8.6, sections=24); led.apply_translation([x, ly, 1.2 + 4.3])
    add(led, "#ffe9a8", "led", P)
add(trimesh.creation.box(extents=[38, 12, 1.6], transform=trimesh.transformations.translation_matrix([b.oled_x, 0, 6.6])), "#1d3f7a", "oled_kort", P)
add(trimesh.creation.box(extents=[30, 11.5, 1.4], transform=trimesh.transformations.translation_matrix([b.oled_x - 4, 0, 7.4 + 0.7])), "#050505", "oled_glass", P)

files = trimesh.exchange.gltf.export_gltf(sc, embed_buffers=True)
data = json.loads(files["model.gltf"])
with open(os.path.join(OUT, "usbsw.json"), "w") as fh:
    json.dump(data, fh, separators=(",", ":"))
print("->", os.path.join(OUT, "usbsw.json"), os.path.getsize(os.path.join(OUT, "usbsw.json")) // 1024, "kB")
