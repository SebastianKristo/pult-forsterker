"""Kontroll av Skjold Fjernkontroll-modellen.

Bruk:  python3 sjekk_modell.py [mappe med A_*.stl i montert stilling] [full|kort]   (standard: asm/ full)
       python3 sjekk_modell.py asm_kort kort   (kort variant: STL-ene ligger i stl_kort/)
STL-ene lages av lag_stl.sh. Krever trimesh og manifold3d. Sjekker:
  1. alle utskrifts-STL-er i stl/ er vanntette, har riktig antall legemer, ligger på platen (min z = 0)
     og passer i Creality K2 (250 × 250 × 250 mm)
  2. ingen deler overlapper i montert stilling (topp, bunn, IR-vindu, logo, hetter, symboler, tastekort med brytere,
     skjermmodul, batteri, SuperMini, lader); par som skal ligge an mot hverandre har bare kontaktflater.
     Hettene sjekkes også mot hverandre (hver hette for seg).
  3. sideveggen er ≥ 1,6 mm (vannrette stråler inn i topp + bunn utenom USB-C, IR-vinduet og lysdiodehullene),
     toppflaten ≥ 1,5 mm utenom hullene, skjermlomma (0,8 mm leppe) og SKJOLD (felt 0,5 mm inn), gulvet ≥ 1,5 mm utenom skruehodene
  4. minst 1,4 mm materiale mellom tastehullene i toppen (fra taster.py)
  5. hver hette står 0,1 mm over bryteren sin (forvandring) og har klaring rundt i hullet
  6. tykkelse: kroppen ≤ 14 mm, høyeste tast ≤ 15,5 mm (mål ≤ 18 mm)"""
import itertools
import sys

import numpy as np
import trimesh
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning)   # trimesh: tomme snitt gir 0/0 i tyngdepunktet

import taster

ASM = sys.argv[1] if len(sys.argv) > 1 else "asm"
VARIANT = sys.argv[2] if len(sys.argv) > 2 else "full"
taster.bruk(VARIANT)
STL = "stl" if VARIANT == "full" else "stl_kort"
W, L, H = taster.W, taster.L, 13.5
print(f"Variant: {VARIANT} ({len(taster.brytere())} taster, {len(taster.HETTER)} hetter)")
ok = True


def melding(god, tekst):
    global ok
    ok &= bool(god)
    print(f"{'OK ' if god else 'FEIL'} {tekst}")


# ---------- 1. utskriftsdelene ----------
ANTALL = {"knapper": None, "knapper_lys": 4, "gull": 2, "farge_rod": 1, "farge_gronn": 1, "farge_gul": 1, "farge_bla": 1,
          "topp": 1, "bunn": 1, "ir_vindu": 1, "bryterbrett": 1, "logo": 6, "symboler_lyse": None, "symboler_morke": None}
mork = sum(1 for h in taster.HETTER if h[8] == "mork")
ANTALL["knapper"] = mork
if VARIANT == "kort":
    del ANTALL["knapper_lys"]   # smarthus-raden finnes ikke
for n, want in ANTALL.items():
    m = trimesh.load(f"{STL}/{n}.stl")
    deler = len(m.split(only_watertight=False))
    paa_plata = abs(m.bounds[0][2]) < 0.02 or n.startswith("symboler")   # symbolene ligger i hettene (samme plassering i 3MF)
    god = m.is_watertight and m.is_volume and (want is None or deler == want) and paa_plata and max(m.extents) <= 250
    melding(god, f"{n:15s} vanntett={m.is_watertight} legemer={deler} {m.volume/1000:6.2f} cm³ {m.extents.round(1)} mm")

# ---------- 2. overlapp i montert stilling ----------
DELER = ["topp", "bunn", "vindu", "logo", "hetter", "symboler", "kort", "skjerm", "batteri", "mcu", "lader"]
A = {n: trimesh.load(f"{ASM}/{n}.stl") for n in DELER}
TOUCH = {("topp", "logo"), ("hetter", "symboler"), ("bunn", "vindu"), ("topp", "kort"), ("bunn", "kort"), ("topp", "skjerm"),
         ("topp", "bunn")}


def overlapp(a, b):
    if np.any(a.bounds[1] < b.bounds[0]) or np.any(b.bounds[1] < a.bounds[0]):
        return 0.0
    try:
        return a.intersection(b, engine="manifold").volume
    except Exception:
        return float("nan")


feil = []
for x, y in itertools.combinations(DELER, 2):
    v = overlapp(A[x], A[y])
    lim = 0.05 if (x, y) in TOUCH or (y, x) in TOUCH else 0.001
    if not v <= lim:
        feil.append(f"{x} × {y}: {v:.3f} mm³")
hett = A["hetter"].split(only_watertight=False)
for a, b in itertools.combinations(hett, 2):
    v = overlapp(a, b)
    if not v <= 0.001:
        feil.append(f"to hetter ved {a.centroid[:2].round(1)} og {b.centroid[:2].round(1)}: {v:.3f} mm³")
melding(not feil and len(hett) == len(taster.HETTER),
        f"ingen overlapp i montert stilling ({len(DELER)} deler, {len(hett)} hetter)" if not feil else "overlapp: " + "; ".join(feil))

# ---------- 3. veggtykkelse ----------
skall = A["topp"].union(A["bunn"], engine="manifold")


def segment(mesh, o, d):
    """Tykkelsen av det første materialet strålen treffer."""
    loc, _, _ = mesh.ray.intersects_location([o], [d])
    if len(loc) < 2:
        return None
    s = sorted(np.linalg.norm(loc - np.array(o), axis=1))
    return s[1] - s[0]


HULL_SIDE = [("hale", W/2 - 5.6, W/2 + 5.6, 1.8, 7.0), ("nese", W/2 - 16.2, W/2 + 16.2, 1.7, 7.5),
             ("hale", W/2 - 9.4, W/2 - 7.6, 3.3, 5.5), ("hale", W/2 + 7.6, W/2 + 9.4, 3.3, 5.5)]
tynn = []
for z in np.arange(2.0, 11.8, 0.6):
    for y in np.arange(14, L - 14, 3):
        for side, o, d in (("v", [-5, y, z], [1, 0, 0]), ("h", [W + 5, y, z], [-1, 0, 0])):
            s = segment(skall, o, d)
            if s is None or s < 1.59:
                tynn.append((side, round(float(y), 1), round(float(z), 1), s and round(s, 2)))
    for x in np.arange(14, W - 14, 2):
        for side, o, d in (("hale", [x, -5, z], [0, 1, 0]), ("nese", [x, L + 5, z], [0, -1, 0])):
            if any(side == f and u0 <= x <= u1 and v0 <= z <= v1 for f, u0, u1, v0, v1 in HULL_SIDE):
                continue
            s = segment(skall, o, d)
            if s is None or s < 1.59:
                tynn.append((side, round(float(x), 1), round(float(z), 1), s and round(s, 2)))
melding(not tynn, "sideveggen er ≥ 1,6 mm rundt hele (utenom USB-C, IR-vinduet og lysdiodehullene)" if not tynn else
        f"sideveggen er tynnere enn 1,6 mm på {len(tynn)} punkter, f.eks. {tynn[:6]}")

# topp og gulv: loddrette stråler
rot, gulv = [], []
SKRUER = [(7.5, L - 5.5), (W - 7.5, L - 5.5), (4.9, 8), (W - 4.9, 8), (W/2, L - 135)]   # skruehodene og forborene
scr = (W/2 - 25.3, W/2 + 25.3, L - 8.1 - 69.8, L - 8.1)   # lomma for 2,8″-modulen (50,6 × 69,8 mm)
for x in np.arange(5.13, W - 5, 1.0):
    for y in np.arange(5.37, L - 5, 1.0):
        s = segment(A["topp"], [x, y, H + 5], [0, 0, -1])
        if s is not None and s < 1.49 and not (scr[0] <= x <= scr[1] and scr[2] <= y <= scr[3]) and not (W/2 - 14 <= x <= W/2 + 14 and 4 <= y <= 10):   # SKJOLD er felt 0,5 mm inn
            rot.append((round(float(x), 1), round(float(y), 1), round(s, 2)))
        g = segment(A["bunn"], [x, y, -5], [0, 0, 1])
        if g is None or g < 1.49:
            gulv.append((round(float(x), 1), round(float(y), 1), g and round(g, 2)))
gulv = [p for p in gulv if not any(np.hypot(p[0] - sx, p[1] - sy) < 2.4 for sx, sy in SKRUER)]
rot = [p for p in rot if not any(np.hypot(p[0] - sx, p[1] - sy) < 1.0 for sx, sy in SKRUER)]   # forboret til 0,8 mm under toppen
melding(not rot, "toppflaten er ≥ 1,5 mm utenom tastehullene og skjermlomma" if not rot else f"tynn topp: {rot[:6]}")
melding(not gulv, "gulvet er ≥ 1,5 mm utenom skruehodene" if not gulv else f"tynt gulv: {gulv[:6]}")

# ---------- 4. materiale mellom tastehullene ----------
steg = taster.sjekk_steg()
melding(not steg, f"≥ {taster.MIN_STEG} mm mellom alle tastehull" if not steg else f"for smalt mellom: {steg}")

# ---------- 5. forvandring og klaring ----------
bryter_topp = 8.2 + 1.0 + 1.5
hette_bunn = min(h.bounds[0][2] for h in hett)
melding(abs(hette_bunn - bryter_topp - 0.1) < 0.02, f"hettene står {hette_bunn - bryter_topp:.2f} mm over bryterne (forvandring)")

# ---------- 6. tykkelse ----------
kropp = max(A["topp"].bounds[1][2], A["bunn"].bounds[1][2]) - A["bunn"].bounds[0][2]
tast = A["hetter"].bounds[1][2]
mal = A["topp"].bounds[1] - A["bunn"].bounds[0]
melding(kropp <= 14.0 and tast <= 15.5, f"mål {mal[0]:.1f} × {mal[1]:.1f} mm, kropp {kropp:.1f} mm tykk, med taster {tast:.1f} mm")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
