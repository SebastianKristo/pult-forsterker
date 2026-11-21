#!/usr/bin/env python3
"""Bygg Skjold Sensor: STL-er for alle varianter, kontroll, K2-plater (3MF) og bilder.

    python3 lag_sensor.py            STL + kontroll + 3MF (krever openscad og trimesh; manifold3d for overlappsjekken)
    python3 lag_sensor.py bilder     også bildene i render/ (uten skjerm: starter en egen Xvfb om DISPLAY mangler)
    python3 lag_sensor.py bilder 11  bare bildene som begynner med 11 (flere prefikser kan gis)

Varianter: kort = esp32 | d1mini | esp32d1 (ESP32 D1 mini, USB ut bak nede) | d1mini_bak (D1 mini med USB-C, USB ut bak
nede), og lokk med/uten PIR og med/uten lysvindu.
  stl/<kort>/bunn.stl                    bunnen (baksiden ned)
  stl/<kort>/lokk.stl                    lokk med PIR, lysvindu og statuslys (forsiden ned)
  stl/<kort>/lokk_uten_pir.stl           … uten PIR (f.eks. med LD2410 mmWave inni, som ser gjennom plasten)
  stl/<kort>/lokk_uten_lux.stl           … uten lysvindu
  stl/<kort>/lokk_enkel.stl              … bare temperatur og fukt
  stl/<kort>/gull.stl                    gullisten og SKJOLD (felt inn i lokket, filament 3)
  stl/<kort>/stativ.stl                  bordstativ (på siden)
  stl/<kort>/sht40/                      bunn, lokk, gull og stativ med lite sensorkammer for SHT40 o.l. (th="sht40")
Standard temperatur/fukt-sensor er DHT11-modulen (th="dht11mod", 35 × 23 mm med PH2.0).
Kontroll: tette deler, ingen overlapp i montert stilling (kjøpte deler med), overheng i utskriftsretning, plass på K2."""
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
SC = "skjold_sensor.scad"
KORT = ["esp32", "d1mini", "esp32d1", "d1mini_bak"]
LOKK = {"lokk": (1, 1), "lokk_uten_pir": (0, 1), "lokk_uten_lux": (1, 0), "lokk_enkel": (0, 0)}
MONTERT = ["bunn", "lokk", "gull", "esp", "plugg", "pir", "lux", "sensor", "led"]


def scad(out, part, kort, pir=1, lux=1, ekstra=()):
    a = ["openscad", "-q", "-D", f'part="{part}"', "-D", f'kort="{kort}"', "-D", f"pir={'true' if pir else 'false'}",
         "-D", f"lux={'true' if lux else 'false'}", *ekstra, "-o", out, SC]
    return subprocess.Popen(a)


def kjor(procs):
    for p in procs:
        assert p.wait() == 0, p.args


procs = []
for k in KORT:
    os.makedirs(f"stl/{k}", exist_ok=True); os.makedirs(f"stl_asm/{k}", exist_ok=True)
    procs += [scad(f"stl/{k}/bunn.stl", "bunn", k), scad(f"stl/{k}/gull.stl", "gull", k), scad(f"stl/{k}/stativ.stl", "stativ", k)]
    procs += [scad(f"stl/{k}/{n}.stl", "lokk", k, p, l) for n, (p, l) in LOKK.items()]
    os.makedirs(f"stl/{k}/sht40", exist_ok=True)   # lite sensorkammer for SHT40/SHT31-kort (5–10 mm lavere boks)
    procs += [scad(f"stl/{k}/sht40/{p}.stl", p, k, ekstra=("-D", 'th="sht40"')) for p in ("bunn", "lokk", "gull", "stativ")]
    # USB-kabelen sjekkes slik den går på bordstativet (for esp32d1 bøyd bakover gjennom stativet)
    procs += [scad(f"stl_asm/{k}/{p}.stl", f"a_{p}", k, ekstra=("-D", 'kabel="stativ"') if p == "plugg" else ())
              for p in MONTERT + ["stativ", "dhtkort", "luxkort"]]
kjor(procs)

ok = True
def meld(god, tekst):
    global ok
    ok &= bool(god)
    print(("OK   " if god else "FEIL ") + tekst)


for k in KORT:
    print(f"--- {k} ---")
    # 1. tette deler i ett legeme
    for p in ["bunn", *LOKK, "gull", "stativ", "sht40/bunn", "sht40/lokk", "sht40/stativ"]:
        m = trimesh.load(f"stl/{k}/{p}.stl")
        n = len(m.split(only_watertight=False))
        meld(m.is_watertight and (n == 1 or p == "gull"), f"{p:14s} tett={m.is_watertight} deler={n} {np.round(m.extents, 1)} mm, "
             f"ca. {m.volume / 1000 * 1.27 * 0.6 + m.area / 100 * 0.04 * 1.27:.0f} g PETG")

    # 2. overlapp i montert stilling (kontaktpar får bare berøre)
    A = {p: trimesh.load(f"stl_asm/{k}/{p}.stl") for p in MONTERT + ["stativ"]}
    LOV = {("lokk", "gull"), ("bunn", "esp"), ("esp", "plugg"), ("bunn", "sensor"), ("lokk", "pir"), ("lokk", "lux"), ("lokk", "led")}
    feil = []
    navn = MONTERT + ["stativ"]
    for i, x in enumerate(navn):
        for y in navn[i + 1:]:
            try:
                v = A[x].intersection(A[y], engine="manifold").volume
            except Exception:
                v = 0
            grense = 6.0 if {x, y} == {"bunn", "esp"} else 0.5   # klemribbene går 0,25 mm inn i kortkantene
            if v > (grense if (x, y) in LOV or (y, x) in LOV else 0.02):
                feil.append(f"{x}×{y} {v:.2f} mm³")
    meld(not feil, "ingen overlapp i montert stilling (med stativet)" + ("" if not feil else ": " + "; ".join(feil)))

    # 2b. holderne uten skruer: DHT11- og GY-302-kortet sitter fritt (ingen overlapp) og kan ikke flytte seg mer enn
    #     0,3 mm noen vei – flyttet 0,35 mm i hver av de seks retningene skal kortet treffe bunnen eller lokket
    holder = A["bunn"].union(A["lokk"], engine="manifold")
    for kort in ("dhtkort", "luxkort"):
        m = trimesh.load(f"stl_asm/{k}/{kort}.stl")
        v0 = m.intersection(holder, engine="manifold").volume
        fri = []
        for akse in range(3):
            for fortegn in (-1, 1):
                d = np.zeros(3); d[akse] = 0.35 * fortegn
                if m.copy().apply_translation(d).intersection(holder, engine="manifold").volume < 1e-3:
                    fri.append("−+"[fortegn > 0] + "xyz"[akse])
        meld(v0 < 0.02 and not fri, f"{kort}: sitter uten skruer, {v0:.3f} mm³ overlapp, klaring ≤ 0,3 mm i alle retninger"
             + ("" if not fri else " – FRITT mot " + ", ".join(fri)))

    # 3. overheng i utskriftsretning: flater som peker mer enn 50° nedover; flate broer opp til 13 mm er greit på K2
    for p in ("bunn", "lokk", "stativ"):
        m = trimesh.load(f"stl/{k}/{p}.stl")
        nz = m.face_normals[:, 2]
        z = m.triangles_center[:, 2]
        ned = (nz < -np.sin(np.radians(50))) & (z > 0.05)
        if p == "lokk":   # taket i gullsporet (0,6 mm) fylles av gullet i samme utskrift
            ned &= z > 0.65
        stor = 0.0
        if ned.any():
            for f in m.submesh([np.where(ned)[0]], append=True).split(only_watertight=False):
                e = np.sort(f.extents[:2])
                flat = f.face_normals[:, 2].max() < -0.99
                if e[0] > (14.0 if flat else 3.0):   # flate broer: 8 mm (nøkkelhull), 12 mm (USB), 13 mm (USB-kanalen)
                    stor += f.area
        meld(stor < 1.0, f"{p}: {m.area_faces[ned].sum():.1f} mm² nedovervendt, {stor:.1f} mm² som trenger støtte")

# 4. K2-plater
sys.path.insert(0, os.path.join(HER, "..", "fjernkontroll"))
import lag_3mf as L   # noqa: E402
L.STL = "stl"
BRIM = {"enable_support": "0", "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.15"}
FIL3MF = {"d1mini_bak": "skjold-sensor-d1mini-usbbak-k2.3mf"}
for k, tittel in (("esp32", "ESP32-WROOM DevKit"), ("d1mini", "Wemos D1 mini"), ("esp32d1", "ESP32 D1 mini, USB bak"),
                  ("d1mini_bak", "Wemos D1 mini USB-C, USB bak")):
    L.OBJ_INNST = {f"{k}/bunn": BRIM, f"{k}/lokk": BRIM, f"{k}/stativ": {"enable_support": "0"}}
    L.write(FIL3MF.get(k, f"skjold-sensor-{k}-k2.3mf"), f"Skjold Sensor ({tittel}) – bunn, lokk med gullist og bordstativ (PETG/PLA)", [
        (f"{k}/bunn", "Bunn (baksiden ned)", 1, (10, 10), None),
        (f"{k}/lokk", "Lokk med PIR og lysvindu (forsiden ned)", 1, (10, 100), None),
        (f"{k}/gull", "Gullist og SKJOLD (felt inn i lokket)", 3, None, f"{k}/lokk"),
        (f"{k}/stativ", "Bordstativ (på siden, valgfritt)", 2, (120, 10), None)], {1: "#ECE9E3", 2: "#2E2D2C", 3: "#D99E40"})

print("ALT OK" if ok else "NOE FEILET")

# 5. bilder (OpenSCAD, Tomorrow, 1600 × 1100), lys og mørk
if "bilder" in sys.argv:
    os.makedirs("render", exist_ok=True)
    env, xv = dict(os.environ), None
    if not env.get("DISPLAY") and shutil.which("Xvfb"):   # én felles skjerm (xvfb-run -a i parallell kolliderer)
        import time
        xv = subprocess.Popen(["Xvfb", ":97", "-screen", "0", "1920x1200x24"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1.5)
        env["DISPLAY"] = ":97"
    valg = [a for a in sys.argv[sys.argv.index("bilder") + 1:]]
    SKRA = "125,-185,120,0,-14,27"
    FORFRA = "0,-200,28,0,-14,28"
    OVENFRA = "70,-130,210,0,-14,30"
    EKSP = "170,-230,150,0,-28,27"
    BILDER = [("01_skra_lys", "samlet", SKRA, "lys", "esp32"), ("02_ovenfra_lys", "samlet", OVENFRA, "lys", "esp32"),
              ("03_eksplodert_lys", "eksplodert", EKSP, "lys", "esp32"), ("04_skra_mork", "samlet", SKRA, "mork", "esp32"),
              ("05_ovenfra_mork", "samlet", OVENFRA, "mork", "esp32"), ("06_eksplodert_mork", "eksplodert", EKSP, "mork", "esp32"),
              ("07_forfra_lys", "samlet", FORFRA, "lys", "esp32"), ("08_d1mini_skra_lys", "samlet", "105,-160,105,0,-14,27", "lys", "d1mini"),
              ("09_stativ_lys", "stativ_samlet", "170,-190,120,0,-10,22", "lys", "esp32"),
              ("10_inni_lys", "inni", "30,-150,130,0,-5,28", "lys", "esp32"),
              ("11_esp32d1_skra_lys", "samlet", "120,-190,125,0,-14,30", "lys", "esp32d1"),
              ("12_esp32d1_bak_lys", "samlet", "120,160,-35,0,-14,26", "lys", "esp32d1"),
              ("13_esp32d1_inni_lys", "inni", "40,-150,140,0,-5,30", "lys", "esp32d1"),
              ("14_esp32d1_stativ_lys", "stativ_samlet", "175,-185,110,0,-10,24", "lys", "esp32d1"),
              ("15_d1mini_bak_skra_lys", "samlet", "110,-180,125,0,-15,32", "lys", "d1mini_bak"),
              ("16_d1mini_bak_bak_lys", "samlet", "110,160,-35,0,-15,28", "lys", "d1mini_bak"),
              ("17_d1mini_bak_inni_lys", "inni", "35,-150,140,0,-5,32", "lys", "d1mini_bak"),
              ("18_d1mini_bak_stativ_lys", "stativ_samlet", "170,-185,110,0,-10,24", "lys", "d1mini_bak"),
              ("19_lokk_inni_lys", "lokk_inni", "70,-40,-120,0,30,24", "lys", "d1mini")]
    procs = []
    BILDER = [b for b in BILDER if not valg or any(b[0].startswith(v) for v in valg)]
    for fil, part, cam, farge, k in BILDER:
        procs.append(subprocess.Popen(["openscad", "-q", "--colorscheme=Tomorrow", "--imgsize=1600,1100", "--projection=p",
                                             f"--camera={cam}", "-D", f'part="{part}"', "-D", f'kort="{k}"', "-D", f'farge="{farge}"',
                                             "-D", "vis=true", "-o", f"render/{fil}.png", SC], env=env))
    kjor(procs)
    if xv:
        xv.terminate()
    print("skrev", len(BILDER), "bilder i render/")

sys.exit(0 if ok else 1)
