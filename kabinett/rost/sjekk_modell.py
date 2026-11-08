"""Kontroll av Skjold Røst-modellen (knappehetter og løs grill).

Bruk:  python3 sjekk_modell.py <mappe med A_*.stl i montert stilling>
A_*.stl lages med  openscad -D 'part="a_kropp"' -o A_kropp.stl skjold_rost.scad  (se dispatch nederst i .scad).
Krever trimesh og manifold3d. Sjekker:
  1. alle utskrifts-STL-er i stl/ er vanntette, ett legeme, ligger på platen (min z = 0) og passer på 250 × 250 mm
  2. ingen deler overlapper i montert stilling (par som skal ligge an mot hverandre har bare kontaktflater)
  3. kroppens yttervegg er hel: stråler inn fra sidene, toppen og baksiden treffer ≥ 1,6 mm materiale overalt,
     bortsett fra de tiltenkte hullene (port, DC, USB, EC11, preget merke)
  4. kroppen og frontplaten flukter i skjøten (samme ytterkant på begge sider av y = 0)
  5. pakningene følger den nye formen: frontpakningen ligger innenfor kroppens snitt i skjøten, bunnpakningen innenfor
     kroppens grunnriss, begge med ≥ 0,5 mm til yttersiden
  6. lydkammeret: netto volum og porttuning (fb) holdes nær forrige utgave (0,92–1,05 l netto, 80–86 Hz)
  7. utskrift uten støtte: kroppens, bunnens og grillens yttersider har ingen flater brattere enn 50° i printretningen"""
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
W, D, H, t = 112, 113, 134, 2.6
# (flate, senter u, senter v, radius) – tiltenkte åpninger. Toppen: v = y (flat topp).
# Bak: port, DC, USB-C og Skjold-merket på én linje (x = −26).
HOLES = [("bak", -26, 40, 11.5), ("bak", -26, 19.5, 5.3), ("bak", -26, 7, 6.4), ("bak", -26, 64, 9.5),
         ("topp", 0, 88, 6.6), ("topp", 0, 43, 33.0)] + [("topp", (i - 2) * 13.725, 11, 5.6) for i in range(5)]


def wall(face, u, v):
    if face == "side+":
        o, d = [W/2 + 5, u, v], [-1, 0, 0]
    elif face == "side-":
        o, d = [-W/2 - 5, u, v], [1, 0, 0]
    elif face == "topp":
        o, d = [u, v, H + 5], [0, 0, -1]   # toppen er skrå; strålen treffer overflaten litt lavere foran
    else:
        o, d = [u, D + 5, v], [0, -1, 0]
    for e in (0.0, 0.013):   # (traff stråla akkurat en kant i nettet, prøves en hundredels mm ved siden av)
        oo = np.array(o, float) + np.cross(d, [0.6, 0.7, 0.4]) * e
        loc, _, _ = k.ray.intersects_location([oo], [d])
        s = np.unique(np.round(np.linalg.norm(loc - oo, axis=1), 3)) if len(loc) else []
        if len(s) >= 2:
            return s[1] - s[0]
    return 0.0


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

# --- pakningene følger formen ---
from shapely.geometry import MultiPoint, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402


def snitt(mesh, origin, normal, to2d):
    sec = mesh.section(plane_origin=origin, plane_normal=normal)
    pts = [to2d(p) for e in sec.discrete for p in e]
    return MultiPoint(pts).convex_hull


ytre_y0 = snitt(k, [0, 0.3, 0], [0, 1, 0], lambda p: (p[0], p[2]))
ytre_z0 = snitt(trimesh.util.concatenate([k, fr]), [0, 0, 0.3], [0, 0, 1], lambda p: (p[0], p[1]))   # kropp + frontplate
pf = A["pakning_front"].vertices
pf = pf[pf[:, 2] > 2]                                       # (nederst lukker bunnplata)
pb = A["pakning_bunn"].vertices
mf = min(ytre_y0.exterior.distance(Point(x, z)) for x, _, z in pf[::7]) if ytre_y0.contains(MultiPoint([(x, z) for x, _, z in pf])) else 0
mb = min(ytre_z0.exterior.distance(Point(x, y)) for x, y, _ in pb[::7]) if ytre_z0.contains(MultiPoint([(x, y) for x, y, _ in pb])) else 0
good = mf >= 0.5 and mb >= 0.5
ok &= good
print(f"{'OK ' if good else 'FEIL'} pakningene følger formen: frontpakningen {mf:.1f} mm og bunnpakningen {mb:.1f} mm innenfor yttersiden")

# --- lydkammeret og porten ---
luft = trimesh.load(f"{ASM}/luft.stl").volume / 1e6        # liter luft mellom vegger, front, gulv og takrom
netto = luft - 0.05                                         # elementet (ca. 50 cm³)
PORT_D, PORT_L = 0.016, 0.078                               # Ø16 mm, 78 mm (portL i skjold_rost.scad)
fb = 343 / (2 * np.pi) * np.sqrt(np.pi * (PORT_D / 2) ** 2 / (netto / 1000 * (PORT_L + 0.732 * PORT_D)))
good = 0.92 < netto < 1.05 and 80 < fb < 86
ok &= good
print(f"{'OK ' if good else 'FEIL'} lydkammer: {luft:.2f} l luft, {netto:.2f} l netto, port Ø16 × 78 mm → fb ≈ {fb:.0f} Hz "
      f"(forrige utgave med fas bak: 1,01 l luft, 0,96 l netto → ca. 84 Hz)")

# --- utskrift uten støtte: yttersidene (nær det konvekse skallet) har ingen flater brattere enn 50° ---
res = []
for n, maxz in (("kropp", 134 - 0.1), ("bunn", 99), ("grill", 99)):   # kropp: leppene på toppen (0,5 mm) regnes ikke
    m = trimesh.load(f"stl/{n}.stl")
    c, nn, a = m.triangles_center, m.face_normals, m.area_faces
    ytre = np.abs(trimesh.proximity.signed_distance(m.convex_hull, c)) < 0.3
    bratt = ytre & (nn[:, 2] < -np.sin(np.radians(50))) & (c[:, 2] > 0.3) & (c[:, 1] < maxz)
    res.append((n, a[bratt].sum()))
good = all(v < 1.0 for _, v in res)
ok &= good
print(f"{'OK ' if good else 'FEIL'} printes uten støtte: " + ", ".join(f"{n} {v:.1f} mm²" for n, v in res) + " brattere enn 50° på yttersiden")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
