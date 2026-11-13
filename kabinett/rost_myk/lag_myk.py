#!/usr/bin/env python3
"""Bygg Skjold Røst Myk: STL-er i stl/ og den finmaskede grillen.

    python3 lag_myk.py            (krever openscad, trimesh og manifold3d)

Grillen lages her med manifold3d: rundt 2000 runde hull er for tungt for OpenSCAD. Hullene (Ø1,5 mm) står i
trekantmønster med 2,4 mm mellom, og holder 3 mm avstand til kanten. Skriptet sjekker også at delene er tette og
regner ut omtrent hvor stort lydkammeret er."""
import math
import os
import re
import subprocess

import numpy as np
import trimesh
import manifold3d as mf

HER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HER)
SC = "skjold_rost_myk.scad"
src = open(SC).read()


def tall(navn):
    return float(re.search(rf"(?:^|[;\s]){navn}\s*=\s*([-\d.]+)", src, re.M).group(1))


W, Hh, R, D, t = tall("W"), tall("Hh"), tall("R"), tall("D"), tall("t")
fotH, leppe, grDyp, grT = tall("fotH"), tall("leppe"), tall("grDyp"), tall("grT")
zc, yF = fotH + Hh / 2, -D / 2
HULL, DELING, KANT = 1.5, 2.4, 3.0
os.makedirs("stl", exist_ok=True)


def scad(part):
    subprocess.run(["openscad", "-q", "-D", f'part="{part}"', "-o", f"stl/{part}.stl", SC], check=True)


def til_manifold(m):
    return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))


def fra_manifold(m):
    x = m.to_mesh()
    return trimesh.Trimesh(np.asarray(x.vert_properties)[:, :3], np.asarray(x.tri_verts), process=True)


def inni(x, z, o):
    """Er punktet inne i tverrsnittet (avrundet rektangel) krympet med o?"""
    w, h, r = W / 2 - o, Hh / 2 - o, max(0.1, R - o)
    ax, az = abs(x), abs(z)
    if ax > w or az > h:
        return False
    if ax > w - r and az > h - r:
        return math.hypot(ax - (w - r), az - (h - r)) <= r
    return True


def grill():
    plate = til_manifold(trimesh.load("stl/grill_plate.stl"))
    hull, rad, dz = [], 0, DELING * math.sqrt(3) / 2
    z = -Hh / 2
    while z <= Hh / 2:
        x = -W / 2 + (DELING / 2 if rad % 2 else 0)
        while x <= W / 2:
            if inni(x, z, leppe + 0.25 + KANT + HULL / 2):
                c = mf.Manifold.cylinder(grT + 2, HULL / 2, HULL / 2, 12).rotate([-90, 0, 0]).translate([x, yF + grDyp - 1, zc + z])
                hull.append(c)
            x += DELING
        z += dz; rad += 1
    ut = plate - mf.Manifold.batch_boolean(hull, mf.OpType.Add)
    m = fra_manifold(ut)
    m.export("stl/grill.stl")
    return len(hull), m


if __name__ == "__main__":
    for p in ("kropp", "front", "grill_plate", "knott", "element"):
        scad(p)
    n, g = grill()
    print(f"grill: {n} hull, tett: {g.is_watertight}")
    for p in ("kropp", "front", "knott"):
        m = trimesh.load(f"stl/{p}.stl")
        print(f"{p}: tett {m.is_watertight}, {m.extents.round(1)} mm")
    # lydkammer: innsiden av kroppen bak frontplata, grovt regnet fra tverrsnittet
    areal = (W - 2 * t) * (Hh - 2 * t) - (4 - math.pi) * (R - t) ** 2
    bafY, bakL = yF + grDyp + grT + 6 + 5, tall("bakL")
    rett = (D / 2 - bakL) - bafY
    vol = areal * rett + areal * (bakL - t) * 2 / 3      # bakenden er omtrent en halv ellipsoide
    print(f"lydkammer: ca. {vol / 1e6:.2f} liter før elektronikk og port")
