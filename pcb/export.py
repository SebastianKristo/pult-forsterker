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
        # låste (håndlagte) spor/vias beholdes alltid – de er kortets strømskinne
        gone = [m for m, a, b, l, _ in segs if " locked" not in m.group(0) and not (touched(a, l, m) and touched(b, l, m))]
        for m, vp, vs in vias:
            if " locked" in m.group(0): continue
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
# GND-spor (rutet som nett) som kolliderer med andre nett (typisk låste spor/vias lagt til etter rutingen) fjernes – planet tar over
def _drop_colliding_gnd():
    import re as _r
    removed = 0
    for _ in range(4):
        rep = os.path.join(OUT, "drc_tmp.txt"); pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
        pts = []
        for blk in _r.split(r"\n(?=\[)", open(rep).read()):
            if not blk.startswith("[clearance]") and not blk.startswith("[hole_clearance]"): continue
            pts += [(float(a), float(b_)) for a, b_ in _r.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (?:Track|Via) \[GND\]", blk)]
        if not pts: break
        gone = [t for t in board.GetTracks() if t.GetNetname() == "GND" and not t.IsLocked()
                and any(seg_contains(t, x, y, 0.3) for x, y in pts)]   # spor og (sy-)vias
        print("  GND-kollisjoner:", len(pts), "spor å fjerne:", len(gone))
        if not gone: break
        for t in gone: board.Remove(t)
        removed += len(gone)
    return removed
# Utvid hvert strømspor så mye naboene tillater (mål fra POWER_NETS i build_board), med 0,16 mm klaring til alt annet kobber.
WIDEN = dict(getattr(_bb, "POWER_NETS", WIDEN))
_CL = pcbnew.FromMM(0.21); _EDGE = pcbnew.FromMM(0.55)   # 0,5 kantavstand/keepout + margin
_others_tr = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
_others_via = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
_pads_all = [pd for fp in board.GetFootprints() for pd in fp.Pads()]
def _max_width(t):
    seg = pcbnew.SEG(t.GetStart(), t.GetEnd()); bb = t.GetBoundingBox(); bb.Inflate(pcbnew.FromMM(2.0))
    lim = pcbnew.FromMM(WIDEN[t.GetNetname()])
    net = t.GetNetname(); lay = t.GetLayer()
    for o in _others_tr:
        if o is t or o.GetNetname() == net or o.GetLayer() != lay or not bb.Intersects(o.GetBoundingBox()): continue
        d = seg.Distance(pcbnew.SEG(o.GetStart(), o.GetEnd())) - o.GetWidth() // 2 - _CL
        lim = min(lim, 2 * d)
    for v in _others_via:
        if v.GetNetname() == net or not bb.Contains(v.GetPosition()): continue
        lim = min(lim, 2 * (seg.Distance(v.GetPosition()) - v.GetWidth() // 2 - _CL))
    for pd in _pads_all:
        if not bb.Intersects(pd.GetBoundingBox()): continue
        if pd.GetNetname() == net:
            # egen fin pad: ikke bredere enn paden der sporet går inn i den
            if min(pd.GetSize().x, pd.GetSize().y) < pcbnew.FromMM(1.0) and (pd.HitTest(t.GetStart()) or pd.HitTest(t.GetEnd())):
                lim = min(lim, max(pd.GetSize().x if pd.GetSize().x < pd.GetSize().y else pd.GetSize().y, t.GetWidth()))
            continue
        if not (pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH or pd.IsOnLayer(lay)): continue
        shp = pd.GetEffectiveShape(lay)
        d = shp.Distance(seg) if hasattr(shp, "Distance") else None
        if d is None:
            d = seg.Distance(pd.GetPosition()) - max(pd.GetSize().x, pd.GetSize().y) // 2
        lim = min(lim, 2 * (d - _CL))
    # kortkant
    for q in (t.GetStart(), t.GetEnd()):
        lim = min(lim, 2 * (min(q.x, q.y, pcbnew.FromMM(180) - q.x, pcbnew.FromMM(100) - q.y) - _EDGE))
    return lim
for t in board.GetTracks():
    if t.GetClass() != "PCB_TRACK" or t.GetNetname() not in WIDEN: continue   # også låste (håndlagte 0,4-stubber utvides der det er plass)
    w = _max_width(t)
    w = int(w // pcbnew.FromMM(0.05)) * pcbnew.FromMM(0.05)   # rund ned til 0,05
    if w > t.GetWidth():
        orig_w[t.m_Uuid.AsString()] = t.GetWidth(); t.SetWidth(int(w)); n_w += 1
print("utvidet spor:", n_w)

def drc_items(board):
    rep = os.path.join(OUT, "drc_tmp.txt"); pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
    import re as _r
    txt = open(rep).read(); items = []
    for blk in _r.split(r"\n(?=\[)", txt):
        m = _r.match(r"\[(\w+)\]", blk)
        if not m: continue
        if "): Zone [" in blk: continue   # sonen fylles på nytt rundt sporene etterpå – gammel fyll skal ikke smalne strømspor
        pts = [(float(a), float(b_), n) for a, b_, n in _r.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (?:Track|Via) \[(\w+)\]", blk)]
        items.append((m.group(1), pts))
    return items
import math as _m
def seg_contains(t, x, y, tol=0.6):
    s_, e_ = t.GetStart(), t.GetEnd(); sx, sy, ex, ey = pcbnew.ToMM(s_.x), pcbnew.ToMM(s_.y), pcbnew.ToMM(e_.x), pcbnew.ToMM(e_.y)
    L = _m.hypot(ex - sx, ey - sy) or 1e-9; u = max(0, min(1, ((x - sx) * (ex - sx) + (y - sy) * (ey - sy)) / L / L))
    return _m.hypot(sx + u * (ex - sx) - x, sy + u * (ey - sy) - y) < tol
print("GND-spor som kolliderte, fjernet:", _drop_colliding_gnd())
for rnd in range(6):
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())   # fersk sonefyll før DRC
    bad = [(x, y, n) for typ, pts in drc_items(board) if typ in ("clearance", "hole_clearance", "solder_mask_bridge", "copper_edge_clearance", "items_not_allowed") for (x, y, n) in pts if n in WIDEN]
    if not bad: break
    fixed = 0
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetNetname() not in WIDEN: continue
        ow = orig_w.get(t.m_Uuid.AsString(), pcbnew.FromMM(0.4))   # nøkkel = UUID (id() på SWIG-proxy er ikke stabil → alt ble 0,2)
        if any(seg_contains(t, x, y) for (x, y, n) in bad if n == t.GetNetname()) and t.GetWidth() > ow + pcbnew.FromMM(0.01):
            t.SetWidth(pcbnew.FromMM(0.5) if t.GetWidth() > pcbnew.FromMM(0.61) else ow); fixed += 1   # tilbake til rutet bredde, ikke 0,25
    print(f"runde {rnd}: {len(bad)} DRC-punkter, {fixed} spor smalnet")

# Hull-til-hull (JLCPCB: ≥ 0,5 mm mellom borehull): to vias som ligger for tett skyves fra hverandre langs senterlinjen,
# og sporendene som satt på viaene flyttes med. Freerouting kjenner ikke denne regelen.
def _fix_hole_near_hole():
    import re as _r, math as _mm
    def drc_bad():
        rep = os.path.join(OUT, "drc_tmp.txt"); pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
        n = 0; pairs = []
        for blk in _r.split(r"\n(?=\[)", open(rep).read()):
            if blk.startswith("[clearance]") or blk.startswith("[hole_clearance]"): n += 1
            if blk.startswith("[hole_near_hole]"):
                m = _r.search(r"min ([-\d.]+) mm; actual ([-\d.]+) mm", blk)
                pts = _r.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): Via \[", blk)
                if m and len(pts) == 2: pairs.append((float(m.group(1)) - float(m.group(2)), [(float(x), float(y)) for x, y in pts]))
        return n, pairs
    def move(v, sx, sy):
        old = pcbnew.VECTOR2I(v.GetPosition()); new = pcbnew.VECTOR2I(old.x + pcbnew.FromMM(sx), old.y + pcbnew.FromMM(sy))
        for t in board.GetTracks():
            if t.GetClass() != "PCB_TRACK" or t.GetNetCode() != v.GetNetCode(): continue
            if t.GetStart() == old: t.SetStart(new)
            if t.GetEnd() == old: t.SetEnd(new)
        v.SetPosition(new)
    moved = 0
    base, pairs = drc_bad()
    for need, (a, b_) in pairs:
        vias = {(round(pcbnew.ToMM(t.GetPosition().x), 4), round(pcbnew.ToMM(t.GetPosition().y), 4)): t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"}
        va, vb = vias.get((round(a[0], 4), round(a[1], 4))), vias.get((round(b_[0], 4), round(b_[1], 4)))
        if va is None or vb is None: continue
        dx, dy = b_[0] - a[0], b_[1] - a[1]; L = _mm.hypot(dx, dy) or 1e-9; ux, uy = dx / L, dy / L
        d = need + 0.03
        options = []
        if not va.IsLocked() and not vb.IsLocked(): options.append(((va, -ux * d / 2, -uy * d / 2), (vb, ux * d / 2, uy * d / 2)))
        if not va.IsLocked(): options.append(((va, -ux * d, -uy * d),))
        if not vb.IsLocked(): options.append(((vb, ux * d, uy * d),))
        # også litt på tvers av linjen (om det er trangt langs den)
        for sgn in (1, -1):
            if not va.IsLocked(): options.append(((va, -ux * d - uy * 0.15 * sgn, -uy * d + ux * 0.15 * sgn),))
            if not vb.IsLocked(): options.append(((vb, ux * d - uy * 0.15 * sgn, uy * d + ux * 0.15 * sgn),))
        ok = False
        for opt in options:
            for v, sx, sy in opt: move(v, sx, sy)
            n, p2 = drc_bad()
            if n <= base and not any(set(map(tuple, pp)) & {tuple(a), tuple(b_)} for _, pp in p2): ok = True; break
            for v, sx, sy in opt: move(v, -sx, -sy)
        if ok: moved += len(opt); print("  hull-til-hull løst:", a, b_)
        else: print("  hull-til-hull IKKE løst:", a, b_)
    return moved
print("vias flyttet for hull-til-hull:", _fix_hole_near_hole())

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
        if not bad and not _via_in_pad(p, 0.5):
            return p
    return None

_all_pads = [pd for fp in board.GetFootprints() for pd in fp.Pads()]
def _via_in_pad(p, r_mm=0.45):
    """Sant hvis en via med radius r_mm på punkt p ville ligge inni/over en pad (uansett nett) – via-i-pad lodder dårlig."""
    c = pcbnew.SHAPE_CIRCLE(p, pcbnew.FromMM(r_mm))
    for pd in _all_pads:
        bb = pd.GetBoundingBox(); bb.Inflate(pcbnew.FromMM(r_mm + 0.1))
        if not bb.Contains(p): continue
        for l in (pcbnew.F_Cu, pcbnew.B_Cu):
            if (pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH or pd.IsOnLayer(l)) and pd.GetEffectiveShape(l).Collide(c, pcbnew.FromMM(0.1)): return True
    return False
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
        if _via_in_pad(p, 0.4): continue
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
    # GND-spor smelter sammen med sonen på samme lag: begge endene binder fragmentene de ligger i
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK" or t.GetNetname() != "GND": continue
        hit = [i for i, (l, p) in enumerate(frags) if l == t.GetLayer() and (p.Contains(t.GetStart()) or p.Contains(t.GetEnd()))]
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
def _seg_clear(layer, a, b_, w):
    """Kan et GND-spor (bredde w) gå fra a til b_ på laget uten å komme nær andre nett?"""
    seg = pcbnew.SEG(a, b_); hw = pcbnew.FromMM(w / 2); cl = pcbnew.FromMM(0.16)
    for t in board.GetTracks():
        if t.GetNetname() == "GND": continue
        if t.GetClass() == "PCB_VIA":
            if seg.Distance(t.GetPosition()) < t.GetWidth() // 2 + hw + cl: return False
        elif t.GetLayer() == layer and seg.Distance(pcbnew.SEG(t.GetStart(), t.GetEnd())) < t.GetWidth() // 2 + hw + cl: return False
    shp = pcbnew.SHAPE_SEGMENT(a, b_, 2 * hw)
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            if pd.GetNetname() == "GND": continue
            if (pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH or pd.IsOnLayer(layer)) and pd.GetEffectiveShape(layer).Collide(shp, cl): return False
    return True
def _track_bridge(frags, minor, main):
    """Kort GND-spor fra en isolert del til hovedplanet på samme lag (prøver nærmeste punktpar på omrissene)."""
    cands = []
    for i in minor:
        li, pi = frags[i]
        for j in main:
            lj, pj = frags[j]
            if lj != li: continue
            if pi.BBox().GetSizeMax() and pi.BBox().Distance(pj.BBox()) > pcbnew.FromMM(8): continue
            oi, oj = pi.Outline(0), pj.Outline(0)
            for a in range(oi.PointCount()):
                pa = oi.CPoint(a)
                for c in range(oj.PointCount()):
                    pc = oj.CPoint(c); d = (pa - pc).EuclideanNorm()
                    if d < pcbnew.FromMM(8): cands.append((d, li, pcbnew.VECTOR2I(pa), pcbnew.VECTOR2I(pc)))
    cands.sort(key=lambda x: x[0])
    for d, layer, pa, pc in cands[:400]:
        # trekk endene 0,3 mm inn i hvert kobberfelt så sporet garantert overlapper
        v = pc - pa; n = v.EuclideanNorm() or 1
        ia = pcbnew.VECTOR2I(int(pa.x - v.x * 300000 / n), int(pa.y - v.y * 300000 / n)); ic = pcbnew.VECTOR2I(int(pc.x + v.x * 300000 / n), int(pc.y + v.y * 300000 / n))
        for w in (0.3, 0.2):
            if _seg_clear(layer, ia, ic, w):
                tr = pcbnew.PCB_TRACK(board); tr.SetStart(ia); tr.SetEnd(ic); tr.SetWidth(pcbnew.FromMM(w)); tr.SetLayer(layer); tr.SetNet(gnd_net); board.Add(tr)
                return True
    return False
n_bridge = 0; n_tbridge = 0
for _ in range(40):
    frags, comps = _gnd_components()
    if len(comps) <= 1: break
    p = None
    for minor in comps[1:]:
        p = _via_in_overlap(frags, minor, comps[0])
        if p is not None: break
    if p is None:
        done_t = False
        for minor in comps[1:]:
            if _track_bridge(frags, minor, comps[0]): done_t = True; break
        if done_t:
            n_tbridge += 1; filler.Fill(board.Zones()); continue
        # Rest-deler uten GND-pads er bare kobberrester: fjern de (ulåste) stitching-viaene i dem, så KiCad fjerner øyene ved fylling
        smd_gnd = [pd.GetPosition() for fp in board.GetFootprints() for pd in fp.Pads() if pd.GetNetname() == "GND"]
        dropped = 0; stuck = []
        for minor in comps[1:]:
            polys = [frags[i][1] for i in minor]
            if any(pl.Contains(q) for pl in polys for q in smd_gnd):
                stuck.append(minor); continue
            for v in [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND" and not t.IsLocked()]:
                if any(pl.Contains(v.GetPosition()) for pl in polys): board.Remove(v); dropped += 1
        filler.Fill(board.Zones())
        print("kobberrester i jordplanet fjernet (vias):", dropped)
        if stuck:
            print("FEIL: jordplanet har", len(stuck), "adskilte deler med GND-pads som ikke lar seg binde med via")
            for minor in stuck:
                print("   del:", [(pcbnew.LayerName(frags[i][0]), round(frags[i][1].BBox().GetLeft() / 1e6, 1), round(frags[i][1].BBox().GetTop() / 1e6, 1)) for i in minor][:4])
        break
    v = pcbnew.PCB_VIA(board); v.SetPosition(p); v.SetWidth(pcbnew.FromMM(0.6)); v.SetDrill(pcbnew.FromMM(0.3)); v.SetNet(gnd_net)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); board.Add(v); n_bridge += 1
    filler.Fill(board.Zones())
else:
    print("FEIL: jordplanet fortsatt delt etter 40 bro-vias")
n_stitch += n_bridge
print("bro-vias mellom jordplan-deler:", n_bridge, "bro-spor:", n_tbridge, "-> deler:", len(_gnd_components()[1]))
print("stitching-vias:", n_stitch)
_rest = sorted(_island_gnd_pads(board))
if _rest: print("FEIL: GND-pads uten forbindelse til jordplanet:", _rest)
else: print("alle GND-pads er koblet til jordplanet")
# Løse sporender (etter smalning/oppdeling): fjern segmenter der en ende ikke treffer spor, via eller pad på samme lag
def _prune_dangling_board():
    removed = 0
    for _ in range(6):
        tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"]
        vias = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
        pads = [pd for fp in board.GetFootprints() for pd in fp.Pads()]
        def touched(pt, layer, me):
            for t in tracks:
                if t is me or t.GetLayer() != layer: continue
                if pcbnew.SEG(t.GetStart(), t.GetEnd()).Distance(pt) <= t.GetWidth() // 2: return True
            for v in vias:
                if (v.GetPosition() - pt).EuclideanNorm() <= v.GetWidth() // 2: return True
            for pd in pads:
                if pd.IsOnLayer(layer) and pd.HitTest(pt): return True
            return False
        gone = [t for t in tracks if t.IsLocked() is False and (not touched(t.GetStart(), t.GetLayer(), t) or not touched(t.GetEnd(), t.GetLayer(), t))]
        if not gone: break
        for t in gone: board.Remove(t)
        removed += len(gone)
    return removed
print("GND-spor som kolliderte (sluttkontroll), fjernet:", _drop_colliding_gnd())
filler.Fill(board.Zones())
_fr, _cm = _gnd_components()
if len(_cm) > 1: print("MERK: jordplanet (sonene) er i", len(_cm), "deler – GND er i tillegg rutet som nett, så alle GND-pads henger sammen (DRC bekrefter)")
_vip = [t for t in board.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "GND" and not t.IsLocked() and _via_in_pad(t.GetPosition(), pcbnew.ToMM(t.GetWidth()) / 2)]
for t in _vip: board.Remove(t)
print("GND-vias inni pads fjernet:", len(_vip))
print("løse sporender fjernet:", _prune_dangling_board())
# Siste finpuss: DRC-ens egne «dangling» (korte stubber og vias som bare brukes på ett lag) fjernes – de er uten funksjon
def _drop_drc_dangling():
    import re as _r
    rep = os.path.join(OUT, "drc_tmp.txt"); pcbnew.WriteDRCReport(board, rep, pcbnew.EDA_UNITS_MILLIMETRES, True)
    gone = 0
    for blk in _r.split(r"\n(?=\[)", open(rep).read()):
        if not (blk.startswith("[track_dangling]") or blk.startswith("[via_dangling]")): continue
        for x, y, kind in _r.findall(r"@\(([-\d.]+) mm, ([-\d.]+) mm\): (Track|Via) \[", blk):
            x, y = float(x), float(y)
            for t in list(board.GetTracks()):
                if (t.GetClass() == "PCB_VIA") != (kind == "Via"): continue
                if kind == "Via" and abs(pcbnew.ToMM(t.GetPosition().x) - x) < 0.01 and abs(pcbnew.ToMM(t.GetPosition().y) - y) < 0.01:
                    board.Remove(t); gone += 1; break
                if kind == "Track" and not t.IsLocked() and (t.GetEnd() - t.GetStart()).EuclideanNorm() < pcbnew.FromMM(1.0) and \
                        (abs(pcbnew.ToMM(t.GetStart().x) - x) < 0.01 and abs(pcbnew.ToMM(t.GetStart().y) - y) < 0.01 or abs(pcbnew.ToMM(t.GetEnd().x) - x) < 0.01 and abs(pcbnew.ToMM(t.GetEnd().y) - y) < 0.01):
                    board.Remove(t); gone += 1; break
    return gone
print("DRC-dangling fjernet:", _drop_drc_dangling())
filler.Fill(board.Zones())
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

# CPL (JLCPCB-format: Designator, Mid X, Mid Y, Layer, Rotation) – bare SMD (THT loddes selv, de får egen liste)
pos = os.path.join(OUT, "cpl_tmp.csv")
subprocess.run(["kicad-cli", "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "front", "-o", pos, PCB], check=True)
bom = {r["Designator"]: r for r in csv.DictReader(open(os.path.join(HERE, "bom.csv")))}
_fp_name = {fp.GetReference(): fp.GetFPID().GetLibItemName().wx_str() for fp in board.GetFootprints()}
_is_tht = {fp.GetReference(): any(pd.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for pd in fp.Pads()) for fp in board.GetFootprints()}
# JLCPCBs 0°-orientering avviker fra KiCads for disse pakkene (samme tabell som KiBot/JLCKicadTools bruker). Sjekk likevel pinne 1 i JLCPCB-forhåndsvisningen.
import re as _rx
JLC_ROT = [(r"^SOT-23", 180), (r"^SOT-223", 180), (r"^(SOIC|SSOP|TSSOP|HTSSOP|HSOP|SOP|MSOP)", 270), (r"^(QFN|WQFN|UQFN|DFN|VQFN|TQFN)", 270), (r"^CP_Elec", 180),
           (r"^USB_C_Receptacle_HRO", 180), (r"^TO-252", 270)]
def jlc_rot(ref, rot):
    name = _fp_name.get(ref, "")
    for pat, add in JLC_ROT:
        if _rx.match(pat, name): return (rot + add) % 360
    return rot % 360
smd_refs = []
with open(os.path.join(OUT, "ki_pultforsterker_main_cpl.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
    for row in csv.DictReader(open(pos)):
        ref = row["Ref"]
        if ref in bom and bom[ref]["Value"] != "DNP" and not _is_tht.get(ref, False):   # også SMD uten LCSC-kode – JLCPCB spør da om en del; Y som KiCad gir (negativ = samme som gerber)
            smd_refs.append(ref)
            w.writerow([ref, f'{float(row["PosX"]):.3f}mm', f'{float(row["PosY"]):.3f}mm', "Top", f'{jlc_rot(ref, float(row["Rot"])):g}'])
os.remove(pos)
# BOM gruppert (JLCPCB-format: Comment, Designator, Footprint, LCSC) – bare SMD
groups = {}; tht = []
for ref, r in bom.items():
    if r["Value"] == "DNP": continue
    if _is_tht.get(ref, False): tht.append((ref, r["Value"], r["Footprint"], r["LCSC"])); continue
    groups.setdefault((r["Value"], r["Footprint"], r["LCSC"]), []).append(ref)
with open(os.path.join(OUT, "ki_pultforsterker_main_bom.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Comment", "Designator", "Footprint", "LCSC Part #"])
    for (val, fp, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([val, ",".join(refs), fp, lcsc])
with open(os.path.join(OUT, "ki_pultforsterker_main_tht_handlodding.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["Designator", "Verdi", "Footprint", "LCSC (kjøp selv)"])
    for r in sorted(tht, key=lambda t: (t[0][0], int(_rx.sub(r"\D", "", t[0]) or 0))): w.writerow(r)
print("CPL/BOM: SMD", len(smd_refs), "deler, THT til håndlodding:", len(tht))
# bilder
for layers, name in [("F.Cu,F.SilkS,F.Mask,Edge.Cuts", "top"), ("B.Cu,B.SilkS,Edge.Cuts", "bottom")]:
    subprocess.run(["kicad-cli", "pcb", "export", "svg", "--layers", layers, "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", os.path.join(OUT, f"board_{name}.svg"), PCB], check=True)
print("Ferdig ->", OUT)
