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
BRIM = {"brim_type": "outer_only", "brim_width": "5", "brim_object_gap": "0", "initial_layer_speed": "25", "initial_layer_infill_speed": "30"}
L.OBJ_INNST = {
    # lokket: trestøtte (bare fra plata) under skjermramme og krage, 6 mm brim og store museører, så det står trygt
    "lokk": {"enable_support": "1", "support_type": "tree(auto)", "support_on_build_plate_only": "1", "support_threshold_angle": "40",
             "support_top_z_distance": "0.2", "support_object_xy_distance": "0.5",
             "brim_type": "outer_only", "brim_width": "6", "brim_object_gap": "0",
             "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.15"},
    "rute": {"enable_support": "0", "sparse_infill_density": "100%", "wall_loops": "1", "top_shell_layers": "0", "bottom_shell_layers": "0",
             "initial_layer_speed": "15", "outer_wall_speed": "30", "inner_wall_speed": "30", "sparse_infill_speed": "30"},
    # kjernen og hylsa er 140 mm høye med tynne vegger (ca. 1 080 og 620 mm² mot plata): 5 mm brim og sakte første lag
    "kjerne": {"enable_support": "0", **BRIM}, "elementplate": {"enable_support": "0"},
    # hylsa: 2 667 små hull blir «små omkretser» som sliceren ellers printer på halv fart. Full fart på dem, to vegger
    # (1,8 mm vegg = 4 linjer, helt fylt) og 0,24 mm lag kutter tiden kraftig uten å endre utseendet nevneverdig.
    "hylse": {"enable_support": "0", "layer_height": "0.24", "wall_loops": "2", "small_perimeter_speed": "100%",
              "outer_wall_speed": "150", "inner_wall_speed": "250", "wall_generator": "arachne", **BRIM},
    "bunn": {"enable_support": "0", "brim_type": "outer_only", "brim_width": "6", "brim_object_gap": "0"},
}
# museører (som på fjernkontrollen): tynne skiver langs kanten av lokket og bunnplata, som holder hjørnene nede på
# plata. Ø24 i de avrundede hjørnene (som løfter seg mest), Ø16 midt på sidene, 0,6 mm (3 lag). Vris av etter print.
def orer(navn, r_hj=12.0, r_side=8.0, h=0.6, bare_ute=False):
    # I 2D (shapely): sirkler langs kanten, minus delens fotavtrykk og (som før) alt mer enn 3 mm inn fra kanten, så
    # skivene ikke fyller fotlommer eller hull. Deretter løftet til h. Gir et rent, lukket volum også når skivene er
    # store og overlapper hverandre (en 3D-boolean med delen gav flater i samme plan og ødelagt nett).
    from shapely.geometry import MultiPoint, Point
    from shapely.ops import unary_union
    m = trimesh.load(f"stl/{navn}.stl")
    snitt = m.section(plane_origin=[0, 0, 0.1], plane_normal=[0, 0, 1])
    pts = snitt.vertices[:, :2]
    c = (pts.max(0) + pts.min(0)) / 2
    fot = []   # delens fotavtrykk gjennom hele ørehøyden (avrundede kanter blir bredere oppover)
    for z in np.linspace(0.05, h + 0.1, 8):
        sn = m.section(plane_origin=[0, 0, z], plane_normal=[0, 0, 1])
        if sn is not None:
            fot += list(sn.to_2D(to_2D=np.eye(4))[0].polygons_full)
    fot = unary_union(fot).buffer(0.05)
    disker = []
    for a in range(0, 360, 45):
        u = np.array([np.cos(np.radians(a)), np.sin(np.radians(a))])
        p = pts[np.argmax((pts - c) @ u)]              # ytterste punkt på kanten i den retningen
        disker.append(Point(p[0], p[1]).buffer(r_hj if a % 90 else r_side, 96))
    inni = MultiPoint(pts).convex_hull.buffer(-0.01 if bare_ute else -3)
    form = unary_union(disker).difference(fot).difference(inni)
    deler = [g for g in getattr(form, "geoms", [form]) if g.area > 1.0]   # bort med smuler
    o = trimesh.util.concatenate([trimesh.creation.extrude_polygon(g, h) for g in deler])
    assert o.is_volume, f"{navn}_orer er ikke et lukket volum"
    o.export(f"stl/{navn}_orer.stl")
for n in ("lokk", "bunn"):
    orer(n, r_hj=18.0, r_side=12.0)   # store ører (Ø36 i hjørnene, Ø24 på sidene) i tillegg til brim
orer("hylse", bare_ute=True)   # 140 mm høy med tynn vegg: museører i tillegg til brim
L.write("skjold-rost-rund-k2-kjerne.3mf", "Skjold Røst Rund – kjerne, knapper og knott", [
    ("kjerne", "Kjerne (mørk, stående)", 2, (10, 10), None),
    ("knapp", "Knappehetter (mørke, toppen ned)", 2, (130, 118), None),
    ("knott", "Knott (gull, toppen ned)", 3, (130, 138), None),
    ("elementplate", "Elementplate med krage (mørk, baksiden ned) – lag ny for et annet element", 2, (130, 10), None)], {2: "#232325", 3: "#D99E40"})
L.write("skjold-rost-rund-k2-hylse.3mf", "Skjold Røst Rund – grillhylse med SKJOLD i gull", [
    ("hylse", "Grillhylse (lys, stående)", 1, (70, 70), None),
    ("hylse_orer", "Museører til hylsa (vris av etter print)", 1, None, "hylse"),
    ("logo", "SKJOLD (gull, innfelt i hylsa)", 3, None, "hylse")], {1: "#ECE9E3", 3: "#D99E40"})
# uten gull: én farge, ingen fargebytter (SKJOLD står felt inn 1 mm; kan males med gulltusj etterpå)
L.write("skjold-rost-rund-k2-hylse-en-farge.3mf", "Skjold Røst Rund – grillhylse i én farge (SKJOLD felt inn)", [
    ("hylse", "Grillhylse (én farge, stående)", 1, (70, 70), None),
    ("hylse_orer", "Museører til hylsa (vris av etter print)", 1, None, "hylse")], {1: "#ECE9E3"})
L.write("skjold-rost-rund-k2-lokk-bunn.3mf", "Skjold Røst Rund – lokk med skjerm, rute og bunnplate", [
    ("lokk", "Lokk med skjermramme (lys, toppen ned)", 1, (10, 10), None),
    ("lokk_orer", "Museører til lokket (vris av etter print)", 1, None, "lokk"),
    ("bunn", "Bunnplate med port (lys)", 1, (130, 130), None),
    ("bunn_orer", "Museører til bunnplata (vris av etter print)", 1, None, "bunn"),
    ("rute", "Rute over skjermen (klar PETG, 100 % fyll)", 4, (14, 160), None)], {1: "#ECE9E3", 4: "#DDE6EA"})
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
