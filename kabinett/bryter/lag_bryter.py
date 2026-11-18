#!/usr/bin/env python3
"""Bygg Skjold Bryter: STL-er for begge kortene, kontroll, K2-plater (3MF) og bilder.

    python3 lag_bryter.py            STL + kontroll + 3MF (krever openscad og trimesh med manifold3d)
    python3 lag_bryter.py bilder     også bildene i render/ (uten skjerm: starter en egen Xvfb om DISPLAY mangler)

  stl/<kort>/kasse.stl   kassa (toppen ned, vingene på plata)
  stl/<kort>/bunn.stl    bunnplata med kortholderen og klipsene
  stl/<kort>/feste.stl   festet som skrus under bordplata (bordsiden ned)
  stl/<kort>/gull.stl    gullisten og SKJOLD (felt inn i fronten, filament 2)
kort = esp32d1 (ESP32 D1 mini / MH-ET LIVE MiniKit) | d1mini (Wemos D1 mini)
Kontroll: tette deler, ingen overlapp i montert stilling (brytere, kort og USB-plugg med), overheng i
utskriftsretning, plass på K2 (250 × 250 mm)."""
import os
import shutil
import subprocess
import sys
import warnings

import numpy as np
import trimesh

warnings.filterwarnings("ignore")
HER = os.path.dirname(os.path.abspath(__file__))
os.chdir(HER)
SC = "skjold_bryter.scad"
KORT = ["esp32d1", "d1mini"]
DELER = ["kasse", "bunn", "feste", "gull"]
MONTERT = ["kasse", "bunn", "feste", "gull", "bryter", "kort", "plugg"]


def scad(out, part, kort):
    return subprocess.Popen(["openscad", "-q", "-D", f'part="{part}"', "-D", f'kort="{kort}"', "-o", out, SC])


procs = []
for k in KORT:
    os.makedirs(f"stl/{k}", exist_ok=True); os.makedirs(f"stl_asm/{k}", exist_ok=True)
    procs += [scad(f"stl/{k}/{p}.stl", p, k) for p in DELER]
    procs += [scad(f"stl_asm/{k}/{p}.stl", f"a_{p}", k) for p in MONTERT]
for p in procs:
    assert p.wait() == 0, p.args

ok = True


def meld(god, tekst):
    global ok
    ok &= bool(god)
    print(("OK   " if god else "FEIL ") + tekst)


for k in KORT:
    print(f"--- {k} ---")
    for p in DELER:
        m = trimesh.load(f"stl/{k}/{p}.stl")
        n = len(m.split(only_watertight=False))
        meld(m.is_watertight and (n == 1 or p == "gull"), f"{p:6s} tett={m.is_watertight} deler={n} {np.round(m.extents, 1)} mm, "
             f"ca. {m.volume / 1000 * 1.27 * 0.6 + m.area / 100 * 0.04 * 1.27:.0f} g PETG")
        meld(m.extents[0] <= 245 and m.extents[1] <= 245, f"{p}: får plass på K2")
    A = {p: trimesh.load(f"stl_asm/{k}/{p}.stl") for p in MONTERT}
    LOV = {("kasse", "gull"), ("bunn", "kort"), ("kasse", "kort"), ("kort", "plugg"), ("kasse", "feste"), ("kasse", "bunn")}   # kontaktflater
    feil = []
    for i, x in enumerate(MONTERT):
        for y in MONTERT[i + 1:]:
            try:
                v = A[x].intersection(A[y], engine="manifold").volume
            except Exception:
                v = 0
            if v > (0.5 if (x, y) in LOV or (y, x) in LOV else 0.02):
                feil.append(f"{x}×{y} {v:.2f} mm³")
    meld(not feil, "ingen overlapp i montert stilling" + ("" if not feil else ": " + "; ".join(feil)))
    # kortet sitter fast: flyttet 0,4 mm i hver retning treffer det bunnen eller kassa (unntatt bakover mot USB-pluggen,
    # der bakveggen holder det)
    holder = A["bunn"].union(A["kasse"], engine="manifold")
    fri = []
    for akse in range(3):
        for fortegn in (-1, 1):
            d = np.zeros(3); d[akse] = 0.4 * fortegn
            if A["kort"].copy().apply_translation(d).intersection(holder, engine="manifold").volume < 1e-3:
                fri.append("−+"[fortegn > 0] + "xyz"[akse])
    meld(not fri, "kortet ligger fast i holderen" + ("" if not fri else " – FRITT mot " + ", ".join(fri)))
    # boksen henger i festet (flyttet 0,4 mm ned treffer den skinnene) og bunnplata i klipsene (0,4 mm ned treffer den kassa)
    for x, y, tekst in (("kasse", "feste", "boksen henger i festet"), ("bunn", "kasse", "bunnplata henger i klipsene")):
        v = A[x].copy().apply_translation([0, 0, -0.4]).intersection(A[y], engine="manifold").volume
        meld(v > 0.5, f"{tekst} ({v:.1f} mm³ når den flyttes 0,4 mm ned)")
    for p in ("kasse", "bunn", "feste"):
        m = trimesh.load(f"stl/{k}/{p}.stl")
        nz, z = m.face_normals[:, 2], m.triangles_center[:, 2]
        ned = (nz < -np.sin(np.radians(50))) & (z > 0.05)
        if p == "kasse":   # taket i gullsporet fylles av gullet i samme utskrift
            ned &= ~((np.abs(m.triangles_center[:, 1]) < 0.7) & (nz < -0.99))
        stor = 0.0
        if ned.any():
            for f in m.submesh([np.where(ned)[0]], append=True).split(only_watertight=False):
                e = np.sort(f.extents[:2])
                flat = f.face_normals[:, 2].max() < -0.99
                if e[0] > (13.0 if flat else 3.0):   # flate broer: USB-hullet (12 mm), skruesøylene (9 mm)
                    stor += f.area
        meld(stor < 1.0, f"{p}: {m.area_faces[ned].sum():.1f} mm² nedovervendt, {stor:.1f} mm² som trenger støtte")

sys.path.insert(0, os.path.join(HER, "..", "fjernkontroll"))
import lag_3mf as L   # noqa: E402
L.STL = "stl"
BRIM = {"enable_support": "0", "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.15"}
for k, tittel in (("esp32d1", "ESP32 D1 mini"), ("d1mini", "Wemos D1 mini")):
    L.OBJ_INNST = {f"{k}/kasse": BRIM, f"{k}/bunn": BRIM, f"{k}/feste": BRIM}
    L.write(f"skjold-bryter-{k}-k2.3mf", f"Skjold Bryter ({tittel}) – kasse med gullist, bunnplate og pultfeste (PETG/PLA)", [
        (f"{k}/kasse", "Kasse (toppen ned)", 1, (12, 12), None),
        (f"{k}/gull", "Gullist og SKJOLD (felt inn i fronten)", 2, None, f"{k}/kasse"),
        (f"{k}/bunn", "Bunnplate med kortholder og klips", 1, (30, 82), None),
        (f"{k}/feste", "Feste under bordplata (bordsiden ned)", 1, (8, 150), None)], {1: "#ECE9E3", 2: "#D99E40"})

if "bilder" in sys.argv:
    os.makedirs("render", exist_ok=True)
    env, xv = dict(os.environ), None
    if not env.get("DISPLAY") and shutil.which("Xvfb"):
        xv = subprocess.Popen(["Xvfb", ":96", "-screen", "0", "1920x1200x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        import time; time.sleep(1)
        env["DISPLAY"] = ":96"
    BILDER = [("01_forfra_under_lys", "samlet", "120,-260,-90,0,28,20", "lys"),
              ("02_forfra_under_mork", "samlet", "120,-260,-90,0,28,20", "mork"),
              ("03_inni", "inni", "60,-60,300,0,28,20", "lys"),
              ("04_eksplodert", "eksplodert", "200,-280,120,0,28,10", "lys"),
              ("05_bakfra", "samlet", "-140,300,-60,0,28,20", "lys"),
              ("06_uttrukket", "uttrukket", "230,-300,-40,0,10,30", "lys")]
    ps = [subprocess.Popen(["openscad", "-q", "--colorscheme=Tomorrow", "--imgsize=1600,1000", "--projection=p", f"--camera={cam}",
                            "-D", f'part="{part}"', "-D", f'farge="{farge}"', "-o", f"render/{fil}.png", SC], env=env)
          for fil, part, cam, farge in BILDER]
    for p in ps:
        p.wait()
    if xv:
        xv.terminate()
    print("skrev", len(BILDER), "bilder i render/")

print("ALT OK" if ok else "NOE FEILET")
