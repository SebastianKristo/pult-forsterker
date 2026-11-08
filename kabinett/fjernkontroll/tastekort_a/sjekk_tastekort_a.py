"""Kontroll av tastekort A. Nettlista (kretser_a.py) og, når kortet er laget, kortet og kabinettet:

  1. TCA9555: VCC = 3V3, GND, adresse 0x20 (A0–A2 til GND), SDA/SCL/INT, 100 nF ved VCC, og alle 24 pinner er koblet
  2. hver tast går til sin egen TCA-pinne (samme rekkefølge som fastvaren) og til GND; ingen nett med bare én pinne
  3. pull-up på SDA, SCL og INT; dokk-deleren 68 k / 100 k på P1_7
  4. bryterne står nøyaktig der taster.py setter tastene i oppsett A (± 0,01 mm), så hettene treffer
  5. kortet: nettene er de samme som i nettlista, og alt er rutet
  6. kabinettet (håndkoblet, standard): kortet ligger der tastekortet lå, og komponentene på undersiden går minst
     0,5 mm klar av bunnen og innmaten (SuperMini, lader, batteri, ledninger …)

Bruk:  python3 tastekort_a/sjekk_tastekort_a.py"""
import math
import os
import sys

import numpy as np

HER = os.path.dirname(os.path.abspath(__file__))
FK = os.path.dirname(HER)
sys.path.insert(0, HER)
import kretser_a  # noqa: E402

ok = True


def melding(god, tekst):
    global ok
    ok &= bool(god)
    print(f"{'OK ' if god else 'FEIL'} {tekst}")


K = {r: (fp, v, side, x, n, rot, p) for r, fp, v, side, x, n, rot, p in kretser_a.KOMP}
N = kretser_a.netter()
u = K["U1"][6]
pute = lambda pin: str(4 + pin) if pin < 8 else str(13 + pin - 8)
krav = {"24": "3V3", "12": "GND", "1": "INT", "22": "SCL", "23": "SDA", "21": "GND", "2": "GND", "3": "GND"}
feil = [f"U1.{p} = {u.get(p)}" for p, v in krav.items() if u.get(p) != v]
mangler = [str(i) for i in range(1, 25) if str(i) not in u]
kond = any(set(K[r][6].values()) == {"3V3", "GND"} and K[r][1] == "100nF" and math.hypot(K[r][3] - K["U1"][3], K[r][4] - K["U1"][4]) < 6 for r in K)
melding(not feil and not mangler and kond, "TCA9555: VCC/GND, adresse 0x20, I²C og INT, 100 nF innen 6 mm, alle 24 pinner koblet"
        if not (feil or mangler) else f"TCA9555: {feil} mangler {mangler}")

tast_feil = []
for f, x, n, p in kretser_a.TASTER:
    nett = f"K_{f.upper()}"
    if u.get(pute(p)) != nett or sorted(N[nett]) != sorted([("U1", pute(p)), (f"SW{p + 1}", "1")]) or K[f"SW{p + 1}"][6]["2"] != "GND":
        tast_feil.append(f)
enslige = [n for n, p in N.items() if len(p) < 2]
melding(not tast_feil and not enslige, f"14 taster: hver til sin TCA-pinne (P0_0 … P1_5) og GND; ingen nett med én pinne"
        if not (tast_feil or enslige) else f"feil: {tast_feil} enslige {enslige}")

pu = lambda nett, til="3V3": [r for r in K if r.startswith("R") and set(K[r][6].values()) == {til, nett}]
deler = K["R4"][1] == "68k" and K["R5"][1] == "100k" and u.get(pute(15)) == "DOKK" and u.get(pute(14)) == "SKJ"
melding(all(pu(n) for n in ("SDA", "SCL", "INT")) and deler, "pull-up på SDA, SCL og INT; P1_6 = skjermstrøm, P1_7 = dokken via 68 k / 100 k")

sys.path.insert(0, FK)
import taster  # noqa: E402
taster.bruk("kort")
fasit = {f: (x, n) for f, x, n, p in taster.tastekort_a()}
k = taster.kart("rutenett")
avvik = []
for bid, nv, x, n, hid in taster.brytere():
    f = k[int(bid[1:])] if hid == "front" else bid
    if f in fasit and math.hypot(fasit[f][0] - x, fasit[f][1] - n) > 0.01:
        avvik.append(f)
for f, x, n, p in kretser_a.TASTER:
    if math.hypot(K[f"SW{p + 1}"][3] - x, K[f"SW{p + 1}"][4] - n) > 0.01:
        avvik.append(f)
melding(not avvik and len(fasit) == 14, "bryterne står der oppsett A har tastene (14 av 14)" if not avvik else f"avvik: {avvik}")

pcb = os.path.join(HER, "skjold-tastekort-a.kicad_pcb")
try:
    import pcbnew
    b = pcbnew.LoadBoard(pcb)
    avv = []
    for f in b.GetFootprints():
        r = f.GetReference()
        for p in f.Pads():
            if not p.GetNumber():
                continue
            vil = K[r][6].get(p.GetNumber(), "") if r in K else ""
            if (vil or p.GetNetname()) and vil != p.GetNetname():
                avv.append(f"{r}.{p.GetNumber()}")
    melding(not avv, "nettene på kortet er de samme som i nettlista" if not avv else f"avvik: {avv[:8]}")
    ikke = b.GetConnectivity().GetUnconnectedCount(True)
    melding(ikke == 0 and len(b.GetTracks()) > 0, f"alt er rutet ({len(b.GetTracks())} spor/viaer, {ikke} ukoblede)")
    # kabinettet: komponentboksene på undersiden mot bunnen og innmaten (asm/ fra lag_stl.sh, standard, håndkoblet)
    import trimesh
    zK = 8.2   # tastekortets underside i det håndkoblede kabinettet
    L = kretser_a.L
    bokser = []
    for f in b.GetFootprints():
        if f.GetLayer() != pcbnew.B_Cu or f.GetReference().startswith("TP"):
            continue
        bb = f.GetCourtyard(pcbnew.B_CrtYd).BBox() if f.GetCourtyard(pcbnew.B_CrtYd).OutlineCount() else f.GetBoundingBox(False, False)
        x0, x1 = pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())
        n0, n1 = pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())
        h = {"TSSOP": 1.2, "JST_SH": 3.0, "Hirose": 2.0, "R_0402": 0.4, "C_0402": 0.5}
        hh = next(v for kk, v in h.items() if kk in str(f.GetFPID().GetLibItemName()))
        boks = trimesh.creation.box(extents=[x1 - x0, n1 - n0, hh])
        boks.apply_translation([(x0 + x1) / 2, L - (n0 + n1) / 2, zK - hh / 2])
        bokser.append((f.GetReference(), boks))
    asm = os.path.join(FK, "asm")
    innmat = {p: trimesh.load(os.path.join(asm, f"{p}.stl")) for p in ("bunn", "batteri", "mcu", "lader", "ir", "vib", "motor", "ledninger", "flex", "pogo") if os.path.exists(os.path.join(asm, f"{p}.stl"))}
    naer = []
    minst = 99
    for ref, bx in bokser:
        for p, m in innmat.items():
            if p == "flex" and ref in ("J2", "J3"):
                continue   # flatkablene går inn i kontaktene
            d = trimesh.proximity.closest_point(m, bx.sample(400))[1].min()
            i_ = trimesh.boolean.intersection([bx, m])
            if not i_.is_empty and i_.volume > 0.01:
                d = -1
            minst = min(minst, d)
            if d < 0.5:
                naer.append(f"{ref}–{p} {d:.2f} mm")
    melding(not naer, f"kabinettet (håndkoblet): komponentene på undersiden går minst {minst:.2f} mm klar av bunnen og innmaten"
            if not naer else f"for nær: {naer[:6]}")
    ytre = trimesh.creation.extrude_polygon(__import__("shapely.affinity", fromlist=["x"]).scale(
        __import__("lag_tastekort_a").omriss_poly(), 1, -1, origin=(0, L / 2)), 1.0)
    ytre.apply_translation([0, 0, zK])
    kort_gml = trimesh.load(os.path.join(asm, "kort.stl"))
    melding(abs(ytre.volume - 1.0 * __import__("lag_tastekort_a").omriss_poly().area) < 1 and
            np.allclose(ytre.bounds[:, :2], kort_gml.bounds[:, :2], atol=0.3),
            f"omrisset er det samme som tastekortet i kabinettet (x {ytre.bounds[0][0]:.1f}–{ytre.bounds[1][0]:.1f}, "
            f"y {ytre.bounds[0][1]:.1f}–{ytre.bounds[1][1]:.1f})")
except ImportError:
    melding(False, "pcbnew mangler")

print("ALT OK" if ok else "NOE FEILET")
sys.exit(0 if ok else 1)
