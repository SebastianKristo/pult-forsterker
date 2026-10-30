#!/usr/bin/env python3
"""KI Pultforsterker v2 – kabinett for hovedkort rev B (180 × 100, USB-switch, AUX 1/2, TFT eller OLED).

Lager (i ../stl/):
  v2_body_revb.stl             kasse 215 × 160 × 48: kortet flush mot høyre vegg (4 × USB-A ut gjennom veggen), Pi 4 under kortet
  v2_lid_revb.stl / v2_lid_frittstaende_revb.stl
  v2_frontplate_revb.stl       frontplate (2,42" OLED-vindu, 4 × 12 mm knapper, 16 mm POWER, encoder)
  v2_frontplate_revb_tft.stl   frontplate med vindu for 2,8" TFT (aktivt område 57,6 × 43,2) i stedet for OLED

Bak (venstre → høyre): høyttalere L−/L+/R−/R+, AUX 1, AUX 2, USB-C PC 1, USB-C PC 2, USB-C (USB-lyd til Pi), RJ45, DC, KCD1.
Alle bakkontaktene er panelmonterte med korte kabler til kortet (kortets bakkant ligger 29 mm fra bakveggen).
"""
import os
import sys

os.environ["VARIANT"] = "pcb"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_stl as b  # noqa: E402
from manifold3d import Manifold  # noqa: E402

b.W, b.D = 215.0, 160.0
HW, HD = b.W / 2, b.D / 2
IW = HW - b.wall
b.tower_xy = (HW - 10, HD - 10)
b.fp_w = b.W - 12
b.vent_sides = (-1,)                                # luftespor bare i venstre vegg (USB-A i høyre)
b.vent_n = 26

# hovedkort 180 × 100, hull (4,4)-(176,96) -> mønster 172 × 92, flush mot høyre innervegg
PCB_W, PCB_D = 180.0, 100.0
PCB_X1 = IW - 0.3
PCB_X0 = PCB_X1 - PCB_W
PCB_Y0 = -HD + b.wall + 29.0                        # 29 mm til bakveggen for panelkontaktene
b.pcb_holes, b.pcb_post_h = (172.0, 92.0), 25.0
b.pcb_pos = (PCB_X0 + 90.0, PCB_Y0 + 50.0)
# Pi 4 under kortet, portene mot +x (pluggene får plass under kortet), SD-kortet mot venstre
PI_X0 = PCB_X0 + 5.0
b.pi_holes = (58.0, 49.0)
b.pi_pos = (PI_X0 + 3.5 + 29.0, b.pcb_pos[1] - 8.0)
b.amp_pos = None

# bakpanel
b.post_x = (-90.0, -76.0, -58.0, -44.0)
AUX_X = (-32.0, -20.0)
USBC_X = (-4.0, 15.0, 34.0)                         # PC 1, PC 2, USB-lyd (Pi)
b.rj45_x, b.dc_x, b.kcd1_x = 59.0, 59.0, 84.0       # RJ45 nederst og DC øverst i samme kolonne (to rader), KCD1 ytterst
RJ45_Z, DC_Z = 13.5, 34.0
b.aux_x, b.usbc_x = AUX_X[0], USBC_X[0]             # body() lager den første av hver; resten under

# USB-A-vindu i høyre vegg: kortets USB-A sitter i kort-y 16,2 … 68,7 (+ 7,2 mm hver vei), åpning over kortet
USB_Y = [PCB_Y0 + y for y in (16.2, 33.7, 51.2, 68.7)]
USB_Z0 = b.floor_t + b.pcb_post_h + 1.6 - 0.5
USB_Z1 = USB_Z0 + 8.0


def body_revb():
    rj, dc = b.rj45_x, b.dc_x
    b.rj45_x = b.dc_x = None                        # lages under i to rader
    m = b.body()
    b.rj45_x, b.dc_x = rj, dc
    m -= b.slot_back(b.rj45, rj, RJ45_Z)
    for s in (-1, 1):
        for dx in (-1.0, -0.5, 0.0, 0.5, 1.0):
            m -= b.hole_back(b.rj45_screw, rj + s * b.rj45_pitch / 2 + dx, RJ45_Z)
    m -= b.hole_back(b.dc_d, dc, DC_Z)
    m -= b.hole_back(b.aux_d, AUX_X[1], b.fz)
    for x in USBC_X[1:]:
        m -= b.slot_back(b.usbc, x, b.fz)
        for s in (-1, 1):
            m -= b.hole_back(b.usbc_screw, x + s * b.usbc_pitch / 2, b.fz)
    for y in USB_Y:   # ett vindu per USB-A (14,4 × 8)
        m -= b.cube(b.wall + 2, 14.8, USB_Z1 - USB_Z0, HW - b.wall - 1, y - 7.4, USB_Z0)
    return m


def frontplate_tft():
    """Frontplate med 2,8" TFT: vindu 59 × 45 for aktivt område 57,6 × 43,2 (modulglass ca. 69 × 50 bak), 4 klemmestolper."""
    m = Manifold.extrude(b.rr_cs(b.fp_w, b.fp_h, b.fp_r), b.fp_t)
    tx = b.oled_x
    m -= Manifold.extrude(b.rr_cs(59.0, 45.0, 1.0), b.fp_t + 2).translate([tx, 0, -1])
    m -= Manifold.extrude(b.rr_cs(71.0, 52.0, 1.5), 1.2).translate([tx, 0, -0.01])   # lomme bak for modulglasset
    for x in b.btn_x:
        for s in (-1, 1):
            m -= b.cyl(b.btn_d, b.fp_t + 2).translate([x, s * b.btn_dz, -1])
    m -= b.cyl(b.pwr_d, b.fp_t + 2).translate([b.pwr_x, 0, -1])
    m -= b.cyl(b.enc_d, b.fp_t + 2).translate([b.enc_x, 0, -1])
    for sx in (-1, 1):
        for sz in (-1, 1):
            px, py = sx * (b.fp_w / 2 - 6), sz * (b.fp_h / 2 - 6)
            m -= b.cyl(3.4, b.fp_t + 2).translate([px, py, -1])
            m -= Manifold.cylinder(1.5, 1.7, 3.2, b.SEG).translate([px, py, b.fp_t - 1.4])
    return m


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stl")
    print(f"kort x {PCB_X0:.1f}…{PCB_X1:.1f}, y {PCB_Y0:.1f}…{PCB_Y0 + PCB_D:.1f} · Pi x {PI_X0:.1f}…{PI_X0 + 85:.1f}")
    b.write_stl(body_revb(), os.path.join(out, "v2_body_revb.stl"))
    b.write_stl(b.lid(), os.path.join(out, "v2_lid_revb.stl"))
    b.write_stl(b.lid(ears=False), os.path.join(out, "v2_lid_frittstaende_revb.stl"))
    b.write_stl(b.frontplate(), os.path.join(out, "v2_frontplate_revb.stl"))
    b.write_stl(frontplate_tft(), os.path.join(out, "v2_frontplate_revb_tft.stl"))
