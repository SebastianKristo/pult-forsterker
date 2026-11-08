"""Bygg tastekort A i KiCad 7 med samme rørlegging som hovedkortet (../hovedkort/lag_hovedkort.py): omriss fra
kabinettet (../tastekort/kort_omriss.dxf), plassering, nett, GND-flater, ruting med Freerouting, DRC, Gerber/bor,
BOM og CPL for JLCPCB, og bilder.

Bruk:  python3 tastekort_a/lag_tastekort_a.py [--uten-ruting | --ruting]   (FREEROUTING=/sti/til/freerouting-2.x.jar)"""
import os
import re
import sys

import pcbnew

HER = os.path.dirname(os.path.abspath(__file__))
FK = os.path.dirname(HER)
sys.path.insert(0, HER)
sys.path.insert(0, os.path.join(FK, "hovedkort"))
import kretser_a  # noqa: E402
import lag_hovedkort as lh  # noqa: E402

L = kretser_a.L
mm = pcbnew.FromMM
V = lh.V


def dxf_linjer(fil):
    t = open(fil).read().split("\n")
    t = [s.strip() for s in t]
    ut, i = [], 0
    while i < len(t):
        if t[i] == "LINE" and (i == 0 or t[i - 1] == "0"):
            d, j = {}, i + 1
            while j < len(t) - 1 and t[j] != "0":
                d[t[j]] = t[j + 1]; j += 2
            ut.append(((float(d["10"]), float(d["20"])), (float(d["11"]), float(d["21"]))))
            i = j
        else:
            i += 1
    return ut


def omriss_poly():
    """Tastekortets omriss fra DXF-en (origo nede til venstre på kortet, halen ned) → (x, n) som i skjold_fjernkontroll.scad:
    x = x_dxf + 3,2 og n = PCB_N1 − y_dxf."""
    from shapely.geometry import LineString, Polygon
    from shapely.ops import polygonize, unary_union
    N1 = kretser_a.taster.PCB_N1
    linjer = [LineString([(a[0] + 3.2, N1 - a[1]), (b[0] + 3.2, N1 - b[1])]) for a, b in dxf_linjer(os.path.join(FK, "tastekort", "kort_omriss.dxf"))]
    flater = list(polygonize(unary_union(linjer)))
    return max(flater, key=lambda p: p.area)


def omriss_punkter():
    return list(omriss_poly().exterior.coords)[:-1]


def lag_brett():
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(2)
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(mm(1.0))
    ds.m_TrackMinWidth = mm(0.15); ds.m_MinClearance = mm(0.15)
    ds.m_ViasMinSize = mm(0.6); ds.m_MinThroughDrill = mm(0.3)
    ds.m_HoleClearance = mm(0.25); ds.m_CopperEdgeClearance = mm(0.3); ds.m_SolderMaskMinWidth = 0
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(mm(0.15)); nc.SetTrackWidth(mm(0.2)); nc.SetViaDiameter(mm(0.6)); nc.SetViaDrill(mm(0.3))
    p = omriss_poly()
    for ring in [p.exterior] + list(p.interiors):
        pts = list(ring.coords)[:-1]
        for a, c in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(*a)); s.SetEnd(V(*c))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            b.Add(s)
    return b


def silke(b):
    s = pcbnew.PCB_TEXT(b)
    s.SetText("SKJOLD TASTEKORT A v1")
    s.SetLayer(pcbnew.B_SilkS)
    s.SetTextSize(V(0.9, 0.9)); s.SetTextThickness(mm(0.15))
    s.SetPosition(V(27.5, 132.0)); s.SetMirrored(True)
    b.Add(s)


def flater(b, nett):
    pts = omriss_punkter()
    for lag in (pcbnew.F_Cu, pcbnew.B_Cu):
        lh.sone(b, lag, nett["GND"], pts)


# lag_hovedkort.py brukes med tastekortets data
lh.KOMP = kretser_a.KOMP
lh.kretser = kretser_a
lh.UT = HER
lh.NAVN = "skjold-tastekort-a"
lh.omriss_poly = omriss_poly
lh.omriss_punkter = omriss_punkter
lh.silke = silke
lh.FPLIB = "/usr/share/kicad/footprints"
for i, (ref, fp, verdi, side, x, n, rot, puter) in enumerate(lh.KOMP):   # eget fotavtrykk (bryterne): relativ sti
    lib, navn = fp.split(":")
    if lib.startswith("/"):
        lh.KOMP[i] = (ref, os.path.relpath(lib[:-len(".pretty")], lh.FPLIB) + ":" + navn, verdi, side, x, n, rot, puter)
_b = omriss_poly().bounds
lh.X0, lh.N0, lh.X1, lh.N1 = _b[0], _b[1], _b[2], _b[3]
lh.ANTENNE = (-9, -9, -9, -9)   # ingen antenne her (bildene tegner rammen utenfor)


def pinnetabell():
    """pinner.csv: TCA9555-pinnene (tast/funksjon), JST-SH-kontakten og loddeputene."""
    import csv
    rader = [("del", "pinne", "nett", "til")]
    pute = lambda pin: str(4 + pin) if pin < 8 else str(13 + pin - 8)
    for f, x, n, p in kretser_a.TASTER:
        rader.append(("U1 TCA9555 0x20", f"P{p // 8}_{p % 8} (pinne {pute(p)})", f"K_{f.upper()}", f"tast «{f}» (SW{p + 1})"))
    rader.append(("U1 TCA9555 0x20", "P1_6 (pinne 19)", "SKJ", "skjermstrøm: AO3401-gaten (utgang, lav = på)"))
    rader.append(("U1 TCA9555 0x20", "P1_7 (pinne 20)", "DOKK", "dokken: POGO+ via 68 kΩ / 100 kΩ (høy = i dokken)"))
    for p, nett, til in (("1", "3V3", "SuperMini 3V3"), ("2", "GND", "SuperMini GND"), ("3", "SDA", "SuperMini GPIO5"),
                         ("4", "SCL", "SuperMini GPIO6"), ("5", "INT", "SuperMini GPIO2 (vekking)")):
        rader.append(("J1 JST-SH 5 p", p, nett, til))
    for ref, fp, verdi, side, x, n, rot, puter in kretser_a.KOMP:
        if ref.startswith("TP"):
            rader.append((ref, "pute", puter["1"], verdi))
    with open(os.path.join(HER, "pinner.csv"), "w", newline="") as f:
        csv.writer(f).writerows(rader)


def bilde_3d(b):
    """render_3d.png: kortet med bryterne (oppsiden) og bokser for delene på undersiden (OpenSCAD)."""
    import subprocess
    p = omriss_poly()
    ring = lambda r: "[" + ", ".join(f"[{x:.3f}, {-n:.3f}]" for x, n in list(r.coords)[:-1]) + "]"
    deler = []
    for f in b.GetFootprints():
        bb = f.GetBoundingBox(False, False)
        x0, x1, n0, n1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetRight(), bb.GetTop(), bb.GetBottom()))
        ref = f.GetReference()
        if ref.startswith("SW"):
            deler.append(f"color([0.85,0.85,0.85]) translate([{(x0 + x1) / 2:.2f}, {-(n0 + n1) / 2:.2f}, 1]) {{ translate([-2,-2,0]) cube([4,4,1.1]); cylinder(d=2.4, h=1.5, $fn=24); }}")
        elif ref.startswith("TP"):
            deler.append(f"color([0.85,0.7,0.3]) translate([{(x0 + x1) / 2:.2f}, {-(n0 + n1) / 2:.2f}, -0.05]) cylinder(d=1.5, h=0.05, $fn=20);")
        else:
            h = 2.0 if ref.startswith("J") else 1.2 if ref == "U1" else 0.45
            c = "[0.92,0.92,0.88]" if ref.startswith("J") else "[0.12,0.12,0.13]"
            deler.append(f"color({c}) translate([{x0:.2f}, {-n1:.2f}, {-h}]) cube([{x1 - x0:.2f}, {n1 - n0:.2f}, {h}]);")
    scad = (f"color([0.05,0.35,0.18]) linear_extrude(1) difference() {{ polygon({ring(p.exterior)}); "
            + "".join(f"polygon({ring(r)});" for r in p.interiors) + "}\n" + "\n".join(deler))
    fil = os.path.join(HER, "tastekort_a_3d.scad")
    open(fil, "w").write("// Laget av lag_tastekort_a.py – bare for bildet render_3d.png\n" + scad + "\n")
    for navn, kamera in (("render_3d.png", "27.5,-132,0,40,0,15,290"), ("render_3d_under.png", "27.5,-132,0,140,0,-15,290")):
        subprocess.run(["openscad", "-q", "--colorscheme=Tomorrow", "--imgsize=1400,1000", "--projection=p",
                        f"--camera={kamera}", "-o", os.path.join(HER, navn), fil], check=False)


def main():
    b = lag_brett()
    nett = lh.plasser(b)
    flater(b, nett)
    pcb = os.path.join(HER, lh.NAVN + ".kicad_pcb")
    b.Save(pcb)
    print("lagret", pcb, len(lh.KOMP), "komponenter,", len(nett), "nett")
    if "--uten-ruting" in sys.argv:
        return b
    ses = os.path.join(HER, lh.NAVN + ".ses")
    if "--ruting" in sys.argv or not os.path.exists(ses):
        lh.rut(pcb, os.path.join(HER, lh.NAVN))
    b = lh.importer_ruting(pcb, ses)
    import drc
    feil, adv, eks, _ = drc.kjør(pcb, os.path.join(HER, lh.NAVN + "-drc.rpt"), fyll=False)
    print("DRC-feil:", dict(feil), "· advarsler:", dict(adv))
    z = lh.gerber(b, os.path.join(HER, "gerber"))
    nb, nc, nd = lh.bom_cpl(b)
    print("skrev", os.path.basename(z), f"· BOM {nb} linjer, CPL {nc} deler, {nd} for hånd")
    for f in lh.bilder(b):
        print("skrev", os.path.basename(f))
    pinnetabell()
    bilde_3d(b)
    print("skrev pinner.csv, render_3d.png og render_3d_under.png")
    return b


if __name__ == "__main__":
    main()
