#!/usr/bin/env python3
"""STL for Pultforsterker v2 (speiler pultforsterker_v2.scad)."""
import os
import struct
import numpy as np
from manifold3d import Manifold, CrossSection, JoinType

W, D, H = 200.0, 120.0, 48.0
wall, floor_t, r_out = 2.7, 2.5, 6.0
lid_t, lip, clear = 3.0, 1.6, 0.3
fp_w, fp_h, fp_t, fp_r = 188.0, 46.0, 2.0, 3.0
fz = H / 2
oled_x, oled_w, oled_h = -30.0, 57.0, 30.0
win_w, win_h, win_r, win_depth = 70.0, 38.0, 2.0, 2.2
btn_d, btn_x, btn_dz = 12.4, (20.0, 37.0), 8.5
pwr_d, pwr_x = 16.4, -80.0
hp_jack, hp_d, hp_dz = False, 6.5, -14.0   # 3,5 mm hodetelefonjack (PJ392) rett under POWER-knappen (hovedkort rev B)
enc_d, enc_x = 7.4, 70.0
kcd1, kcd1_x = (19.4, 13.0), 76.0
dc_d, dc_x = 11.4, 54.0
usbc, usbc_x, usbc_pitch, usbc_screw = (9.6, 3.8), 36.0, 17.0, 2.7
aux_d, aux_x = 6.4, 20.0
post_d, post_x = 6.4, (-30.0, -45.0, -65.0, -80.0)
tower_d, tower_xy, insert_d = 8.0, (90.0, 50.0), 4.0
amp_holes, amp_pos = (50.0, 42.0), (55.0, 15.0)
pi_holes, pi_pos = (58.0, 23.0), (-55.0, 20.0)
vent_n, vent_w, vent_gap, vent_h = 16, 2.4, 3.6, 24.0
rj45, rj45_x, rj45_pitch, rj45_screw = (17.0, 15.6), None, 26.0, 3.3   # None = ingen RJ45 (Pi Zero); skruer som slisser 25–27 mm

VARIANT = os.environ.get("VARIANT", "zero")
if VARIANT == "pi4":
    # Raspberry Pi 4 B med Ethernet: 15 mm dypere kasse, Pi-en til høyre med portene mot venstre,
    # forsterkeren til venstre rett ved terminalene, RJ45-panelforlenger bak.
    D = 135.0
    tower_xy = (90.0, 57.0)
    pi_holes, pi_pos = (58.0, 49.0), (53.0, -10.0)
    amp_pos = (-58.0, 24.0)
    kcd1_x, dc_x, rj45_x, usbc_x, aux_x = 86.0, 68.0, 44.0, 14.0, -6.0
    post_x = (-24.0, -39.0, -59.0, -74.0)
    vent_n = 20
if VARIANT == "pcb":
    # KI hovedkort rev A (150 x 100) stablet over Raspberry Pi 4: Pi-en ligger på gulvet (6 mm stolper) med
    # USB/Ethernet-portene mot venstre utenfor kortet, hovedkortet 25 mm over på Ø8-stolper. 40-pin flatkabel (10 cm)
    # fra J5 ned til Pi-en. Bakveggen som Pi 4-varianten, 26 mm fra bakvegg til kortets bakkant (plass til DC-099/KCD1/RJ45).
    D = 165.0
    tower_xy = (90.0, 72.0)
    pi_holes, pi_pos = (58.0, 49.0), (-40.5, 18.0)         # Pi 4 under kortet, porter mot venstre
    amp_pos = None                                          # ingen forsterkermodul
    pcb_holes, pcb_pos, pcb_post_h = (142.0, 92.0), (3.0, 3.8), 25.0
    kcd1_x, dc_x, rj45_x, usbc_x, aux_x = 86.0, 68.0, 44.0, 14.0, -6.0
    post_x = (-24.0, -39.0, -59.0, -74.0)
    vent_n = 24
else:
    pcb_holes = pcb_pos = None
SEG = 64
vent_sides = (-1, 1)   # luftespor i venstre (−1) og høyre (+1) sidevegg


def rr_cs(w, d, r):
    return CrossSection.square([w, d], True).offset(-r, JoinType.Round, 2.0, SEG).offset(r, JoinType.Round, 2.0, SEG)


def rrect(w, d, r, h):
    return Manifold.extrude(rr_cs(w, d, r), h)


def cyl(d, h):
    return Manifold.cylinder(h, d / 2, d / 2, SEG)


def cube(sx, sy, sz, x=0, y=0, z=0, center=False):
    return Manifold.cube([sx, sy, sz], center).translate([x, y, z])


def hole_y(d, x, z, y0=-D / 2 - 3, length=wall + 6):
    return cyl(d, length).rotate([-90, 0, 0]).translate([x, y0, z])


def hole_back(d, x, z):
    return hole_y(d, x, z, D / 2 - wall - 3)


def slot_back(sz, x, z):
    return cube(sz[0], wall + 2, sz[1], x - sz[0] / 2, D / 2 - wall - 1, z - sz[1] / 2)


def rrect_y(w, h, r, x, y, z, length):
    return Manifold.extrude(rr_cs(w, h, r), length).rotate([-90, 0, 0]).translate([x, y, z])


def body():
    m = rrect(W, D, r_out, H) - rrect(W - 2 * wall, D - 2 * wall, r_out - wall, H).translate([0, 0, floor_t])
    m -= rrect_y(oled_w, oled_h, 1.5, oled_x, -D / 2 - 1, fz, wall + 2)
    for x in btn_x:
        for s in (-1, 1):
            m -= hole_y(btn_d, x, fz + s * btn_dz)
    m -= hole_y(pwr_d, pwr_x, fz)
    if hp_jack:
        m -= hole_y(hp_d, pwr_x, fz + hp_dz)
    m -= hole_y(enc_d, enc_x, fz)
    m -= cube(20, 1.2, 26, enc_x - 10, -D / 2 + wall - 0.01, fz - 13)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m -= hole_y(2.6, sx * (fp_w / 2 - 6), fz + sz * (fp_h / 2 - 6))
    m -= slot_back(kcd1, kcd1_x, fz)
    if dc_x is not None:
        m -= hole_back(dc_d, dc_x, fz)
    m -= slot_back(usbc, usbc_x, fz)
    for s in (-1, 1):
        m -= hole_back(usbc_screw, usbc_x + s * usbc_pitch / 2, fz)
    m -= hole_back(aux_d, aux_x, fz)
    for x in post_x:
        m -= hole_back(post_d, x, fz)
    if rj45_x is not None:
        m -= slot_back(rj45, rj45_x, fz)
        for s in (-1, 1):   # sliss 2 mm lang: passer skrueavstand 25–27 mm
            for dx in (-1.0, -0.5, 0.0, 0.5, 1.0):
                m -= hole_back(rj45_screw, rj45_x + s * rj45_pitch / 2 + dx, fz)
    for s in vent_sides:
        for i in range(vent_n):
            m -= cube(wall + 2, vent_w, vent_h, s * (W / 2 - wall / 2) - (wall + 2) / 2,
                      -((vent_n - 1) * vent_gap) / 2 + i * vent_gap, floor_t + 12)
    if amp_pos is not None:
        for i in range(10):
            m -= cube(2.4, 50, floor_t + 2, amp_pos[0] - 27 + i * 6, amp_pos[1] - 25, -1)
    if pcb_pos is not None:   # luftespor under hovedkortet (forsterkerdelen) og stolper
        for i in range(14):
            m -= cube(2.4, 60, floor_t + 2, pcb_pos[0] + 5 + i * 5, pcb_pos[1] - 30, -1)
        for x in (-1, 1):
            for y in (-1, 1):
                m += (cyl(8, floor_t + pcb_post_h) - cyl(2.6, floor_t + pcb_post_h + 1)).translate([pcb_pos[0] + x * pcb_holes[0] / 2, pcb_pos[1] + y * pcb_holes[1] / 2, 0])
    if VARIANT in ("pi4", "pcb") and pi_pos is not None:   # luftespor i gulvet under Pi 4
        for i in range(12):
            m -= cube(2.4, 44, floor_t + 2, pi_pos[0] - 33 + i * 6, pi_pos[1] - 22, -1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            tower = cyl(tower_d, H) + cube(tower_d, 1, H, -tower_d / 2, 0, 0)
            tower -= cyl(insert_d, 7).translate([0, 0, H - 6])
            m += tower.translate([sx * tower_xy[0], sy * tower_xy[1], 0])
    for x in (-1, 1):
        for y in (-1, 1):
            if amp_pos is not None:
                m += (cyl(6, floor_t + 5) - cyl(2.6, floor_t + 6)).translate([amp_pos[0] + x * amp_holes[0] / 2, amp_pos[1] + y * amp_holes[1] / 2, 0])
            if pi_pos is not None:
                m += (cyl(5.5, floor_t + 4) - cyl(2.2, floor_t + 5)).translate([pi_pos[0] + x * pi_holes[0] / 2, pi_pos[1] + y * pi_holes[1] / 2, 0])
    return m


def frontplate():
    m = Manifold.extrude(rr_cs(fp_w, fp_h, fp_r), fp_t)
    m -= Manifold.extrude(rr_cs(oled_w + 4, oled_h + 4, 1), fp_t + 2).translate([oled_x, 0, -1])
    m -= Manifold.extrude(rr_cs(win_w, win_h, win_r), win_depth + 1).translate([oled_x, 0, fp_t - win_depth])
    for x in btn_x:
        for s in (-1, 1):
            m -= cyl(btn_d, fp_t + 2).translate([x, s * btn_dz, -1])
    m -= cyl(pwr_d, fp_t + 2).translate([pwr_x, 0, -1])
    if hp_jack:
        m -= cyl(hp_d, fp_t + 2).translate([pwr_x, hp_dz, -1])
    m -= cyl(enc_d, fp_t + 2).translate([enc_x, 0, -1])
    for sx in (-1, 1):
        for sz in (-1, 1):
            px, py = sx * (fp_w / 2 - 6), sz * (fp_h / 2 - 6)
            m -= cyl(3.4, fp_t + 2).translate([px, py, -1])
            m -= Manifold.cylinder(1.5, 1.7, 3.2, SEG).translate([px, py, fp_t - 1.4])
    return m


def lid(ears=True):
    ear_w, ear_l, ear_slot, ear_screw = 22.0, 19.0, 10.0, 4.6
    m = rrect(W, D, r_out, lid_t)
    m += rrect(W - 2 * wall - 2 * clear, D - 2 * wall - 2 * clear, r_out - wall, lip).translate([0, 0, -lip])
    for sx in (-1, 1):
        for sy in (-1, 1):
            if ears:
                m += rrect(ear_l, ear_w, 3, lid_t).translate([sx * (W / 2 + 8.5), sy * 40, 0])
    for sx in (-1, 1):
        for sy in (-1, 1):
            px, py = sx * tower_xy[0], sy * tower_xy[1]
            m -= cyl(3.4, lid_t + lip + 2).translate([px, py, -lip - 1])
            m -= Manifold.cylinder(1.7, 1.7, 3.2, SEG).translate([px, py, lid_t - 1.6])
            slot = Manifold.hull(cyl(ear_screw, lid_t + 2).translate([-ear_slot / 2 + ear_screw / 2, 0, 0]) +
                                 cyl(ear_screw, lid_t + 2).translate([ear_slot / 2 - ear_screw / 2, 0, 0]))
            if ears:
                m -= slot.translate([sx * (W / 2 + 10), sy * 40, -1])
    m -= cube(30, 13, lip + 1.7, 0, D / 2 - 6.5, -lip - 1, True)
    return m


def write_stl(man, path):
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3]
    t = np.asarray(mesh.tri_verts, dtype=np.int64)
    tri = v[t]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    with open(path, "wb") as f:
        f.write(b"Pultforsterker v2".ljust(80, b"\0"))
        f.write(struct.pack("<I", len(t)))
        f.write(rec.tobytes())
    bb = man.bounding_box()
    print(f"{os.path.basename(path)}: {len(t)} tri, {man.volume()/1000:.0f} cm3, "
          f"{bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm")


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    sfx = {"zero": "", "pi4": "_pi4", "pcb": "_pcb"}[VARIANT]
    write_stl(body(), os.path.join(here, f"v2_body{sfx}.stl"))
    if VARIANT == "zero":
        write_stl(frontplate(), os.path.join(here, "v2_frontplate.stl"))   # frontplaten er lik for begge
    write_stl(lid(), os.path.join(here, f"v2_lid{sfx}.stl"))
    write_stl(lid(ears=False), os.path.join(here, f"v2_lid_frittstaende{sfx}.stl"))
