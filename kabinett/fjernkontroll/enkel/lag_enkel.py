"""Bygg bærekortet til Skjold Fjernkontroll Enkel i KiCad 7 med samme rørlegging som hovedkortet: omriss (samme som
hovedkortet, med vindu under XIAO-ens BAT-puter), plassering, GND-flater på begge sider, brede spor (0,3 mm signal,
0,5 mm strøm), ingen viaer under delene, Freerouting, DRC, Gerber/bor, BOM/CPL for JLC, bilder og kabinettdata.

Bruk:  python3 enkel/lag_enkel.py [--uten-ruting | --ruting]   (FREEROUTING=/sti/til/freerouting-2.x.jar)"""
import os
import sys

import pcbnew

HER = os.path.dirname(os.path.abspath(__file__))
FK = os.path.dirname(HER)
sys.path.insert(0, HER)
sys.path.insert(0, os.path.join(FK, "hovedkort"))
import kretser_en  # noqa: E402
import lag_hovedkort as lh  # noqa: E402

mm = pcbnew.FromMM
V = lh.V
# Nett med 0,5 mm spor: der strømmen går (batteriet, IR-pulsene på ~0,2 A og 5 V fra dokken). 3V3/3V3_SW/LED_A/LED_K ender på
# FPC-pinner med 0,5 mm deling, der et 0,5 mm spor ikke får plass; de bærer under 150 mA og får 0,3 mm. GND er jordflatene.
STROM = {"VBAT", "VBUS", "POGO", "IR_A", "IR_K"}
VINDU = (22.0, 182.0, 33.0, 194.0)   # (x0, n0, x1, n1): vindu under XIAO-en for ledningene til BAT-putene


def omriss_poly():
    from shapely.geometry import box
    p = OMRISS_HK()
    return p.difference(box(*VINDU))


OMRISS_HK = lh.omriss_poly


def lag_brett():
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(2)
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(mm(1.0))
    ds.m_TrackMinWidth = mm(0.25); ds.m_MinClearance = mm(0.15)
    ds.m_ViasMinSize = mm(0.7); ds.m_MinThroughDrill = mm(0.35)
    ds.m_HoleClearance = mm(0.25); ds.m_CopperEdgeClearance = mm(0.4); ds.m_SolderMaskMinWidth = 0
    nc = ds.m_NetSettings.m_DefaultNetClass
    nc.SetClearance(mm(0.15)); nc.SetTrackWidth(mm(0.3)); nc.SetViaDiameter(mm(0.7)); nc.SetViaDrill(mm(0.35))
    p = omriss_poly()
    for ring in [p.exterior] + list(p.interiors):
        pts = list(ring.coords)[:-1]
        for a, c in zip(pts, pts[1:] + pts[:1]):
            s = pcbnew.PCB_SHAPE(b)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(*a)); s.SetEnd(V(*c))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            b.Add(s)
    from shapely.geometry import Point
    for x, n, d in lh.HULL:   # midtskruen (hel sirkel inne i kortet)
        if d and lh.N0 < n < lh.N1 and p.buffer(-0.01).contains(Point(x, n).buffer(d / 2)):
            s = pcbnew.PCB_SHAPE(b)
            s.SetShape(pcbnew.SHAPE_T_CIRCLE)
            s.SetStart(V(x, n)); s.SetEnd(V(x + d / 2, n))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            b.Add(s)
    return b


def strom_klasse(b):
    """Strømnettene får 0,5 mm spor (egen nettklasse)."""
    ns = b.GetDesignSettings().m_NetSettings
    k = pcbnew.NETCLASS("Strom")
    k.SetTrackWidth(mm(0.5)); k.SetClearance(mm(0.15)); k.SetViaDiameter(mm(0.8)); k.SetViaDrill(mm(0.4))
    try:
        ns.m_NetClasses["Strom"] = k
        k = ns.m_NetClasses["Strom"]
        for navn, ni in b.GetNetsByName().items():
            if str(navn) in STROM:
                ni.SetNetClass(k)
    except Exception as e:   # noqa: BLE001
        print("advarsel: kunne ikke sette nettklassen for strøm:", e)


def silke(b):
    def tekst(t, x, y, h=1.0, lag=pcbnew.B_SilkS):
        s = pcbnew.PCB_TEXT(b)
        s.SetText(t); s.SetLayer(lag)
        s.SetTextSize(V(h, h)); s.SetTextThickness(mm(0.15))
        s.SetPosition(V(x, y)); s.SetMirrored(lag == pcbnew.B_SilkS)
        b.Add(s)
    tekst("SKJOLD FJERNKONTROLL ENKEL v1", 27.5, 125.0, 1.0)
    tekst("XIAO ESP32S3 HER (komponentsiden ned)", 27.5, 176.0, 0.8)
    # tastenavn på oppsiden (ved siden av bryterne) og + ved batteriets pinne 1
    for f, x, n, p in kretser_en.TASTER:
        tekst(f.replace("_", " ").upper(), x, n + 3.4, 0.8, pcbnew.F_SilkS)
    j1 = b.FindFootprintByReference("J1")
    p1 = [p for p in j1.Pads() if p.GetNumber() == "1"][0].GetPosition()
    p2 = [p for p in j1.Pads() if p.GetNumber() == "2"][0].GetPosition()
    dx, dy = pcbnew.ToMM(p1.x - p2.x), pcbnew.ToMM(p1.y - p2.y)
    lg = (dx * dx + dy * dy) ** 0.5
    tekst("+", pcbnew.ToMM(p1.x) + 1.7 * dx / lg, pcbnew.ToMM(p1.y) + 1.7 * dy / lg, 1.2)
    tekst("IR+", 4.5, 81.5, 0.8)
    for ref in ("TP1", "TP2", "TP3", "TP4"):
        f_ = b.FindFootprintByReference(ref)
        tekst(f_.GetValue(), pcbnew.ToMM(f_.GetPosition().x) - 3.4, pcbnew.ToMM(f_.GetPosition().y), 0.8)


def flater(b, nett):
    pts = list(OMRISS_HK().exterior.coords)[:-1]
    for lag in (pcbnew.F_Cu, pcbnew.B_Cu):
        lh.sone(b, lag, nett["GND"], pts)
    # ingen viaer under delene: regelområder (bare viaer forbudt) over hver dels gårdsplass på undersiden og under bryterne
    for f in b.GetFootprints():
        if f.GetReference().startswith("TP"):
            continue
        cy = f.GetCourtyard(pcbnew.B_CrtYd if f.GetLayer() == pcbnew.B_Cu else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False, False)
        x0, x1, y0, y1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetRight(), bb.GetTop(), bb.GetBottom()))
        z = pcbnew.ZONE(b)
        z.SetIsRuleArea(True); z.SetDoNotAllowVias(True); z.SetDoNotAllowTracks(False); z.SetDoNotAllowCopperPour(False)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
        ls = pcbnew.LSET(); ls.AddLayer(pcbnew.F_Cu); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls)
        o = z.Outline(); o.NewOutline()
        for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
            o.Append(mm(x), mm(y))
        b.Add(z)


_forenkle = lh.forenkle_dsn


def forenkle_dsn(dsn):
    """Som for hovedkortet, og strømnettene flyttes til klassen «Strom» (0,5 mm) i DSN-fila (KiCad 7 skriver dem i
    standardklassen når klassen settes fra skript)."""
    import re
    _forenkle(dsn)
    s = open(dsn).read()
    m = re.search(r'\(class kicad_default ""([^()]*)', s)
    nett = m.group(1).split()
    sig = [n for n in nett if n not in STROM]
    s = s[:m.start(1)] + " " + " ".join(sig) + "\n      " + s[m.end(1):]
    s = s.replace("(class Strom\n", "(class Strom " + " ".join(n for n in nett if n in STROM) + "\n", 1)
    # vinduet under XIAO-en er et hull i kortet: Freerouting holder bare vanlig klaring til det, så det gjøres 0,4 mm større
    x0, n0, x1, n1 = (round(v * 1000) for v in VINDU)
    gml = f"{x0} -{n1}  {x1} -{n1}  {x1} -{n0}  {x0} -{n0}\n            {x0} -{n1}"
    assert gml in s, "fant ikke vinduet i DSN-fila"
    x0, n0, x1, n1 = x0 - 400, n0 - 400, x1 + 400, n1 + 400
    s = s.replace(gml, f"{x0} -{n1}  {x1} -{n1}  {x1} -{n0}  {x0} -{n0}\n            {x0} -{n1}")
    open(dsn, "w").write(s)


lh.forenkle_dsn = forenkle_dsn
lh.HANDLODD = {"U1"}   # XIAO-en loddes for hånd (kantputer), JLC monterer resten av undersiden
lh.KOMP = kretser_en.KOMP
lh.kretser = kretser_en
lh.UT = HER
lh.NAVN = "skjold-enkel"
lh.omriss_poly = omriss_poly
lh.omriss_punkter = lambda: list(omriss_poly().exterior.coords)[:-1]
lh.silke = silke
for i, (ref, fp, verdi, side, x, n, rot, puter) in enumerate(lh.KOMP):
    lib, navn = fp.split(":")
    if lib.startswith("/"):
        lh.KOMP[i] = (ref, os.path.relpath(lib[:-len(".pretty")], lh.FPLIB) + ":" + navn, verdi, side, x, n, rot, puter)
lh.ANTENNE = (-9, -9, -9, -9)

HOYDE = {"Seeed_XIAO": 3.6, "TSSOP": 1.2, "SOIC-28W": 2.65, "SOT-23": 1.1, "D_SOD-123": 1.2, "R_0805": 0.6, "C_0805": 1.25,
         "C_1210": 2.5, "Hirose_FH12": 2.0, "JST_PH": 5.0, "JST_SH": 3.0, "SW_Tact": 1.5, "TestPoint": 0.05}


def scad_data(b):
    """enkel_data.scad til kabinettet: omriss, hull, USB-C-plassering og bokser for delene (som hovedkort_data.scad)."""
    L = kretser_en.L
    p = omriss_poly()
    ut = ["// Laget av enkel/lag_enkel.py – ikke rediger for hånd.",
          "EN_OMRISS = [" + ", ".join(f"[{x:.3f}, {L - n:.3f}]" for x, n in list(p.exterior.coords)[:-1]) + "];",
          "EN_VINDU = [" + ", ".join(f"[{x:.3f}, {L - n:.3f}]" for x, n in list(p.interiors[0].coords)[:-1]) + "];" if p.interiors else "EN_VINDU = [];",
          "EN_HULL = [[48.0, 107.5, 2.4]];",
          f"EN_USB_X = {kretser_en.XIAO_X:.2f};",
          "EN_DELER = [   // [x0, y0, x1, y1, høyde, side (1 = oppe, −1 = under), ref]"]
    for f in b.GetFootprints():
        ref = f.GetReference()
        navn = str(f.GetFPID().GetLibItemName())
        h = next(v for k_, v in HOYDE.items() if navn.startswith(k_))
        side = -1 if f.GetLayer() == pcbnew.B_Cu else 1
        cy = f.GetCourtyard(pcbnew.B_CrtYd if side < 0 else pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False, False)
        x0, x1, n0, n1 = (pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetRight(), bb.GetTop(), bb.GetBottom()))
        if ref == "U1":   # XIAO: selve modulen (17,5 × 21) og USB-C-kontakten (9 × 7,3, 1,0 mm ut over enden)
            x0, x1, n0, n1 = kretser_en.XIAO_X - 8.75, kretser_en.XIAO_X + 8.75, kretser_en.XIAO_N - 10.5, kretser_en.XIAO_N + 10.5
            ut.append(f"  [{kretser_en.XIAO_X - 4.5:.2f}, {L - (n1 + 1.0):.2f}, {kretser_en.XIAO_X + 4.5:.2f}, {L - (n1 - 6.0):.2f}, 4.2, -1, \"USBC\"],")
        ut.append(f"  [{x0:.2f}, {L - n1:.2f}, {x1:.2f}, {L - n0:.2f}, {h}, {side}, \"{ref}\"],")
    ut[-1] = ut[-1].rstrip(",")
    ut.append("];")
    fil = os.path.join(HER, "enkel_data.scad")
    open(fil, "w").write("\n".join(ut) + "\n")
    return fil


def main():
    b = lag_brett()
    nett = lh.plasser(b)
    strom_klasse(b)
    flater(b, nett)
    pcb = os.path.join(HER, lh.NAVN + ".kicad_pcb")
    b.Save(pcb)
    scad_data(b)
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
    return b


if __name__ == "__main__":
    main()
