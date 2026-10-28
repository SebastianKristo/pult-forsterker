#!/usr/bin/env python3
"""Pultforsterker Radio Retro (mono, Raspberry Pi 4) – printbare deler.

Bygger på design-handoffen (radio/handoff) og delene som er kjøpt:
  * 2,8" SPI-TFT (ILI9341, rødt kort 86 × 50, pinnerad mot venstre)
  * 9 × taktile brytere 6 × 6 × 7 mm (Vertical-settet) på hullkort, 6 × 3 mm LED + 2 mm akrylstav som lysprikk
  * EC11 «Plum» 20 mm, 3" 78 mm kvadratisk høyttaler (AUIN), PAM8406, 12 mm POWER-knapp i toppen av skallet
  * Raspberry Pi 4 liggende på et brett i bunnen, lyd ut på 3,5 mm-jacken

Koordinater som i handoffen: x mot høyre, y dybde (front = −y), z opp, origo midt i skallet. mm.
Alle mål som avhenger av delene står samlet under «DELER», så de kan justeres etter måling.

Kjør:  python3 build_radio.py   →  stl/*.stl (utskriftsretning) + radio_montert.glb (forhåndsvisning)
"""
import json
import math
import os

import numpy as np
from manifold3d import CrossSection, FillRule, Manifold

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "stl")
SEG = 48

# ---------------------------------------------------------------- skall (fra handoffen)
CT = json.load(open(os.path.join(HERE, "handoff", "retro", "shell_contours.json")))["deep"]
YMIN, YMAX = -52.0, 52.0


def _fix_recess(c):
    """Bakre snitt treffer bunnslissene: speil øvre halvdel (som i handoffen)."""
    rec, inn = c["recess"], c["inner"]
    n = len(rec)
    rad = lambda p: math.hypot(p[0], p[1])
    out = []
    for k, p in enumerate(rec):
        if p[1] >= 0:
            out.append(p); continue
        m = (n - k) % n
        lim = rad(rec[m]) * rad(inn[k]) / rad(inn[m])
        r = rad(p)
        out.append([p[0] * lim / r, p[1] * lim / r] if r > lim else p)
    return out


IN = np.array(CT["inner"], float)
REC = np.array(_fix_recess(CT), float)


def shrink(P, d):
    r = np.hypot(P[:, 0], P[:, 1])[:, None]
    return P * (r - d) / r


def zat(P, x, s):
    v = [s * p[1] for p in P if abs(p[0] - x) < 4 and s * p[1] > 0]
    return max(v)


def cs_poly(P):
    return CrossSection([P.tolist()], FillRule.EvenOdd)


def rr(w, h, r, cx=0.0, cy=0.0):
    """Avrundet rektangel w × h (hele mål)."""
    r = min(r, w / 2 - 1e-3, h / 2 - 1e-3)
    return CrossSection.square([w - 2 * r, h - 2 * r], True).offset(r, circular_segments=SEG).translate([cx, cy]) if r > 0 \
        else CrossSection.square([w, h], True).translate([cx, cy])


def circ(d, cx=0.0, cy=0.0, n=SEG):
    return CrossSection.circle(d / 2, n).translate([cx, cy])


def ext(cs, h, z0=0.0):
    return Manifold.extrude(cs, h).translate([0, 0, z0])


def cyl(d, h, x=0.0, y=0.0, z0=0.0, d2=None, n=SEG):
    return Manifold.cylinder(h, d / 2, (d2 if d2 else d) / 2, n).translate([x, y, z0])


def union(parts):
    parts = [p for p in parts if p is not None]
    return Manifold.batch_boolean(parts, __import__("manifold3d").OpType.Add) if len(parts) > 1 else parts[0]


def text_cs(txt, h, cx, cy, bold=True, anchor="center"):
    """Tekst som CrossSection (matplotlib TextPath, DejaVu Sans)."""
    from matplotlib.font_manager import FontProperties
    from matplotlib.textpath import TextPath
    tp = TextPath((0, 0), txt, size=h * 1.38, prop=FontProperties(family="DejaVu Sans", weight="bold" if bold else "normal"))
    polys = [p for p in tp.to_polygons(closed_only=True) if len(p) >= 3]
    cs = CrossSection([p.tolist() for p in polys], FillRule.EvenOdd)
    (x0, y0), (x1, y1) = cs.bounds()[:2], cs.bounds()[2:]
    dx = cx - (x0 + x1) / 2 if anchor == "center" else cx - x0
    return cs.translate([dx, cy - (y0 + y1) / 2])


def tri(cx, cy, w, h, left=False):
    s = -1 if left else 1
    return CrossSection([[[cx - s * w / 2, cy - h / 2], [cx + s * w / 2, cy], [cx - s * w / 2, cy + h / 2]]], FillRule.EvenOdd)


# ---------------------------------------------------------------- DELER (juster etter måling)
FPY, FT, COLLAR = YMIN + 12, 3.0, 6.0          # faceplate front y = −40, 3 mm tykk, 6 mm krage
CL = 0.35                                      # klaring mot skallets innside
PITCH = 12.7                                   # tasteavstand = 5 hull på hullkortet (2,54 mm)
FAV = [(50 + (i - 2.5) * PITCH, -30.0) for i in range(6)]
LED = [(x, z + 3 * 2.54) for x, z in FAV]       # lysprikk 7,62 mm over tasten (3 hull – gir plass til hettekragen)
ROW2 = -30.0 - 6 * 2.54                         # SOURCE ◀◀ ▶▶ (6 hull under)
BTN2 = [("source", FAV[0][0], ROW2), ("prev", FAV[1][0], ROW2), ("next", FAV[2][0], ROW2)]
KEY_HOLE = (10.9, 6.7)                          # hull i faceplaten
CAP = (10.4, 6.2, 1.8)                          # tastehette b × h × r
CAP_FLANGE = (12.6, 8.4)                        # krage bak faceplaten (holder hetten på plass)
CAP_OUT = 1.5                                   # hvor mye hetten stikker ut foran
BOARD_GAP = 12.0                                # faceplate bak → hullkortets forside
SW_H = 7.0                                      # bryterhøyde over kortet (6 × 6 × 7)
LED_H = 5.3                                     # 3 mm LED, kropp over kortet
ROD_D = 2.0                                     # akrylstav
PROTO = dict(x0=6.0, x1=94.0, z0=-50.0, z1=-19.0, holes=[(9, -47), (91, -47), (9, -22), (91, -22)])

DISP = dict(x=50.0, z=6.0)                      # senter av aktivt område (handoff)
WIN = (60.0, 46.0, 1.0)                         # vindu gjennom faceplaten
ACRYL = (64.0, 50.0, 2.5, 2.0)                  # røykfarget akryl: b × h × r × tykkelse (lomme foran)
GLASS = dict(w=69.6, h=50.4, t=2.6, dx=-2.6)    # TFT-glass, senter forskjøvet 2,6 mm mot pinneraden (venstre)
TFT_PCB = dict(w=86.0, h=50.0, left=12.0)       # kortet stikker 12 mm ut på pinnesiden, 5 mm på andre siden
CLAMP_BOSS = [(25, -22.5), (75, -22.5), (25, 34.5), (75, 34.5)]

ENC = dict(x=98.0, z=-8.0, hole=7.4)           # EC11, M7-hylse
KNOB = dict(d=28.0, h=16.0, shaft=5.85, depth=12.0)

SPK = dict(x=-52.0, z=0.0, hole=72.0, frame=78.0)
MAGS = [(-96, 40), (-96, -40), (-18, 56), (-18, -56)]
MAG = (6.3, 2.2)

WALL_X = (-4.0, -1.6)                           # skillevegg (flyttet 8,8 mm mot venstre for TFT-kortet)
POWER_TOP = (0.0, 5.5)                          # 12 mm knapp i toppen (x, y)

BACK = dict(y0=YMAX - 3.0, t=2.7, z=-34.0, kcd1=(44.0, 19.2, 12.8), dc=(22.0, 11.2), usbc=(6.0, 9.4, 3.6, 17.0, 2.7))

PI = dict(x0=4.0, y0=-12.0, w=85.0, d=56.0, holes=[(3.5, 3.5), (61.5, 3.5), (3.5, 52.5), (61.5, 52.5)])
TRAY = dict(z=-66.4, t=2.4, x1=92.0, y0=-14.0, y1=46.0, boss_h=4.0)

GRILL = dict(t=1.6, dome=10.0, hole=3.2, pitch=5.4, K=dict(x=68.0, z=-20.0, w=124.0, h=112.0, r=24.0))


# ================================================================= FACEPLATE
def faceplate():
    outer = cs_poly(shrink(IN, CL))
    plate = ext(outer, FT)
    collar = ext(outer - cs_poly(shrink(IN, CL + 2.0)), COLLAR, FT)
    body = plate + collar

    cuts = [ext(circ(SPK["hole"], SPK["x"], SPK["z"], 96), FT + 1, -0.5)]
    cuts.append(ext(rr(WIN[0], WIN[1], WIN[2], DISP["x"], DISP["z"]), FT + 1, -0.5))
    cuts.append(ext(rr(ACRYL[0] + 0.3, ACRYL[1] + 0.3, ACRYL[2], DISP["x"], DISP["z"]), ACRYL[3] + 1, -1))   # 2 mm lomme forfra
    for x, z in FAV + [(b[1], b[2]) for b in BTN2]:
        cuts.append(ext(rr(KEY_HOLE[0], KEY_HOLE[1], CAP[2] + 0.25, x, z), FT + 1, -0.5))
    for x, z in LED:
        cuts.append(ext(circ(ROD_D + 0.1, x, z, 24), FT + 1, -0.5))
    cuts.append(ext(circ(ENC["hole"], ENC["x"], ENC["z"]), FT + 1, -0.5))
    for x, z in MAGS:
        cuts.append(ext(circ(MAG[0], x, z, 32), MAG[1] + 0.01, -0.01))   # lomme forfra, 2,2 dyp
    # etiketter, 0,4 mm gravert forfra
    lab = text_cs("SOURCE", 1.8, BTN2[0][1], ROW2 - 5.6) + text_cs("VOLUME · PUSH MUTE", 1.8, ENC["x"], ENC["z"] - KNOB["d"] / 2 - 3)
    cuts.append(ext(lab, 0.4, -0.01))

    adds = []
    # lysledere: hylse bak hver prikk, 2,1 mm for staven, 3,2 mm for LED-toppen
    led_top = FT + BOARD_GAP - LED_H
    for x, z in LED:
        adds.append(cyl(4.4, led_top - FT - 0.2, x, z, FT))
    # hullkort-stolper
    for x, z in PROTO["holes"]:
        adds.append(cyl(5.0, BOARD_GAP, x, z, FT))
    # TFT: ramme som låser glasset, og fire klemme-stolper
    gx = DISP["x"] + GLASS["dx"]
    frame = rr(GLASS["w"] + 0.6 + 2.4, GLASS["h"] + 0.6 + 2.4, 1.5, gx, DISP["z"]) - rr(GLASS["w"] + 0.6, GLASS["h"] + 0.6, 0.5, gx, DISP["z"])
    adds.append(ext(frame, 2.0, FT))
    for x, z in CLAMP_BOSS:
        adds.append(cyl(6.0, GLASS["t"] + 1.6, x, z, FT))
    # høyttaler: fire styrelister rundt den kvadratiske rammen + fire klemmestolper på diagonalene
    s = SPK["frame"] / 2 + 0.4
    for dx, dz, w, h in [(s + 0.6, 0, 1.2, 30), (-s - 0.6, 0, 1.2, 30), (0, s + 0.6, 30, 1.2), (0, -s - 0.6, 30, 1.2)]:
        adds.append(ext(rr(w, h, 0.3, SPK["x"] + dx, SPK["z"] + dz), 3.0, FT))
    rd = SPK["frame"] / 2 * math.sqrt(2) + 3.5
    spk_boss = [(SPK["x"] + sx * rd / math.sqrt(2), SPK["z"] + sz * rd / math.sqrt(2)) for sx in (-1, 1) for sz in (-1, 1)]
    for x, z in spk_boss:
        adds.append(cyl(7.0, 2.5, x, z, FT))
    # EC11: støtte-ring rundt hylsen bak (mot vridning når mutteren strammes)
    adds.append(ext(circ(ENC["hole"] + 5, ENC["x"], ENC["z"]) - circ(ENC["hole"] + 0.2, ENC["x"], ENC["z"]), 1.0, FT))

    body = body + union(adds)
    body = body - union(cuts)
    # hull i stolper / hylser
    holes = []
    for x, z in LED:
        holes.append(cyl(ROD_D + 0.1, 10, x, z, FT - 0.5, n=24))
        holes.append(cyl(3.3, 4.0, x, z, led_top - 3.0, n=24))
    for x, z in PROTO["holes"]:
        holes.append(cyl(2.2, BOARD_GAP, x, z, FT + 1.0))
    for x, z in CLAMP_BOSS:
        holes.append(cyl(2.2, 6, x, z, FT + 0.5))
    for x, z in spk_boss:
        holes.append(cyl(2.6, 5.0, x, z, FT + 2.5 - 5.0 + 0.5))   # M3 selvgjengende, blind (0,5 mm hud foran)
    body = body - union(holes)
    return body, spk_boss


# ================================================================= TASTEHETTER
def keycap(label=None, icon=None):
    w, h, r = CAP
    front = ext(rr(w, h, r), CAP_OUT + FT)                              # forside z = 0 (ligger på bordet)
    flange = ext(rr(CAP_FLANGE[0], CAP_FLANGE[1], 1.2), 1.0, CAP_OUT + FT)
    stem_len = BOARD_GAP - SW_H - 1.0
    stem = cyl(3.4, stem_len, 0, 0, CAP_OUT + FT + 1.0, n=32)
    cap = front + flange + stem - cyl(1.6, stem_len - 1.5, 0, 0, CAP_OUT + FT + 1.0 + 1.5, n=24)   # hul stamme (sparer fyll)
    eng = None
    if label:
        eng = text_cs(label, 3.6, 0, 0)
    elif icon == "prev":
        eng = tri(-1.4, 0, 2.6, 3.4, True) + tri(1.2, 0, 2.6, 3.4, True)
    elif icon == "next":
        eng = tri(-1.2, 0, 2.6, 3.4) + tri(1.4, 0, 2.6, 3.4)
    elif icon == "source":
        eng = circ(3.6, 0, 0, 32) - circ(2.2, 0, 0, 32) + rr(0.8, 2.4, 0.2, 0, 1.4)
    if eng:
        cap = cap - ext(eng, 0.5, -0.01)                                 # gravert i forsiden
    return cap


# ================================================================= TFT-KLEMME, HØYTTALERKLEMME
def tft_clamp():
    return ext(rr(14, 7, 2), 2.0) - ext(circ(2.8, -3.5, 0), 3, -0.5)


def spk_clamp():
    return ext(rr(16, 8, 2.5), 2.0) - ext(circ(3.3, -4, 0), 3, -0.5)


# ================================================================= GRILL
def sd_rr(x, z, K):
    qx = np.abs(x - K["x"]) - K["w"] / 2 + K["r"]
    qz = np.abs(z - K["z"]) - K["h"] / 2 + K["r"]
    return np.hypot(np.maximum(qx, 0), np.maximum(qz, 0)) + np.minimum(np.maximum(qx, qz), 0) - K["r"]


def grill():
    K = GRILL["K"]
    gp = cs_poly(shrink(IN, CL + 0.4)) - rr(K["w"], K["h"], K["r"], K["x"], K["z"])
    # kantlinjen for kuppelen (avstand til nærmeste kant)
    segs = []
    for poly in gp.to_polygons():
        p = np.array(poly); q = np.roll(p, -1, axis=0); segs.append((p, q))
    P = np.vstack([s[0] for s in segs]); Q = np.vstack([s[1] for s in segs])

    def dome(x, z):
        d = np.full(x.shape, 1e9)
        for i in range(0, len(P), 64):
            p, q = P[i:i + 64], Q[i:i + 64]
            dx, dz = (q - p)[:, 0], (q - p)[:, 1]
            L = dx * dx + dz * dz + 1e-12
            t = np.clip(((x[:, None] - p[:, 0]) * dx + (z[:, None] - p[:, 1]) * dz) / L, 0, 1)
            dd = np.hypot(x[:, None] - p[:, 0] - t * dx, z[:, None] - p[:, 1] - t * dz).min(axis=1)
            d = np.minimum(d, dd)
        t = np.minimum(1, d / 28.0)
        return GRILL["dome"] * t * t * (3 - 2 * t)

    perf = cs_poly(shrink(IN, 4.0))
    holes = []
    pitch = GRILL["pitch"]
    for j in range(-16, 17):
        for i in range(-26, 27):
            x, z = (i + (j & 1) * 0.5) * pitch, j * pitch * 0.866
            if not _inside(perf, x, z):
                continue
            if sd_rr(np.array([x]), np.array([z]), K)[0] < 3.4 or any(math.hypot(x - mx, z - mz) < 7 for mx, mz in MAGS):
                continue
            holes.append(circ(GRILL["hole"], x, z, 12))
    sheet = gp - CrossSection.batch_boolean(holes, __import__("manifold3d").OpType.Add) if holes else gp
    m = ext(sheet, GRILL["t"]).refine_to_length(3.0)

    def warp(v):
        v = np.array(v, dtype=np.float64)
        v[:, 2] += dome(v[:, 0], v[:, 1])
        return v
    m = m.warp_batch(warp)
    # magnetstolper under kuppelen
    for mx, mz in MAGS:
        h = float(dome(np.array([mx]), np.array([mz]))[0])
        m = m + cyl(9.0, h + 0.8, mx, mz, 0) - cyl(MAG[0], MAG[1], mx, mz, -0.01, n=32)
    return m


_inside_cache = {}


def _inside(cs, x, z):
    key = id(cs)
    if key not in _inside_cache:
        _inside_cache[key] = [np.array(p) for p in cs.to_polygons()]
    inside = False
    for poly in _inside_cache[key]:
        xs, zs = poly[:, 0], poly[:, 1]
        xs2, zs2 = np.roll(xs, -1), np.roll(zs, -1)
        cond = ((zs > z) != (zs2 > z)) & (x < (xs2 - xs) * (z - zs) / (zs2 - zs + 1e-12) + xs)
        inside ^= bool(np.count_nonzero(cond) & 1)
    return inside


# ================================================================= BAKPLATE
def backplate():
    b = BACK
    plate = ext(cs_poly(shrink(REC, 0.3)), b["t"])
    cuts = [rr(b["kcd1"][1], b["kcd1"][2], 0.5, b["kcd1"][0], b["z"]), circ(b["dc"][1], b["dc"][0], b["z"]),
            rr(b["usbc"][1], b["usbc"][2], 1.6, b["usbc"][0], b["z"])]
    for s in (-1, 1):
        cuts.append(circ(b["usbc"][4], b["usbc"][0] + s * b["usbc"][3] / 2, b["z"], 24))
    sc = shrink(REC, 3.5)
    for k in (22, 68, 112, 158):
        cuts.append(circ(3.4, sc[k][0], sc[k][1], 24))
    for dx in (-30, -20, -10, 0, 10, 20, 30):
        for dz in (20, 34):
            cuts.append(rr(2.4, 9.0, 1.1, dx, dz))
    plate = plate - ext(CrossSection.batch_boolean(cuts, __import__("manifold3d").OpType.Add), b["t"] + 2, -1)
    # sett bakfra er x speilet: lag teksten på −x og speil den
    lab = text_cs("POWER", 2.6, -b["kcd1"][0], b["z"] + 12) + text_cs("DC 5V", 2.6, -b["dc"][0], b["z"] + 12) + text_cs("USB", 2.6, -b["usbc"][0], b["z"] + 12)
    plate = plate - ext(lab.mirror([1, 0]), 0.4, b["t"] - 0.4 + 0.01)   # gravert på utsiden (bak)
    return plate


# ================================================================= SKILLEVEGG (2D i (y, z), ekstrudert langs x)
def divider():
    x0, x1 = WALL_X
    xm = (x0 + x1) / 2
    y0, y1 = FPY + FT + 0.2, YMAX - 3.0 - 0.3
    zt, zb = zat(IN, xm, 1) - 0.6, -zat(IN, xm, -1) + 0.6
    wall = rr(y1 - y0, zt - zb, 1.0, (y0 + y1) / 2, (zt + zb) / 2)
    # hakk for faceplatens krage (2,35 mm fra veggen, 6 mm dyp) og for POWER-knappen i toppen
    wall = wall - rr(COLLAR + 0.6, 6.0, 0.3, y0 + (COLLAR + 0.6) / 2 - 0.01, zt) - rr(COLLAR + 0.6, 6.0, 0.3, y0 + (COLLAR + 0.6) / 2 - 0.01, zb)
    wall = wall - rr(19.0, 64.0, 3.0, POWER_TOP[1], zt)            # 12 mm knapp + kabelsko (ned til z ≈ 40)
    # kabelhull (høyttalerledning fra forsterkeren) og to M3 for Pi-brettets lepp
    wall = wall - circ(10.0, 30.0, 0.0) - circ(3.4, 0.0, TRAY["z"] + 6.0, 24) - circ(3.4, 35.0, TRAY["z"] + 6.0, 24)
    m = Manifold.extrude(wall, x1 - x0)
    # (y, z, x) -> (x, y, z)
    m = m.transform([[0, 0, 1, x0], [1, 0, 0, 0], [0, 1, 0, 0]])
    return m


# ================================================================= PI-BRETT (verdenskoordinater direkte)
def pi_tray():
    t = TRAY
    x0 = WALL_X[1]
    plate = Manifold.cube([t["x1"] - x0, t["y1"] - t["y0"], t["t"]]).translate([x0, t["y0"], t["z"]])
    lip = Manifold.cube([2.4, t["y1"] - t["y0"], 12.0]).translate([x0, t["y0"], t["z"]])
    m = plate + lip
    for yy in (0.0, 35.0):
        m = m - Manifold.cylinder(6, 1.3, 1.3, 24).rotate([0, 90, 0]).translate([x0 - 1, yy, t["z"] + 6.0])
    # ribber ned mot skallets bunn (følger bunnkonturen)
    for yy in (t["y0"] + 2, t["y1"] - 4):
        pts = [[x, -zat(IN, x, -1) + 0.4] for x in np.arange(x0, t["x1"] + 0.01, 4.0)]
        pts += [[t["x1"], t["z"] + 0.5], [x0, t["z"] + 0.5]]
        rib = Manifold.extrude(CrossSection([pts], FillRule.EvenOdd), 2.0)
        rib = rib.transform([[1, 0, 0, 0], [0, 0, 1, yy], [0, 1, 0, 0]])
        m = m + rib
    # Pi-stolper (M2,5)
    for hx, hy in PI["holes"]:
        x, y = PI["x0"] + hx, PI["y0"] + hy
        m = m + cyl(5.5, t["boss_h"], x, y, t["z"] + t["t"]) - cyl(2.2, t["boss_h"] + t["t"] + 1, x, y, t["z"] - 0.5)
    return m


# ================================================================= KNOTT OG BEIN
def knob():
    r, h = KNOB["d"] / 2, KNOB["h"]
    prof = [[0, 0.6], [r - 0.5, 0.6], [r, 1.2], [r, h - 1.4], [r - 0.8, h - 0.4], [r - 2.4, h], [0, h]]
    body = Manifold.revolve(CrossSection([prof], FillRule.EvenOdd), 128)
    ribs = []
    for i in range(40):
        a = 360 * i / 40
        ribs.append(Manifold.cube([1.2, 1.2, 9.0], True).rotate([0, 0, 45]).translate([r + 0.25, 0, 1.6 + 4.5 + 2]).rotate([0, 0, a]))
    body = body - union(ribs)
    body = body - cyl(KNOB["shaft"], KNOB["depth"], 0, 0, -0.01, n=48) - cyl(KNOB["shaft"] + 1.2, 0.8, 0, 0, -0.01, KNOB["shaft"], n=48)
    body = body - Manifold.cube([1.2, 5.0, 0.8], True).translate([0, r - 5.0, h - 0.4])     # markør i toppen
    return body   # trykkes på med åpningen ned; print med toppen ned


def leg():
    L, tilt = 24.0, 8.0
    c = Manifold.cylinder(L + 6, 2.6, 4.2, 48).translate([0, 0, -3]).rotate([0, -tilt, 0])
    c = c.trim_by_plane([0, 0, 1], 0.0).trim_by_plane([0, 0, -1], -L)    # 0 … L, horisontal topp og fot
    return c - cyl(4.0, 6.0, 0, 0, L - 6.0 + 0.01, n=32)                 # M3 varmeinnsats i toppen


# ================================================================= EKSPORT
def save(m, name, R=None, t=None):
    mesh = m.to_mesh()
    v = np.array(mesh.vert_properties)[:, :3]
    f = np.array(mesh.tri_verts)
    if R is not None:
        v = v @ np.array(R, float).T
        if np.linalg.det(np.array(R, float)) < 0:
            f = f[:, ::-1]
    v = v - [v[:, 0].mean(), v[:, 1].mean(), v[:, 2].min()] if t is None else v
    import trimesh
    tm = trimesh.Trimesh(v, f, process=False)
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name + ".stl")
    tm.export(p)
    bb = tm.bounds
    print(f"{name}.stl  {len(f)} tri  {bb[1][0]-bb[0][0]:.1f} × {bb[1][1]-bb[0][1]:.1f} × {bb[1][2]-bb[0][2]:.1f} mm  vanntett={tm.is_watertight}")
    return tm


def to_world(m, kind):
    """Lokale deler -> skallets koordinater (for forhåndsvisning)."""
    mesh = m.to_mesh()
    v = np.array(mesh.vert_properties)[:, :3].copy()
    f = np.array(mesh.tri_verts)
    if kind == "face":       # (x, z, Z) -> (x, FPY + Z, z)  (speiling -> snu trekantene)
        v = np.c_[v[:, 0], FPY + v[:, 2], v[:, 1]]; f = f[:, ::-1]
    elif kind == "grill":    # Z mot fronten (ekte rotasjon)
        v = np.c_[v[:, 0], FPY - v[:, 2], v[:, 1]]
    elif kind == "back":
        v = np.c_[v[:, 0], BACK["y0"] + v[:, 2], v[:, 1]]; f = f[:, ::-1]
    import trimesh
    return trimesh.Trimesh(v, f, process=False)


if __name__ == "__main__":
    import trimesh
    fp, spk_boss = faceplate()
    caps = {f"tast_{i+1}": keycap(label=str(i + 1)) for i in range(6)}
    caps.update({"tast_source": keycap(icon="source"), "tast_forrige": keycap(icon="prev"), "tast_neste": keycap(icon="next")})
    gr = grill()
    bp = backplate()
    dv = divider()
    tr = pi_tray()
    kn = knob()
    lg = leg()

    # utskriftsretning: forsiden ned på faceplate/taster/grill-kant; bakplaten innsiden ned
    MY = [[1, 0, 0], [0, -1, 0], [0, 0, 1]]       # lokale (x, z)-deler er speilet: speil tilbake -> ekte del, forsiden ned
    save(fp, "faceplate", R=MY)
    for n, c in caps.items():
        save(c, n, R=MY)
    save(gr, "grill")                             # kuppel opp (trenger støtte under kuppelen)
    save(bp, "bakplate", R=[[1, 0, 0], [0, 1, 0], [0, 0, -1]])   # utsiden (med tekst) ned
    save(dv, "skillevegg", R=[[0, 0, 1], [0, 1, 0], [-1, 0, 0]])   # flat på bordet
    save(tr, "pi_brett", R=[[0, 0, -1], [0, 1, 0], [1, 0, 0]])   # stående på leppen
    save(kn, "volumknott", R=[[1, 0, 0], [0, -1, 0], [0, 0, -1]])  # toppen ned
    save(lg, "bein_x4")
    save(tft_clamp(), "tft_klemme_x4")
    save(spk_clamp(), "hoyttaler_klemme_x4")

    # --------- forhåndsvisning (GLB) i skallets koordinater
    C = dict(skall="#D9A21B", grill="#DCCBA0", face="#5B4636", cap="#EFE6D0", alu="#D4D3CE", inner="#3a3a3c", pcb="#1f6b3a", tft="#c0392b", glass="#0b0c0e")
    sc = trimesh.Scene()

    def add(tm, col, name):
        tm.visual.face_colors = trimesh.visual.color.hex_to_rgba(col)
        sc.add_geometry(tm, node_name=name)

    shell = trimesh.load(os.path.join(HERE, "handoff", "retro", "deep.stl"))
    add(shell, C["skall"], "skall")
    add(to_world(fp, "face"), C["face"], "faceplate")
    add(to_world(gr, "grill"), C["grill"], "grill")
    add(to_world(bp, "back"), C["face"], "bakplate")
    add(trimesh.Trimesh(np.array(dv.to_mesh().vert_properties)[:, :3], np.array(dv.to_mesh().tri_verts)), C["inner"], "skillevegg")
    add(trimesh.Trimesh(np.array(tr.to_mesh().vert_properties)[:, :3], np.array(tr.to_mesh().tri_verts)), C["inner"], "pi_brett")
    for (n, c), (x, z) in zip(caps.items(), FAV + [(b[1], b[2]) for b in BTN2]):
        add(to_world(c.translate([x, z, -CAP_OUT]), "face"), C["cap"], n)
    k = kn.rotate([180, 0, 0]).translate([ENC["x"], ENC["z"], -0.6])
    add(to_world(k, "face"), C["alu"], "knott")
    for sx in (-1, 1):
        for sy in (-1, 1):
            l = lg.rotate([0, 0, 0 if sx > 0 else 180])
            l = l.translate([sx * 82, sy * 28, -zat(IN, sx * 82, -1) - 6.0 - 24.0])
            add(trimesh.Trimesh(np.array(l.to_mesh().vert_properties)[:, :3], np.array(l.to_mesh().tri_verts)), C["alu"], f"bein_{sx}_{sy}")
    # innmat (enkle klosser): TFT, hullkort, Pi, høyttaler, forsterker
    def box(x0, x1, y0, y1, z0, z1, col, name):
        add(trimesh.creation.box(extents=[x1 - x0, y1 - y0, z1 - z0], transform=trimesh.transformations.translation_matrix([(x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2])), col, name)
    gx = DISP["x"] + GLASS["dx"]
    yb = FPY + FT
    box(gx - GLASS["w"] / 2, gx + GLASS["w"] / 2, yb, yb + GLASS["t"], DISP["z"] - GLASS["h"] / 2, DISP["z"] + GLASS["h"] / 2, C["glass"], "tft_glass")
    box(gx - GLASS["w"] / 2 - TFT_PCB["left"], gx - GLASS["w"] / 2 - TFT_PCB["left"] + TFT_PCB["w"], yb + GLASS["t"], yb + GLASS["t"] + 1.6, DISP["z"] - 25, DISP["z"] + 25, C["tft"], "tft_kort")
    box(PROTO["x0"], PROTO["x1"], yb + BOARD_GAP, yb + BOARD_GAP + 1.6, PROTO["z0"], PROTO["z1"], C["pcb"], "hullkort")
    pz = TRAY["z"] + TRAY["t"] + TRAY["boss_h"]
    box(PI["x0"], PI["x0"] + PI["w"], PI["y0"], PI["y0"] + PI["d"], pz, pz + 1.6, C["pcb"], "pi4")
    box(PI["x0"] + 66, PI["x0"] + 87, PI["y0"] + 2, PI["y0"] + 54, pz + 1.6, pz + 17.6, C["alu"], "pi4_usb_eth")
    box(WALL_X[1], WALL_X[1] + 12, 14, 38, 8, 30, "#1d4fa0", "pam8406")
    spk = trimesh.creation.cylinder(radius=SPK["frame"] / 2 - 6, height=36, sections=48)
    spk.apply_transform(trimesh.transformations.rotation_matrix(math.pi / 2, [1, 0, 0]))
    spk.apply_translation([SPK["x"], yb + 18, SPK["z"]])
    add(spk, "#222222", "hoyttaler")
    glb = os.path.join(HERE, "radio_montert.glb")
    sc.export(glb)
    print("->", glb)
