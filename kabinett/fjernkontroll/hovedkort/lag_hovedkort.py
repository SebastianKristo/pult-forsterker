"""Bygg hovedkortet i KiCad 7 (pcbnew-API): omriss fra kabinettet, plassering, nett, GND-flater, antennefri sone,
ruting med Freerouting (xvfb), DRC (pcbnew.WriteDRCReport), Gerber/bor, BOM og CPL for JLCPCB, og bilder.

Bruk:  python3 hovedkort/lag_hovedkort.py [--uten-ruting]
Krever: KiCad 7 (pcbnew), kicad-footprints, Java og Freerouting (FREEROUTING=/sti/til/freerouting.jar)."""
import csv
import math
import os
import shutil
import subprocess
import sys
import zipfile

import pcbnew

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import kretser  # noqa: E402
from kretser import KOMP, W, L  # noqa: E402

FPLIB = "/usr/share/kicad/footprints"
UT = HER
NAVN = "skjold-hovedkort"
mm = pcbnew.FromMM


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


# ---------- omriss: under tastene, fra n = 79,5 til halen, med hjørner som følger innerveggen ----------
N0, N1 = 79.5, L - 3.2          # 79,5 … 199,3: innenfor leppa på bunnen (3,1 mm inn fra ytterkanten)
X0, X1 = 3.2, W - 3.2
R_HALE = 7.8                    # innerveggens hjørneradius (11 − 1,8) minus leppa
R_NESE = 3.0
HULL = [(7.5, L - 5.5, 0), (W - 7.5, L - 5.5, 0), (4.9, L - 8, 6.6), (W - 4.9, L - 8, 6.6), (W - 7, 95, 2.4)]   # (x, n, Ø)


def omriss_poly():
    """Omrisset som shapely-polygon: avrundet rektangel, med hakk der skruetårnene i halen går gjennom."""
    from shapely.geometry import Point, Polygon
    p = Polygon(omriss_rå())
    for x, n, d in HULL:
        if d and N0 < n < N1:
            c = Point(x, n).buffer(d / 2, 48)
            if not p.buffer(-0.01).contains(c):
                p = p.difference(c)
    return p


def omriss_punkter():
    return list(omriss_poly().exterior.coords)[:-1]


def omriss_rå(k=24):
    pts = []
    def bue(cx, cy, r, a0, a1):
        for i in range(k + 1):
            a = math.radians(a0 + (a1 - a0) * i / k)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    bue(X0 + R_NESE, N0 + R_NESE, R_NESE, 180, 270)
    bue(X1 - R_NESE, N0 + R_NESE, R_NESE, 270, 360)
    bue(X1 - R_HALE, N1 - R_HALE, R_HALE, 0, 90)
    bue(X0 + R_HALE, N1 - R_HALE, R_HALE, 90, 180)
    return pts


def lag_brett():
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(2)
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(mm(1.0))
    ds.m_TrackMinWidth = mm(0.15)
    ds.m_MinClearance = mm(0.15)
    ds.m_ViasMinSize = mm(0.6)
    ds.m_MinThroughDrill = mm(0.3)
    ds.m_HoleClearance = mm(0.25)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_SolderMaskMinWidth = 0
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(mm(0.15))
    nc.SetTrackWidth(mm(0.2))
    nc.SetViaDiameter(mm(0.6))
    nc.SetViaDrill(mm(0.3))
    # omriss
    pts = omriss_punkter()
    for a, c in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(b)
        s.SetShape(pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(V(*a)); s.SetEnd(V(*c))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
        b.Add(s)
    from shapely.geometry import Point, Polygon
    rå = Polygon(omriss_rå())
    for x, n, d in HULL:
        if d and N0 < n < N1 and rå.buffer(-0.01).contains(Point(x, n).buffer(d / 2)):
            s = pcbnew.PCB_SHAPE(b)
            s.SetShape(pcbnew.SHAPE_T_CIRCLE)
            s.SetStart(V(x, n)); s.SetEnd(V(x + d / 2, n))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            b.Add(s)
    return b


def plasser(b):
    nett = {}
    def ni(navn):
        if navn not in nett:
            n_ = pcbnew.NETINFO_ITEM(b, navn)
            b.Add(n_)
            nett[navn] = n_
        return nett[navn]
    for ref, fp, verdi, side, x, n, rot, puter in KOMP:
        lib, navn = fp.split(":")
        f = pcbnew.FootprintLoad(f"{FPLIB}/{lib}.pretty", navn)
        if f is None:
            raise SystemExit(f"fant ikke fotavtrykket {fp}")
        if ref == "U1":   # fjern de små termiske viaene (0,2 mm bor) under modulen: tastene sitter rett over på oppsiden
            for p_ in list(f.Pads()):
                if p_.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                    f.Remove(p_)
        f.SetReference(ref)
        f.SetValue(verdi)
        f.SetPosition(V(x, n))
        b.Add(f)
        f.SetOrientationDegrees(rot)
        if side == "B":
            f.Flip(f.GetPosition(), False)
        for p in f.Pads():
            nv = puter.get(p.GetNumber())
            if nv:
                p.SetNet(ni(nv))
    silke(b)
    return nett


def silke(b):
    """Tekst på undersidens silketrykk: «+» ved batteriets pinne 1 (i forlengelsen av pinnerekka), og navn og versjon."""
    def tekst(t, x, y, h=1.0):
        s = pcbnew.PCB_TEXT(b)
        s.SetText(t)
        s.SetLayer(pcbnew.B_SilkS)
        s.SetTextSize(V(h, h))
        s.SetTextThickness(mm(0.15))
        s.SetPosition(V(x, y))
        s.SetMirrored(True)
        b.Add(s)
    j2 = b.FindFootprintByReference("J2")
    p1 = [p for p in j2.Pads() if p.GetNumber() == "1"][0].GetPosition()
    p2 = [p for p in j2.Pads() if p.GetNumber() == "2"][0].GetPosition()
    sx, sy = pcbnew.ToMM(p1.x), pcbnew.ToMM(p1.y)
    rx, ry = sx - pcbnew.ToMM(p2.x), sy - pcbnew.ToMM(p2.y)
    lengde = (rx * rx + ry * ry) ** 0.5
    tekst("+", sx + 1.7 * rx / lengde, sy + 1.7 * ry / lengde, 1.2)   # i pinnerekka, utenfor pinne 1
    tekst("SKJOLD FJERNKONTROLL HK v1", 27.5, 137.0, 0.9)


def sone(b, lag, nett, pts, regel=False):
    z = pcbnew.ZONE(b)
    if regel:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu)
        z.SetLayerSet(ls)
    else:
        z.SetLayer(lag)
        z.SetNet(nett)
        z.SetMinThickness(mm(0.2))
        z.SetLocalClearance(mm(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetThermalReliefGap(mm(0.3))
        z.SetThermalReliefSpokeWidth(mm(0.3))
    o = z.Outline()
    o.NewOutline()
    for x, y in pts:
        o.Append(mm(x), mm(y))
    b.Add(z)
    return z


ANTENNE = (X0 - 1.0, kretser.ESP_N - 24.0, 8.3, kretser.ESP_N + 24.0)   # (x0, n0, x1, n1): ingen kobber (som modulens egen sone)


def flater(b, nett):
    pts = omriss_punkter()
    for lag in (pcbnew.F_Cu, pcbnew.B_Cu):
        sone(b, lag, nett["GND"], pts)
    x0, n0, x1, n1 = ANTENNE
    sone(b, None, None, [(x0, n0), (x1, n0), (x1, n1), (x0, n1)], regel=True)


def fyll(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def forenkle_dsn(dsn):
    """Freerouting går tom for minne med det detaljerte omrisset (ca. 280 punkter i hakkene og hjørnene). I DSN-fila
    erstattes det med et forenklet omriss 0,25 mm innenfor (ca. 30 punkter); kortet selv beholder det ekte omrisset."""
    import re
    from shapely.geometry import Polygon
    s = open(dsn).read()
    m = re.search(r"\(boundary\s*\(path pcb 0\s+([-\d.\s]+)\)\s*\)", s)
    tall = [float(v) for v in m.group(1).split()]
    p = Polygon(list(zip(tall[0::2], tall[1::2]))).buffer(-250, join_style=2).simplify(150)
    ny = "(boundary\n      (path pcb 0  " + "  ".join(f"{x:.1f} {y:.1f}" for x, y in p.exterior.coords) + "))"
    open(dsn, "w").write(s[:m.start()] + ny + s[m.end():])


def rut(pcb, sti):
    """Ruter med Freerouting 2.x uten grafikk. Jordflatene tas ut av DSN-fila (GND rutes som spor og bindes sammen av
    flatene etterpå), og omrisset forenkles (se forenkle_dsn)."""
    dsn, ses = sti + ".dsn", sti + ".ses"
    kopi = pcbnew.LoadBoard(pcb)
    for z in list(kopi.Zones()):
        if not z.GetIsRuleArea():
            kopi.Remove(z)
    pcbnew.ExportSpecctraDSN(kopi, dsn)
    forenkle_dsn(dsn)
    jar = os.environ.get("FREEROUTING", "freerouting.jar")   # testet med freerouting-2.0.1.jar
    cmd = ["java", "-Xmx8g", "-jar", jar, "--gui.enabled=false", "-de", dsn, "-do", ses, "-mp", "30"]
    print("ruter:", " ".join(cmd))
    subprocess.run(cmd, check=False, timeout=3600)
    if not os.path.exists(ses):
        raise SystemExit("Freerouting laget ingen .ses")


def les_ses(tekst):
    """Enkel S-uttrykksleser for Freerouting-økta (.ses)."""
    import re
    tok = re.findall(r'"[^"]*"|\(|\)|[^\s()]+', tekst)
    stabel, rot = [], []
    cur = rot
    for t in tok:
        if t == "(":
            ny = []
            cur.append(ny)
            stabel.append(cur)
            cur = ny
        elif t == ")":
            cur = stabel.pop()
        else:
            cur.append(t.strip('"'))
    return rot[0]


def importer_ruting(pcb, ses):
    """Leser sporene og viaene fra .ses inn i kortet. (pcbnew.ImportSpecctraSES i KiCad 7 virker bare i
    redigeringsprogrammet, ikke fra et skript, så økta leses her.)"""
    b = pcbnew.LoadBoard(pcb)
    for t in list(b.GetTracks()):
        b.Remove(t)
    s = les_ses(open(ses).read())
    def finn(node, navn):
        return [x for x in node if isinstance(x, list) and x and x[0] == navn]
    ruter = finn(s, "routes")[0]
    oppl = finn(ruter, "resolution")[0]
    skala = {"um": 1000, "mm": 1000000, "mil": 25400}[oppl[1]] / float(oppl[2])   # nm per enhet
    lag = {"F.Cu": pcbnew.F_Cu, "B.Cu": pcbnew.B_Cu}
    nett = b.GetNetsByName()
    spor = viaer = 0
    for n in finn(finn(ruter, "network_out")[0], "net"):
        ni = nett[n[1]]
        for w in finn(n, "wire"):
            for p in finn(w, "path"):
                bredde = int(float(p[2]) * skala)
                xy = [float(v) for v in p[3:]]
                pts = [pcbnew.VECTOR2I(int(xy[k] * skala), int(-xy[k + 1] * skala)) for k in range(0, len(xy), 2)]
                for a, c in zip(pts, pts[1:]):
                    t = pcbnew.PCB_TRACK(b)
                    t.SetStart(a)
                    t.SetEnd(c)
                    t.SetWidth(bredde)
                    t.SetLayer(lag[p[1]])
                    t.SetNet(ni)
                    b.Add(t)
                    spor += 1
        for v in finn(n, "via"):
            via = pcbnew.PCB_VIA(b)
            via.SetPosition(pcbnew.VECTOR2I(int(float(v[2]) * skala), int(-float(v[3]) * skala)))
            via.SetDrill(mm(0.3))
            via.SetWidth(mm(0.6))
            via.SetNet(ni)
            b.Add(via)
            viaer += 1
    print(f"ruting lest: {spor} spor, {viaer} viaer")
    fyll(b)
    b.Save(pcb)
    return b


def gerber(b, mappe):
    os.makedirs(mappe, exist_ok=True)
    pc = pcbnew.PLOT_CONTROLLER(b)
    po = pc.GetPlotOptions()
    po.SetOutputDirectory(mappe)
    po.SetPlotFrameRef(False)
    po.SetUseGerberProtelExtensions(True)
    po.SetCreateGerberJobFile(False)
    po.SetSubtractMaskFromSilk(True)
    po.SetUseAuxOrigin(False)
    po.SetDrillMarksType(pcbnew.DRILL_MARKS_NO_DRILL_SHAPE) if hasattr(pcbnew, "DRILL_MARKS_NO_DRILL_SHAPE") else None
    lag = [(pcbnew.F_Cu, "F_Cu"), (pcbnew.B_Cu, "B_Cu"), (pcbnew.F_SilkS, "F_Silkscreen"), (pcbnew.B_SilkS, "B_Silkscreen"),
           (pcbnew.F_Mask, "F_Mask"), (pcbnew.B_Mask, "B_Mask"), (pcbnew.F_Paste, "F_Paste"), (pcbnew.B_Paste, "B_Paste"),
           (pcbnew.Edge_Cuts, "Edge_Cuts")]
    filer = []
    for l, n in lag:
        pc.SetLayer(l)
        pc.OpenPlotfile(n, pcbnew.PLOT_FORMAT_GERBER, n)
        pc.PlotLayer()
        filer.append(pc.GetPlotFileName())
    pc.ClosePlot()
    dw = pcbnew.EXCELLON_WRITER(b)
    dw.SetOptions(False, False, pcbnew.VECTOR2I(0, 0), False)
    dw.SetFormat(True)
    dw.CreateDrillandMapFilesSet(mappe, True, False)
    filer += [os.path.join(mappe, f) for f in os.listdir(mappe) if f.endswith(".drl")]
    z = os.path.join(UT, NAVN + "-gerber.zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in filer:
            zf.write(f, os.path.basename(f))
    return z


def bom_cpl(b):
    """JLC-format. Bryterne på oppsiden er DNP (loddes for hånd), så JLC bare monterer undersiden."""
    rader = {}
    cpl = [("Designator", "Mid X", "Mid Y", "Layer", "Rotation")]
    for f in b.GetFootprints():
        ref, verdi = f.GetReference(), f.GetValue()
        fp = str(f.GetFPID().GetLibItemName())
        if ref.startswith("TP"):
            continue
        dnp = f.GetLayer() == pcbnew.F_Cu
        nok = (verdi, fp, dnp)
        rader.setdefault(nok, []).append(ref)
        if not dnp:
            p = f.GetPosition()
            cpl.append((ref, f"{pcbnew.ToMM(p.x):.3f}mm", f"{-pcbnew.ToMM(p.y):.3f}mm", "Bottom" if f.GetLayer() == pcbnew.B_Cu else "Top",
                        f"{f.GetOrientationDegrees() % 360:.0f}"))
    bom = [("Comment", "Designator", "Footprint", "LCSC Part #")]
    dnp_rad = []
    for (verdi, fp, dnp), refs in sorted(rader.items(), key=lambda q: q[1][0]):
        nr = kretser.LCSC.get(verdi.split()[0], "")
        lc = f"{nr} (sjekk)" if nr else f"sjekk: søk «{verdi.split()[0]} {fp.split('_')[0]}»"
        (dnp_rad if dnp else bom).append((verdi, ",".join(sorted(refs, key=lambda r: (r.rstrip('0123456789'), int(''.join(c for c in r if c.isdigit()) or 0)))), fp, lc))
    for n, rows in (("bom-jlc.csv", bom), ("cpl-jlc.csv", cpl), ("dnp-handlodding.csv", [("Comment", "Designator", "Footprint", "LCSC Part #")] + dnp_rad)):
        with open(os.path.join(UT, n), "w", newline="") as fh:
            csv.writer(fh).writerows(rows)
    return len(bom) - 1, len(cpl) - 1, sum(len(r[1].split(",")) for r in dnp_rad)


def bilder(b):
    """PNG av kobberlagene (sett ovenfra; undersiden speilet som i JLCs visning er ikke gjort: sett gjennom kortet)."""
    from PIL import Image, ImageDraw
    sk = 12
    x0, y0 = X0 - 1, N0 - 1
    bw, bh = int((X1 - X0 + 2) * sk), int((N1 - N0 + 2) * sk)
    def px(v):
        return ((pcbnew.ToMM(v.x) - x0) * sk, (pcbnew.ToMM(v.y) - y0) * sk)
    ut = []
    for lag, navn, farge in ((pcbnew.F_Cu, "oppside", (196, 120, 40)), (pcbnew.B_Cu, "underside", (60, 110, 200))):
        im = Image.new("RGB", (bw, bh), (18, 50, 32))
        d = ImageDraw.Draw(im)
        d.polygon([((x - x0) * sk, (y - y0) * sk) for x, y in omriss_punkter()], fill=(28, 80, 50))
        for z in b.Zones():
            if z.GetIsRuleArea() or not z.IsOnLayer(lag):
                continue
            ps = z.GetFilledPolysList(lag)
            for i in range(ps.OutlineCount()):
                o = ps.COutline(i)
                d.polygon([px(o.CPoint(j)) for j in range(o.PointCount())], fill=tuple(int(c * 0.55) for c in farge))
                for h in range(ps.HoleCount(i)):
                    hh = ps.CHole(i, h)
                    d.polygon([px(hh.CPoint(j)) for j in range(hh.PointCount())], fill=(28, 80, 50))
        for t in b.GetTracks():
            if t.GetClass() == "PCB_VIA":
                c = px(t.GetPosition()); r = pcbnew.ToMM(t.GetWidth()) / 2 * sk
                d.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(220, 200, 120))
            elif t.IsOnLayer(lag):
                d.line([px(t.GetStart()), px(t.GetEnd())], fill=farge, width=max(1, int(pcbnew.ToMM(t.GetWidth()) * sk)))
        for f in b.GetFootprints():
            for p in f.Pads():
                if not p.IsOnLayer(lag):
                    continue
                poly = p.GetEffectivePolygon()
                for i in range(poly.OutlineCount()):
                    o = poly.COutline(i)
                    d.polygon([px(o.CPoint(j)) for j in range(o.PointCount())], fill=(235, 205, 120))
        a = ANTENNE
        d.rectangle([(a[0] - x0) * sk, (a[1] - y0) * sk, (a[2] - x0) * sk, (a[3] - y0) * sk], outline=(255, 80, 80), width=3)
        fil = os.path.join(UT, f"{NAVN}-{navn}.png")
        im.rotate(90, expand=True).save(fil)
        ut.append(fil)
    return ut


HOYDE = {"ESP32-S3-WROOM-1": 3.1, "USB_C_Receptacle_HRO_TYPE-C-31-M-12": 3.3, "TSSOP-24": 1.2, "SOT-23": 1.1, "SOT-23-5": 1.1,
         "SOT-23-6": 1.1, "SOIC-8-1EP": 1.7, "D_SOD-123": 1.2, "R_0402": 0.4, "C_0402": 0.5, "C_0603": 0.9, "C_1210": 2.5,
         "Hirose_FH12-18S": 2.0, "Hirose_FH12-6S": 2.0, "JST_PH_S2B-PH-SM4-TB": 5.0, "JST_SH_SM05B-SRSS-TB": 3.0,
         "SW_SPST_PTS810": 2.5, "SW_Push_1P1T_NO_CK_KMR2": 1.9, "TestPoint": 0.05}


def hoyde(fp):
    for k_, h in HOYDE.items():
        if fp.startswith(k_):
            return h
    raise SystemExit("ukjent høyde for " + fp)


def scad_data(b):
    """hovedkort_data.scad til kabinettet: omrisset (modellens y = L − n), hullet for midtskruen og en boks per
    komponent (courtyard × høyde), oppsiden og undersiden. USB-C-kontakten får egen linje for åpningen i halen."""
    def y(n):
        return round(L - n, 3)
    rader = []
    usb = None
    for f in b.GetFootprints():
        fp = str(f.GetFPID().GetLibItemName())
        lag = pcbnew.F_CrtYd if f.GetLayer() == pcbnew.F_Cu else pcbnew.B_CrtYd
        bokser = [g.GetBoundingBox() for g in f.GraphicalItems() if g.GetLayer() == lag] or [f.GetBoundingBox(False, False)]
        x0 = min(pcbnew.ToMM(q.GetX()) for q in bokser); x1 = max(pcbnew.ToMM(q.GetRight()) for q in bokser)
        n0 = min(pcbnew.ToMM(q.GetY()) for q in bokser); n1 = max(pcbnew.ToMM(q.GetBottom()) for q in bokser)
        if fp.startswith("ESP32"):   # bare selve modulen (18 × 25,5 mm), ikke antennesonen i courtyarden
            x0, x1 = kretser.ESP_X - 12.75, kretser.ESP_X + 12.75
            n0, n1 = kretser.ESP_N - 9.0, kretser.ESP_N + 9.0
        side = 1 if f.GetLayer() == pcbnew.F_Cu else -1
        rader.append(f"  [{x0:.2f}, {y(n1):.2f}, {x1:.2f}, {y(n0):.2f}, {hoyde(fp)}, {side}, \"{f.GetReference()}\"]")
        if f.GetReference() == "J1":
            usb = ((x0 + x1) / 2, x1 - x0)
    pts = ", ".join(f"[{x:.3f}, {y(n):.3f}]" for x, n in omriss_punkter())
    hull_ = ", ".join(f"[{x}, {y(n)}, {d}]" for x, n, d in HULL if d and N0 < n < N1 and d < 3)
    with open(os.path.join(UT, "hovedkort_data.scad"), "w") as fh:
        fh.write("// Laget av hovedkort/lag_hovedkort.py – ikke rediger for hånd.\n"
                 f"HK_OMRISS = [{pts}];\nHK_HULL = [{hull_}];\nHK_USB_X = {usb[0]:.2f};\n"
                 "HK_DELER = [   // [x0, y0, x1, y1, høyde, side (1 = oppe, −1 = under), ref]\n" + ",\n".join(rader) + "\n];\n")


def main():
    b = lag_brett()
    nett = plasser(b)
    flater(b, nett)
    pcb = os.path.join(UT, NAVN + ".kicad_pcb")
    b.Save(pcb)
    print("lagret", pcb, len(KOMP), "komponenter,", len(nett), "nett")
    scad_data(b)
    if "--uten-ruting" in sys.argv:
        return b
    ses = os.path.join(UT, NAVN + ".ses")
    if "--ruting" in sys.argv or not os.path.exists(ses):
        rut(pcb, os.path.join(UT, NAVN))
    b = importer_ruting(pcb, ses)
    import drc
    feil, adv, eks, _ = drc.kjør(pcb, os.path.join(UT, NAVN + "-drc.rpt"), fyll=False)
    print("DRC-feil:", dict(feil), "· advarsler:", dict(adv))
    z = gerber(b, os.path.join(UT, "gerber"))
    nb, nc, nd = bom_cpl(b)
    print("skrev", os.path.basename(z), f"· BOM {nb} linjer, CPL {nc} deler, {nd} for hånd")
    for f in bilder(b):
        print("skrev", os.path.basename(f))
    return b


if __name__ == "__main__":
    main()
