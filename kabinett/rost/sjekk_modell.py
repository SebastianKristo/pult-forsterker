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
  6. lydkammeret (uten takrommet): netto volum og porttuning (fb) (0,86–1,00 l netto, 80–88 Hz)
  7. utskrift uten støtte: kroppens, bunnens og grillens yttersider har ingen flater brattere enn 50° i printretningen,
     og knappeholderen har ingen overheng i det hele tatt
  8. skjermen: modulen (kort 70,08 × 48,04, glass, flatkabel, pinnerad) ligger i lomma uten å kollidere, knappeholderens
     sidevanger klemmer kortet, og vinduet ligger over hele det aktive området med jevn kant rundt (sentrert)
  9. knappene: bryterne sitter i lommene med presspasning (klemribbene), luften mellom hetteflensen og stempelet er
     btnGap (0,2 mm), og hettene kan trykkes helt ned uten å treffe noe annet enn bryteren"""
import itertools
import sys

import numpy as np
import trimesh

ASM = sys.argv[1]
ok = True
PRINT = ["kropp", "front", "logo", "grill", "bunn", "knott", "rute", "knapp", "knappeholder",
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
         ("front", "pakning_bunn"), ("bunn", "pakning_front"), ("kropp", "rute"), ("kropp", "knapp"), ("kropp", "krage"), ("kropp", "dc_skive"),
         ("kropp", "usb_propp"), ("dc_skive", "usb_propp"), ("kropp", "knappeholder")}
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
# kjøpte deler: skjermmodulen og taktbryterne skal ligge i lommene uten å kollidere med noe (bortsett fra klemribbene)
sk = trimesh.load(f"{ASM}/skjerm.stl")
br = trimesh.load(f"{ASM}/bryter.stl")
for n in PRINT:
    for navn, m in (("skjermmodul", sk), ("taktbrytere", br)):
        v = overlap(A[n], m)
        lim = {("knappeholder", "skjermmodul"): 8.0, ("knappeholder", "taktbrytere"): 8.0}.get((n, navn), 0.05)
        if not v <= lim:
            olap.append(f"{n} × {navn}: {v:.3f} mm³")
print("OK  ingen overlapp i montert stilling" if not olap else "FEIL overlapp: " + "; ".join(olap))

# --- yttervegg ---
k = A["kropp"]
W, D, H, t = 112, 113, 134, 2.6
# (flate, senter u, senter v, radius) – tiltenkte åpninger. Toppen: v = y (flat topp).
# Bak: port, DC, USB-C og Skjold-merket på én linje (x = −26).
AA = trimesh.load(f"{ASM}/skjermflate.stl").bounds        # aktivt område på glasset (montert)
aaC = AA.mean(axis=0)
RUTE = A["rute"].bounds                                     # ruta i forsenkningen (montert)
KAPPER = [b for b in A["knapp"].split(only_watertight=False)]
HOLES = [("bak", -26, 40, 11.5), ("bak", -26, 19.5, 5.3), ("bak", -26, 7, 6.4), ("bak", -26, 64, 9.5),
         ("topp", 0, 88, 6.6)] + [("topp", c.bounds.mean(axis=0)[0], c.bounds.mean(axis=0)[1], 5.6) for c in KAPPER]


def under_ruta(face, u, v):   # forsenkningen for ruta (og hyllen den ligger på) regnes for seg under
    return face == "topp" and RUTE[0][0] - 0.3 <= u <= RUTE[1][0] + 0.3 and RUTE[0][1] - 0.3 <= v <= RUTE[1][1] + 0.3


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
            if any(f == face and np.hypot(u - a, v - b) < r for f, a, b, r in HOLES) or under_ruta(face, u, v):
                continue
            w = wall(face, u, v)
            if w < 1.59:
                bad.append((face, round(float(u), 1), round(float(v), 1), round(w, 2)))
if bad:
    ok = False
    print(f"FEIL yttervegg tynnere enn 1,6 mm på {len(bad)} punkter, f.eks. {bad[:6]}")
else:
    print("OK  yttervegg ≥ 1,6 mm overalt utenom tiltenkte hull")
# hyllen under ruta (mellom forsenkningen og glasslomma): ruta ligger på den, minst 1,3 mm
hylle = []
for u in np.arange(RUTE[0][0] + 0.4, RUTE[1][0] - 0.3, 0.5):
    for v in np.arange(RUTE[0][1] + 0.4, RUTE[1][1] - 0.3, 0.5):
        if min(u - RUTE[0][0], RUTE[1][0] - u, v - RUTE[0][1], RUTE[1][1] - v) > 1.0:
            continue   # (innenfor er vinduet med fas; hyllen er de ytterste 1–1,5 mm)
        w = wall("topp", u, v)
        if w > 0:
            hylle.append(w)
good = min(hylle) >= 1.3
ok &= good
print(f"{'OK ' if good else 'FEIL'} hyllen under ruta er minst {min(hylle):.2f} mm tykk (≥ 1,3 mm)")

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
good = 0.86 < netto < 1.00 and 80 < fb < 88
ok &= good
print(f"{'OK ' if good else 'FEIL'} lydkammer: {luft:.2f} l luft, {netto:.2f} l netto, port Ø16 × 78 mm → fb ≈ {fb:.0f} Hz "
      f"(forrige utgave, også uten takrommet: 0,95 l luft, 0,90 l netto → ca. 86 Hz)")

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
m = trimesh.load("stl/knappeholder.stl")
ned = (m.face_normals[:, 2] < -0.5) & (m.triangles_center[:, 2] > 0.05)
good = m.area_faces[ned].sum() < 0.5
ok &= good
print(f"{'OK ' if good else 'FEIL'} knappeholderen har {m.area_faces[ned].sum():.1f} mm² overheng (printes med bunnen ned)")

# --- skjermen ---
glass_top = sk.bounds[1][2]
pz = sk.bounds[1][2] - 5.25 + 0.5                            # midt i kortet (kort 1,0 + glass 4,25)
pv = np.array([p for e in sk.section(plane_origin=[0, 0, pz], plane_normal=[0, 0, 1]).discrete for p in e])
pcbB = pv[:, 0].max() - pv[:, 0].min()
pcbH = np.ptp(pv[np.abs(pv[:, 0]) > 10][:, 1])


def fri(x, y):   # ingen del av kroppen over glasset i dette punktet (stråle ovenfra)
    loc, _, _ = k.ray.intersects_location([[x, y, 200]], [[0, 0, -1]])
    return not np.any(loc[:, 2] > glass_top + 0.01) if len(loc) else True


blokk = [(x, y) for x in np.linspace(AA[0][0], AA[1][0], 23) for y in np.linspace(AA[0][1], AA[1][1], 12) if not fri(x, y)]


def kant(x0, y0, dx, dy):   # hvor langt fra AA-kanten vinduet er fritt (ved glasset)
    for d in np.arange(0, 6, 0.02):
        if not fri(x0 + dx * d, y0 + dy * d):
            return d
    return 6


mx = [kant(AA[0][0], aaC[1], -1, 0), kant(AA[1][0], aaC[1], 1, 0)]
my = [kant(aaC[0], AA[0][1], 0, -1), kant(aaC[0], AA[1][1], 0, 1)]
klem = overlap(A["knappeholder"], sk)
good = not blokk and min(mx + my) >= 0.3 and abs(mx[0] - mx[1]) < 0.1 and abs(my[0] - my[1]) < 0.1 and 0.05 < klem < 8
ok &= good
print(f"{'OK ' if good else 'FEIL'} skjerm: kort {pcbB:.2f} × {pcbH:.2f} mm i lomma uten kollisjon, aktivt område "
      f"{AA[1][0]-AA[0][0]:.1f} × {AA[1][1]-AA[0][1]:.2f} mm helt synlig ({len(blokk)} punkter dekket), vinduet går "
      f"{mx[0]:.2f}/{mx[1]:.2f} mm (venstre/høyre) og {my[0]:.2f}/{my[1]:.2f} mm (foran/bak) utenfor det; "
      f"sidevangene klemmer kortet ({klem:.2f} mm³ klemribbe)")

# --- knappene: presspasning, luft til stempelet og vandring ---
hus = stempel = sorted(br.split(only_watertight=False), key=lambda b: b.bounds[0][0])   # hus, stempel og bein
kapper = sorted(KAPPER, key=lambda b: b.bounds[0][0])
press = [overlap(A["knappeholder"], h) for h in hus]
gap = [c.bounds[0][2] - s_.bounds[1][2] for c, s_ in zip(kapper, stempel)]
TRAVEL = 0.25                                    # bryterens vandring
fritt = []
for c, g in zip(kapper, gap):
    ned_ = c.copy()
    ned_.apply_translation([0, 0, -(g + TRAVEL)])
    fritt.append(sum(overlap(A[n], ned_) for n in ("kropp", "knappeholder")) + overlap(sk, ned_))
good = len(hus) == 5 and len(stempel) == 5 and all(0.1 < p < 2.0 for p in press) and all(0.1 <= g <= 0.3 for g in gap) \
    and all(f < 0.01 for f in fritt)
ok &= good
print(f"{'OK ' if good else 'FEIL'} knapper: bryterne klemmes i lommene ({', '.join(f'{p:.2f}' for p in press)} mm³ klemribbe), "
      f"luft flens–stempel {', '.join(f'{g:.2f}' for g in gap)} mm, hettene går {TRAVEL} mm forbi klikket uten å treffe noe "
      f"({max(fritt):.3f} mm³)")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
