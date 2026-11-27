"""Kontroll av Skjold Jord (kjøres av lag_jord.sh). Krever trimesh og manifold3d.
  1. utskrifts-STL-ene er vanntette, ligger på plata (min z = 0) og får plass på 250 × 250 mm
  2. ingen deler overlapper i montert stilling, utenom det som skal presses: mansjetten mot sensorkortet og kroppen,
     pakningsleppen mot kroppen og USB-pluggen mot kroppen (TPU, tetter med overlapp)
  3. referansedelene (sensorkort, XIAO, batteri) har plass: ingen kollisjon med huset eller hverandre"""
import itertools
import sys
import warnings

import trimesh

warnings.filterwarnings("ignore", category=RuntimeWarning)
feil = []
for n in ["kropp", "lokk", "logo", "pakning", "mansjett", "plugg"]:
    m = trimesh.load(f"stl/{n}.stl")
    if not m.is_watertight: feil.append(f"{n}: ikke vanntett")
    if abs(m.bounds[0][2]) > 0.02: feil.append(f"{n}: ligger ikke på plata (min z {m.bounds[0][2]:.2f})")
    if (m.bounds[1][:2] - m.bounds[0][:2]).max() > 250: feil.append(f"{n}: for stor for plata")
A = {n: trimesh.load(f"asm/{n}.stl") for n in ["kropp", "lokk", "logo", "pakning", "mansjett", "plugg", "sensor", "xiao", "batteri"]}
TETT = {("kropp", "mansjett"), ("mansjett", "sensor"), ("kropp", "pakning"), ("kropp", "plugg"), ("kropp", "logo"), ("lokk", "pakning")}
for a, b in itertools.combinations(A, 2):
    (a0, a1), (b0, b1) = A[a].bounds, A[b].bounds
    if (a1 < b0).any() or (b1 < a0).any():
        continue
    v = A[a].intersection(A[b], engine="manifold").volume
    lov = (a, b) in TETT or (b, a) in TETT
    print(f"{a:9s} ∩ {b:9s} {v:8.3f} mm³{'  (tetter)' if lov else ''}")
    if v > 0.05 and not lov:
        feil.append(f"{a} og {b} overlapper ({v:.2f} mm³)")
k = A["kropp"]
print("kroppen:", (k.bounds[1] - k.bounds[0]).round(1), "mm (med spydet)")
if feil:
    print("FEIL:\n  " + "\n  ".join(feil)); sys.exit(1)
print("OK")
