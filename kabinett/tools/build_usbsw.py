#!/usr/bin/env python3
"""KI Pultforsterker v2 med innebygd USB-switch (Ugreen 2 PC → 4 USB) – etter design_handoff USB_SWITCH.md,
tilpasset hovedkortet (150 × 100) stablet over Raspberry Pi 4.

Lager (i ../stl/):
  v2_body_usbsw.stl             kasse 215 × 160 × 48
  v2_lid_usbsw.stl              lokk med pultører
  v2_lid_frittstaende_usbsw.stl lokk uten ører
  v2_frontplate_usbsw.stl       frontplate til de ekte delene (2,42" OLED, 12 mm metallknapper, 16 mm POWER, EC11)
  v2_frontplate_test.stl        midlertidig testfront: 0,91" OLED, 12 × 12 tact-knapper med hette, 5 mm LED-er, EC11/potmeter

Plassering (sett ovenfra, front nede):
  venstre vegg | Ugreen 53 × 100 (USB-A ut gjennom vindu i veggen, USB-B mot høyre) | hovedkortet 150 × 100 på 25 mm stolper
  Pi 4 under hovedkortet til høyre, portene mot høyre (RJ45/USB-plugger får plass under kortet), SD-kortet mot venstre.
"""
import os
import sys

os.environ["VARIANT"] = "pcb"
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_stl as b  # noqa: E402
from manifold3d import Manifold  # noqa: E402

# ---------- hovedmål ----------
b.W, b.D = 215.0, 160.0
HW, HD = b.W / 2, b.D / 2
IW = HW - b.wall                                   # innvendig halvbredde 104,8
b.tower_xy = (HW - 10, HD - 10)                    # skruetårn (±97,5, ±70)
b.fp_w = b.W - 12                                  # frontplate 203 × 46

# ---------- innmat ----------
UG = dict(w=53.0, l=100.0, h=16.0)                 # Ugreen USB 2.0 sharing switch (mål den!)
UG["x0"] = -IW + 0.2                               # flush mot venstre vegg
UG["x1"] = UG["x0"] + UG["w"]
b.pcb_holes, b.pcb_pos, b.pcb_post_h = (142.0, 92.0), (UG["x1"] + 1.0 + 75.0, 2.0), 25.0   # kortsenter x ≈ 24,6
PCB_X0, PCB_X1 = b.pcb_pos[0] - 75, b.pcb_pos[0] + 75
# Pi 4 (85 × 56) med portene mot +x: kortets høyre kant 28 mm inn fra hovedkortets høyre kant (3 mm port + 25 mm plugg)
PI_X1 = PCB_X1 - 28.0
PI_X0 = PI_X1 - 85.0
b.pi_holes = (58.0, 49.0)
b.pi_pos = (PI_X0 + 3.5 + 29.0, 0.0)               # hullmønsterets senter: 32,5 mm fra SD-enden
b.amp_pos = None
b.vent_sides = (1,)                                 # ingen luftespor i venstre vegg (der står Ugreen)
b.vent_n = 26

# ---------- bakpanel (venstre → høyre) ----------
b.post_x = (-84.0, -70.0, -52.0, -38.0)            # høyttalerterminaler L−/L+ … R−/R+
USBB = dict(w=12.2, h=11.0, x=(-22.0, -6.0), z=b.floor_t + 10.0)   # 2 × USB-B panel (PC 1, PC 2), lavt
b.aux_x, b.usbc_x, b.rj45_x, b.dc_x, b.kcd1_x = -6.0, 10.0, 38.0, 62.0, 80.0   # KCD1 klar av skruetårnet (97,5)

# ---------- vindu i venstre vegg for Ugreen sine 4 USB-A ----------
SIDE = dict(y=0.0, hw=35.0, z0=6.0, z1=15.0)        # 70 × 9 mm


def body_usbsw():
    m = b.body()
    # USB-B-hull bak
    for x in USBB["x"]:
        m -= b.cube(USBB["w"], b.wall + 2, USBB["h"], x - USBB["w"] / 2, HD - b.wall - 1, USBB["z"] - USBB["h"] / 2)
    # vindu i venstre vegg
    m -= b.cube(b.wall + 2, 2 * SIDE["hw"], SIDE["z1"] - SIDE["z0"], -HW - 1, SIDE["y"] - SIDE["hw"], SIDE["z0"])
    # skinner som holder Ugreen på plass (6 mm høye, foran og bak), og et stopp mot høyre i bakkant/forkant
    for sy in (-1, 1):
        y = SIDE["y"] + sy * (UG["l"] / 2 + 0.3)
        m += b.cube(UG["w"] - 6, 2.0, 6.0, UG["x0"] + 3, y if sy > 0 else y - 2.0, b.floor_t - 0.01)
        m += b.cube(2.0, 10.0, 6.0, UG["x1"] + 0.3, y - 10.0 if sy > 0 else y, b.floor_t - 0.01)   # hjørnestopp, USB-B-portene i midten er fri
    return m


def frontplate_test():
    """Midlertidig testfront: samme ytre mål og skruehull som den ekte frontplaten, men 10 mm tykk med lommer bakfra,
    så de midlertidige delene sitter i platen og ledningene går inn gjennom hullene i frontveggen.
    - 0,91" OLED (kort 38 × 12, glass 30 × 11,5, pinnene mot høyre): lomme 38,6 × 12,6 bak, vindu 25 × 8 foran.
      Pinnene går inn gjennom det store skjermvinduet i veggen.
    - 12 × 12 tact-knapper med hette: kroppen i en 12,3 × 12,3-lomme bakfra, hetten (Ø ≈ 12) gjennom Ø12,6, og plass til
      skjørtet på hetten (Ø14,6 × 1,8) rett bak frontskinnet. Knappen settes inn bakfra, hetten klikkes på forfra.
      Bøy pinnene flatt – ledningene går inn gjennom knapphullet i veggen.
    - 5 mm LED over/under hver knapp: Ø5,2 gjennom, krage Ø6,2 bak, spor bak til knapphullet for beina.
    - Encoder/potmeter monteres i frontveggen som før (Ø7,4); testplaten har en Ø22-åpning rundt, så mutteren og knotten får plass.
    """
    T, skin = 10.0, 2.0                                       # platetykkelse, frontskinn (frontflaten er z = T, print forsiden ned)
    TACT = dict(body=12.3, cap=12.6, skirt=14.6, skirt_h=1.8, solder=16.0, solder_h=2.4)
    body_front = T - skin - TACT["skirt_h"]                   # knappekroppens forside (z = 6,2)
    m = Manifold.extrude(b.rr_cs(b.fp_w, b.fp_h, b.fp_r), T)

    def back(cs, depth, x, y):                                # lomme fra baksiden (z = 0) og «depth» inn
        return Manifold.extrude(cs, depth + 0.01).translate([x, y, -0.01])

    def thru(d, x, y):
        return b.cyl(d, T + 2).translate([x, y, -1])

    def groove(x0, y0, x1, y1, w=2.2, d=1.6):                 # spor i baksiden for LED-bein
        import math
        L = math.hypot(x1 - x0, y1 - y0)
        g = b.cube(L, w, d + 0.01, 0, -w / 2, -0.01).rotate([0, 0, math.degrees(math.atan2(y1 - y0, x1 - x0))])
        return g.translate([x0, y0, 0])

    # OLED: glasset sitter 4 mm forskjøvet bort fra pinnene (pinner mot høyre → glasset mot venstre)
    ox = b.oled_x
    m -= back(b.rr_cs(38.6, 12.6, 0.5), T - skin, ox, 0.0)
    m -= Manifold.extrude(b.rr_cs(25.0, 8.0, 0.8), T + 2).translate([ox - 4.0, 0.0, -1])
    m -= Manifold.extrude(b.rr_cs(29.0, 11.0, 1.2), 0.8).translate([ox - 4.0, 0.0, T - 0.79])   # fas foran
    # knapper: AIRPLAY/BT øverst, AUX/USB nederst, POWER til venstre
    btns = [(x, s * b.btn_dz) for s in (1, -1) for x in b.btn_x] + [(b.pwr_x, 0.0)]
    for x, y in btns:
        m -= thru(TACT["cap"], x, y)
        m -= back(b.rr_cs(TACT["body"], TACT["body"], 0.3), body_front, x, y)
        m -= b.cyl(TACT["skirt"], TACT["skirt_h"] + 0.01).translate([x, y, body_front - 0.005])
        m -= back(b.rr_cs(TACT["solder"], TACT["solder"], 1.0), TACT["solder_h"], x, y)
        ly = (y + 10.5) if (y >= 0) else (y - 10.5)            # LED over øverste rad / POWER, under nederste rad
        m -= thru(5.2, x, ly)
        m -= b.cyl(6.2, 1.2).translate([x, ly, -0.01])
        m -= groove(x, ly, x, y)
    # encoder / potmeter: sitter i frontveggen, åpning i testplaten rundt mutter og knott
    m -= thru(22.0, b.enc_x, 0.0)
    # skruehull med forsenkning foran og lomme bak, så M3 × 10 holder
    for sx in (-1, 1):
        for sz in (-1, 1):
            px, py = sx * (b.fp_w / 2 - 6), sz * (b.fp_h / 2 - 6)
            m -= b.cyl(3.4, T + 2).translate([px, py, -1])
            m -= Manifold.cylinder(1.5, 1.7, 3.2, b.SEG).translate([px, py, T - 1.4])
            m -= b.cyl(7.0, T - 4.0).translate([px, py, -0.01])
    # spar materiale: hulrom bak der det ikke sitter noe
    for x0, x1 in ((-66.0, -51.0), (-6.0, 9.0), (48.0, 56.0)):
        m -= b.cube(x1 - x0, b.fp_h - 14, T - skin - 1.0, x0, -(b.fp_h - 14) / 2, -0.01)
    return m


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "stl")
    print(f"Ugreen x {UG['x0']:.1f}…{UG['x1']:.1f} · hovedkort x {PCB_X0:.1f}…{PCB_X1:.1f} · Pi 4 x {PI_X0:.1f}…{PI_X1:.1f}")
    b.write_stl(body_usbsw(), os.path.join(out, "v2_body_usbsw.stl"))
    b.write_stl(b.lid(), os.path.join(out, "v2_lid_usbsw.stl"))
    b.write_stl(b.lid(ears=False), os.path.join(out, "v2_lid_frittstaende_usbsw.stl"))
    b.write_stl(b.frontplate(), os.path.join(out, "v2_frontplate_usbsw.stl"))
    b.write_stl(frontplate_test(), os.path.join(out, "v2_frontplate_test.stl"))
