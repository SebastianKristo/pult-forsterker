"""Kontroll av Skjold Røst-modellen (knappehetter og løs grill).

Bruk:  python3 sjekk_modell.py <mappe med A_*.stl i montert stilling>
A_*.stl lages med  openscad -D 'part="a_kropp"' -o A_kropp.stl skjold_rost.scad  (se dispatch nederst i .scad).
Krever trimesh og manifold3d. Sjekker:
  1. alle utskrifts-STL-er i stl/ er vanntette, ett legeme, ligger på platen (min z = 0) og passer på 250 × 250 mm
  2. ingen deler overlapper i montert stilling (par som skal ligge an mot hverandre har bare kontaktflater)
  3. kroppens yttervegg er hel: stråler inn fra sidene, toppen og baksiden treffer ≥ 1,6 mm materiale overalt,
     bortsett fra de tiltenkte hullene (port, DC, USB, EC11, gravert navn)
  4. kroppen og frontplaten flukter i skjøten (samme ytterkant på begge sider av y = 0)"""
import itertools
import sys

import numpy as np
import trimesh

ASM = sys.argv[1]
ok = True
PRINT = ["kropp", "front", "logo", "grill", "bunn", "knott", "rute", "knapp",
         "pakning_front", "pakning_bunn", "krage", "dc_skive", "usb_propp"]
MULTI = {"logo": None, "knapp": 5}   # logo: flere bokstaver; knapp: fem hetter i én fil
for n in PRINT:
    m = trimesh.load(f"stl/{n}.stl")
    parts = len(m.split(only_watertight=False))
    good = m.is_watertight and m.is_volume and (parts == 1 or (n in MULTI and (MULTI[n] is None or parts == MULTI[n]))) \
        and (abs(m.bounds[0][2]) < 0.02 or n == "logo") \
        and m.extents[0] <= 250 and m.extents[1] <= 250
    ok &= good
    print(f"{'OK ' if good else 'FEIL'} {n:15s} vanntett={m.is_watertight} deler={parts:2d} {m.volume/1000:7.2f} cm³ "
          f"{m.extents.round(1)} mm  min z={m.bounds[0][2]:.2f}")

A = {n: trimesh.load(f"{ASM}/{n}.stl") for n in PRINT}
# par som skal ligge an mot hverandre (bare kontaktflater, sjekkes med liten toleranse)
TOUCH = {("kropp", "front"), ("kropp", "bunn"), ("front", "bunn"), ("front", "logo"),
         ("kropp", "pakning_front"), ("front", "pakning_front"), ("kropp", "pakning_bunn"), ("bunn", "pakning_bunn"),
         ("front", "pakning_bunn"), ("kropp", "rute"), ("kropp", "knapp"), ("kropp", "krage"), ("kropp", "dc_skive"),
         ("kropp", "usb_propp"), ("dc_skive", "usb_propp")}
# grillens tapper har klemribber som skal klemme mot hullene i fronten (tilsiktet presspasning)
PRESS = {("front", "grill"): 6.0}


def overlap(a, b):
    if np.any(a.bounds[1] < b.bounds[0]) or np.any(b.bounds[1] < a.bounds[0]):
        return 0.0
    try:
        return a.intersection(b, engine="manifold").volume
    except Exception:
        return float("nan")


olap = []
for x, y in itertools.combinations(PRINT, 2):
    v = overlap(A[x], A[y])
    lim = PRESS.get((x, y), PRESS.get((y, x), 0.05 if (x, y) in TOUCH or (y, x) in TOUCH else 0.001))
    if not v <= lim:
        olap.append(f"{x} × {y}: {v:.3f} mm³")
ok &= not olap
# skjermmodulen (kjøpt del) skal ligge i lomma uten å kollidere med kroppen
try:
    sk = trimesh.load(f"{ASM}/skjerm.stl")
    v = overlap(A["kropp"], sk)
    if not v <= 0.05:
        olap.append(f"kropp × skjermmodul: {v:.3f} mm³")
except Exception as e:
    print("(skjermmodul ikke sjekket:", e, ")")
print("OK  ingen overlapp i montert stilling" if not olap else "FEIL overlapp: " + "; ".join(olap))

# --- yttervegg ---
k = A["kropp"]
W, D, H, t = 106, 113, 136, 2.6
# (flate, senter u, senter v, radius) – tiltenkte åpninger. Toppen: v ≈ y (toppen heller bare ≈ 2,4°).
HOLES = [("bak", -26, 40, 11.5), ("bak", -25, 13, 4.5), ("bak", 15, 13, 5.6), ("bak", 0, 100, 18),
         ("topp", 0, 88, 6.6), ("topp", 0, 42, 33.0)] + [("topp", x, 10.5, 5.6) for x in (-32, -16, 0, 16, 32)]


def wall(face, u, v):
    if face == "side+":
        o, d = [W/2 + 5, u, v], [-1, 0, 0]
    elif face == "side-":
        o, d = [-W/2 - 5, u, v], [1, 0, 0]
    elif face == "topp":
        o, d = [u, v, H + 5], [0, 0, -1]   # toppen er skrå; strålen treffer overflaten litt lavere foran
    else:
        o, d = [u, D + 5, v], [0, -1, 0]
    loc, _, _ = k.ray.intersects_location([o], [d])
    if len(loc) < 2:
        return 0.0
    s = sorted(np.linalg.norm(loc - o, axis=1))
    return s[1] - s[0]


bad = []
for face, us, vs in [("side+", np.arange(9, D - 13, 3), np.arange(3, H - 4, 3)), ("side-", np.arange(9, D - 13, 3), np.arange(3, H - 4, 3)),
                     ("topp", np.arange(-36, 37, 3), np.arange(9, D - 13, 3)), ("bak", np.arange(-36, 37, 3), np.arange(3, H - 4, 3))]:
    for u in us:
        for v in vs:
            if any(f == face and np.hypot(u - a, v - b) < r for f, a, b, r in HOLES):
                continue
            w = wall(face, u, v)
            if w < 1.59:
                bad.append((face, round(float(u), 1), round(float(v), 1), round(w, 2)))
if bad:
    ok = False
    print(f"FEIL yttervegg tynnere enn 1,6 mm på {len(bad)} punkter, f.eks. {bad[:6]}")
else:
    print("OK  yttervegg ≥ 1,6 mm overalt utenom tiltenkte hull")

# --- skjøten flukter: tverrsnitt av kropp og front like ved y = 0 har samme ytterkant ---
fr = A["front"]
for z in [20, 60, 100, 125]:
    xs = []
    for m, y in [(k, 0.6), (fr, -0.6)]:
        loc, _, _ = m.ray.intersects_location([[-80, y, z]], [[1, 0, 0]])
        xs.append(round(float(loc[:, 0].min()), 2) if len(loc) else None)
    good = xs[0] is not None and xs[1] is not None and abs(xs[0] - xs[1]) < 0.05
    ok &= good
    print(f"{'OK ' if good else 'FEIL'} skjøt z={z}: kropp x={xs[0]}  front x={xs[1]}")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
