#!/usr/bin/env python3
"""Bygg Skjold IR: STL-er for begge kortene, kontroll, K2-plater (3MF) og bilder.

    python3 lag_ir.py            STL + kontroll + 3MF (krever openscad og trimesh; manifold3d for overlappsjekken)
    python3 lag_ir.py bilder     også bildene i render/ (uten skjerm: xvfb-run brukes av seg selv om DISPLAY mangler)

Varianter: kort = c3 (ESP32-C3 SuperMini) | d1mini (Wemos D1 mini).
  stl/<kort>/bunn.stl        bunnen (undersiden ned)
  stl/<kort>/topp.stl        toppen (toppflaten ned)
  stl/<kort>/topp_opp.stl    … med en fjerde lysdiode rett opp
  stl/<kort>/gull.stl        gullringen (felt inn i toppen, filament 3)
  stl/<kort>/lysleder.stl    lyslederen over den blå lysdioden (klar PETG, toppenden ned)
Kontroll: tette deler, ingen overlapp i montert stilling (kjøpte deler med), fri sikt for lysdiodene og mottakeren,
overheng i utskriftsretning, plass på K2."""
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
SC = "skjold_ir.scad"
KORT = ["c3", "d1mini"]
DELER = ["bunn", "topp", "gull", "lysleder"]
MONTERT = ["bunn", "topp", "gull", "lysleder", "kort", "led", "mott", "driver", "magnet"]


def scad(out, part, kort, ekstra=()):
    return subprocess.Popen(["openscad", "-q", "-D", f'part="{part}"', "-D", f'kort="{kort}"', *ekstra, "-o", out, SC])


def kjor(procs):
    for p in procs:
        assert p.wait() == 0, p.args


procs = []
for k in KORT:
    os.makedirs(f"stl/{k}", exist_ok=True); os.makedirs(f"stl_asm/{k}", exist_ok=True)
    procs += [scad(f"stl/{k}/{p}.stl", p, k) for p in DELER]
    procs.append(scad(f"stl/{k}/topp_opp.stl", "topp", k, ("-D", "led_opp=true")))
    procs += [scad(f"stl_asm/{k}/{p}.stl", f"a_{p}", k) for p in MONTERT]
    procs.append(scad(f"stl_asm/{k}/led_opp.stl", "a_led", k, ("-D", "led_opp=true")))
    procs.append(scad(f"stl_asm/{k}/topp_opp.stl", "a_topp", k, ("-D", "led_opp=true")))
kjor(procs)

ok = True


def meld(god, tekst):
    global ok
    ok &= bool(god)
    print(("OK   " if god else "FEIL ") + tekst)


def tall(navn):
    import re
    return float(re.search(rf"^{navn}\s*=\s*([-\d.]+)", open(SC).read(), re.M).group(1))


B, R, zs, ir_inne = tall("B"), tall("R"), tall("zs"), tall("ir_inne")
mott_x, vegg = tall("mott_x"), tall("vegg")


def rs(a):
    """avstand fra midten til ytterflaten i retning a (som rs() i scad-fila)"""
    ux, uy = abs(np.sin(np.radians(a))), abs(np.cos(np.radians(a)))
    h, c = B / 2, B / 2 - R
    t = min(h / ux if ux > 1e-6 else 1e9, h / uy if uy > 1e-6 else 1e9)
    if ux * t <= c + 1e-6 or uy * t <= c + 1e-6:
        return t
    b = (ux + uy) * c
    return b + np.sqrt(b * b - 2 * c * c + R * R)


def kjegle(start, akse, halv, hinder):
    """antall stråler i en kjegle (±halv grader) fra start langs akse som treffer hinder"""
    akse = np.asarray(akse, float) / np.linalg.norm(akse)
    u = np.cross(akse, [0, 0, 1] if abs(akse[2]) < 0.9 else [1, 0, 0]); u /= np.linalg.norm(u)
    w = np.cross(akse, u)
    treff = n = 0
    for a in np.radians(np.linspace(0, halv, 4)):
        for b in np.radians(np.arange(0, 360, 30)):
            r = np.cos(a) * akse + np.sin(a) * (np.cos(b) * u + np.sin(b) * w)
            n += 1
            treff += len(hinder.ray.intersects_location([start], [r])[0]) > 0
    return treff, n


for k in KORT:
    print(f"--- {k} ---")
    # 1. tette deler i ett legeme (støvkorn under 0,01 mm³ fra boolske operasjoner telles ikke)
    for p in DELER + ["topp_opp"]:
        m = trimesh.load(f"stl/{k}/{p}.stl")
        n = len([b for b in m.split(only_watertight=False) if abs(b.volume) >= 0.01])
        meld(m.is_watertight and n == 1, f"{p:9s} tett={m.is_watertight} deler={n} {np.round(m.extents, 1)} mm, "
             f"ca. {m.volume / 1000 * 1.24 * 0.6 + m.area / 100 * 0.04 * 1.24:.0f} g PLA")

    # 2. overlapp i montert stilling (kontaktpar får bare berøre)
    A = {p: trimesh.load(f"stl_asm/{k}/{p}.stl") for p in MONTERT}
    LOV = {("bunn", "topp"), ("topp", "gull"), ("bunn", "kort"), ("bunn", "led"), ("topp", "led"), ("bunn", "mott"),
           ("bunn", "driver"), ("bunn", "magnet"), ("topp", "lysleder"), ("kort", "lysleder")}
    feil = []
    for i, x in enumerate(MONTERT):
        for y in MONTERT[i + 1:]:
            try:
                v = A[x].intersection(A[y], engine="manifold").volume
            except Exception:
                v = 0
            if v > (0.5 if (x, y) in LOV or (y, x) in LOV else 0.02):
                feil.append(f"{x}×{y} {v:.2f} mm³")
    opp = trimesh.load(f"stl_asm/{k}/led_opp.stl")
    for x in ("topp_opp",):
        v = trimesh.load(f"stl_asm/{k}/{x}.stl").intersection(opp, engine="manifold").volume
        if v > 0.5:
            feil.append(f"{x}×led_opp {v:.2f} mm³")
    meld(not feil, "ingen overlapp i montert stilling (kort, lysdioder, VS1838B, driver, magneter, lysleder)"
         + ("" if not feil else ": " + "; ".join(feil)))

    # 3. fri sikt: lysdiodene (±17°, som TSAL6200) og mottakeren (±25°) ser ut forbi kanten på hullet
    hinder = trimesh.util.concatenate([A["bunn"], A["topp"]])
    tot = [0, 0]
    for a in (-45, 0, 45):
        r = np.radians(a)
        akse = np.array([np.sin(r), -np.cos(r), 0.0])
        t, n = kjegle(akse * (rs(a) - ir_inne + 0.05) + [0, 0, zs], akse, 17, hinder)
        tot[0] += t; tot[1] += n
    meld(tot[0] == 0, f"fri sikt fra de tre lysdiodene (±17°): {tot[0]} av {tot[1]} stråler treffer kabinettet")
    t, n = kjegle(np.array([mott_x, -B / 2 + vegg - 0.05, zs]), [0, -1, 0], 25, hinder)
    meld(t == 0, f"fri sikt for VS1838B (±25°): {t} av {n} stråler treffer kabinettet")

    # 4. overheng i utskriftsretning: flater som peker mer enn 50° nedover; flate broer opp til 13 mm er greit på K2
    for p in ("bunn", "topp", "topp_opp", "lysleder"):
        m = trimesh.load(f"stl/{k}/{p}.stl")
        nz = m.face_normals[:, 2]
        z = m.triangles_center[:, 2]
        ned = (nz < -np.sin(np.radians(50))) & (z > 0.05)
        if p.startswith("topp"):   # taket i gullsporet (0,6 mm) fylles av gullet i samme utskrift
            ned &= z > 0.65
        stor = 0.0
        if ned.any():
            for f in m.submesh([np.where(ned)[0]], append=True).split(only_watertight=False):
                e = np.sort(f.extents[:2])
                flat = f.face_normals[:, 2].max() < -0.99
                if e[0] > (13.0 if flat else 3.0):
                    stor += f.area
        meld(stor < 1.0, f"{p}: {m.area_faces[ned].sum():.1f} mm² nedovervendt, {stor:.1f} mm² som trenger støtte")

# 5. K2-plater
sys.path.insert(0, os.path.join(HER, "..", "fjernkontroll"))
import lag_3mf as L   # noqa: E402
L.STL = "stl"
INNST = {"enable_support": "0", "initial_layer_speed": "20", "initial_layer_infill_speed": "30", "elefant_foot_compensation": "0.15"}
FARGER = {1: "#ECE9E3", 2: "#2E2D2C", 3: "#D99E40", 4: "#DDE6EA"}
for k, tittel in (("c3", "ESP32-C3 SuperMini"), ("d1mini", "Wemos D1 mini")):
    for topp, navn, tekst in (("topp", f"skjold-ir-{k}-k2.3mf", "tre lysdioder"),
                              ("topp_opp", f"skjold-ir-{k}-k2-opp.3mf", "fire lysdioder (én rett opp)")):
        L.OBJ_INNST = {f"{k}/bunn": INNST, f"{k}/{topp}": INNST, f"{k}/lysleder": {"enable_support": "0"}}
        L.write(navn, f"Skjold IR ({tittel}, {tekst}) – topp med gullring, bunn og lysleder (PLA/PETG)", [
            (f"{k}/{topp}", "Topp (toppflaten ned, Bone White)", 1, (10, 10), None),
            (f"{k}/gull", "Gullring (felt inn i toppen)", 3, None, f"{k}/{topp}"),
            (f"{k}/bunn", "Bunn (undersiden ned, mørk)", 2, (80, 10), None),
            (f"{k}/lysleder", "Lysleder (klar PETG, toppenden ned)", 4, (150, 10), None)], FARGER)

print("ALT OK" if ok else "NOE FEILET")

# 6. bilder (OpenSCAD, Tomorrow, 1600 × 1100), lys og mørk
if "bilder" in sys.argv:
    os.makedirs("render", exist_ok=True)
    pre = [] if os.environ.get("DISPLAY") or not shutil.which("xvfb-run") else ["xvfb-run", "-a"]
    SKRA = "0,0,8,58,0,25,175"
    OVENFRA = "0,0,10,20,0,15,165"
    EKSP = "0,0,10,62,0,25,240"
    INNI = "0,2,6,48,0,22,160"
    FORFRA = "0,0,10,84,0,0,150"
    BILDER = [("01_skra_lys", "samlet", SKRA, "lys", "c3", ()), ("02_ovenfra_lys", "samlet", OVENFRA, "lys", "c3", ()),
              ("03_eksplodert_lys", "eksplodert", EKSP, "lys", "c3", ()), ("04_skra_mork", "samlet", SKRA, "mork", "c3", ()),
              ("05_ovenfra_mork", "samlet", OVENFRA, "mork", "c3", ()), ("06_eksplodert_mork", "eksplodert", EKSP, "mork", "c3", ()),
              ("07_inni", "inni", INNI, "lys", "c3", ()), ("08_forfra", "samlet", FORFRA, "lys", "c3", ()),
              ("09_d1mini_inni", "inni", INNI, "lys", "d1mini", ()),
              ("10_opp", "samlet", SKRA, "lys", "c3", ("-D", "led_opp=true")),
              ("11_undersiden", "undersiden", "0,0,0,200,0,20,170", "lys", "c3", ())]
    procs = []
    for fil, part, cam, farge, k, ekstra in BILDER:
        procs.append(subprocess.Popen(pre + ["openscad", "-q", "--colorscheme=Tomorrow", "--imgsize=1600,1100", "--projection=p",
                                             f"--camera={cam}", "-D", f'part="{part}"', "-D", f'kort="{k}"', "-D", f'farge="{farge}"',
                                             *ekstra, "-o", f"render/{fil}.png", SC]))
    kjor(procs)
    print("skrev", len(BILDER), "bilder i render/")

sys.exit(0 if ok else 1)
