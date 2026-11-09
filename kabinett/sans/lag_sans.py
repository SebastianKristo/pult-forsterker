#!/usr/bin/env python3
"""Bygg Skjold Sans: STL-er (stl/ i utskriftsretning, stl_asm/ montert), kontroll og K2-plate (3MF).

    python3 lag_sans.py            (krever openscad og trimesh; manifold3d for overlappsjekken)

Kontroll: tette deler i ett legeme, ingen overlapp i montert stilling (kjøpte deler inkludert), overheng i
utskriftsretning, plass på K2 (250 × 250)."""
import os
import subprocess
import sys
import warnings

import numpy as np
import trimesh

warnings.filterwarnings("ignore")
HER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HER)
SC = "skjold_sans.scad"
os.makedirs("stl", exist_ok=True); os.makedirs("stl_asm", exist_ok=True)

UTSKRIFT = ["kropp", "logo", "bakplate"]
MONTERT = ["kropp", "logo", "bakplate", "d1", "plugg", "pir", "lys", "sensor"]
procs = [subprocess.Popen(["openscad", "-q", "-D", f'part="{p}"', "-o", f"stl/{p}.stl", SC]) for p in UTSKRIFT]
procs += [subprocess.Popen(["openscad", "-q", "-D", f'part="a_{p}"', "-o", f"stl_asm/{p}.stl", SC]) for p in MONTERT]
for pr in procs:
    assert pr.wait() == 0

ok = True
def meld(god, tekst):
    global ok
    ok &= bool(god)
    print(("OK   " if god else "FEIL ") + tekst)


# 1. tette deler
for p in UTSKRIFT:
    m = trimesh.load(f"stl/{p}.stl")
    n = len(m.split(only_watertight=False))
    meld(m.is_watertight and (n == 1 or p == "logo"), f"{p:9s} tett={m.is_watertight} deler={n} {m.volume / 1000:5.1f} cm³ "
         f"{np.round(m.extents, 1)} mm, ca. {m.volume / 1000 * 1.27 * 0.6:.0f} g PETG (60 % fyll)")

# 2. overlapp i montert stilling (kontaktpar får bare berøre)
A = {p: trimesh.load(f"stl_asm/{p}.stl") for p in MONTERT}
LOV = {("kropp", "logo"), ("bakplate", "d1"), ("d1", "plugg"), ("bakplate", "sensor"), ("kropp", "lys"), ("kropp", "pir")}
feil = []
for i, x in enumerate(MONTERT):
    for y in MONTERT[i + 1:]:
        try:
            v = A[x].intersection(A[y], engine="manifold").volume
        except Exception:
            v = 0
        if v > (1.0 if (x, y) in LOV or (y, x) in LOV else 0.05):
            feil.append(f"{x}×{y} {v:.2f} mm³")
meld(not feil, "ingen overlapp i montert stilling" + ("" if not feil else ": " + "; ".join(feil)))

# 3. overheng i utskriftsretning: flater som peker mer enn 50° nedover (ikke mot plata); broer er greit
for p in ("kropp", "bakplate"):
    m = trimesh.load(f"stl/{p}.stl")
    nz = m.face_normals[:, 2]
    z = m.triangles_center[:, 2]
    ned = (nz < -np.sin(np.radians(50))) & (z > 0.05)   # mer enn 50° fra loddrett
    if p == "kropp":   # taket i gullkantens spor (0,6 mm) fylles av gullkanten i samme utskrift
        ned &= z > 0.65
    flater = m.submesh([np.where(ned)[0]], append=True) if ned.any() else None
    stor = 0.0
    if flater is not None:
        for f in flater.split(only_watertight=False):
            e = np.sort(f.extents[:2])
            flat = f.face_normals[:, 2].max() < -0.99
            if e[0] > (15.0 if flat else 3.0):   # flate broer opp til 15 mm (kabelkanalen) og smale kanter er greit på K2
                stor += f.area
    meld(stor < 1.0, f"{p}: {m.area_faces[ned].sum():.1f} mm² nedovervendt, {stor:.1f} mm² som trenger støtte")

# 4. K2-plata
sys.path.insert(0, os.path.join(HER, "..", "fjernkontroll"))
import lag_3mf as L   # noqa: E402
L.STL = "stl"
BRIM = {"enable_support": "0", "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.15"}
L.OBJ_INNST = {"kropp": BRIM, "bakplate": BRIM}
L.write("skjold-sans-k2.3mf", "Skjold Sans – skjoldformet kropp med gullkant og bakplate (PETG/ASA)", [
    ("kropp", "Kropp (lys, forsiden ned)", 1, (30, 40), None),
    ("logo", "Gullkant (felt inn i forsiden)", 3, None, "kropp"),
    ("bakplate", "Bakplate (lys, baksiden ned)", 1, (120, 40), None)], {1: "#ECE9E3", 3: "#D99E40"})
print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
