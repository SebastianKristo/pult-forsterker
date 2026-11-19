#!/usr/bin/env python3
"""Bygg Skjold Nøkkel: STL-er, kontroll, K2-plate (3MF) og bilder.

    python3 lag_nokkel.py            STL + kontroll + 3MF (krever openscad og trimesh med manifold3d)
    python3 lag_nokkel.py bilder     også bildene i render/ (uten skjerm: starter en egen Xvfb :97 om DISPLAY mangler)

  stl/kasse.stl   topp, sider og ender med fjærtunga over BOOT (toppen ned)
  stl/bunn.stl    bunnplata med støttene under kortet og vulstene som klikker i
  stl/gull.stl    gullisten, Skjold-merket, SKJOLD og ringen rundt trykkpunktet (felt inn i toppen, filament 2)
  stl/vindu.stl   lyslederen over RGB-LED-en (hvit eller klar, filament 3)
Kontroll: tette deler, ingen overlapp i montert stilling (kort, knapper og USB-plugg med), kortet ligger fast,
BOOT kan trykkes (luft og vandring), USB-pluggen går inn, COM er dekket, lyset når vinduet, binders når RST,
overheng i utskriftsretning, plass på K2 (250 × 250 mm)."""
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
SC = "skjold_nokkel.scad"
DELER = ["kasse", "bunn", "gull", "vindu"]
MONTERT = ["kasse", "bunn", "gull", "vindu", "kort", "plugg"]
EKSTRA = ["kasse_fast", "tunge", "tunge_trykt", "kort_u", "stift", "plugg_com", "lys", "binders"]


def scad(out, part):
    return subprocess.Popen(["openscad", "-q", "-D", f'part="{part}"', "-o", out, SC])


def verdier():
    """Les mål fra .scad-fila via echo (så rapporten viser det som faktisk er brukt)."""
    navn = ["Lx", "W", "H", "luft", "knappVandring", "overTrykk", "trykk", "trykkVinkel", "rstHull", "hullB", "hullH", "vinduD"]
    fil, scf = os.path.join("stl_asm", "verdier.echo"), os.path.join("stl_asm", "verdier.scad")
    with open(scf, "w") as f:
        f.write(f'include <../{SC}>\npart = "ingen";\necho(' + ",".join(f'"{n}",{n}' for n in navn) + ");\n")
    subprocess.run(["openscad", "-o", fil, scf], check=True, capture_output=True)
    t = open(fil).read().split("ECHO:")[-1].strip()
    os.remove(fil); os.remove(scf)
    deler = [d.strip().strip('"') for d in t.split(",")]
    return {deler[i]: float(deler[i + 1]) for i in range(0, len(deler) - 1, 2)}


os.makedirs("stl", exist_ok=True); os.makedirs("stl_asm", exist_ok=True)
procs = [scad(f"stl/{p}.stl", p) for p in DELER] + [scad(f"stl_asm/{p}.stl", f"a_{p}") for p in MONTERT + EKSTRA]
for p in procs:
    assert p.wait() == 0, p.args

ok = True


def meld(god, tekst):
    global ok
    ok &= bool(god)
    print(("OK   " if god else "FEIL ") + tekst)


def snitt(a, b):
    try:
        return a.intersection(b, engine="manifold").volume
    except Exception:
        return 0.0


try:
    V = verdier()
    print(f"Kabinettet: {V['Lx']:.1f} × {V['W']:.1f} × {V['H']:.1f} mm (l × b × h, uten øyet)")
except Exception as e:   # bare til rapporten
    V = {}
    print("(fikk ikke lest målene:", e, ")")

# 1. tette deler
for p in DELER:
    m = trimesh.load(f"stl/{p}.stl")
    n = len(m.split(only_watertight=False))
    meld(m.is_watertight and (n == 1 or p == "gull"), f"{p:6s} tett={m.is_watertight} deler={n} {np.round(m.extents, 1)} mm, "
         f"ca. {m.volume / 1000 * 1.27 * 0.6 + m.area / 100 * 0.04 * 1.27:.1f} g PETG")
    meld(m.extents[0] <= 245 and m.extents[1] <= 245, f"{p}: får plass på K2")

A = {p: trimesh.load(f"stl_asm/{p}.stl") for p in MONTERT + EKSTRA}

# 2. ingen overlapp i montert stilling
LOV = {("kasse", "gull"), ("kasse", "vindu"), ("bunn", "kort"), ("kort", "plugg"), ("kasse", "bunn")}   # kontaktflater
feil = []
for i, x in enumerate(MONTERT):
    for y in MONTERT[i + 1:]:
        v = snitt(A[x], A[y])
        if v > (0.5 if (x, y) in LOV or (y, x) in LOV else 0.02):
            feil.append(f"{x}×{y} {v:.2f} mm³")
meld(not feil, "ingen overlapp i montert stilling (kort, knapper og USB-plugg med)" + ("" if not feil else ": " + "; ".join(feil)))

# 3. kortet ligger fast: flyttet 0,4 mm i hver retning treffer det kassa eller bunnplata
holder = A["bunn"].union(A["kasse"], engine="manifold")
fri = []
for akse in range(3):
    for fortegn in (-1, 1):
        d = np.zeros(3); d[akse] = 0.4 * fortegn
        if snitt(A["kort"].copy().apply_translation(d), holder) < 1e-3:
            fri.append("−+"[fortegn > 0] + "xyz"[akse])
meld(not fri, "kortet ligger fast (flyttet 0,4 mm i alle seks retninger treffer det kabinettet)" + ("" if not fri else " – FRITT mot " + ", ".join(fri)))

# 4. bunnplata henger i klipsene (0,4 mm ned treffer den sporene i kassa)
v = snitt(A["bunn"].copy().apply_translation([0, 0, -0.4]), A["kasse"])
meld(v > 0.05, f"bunnplata henger i klipsene ({v:.2f} mm³ når den flyttes 0,4 mm ned)")

# 5. BOOT: luft 0,1–0,3 mm mellom stempelet og knappen, og tunga kan trykkes forbi klikket uten å treffe noe annet
t0 = snitt(A["tunge"], A["stift"])
t1 = snitt(A["tunge"].copy().apply_translation([0, 0, -0.1]), A["stift"])
t3 = snitt(A["tunge"].copy().apply_translation([0, 0, -0.3]), A["stift"])
meld(t0 < 1e-3 and t1 < 1e-3 and t3 > 1e-3, f"BOOT: luft mellom 0,1 og 0,3 mm til stempelet (flyttet 0,1 mm: {t1:.3f} mm³, 0,3 mm: {t3:.3f} mm³)")
rest = A["kasse_fast"].union(A["bunn"], engine="manifold").union(A["kort_u"], engine="manifold")
vr = snitt(A["tunge_trykt"], rest)
vs = snitt(A["tunge_trykt"], A["stift"])
meld(vr < 0.02 and vs > 0.05, f"BOOT: tunga trykket {V.get('trykk', 0):.2f} mm ({V.get('trykkVinkel', 0):.1f}°) treffer bare knappen "
     f"({vs:.2f} mm³ i knappens stempel, {vr:.3f} mm³ i alt annet); knappen går {V.get('overTrykk', 0):.1f} mm forbi klikket")
# tunga er fri (spalten rundt): uten roten henger den ikke sammen med resten av kassa
meld(snitt(A["tunge"].copy().apply_translation([0, 0, -0.05]), A["kasse_fast"]) < 0.02, "fjærtunga er fri rundt (spalten går hele veien)")

# 6. USB: pluggen går inn uten å treffe kabinettet, og COM-porten er dekket
vp = snitt(A["plugg"], A["kasse"].union(A["bunn"], engine="manifold"))
meld(vp < 0.01, f"USB-pluggen går helt inn uten å treffe kabinettet ({vp:.3f} mm³)")
vc = snitt(A["plugg_com"], A["kasse"])
meld(vc > 5, f"COM-porten er dekket (en plugg der treffer veggen: {vc:.0f} mm³)")

# 7. lyset fra RGB-LED-en når lysvinduet, og en binders når RST
vl = snitt(A["lys"], A["kasse"])
meld(vl < 0.01, f"fri vei fra RGB-LED-en til lysvinduet ({vl:.3f} mm³)")
vb = snitt(A["binders"], A["kasse"])
meld(vb < 0.01 and V.get("rstHull", 9) < 2, f"en binders (Ø1,0) når RST gjennom hullet (Ø{V.get('rstHull', 0):.1f}, for lite for en finger)")

# 8. overheng i utskriftsretning
for p in ("kasse", "bunn"):
    m = trimesh.load(f"stl/{p}.stl")
    nz, z = m.face_normals[:, 2], m.triangles_center[:, 2]
    ned = (nz < -np.sin(np.radians(50))) & (z > 0.05)
    if p == "kasse":   # taket i gullsporet (toppen ligger på plata) fylles av gullet i samme utskrift
        ned &= ~((z < 0.7) & (nz < -0.99))
    stor = 0.0
    if ned.any():
        for f in m.submesh([np.where(ned)[0]], append=True).split(only_watertight=False):
            e = np.sort(f.extents[:2])
            flat = f.face_normals[:, 2].max() < -0.99
            if e[0] > (13.0 if flat else 3.0):   # flate broer: USB-hullet (ca. 9 mm)
                stor += f.area
    meld(stor < 1.0, f"{p}: {m.area_faces[ned].sum():.1f} mm² nedovervendt, {stor:.1f} mm² som trenger støtte")

# 9. K2-plate
sys.path.insert(0, os.path.join(HER, "..", "fjernkontroll"))
import lag_3mf as L   # noqa: E402
L.STL = "stl"
BRIM = {"enable_support": "0", "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.15"}
L.OBJ_INNST = {"kasse": BRIM, "bunn": BRIM}
L.write("skjold-nokkel-k2.3mf", "Skjold Nøkkel (ESP32-S3-DevKitC-1) – kasse med gull og lysvindu, og bunnplate (PETG/PLA)", [
    ("kasse", "Kasse (toppen ned)", 1, (90, 110), None),
    ("gull", "Gullist, merke, SKJOLD og ring (felt inn i toppen)", 2, None, "kasse"),
    ("vindu", "Lysvindu (hvit eller klar, felt inn i toppen)", 3, None, "kasse"),
    ("bunn", "Bunnplate", 1, (90, 70), None)], {1: "#ECE9E3", 2: "#D99E40", 3: "#F4F6F7"})

# 10. bilder
if "bilder" in sys.argv:
    os.makedirs("render", exist_ok=True)
    env, xv = dict(os.environ), None
    if not env.get("DISPLAY"):
        env["DISPLAY"] = ":97"
        if not os.path.exists("/tmp/.X11-unix/X97") and shutil.which("Xvfb"):
            import time
            xv = subprocess.Popen(["Xvfb", ":97", "-screen", "0", "1920x1200x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(1.5)
    SKRA = "-40,-95,85,33,0,4"
    BILDER = [("01_skra_lys", "samlet", SKRA, "lys"),
              ("02_skra_mork", "samlet", SKRA, "mork"),
              ("03_usb_ende", "samlet", "-95,-55,40,30,0,4", "lys"),
              ("04_eksplodert", "eksplodert", "-55,-120,95,30,0,4", "lys"),
              ("05_inni", "inni", "20,-70,110,32,0,3", "lys"),
              ("06_undersiden", "samlet", "95,-70,-75,35,0,4", "lys"),
              ("07_snitt_boot", "snitt", "75,-35,22,31,-4,5", "lys")]
    ps = [subprocess.Popen(["openscad", "-q", "--colorscheme=Tomorrow", "--imgsize=1600,1000", "--projection=p", f"--camera={cam}",
                            "-D", f'part="{part}"', "-D", f'farge="{farge}"', "-o", f"render/{fil}.png", SC], env=env)
          for fil, part, cam, farge in BILDER]
    for p in ps:
        p.wait()
    if xv:
        xv.terminate()
    print("skrev", len(BILDER), "bilder i render/")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
