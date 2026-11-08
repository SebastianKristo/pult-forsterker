"""Tastene på Skjold Fjernkontroll – én kilde for kabinettet, tastekortet, fastvaren og dokumentasjonen.

To varianter: «kort» (standard, uten talltastene og smarthus-raden: 14 taster, 201,5 mm) og «full» (valgfri, 30 taster, 244,5 mm).
Kjør:  python3 taster.py
  skriver  taster.scad                      (hettene og bryterne for begge variantene til skjold_fjernkontroll.scad)
           tastekort/ og tastekort_full/     (plassering.csv og koblinger.csv: bryter- og brikkeplassering og
                                              hver bryter → TCA9555-brikke og pinne)
           ../../esphome/skjold-fjernkontroll.yaml       (standard/kort: blokkene mellom «# >>> navneliste/hendelser/taster» og «# <<< …»)
           ../../esphome/skjold-fjernkontroll-full.yaml  (laget fra den over, med full variants taster og 3 × TCA9555)
           ../../esphome/skjold-fjernkontroll-hovedkort.yaml  (standard på hovedkortet: samme taster, hovedkortets GPIO-er)
           ../../esphome/skjold-fjernkontroll-tastekort-a.yaml  (håndkoblet med tastekort A: oppsett A, én TCA9555)
           ../../esphome/skjold-fjernkontroll-enkel.yaml  (enkel utgave: XIAO ESP32S3 + MCP23017, oppsett A)
  og skriver koblingstabellen for standard (kort) til stdout, til LES_MEG.md (python3 taster.py full for full).

Koordinater: x = tvers (0 … W, venstre kant = 0), n = avstand fra nesen (IR-enden) målt langs fjernkontrollen.
Former:  rund (d) · pille (b × h, h langs fjernkontrollen) · vippe (to brytere) · ring (D-pad med fire brytere) · ok."""
import csv
import math
import os
import re

W, L = 55.0, 230.0          # ytre mål (må stemme med skjold_fjernkontroll.scad); L byttes av bruk("kort")
L_FULL, L_KORT = 245.5, 202.5
DN = 22.0                   # alt under skjermen flyttet 22 mm mot halen for 2,8″-skjermen (DN i .scad)
CX = W / 2
SPILL = 0.35                # klaring rundt hetta i hullet (hver side)
MIN_STEG = 1.4              # minste materiale mellom to hull i toppen
PCB_N0, PCB_N1 = 57.5 + DN, 198.5 + DN  # tastekortet strekker seg fra n = 57,5 til 198,5 (under skjermen og ned mot halen)

# ---------- hettene ----------
# (id, navn, form, x, n, b, h, ikon, farge, [bryter-id …])
HETTER = [
    # øverste rad, like bred som gullringen: av/på, Skjold-tasten (gull) og meny (kort trykk = meny, langt = guide)
    ("av", "Av-på", "rund", CX - 14.5, 60.6, 11.5, 11.5, "av", "mork", ["av"]),
    ("hjem", "Skjold (aktiviteter)", "rund", CX, 60.6, 11.5, 11.5, "skjold", "gull", ["hjem"]),
    ("meny", "Meny (hold: guide)", "rund", CX + 14.5, 60.6, 11.5, 11.5, "meny", "mork", ["meny"]),
    # D-pad: gullring Ø39 med fire brytere og OK (Ø15) i midten
    ("dpad", "D-pad", "ring", CX, 88.7, 39, 17, "pil", "gull", ["opp", "ned", "venstre", "hoyre"]),
    ("ok", "OK", "ok", CX, 88.7, 15, 15, "OK", "mork", ["ok"]),
] + [
    # talltaster 1–9, så − 0 ↵
    (f"tall_{d}", f"Tall {d}", "pille", (CX - 14, CX, CX + 14)[(d - 1) % 3], 171.7 + 8.4 * ((d - 1) // 3), 11.6, 6.0, str(d), "mork", [f"tall_{d}"])
    for d in range(1, 10)
] + [
    ("strek", "Strek", "pille", CX - 14, 196.9, 11.6, 6.0, "strek", "mork", ["strek"]),
    ("tall_0", "Tall 0", "pille", CX, 196.9, 11.6, 6.0, "0", "mork", ["tall_0"]),
    ("enter", "Enter", "pille", CX + 14, 196.9, 11.6, 6.0, "enter", "mork", ["enter"]),
    # smarthus-raden: lys, stikkontakt, − og +
    ("lys", "Lys", "pille", CX - 18, 206.5, 9.6, 6.0, "lys", "lys", ["lys"]),
    ("stikk", "Stikkontakt", "pille", CX - 6, 206.5, 9.6, 6.0, "stikk", "lys", ["stikk"]),
    ("minus", "Minus (dempe lys)", "pille", CX + 6, 206.5, 9.6, 6.0, "minus", "lys", ["minus"]),
    ("pluss", "Pluss (mer lys)", "pille", CX + 18, 206.5, 9.6, 6.0, "pluss", "lys", ["pluss"]),
]

# alt under skjermen ligger DN mm lenger bak enn i første utgave (2,0″-skjerm)
HETTER = [h[:4] + (h[4] + DN,) + h[5:] for h in HETTER]

# ---------- tasteoppsett under D-paden ----------
# Tastekortet har et fast rutenett av brytere under tasteblokken: 7 kolonner × 5 rader. Hver hette trykker på én bestemt
# bryter (to for volumpiller); over de andre bryterne har hetta en grunn lomme, så de ikke trykkes. Et nytt oppsett er
# en ny topp med hetter (printes på nytt) og en ny linje i OPPSETT under; kortet og fastvaren er de samme.
GRID_DX = [-17.25, -9.625, -4.8125, 0.0, 4.8125, 9.625, 17.25]   # kolonner: x − CX
GRID_N = [118.3 + 9.625 * k for k in range(5)]                  # rader: n (før DN)
GRID = [(CX + dx, n + DN) for n in GRID_N for dx in GRID_DX]     # rad for rad, venstre mot høyre
PINNER = [(5.5, GRID_N[2] + DN), (W - 5.5, GRID_N[2] + DN)]   # pinner fra toppen og stolper fra bunnen klemmer kortet
FUNKSJONER = ["tilbake", "avslutt", "spill_pause", "demp", "vol_opp", "vol_ned"]


def g(c, r):
    """Bryter i rutenettet: kolonne c (0–6), rad r (0–4) → indeks."""
    return r * len(GRID_DX) + c


# (id, navn, form, x, n, b, h, ikon, farge, [(funksjon, rutenett-indeks), …])  – n før DN
_R = GRID_N
OPPSETT = {
    # A: to kolonner med like store runde taster (Ø16, 3,25 mm mellomrom); volumpillen øverst til høyre
    "rutenett": [
        ("tilbake", "Tilbake", "rund", CX - 9.625, _R[0], 16, 16, "tilbake", "mork", [("tilbake", g(1, 0))]),
        ("avslutt", "Avslutt", "rund", CX - 9.625, _R[2], 16, 16, "avslutt", "mork", [("avslutt", g(1, 2))]),
        ("spill_pause", "Spill-pause", "rund", CX - 9.625, _R[4], 16, 16, "spill_pause", "mork", [("spill_pause", g(1, 4))]),
        ("vol", "Volum", "vippe", CX + 9.625, _R[1], 16, 35.25, "vol", "mork", [("vol_opp", g(5, 0)), ("vol_ned", g(5, 2))]),
        ("demp", "Demp", "rund", CX + 9.625, _R[4], 16, 16, "demp", "mork", [("demp", g(5, 4))]),
    ],
    # B: vannrett volumpille over hele bredden (− til venstre, + til høyre) og en rad med fire runde taster
    "vannrett": [
        ("vol", "Volum", "vippe", CX, _R[1], 35.75, 14, "vol", "mork", [("vol_ned", g(0, 1)), ("vol_opp", g(6, 1))]),
        ("tilbake", "Tilbake", "rund", CX - 17.25, _R[3], 8.6, 8.6, "tilbake", "mork", [("tilbake", g(0, 3))]),
        ("spill_pause", "Spill-pause", "rund", CX - 5.75, _R[3], 8.6, 8.6, "spill_pause", "mork", [("spill_pause", g(2, 3))]),
        ("demp", "Demp", "rund", CX + 5.75, _R[3], 8.6, 8.6, "demp", "mork", [("demp", g(4, 3))]),
        ("avslutt", "Avslutt", "rund", CX + 17.25, _R[3], 8.6, 8.6, "avslutt", "mork", [("avslutt", g(6, 3))]),
    ],
    # C: stor spill/pause i midten (Ø22) med fire små taster i hjørnene og demp under
    "stor": [
        ("spill_pause", "Spill-pause", "rund", CX, _R[2], 22, 22, "spill_pause", "mork", [("spill_pause", g(3, 2))]),
        ("tilbake", "Tilbake", "rund", CX - 17.25, _R[0], 9, 9, "tilbake", "mork", [("tilbake", g(0, 0))]),
        ("avslutt", "Avslutt", "rund", CX + 17.25, _R[0], 9, 9, "avslutt", "mork", [("avslutt", g(6, 0))]),
        ("vol_ned", "Volum −", "rund", CX - 17.25, _R[4], 9, 9, "minus", "mork", [("vol_ned", g(0, 4))]),
        ("vol_opp", "Volum +", "rund", CX + 17.25, _R[4], 9, 9, "pluss", "mork", [("vol_opp", g(6, 4))]),
        ("demp", "Demp", "rund", CX, _R[4], 10.8, 10.8, "demp", "mork", [("demp", g(3, 4))]),
    ],
}
OPPSETT = {k: [h[:4] + (h[4] + DN,) + h[5:] for h in v] for k, v in OPPSETT.items()}
OPPSETT_NAVN = {"rutenett": "A «Rutenett»", "vannrett": "B «Vannrett»", "stor": "C «Stor»"}


def kart(navn):
    """Rutenett-indeks → funksjon for et oppsett ("" = ikke i bruk)."""
    k = [""] * len(GRID)
    for h in OPPSETT[navn]:
        for f, i in h[9]:
            k[i] = f
    return k
HETTER_FULL = HETTER
# kort variant: uten talltastene (1–9, −, 0, ↵) og smarthus-raden (lys, stikk, −, +); fargetastene blir nederste rad
KORT_UTEN = {f"tall_{d}" for d in range(10)} | {"strek", "enter", "lys", "stikk", "minus", "pluss"}
HETTER_KORT = [h for h in HETTER_FULL if h[0] not in KORT_UTEN]
VARIANT = "full"
TCA_POS = [(CX - 13, 135.0 + DN), (CX, 135.0 + DN), (CX + 13, 135.0 + DN)]

BRYTER_NAVN = {
    "opp": "Opp", "ned": "Ned", "venstre": "Venstre", "hoyre": "Høyre", "vol_opp": "Volum +", "vol_ned": "Volum −",
    "kan_opp": "Kanal +", "kan_ned": "Kanal −",
}
DPAD_R = 14.0      # bryterne under gullringen (radius fra senter)
VIPPE_D = 9.625    # bryterne under volumpillen: ± fra midten


def brytere():
    """[(bryter-id, navn, x, n, hette-id)] i fast rekkefølge (= TCA9555-pinnene)."""
    ut = []
    for hid, navn, form, x, n, b, h, ikon, farge, ids in HETTER:
        if form == "ring":
            for bid, (dx, dn) in zip(ids, [(0, -DPAD_R), (0, DPAD_R), (-DPAD_R, 0), (DPAD_R, 0)]):
                ut.append((bid, BRYTER_NAVN[bid], x + dx, n + dn, hid))
        elif form == "vippe":
            for bid, dn in zip(ids, [-VIPPE_D, VIPPE_D]):
                ut.append((bid, BRYTER_NAVN[bid], x, n + dn, hid))
        else:
            ut.append((ids[0], navn, x, n, hid))
    fast = [b for b in ut if not b[0].startswith(("tall_", "strek", "enter", "lys", "stikk", "minus", "pluss"))]
    resten = [b for b in ut if b not in fast]
    rute = [(f"g{i:02d}", f"Rutenett r{i // len(GRID_DX)} k{i % len(GRID_DX)}", x, n, "front") for i, (x, n) in enumerate(GRID)]
    return fast + rute + resten


def tca(i):
    """Bryter nr. i → (brikke, adresse, pinne 0–15, «P0_3»)."""
    chip = i // 16
    pin = i % 16
    return "ABCD"[chip], 0x20 + chip, pin, f"P{pin // 8}_{pin % 8}"


# fire ledige pinner på siste brikke (pinne 12–15) brukes til styring: C i full variant, B i kort
def ekstra():
    c = "ABCD"[len(TCA_POS) - 1]
    return [("vibrator", c, 12, "P1_4", "utgang: vibrasjonsmotor (via AO3400)"),
            ("strom_skjerm", c, 13, "P1_5", "utgang: 3V3 til skjerm og IR-mottaker (lav = på, AO3401)"),
            ("lader", c, 14, "P1_6", "inngang: TP4056 CHRG (lav = lader)"),
            ("ledig", c, 15, "P1_7", "ledig")]


def bruk(variant):
    """Velg variant («full» eller «kort») for funksjonene under."""
    global HETTER, L, PCB_N1, VARIANT, TCA_POS
    VARIANT = variant
    if variant == "kort":
        HETTER, L, TCA_POS = HETTER_KORT, L_KORT, [(CX + 13, 145.0), (CX + 13, 157.0), (CX + 13, 169.0)]
    else:
        HETTER, L, TCA_POS = HETTER_FULL, L_FULL, [(CX - 13, 150.0), (CX, 150.0), (CX + 13, 150.0), (CX + 13, 162.0)]
    PCB_N1 = max(b[3] for b in brytere()) + 6.3   # 6,3 mm bak siste bryterrad


# ---------- 2D-former for sjekk av materialet mellom hullene ----------
def hull_form(h):
    hid, navn, form, x, n, b, hh, *_ = h
    s = SPILL
    if form in ("rund", "ok"):
        return ("sirkel", x, n, b / 2 + s)
    if form == "ring":
        return ("sirkel", x, n, b / 2 + s)
    if form in ("pille", "vippe"):
        return ("pille", x, n, b / 2 + s, hh / 2 + s)
    raise ValueError(form)


def pille_punkter(x, n, a, c, k=48):
    """Rand av en pille (rundet rektangel med radius = halve korteste side)."""
    r = min(a, c)
    pts = []
    for cx, cy, a0 in [(x + a - r, n + c - r, 0), (x - a + r, n + c - r, 90), (x - a + r, n - c + r, 180), (x + a - r, n - c + r, 270)]:
        for i in range(k // 4 + 1):
            t = math.radians(a0 + 90 * i / (k // 4))
            pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def rand(f, k=96):
    if f[0] == "sirkel":
        _, x, n, r = f
        return [(x + r * math.cos(2 * math.pi * i / k), n + r * math.sin(2 * math.pi * i / k)) for i in range(k)]
    return pille_punkter(*f[1:])


def inni(f, p):
    if f[0] == "sirkel":
        return math.hypot(p[0] - f[1], p[1] - f[2]) < f[3]
    _, x, n, a, c = f
    r = min(a, c)
    dx, dy = max(abs(p[0] - x) - (a - r), 0), max(abs(p[1] - n) - (c - r), 0)
    return math.hypot(dx, dy) < r


def avstand(fa, fb):
    """Korteste avstand mellom randene til to hull (negativ = overlapp)."""
    pa, pb = rand(fa), rand(fb)
    if any(inni(fb, p) for p in pa) or any(inni(fa, p) for p in pb):
        return -1.0
    return min(math.hypot(a[0] - b[0], a[1] - b[1]) for a in pa for b in pb)


def sjekk_steg():
    """[(hette a, hette b, avstand)] for alle par nærmere enn MIN_STEG (ring og OK er ett hull sammen),
    for de faste tastene sammen med hvert tasteoppsett."""
    feil = []
    for o, hf in OPPSETT.items():
        feil += [(o,) + f for f in _steg([q for q in HETTER if q[2] != "ok"] + hf)]
    return feil


def _steg(hs):
    feil = []
    feil = []
    for i, a in enumerate(hs):
        for b in hs[i + 1:]:
            fa, fb = hull_form(a), hull_form(b)
            if abs(fa[1] - fb[1]) > 40 or abs(fa[2] - fb[2]) > 40:
                continue
            d = avstand(fa, fb)
            if d < MIN_STEG + (0.7 if a in sum(OPPSETT.values(), []) or b in sum(OPPSETT.values(), []) else 0):
                feil.append((a[0], b[0], round(d, 2)))   # oppsetthettene: ≥ 2,1 mm, så flensene ikke møtes
    return feil


# ---------- utdata ----------
def scad():
    """taster.scad: lister som skjold_fjernkontroll.scad leser (n måles fra nesen, y = L − n i modellen)."""
    rows = []
    for hid, navn, form, x, n, b, h, ikon, farge, ids in HETTER:
        rows.append(f'  ["{hid}", "{form}", {x:.2f}, {n:.2f}, {b:.2f}, {h:.2f}, "{ikon}", "{farge}"]')
    br = [f'  ["{bid}", {x:.2f}, {n:.2f}]' for bid, _, x, n, _ in brytere()]
    v = VARIANT.upper()
    return (f"// variant «{VARIANT}»: {len(brytere())} brytere ({len(GRID)} i rutenettet), {len(HETTER)} faste hetter, L = {L}\n"
            f"HETTER_{v} = [\n{(',' + chr(10)).join(rows)}\n];\n"
            f"BRYTERE_{v} = [\n{(',' + chr(10)).join(br)}\n];\n"
            f"PCB_N1_{v} = {PCB_N1:.2f};\nL_{v} = {L};\n")


def front_scad():
    """Rutenettet og tasteoppsettene til taster.scad. Oppsetthette: [id, form, x, n, b, h, ikon, farge, [[x, n] mål …]]."""
    ut = ["// ---------- tasteoppsett ----------",
          "GRID = [" + ", ".join(f"[{x:.4f}, {n:.4f}]" for x, n in GRID) + "];",
          "FRONT_STOTTER = [" + ", ".join(f"[{x}, {n:.4f}]" for x, n in PINNER) + "];",
          "OPPSETT_NAVN = [" + ", ".join(f'"{o}"' for o in OPPSETT) + "];"]
    for o, hs in OPPSETT.items():
        rows = []
        for hid, navn, form, x, n, b, h, ikon, farge, mal in hs:
            m = ", ".join(f"[{GRID[i][0]:.4f}, {GRID[i][1]:.4f}]" for _, i in mal)
            rows.append(f'  ["{hid}", "{form}", {x:.4f}, {n:.4f}, {b:.2f}, {h:.2f}, "{ikon}", "{farge}", [{m}]]')
        ut.append(f"OPPSETT_{o.upper()} = [\n" + ",\n".join(rows) + "\n];")
    return "\n".join(ut) + "\n"


def plassering():
    """Bryterne og brikkene på tastekortet. Origo = kortets nedre venstre hjørne sett ovenfra (halen ned):
    kortet går fra x = 3,2 til W − 3,2 og n = PCB_N0 … PCB_N1, så kort-x = x − 3,2 og kort-y = PCB_N1 − n."""
    rows = [("ref", "verdi", "fotavtrykk", "x_mm", "y_mm", "rot", "side")]
    for i, (bid, navn, x, n, hid) in enumerate(brytere()):
        rows.append((f"SW{i + 1}", f"{bid}", "SW-SMD_4x4x1.5", f"{x - 3.2:.2f}", f"{PCB_N1 - n:.2f}", "0", "topp"))
    for i, (x, n) in enumerate(TCA_POS):
        rows.append((f"U{i + 1}", f"TCA9555PWR 0x{0x20 + i:02X}", "TSSOP-24", f"{x - 3.2:.2f}", f"{PCB_N1 - n:.2f}", "90", "bunn"))
    fpc_n = 8.4 + 66.5 + 37.0   # fpcN i skjold_fjernkontroll.scad: skjermhalen er 42,58 mm
    tp_n = 8.4 + 66.5 + 29.6    # tpN: berøringens hale er ca. 35,2 mm
    fpc_x = CX - 47.8 / 2 + 17.96 + 9.5 / 2
    rows.append(("J1", "FPC 18p 0,5 mm (skjerm)", "FPC-18P-0.5mm bunnkontakt (FH12-18S-0.5SH-stil)", f"{fpc_x - 3.2:.2f}", f"{PCB_N1 - fpc_n:.2f}", "0", "bunn"))
    rows.append(("J2", "FPC 6p 0,5 mm (berøring)", "FPC-6P-0.5mm bunnkontakt (FH12-6S-0.5SH-stil)", f"{CX + 8 - 3.2:.2f}", f"{PCB_N1 - tp_n:.2f}", "0", "bunn"))
    rows.append(("U9", "XPT2046 (bare budsjett-skjerm)", "TSSOP-16", f"{CX - 17 - 3.2:.2f}", f"{PCB_N1 - fpc_n:.2f}", "90", "bunn"))
    return rows


def koblinger():
    rows = [("bryter", "navn", "brikke", "adresse", "pinne", "esphome_nummer")]
    for i, (bid, navn, x, n, hid) in enumerate(brytere()):
        c, a, p, pn = tca(i)
        rows.append((bid, navn, c, f"0x{a:02X}", pn, str(p)))
    for bid, c, p, pn, m in ekstra():
        rows.append((bid, m, c, f"0x{0x20 + len(TCA_POS) - 1:02X}", pn, str(p)))
    return rows


REPETER = {"vol_opp", "vol_ned", "opp", "ned", "venstre", "hoyre", "minus", "pluss"}   # gjentas når de holdes
TREG = {"av", "hjem", "meny", "tilbake", "avslutt", "lys", "stikk"}                  # har langt trykk (sendes ved slipp)
DOBBEL = {"av", "hjem", "meny", "lys", "stikk"}                                        # har også dobbelttrykk
# Samme lister står i esphome/skjold_ui.h (Tastatur).


def tastenavn():
    """Navnene tastene sendes med (faste taster, tasteblokkens funksjoner og talltastene): samme rekkefølge som IR-plassene."""
    fast = [b[0] for b in brytere() if not b[0].startswith("g")]
    return fast[:8] + FUNKSJONER + fast[8:]


def yaml_blokker():
    """Blokker i esphome/skjold-fjernkontroll.yaml: navnelista og oppsettkartet (globals), hendelsestypene (event),
    en binary_sensor for hver bryter (faste taster og rutenettet) og valget av tasteoppsett (select).
    Tastene meldes som trykk og slipp til Tastatur i esphome/skjold_ui.h (kort, langt ≥ 0,6 s, dobbelt, gjentak).
    Rutenettbryterne slår opp funksjonen i oppsettkartet for tasteoppsettet som er valgt (tom = ikke i bruk)."""
    hub = {"A": "tca_a", "B": "tca_b", "C": "tca_c", "D": "tca_d"}
    ids = tastenavn()
    navn_ = list(OPPSETT)
    rader = ", ".join("{" + ", ".join(f'"{f}"' for f in kart(o)) + "}" for o in navn_)
    navn = ["# >>> navneliste (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
            "  - id: taster_navn",
            "    type: std::vector<std::string>",
            "    initial_value: '{" + ", ".join(f'"{i}"' for i in ids) + "}'",
            "  # rutenettbryter → funksjon for hvert tasteoppsett (" + ", ".join(navn_) + ")",
            "  - id: oppsett_kart",
            "    type: std::vector<std::vector<std::string>>",
            "    initial_value: '{" + rader + "}'",
            "  - id: oppsett_nr",
            "    type: int",
            "    restore_value: true",
            f"    initial_value: '{navn_.index('rutenett')}'",
            "# <<< navneliste"]
    hend = (["# >>> hendelser (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
             "    event_types:"] + [f"      - {i}" for i in ids] + [f"      - {i}_lang" for i in ids if i in TREG]
            + [f"      - {i}_dobbel" for i in ids if i in DOBBEL] + ["# <<< hendelser"])
    valg = ["# >>> oppsettvalg (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
            "  - platform: template",
            "    id: oppsett_valg",
            "    name: Tasteoppsett",
            "    icon: mdi:view-grid-outline",
            "    optimistic: true",
            "    restore_value: true",
            "    initial_option: ${oppsett}",
            "    options: [ " + ", ".join(navn_) + " ]",
            "    on_value:",
            "      - lambda: 'id(oppsett_nr) = i;'",
            "# <<< oppsettvalg"]
    ut = ["# >>> taster (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
          "  # Hver bryter melder trykk og slipp til tastaturet i skjold_ui.h, som avgjør kort/langt/dobbelt trykk og gjentar."]
    vekk = []
    for i, (bid, nv, x, n, hid) in enumerate(brytere()):
        c, a, p, pn = tca(i)
        if hid == "front":
            k = int(bid[1:])
            navn_ = f"!lambda 'return id(oppsett_kart)[id(oppsett_nr)][{k}];'"
            vekk.append(f'{{{"ABCD".index(c)}, {p}, "", {k}}}')
        else:
            navn_ = f'"{bid}"'
            vekk.append(f'{{{"ABCD".index(c)}, {p}, "{bid}", -1}}')
        ut += [f"  - platform: gpio",
               f"    id: t_{bid}",
               f"    name: \"Tast {nv}\"",
               f"    internal: true",
               f"    pin: {{ tca9555: {hub[c]}, number: {p}, mode: {{ input: true }}, inverted: true }}",
               f"    filters: [ {{ delayed_on: 10ms }}, {{ delayed_off: 15ms }} ]",
               f"    on_press: [ {{ script.execute: {{ id: tast_ned, navn: {navn_} }} }} ]",
               f"    on_release: [ {{ script.execute: {{ id: tast_opp, navn: {navn_} }} }} ]"]
    brikker = sorted({tca(i)[0] for i in range(len(brytere()))})
    les = " ".join(f"case {'ABCD'.index(c)}: nede = !id({hub[c]}).digital_read(b.p); break;" for c in brikker)
    vekking = ["# >>> vekking (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
               "  # Rett etter oppstart: hvorfor den våknet, og hvilken tast som holdes (den sendes som første trykk).",
               "  - id: les_vekketast",
               "    then:",
               "      - lambda: |-",
               "          static const struct { uint8_t c, p; const char *navn; int g; } B[] = {",
               "            " + ", ".join(vekk) + "};",
               "          auto aarsak = esp_sleep_get_wakeup_cause();",
               "          ESP_LOGI(\"vekking\", \"vekket av %s\", aarsak == ESP_SLEEP_WAKEUP_EXT0 ? \"tast (TCA9555 INT)\" :",
               "                   aarsak == ESP_SLEEP_WAKEUP_EXT1 ? \"vibrasjonsbryteren (løftet)\" : \"strøm på / omstart\");",
               "          if (aarsak != ESP_SLEEP_WAKEUP_EXT0) return;",
               "          for (auto &b : B) {",
               "            bool nede = false;",
               "            switch (b.c) { " + les + " }",
               "            if (!nede) continue;",
               "            std::string n = b.g < 0 ? std::string(b.navn) : id(oppsett_kart)[id(oppsett_nr)][b.g];",
               "            if (n.empty()) continue;",
               "            ESP_LOGI(\"vekking\", \"tasten %s holdes: sendes som første trykk\", n.c_str());",
               "            skjold::tastatur.ignorer = n;",
               "            skjold::tastatur.ignorer_til = millis() + 1500;",
               "            return;",
               "          }",
               "# <<< vekking"]
    ut.append("# <<< taster")
    return {"navneliste": "\n".join(navn), "hendelser": "\n".join(hend), "taster": "\n".join(ut), "oppsettvalg": "\n".join(valg),
            "vekking": "\n".join(vekking)}


def oppsett_tabell():
    """Markdown: hvilken rutenettbryter hver funksjon bruker i hvert oppsett."""
    lines = ["| Funksjon | " + " | ".join(OPPSETT_NAVN[o] for o in OPPSETT) + " |", "|---|" + "---|" * len(OPPSETT)]
    for f in FUNKSJONER:
        cel = []
        for o in OPPSETT:
            i = kart(o).index(f) if f in kart(o) else None
            cel.append("–" if i is None else f"`g{i:02d}` (rad {i // len(GRID_DX)}, kolonne {i % len(GRID_DX)})")
        lines.append(f"| `{f}` | " + " | ".join(cel) + " |")
    return "\n".join(lines)


def tabell():
    lines = ["| Tast | Bryter-id | Brikke | Adresse | Pinne |", "|---|---|---|---|---|"]
    for row in koblinger()[1:]:
        bid, navn, c, a, pn, _ = row
        lines.append(f"| {navn} | `{bid}` | {c} | {a} | {pn} |")
    return "\n".join(lines)


def full_yaml(kort):
    """esphome/skjold-fjernkontroll-full.yaml: samme fil som standard (kort), men med talltastene og
    smarthus-raden (30 taster) og 4 × TCA9555."""
    k = kort
    for a, b in [("  name: skjold-fjernkontroll\n", "  name: skjold-fjernkontroll-full\n"),
                 ("  friendly_name: Skjold Fjernkontroll\n", "  friendly_name: Skjold Fjernkontroll Full\n"),
                 ("  ekstra_hub: tca_c ", "  ekstra_hub: tca_d "),
                 ("  - { id: tca_c, i2c_id: bus_a, address: 0x22 }\n",
                  "  - { id: tca_c, i2c_id: bus_a, address: 0x22 }\n  - { id: tca_d, i2c_id: bus_a, address: 0x23 }\n"),
                 ("  ap: { ssid: \"Skjold Fjernkontroll\" }", "  ap: { ssid: \"Skjold Fjernkontroll Full\" }"),
                 ("# Dette er standardvarianten (uten talltastene og smarthus-raden). Full variant med talltaster og smarthus-rad:\n"
                  "# skjold-fjernkontroll-full.yaml, laget av kabinett/fjernkontroll/taster.py fra denne fila.\n", ""),
                 ("14 taster, IR og Wi-Fi", "30 taster, IR og Wi-Fi"),
                 ("3 × TCA9555 på tastekortet (8 faste taster", "4 × TCA9555 på tastekortet (24 faste taster")]:
        assert a in k, a
        k = k.replace(a, b)
    hode = ("# FULL VARIANT (valgfri) – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger\n"
            "# her: endre skjold-fjernkontroll.yaml og kjør python3 taster.py. Med talltastene og smarthus-raden (30 taster,\n"
            "# 4 × TCA9555).\n")
    for kk, v in yaml_blokker().items():
        k = re.sub(rf"# >>> {kk}.*?# <<< {kk}", lambda _m, v=v: v, k, flags=re.S)
    return hode + k


def hovedkort_yaml(kort):
    """esphome/skjold-fjernkontroll-hovedkort.yaml: standardvarianten (kort) på det ferdige hovedkortet
    (hovedkort/kretser.py): ESP32-S3-WROOM-1 i stedet for SuperMini, og vibrator, skjermstrøm og ladestatus
    på egne GPIO-er i stedet for på TCA9555. Tastene og TCA9555-adressene er de samme."""
    k = kort
    for a, b in [
            ("# Dette er standardvarianten (uten talltastene og smarthus-raden). Full variant med talltaster og smarthus-rad:\n"
             "# skjold-fjernkontroll-full.yaml, laget av kabinett/fjernkontroll/taster.py fra denne fila.\n", ""),
            ("ESP32-S3 SuperMini, 2,8″", "hovedkortet (ESP32-S3-WROOM-1-N4R2), 2,8″"),
            ("3 × TCA9555 på tastekortet (8 faste taster + vibrator, skjermstrøm og ladestatus, og 35 brytere",
             "3 × TCA9555 på hovedkortet (8 faste taster og 35 brytere"),
            ("(TCA9555 INT → GPIO2) eller av at du løfter den\n#     (vibrasjonsbryter → GPIO4).",
             "(TCA9555 INT → GPIO7) eller av at du løfter den\n#     (vibrasjonsbryter → GPIO6)."),
            ("# Pinnene er Skjolds eget oppsett for SuperMini (se koblingstabellen i LES_MEG.md). IKKE TESTET PÅ MASKINVARE.",
             "# Pinnene følger hovedkortet (kabinett/fjernkontroll/hovedkort/kretser.py, pinnetabellen i LES_MEG.md). IKKE TESTET PÅ MASKINVARE."),
            ("  ekstra_hub: tca_c                  # brikken med vibrator, skjermstrøm og ladestatus (full variant: tca_d)\n", ""),
            ("(AO3401 via TCA9555)", "(AO3401, GPIO15)"),
            ("  board: esp32-s3-devkitc-1          # ESP32-S3 SuperMini (ESP32-S3FH4R2: 4 MB flash, 2 MB PSRAM)",
             "  board: esp32-s3-devkitc-1          # ESP32-S3-WROOM-1-N4R2 (4 MB flash, 2 MB PSRAM)"),
            ("  - id: bus_a                        # tastekortet (2 × TCA9555, full variant 3)\n    sda: GPIO5\n    scl: GPIO6",
             "  - id: bus_a                        # 3 × TCA9555 (4,7 kΩ til 3V3)\n    sda: GPIO8\n    scl: GPIO9"),
            ("    sda: GPIO8\n    scl: GPIO3                       # strappe-pinne, men bare for JTAG-valg (eFuse) – trygg med pull-up",
             "    sda: GPIO18\n    scl: GPIO38                      # pull-up til 3V3_SW: bussen er død når skjermstrømmen er av"),
            ("  clk_pin: GPIO9\n  mosi_pin: GPIO10", "  clk_pin: GPIO12\n  mosi_pin: GPIO11"),
            ("    id: baklys_pwm\n    pin: GPIO13", "    id: baklys_pwm\n    pin: GPIO21                      # → AO3400 (Q3) på LED-katoden"),
            ("    pin: { tca9555: $ekstra_hub, number: 13, mode: { output: true }, inverted: true }   # lav = på",
             "    pin: { number: GPIO15, inverted: true }   # AO3401 (Q2), lav = på (100 kΩ holder den av i søvn)"),
            ("    pin: { tca9555: $ekstra_hub, number: 12, mode: { output: true } }",
             "    pin: GPIO16                      # → 1 kΩ → AO3400 (Q5) → motoren"),
            ("    dc_pin: GPIO11\n    reset_pin: GPIO12                # deles med berøringens RST",
             "    dc_pin: GPIO13\n    reset_pin: GPIO14"),
            ("    i2c_id: bus_b\n    interrupt_pin: GPIO7", "    i2c_id: bus_b\n    interrupt_pin: GPIO10\n    reset_pin: GPIO2"),
            ("  pin: GPIO43                        # → 1 kΩ → AO3400 → 3 × IR-diode 940 nm (hver med 10 Ω fra batteriet)",
             "  pin: GPIO4                         # → 100 Ω → AO3400 (Q4) → 3 × IR-diode 940 nm på IR-kortet"),
            ("  pin: { number: GPIO44, inverted: true }   # VS1838B (aktiv lav)",
             "  pin: { number: GPIO5, inverted: true }    # VS1838B (aktiv lav)"),
            ("  wakeup_pin: { number: GPIO2, inverted: true, mode: { input: true } }   # TCA9555 INT (felles, 10 kΩ til 3V3)",
             "  wakeup_pin: { number: GPIO7, inverted: true, mode: { input: true } }   # TCA9555 INT (felles, 10 kΩ til 3V3)"),
            ("    pins: [ { number: GPIO4, allow_other_uses: true } ]   # vibrasjonsbryter SW-18010P mellom 3V3 og GPIO4 (1 MΩ ned)",
             "    pins: [ { number: GPIO6, allow_other_uses: true } ]   # vibrasjonsbryter SW-18010P mellom 3V3 og GPIO6 (1 MΩ ned)"),
            ("    pin: GPIO1                       # VBAT via 2 × 220 kΩ", "    pin: GPIO1                       # VBAT via 2 × 1 MΩ og 100 nF"),
            ("    pin: { tca9555: $ekstra_hub, number: 14, mode: { input: true }, inverted: true }   # TP4056 CHRG (lav = lader)",
             "    pin: { number: GPIO17, inverted: true }   # TP4056 CHRG (åpen drain, 10 kΩ til 3V3; lav = lader)"),
            ("    pin: { number: GPIO4, mode: { input: true }, allow_other_uses: true }",
             "    pin: { number: GPIO6, mode: { input: true }, allow_other_uses: true }"),
            ("    pin: { tca9555: $ekstra_hub, number: 15, mode: { input: true } }   # pogo + via 68 kΩ / 100 kΩ (høy = i dokken)",
             "    pin: { number: GPIO40, mode: { input: true } }   # pogo + (POGO) via R26 68 kΩ / R27 100 kΩ (høy = i dokken)")]:
        assert k.count(a) == 1, a
        k = k.replace(a, b)
    assert "ekstra_hub" not in k and "GPIO43" not in k and "GPIO3\n" not in k
    hode = ("# HOVEDKORT – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger her: endre\n"
            "# skjold-fjernkontroll.yaml og kjør python3 taster.py. Samme fjernkontroll (samme navn, taster og hendelser) på det\n"
            "# ferdige kretskortet i kabinett/fjernkontroll/hovedkort/ i stedet for den håndkoblede SuperMini-versjonen.\n")
    return hode + k


def tastekort_a():
    """Tastekort A (bare tasteoppsett A, én TCA9555 0x20): [(funksjon, x, n, pinne)] i pinnerekkefølge.
    Pinne 0–13 = tastene, 14 = skjermstrøm (P1_6, utgang), 15 = dokken (P1_7, inngang)."""
    bruk("kort")
    b = brytere()
    fast = [(bid, x, n) for bid, nv, x, n, hid in b if hid != "front"]
    k = kart("rutenett")
    rute = {k[int(bid[1:])]: (x, n) for bid, nv, x, n, hid in b if hid == "front" and k[int(bid[1:])]}
    rek = ["tilbake", "avslutt", "spill_pause", "demp", "vol_opp", "vol_ned"]
    ut = [(f, x, n) for f, x, n in fast] + [(f,) + rute[f] for f in rek]
    assert len(ut) == 14
    return [(f, x, n, i) for i, (f, x, n) in enumerate(ut)]


def tastekort_a_yaml(kort):
    """esphome/skjold-fjernkontroll-tastekort-a.yaml: håndkoblet med tastekort A (bare oppsett A, én TCA9555).
    Skjermstrøm på P1_6 og dokken på P1_7; ingen vibrasjonsmotor og ingen ladestatus (CHRG) i denne utgaven."""
    k = kort
    for a, b in [
            ("# Dette er standardvarianten (uten talltastene og smarthus-raden). Full variant med talltaster og smarthus-rad:\n"
             "# skjold-fjernkontroll-full.yaml, laget av kabinett/fjernkontroll/taster.py fra denne fila.\n", ""),
            ("3 × TCA9555 på tastekortet (8 faste taster + vibrator, skjermstrøm og ladestatus, og 35 brytere",
             "tastekort A med 1 × TCA9555 (14 taster i oppsett A, skjermstrøm og dokken; ikke vibrator eller ladestatus,"),
            ("  ekstra_hub: tca_c                  # brikken med vibrator, skjermstrøm og ladestatus (full variant: tca_d)\n",
             "  ekstra_hub: tca_a                  # tastekort A: én brikke (skjermstrøm P1_6, dokken P1_7)\n"),
            ("  - { id: tca_b, i2c_id: bus_a, address: 0x21 }\n  - { id: tca_c, i2c_id: bus_a, address: 0x22 }\n", ""),
            ("    pin: { tca9555: $ekstra_hub, number: 13, mode: { output: true }, inverted: true }   # lav = på",
             "    pin: { tca9555: $ekstra_hub, number: 14, mode: { output: true }, inverted: true }   # P1_6, lav = på"),
            ("  - platform: gpio\n    id: vibrator\n    pin: { tca9555: $ekstra_hub, number: 12, mode: { output: true } }",
             "  - platform: template                # tastekort A: ingen vibrasjonsmotor\n    id: vibrator\n    type: binary\n    write_action: []"),
            ("  - platform: gpio\n    id: lader\n    name: Lader\n    pin: { tca9555: $ekstra_hub, number: 14, mode: { input: true }, inverted: true }   # TP4056 CHRG (lav = lader)",
             "  - platform: template                # tastekort A: CHRG er ikke koblet\n    id: lader\n    name: Lader\n    lambda: 'return false;'")]:
        assert k.count(a) == 1, a
        k = k.replace(a, b)
    taster_ = ["# >>> taster (laget av kabinett/fjernkontroll/taster.py – ikke rediger mellom merkene)",
               "  # Tastekort A: én TCA9555 (0x20), pinne 0–13 = tastene i oppsett A."]
    vekk = []
    for f, x, n, p in tastekort_a():
        taster_ += [f"  - platform: gpio", f"    id: t_{f}", f"    name: \"Tast {f}\"", f"    internal: true",
                    f"    pin: {{ tca9555: tca_a, number: {p}, mode: {{ input: true }}, inverted: true }}",
                    f"    filters: [ {{ delayed_on: 10ms }}, {{ delayed_off: 15ms }} ]",
                    f"    on_press: [ {{ script.execute: {{ id: tast_ned, navn: \"{f}\" }} }} ]",
                    f"    on_release: [ {{ script.execute: {{ id: tast_opp, navn: \"{f}\" }} }} ]"]
        vekk.append(f'{{0, {p}, "{f}", -1}}')
    taster_.append("# <<< taster")
    k = re.sub(r"# >>> taster.*?# <<< taster", lambda _m: "\n".join(taster_), k, flags=re.S)
    vb = yaml_blokker()["vekking"].split("\n")
    vb = [("            " + ", ".join(vekk) + "};") if l.startswith("            {") else l for l in vb]
    vb = [("            switch (b.c) { case 0: nede = !id(tca_a).digital_read(b.p); break; }") if "switch (b.c)" in l else l for l in vb]
    k = re.sub(r"# >>> vekking.*?# <<< vekking", lambda _m: "\n".join(vb), k, flags=re.S)
    assert "tca_b" not in k and "tca_c" not in k
    hode = ("# TASTEKORT A – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger her.\n"
            "# Håndkoblet utgave med tastekort A (kabinett/fjernkontroll/tastekort_a/): bare tasteoppsett A, én TCA9555.\n")
    return hode + k


def enkel_yaml(tastekort_a):
    """esphome/skjold-fjernkontroll-enkel.yaml: Skjold Fjernkontroll Enkel (enkel/): Seeed XIAO ESP32S3 og MCP23017 på
    et enkelt bærekort, laget fra tastekort A-fila (samme 14 taster i oppsett A, samme pinner på utvideren)."""
    k = tastekort_a
    for a, b in [
            ("# TASTEKORT A – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger her.\n"
             "# Håndkoblet utgave med tastekort A (kabinett/fjernkontroll/tastekort_a/): bare tasteoppsett A, én TCA9555.\n",
             "# ENKEL UTGAVE – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger her.\n"
             "# Skjold Fjernkontroll Enkel (kabinett/fjernkontroll/enkel/): Seeed XIAO ESP32S3 + MCP23017 på et bærekort, oppsett A.\n"
             "# XIAO-pinner: D0 GPIO1 VBAT · D1 GPIO2 INT (MCP23017, vekking) · D2 GPIO3 DC · D3 GPIO4 RES (+ berøring RST) ·\n"
             "# D4 GPIO5 SDA · D5 GPIO6 SCL · D6 GPIO43 IR TX · D7 GPIO44 IR RX · D8 GPIO7 SCK · D9 GPIO8 baklys · D10 GPIO9 MOSI.\n"
             "# MCP23017 (0x20): GPA0–7 + GPB0–5 = tastene, GPB6 = skjermstrøm (AO3401), GPB7 = dokken.\n"),
            ("  ekstra_hub: tca_a                  # tastekort A: én brikke (skjermstrøm P1_6, dokken P1_7)\n",
             "  ekstra_hub: tca_a                  # MCP23017 (skjermstrøm GPB6, dokken GPB7)\n"),
            ("  board: esp32-s3-devkitc-1          # ESP32-S3 SuperMini (ESP32-S3FH4R2: 4 MB flash, 2 MB PSRAM)\n  variant: esp32s3\n  flash_size: 4MB",
             "  board: esp32-s3-devkitc-1          # Seeed XIAO ESP32S3 (8 MB flash, 8 MB PSRAM)\n  variant: esp32s3\n  flash_size: 8MB"),
            ("psram:\n  mode: quad\n", "psram:\n  mode: octal\n"),
            ("logger:\n  level: INFO\n", "logger:\n  level: INFO\n  hardware_uart: USB_SERIAL_JTAG   # GPIO43/44 brukes til IR\n"),
            ("  - id: bus_a                        # tastekortet (2 × TCA9555, full variant 3)",
             "  - id: bus_a                        # MCP23017 (0x20) og berøringen (0x38), 4,7 kΩ til 3V3"),
            ("  - id: bus_b                        # berøring (FT6336U, 0x38) – egen buss, så skjermen kan slås helt av i søvn\n"
             "    sda: GPIO8\n    scl: GPIO3                       # strappe-pinne, men bare for JTAG-valg (eFuse) – trygg med pull-up\n"
             "    frequency: 400kHz\n    scan: false\n", ""),
            ("tca9555:\n  - { id: tca_a, i2c_id: bus_a, address: 0x20 }\n",
             "mcp23017:\n  - id: tca_a\n    i2c_id: bus_a\n    address: 0x20\n    open_drain_interrupt: true   # INTA (åpen drain, 10 kΩ til 3V3) → GPIO2\n"
             "    # INTA vekker ESP-en (deep_sleep wakeup_pin); mens den er våken leses utvideren hver løkke\n"),
            ("  clk_pin: GPIO9\n  mosi_pin: GPIO10", "  clk_pin: GPIO7\n  mosi_pin: GPIO9"),
            ("    id: baklys_pwm\n    pin: GPIO13", "    id: baklys_pwm\n    pin: GPIO8                       # → 100 Ω → AO3400 (Q2) på LED-katoden"),
            ("    pin: { tca9555: $ekstra_hub, number: 14, mode: { output: true }, inverted: true }   # P1_6, lav = på",
             "    pin: { mcp23xxx: $ekstra_hub, number: 14, mode: { output: true }, inverted: true }   # GPB6 → AO3401 (Q1), lav = på"),
            ("    dc_pin: GPIO11\n    reset_pin: GPIO12                # deles med berøringens RST",
             "    dc_pin: GPIO3\n    reset_pin: GPIO4                 # deles med berøringens RST"),
            ("    i2c_id: bus_b\n    interrupt_pin: GPIO7", "    i2c_id: bus_a                    # INT er ikke koblet: berøringen leses jevnlig"),
            ("  wakeup_pin: { number: GPIO2, inverted: true, mode: { input: true } }   # TCA9555 INT (felles, 10 kΩ til 3V3)",
             "  wakeup_pin: { number: GPIO2, inverted: true, mode: { input: true } }   # MCP23017 INTA"),
            ("  esp32_ext1_wakeup:\n    pins: [ { number: GPIO4, allow_other_uses: true } ]   # vibrasjonsbryter SW-18010P mellom 3V3 og GPIO4 (1 MΩ ned)\n    mode: ANY_HIGH\n", ""),
            ("  - platform: gpio\n    id: loftet\n    internal: true\n    pin: { number: GPIO4, mode: { input: true }, allow_other_uses: true }\n    on_press:\n      - script.execute: sovn_teller\n", ""),
            ("    pin: { tca9555: $ekstra_hub, number: 15, mode: { input: true } }   # pogo + via 68 kΩ / 100 kΩ (høy = i dokken)",
             "    pin: { mcp23xxx: $ekstra_hub, number: 15, mode: { input: true }, interrupt: CHANGE }   # GPB7: POGO+ via 68 kΩ / 100 kΩ"),
            ("    pin: GPIO1                       # VBAT via 2 × 220 kΩ", "    pin: GPIO1                       # VBAT via 1 MΩ / 1 MΩ og 100 nF (D0)"),
            ("  pin: GPIO43                        # → 1 kΩ → AO3400 → 3 × IR-diode 940 nm (hver med 10 Ω fra batteriet)",
             "  pin: GPIO43                        # → 100 Ω → AO3400 (Q3) → 2 × IR-diode 940 nm i serie, 6,8 Ω fra batteriet"),
            ("      - output.turn_off: strom_skjerm      # skjerm, berøring og IR-mottaker uten strøm\n",
             "      - lambda: |-                       # berøringen har strøm fra 3V3 hele tiden (deler I²C med MCP23017): dvalemodus\n"
             "          const uint8_t dvale[2] = {0xA5, 0x03};   // FT6336U PWR_MODE = hibernate (ca. 25 µA); vekkes av RST ved oppstart\n"
             "          id(bus_a)->write(0x38, dvale, 2);\n"
             "      - output.turn_off: strom_skjerm      # skjerm og IR-mottaker uten strøm\n"),
            ("  name: skjold-fjernkontroll\n", "  name: skjold-fjernkontroll\n")]:
        assert k.count(a) == 1, a
        k = k.replace(a, b)
    k = k.replace("mode: { input: true }, inverted: true }", "mode: { input: true, pullup: true }, inverted: true, interrupt: CHANGE }")
    k = k.replace("{ tca9555: tca_a,", "{ mcp23xxx: tca_a,")
    # maskinvarebeskrivelsen i toppen av fila
    import re
    i = k.index("# Maskinvare (se kabinett/fjernkontroll/LES_MEG.md)")
    j = k.index("#\n", i)
    k = k[:i] + ("# Maskinvare (se «Enkel utgave» i kabinett/fjernkontroll/LES_MEG.md): Seeed XIAO ESP32S3 (lader LiPo-en selv), 2,8″ IPS\n"
                 "# ST7789 + FT6336U berøring (naken FPC-modul HP28030), MCP23017 med 14 taster (4 × 4 mm), 2 × IR-diode 940 nm, VS1838B,\n"
                 "# LiPo 603450 på XIAO-ens BAT-puter og pogo-dokk (5 V via Schottky til XIAO-ens 5V). Ingen vibrasjonsbryter.\n") + k[j:]
    k = re.sub(r"#   · Tasteblokken under D-paden har flere oppsett.*?\n(#     .*?\n)*", "#   · Tastene sitter fast i oppsett A (14 taster), rett på bærekortet.\n", k, count=1)
    k = re.sub(r"#   · Dyp søvn etter \$\{sovn_etter\} uten bruk\..*?\n(#     .*?\n)*",
               "#   · Dyp søvn etter ${sovn_etter} uten bruk. Vekkes av en tast (MCP23017 INTA → GPIO2).\n", k, count=1)
    k = k.replace("# Pinnene er Skjolds eget oppsett for SuperMini (se koblingstabellen i LES_MEG.md).",
                  "# Pinnene er XIAO-ens D0–D10 (se enkel/pinner.csv).")
    assert "tca9555" not in k and "GPIO10" not in k and "GPIO13" not in k, [l for l in k.split("\n") if "tca9555" in l or "GPIO10" in l][:3]
    return k


def hullkort_yaml(enkel):
    """esphome/skjold-fjernkontroll-hullkort.yaml: hullkort-utgaven (hullkort/): samme XIAO-pinner og MCP23017-pinner som
    den enkle utgaven, men uten skjermbryter (AO3401): skjermen står på 3V3 og går i dvale (SLPIN) av seg selv før dyp
    søvn, og GPB6 gir strøm rett til IR-mottakeren (høy = på). Tastene bruker MCP-ens interne pull-ups."""
    k = enkel
    for a, b in [
            ("# ENKEL UTGAVE – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger her.\n"
             "# Skjold Fjernkontroll Enkel (kabinett/fjernkontroll/enkel/): Seeed XIAO ESP32S3 + MCP23017 på et bærekort, oppsett A.\n",
             "# HULLKORT-UTGAVE – laget av kabinett/fjernkontroll/taster.py fra skjold-fjernkontroll.yaml. Ikke rediger her.\n"
             "# Skjold Fjernkontroll, hullkort (kabinett/fjernkontroll/hullkort/): Seeed XIAO ESP32S3, MCP23017-modul (CJMCU-2317)\n"
             "# og 14 × 6 × 6 mm THT-brytere på hullkort, uten kretskort. Oppsett A.\n"),
            ("# MCP23017 (0x20): GPA0–7 + GPB0–5 = tastene, GPB6 = skjermstrøm (AO3401), GPB7 = dokken.\n",
             "# MCP23017-modulen (0x20): GPA0–7 + GPB0–5 = tastene (interne pull-ups), GPB6 = strøm til IR-mottakeren, GPB7 = dokken.\n"),
            ("# Maskinvare (se «Enkel utgave» i kabinett/fjernkontroll/LES_MEG.md): Seeed XIAO ESP32S3 (lader LiPo-en selv), 2,8″ IPS\n"
             "# ST7789 + FT6336U berøring (naken FPC-modul HP28030), MCP23017 med 14 taster (4 × 4 mm), 2 × IR-diode 940 nm, VS1838B,\n",
             "# Maskinvare (se «Hullkort-utgave» i kabinett/fjernkontroll/LES_MEG.md): Seeed XIAO ESP32S3 (lader LiPo-en selv), 2,8″ IPS\n"
             "# ST7789 + FT6336U berøring (HP28030 på FPC-adaptere til 2,54 mm), MCP23017-modul med 14 taster (6 × 6 mm), 2 × IR-diode, VS1838B,\n"),
            ("# Pinnene er XIAO-ens D0–D10 (se enkel/pinner.csv).", "# Pinnene er XIAO-ens D0–D10, som i den enkle utgaven (se hullkort/koblinger.csv)."),
            ("        - output.turn_on: strom_skjerm         # 3V3 til skjerm og IR-mottaker (AO3401 via TCA9555)\n",
             "        - output.turn_on: strom_skjerm         # strøm til IR-mottakeren (MCP GPB6)\n"),
            ("  - id: bus_a                        # MCP23017 (0x20) og berøringen (0x38), 4,7 kΩ til 3V3",
             "  - id: bus_a                        # MCP23017-modulen (0x20) og berøringen (0x38), 10 kΩ pull-ups på modulen"),
            ("    pin: { mcp23xxx: $ekstra_hub, number: 14, mode: { output: true }, inverted: true }   # GPB6 → AO3401 (Q1), lav = på",
             "    pin: { mcp23xxx: $ekstra_hub, number: 14, mode: { output: true } }   # GPB6 → VS1838B VCC (høy = på; skjermen står på 3V3)"),
            ("      - output.turn_off: strom_skjerm      # skjerm og IR-mottaker uten strøm\n",
             "      - output.turn_off: strom_skjerm      # IR-mottakeren uten strøm (skjermen går i dvale, SLPIN, når ESP-en sover)\n")]:
        assert k.count(a) == 1, a
        k = k.replace(a, b)
    assert "pullup: true" in k
    return k


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    deler, yml = [], os.path.join(here, "..", "..", "esphome", "skjold-fjernkontroll.yaml")
    for v, antall in (("kort", 8 + len(GRID)), ("full", 24 + len(GRID))):
        bruk(v)
        assert len(brytere()) == antall, (v, len(brytere()))
        feil = sjekk_steg()
        if feil:
            raise SystemExit(f"{v}: for lite materiale mellom hullene: {feil}")
        deler.append(scad())
        mappe = os.path.join(here, "tastekort" if v == "kort" else "tastekort_full")
        os.makedirs(mappe, exist_ok=True)
        for fn, rows in (("plassering.csv", plassering()), ("koblinger.csv", koblinger())):
            with open(os.path.join(mappe, fn), "w", newline="") as f:
                csv.writer(f).writerows(rows)
    with open(os.path.join(here, "taster.scad"), "w") as f:
        f.write("// Laget av taster.py – ikke rediger for hånd.\n"
                "// hette: [id, form, x, n (fra nesen), bredde, høyde, ikon, farge] · bryter: [id, x, n]\n"
                f"DPAD_R = {DPAD_R};\nVIPPE_D = {VIPPE_D};\nPCB_N0 = {PCB_N0};\n" + "".join(deler) + front_scad())
    # standard (kort) er hovedfila; full lages fra den
    bruk("kort")
    s = open(yml).read()
    ny = s
    for k, v in yaml_blokker().items():
        ny = re.sub(rf"# >>> {k}.*?# <<< {k}", lambda _m, v=v: v, ny, flags=re.S)
    if ny != s:
        open(yml, "w").write(ny)
    bruk("full")
    open(yml.replace(".yaml", "-full.yaml"), "w").write(full_yaml(ny))
    bruk("kort")
    open(yml.replace(".yaml", "-hovedkort.yaml"), "w").write(hovedkort_yaml(ny))
    ta = tastekort_a_yaml(ny)
    open(yml.replace(".yaml", "-tastekort-a.yaml"), "w").write(ta)
    en = enkel_yaml(ta)
    open(yml.replace(".yaml", "-enkel.yaml"), "w").write(en)
    open(yml.replace(".yaml", "-hullkort.yaml"), "w").write(hullkort_yaml(en))
    bruk("kort")
    import sys
    if len(sys.argv) > 1:
        bruk(sys.argv[1])
    print(tabell())
    print()
    print(oppsett_tabell())


if __name__ == "__main__":
    main()
