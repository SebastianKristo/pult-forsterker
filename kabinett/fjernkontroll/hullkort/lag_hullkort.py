"""Lager alt for hullkort-utgaven fra hullkort.py:

  hullkort_data.scad   omriss, bryterne (snappet), bein, delene på gulvet, stolper og ledningsbunter til kabinettet
  hullkort.json        det samme pluss kutt, ledninger og monteringsstegene, til 3D-siden
  koblinger.csv        alle ledningene med farge og lengde
  tegning.pdf / tegning-oppside.png / tegning-kobberside.png   hullkortet i 1:1 fra begge sider

Bruk:  python3 hullkort/lag_hullkort.py"""
import csv
import json
import math
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import hullkort as hk  # noqa: E402
import taster  # noqa: E402

L, W, CX, P = hk.L, hk.W, hk.CX, hk.P


def y(n):
    return L - n


def scad():
    h = hk.hullkart()
    ut = ["// Laget av hullkort/lag_hullkort.py – ikke rediger for hånd. (x, y) med y = L − n som i modellen.",
          f"HU_Z_KORT = {hk.Z_KORT}; HU_KORT_T = {hk.KORT_T}; HU_SW_H = {hk.SW_H}; HU_SW_KROPP = {hk.SW_KROPP}; HU_BEIN = {hk.BEIN};",
          f"HU_H = {hk.H:.2f}; HU_USB_X = {hk.USB_X:.2f}; HU_USB_Z = {hk.USB_Z:.2f}; HU_FPC_Z = {hk.FPC_Z:.2f};",
          "HU_OMRISS = [" + ", ".join(f"[{x:.3f}, {y(n):.3f}]" for x, n in hk.omriss()) + "];",
          f"HU_HULL = [[{hk.MIDTSKRUE[0]}, {y(hk.MIDTSKRUE[1])}, 2.4]];",
          "HU_BRYTERE = [   // [funksjon, x, y]",
          ",\n".join(f'  ["{b[0]}", {b[6]:.3f}, {y(b[7]):.3f}]' for b in hk.BRYTERE) + "\n];",
          "HU_BEINPOS = [" + ", ".join(f"[{hk.hull_xy(k, j)[0]:.3f}, {y(hk.hull_xy(k, j)[1]):.3f}]" for (k, j) in sorted(h)) + "];",
          "HU_GULV = [   // [x0, y0, x1, y1, z0, z1, ref]",
          ",\n".join(f'  [{x0:.2f}, {y(n1):.2f}, {x1:.2f}, {y(n0):.2f}, {z0:.2f}, {z1:.2f}, "{r}"]'
                     for r, _, x0, x1, n0, n1, z0, z1 in hk.GULV) + "\n];",
          "HU_STOLPER = [" + ", ".join(f"[{x}, {n}]" for x, n in hk.STOLPER) + "];   // (x, n)",
          "HU_PINNER = [" + ", ".join(f"[{x}, {n}]" for x, n in hk.PINNER) + "];   // (x, n)",
          "HU_BUNTER = [" + ", ".join("[" + ", ".join(f"[{x}, {n}]" for x, n in v) + "]" for v in hk.BUNTER.values()) + "];   // (x, n)"]
    # oppsett A med aktuatorene over de snappede bryterne
    s = {b[0]: (b[6], b[7]) for b in hk.BRYTERE}
    rows = []
    for hid, navn, form, x, n, b_, hh, ikon, farge, mal in taster.OPPSETT["rutenett"]:
        m = ", ".join(f"[{s[f][0]:.4f}, {s[f][1]:.4f}]" for f, _ in mal)
        rows.append(f'  ["{hid}", "{form}", {x:.4f}, {n:.4f}, {b_:.2f}, {hh:.2f}, "{ikon}", "{farge}", [{m}]]')
    ut.append("HU_FRONT = [\n" + ",\n".join(rows) + "\n];")
    fil = os.path.join(HER, "hullkort_data.scad")
    open(fil, "w").write("\n".join(ut) + "\n")
    return fil


def koblinger():
    rad = [("nett", "farge", "fra", "til", "lengde_mm", "merknad")]
    for nett, hull, maal, beskr in hk.ledninger_paa_kortet():
        x, n = hk.hull_xy(*hull)
        if isinstance(maal, tuple):
            x2, n2 = hk.hull_xy(*maal)
            lg = int(math.ceil((abs(x2 - x) + abs(n2 - n) + 10) / 10.0) * 10)
            rad.append((nett, hk.farge(nett)[0], f"hull {hull_navn(hull)}", f"hull {hull_navn(maal)}", lg, "på kobbersiden"))
        else:
            mx, mn = hk.ENDEPUNKT["MCP"]
            lg = int(math.ceil((abs(mx - x) + abs(mn - n) + 25) / 10.0) * 10)
            rad.append((nett, hk.farge(nett)[0], f"hull {hull_navn(hull)}", maal, lg, beskr))
    for nett, a, b in hk.LEDNINGER:
        rad.append((nett, hk.farge(nett)[0], a, b, hk.lengde(a.split()[0], b.split()[0]), ""))
    with open(os.path.join(HER, "koblinger.csv"), "w", newline="") as f:
        csv.writer(f).writerows(rad)
    return rad


def hull_navn(kj):
    """Hullnavn som på tegningen: kolonne A–S fra venstre (sett ovenfra), rad 1… fra nesen."""
    k, j = kj
    return f"{'ABCDEFGHIJKLMNOPQRS'[int(k - hk.K_MIN)]}{int(j - hk.J_MIN + 1)}"


def json_data():
    h = hk.hullkart()
    kutt, seg = hk.kutt_og_segmenter(h)
    d = {
        "z": {"kort": hk.Z_KORT, "kortT": hk.KORT_T, "swH": hk.SW_H, "H": round(hk.H, 2), "bein": hk.BEIN, "fpc": hk.FPC_Z},
        "omriss": [[round(x, 3), round(y(n), 3)] for x, n in hk.omriss()],
        "brytere": [{"f": b[0], "x": round(b[6], 3), "y": round(y(b[7]), 3), "avvik": round(b[8], 2), "pinne": hk.mcp_pinne(b[3])}
                    for b in hk.BRYTERE],
        "bein": [[round(hk.hull_xy(k, j)[0], 3), round(y(hk.hull_xy(k, j)[1]), 3), nett] for (k, j), nett in sorted(h.items())],
        "kutt": [[round(CX + k * P, 3), round(y(hk.R0 + j * P), 3), t] for k, j, t in kutt],
        "gulv": [{"ref": r, "navn": nv, "x0": x0, "x1": x1, "y0": y(n1), "y1": y(n0), "z0": z0, "z1": z1} for r, nv, x0, x1, n0, n1, z0, z1 in hk.GULV],
        "ledninger": [],
    }
    # ledningene: hullkortets (fra hullet ned til gulvet og bort til MCP-modulen) og de mellom delene
    zk = hk.Z_KORT - 0.6
    for nett, hull, maal, beskr in hk.ledninger_paa_kortet():
        x, n = hk.hull_xy(*hull)
        if isinstance(maal, tuple):
            x2, n2 = hk.hull_xy(*maal)
            pts = [[x, y(n), zk], [x, y(n2), zk], [x2, y(n2), zk]]
        else:
            mx, mn = hk.ENDEPUNKT["MCP"]
            pin = hk.mcp_pinne(next(b[3] for b in hk.BRYTERE if "K_" + b[0].upper() == nett)) if nett.startswith("K_") else "GND"
            mx += (-9.5 if pin.startswith("GPA") else 9.5) if pin != "GND" else 0
            mn += (int(pin[3]) - 3.5) * 2.54 if pin != "GND" else -12
            pts = [[x, y(n), zk], [x, y(n), 4.6], [mx, y(n), 4.6], [mx, y(mn), 3.6]]
        d["ledninger"].append({"nett": nett, "farge": hk.farge(nett)[1], "fargenavn": hk.farge(nett)[0], "tekst": f"{nett}: {beskr}",
                               "pts": [[round(v, 2) for v in p] for p in pts]})
    for i, (nett, a, b) in enumerate(hk.LEDNINGER):
        (x0, n0), (x1, n1) = hk.endepunkt(a), hk.endepunkt(b)
        z = 2.4 + (i % 4) * 0.6
        pts = [[x0, y(n0), z + 1.0], [x0, y(n0), z], [x0, y((n0 + n1) / 2), z], [x1, y((n0 + n1) / 2), z], [x1, y(n1), z], [x1, y(n1), z + 1.0]]
        d["ledninger"].append({"nett": nett, "farge": hk.farge(nett)[1], "fargenavn": hk.farge(nett)[0], "tekst": f"{nett}: {a} → {b}",
                               "pts": [[round(v, 2) for v in p] for p in pts]})
    d["smadeler"] = [{"ref": r, "verdi": v, "hvor": hv, "hvordan": hd} for r, v, a, b, hv, hd in hk.SMADELER]
    fil = os.path.join(HER, "hullkort.json")
    json.dump(d, open(fil, "w"), ensure_ascii=False, indent=0)
    return fil


if __name__ == "__main__":
    print("skrev", scad())
    print("skrev", json_data())
    print("koblinger.csv:", len(koblinger()) - 1, "ledninger")
    import tegning
    tegning.main()
