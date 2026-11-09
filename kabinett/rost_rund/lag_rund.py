#!/usr/bin/env python3
"""Bygg Skjold Røst Rund: STL-er (stl/ i utskriftsretning, stl_asm/ montert), grillhylsa, kontroll og K2-plater.

    python3 lag_rund.py            (krever openscad, trimesh og manifold3d)

Hylsa (grillen hele veien rundt) lages her med manifold3d: rundt 2400 sekskanthull er for tungt for OpenSCAD.
Hullene står med en spiss opp (sidene 30° fra loddrett), så hylsa printes stående uten støtte. Nederst er et helt
bånd med SKJOLD i gull foran, øverst et smalt bånd, og bak nede en spiss utsparing rundt DC og USB-C.
Kontroll: tette deler, ingen overlapp i montert stilling, overheng ≤ 50° på yttersidene, plass på K2 (250 × 250),
lydkammerets volum og porttuning."""
import math
import os
import re
import subprocess
import sys
import zipfile

import numpy as np
import trimesh
import manifold3d as mf

HER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HER)
SC = "skjold_rost_rund.scad"
src = open(SC).read()


def tall(navn):
    m = re.search(rf"(?:^|[;\s]){navn}\s*=\s*([-\d.]+)", src, re.M)
    return float(m.group(1))


W, Dp, R, H = tall("W"), tall("Dp"), tall("R"), tall("H")
bpT, capT, sl, sg, t = tall("bpT"), tall("capT"), tall("sl"), tall("sg"), tall("t")
z0, z1 = bpT, H - capT
ioX, ioW, ioH = tall("ioX"), tall("ioW"), tall("ioH")
portD, portL = tall("portD"), tall("portL")
os.makedirs("stl", exist_ok=True); os.makedirs("stl_asm", exist_ok=True)


def scad(part, ut):
    subprocess.run(["openscad", "-q", "-D", f'part="{part}"', "-o", ut, SC], check=True)


# ---------- 1. OpenSCAD-delene ----------
procs = []
for p in ("kjerne", "bunn", "lokk", "knott", "knapp", "rute", "elementplate"):
    procs.append(subprocess.Popen(["openscad", "-q", "-D", f'part="{p}"', "-o", f"stl/{p}.stl", SC]))
for p in ("kjerne", "bunn", "lokk", "knott", "knapp", "logo", "stenger", "rute", "skjerm", "skjermflate", "element", "knappekort", "ec11", "elementplate"):
    procs.append(subprocess.Popen(["openscad", "-q", "-D", f'part="a_{p}"', "-o", f"stl_asm/{p}.stl", SC]))
procs.append(subprocess.Popen(["openscad", "-q", "-D", 'part="logo_kutt"', "-o", "stl_asm/logo_kutt.stl", SC]))
for pr in procs:
    assert pr.wait() == 0


# ---------- 2. hylsa ----------
def to_manifold(tm):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(tm.vertices, dtype=np.float32), tri_verts=np.asarray(tm.faces, dtype=np.uint32)))


def to_trimesh(m):
    me = m.to_mesh()
    return trimesh.Trimesh(np.asarray(me.vert_properties)[:, :3], np.asarray(me.tri_verts), process=True)


def rr(w, d, r):
    return mf.CrossSection.square([w - 2 * r, d - 2 * r], center=True).offset(r, mf.JoinType.Round, circular_segments=96)


a, b = W / 2, Dp / 2
rm = R - sl / 2   # midt i veggen
segs = []   # (lengde, funksjon s → (punkt, normal))
def rett(p0, p1, n):
    p0, p1 = np.array(p0, float), np.array(p1, float)
    return (np.linalg.norm(p1 - p0), lambda s, p0=p0, p1=p1, n=n: (p0 + (p1 - p0) * s / np.linalg.norm(p1 - p0), np.array(n, float)))
def bue(c, t0, t1):
    c = np.array(c, float)
    return (math.radians(t1 - t0) * rm, lambda s, c=c, t0=t0: (c + rm * np.array([math.cos(math.radians(t0) + s / rm), math.sin(math.radians(t0) + s / rm)]),
                                                             np.array([math.cos(math.radians(t0) + s / rm), math.sin(math.radians(t0) + s / rm)])))
ym, xm = b - sl / 2, a - sl / 2
segs = [rett((0, -ym), (a - R, -ym), (0, -1)), bue((a - R, -(b - R)), -90, 0), rett((xm, -(b - R)), (xm, b - R), (1, 0)),
        bue((a - R, b - R), 0, 90), rett((a - R, ym), (-(a - R), ym), (0, 1)), bue((-(a - R), b - R), 90, 180),
        rett((-xm, b - R), (-xm, -(b - R)), (-1, 0)), bue((-(a - R), -(b - R)), 180, 270), rett((-(a - R), -ym), (0, -ym), (0, -1))]
P = sum(L for L, _ in segs)
N = int(round(P / 4.5)); pitch = P / N
af = 3.2                                  # sekskantens bredde over flatene
rv = af / math.sqrt(3)                    # radius (til spissen)
band0, band1, row = z0 + 14.5, z1 - 4.5, 3.9


def punkt(s):
    s %= P
    for L, f in segs:
        if s <= L:
            return f(s)
        s -= L
    return segs[-1][1](segs[-1][0])


def i_io(x, z):   # utsparingen bak (med 3 mm kant)
    return abs(x - ioX) < ioW / 2 + 3 and z < z0 + ioH - abs(x - ioX) + 4


hexcs = mf.CrossSection.circle(rv, 6).rotate(90)   # en spiss opp (v-aksen)
prisme = hexcs.extrude(sl + 3).translate([0, 0, -(sl + 3) / 2])
hull_ = []
nrow = int((band1 - band0) / row)
for j in range(nrow + 1):
    z = band0 + j * row
    for i in range(N):
        s = (i + 0.5 * (j % 2)) * pitch
        p, n = punkt(s)
        if n[1] > 0.5 and i_io(p[0], z):
            continue
        tng = np.array([-n[1], n[0], 0.0]); up = np.array([0, 0, 1.0]); nn = np.array([n[0], n[1], 0.0])
        M = np.column_stack([tng, up, nn, [p[0], p[1], z]])
        hull_.append(prisme.transform(M))
hylse = rr(W, Dp, R).extrude(z1 - z0).translate([0, 0, z0]) - rr(W - 2 * sl, Dp - 2 * sl, R - sl).extrude(z1 - z0 + 2).translate([0, 0, z0 - 1])
hylse = hylse - mf.Manifold.batch_boolean(hull_, mf.OpType.Add)
# utsparingen bak: rektangel + 45° tak (spiss), gjennom bakveggen
io2d = mf.CrossSection([[[-ioW / 2, -1], [ioW / 2, -1], [ioW / 2, ioH - ioW / 2], [0, ioH], [-ioW / 2, ioH - ioW / 2]]])
io3d = io2d.extrude(12).transform(np.array([[1, 0, 0, ioX], [0, 0, -1, b + 2], [0, 1, 0, z0], ], float))
hylse = hylse - io3d
logo_kutt = to_manifold(trimesh.load("stl_asm/logo_kutt.stl"))
hylse = hylse - logo_kutt
hm = to_trimesh(hylse)
hm.export("stl_asm/hylse.stl")
hm.copy().apply_translation([0, 0, -z0]).export("stl/hylse.stl")
trimesh.load("stl_asm/logo.stl").apply_translation([0, 0, -z0]).export("stl/logo.stl")
print(f"hylse: {len(hull_)} hull ({N} rundt × {nrow + 1} rader), {hm.volume / 1000:.1f} cm³")

# ---------- 3. kontroll ----------
ok = True
def meld(god, tekst):
    global ok
    ok &= bool(god); print(("OK   " if god else "FEIL ") + tekst)

DELER = ["kjerne", "bunn", "lokk", "knott", "knapp", "hylse", "logo", "rute", "elementplate"]
FLERE = {"knapp": 5, "logo": None}
for n in DELER:
    m = trimesh.load(f"stl/{n}.stl")
    k = len(m.split(only_watertight=False))
    god = m.is_watertight and (k == 1 or (n in FLERE and (FLERE[n] is None or k == FLERE[n]))) and (abs(m.bounds[0][2]) < 0.05 or n == "logo") \
        and m.extents[0] <= 250 and m.extents[1] <= 250 and m.extents[2] <= 250
    meld(god, f"{n:7s} tett={m.is_watertight} deler={k} {m.volume / 1000:6.1f} cm³ {m.extents.round(1)} mm")

A = {n: trimesh.load(f"stl_asm/{n}.stl") for n in ("kjerne", "bunn", "lokk", "knott", "knapp", "hylse", "logo", "rute", "skjerm", "element", "knappekort", "ec11", "elementplate")}
LOV = {("kjerne", "bunn"), ("kjerne", "lokk"), ("bunn", "hylse"), ("lokk", "hylse"), ("lokk", "knapp"), ("hylse", "logo"), ("lokk", "knott"),
       ("lokk", "rute"), ("lokk", "skjerm"), ("lokk", "knappekort"), ("lokk", "ec11"), ("knapp", "knappekort"), ("knott", "ec11"), ("kjerne", "elementplate"), ("elementplate", "element")}
import itertools
feil = []
for x, y in itertools.combinations(A, 2):
    if (x, y) in LOV or (y, x) in LOV:
        continue
    ax, ay = A[x].bounds, A[y].bounds
    if np.any(ax[1] < ay[0]) or np.any(ay[1] < ax[0]):
        continue
    try:
        v = A[x].intersection(A[y], engine="manifold").volume
    except Exception:
        v = 0
    if v > 0.05:
        feil.append(f"{x}×{y} {v:.2f} mm³")
for x, y in LOV:   # kontaktpar: bare berøring
    try:
        v = A[x].intersection(A[y], engine="manifold").volume
    except Exception:
        v = 0
    if v > 1.0:
        feil.append(f"{x}×{y} {v:.2f} mm³ (skal bare ligge an)")
meld(not feil, "ingen overlapp i montert stilling" + ("" if not feil else ": " + "; ".join(feil)))

for n in ("kjerne", "hylse", "bunn", "lokk"):
    m = trimesh.load(f"stl/{n}.stl")
    c, nn, ar = m.triangles_center, m.face_normals, m.area_faces
    ytre = np.abs(trimesh.proximity.signed_distance(m.convex_hull, c)) < 0.3
    bratt = ytre & (nn[:, 2] < -math.sin(math.radians(50))) & (c[:, 2] > 0.3)
    if n == "hylse":   # bokstavene i logoen er 0,6 mm dype: takene i dem er små broer, ikke overheng
        lb = trimesh.load("stl/logo.stl").bounds
        bratt &= ~np.all((c > lb[0] - 0.5) & (c < lb[1] + 0.5), axis=1)
        bratt &= ar > 0.1   # og der de rette hullene skjærer den buede veggen blir det fliser på ~0,02 mm² (under én linje)
    meld(ar[bratt].sum() < 1.0, f"{n}: {ar[bratt].sum():.1f} mm² overheng brattere enn 50° på yttersiden")

# lydkammeret: luft innenfor kjernen, minus frontblokk, tårn, port, krage
inner = rr(W - 2 * (sl + sg + t), Dp - 2 * (sl + sg + t), R - (sl + sg + t)).extrude(z1 - z0).translate([0, 0, z0])
luft = inner - to_manifold(A["kjerne"]) - to_manifold(A["bunn"]) - to_manifold(A["lokk"])
V = luft.volume() / 1e6
netto = V - 0.05 - 0.05            # element ca. 50 cm³, elektronikk og knappekort ca. 50 cm³
Sp = math.pi * (portD / 2000) ** 2
Leff = portL / 1000 + 0.85 * (portD / 2000) * 2 * 0.85
fb = 343 / (2 * math.pi) * math.sqrt(Sp / (netto / 1000 * Leff))
meld(0.85 <= netto <= 1.4 and 65 <= fb <= 95, f"lydkammer: {V:.2f} l luft, ca. {netto:.2f} l netto, port Ø{portD:.0f} × {portL:.0f} mm → fb ≈ {fb:.0f} Hz")
print("ALT OK" if ok else "NOE FEILET")

# ---------- 4. K2-plater ----------
sys.path.insert(0, os.path.join(HER, "..", "fjernkontroll"))
import lag_3mf as L   # noqa: E402
L.STL = "stl"
# Utskriftsinnstillinger som objektinnstillinger i 3MF-en (Creality Print / OrcaSlicer leser model_settings.config):
# lokket printes med toppen ned (ingen støtte trengs: alt under lokket peker opp, vinduets fas er 45°, glasslomma er åpen
# oppover); sakte første lag og elefantfot-kompensasjon gir skarpe kanter rundt rutas forsenkning og knappehullene.
# Ruta printes i klar PETG med 100 % fyll og bare én vegg (klarest), sakte.
L.OBJ_INNST = {
    "lokk": {"enable_support": "0", "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.15"},
    "rute": {"enable_support": "0", "sparse_infill_density": "100%", "wall_loops": "1", "top_shell_layers": "0", "bottom_shell_layers": "0",
             "initial_layer_speed": "15", "outer_wall_speed": "30", "inner_wall_speed": "30", "sparse_infill_speed": "30"},
    "kjerne": {"enable_support": "0"}, "elementplate": {"enable_support": "0"}, "hylse": {"enable_support": "0", "outer_wall_speed": "120"}, "bunn": {"enable_support": "0"},
}
L.write("skjold-rost-rund-k2-kjerne.3mf", "Skjold Røst Rund – kjerne, knapper og knott", [
    ("kjerne", "Kjerne (mørk, stående)", 2, (10, 10), None),
    ("knapp", "Knappehetter (mørke, toppen ned)", 2, (130, 118), None),
    ("knott", "Knott (gull, toppen ned)", 3, (130, 138), None),
    ("elementplate", "Elementplate med krage (mørk, baksiden ned) – lag ny for et annet element", 2, (130, 10), None)], {2: "#232325", 3: "#D99E40"})
L.write("skjold-rost-rund-k2-hylse.3mf", "Skjold Røst Rund – grillhylse med SKJOLD i gull", [
    ("hylse", "Grillhylse (lys, stående)", 1, (70, 70), None),
    ("logo", "SKJOLD (gull, innfelt i hylsa)", 3, None, "hylse")], {1: "#ECE9E3", 3: "#D99E40"})
L.write("skjold-rost-rund-k2-lokk-bunn.3mf", "Skjold Røst Rund – lokk med skjerm, rute og bunnplate", [
    ("lokk", "Lokk med skjermramme (lys, toppen ned)", 1, (10, 10), None),
    ("bunn", "Bunnplate med port (lys)", 1, (130, 10), None),
    ("rute", "Rute over skjermen (klar PETG, 100 % fyll)", 4, (20, 120), None)], {1: "#ECE9E3", 4: "#DDE6EA"})
# elementplater for alle elementene i malen (kabinett/elementer/elementer.scad), på én plate
EL = ["rs75_4", "frs8_4", "grs3fr4", "faital3fe22"]
procs = [subprocess.Popen(["openscad", "-q", "-D", 'part="elementplate"', "-D", f'element="{e}"', "-o", f"stl/elementplate_{e}.stl", SC]) for e in EL]
for pr in procs:
    assert pr.wait() == 0
L.OBJ_INNST = {f"elementplate_{e}": {"enable_support": "0"} for e in EL}
L.write("skjold-rost-rund-k2-elementplater.3mf", "Skjold Røst Rund – elementplater med krage (velg den som passer elementet ditt)", [
    (f"elementplate_{e}", f"Elementplate {e} (mørk, baksiden ned)", 2, ((10, 130)[i % 2], (10, 125)[i // 2]), None)
    for i, e in enumerate(EL)], {2: "#232325"})
sys.exit(0 if ok else 1)
