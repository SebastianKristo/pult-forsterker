"""Tegningen av hullkortet i 1:1 (skriv ut i 100 %, «faktisk størrelse»): tegning.pdf (2 sider A4) og PNG-er.

Side 1: hullkortet sett ovenfra (bryterne, nesen opp) og fra kobbersiden (speilvendt: kutt, ledninger, lodding).
Side 2: delene på gulvet i bunnen (XIAO, MCP-modulen, FPC-adapterne, pogo) med hullkortets omriss over."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Polygon, Rectangle  # noqa: E402

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HER)
import hullkort as hk  # noqa: E402

MM = 1 / 25.4
A4 = (210 * MM, 297 * MM)
KOL = "ABCDEFGHIJKLMNOPQRS"


def akser(fig, x0, y0, w, h, xlim, ylim, speil=False):
    """Akser i mm på arket: (x0, y0) nederst til venstre, w × h mm, med 1:1-skala."""
    ax = fig.add_axes([x0 / 210, y0 / 297, w / 210, h / 297])
    ax.set_xlim(*(xlim[::-1] if speil else xlim))
    ax.set_ylim(ylim[1], ylim[0])            # n nedover (nesen øverst)
    ax.set_aspect("equal")
    ax.axis("off")
    return ax


def hullnavn(k, j):
    return f"{KOL[k - hk.K_MIN]}{j - hk.J_MIN + 1}"


def kort(ax, speil):
    o = hk.omriss()
    ax.add_patch(Polygon(o, closed=True, fc="#f3e9d2" if not speil else "#f6efe2", ec="#333", lw=0.6))
    h = hk.hullkart()
    kutt, seg = hk.kutt_og_segmenter(h)
    if speil:   # kobberstripene
        for j in range(hk.J_MIN, hk.J_MAX + 1):
            ks = [k for k in range(hk.K_MIN, hk.K_MAX + 1) if hk.paa_kortet(k, j)]
            if ks:
                x0, n = hk.hull_xy(ks[0], j)
                x1, _ = hk.hull_xy(ks[-1], j)
                ax.add_patch(Rectangle((x0 - 1.15, n - 0.9), x1 - x0 + 2.3, 1.8, fc="#d9a066", ec="none", alpha=0.75))
    for j in range(hk.J_MIN, hk.J_MAX + 1):
        for k in range(hk.K_MIN, hk.K_MAX + 1):
            if hk.paa_kortet(k, j):
                x, n = hk.hull_xy(k, j)
                ax.add_patch(Circle((x, n), 0.5, fc="white", ec="#777", lw=0.25))
    # kolonne- og radmerker
    for k in range(hk.K_MIN, hk.K_MAX + 1):
        x, _ = hk.hull_xy(k, hk.J_MIN)
        ax.text(x, hk.KANT_N0 - 1.3, KOL[k - hk.K_MIN], ha="center", va="bottom", fontsize=4.2, color="#555")
    for j in range(hk.J_MIN, hk.J_MAX + 1, 5):
        _, n = hk.hull_xy(hk.K_MIN, j)
        ax.text(hk.KANT_X0 - 0.8 if not speil else hk.KANT_X0 - 0.8, n, str(j - hk.J_MIN + 1), ha="right" if not speil else "left",
                va="center", fontsize=4.2, color="#555")
    mx, mn = hk.MIDTSKRUE
    ax.add_patch(Circle((mx, mn), 1.2, fc="#bbb", ec="#333", lw=0.4))
    ax.text(mx, mn + 2.2, "bor Ø2,4", ha="center", fontsize=3.6)
    return h, kutt, seg


def oppside(ax):
    h, kutt, seg = kort(ax, False)
    for b in hk.BRYTERE:
        x, n = b[6], b[7]
        ax.add_patch(Rectangle((x - 3, n - 3), 6, 6, fc="#2b2b2d", ec="#000", lw=0.4, alpha=0.85))
        ax.add_patch(Circle((x, n), 1.75, fc="#555", ec="#000", lw=0.3))
        ax.text(x, n, b[0].replace("_", " ").replace("spill pause", "spill/\npause").replace("vol opp", "vol+").replace("vol ned", "vol−"),
                ha="center", va="center", fontsize=3.4, color="white")
        for k, j, nett in hk.bein(b):
            bx, bn = hk.hull_xy(k, j)
            ax.add_patch(Circle((bx, bn), 0.55, fc="#111" if nett == "GND" else "#c9b037", ec="none"))
    for x, n in hk.PINNER:
        ax.add_patch(Circle((x, n), 1.1, fc="none", ec="#2f6fd0", lw=0.5, ls="--"))
        ax.text(x, n - 1.6, "pinne", ha="center", fontsize=3.2, color="#2f6fd0")
    ax.text(hk.CX, hk.KANT_N0 - 4.2, "OPPSIDE (bryterne) – sett ovenfra, nesen opp", ha="center", fontsize=6, weight="bold")
    ax.text(hk.CX, hk.KANT_N1 + 2.0, "svart bein = GND-siden · gult bein = tastens side", ha="center", va="top", fontsize=4.2)


def kobberside(ax):
    h, kutt, seg = kort(ax, True)
    for k, j, t in kutt:
        x, n = hk.CX + k * hk.P, hk.R0 + j * hk.P
        if t == "hull":
            ax.plot([x - 0.9, x + 0.9], [n - 0.9, n + 0.9], color="#d00", lw=0.8)
            ax.plot([x - 0.9, x + 0.9], [n + 0.9, n - 0.9], color="#d00", lw=0.8)
        else:
            ax.plot([x, x], [n - 1.1, n + 1.1], color="#d00", lw=0.9)
    for (k, j), nett in h.items():
        x, n = hk.hull_xy(k, j)
        ax.add_patch(Circle((x, n), 0.7, fc="#9a9a9a", ec="#444", lw=0.3))
    for nett, hull, maal, beskr in hk.ledninger_paa_kortet():
        x, n = hk.hull_xy(*hull)
        f = hk.farge(nett)[1]
        if isinstance(maal, tuple):
            x2, n2 = hk.hull_xy(*maal)
            ax.plot([x, x, x2], [n, n2, n2], color=f, lw=0.9, solid_capstyle="round")
        else:
            ax.add_patch(Circle((x, n), 0.75, fc=f, ec="#000", lw=0.3))
            ax.text(x + (1.2 if x < hk.CX else -1.2), n + 0.2, f"{hullnavn(*hull)} → {maal}\n{hk.farge(nett)[0]}",
                    ha="left" if x < hk.CX else "right", va="center", fontsize=3.0,
                    bbox=dict(fc="white", ec="none", alpha=0.7, pad=0.2))
    ax.text(hk.CX, hk.KANT_N0 - 4.2, "KOBBERSIDE – sett nedenfra (speilvendt)", ha="center", fontsize=6, weight="bold")
    ax.text(hk.CX, hk.KANT_N1 + 2.0, "rødt × = kutt stripa i hullet (3,5 mm bor) · rød strek = riss mellom hullene\n"
            "svart = GND-kjeden · farget prikk = ledning til MCP-modulen", ha="center", va="top", fontsize=4.0)


def gulv(ax):
    # bunnens innside, delene, og hullkortets omriss stiplet
    ax.add_patch(Rectangle((0, 0), hk.W, hk.L, fc="#e9e7e2", ec="#333", lw=0.5))
    ax.add_patch(Polygon(hk.omriss(), closed=True, fc="none", ec="#999", lw=0.5, ls="--"))
    farge = {"U1": "#3a3a3d", "USBC": "#999", "U2": "#6a4aa8", "A1": "#c9822b", "A2": "#c9822b"}
    for r, navn, x0, x1, n0, n1, z0, z1 in hk.GULV:
        ax.add_patch(Rectangle((x0, n0), x1 - x0, n1 - n0, fc=farge[r], ec="#000", lw=0.4, alpha=0.35 if "kort" in navn else 0.7))
    tekst = {"U1": "XIAO ESP32S3\nUSB-C mot halen", "U2": "MCP23017-modul\n(CJMCU-2317)\npå tape", "A1": "FPC 18p → 2,54\n(skjermen)",
             "A2": "FPC 6p →\n2,54\n(berøring)"}
    for r in tekst:
        bs = [g for g in hk.GULV if g[0] == r]
        x0, x1 = min(b[2] for b in bs), max(b[3] for b in bs)
        n0, n1 = min(b[4] for b in bs), max(b[5] for b in bs)
        ax.text((x0 + x1) / 2, (n0 + n1) / 2, tekst[r], ha="center", va="center", fontsize=4.5, color="#000")
    ax.add_patch(Rectangle((40 - 3, 159 - 10.5), 6, 21, fc="#222", ec="#000", lw=0.4, alpha=0.5))
    ax.text(40, 159, "pogo\n(dokk)", ha="center", va="center", fontsize=4, color="white")
    ax.add_patch(Rectangle((hk.CX - 17, 12), 34, 50, fc="#9aa0a8", ec="#000", lw=0.4, alpha=0.6))
    ax.text(hk.CX, 37, "LiPo 603450\n1200 mAh", ha="center", va="center", fontsize=5)
    ax.add_patch(Rectangle((hk.CX - 17, 6.6), 34, 1.0, fc="#2f9a52", ec="#000", lw=0.4))
    ax.text(hk.CX, 4.6, "IR-kortet (2 × IR-diode, VS1838B, AO3400A)", ha="center", fontsize=4)
    for navn, pts in hk.BUNTER.items():
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#d23a2c" if navn == "batteri" else "#2bb3a8", lw=1.4, alpha=0.8)
    for x, n in hk.STOLPER + hk.PINNER:
        ax.add_patch(Circle((x, n), 1.5, fc="#777", ec="#000", lw=0.3))
    ax.text(hk.CX, -4, "BUNNEN – delene på gulvet, sett ovenfra (hullkortets omriss stiplet)", ha="center", fontsize=6, weight="bold")


def main():
    pdf = os.path.join(HER, "tegning.pdf")
    xl = (hk.KANT_X0 - 3, hk.KANT_X1 + 3)
    nl = (hk.KANT_N0 - 6, hk.KANT_N1 + 7)
    bw, bh = xl[1] - xl[0], nl[1] - nl[0]
    with PdfPages(pdf) as pp:
        fig = plt.figure(figsize=A4)
        fig.text(0.5, 0.975, "Skjold Fjernkontroll – hullkort-utgaven, hullkortet i 1:1", ha="center", fontsize=10, weight="bold")
        fig.text(0.5, 0.955, "Skriv ut i 100 % («faktisk størrelse»). Linjalen under skal være 50 mm. Hullkort 2,54 mm med kobberstriper på tvers, "
                 f"{hk.K_MAX - hk.K_MIN + 1} × {hk.J_MAX - hk.J_MIN + 1} hull.", ha="center", fontsize=6)
        a1 = akser(fig, 12, 297 - 25 - bh, bw, bh, xl, nl)
        oppside(a1)
        a2 = akser(fig, 210 - 12 - bw, 297 - 25 - bh, bw, bh, xl, nl, speil=True)
        kobberside(a2)
        # tabellen over ledningene på hullkortet (under tegningene)
        import math
        h = hk.hullkart()
        kutt, _ = hk.kutt_og_segmenter(h)
        rader = ["Ledninger på kobbersiden (tynn 30 AWG Kynar/silikon):", ""]
        for nett, hull, maal, beskr in hk.ledninger_paa_kortet():
            x, n = hk.hull_xy(*hull)
            if isinstance(maal, tuple):
                x2, n2 = hk.hull_xy(*maal)
                lg = int(math.ceil((abs(x2 - x) + abs(n2 - n) + 10) / 10.0) * 10)
                rader.append(f"{nett:13s} {hullnavn(*hull):>4s} → {hullnavn(*maal):<10s} {hk.farge(nett)[0]:10s} {lg:3d} mm")
            else:
                mx, mn = hk.ENDEPUNKT["MCP"]
                lg = int(math.ceil((abs(mx - x) + abs(mn - n) + 25) / 10.0) * 10)
                rader.append(f"{nett:13s} {hullnavn(*hull):>4s} → {maal:<10s} {hk.farge(nett)[0]:10s} {lg:3d} mm")
        rader += ["", f"Kutt: {sum(1 for k in kutt if k[2] == 'hull')} i hull (drill 3,5 mm, vri for hånd), "
                  f"{sum(1 for k in kutt if k[2] == 'riss')} riss mellom hull (kniv, to snitt)."]
        half = (len(rader) + 1) // 2
        fig.text(12 / 210, (297 - 25 - bh - 12) / 297, "\n".join(rader[:half]), family="monospace", fontsize=5.2, va="top")
        fig.text(110 / 210, (297 - 25 - bh - 12) / 297, "\n".join(rader[half:]), family="monospace", fontsize=5.2, va="top")
        lin = fig.add_axes([60 / 210, 18 / 297, 50 / 210, 4 / 297])
        lin.set_xlim(0, 50); lin.set_ylim(0, 4); lin.axis("off")
        lin.plot([0, 50], [1, 1], color="k", lw=0.8)
        for i in range(0, 51, 10):
            lin.plot([i, i], [1, 2.5], color="k", lw=0.6)
            lin.text(i, 3, f"{i}", ha="center", fontsize=5)
        fig.text(115 / 210, 19 / 297, "mm", fontsize=6)
        pp.savefig(fig)
        fig.savefig(os.path.join(HER, "tegning-side1.png"), dpi=300)
        # to PNG-er, én per side av kortet, også 1:1 ved 300 dpi
        for navn, f_ in (("oppside", oppside), ("kobberside", kobberside)):
            f2 = plt.figure(figsize=((bw + 6) * MM, (bh + 6) * MM))
            ax = f2.add_axes([3 / (bw + 6), 3 / (bh + 6), bw / (bw + 6), bh / (bh + 6)])
            ax.set_xlim(*(xl[::-1] if navn == "kobberside" else xl)); ax.set_ylim(nl[1], nl[0]); ax.set_aspect("equal"); ax.axis("off")
            f_(ax)
            f2.savefig(os.path.join(HER, f"tegning-{navn}.png"), dpi=300, facecolor="white")
            plt.close(f2)
        plt.close(fig)
        fig = plt.figure(figsize=A4)
        fig.text(0.5, 0.975, "Skjold Fjernkontroll – hullkort-utgaven, delene i bunnen (1:1)", ha="center", fontsize=10, weight="bold")
        ax = akser(fig, (210 - 61) / 2, 297 - 20 - 210, 61, 210, (-3, hk.W + 3), (-8, hk.L + 2))
        gulv(ax)
        pp.savefig(fig)
        fig.savefig(os.path.join(HER, "tegning-side2.png"), dpi=200)
        plt.close(fig)
    print("skrev", pdf, "og tegning-*.png")


if __name__ == "__main__":
    main()
