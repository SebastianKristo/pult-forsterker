#!/usr/bin/env python3
"""Etter ruting: importer SES, fyll soner, kjør DRC, eksporter Gerber/drill/CPL/BOM til produksjon/."""
import os, subprocess, csv, zipfile, json, sys
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "ki_pultforsterker_main.kicad_pcb")
SES = os.path.join(HERE, "board.ses")
OUT = os.path.join(HERE, "produksjon")
os.makedirs(OUT, exist_ok=True)

def ses_to_sexpr(path, nets):
    """Specctra-SES (Freerouting) -> KiCad s-expr (segment/via). Enheter: resolution um N; y speilet."""
    import re
    txt = open(path).read()
    res = int(re.search(r"\(resolution um (\d+)\)", txt).group(1)); k = 1000.0 / res / 1e6   # -> mm
    vias = {m.group(1): int(m.group(2)) for m in re.finditer(r'\(padstack "([^"]+)"\s*\(shape\s*\(circle F\.Cu (\d+)', txt)}
    out = []; n_t = n_v = 0
    for m in re.finditer(r"\(net (\S+)(.*?)\n      \)", txt, re.S):
        name, body = m.group(1).strip('"'), m.group(2)
        if name not in nets: print("ukjent nett i SES:", name); continue
        code = nets[name]
        for w in re.finditer(r"\(path (\S+) (\d+)((?:\s+-?\d+\s+-?\d+)+)", body):
            layer, width = w.group(1), int(w.group(2)) * k
            pts = [float(v) * k for v in w.group(3).split()]
            for q in range(0, len(pts) - 2, 2):
                out.append(f'  (segment (start {pts[q]:.4f} {-pts[q+1]:.4f}) (end {pts[q+2]:.4f} {-pts[q+3]:.4f}) (width {width:.3f}) (layer "{layer}") (net {code}))'); n_t += 1
        for v in re.finditer(r'\(via "([^"]+)" (-?\d+) (-?\d+)', body):
            d = vias[v.group(1)] * k; drill = int(v.group(1).split("_")[1].split(":")[1]) / 1000
            out.append(f'  (via (at {int(v.group(2))*k:.4f} {-int(v.group(3))*k:.4f}) (size {d:.3f}) (drill {drill:.3f}) (layers "F.Cu" "B.Cu") (net {code}))'); n_v += 1
    print(f"SES: {n_t} sporsegmenter, {n_v} vias")
    return "\n".join(out)

# 1) regenerer kortet uten spor, 2) lim inn SES-rutingen som tekst, 3) last inn i pcbnew
subprocess.run([sys.executable, os.path.join(HERE, "build_board.py")], check=True, capture_output=True)
pcb_txt = open(PCB).read()
if os.path.exists(SES) and "--no-ses" not in sys.argv:
    import re as _re
    nets = {m.group(2): int(m.group(1)) for m in _re.finditer(r'\(net (\d+) "([^"]*)"\)', pcb_txt)}
    body = ses_to_sexpr(SES, nets)
    # manuelle spor der Freerouting ga opp
    MANUAL = [   # samme som de faste sporene i board.dsn (Freerouting skriver dem ikke tilbake i SES)
        ("OUTNL", "F.Cu", 0.3, [(87.65, 36.275), (90.5, 36.2)]),
        ("LED_USB_G", "B.Cu", 0.25, [(9.54, 85.72), (12.5, 85.72), (12.5, 98.6), (132.5, 98.6), (132.5, 81.6), (123.175, 81.6)]),
        ("LED_USB_G", "F.Cu", 0.25, [(123.175, 81.6), (123.175, 80.0)]),
        ("OUTPR", "F.Cu", 0.4, [(103.54, 28.5), (103.54, 26.4)]),
        ("OUTPR", "B.Cu", 0.6, [(103.54, 26.4), (127.0, 26.4), (127.0, 41.3)]),
        ("OUTPR", "F.Cu", 0.6, [(127.0, 41.3), (127.05, 43.0)]),
    ]
    MANUAL_VIAS = [("LED_USB_G", (123.175, 81.6)), ("OUTPR", (103.54, 26.4)), ("OUTPR", (127.0, 41.3))]
    for n, layer, w, pts in MANUAL:
        for a, b2 in zip(pts, pts[1:]):
            body += f'\n  (segment (start {a[0]:.4f} {a[1]:.4f}) (end {b2[0]:.4f} {b2[1]:.4f}) (width {w}) (layer "{layer}") (net {nets[n]}))'
    for n, (x, y) in MANUAL_VIAS:
        body += f'\n  (via (at {x:.4f} {y:.4f}) (size 0.6) (drill 0.3) (layers "F.Cu" "B.Cu") (net {nets[n]}))'
    pcb_txt = pcb_txt.rstrip()
    assert pcb_txt.endswith(")")
    pcb_txt = pcb_txt[:-1] + body + "\n)\n"
    open(PCB, "w").write(pcb_txt)
board = pcbnew.LoadBoard(PCB)

# Bredere strøm-/høyttalerspor der de ikke er inntil små pads (Freerouting ruter smalt ved IC-ene)
WIDEN = {"VIN24": 1.5, "24V_IN": 1.5, "SPK_LN": 1.2, "SPK_LP": 1.2, "SPK_RN": 1.2, "SPK_RP": 1.2, "OUTNL": 1.0, "OUTPL": 1.0, "OUTNR": 1.0, "OUTPR": 1.0, "5V": 0.9, "BUCK_SW": 1.0}
fine_pads = [pd.GetPosition() for fp in board.GetFootprints() for pd in fp.Pads() if min(pd.GetSize().x, pd.GetSize().y) < pcbnew.FromMM(1.3)]
def near_fine(pt, r=pcbnew.FromMM(1.8)):
    return any(abs(pt.x - q.x) < r and abs(pt.y - q.y) < r for q in fine_pads)
n_w = 0; orig_w = {}
# GND-spor er overflødige (soner) – fjern dem der de kolliderer med de manuelle sporene
GND_CLEAR = []
for t in list(board.GetTracks()):
    if t.GetClass() == "PCB_TRACK" and t.GetNetname() == "GND":
        sx, sy, ex, ey = pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)
        for (x0, y0, x1, y1, ly) in GND_CLEAR:
            if board.GetLayerName(t.GetLayer()) == ly and (x0 <= sx <= x1 and y0 <= sy <= y1 or x0 <= ex <= x1 and y0 <= ey <= y1):
                board.Remove(t); break
for t in board.GetTracks():
    if t.GetClass() != "PCB_TRACK": continue
    w = WIDEN.get(t.GetNetname())
    if w and not near_fine(t.GetStart()) and not near_fine(t.GetEnd()):
        orig_w[id(t)] = t.GetWidth(); t.SetWidth(pcbnew.FromMM(w)); n_w += 1
print("utvidet spor:", n_w)

def drc_items(board):
    rep = os.path.join(OUT, "drc_tmp.txt"); pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
    import re as _r
    txt = open(rep).read(); items = []
    for blk in _r.split(r"\n(?=\[)", txt):
        m = _r.match(r"\[(\w+)\]", blk)
        if not m: continue
        pts = [(float(a), float(b_), n) for a, b_, n in _r.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (?:Track|Via) \[(\w+)\]", blk)]
        items.append((m.group(1), pts))
    return items
import math as _m
def seg_contains(t, x, y, tol=0.6):
    s_, e_ = t.GetStart(), t.GetEnd(); sx, sy, ex, ey = pcbnew.ToMM(s_.x), pcbnew.ToMM(s_.y), pcbnew.ToMM(e_.x), pcbnew.ToMM(e_.y)
    L = _m.hypot(ex - sx, ey - sy) or 1e-9; u = max(0, min(1, ((x - sx) * (ex - sx) + (y - sy) * (ey - sy)) / L / L))
    return _m.hypot(sx + u * (ex - sx) - x, sy + u * (ey - sy) - y) < tol
for rnd in range(4):
    bad = [(x, y, n) for typ, pts in drc_items(board) if typ in ("clearance", "hole_clearance", "solder_mask_bridge") for (x, y, n) in pts if n in WIDEN]
    if not bad: break
    fixed = 0
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetNetname() not in WIDEN: continue
        if any(seg_contains(t, x, y) for (x, y, n) in bad if n == t.GetNetname()) and t.GetWidth() > pcbnew.FromMM(0.61):
            t.SetWidth(pcbnew.FromMM(0.5)); fixed += 1
    print(f"runde {rnd}: {len(bad)} DRC-punkter, {fixed} spor smalnet")

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
subprocess.run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "-o", pos, PCB], check=True)
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
