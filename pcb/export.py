#!/usr/bin/env python3
"""Etter ruting: importer SES, fyll soner, kjør DRC, eksporter Gerber/drill/CPL/BOM til produksjon/."""
import os, subprocess, csv, zipfile, json, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "ki_pultforsterker_main.kicad_pcb")
SES = os.path.join(HERE, "board.ses")
OUT = os.path.join(HERE, "produksjon")
os.makedirs(OUT, exist_ok=True)

board = pcbnew.LoadBoard(PCB)
def import_ses(board, path):
    """Leser Specctra-SES (Freerouting) og lager spor/vias. Enheter: resolution um N -> 1/N um; y er speilet."""
    import re
    txt = open(path).read()
    res = int(re.search(r"\(resolution um (\d+)\)", txt).group(1))
    scale = 1000.0 / res   # -> nm
    layers = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    vias = {m.group(1): (int(m.group(2)), ) for m in re.finditer(r'\(padstack "([^"]+)"\s*\(shape\s*\(circle F\.Cu (\d+)', txt)}
    drills = {k: int(k.split("_")[1].split(":")[1]) * 1000 for k in vias}   # "Via[0-1]_800:400_um" -> 400 um
    nets = {n.GetNetname(): n for n in board.GetNetInfo().NetsByName().values()}
    for ref in list(board.GetTracks()):
        board.Remove(ref)
    n_t = n_v = 0
    for m in re.finditer(r"\(net (\S+)(.*?)\n      \)", txt, re.S):
        name, body = m.group(1).strip('"'), m.group(2)
        net = nets.get(name)
        if net is None:
            print("ukjent nett i SES:", name); continue
        for w in re.finditer(r"\(path (\S+) (\d+)((?:\s+-?\d+\s+-?\d+)+)", body):
            layer, width = layers[w.group(1)], int(int(w.group(2)) * scale)
            pts = [int(float(v) * scale) for v in w.group(3).split()]
            for i in range(0, len(pts) - 2, 2):
                t = pcbnew.PCB_TRACK(board); t.SetLayer(layer); t.SetWidth(width); t.SetNet(net)
                t.SetStart(pcbnew.VECTOR2I(pts[i], -pts[i + 1])); t.SetEnd(pcbnew.VECTOR2I(pts[i + 2], -pts[i + 3])); board.Add(t); n_t += 1
        for v in re.finditer(r'\(via "([^"]+)" (-?\d+) (-?\d+)', body):
            via = pcbnew.PCB_VIA(board); via.SetPosition(pcbnew.VECTOR2I(int(int(v.group(2)) * scale), -int(int(v.group(3)) * scale)))
            via.SetWidth(int(vias[v.group(1)][0] * scale)); via.SetDrill(drills[v.group(1)]); via.SetNet(net); via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(via); n_v += 1
    print(f"SES: {n_t} sporsegmenter, {n_v} vias")

if os.path.exists(SES) and "--no-ses" not in sys.argv:
    import_ses(board, SES)

# Bredere strøm-/høyttalerspor der de ikke er inntil fine pads (Freerouting ruter med smal bredde ved IC-ene)
WIDEN = {"VIN24": 2.0, "24V_IN": 2.0, "SPK_LN": 1.5, "SPK_LP": 1.5, "SPK_RN": 1.5, "SPK_RP": 1.5, "OUTNL": 1.2, "OUTPL": 1.2, "OUTNR": 1.2, "OUTPR": 1.2, "5V": 1.0, "BUCK_SW": 1.2}
fine_pads = [pd.GetPosition() for fp in board.GetFootprints() for pd in fp.Pads() if min(pd.GetSize().x, pd.GetSize().y) < pcbnew.FromMM(1.3)]
def near_fine(pt, r=pcbnew.FromMM(1.6)):
    return any(abs(pt.x - q.x) < r and abs(pt.y - q.y) < r for q in fine_pads)
n_w = 0
for t in board.GetTracks():
    if t.GetClass() != "PCB_TRACK": continue
    w = WIDEN.get(t.GetNetname())
    if w and not near_fine(t.GetStart()) and not near_fine(t.GetEnd()):
        t.SetWidth(pcbnew.FromMM(w)); n_w += 1
print("utvidet spor:", n_w)
# flytt referansetekst til Fab-laget (silk ellers i konflikt med pads på tett kort)
for fp in board.GetFootprints():
    fp.Reference().SetLayer(pcbnew.F_Fab); fp.Reference().SetVisible(True)
filler = pcbnew.ZONE_FILLER(board); filler.Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)

# DRC (KiCad 7: pcbnew.WriteDRCReport)
rep = os.path.join(OUT, "drc_report.txt")
pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
txt = open(rep).read()
import re as _re
viol = _re.findall(r"^\[(\w+)\]: (.*)$", txt, _re.M)
unc = txt.count("[unconnected_items]")
print(f"DRC: {len(viol)} meldinger ({unc} ukoblede). Typer:", sorted(set(v[0] for v in viol)))
for t, d in viol[:20]:
    print("  -", t, d[:110])

# Gerber + drill
gdir = os.path.join(OUT, "gerber"); os.makedirs(gdir, exist_ok=True)
for f in os.listdir(gdir): os.remove(os.path.join(gdir, f))
subprocess.run(["kicad-cli", "pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts",
                "--subtract-soldermask", "--use-drill-file-origin", "-o", gdir + "/", PCB], check=True)
subprocess.run(["kicad-cli", "pcb", "export", "drill", "--format", "excellon", "--excellon-units", "mm", "--generate-map", "--map-format", "gerberx2",
                "--drill-origin", "absolute", "-o", gdir + "/", PCB], check=True)
with zipfile.ZipFile(os.path.join(OUT, "ki_pultforsterker_main_gerber.zip"), "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(os.listdir(gdir)): z.write(os.path.join(gdir, f), f)

# CPL (JLCPCB/PCBWay-format: Designator, Mid X, Mid Y, Layer, Rotation)
pos = os.path.join(OUT, "cpl_tmp.csv")
subprocess.run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "--smd-only", "-o", pos, PCB], check=True)
bom = {r["Designator"]: r for r in csv.DictReader(open(os.path.join(HERE, "bom.csv")))}
with open(os.path.join(OUT, "ki_pultforsterker_main_cpl.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for row in csv.DictReader(open(pos)):
        ref = row["Ref"]
        if ref in bom and bom[ref]["LCSC"]:
            w.writerow([ref, f'{float(row["PosX"]):.3f}mm', f'{-float(row["PosY"]):.3f}mm', "Top", row["Rot"]])
os.remove(pos)
# BOM gruppert (JLCPCB-format: Comment, Designator, Footprint, LCSC)
groups = {}
for ref, r in bom.items():
    if not r["LCSC"]: continue
    groups.setdefault((r["Value"], r["Footprint"], r["LCSC"]), []).append(ref)
with open(os.path.join(OUT, "ki_pultforsterker_main_bom.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([val, ",".join(refs), fp, lcsc])
# bilder
for layers, name in [("F.Cu,F.SilkS,F.Mask,Edge.Cuts", "top"), ("B.Cu,B.SilkS,Edge.Cuts", "bottom")]:
    subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", os.path.join(OUT, f"board_{name}.svg"), PCB], check=True)
print("Ferdig ->", OUT)
