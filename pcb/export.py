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
                if abs(pts[q] - pts[q+2]) < 0.05 and abs(pts[q+1] - pts[q+3]) < 0.05:
                    continue   # mikroskopiske restsegmenter fra Freerouting («track dangling»)
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
    MANUAL = []   # rev B: ingen manuelle spor ennå
    MANUAL_VIAS = []
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
_ds = board.GetDesignSettings(); _ds.m_ViasMinSize = pcbnew.FromMM(0.5); _ds.m_MinThroughDrill = pcbnew.FromMM(0.3)   # standard JLCPCB-via 0,3 mm hull
board.GetAllNetClasses()["Default"].SetClearance(pcbnew.FromMM(0.14)) if hasattr(board, "GetAllNetClasses") else _ds.m_NetSettings.m_DefaultNetClass.SetClearance(pcbnew.FromMM(0.14))   # Freerouting ruter med 0,15; avrunding gir 0,148 – JLCPCB-minimum er 0,127
# Fiks for allerede rutet kort: U4 pinne 3 (GND) fikk stubb som krysset pinne 2 – erstatt med via-i-pad ytterst på paden
import build_board as _bb
for (ref, pad), (vx, vy) in getattr(_bb, "FIXED_GND_VIP", {}).items():
    fp_ = board.FindFootprintByReference(ref); pd_ = next(p for p in fp_.Pads() if p.GetNumber() == pad)
    for t in list(board.GetTracks()):
        if t.GetNetname() == "GND" and t.IsLocked() and t.GetClass() == "PCB_TRACK" and (t.GetStart() - pd_.GetPosition()).EuclideanNorm() < pcbnew.FromMM(0.05):
            end = t.GetEnd(); board.Remove(t)
            for v in list(board.GetTracks()):
                if v.GetClass() == "PCB_VIA" and (v.GetPosition() - end).EuclideanNorm() < pcbnew.FromMM(0.05): board.Remove(v)
    if not any(v.GetClass() == "PCB_VIA" and (v.GetPosition() - pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy))).EuclideanNorm() < pcbnew.FromMM(0.05) for v in board.GetTracks()):
        gn_ = board.FindNet("GND")
        v = pcbnew.PCB_VIA(board); v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(vx), pcbnew.FromMM(vy))); v.SetWidth(pcbnew.FromMM(0.5)); v.SetDrill(pcbnew.FromMM(0.3)); v.SetNet(gn_); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetLocked(True); board.Add(v)
        print("via-i-pad:", ref, pad)

# Fjern løse ender: låste hjelpespor/vias (USB_SEL, USB3_DP …) som Freerouting ikke brukte, og rester som henger i løse luften.
# Gjøres på tekstnivå (regex på segment/via-linjene) – pcbnew/SWIG tåler ikke board.Remove() godt her.
def _prune_dangling_text(path, board):
    import re as _re2
    txt = open(path).read()
    gnd = board.FindNet("GND").GetNetCode()
    pads = [(pd, pcbnew.VECTOR2I(pd.GetPosition().x, pd.GetPosition().y)) for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() != "GND"]
    seg_re = _re2.compile(r'^\s*\(segment(?: locked)? \(start ([-\d.]+) ([-\d.]+)\) \(end ([-\d.]+) ([-\d.]+)\) \(width ([-\d.]+)\)(?: \(locked yes\))? \(layer "([^"]+)"\) \(net (\d+)\).*$', _re2.M)
    via_re = _re2.compile(r'^\s*\(via(?: locked)? \(at ([-\d.]+) ([-\d.]+)\) \(size ([-\d.]+)\) \(drill [-\d.]+\)(?: \(locked yes\))? \(layers "F\.Cu" "B\.Cu"\)(?: \(free yes\))? \(net (\d+)\).*$', _re2.M)
    # «berører» = innenfor sporbredden/via-størrelsen: Freerouting skjøter spor med overlapp, ikke alltid eksakt i endepunktene
    def near(a, b, tol): return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 < tol * tol
    def on_seg(p, a, b, tol):
        ax, ay = a; bx, by = b; px, py = p; dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
        return (px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2 < tol * tol
    def pad_hit(p, layer):
        v = pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))
        return any(pd.IsOnLayer(layer) and pd.HitTest(v) for pd, _ in pads)
    removed = 0
    for _ in range(8):
        segs = [(m, (float(m.group(1)), float(m.group(2))), (float(m.group(3)), float(m.group(4))), m.group(6), float(m.group(5))) for m in seg_re.finditer(txt) if int(m.group(7)) != gnd]
        vias = [(m, (float(m.group(1)), float(m.group(2))), float(m.group(3))) for m in via_re.finditer(txt) if int(m.group(4)) != gnd]
        LAY = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
        def touched(p, layer, me):
            if pad_hit(p, LAY[layer]): return True
            if any(near(vp, p, vs / 2 + 0.01) for _, vp, vs in vias): return True
            return any(m is not me and l == layer and on_seg(p, a, b, w / 2 + 0.01) for m, a, b, l, w in segs)
        gone = [m for m, a, b, l, _ in segs if not (touched(a, l, m) and touched(b, l, m))]
        for m, vp, vs in vias:
            ok = sum(1 for l in ("F.Cu", "B.Cu") if any(l2 == l and on_seg(vp, a, b, vs / 2 + w / 2) for _, a, b, l2, w in segs) or pad_hit(vp, LAY[l]))
            if ok < 2: gone.append(m)
        if not gone: break
        spans = sorted(((m.start(), m.end()) for m in gone), reverse=True)
        for a, b in spans:
            txt = txt[:a] + txt[b:]
        removed += len(gone)
    open(path, "w").write(txt)
    print("fjernet løse spor/vias:", removed)
    return pcbnew.LoadBoard(path)
board = _prune_dangling_text(PCB, board)
# Bredere strøm-/høyttalerspor der de ikke er inntil små pads (Freerouting ruter smalt ved IC-ene)
WIDEN = {"5V_USB": 0.6, "VIN24": 1.5, "24V_IN": 1.5, "SPK_LN": 1.2, "SPK_LP": 1.2, "SPK_RN": 1.2, "SPK_RP": 1.2, "OUTNL": 1.0, "OUTPL": 1.0, "OUTNR": 1.0, "OUTPR": 1.0, "5V": 0.9, "BUCK_SW": 1.0}
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
for rnd in range(6):
    bad = [(x, y, n) for typ, pts in drc_items(board) if typ in ("clearance", "hole_clearance", "solder_mask_bridge") for (x, y, n) in pts if n in WIDEN]
    if not bad: break
    fixed = 0
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetNetname() not in WIDEN: continue
        if any(seg_contains(t, x, y) for (x, y, n) in bad if n == t.GetNetname()) and t.GetWidth() > pcbnew.FromMM(0.26):
            t.SetWidth(pcbnew.FromMM(0.5 if t.GetWidth() > pcbnew.FromMM(0.61) else 0.25)); fixed += 1
    print(f"runde {rnd}: {len(bad)} DRC-punkter, {fixed} spor smalnet")

for fp in board.GetFootprints():
    fp.Reference().SetLayer(pcbnew.F_Fab); fp.Reference().SetVisible(True)

filler = pcbnew.ZONE_FILLER(board); filler.Fill(board.Zones())

# Stitching-vias: GND-sonen på F.Cu blir delt i øyer av sporene. Sett én via i hver øy (på et fritt punkt), så alle øyene
# henger sammen via B.Cu-sonen. Gjentas til ingen nye øyer dukker opp.
def _free_point(poly, board, gnd):
    """Finn et punkt inne i polygonet med ≥ 0,7 mm klaring til alle spor/pads som ikke er GND."""
    bb = poly.BBox(); import random
    rnd = random.Random(1)
    cands = [(bb.Centre().x, bb.Centre().y)] + [(bb.GetLeft() + rnd.random() * bb.GetWidth(), bb.GetTop() + rnd.random() * bb.GetHeight()) for _ in range(400)]
    items = [t for t in board.GetTracks() if t.GetNetname() != "GND"]
    pads = [pd for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() != "GND"]
    for x, y in cands:
        p = pcbnew.VECTOR2I(int(x), int(y))
        if not poly.Contains(p):
            continue
        if any(poly.Contains(pcbnew.VECTOR2I(int(x + dx), int(y + dy))) is False for dx, dy in ((500000, 0), (-500000, 0), (0, 500000), (0, -500000))):
            continue
        bad = False
        for t in items:
            if t.GetClass() == "PCB_VIA":
                if (t.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(0.9): bad = True; break
            elif t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
                seg = pcbnew.SEG(t.GetStart(), t.GetEnd())
                if seg.Distance(p) < pcbnew.FromMM(0.75) + t.GetWidth() // 2: bad = True; break
        if bad: continue
        for pd in pads:
            if (pd.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(1.6): bad = True; break
        if not bad:
            return p
    return None

gnd_net = board.FindNet("GND")
n_stitch = 0
for rnd_ in range(3):
    z = [zz for zz in board.Zones() if zz.GetLayer() == pcbnew.F_Cu and zz.GetNetname() == "GND"][0]   # ikke keepout-sonene
    polys = z.GetFilledPolysList(pcbnew.F_Cu)
    added = 0
    for i in range(polys.OutlineCount()):
        poly = pcbnew.SHAPE_POLY_SET(); poly.AddOutline(polys.Outline(i))
        # øyer som allerede har en via/THT-pad på GND inne i seg trenger ingen ny
        has = any(poly.Contains(t.GetPosition()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND")
        has = has or any(poly.Contains(pd.GetPosition()) for fp in board.GetFootprints() for pd in fp.Pads()
                         if pd.GetNetname() == "GND" and pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
        if has: continue
        p = _free_point(poly, board, gnd_net)
        if p is None: continue
        v = pcbnew.PCB_VIA(board); v.SetPosition(p); v.SetWidth(pcbnew.FromMM(0.8)); v.SetDrill(pcbnew.FromMM(0.4)); v.SetNet(gnd_net)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v); added += 1
    n_stitch += added
    filler.Fill(board.Zones())
    if not added: break
# Rutenett med stitching-vias (hver 7 mm der begge sonene har kobber og det er fritt) – binder F.Cu- og B.Cu-planet sammen
def _zone_poly(layer):
    z = [zz for zz in board.Zones() if zz.GetLayer() == layer and zz.GetNetname() == "GND"][0]
    return z.GetFilledPolysList(layer)
_tracks_ng = [t for t in board.GetTracks() if t.GetNetname() != "GND" or t.GetClass() == "PCB_VIA"]
_pads_ng = [pd for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() != "GND"]
def _clear(p, r_track=0.55, r_pad=1.3, r_via=0.8):
    for t in _tracks_ng:
        if t.GetClass() == "PCB_VIA":
            if (t.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(r_via): return False
        elif pcbnew.SEG(t.GetStart(), t.GetEnd()).Distance(p) < pcbnew.FromMM(r_track) + t.GetWidth() // 2: return False
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            if (pd.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(1.7 if pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH else 1.1): return False
            bb = pd.GetBoundingBox(); bb.Inflate(pcbnew.FromMM(0.9))   # store pads (TO-252-tab o.l.): klaring fra kanten
            if bb.Contains(p): return False
    return not any((pd.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(r_pad) for pd in _pads_ng)
pf, pb = _zone_poly(pcbnew.F_Cu), _zone_poly(pcbnew.B_Cu)
grid = 0
for gx in range(6, 175, 7):
    for gy in range(6, 95, 7):
        p = pcbnew.VECTOR2I(pcbnew.FromMM(gx), pcbnew.FromMM(gy))
        if pf.Contains(p) and pb.Contains(p) and _clear(p):
            v = pcbnew.PCB_VIA(board); v.SetPosition(p); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); v.SetNet(gnd_net)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v); grid += 1
print("rutenett-vias:", grid); n_stitch += grid
filler.Fill(board.Zones())
# Andre runde med mindre via (0,6/0,3) og lavere krav til klaring for øyene som fortsatt står alene
def _free_point2(poly, board):
    bb = poly.BBox(); import random
    rnd = random.Random(2)
    cands = [(bb.GetLeft() + rnd.random() * bb.GetWidth(), bb.GetTop() + rnd.random() * bb.GetHeight()) for _ in range(1500)]
    items = [t for t in board.GetTracks() if t.GetNetname() != "GND"]
    pads = [pd for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() != "GND"]
    for x, y in cands:
        p = pcbnew.VECTOR2I(int(x), int(y))
        if not poly.Contains(p): continue
        if any(not poly.Contains(pcbnew.VECTOR2I(int(x + dx), int(y + dy))) for dx, dy in ((350000, 0), (-350000, 0), (0, 350000), (0, -350000))): continue
        bad = False
        for t in items:
            if t.GetClass() == "PCB_VIA":
                if (t.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(0.7): bad = True; break
            elif t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
                if pcbnew.SEG(t.GetStart(), t.GetEnd()).Distance(p) < pcbnew.FromMM(0.5) + t.GetWidth() // 2: bad = True; break
        if bad: continue
        if any((pd.GetPosition() - p).EuclideanNorm() < pcbnew.FromMM(1.2) for pd in pads): continue
        return p
    return None

for rnd_, layer in ((0, pcbnew.F_Cu), (1, pcbnew.F_Cu), (2, pcbnew.B_Cu), (3, pcbnew.B_Cu)):
    z = [zz for zz in board.Zones() if zz.GetLayer() == layer and zz.GetNetname() == "GND"][0]
    polys = z.GetFilledPolysList(layer); added = 0
    for i in range(polys.OutlineCount()):
        poly = pcbnew.SHAPE_POLY_SET(); poly.AddOutline(polys.Outline(i))
        has = any(poly.Contains(t.GetPosition()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND")
        has = has or any(poly.Contains(pd.GetPosition()) for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() == "GND" and pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH)
        if has: continue
        p = _free_point2(poly, board)
        if p is None: continue
        v = pcbnew.PCB_VIA(board); v.SetPosition(p); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); v.SetNet(gnd_net)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v); added += 1
    n_stitch += added; filler.Fill(board.Zones())
# GND-pads på små SMD-pakker som sonen ikke når: kort spor ut fra paden + via
def _pad_unconnected_gnd(board):
    rep = os.path.join(OUT, "drc_tmp.txt"); pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
    import re as _r
    out = set()
    for blk in _r.split(r"\n(?=\[)", open(rep).read()):
        if not blk.startswith("[unconnected_items]"): continue
        for m in _r.finditer(r"Pad (\w+) \[GND\] of (\w+) on", blk):
            out.add((m.group(2), m.group(1)))
    return out
def _island_gnd_pads(board):
    out = set()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        polys = _zone_poly(layer)
        for i in range(polys.OutlineCount()):
            p = pcbnew.SHAPE_POLY_SET(); p.AddOutline(polys.Outline(i))
            if any(p.Contains(t.GetPosition()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"): continue
            if any(p.Contains(pd.GetPosition()) for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() == "GND" and pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH): continue
            for fp in board.GetFootprints():
                for pd in fp.Pads():
                    if pd.GetNetname() == "GND" and pd.GetAttribute() != pcbnew.PAD_ATTRIB_PTH and p.Contains(pd.GetPosition()):
                        out.add((fp.GetReference(), pd.GetNumber()))
    return out
for ref, num in sorted(_pad_unconnected_gnd(board) | _island_gnd_pads(board)):
    fp = board.FindFootprintByReference(ref)
    pd = next((p for p in fp.Pads() if p.GetNumber() == num), None)
    if pd is None: continue
    import math as _mm
    c = fp.GetPosition(); pp = pd.GetPosition()
    a0 = _mm.atan2(pp.y - c.y, pp.x - c.x)
    done = False
    for dist, da in [(d_, a_) for d_ in (1.2, 1.6, 2.0, 2.5, 3.0, 3.6, 4.4, 5.2) for a_ in (0, 0.5, -0.5, 1.0, -1.0, 1.57, -1.57, 2.2, -2.2, 2.7, -2.7, 3.14)]:
        if done: break
        q = pcbnew.VECTOR2I(int(pp.x + _mm.cos(a0 + da) * pcbnew.FromMM(dist)), int(pp.y + _mm.sin(a0 + da) * pcbnew.FromMM(dist)))
        clash = any((t.GetPosition() - q).EuclideanNorm() < pcbnew.FromMM(0.7) for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
        clash = clash or any(pcbnew.SEG(t.GetStart(), t.GetEnd()).Distance(q) < pcbnew.FromMM(0.45) + t.GetWidth() // 2 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetNetname() != "GND")
        clash = clash or any(p2.GetNetname() != "GND" and (p2.GetPosition() - q).EuclideanNorm() < pcbnew.FromMM(0.9) for f2 in board.GetFootprints() for p2 in f2.Pads())
        segq = pcbnew.SEG(pp, q)
        segshape = pcbnew.SHAPE_SEGMENT(pp, q, pcbnew.FromMM(0.2))
        clash = clash or any(p2.GetNetname() != "GND" and p2.GetEffectiveShape(pd.GetLayer()).Collide(segshape, pcbnew.FromMM(0.25)) for f2 in board.GetFootprints() for p2 in f2.Pads())
        clash = clash or any(t.GetClass() == "PCB_TRACK" and t.GetNetname() != "GND" and t.GetLayer() == pd.GetLayer()
                             and segq.Distance(pcbnew.SEG(t.GetStart(), t.GetEnd())) < pcbnew.FromMM(0.3) + t.GetWidth() // 2 for t in board.GetTracks())
        clash = clash or any((t.GetPosition() - q).EuclideanNorm() < pcbnew.FromMM(0.8) for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
        clash = clash or any((p2.GetPosition() - q).EuclideanNorm() < pcbnew.FromMM(1.0) for f2 in board.GetFootprints() for p2 in f2.Pads())
        if not clash:
            tr = pcbnew.PCB_TRACK(board); tr.SetStart(pp); tr.SetEnd(q); tr.SetWidth(pcbnew.FromMM(0.2)); tr.SetLayer(pd.GetLayer()); tr.SetNet(gnd_net); board.Add(tr)
            v = pcbnew.PCB_VIA(board); v.SetPosition(q); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); v.SetNet(gnd_net); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v)
            n_stitch += 1; print("GND-stubb:", ref, num); done = True
    if not done: print("GND-stubb FEILET:", ref, num)
filler.Fill(board.Zones())

# Sammenheng i jordplanet: alle sonefragmenter (F + B) må henge sammen via vias/PTH-pads. Fragmentgrupper som står
# alene får en via der et fragment overlapper hovedplanet på motsatt lag.
def _gnd_components():
    conn = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND"]
    conn += [pd.GetPosition() for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() == "GND" and pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH]
    frags = []
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        ps = _zone_poly(layer)
        for i in range(ps.OutlineCount()):
            poly = pcbnew.SHAPE_POLY_SET(); poly.AddOutline(ps.Outline(i)); frags.append((layer, poly))
    par = list(range(len(frags)))
    def f(x):
        while par[x] != x: par[x] = par[par[x]]; x = par[x]
        return x
    for c in conn:
        hit = [i for i, (_, p) in enumerate(frags) if p.Contains(c)]
        for i in hit[1:]: par[f(i)] = f(hit[0])
    groups = {}
    for i in range(len(frags)): groups.setdefault(f(i), []).append(i)
    comps = sorted(groups.values(), key=lambda l: -sum(frags[i][1].Area() for i in l))
    return frags, comps
def _via_in_overlap(frags, minor, main):
    for i in minor:
        li, pi = frags[i]
        for j in main:
            lj, pj = frags[j]
            if lj == li or not pi.BBox().Intersects(pj.BBox()): continue
            inter = pcbnew.SHAPE_POLY_SET(pi); inter.BooleanIntersection(pj, pcbnew.SHAPE_POLY_SET.PM_FAST)
            if inter.OutlineCount() == 0: continue
            for k in range(inter.OutlineCount()):
                poly = pcbnew.SHAPE_POLY_SET(); poly.AddOutline(inter.Outline(k))
                p = _free_point2(poly, board)
                if p is not None: return p
    return None
n_bridge = 0
for _ in range(40):
    frags, comps = _gnd_components()
    if len(comps) <= 1: break
    p = None
    for minor in comps[1:]:
        p = _via_in_overlap(frags, minor, comps[0])
        if p is not None: break
    if p is None:
        print("FEIL: jordplanet har", len(comps), "adskilte deler som ikke lar seg binde med via")
        for minor in comps[1:]:
            print("   del:", [(pcbnew.LayerName(frags[i][0]), round(frags[i][1].BBox().GetLeft() / 1e6, 1), round(frags[i][1].BBox().GetTop() / 1e6, 1)) for i in minor][:4])
        break
    v = pcbnew.PCB_VIA(board); v.SetPosition(p); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); v.SetNet(gnd_net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v); n_bridge += 1
    filler.Fill(board.Zones())
else:
    print("FEIL: jordplanet fortsatt delt etter 40 bro-vias")
n_stitch += n_bridge
print("bro-vias mellom jordplan-deler:", n_bridge, "-> deler:", len(_gnd_components()[1]))
print("stitching-vias:", n_stitch)
_rest = sorted(_island_gnd_pads(board))
if _rest: print("FEIL: GND-pads uten forbindelse til jordplanet:", _rest)
else: print("alle GND-pads er koblet til jordplanet")
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
