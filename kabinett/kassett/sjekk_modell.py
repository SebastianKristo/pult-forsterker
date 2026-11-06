"""Kontroll av Skjold Kassett-modellen: vanntette STL-er og ingen kollisjoner i montert stilling.

Bruk:  python3 sjekk_modell.py <mappe med STL-er i utskriftsretning> <mappe med A_*.stl i montert stilling>
A_*.stl lages med  openscad -D 'part="A_topp"' -o A_topp.stl skjold_kassett.scad  (se dispatch nederst i .scad).
Krever trimesh og manifold3d. Spolene sjekkes i 12 rotasjonsvinkler (de går rundt når musikken spiller)."""
import itertools
import sys

import numpy as np
import trimesh

PRINT, ASM = sys.argv[1], sys.argv[2]
ok = True
for n in ["spiller_topp", "spiller_bunn", "vindu", "lysleder", "trinse", "motortrinse", "kassett_front", "kassett_bak", "spole"]:
    m = trimesh.load(f"{PRINT}/{n}.stl")
    parts = len(m.split(only_watertight=False))
    good = m.is_watertight and m.is_volume and parts == 1
    ok &= good
    print(f"{'OK ' if good else 'FEIL'} {n:14s} vanntett={m.is_watertight} volum={m.is_volume} deler={parts} "
          f"{m.volume/1000:6.1f} cm³  {m.extents.round(1)} mm  min z={m.bounds[0][2]:.2f}")

A = {n: trimesh.load(f"{ASM}/A_{n}.stl") for n in
     ["topp", "bunn", "vindu", "lysleder", "tr0", "tr1", "mt", "kf", "kb", "s0", "s1", "pn", "n20", "oring"]}
# par som skal ligge an mot hverandre (kontaktflater) – sjekkes ikke for overlapp
TOUCH = {("kf", "kb"), ("mt", "n20"), ("oring", "tr0"), ("oring", "tr1"), ("oring", "mt")}


def overlap(a, b):
    if not trimesh.bounds.contains(np.vstack([a.bounds[0] - 0.01, a.bounds[1] + 0.01]), [b.centroid])[0] and \
            np.any(a.bounds[1] < b.bounds[0]) or np.any(b.bounds[1] < a.bounds[0]):
        return 0.0
    try:
        return a.intersection(b, engine="manifold").volume
    except Exception:
        return float("nan")


def check(names, meshes, tag=""):
    global ok
    for x, y in itertools.combinations(names, 2):
        if (x, y) in TOUCH or (y, x) in TOUCH:
            continue
        v = overlap(meshes[x], meshes[y])
        if v > 0.01 or v != v:
            ok = False
            print(f"FEIL overlapp {x}–{y}{tag}: {v:.3f} mm³")


check(list(A), A)
# spolene rundt sin egen akse (y-aksen i verden, gjennom senteret av spolen)
for ang in range(0, 360, 30):
    B = dict(A)
    for s in ("s0", "s1"):
        c = A[s].bounding_box.centroid
        R = trimesh.transformations.rotation_matrix(np.radians(ang), [0, 1, 0], c)
        B[s] = A[s].copy().apply_transform(R)
    check(["s0", "s1", "kf", "kb", "topp", "vindu", "tr0", "tr1"], B, f" ({ang}°)")


def gap(a, b, n=4000):
    pts, _ = trimesh.sample.sample_surface(a, n, seed=1)
    return float(np.min(trimesh.proximity.signed_distance(b, pts) * -1))


print(f"avstand spole–kassett: {min(gap(A['s0'], A['kf']), gap(A['s0'], A['kb'])):.2f} mm,"
      f" kassett–spor: {min(gap(A['kb'], A['topp']), gap(A['kf'], A['topp'])):.2f} mm,"
      f" kassett–rute: {gap(A['kf'], A['vindu']):.2f} mm, trinse–lomme: {gap(A['tr0'], A['topp']):.2f} mm")
print("ALT OK" if ok else "FEIL FUNNET")
sys.exit(0 if ok else 1)
