"""Kontroll av Skjold Radio-modellen.

Bruk:  python3 sjekk_modell.py [mappe med A_*.stl i montert stilling]   (standard: asm/)
STL-ene lages med  openscad -D 'part="kropp"' -o stl/kropp.stl skjold_radio.scad  og  -D 'part="A_kropp"' -o asm/kropp.stl
(se lag_stl.sh). Krever trimesh og manifold3d. Sjekker:
  1. alle utskrifts-STL-er i stl/ er vanntette, ett legeme (knapp: sju hetter), ligger på platen (min z = 0)
     og passer i Creality K2 (250 × 250 × 250 mm)
  2. ingen deler overlapper i montert stilling (høyttalerstoffet tas med, det skal ligge an mot grillrammen) (par som skal ligge an mot hverandre har bare kontaktflater)
  3. lydkammeret er tett: ett lukket rom når lokket og elementet er på (bare kabelhullet i gulvet er åpent),
     med netto volum 0,6–0,9 l (mono, ett 3″-element)
  4. kroppens og bakplatas yttervegg er hel (≥ 2 mm) utenom de tiltenkte hullene
  5. grillen med stoffet stikker 3 mm ut fra fronten (som Skjold Røst), mens gullista og panelet ligger i flukt
  6. symbolinnleggene (knappehettene, volumknotten, hjulet) er vanntette, 0,6 mm dype, i flukt med flaten og fyller
     lomma i sin egen del uten å overlappe den (montert: bare kontakt med sin egen del)
  7. det er plass i dybden: bak kammerlokket, bak Pi-en og foran kontaktene i bakplata"""
import itertools
import sys

import numpy as np
import trimesh

ASM = sys.argv[1] if len(sys.argv) > 1 else "asm"
ok = True
PRINT = ["kropp", "bak", "kammer", "lokk", "grill", "list", "brakett", "knott", "volum", "knapp",
         "knapp_symbol", "volum_symbol", "knott_symbol"]
LEGEMER = {"knapp": 7, "knapp_symbol": 8, "volum_symbol": 3, "knott_symbol": 3}   # 6 tall + ⏻ (sirkel og strek); høyttaler; ⏯
for n in PRINT:
    m = trimesh.load(f"stl/{n}.stl")
    parts = len(m.split(only_watertight=False))
    good = m.is_watertight and m.is_volume and parts == LEGEMER.get(n, 1) \
        and (abs(m.bounds[0][2]) < 0.02 or n in ("volum_symbol", "knott_symbol")) and max(m.extents) <= 250
    ok &= good
    print(f"{'OK ' if good else 'FEIL'} {n:12s} vanntett={m.is_watertight} deler={parts} {m.volume/1000:7.1f} cm³ "
          f"{m.extents.round(1)} mm")

ASMP = ["kropp", "bak", "kammer", "lokk", "grill", "list", "brakett", "knapper", "knott", "volum", "stoff",
        "knapp_symboler", "knott_symbol", "volum_symbol"]
A = {n: trimesh.load(f"{ASM}/{n}.stl") for n in ASMP}
TOUCH = {("grill", "stoff"), ("kropp", "stoff"), ("kropp", "bak"), ("kropp", "kammer"), ("kammer", "lokk"), ("kropp", "brakett"), ("kropp", "list"),
         ("knapper", "knapp_symboler"), ("knott", "knott_symbol"), ("volum", "volum_symbol")}   # innleggene ligger i lomma i sin del


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

# --- lydkammeret: luft inne i kammeret, avgrenset av kammer + lokk + elementet (+ gulvet under kabelhullet) ---
# --- symbolinnleggene: 0,6 mm dype, i flukt med flaten, fyller lomma uten overlapp ---
SYMD = 0.6
for del_, sym, flate in (("knapp", "knapp_symbol", 0.0), ("volum", "volum_symbol", 13 - 0.5), ("knott", "knott_symbol", 15 - 0.5)):
    a, s = trimesh.load(f"stl/{del_}.stl"), trimesh.load(f"stl/{sym}.stl")
    olap_s = a.intersection(s, engine="manifold").volume
    dyp = s.extents[2]
    flukt = abs((s.bounds[0][2] if flate == 0 else s.bounds[1][2]) - flate) < 0.01
    # åpen lomme: et tynt lag rett over/under innlegget skal være luft (flaten), og et tynt lag rett innenfor innlegget fylt av delen
    ut, inn = s.copy(), s.copy()
    ut.apply_translation([0, 0, -SYMD if flate == 0 else SYMD])
    inn.apply_translation([0, 0, SYMD if flate == 0 else -SYMD])
    fri = ut.intersection(a, engine="manifold").volume                  # over flaten: ingenting (innlegget synes)
    bunn = s.volume - inn.intersection(a, engine="manifold").volume      # under innlegget: delen er hel (lommebunnen)
    good = olap_s < 0.001 and abs(dyp - SYMD) < 0.01 and flukt and fri < 0.01 and bunn < 0.05 * s.volume
    ok &= good
    print(f"{'OK ' if good else 'FEIL'} {sym:12s} i lomma i {del_}: dybde {dyp:.2f} mm, i flukt={flukt}, "
          f"overlapp {olap_s:.4f} mm³, {s.volume:.1f} mm³")

W, D, H, kX0, kW, kY0, kD, kH, kT, baffT = 240, 115, 137, 22, 86, 8.6, 92, 124, 2.8, 7
drvX, drvZ = kX0 + kW/2, kH/2
box = A["kammer"].union(A["lokk"], engine="manifold")
el = trimesh.creation.cylinder(radius=43, height=4, sections=64)   # elementet tetter utsparingen i baffelen
el.apply_transform(trimesh.transformations.rotation_matrix(np.pi/2, [1, 0, 0]))
el.apply_translation([drvX, kY0 - 2, drvZ])
box = box.union(el, engine="manifold")
x0, x1 = kX0 + kT, kX0 + kW - kT
inner = trimesh.creation.box(extents=[x1 - x0 - 0.02, kD - baffT - 0.02, kH - 2*kT - 0.02])
inner.apply_translation([(x0 + x1)/2, kY0 + baffT + (kD - baffT)/2, kH/2])
air = inner.difference(box, engine="manifold")
drv = 0.05e6   # elementets magnet/kurv bak baffelen ≈ 0,05 l
vol = (air.volume - drv) / 1e6
# tetthet: stråler fra luftrommets midte og fire punkter rundt det i 26 retninger skal alle treffe kammer/lokk
dirs = np.array([d for d in itertools.product([-1, 0, 1], repeat=3) if any(d)], float)
cs = [np.array([(x0 + x1)/2 + dx, kY0 + baffT + (kD - baffT)/2, kH/2 + dz]) for dx, dz in ((0, 0), (-20, -35), (20, -35), (-20, 35), (20, 35))]
hits = np.concatenate([box.ray.intersects_any(np.repeat([c], len(dirs), 0), dirs) for c in cs])
good = hits.all() and 0.60 < vol < 0.90
ok &= good
print(f"{'OK ' if good else 'FEIL'} kammer (mono): netto ≈ {vol:.2f} l, lukket i alle {hits.sum()}/{len(hits)} retninger")

# --- yttervegg ≥ 2 mm: stråler inn fra sidene, toppen, gulvet og bakplata ---
# tiltenkte hull som rektangler (flate, u0, u1, v0, v1)
HOLES = [("bunn", x - 3.7, x + 3.7, y - 3.7, y + 3.7) for x in (kX0 - 4, kX0 + kW + 4) for y in (kY0 + 12, kY0 + kD - 12)] + \
        [("bunn", 129, 209, 33, 87)] + \
        [("bak", 134.5, 145.5, 16.5, 27.5), ("bak", 155, 165, 17, 27), ("bak", 174, 186, 19, 25),
         ("bak", 195, 222, 9, 41), ("bak", 127, 213, 77, 119)] + \
        [("bak", x - 4.5, x + 4.5, z - 4.5, z + 4.5) for x, z in ((8.5, 5.5), (W - 8.5, 5.5), (8.5, H - 8.5), (W - 8.5, H - 8.5), (W/2, H - 6))]


def wall(mesh, o, d):
    loc, _, _ = mesh.ray.intersects_location([o], [d])
    if len(loc) < 2:
        return 0.0
    s = sorted(np.linalg.norm(loc - np.array(o), axis=1))
    return s[1] - s[0]


bad = []
FACES = [("side+", A["kropp"], np.arange(20, D - 20, 4), np.arange(-2, H - 2, 4), lambda u, v: ([W + 5, u, v], [-1, 0, 0])),
         ("side-", A["kropp"], np.arange(20, D - 20, 4), np.arange(-2, H - 2, 4), lambda u, v: ([-5, u, v], [1, 0, 0])),
         ("topp", A["kropp"], np.arange(20, W - 20, 4), np.arange(20, D - 20, 4), lambda u, v: ([u, v, H + 5], [0, 0, -1])),
         ("bunn", A["kropp"], np.arange(20, W - 20, 4), np.arange(20, D - 20, 4), lambda u, v: ([u, v, -10], [0, 0, 1])),
         ("bak", A["bak"], np.arange(20, W - 20, 4), np.arange(4, H - 8, 4), lambda u, v: ([u, D + 5, v], [0, -1, 0]))]
for face, mesh, us, vs, ray in FACES:
    for u in us:
        for v in vs:
            if any(f == face and u0 <= u <= u1 and v0 <= v <= v1 for f, u0, u1, v0, v1 in HOLES):
                continue
            o, d = ray(u, v)
            w = wall(mesh, o, d)
            if w < 1.99:
                bad.append((face, float(u), float(v), round(w, 2)))
if bad:
    ok = False
    print(f"FEIL yttervegg tynnere enn 2 mm på {len(bad)} punkter, f.eks. {bad[:6]}")
else:
    print("OK  yttervegg ≥ 2 mm på sidene, toppen, gulvet og bakplata utenom tiltenkte hull")

# --- grillen stikker 3 mm ut (som Røst); gullista står bare 0,4 mm ut, panelet (kroppen) er flatt ---
ut_stoff, ut_grill, ut_list, ut_kropp = -A["stoff"].bounds[0][1], -A["grill"].bounds[0][1], -A["list"].bounds[0][1], -A["kropp"].bounds[0][1]
good = abs(ut_stoff - 3.0) < 0.05 and abs(ut_grill - 2.5) < 0.05 and ut_list < 0.45 and abs(ut_kropp) < 0.01
ok &= good
print(f"{'OK ' if good else 'FEIL'} grillen stikker {ut_stoff:.1f} mm ut (rammen {ut_grill:.1f} mm + stoffet), gullista {ut_list:.1f} mm, panelet i flukt")

# --- plass i dybden (115 mm): bak kammerlokket, bak Pi-en og bak luftespaltene (kontaktene i bakplata) ---
bak_inn = A["bak"].bounds[0][1]
lokk_luft = bak_inn - A["lokk"].bounds[1][1]                  # skruehoder (3 mm) og skumtape
pi_bak = A["brakett"].bounds[1][1] + 1.4 + 16                 # Pi-tårnene + kortet + USB/nett-kontaktene (16 mm)
pi_luft = bak_inn - pi_bak                                    # DSI-kabelen og USB-skjøten bøyes bak Pi-en
spalte_bak = 34 + 52                                          # ventGulv: y0 + lengde
kontakt_luft = bak_inn - spalte_bak                           # DC-022 (≈ 14 mm), PJ-392 og USB-C-skjøten med lodding/bøy
good = lokk_luft >= 6 and pi_luft >= 50 and kontakt_luft >= 25
ok &= good
print(f"{'OK ' if good else 'FEIL'} dybden {A['kropp'].bounds[1][1]:.0f} mm (+ 3 mm grill): {lokk_luft:.1f} mm bak kammerlokket, "
      f"{pi_luft:.0f} mm bak Pi-en, {kontakt_luft:.0f} mm fri gulvflate foran bakplata for kontaktene")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
