"""Kontroll av Skjold Radio-modellen.

Bruk:  python3 sjekk_modell.py [mappe med A_*.stl i montert stilling]   (standard: asm/)
STL-ene lages med  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_radio.scad  og  -D 'part="A_kropp"' -o asm/kropp.stl
(se lag_stl.sh). Krever trimesh og manifold3d. Sjekker:
  1. alle utskrifts-STL-er i stl/ er vanntette, ett legeme (knapp: sju hetter), ligger på platen (min z = 0)
     og passer i Creality K2 (250 × 250 × 250 mm)
  2. ingen deler overlapper i montert stilling (par som skal ligge an mot hverandre har bare kontaktflater)
  3. lydkammeret er tett: hver halvdel er et lukket rom når lokket er på (bare de to kabelhullene i gulvet er åpne)
  4. kroppens yttervegg er hel (≥ 2 mm) utenom de tiltenkte hullene, og netto kammervolum per side"""
import itertools
import sys

import numpy as np
import trimesh

ASM = sys.argv[1] if len(sys.argv) > 1 else "asm"
ok = True
PRINT = ["kropp", "kammer", "lokk", "grill", "bunn", "brakett", "knott", "volum", "knapp"]
for n in PRINT:
    m = trimesh.load(f"stl/{n}.stl")
    parts = len(m.split(only_watertight=False))
    good = m.is_watertight and m.is_volume and parts == (7 if n == "knapp" else 1) \
        and abs(m.bounds[0][2]) < 0.02 and max(m.extents) <= 250
    ok &= good
    print(f"{'OK ' if good else 'FEIL'} {n:9s} vanntett={m.is_watertight} deler={parts} {m.volume/1000:7.1f} cm³ "
          f"{m.extents.round(1)} mm")

ASMP = ["kropp", "kammer", "lokk", "grill", "bunn", "brakett", "knapper", "knott", "volum"]
A = {n: trimesh.load(f"{ASM}/{n}.stl") for n in ASMP}
TOUCH = {("kropp", "bunn"), ("kammer", "bunn"), ("kammer", "lokk"), ("kropp", "brakett")}


def overlap(a, b):
    if np.any(a.bounds[1] < b.bounds[0]) or np.any(b.bounds[1] < a.bounds[0]):
        return 0.0
    try:
        return a.intersection(b, engine="manifold").volume
    except Exception:
        return float("nan")


olap = []
for x, y in itertools.combinations(ASMP, 2):
    v = overlap(A[x], A[y])
    lim = 0.05 if (x, y) in TOUCH or (y, x) in TOUCH else 0.001
    if not v <= lim:
        olap.append(f"{x} × {y}: {v:.3f} mm³")
ok &= not olap
print("OK  ingen overlapp i montert stilling" if not olap else "FEIL overlapp: " + "; ".join(olap))

# --- lydkammeret: luft inne i hver halvdel, avgrenset av kammer + lokk (+ bunnplata under kabelhullene) ---
W, D, kX0, kY0, kD, kH, kT, baffT = 236, 152, 22, 8.6, 78, 88, 2.8, 7
box = A["kammer"].union(A["lokk"], engine="manifold")
for s in (-1, 1):   # elementene tetter utsparingene i baffelen
    el = trimesh.creation.cylinder(radius=43, height=4, sections=64)
    el.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
    el.apply_translation([W/2 + s*52, kY0 - 2, kH/2])
    box = box.union(el, engine="manifold")
tot = 0
for side, (x0, x1) in {"venstre": (kX0 + kT, W/2 - kT/2), "høyre": (W/2 + kT/2, W - kX0 - kT)}.items():
    inner = trimesh.creation.box(extents=[x1 - x0 - 0.02, kD - baffT - 0.02, kH - 2*kT - 0.02])
    inner.apply_translation([(x0 + x1)/2, kY0 + baffT + (kD - baffT)/2, kH/2])
    air = inner.difference(box, engine="manifold")
    drv = 0.05e6   # elementets magnet/kurv bak baffelen ≈ 0,05 l
    vol = (air.volume - drv) / 1e6
    tot += vol
    # tetthet: stråler fra luftrommets midte i 26 retninger skal alle treffe kammer/lokk
    c = np.array([(x0 + x1)/2, kY0 + baffT + (kD - baffT)/2, kH/2])
    dirs = np.array([d for d in itertools.product([-1, 0, 1], repeat=3) if any(d)], float)
    hits = box.ray.intersects_any(np.repeat([c], len(dirs), 0), dirs)
    good = hits.all() and 0.40 < vol < 0.60
    ok &= good
    print(f"{'OK ' if good else 'FEIL'} kammer {side}: netto ≈ {vol:.2f} l, lukket i alle {hits.sum()}/{len(dirs)} retninger")

# --- yttervegg ≥ 2 mm: stråler inn fra sidene og bak ---
k = A["kropp"]
HOLES = [("bak", 40, 26, 5), ("bak", 62, 26, 4), ("bak", 82, 26, 6.5)] + \
        [("bak", 128 + i*10, z, 3.5) for i in range(8) for z in range(12, 47, 2)] + [("side+", 72, 52, 4.5)]


def wall(o, d):
    loc, _, _ = k.ray.intersects_location([o], [d])
    if len(loc) < 2:
        return 0.0
    s = sorted(np.linalg.norm(loc - np.array(o), axis=1))
    return s[1] - s[0]


bad = []
for face, us, vs in [("side+", np.arange(20, D - 20, 4), np.arange(-2, 96, 4)), ("side-", np.arange(20, D - 20, 4), np.arange(-2, 96, 4)),
                     ("bak", np.arange(20, W - 20, 4), np.arange(-2, 120, 4))]:
    for u in us:
        for v in vs:
            if any(f == face and np.hypot(u - a, v - b) < r for f, a, b, r in HOLES):
                continue
            o, d = ([W + 5, u, v], [-1, 0, 0]) if face == "side+" else ([-5, u, v], [1, 0, 0]) if face == "side-" else ([u, D + 5, v], [0, -1, 0])
            w = wall(o, d)
            if w < 1.99:
                bad.append((face, float(u), float(v), round(w, 2)))
if bad:
    ok = False
    print(f"FEIL yttervegg tynnere enn 2 mm på {len(bad)} punkter, f.eks. {bad[:6]}")
else:
    print("OK  yttervegg ≥ 2 mm på sidene og bak utenom tiltenkte hull")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
