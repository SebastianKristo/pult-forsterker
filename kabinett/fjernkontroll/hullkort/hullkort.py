"""Skjold Fjernkontroll – hullkort-utgaven (uten kretskort): all geometri og alle koblinger på ett sted.

Kilden for hullkort_data.scad (kabinettet), hullkort.json (3D-siden), tegningene og sjekken. Koordinater som ellers i
prosjektet: x tvers (0 … 55), n fra nesen (0 … 202,5), z fra undersiden. På hullkortet: kolonne k (x = CX + k · 2,54),
rad j (n = R0 + j · 2,54); kobberstripene går på tvers (langs x), sett fra kobbersiden (undersiden).

Bryterne er 6 × 6 × 4,3 mm THT med beina i et 2 × 3-rutenett (5,08 × 7,62 mm): senteret står på en kolonne og midt
mellom to rader. Beina to og to (de 6,5 mm fra hverandre, langs n) er koblet inni bryteren, så venstre bein (GND) og
høyre bein (tasten) er hver sin side. Kuttene i stripene lages av koden: der to nabohull på samme stripe har ulike nett."""
import math
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import taster  # noqa: E402

taster.bruk("kort")
W, L = taster.W, taster.L          # 55 × 202,5
CX = W / 2
P = 2.54

# ---------- høyder (z) ----------
TB = 1.6                           # gulvet
Z_KORT = 7.4                       # hullkortets underside
KORT_T = 1.6                       # hullkortet (FR4/pertinax 1,6 mm)
SW_H = 4.3                         # 6 × 6 × 4,3 mm THT-bryter (fra kortet til toppen av knappen)
SW_KROPP = 3.5                     # selve bryterhuset
BEIN = 0.8                         # beina klippes til 0,8 mm under kortet (med loddet)
TAPE = 0.2                         # dobbeltsidig tape under modulene
H = 13.5 + (Z_KORT + KORT_T + SW_H + 0.1 - 10.8)   # samme hetter og topp som de andre, bare høyere (16,1 mm)


# ---------- bryterne: snappet til 2,54 mm ----------
def _snap(r0):
    ut = []
    for f, x, n, p in taster.tastekort_a():
        k = round((x - CX) / P)
        j = round((n - r0) / P - 0.5)
        sx, sn = CX + k * P, r0 + (j + 0.5) * P
        ut.append((f, x, n, p, k, j, sx, sn, math.hypot(sx - x, sn - n)))
    return ut


def _beste_r0():
    """Radenes origo (0 … 2,54) som gir minst største avvik; kolonnene står symmetrisk om midten (k = 0 i x = 27,5)."""
    return min((max(s[8] for s in _snap(r / 100)), r / 100) for r in range(254))[1]


R0 = _beste_r0()
BRYTERE = _snap(R0)       # (funksjon, x, n, mcp-pinne, k, j, x_snappet, n_snappet, avvik)


def hull_xy(k, j):
    return CX + k * P, R0 + j * P


def bein(b):
    """De fire beina: [(k, j, nett)]; venstre side GND, høyre side tasten (diagonalt motsatte bein er alltid ulike)."""
    f, k, j = b[0], b[4], b[5]
    return [(k - 1, j - 1, "GND"), (k - 1, j + 2, "GND"), (k + 1, j - 1, "K_" + f.upper()), (k + 1, j + 2, "K_" + f.upper())]


# ---------- hullkortet ----------
K_MIN, K_MAX = -9, 9                                   # 19 kolonner: x 4,64 … 50,36 (kantene midt mellom hullene)
J_MIN = math.ceil((77.6 + P / 2 - R0) / P)            # første rad: kanten ≥ n 77,6 (2 mm bak skjermmodulen)
J_MAX = math.floor((198.6 - P / 2 - R0) / P)          # siste rad: kanten ≤ n 198,6
KANT_X0, KANT_X1 = CX + (K_MIN - 0.5) * P, CX + (K_MAX + 0.5) * P
KANT_N0, KANT_N1 = R0 + (J_MIN - 0.5) * P, R0 + (J_MAX + 0.5) * P
HJORNE = 3                                             # 3 × 3 hull kuttes bort i hjørnene ved halen (skruetårnene)
MIDTSKRUE = (48.0, 95.0)                              # Ø2,4 mm hull for midtskruen (bores mellom hullene)


def omriss():
    """Omrisset (x, n) med hjørnene ved halen kuttet for skruetårnene."""
    xh0, xh1 = KANT_X0 + HJORNE * P, KANT_X1 - HJORNE * P
    nh = KANT_N1 - HJORNE * P
    return [(KANT_X0, KANT_N0), (KANT_X1, KANT_N0), (KANT_X1, nh), (xh1, nh), (xh1, KANT_N1), (xh0, KANT_N1), (xh0, nh), (KANT_X0, nh)]


def paa_kortet(k, j):
    if not (K_MIN <= k <= K_MAX and J_MIN <= j <= J_MAX):
        return False
    x, n = hull_xy(k, j)
    xh0, xh1, nh = KANT_X0 + HJORNE * P, KANT_X1 - HJORNE * P, KANT_N1 - HJORNE * P
    if n > nh and (x < xh0 or x > xh1):
        return False
    return math.hypot(x - MIDTSKRUE[0], n - MIDTSKRUE[1]) > 1.2 + 0.5


# ---------- delene på gulvet (under hullkortet) ----------
# [ref, navn, x0, x1, n0, n1, z0, z1]; flere bokser per del (kort, brikke, kontakt). Mål merket «sjekk» i LES_MEG.
XIAO_N0 = 178.4
GULV = [
    ("U1", "XIAO ESP32S3 (kort)", CX - 8.75, CX + 8.75, XIAO_N0, XIAO_N0 + 21.0, TB + 0.5, TB + 1.5),
    ("U1", "XIAO ESP32S3 (skjerm)", CX - 7.5, CX + 7.5, XIAO_N0 + 2.5, XIAO_N0 + 14.0, TB + 1.5, TB + 4.0),
    ("USBC", "XIAO USB-C", CX - 4.5, CX + 4.5, XIAO_N0 + 15.0, XIAO_N0 + 22.0, TB + 1.5, TB + 4.7),
    ("U2", "MCP23017-modul (kort)", 8.75, 29.75, 131.0, 157.0, TB + TAPE, TB + TAPE + 1.6),
    ("U2", "MCP23017 (SOIC-28)", 19.25 - 5.15, 19.25 + 5.15, 135.05, 152.95, TB + TAPE + 1.6, TB + TAPE + 1.6 + 2.65),
    ("A1", "FPC 18p-adapter (kort)", 15.3, 37.3, 106.0, 124.0, TB + TAPE, TB + TAPE + 1.0),
    ("A1", "FPC 18p-kontakt", 26.31 - 6.7, 26.31 + 6.7, 106.0, 111.4, TB + TAPE + 1.0, TB + TAPE + 3.0),
    ("A2", "FPC 6p-adapter (kort)", 29.5, 42.5, 91.0, 105.0, TB + TAPE, TB + TAPE + 1.0),
    ("A2", "FPC 6p-kontakt", 35.5 - 3.7, 35.5 + 3.7, 91.0, 96.4, TB + TAPE + 1.0, TB + TAPE + 3.0),
]
USB_X = CX
USB_Z = TB + 1.5 + 1.6             # USB-C-kontaktens senter (4,7)
FPC_Z = TB + TAPE + 2.0            # der flatkablene går inn i adapterne
# stolper fra bunnen under hullkortet og pinner fra toppen (klemmer kortet), utenfor delene, beina og ledningene
STOLPER = [(6.75, 100.0), (50.0, 125.0), (10.0, 178.0), (W - 4.2, 184.0)]
PINNER = [(6.75, 165.0), (48.25, 165.0)]
# ledningsbunter på gulvet (x, n, bredde): IR-kortet langs venstre side, batteriet langs høyre side til XIAO-en
BUNTER = {
    "IR": [(4.0, 12.0), (4.0, 184.0), (CX - 10.0, 184.0)],
    "batteri": [(31.5, 66.0), (43.75, 66.0), (43.75, 100.0), (45.5, 102.0), (45.5, 176.0), (CX + 9.6, 182.0)],
}

# ---------- nettene og koblingene ----------
# XIAO-putene (som i den enkle utgaven) og MCP23017-modulens pinner (CJMCU-2317: VCC, GND, SCL, SDA, RST, INTA, INTB,
# A0–A2, GPA0–7, GPB0–7; pinnene er merket på modulen, rekkefølgen varierer – derfor kobles alt etter navn)
XIAO = {"D0": "VBAT_ADC", "D1": "INT", "D2": "LCD_DC", "D3": "LCD_RES", "D4": "SDA", "D5": "SCL", "D6": "IR_TX",
        "D7": "IR_RX", "D8": "LCD_SCK", "D9": "LCD_BL", "D10": "LCD_MOSI", "3V3": "3V3", "GND": "GND", "5V": "VBUS",
        "BAT+": "VBAT", "BAT-": "GND"}
GPIO = {"D0": 1, "D1": 2, "D2": 3, "D3": 4, "D4": 5, "D5": 6, "D6": 43, "D7": 44, "D8": 7, "D9": 8, "D10": 9}


def mcp_pinne(p):
    return f"GPA{p}" if p < 8 else f"GPB{p - 8}"


MCP = {"VCC": "3V3", "GND": "GND", "SDA": "SDA", "SCL": "SCL", "INTA": "INT", "GPB6": "IR_STROM", "GPB7": "DOKK"}
for b in BRYTERE:
    MCP[mcp_pinne(b[3])] = "K_" + b[0].upper()
# 18-pinners skjermadapter (pinne = FPC-pinnen; ANTATT rekkefølge som på hovedkortet – sjekk)
A1 = {"1": "GND", "2": "LCD_RES", "3": "LCD_SCK", "4": "LCD_DC", "5": "GND", "6": "LCD_MOSI", "8": "GND", "9": "3V3",
      "10": "3V3", "11": "LED_A", "12": "LED_K", "13": "LED_K", "14": "LED_K", "15": "LED_K", "16": "GND", "18": "GND"}
A1_FUNK = {"1": "GND", "2": "RESET", "3": "SCK", "4": "D/C", "5": "CS", "6": "MOSI", "7": "MISO (ikke brukt)", "8": "GND",
           "9": "VDD", "10": "VDD", "11": "LED-A", "12": "LED-K1", "13": "LED-K2", "14": "LED-K3", "15": "LED-K4",
           "16": "GND", "17": "NC", "18": "GND"}
A2 = {"1": "3V3", "2": "GND", "3": "SDA", "4": "SCL", "6": "LCD_RES"}    # berøring: VDD, GND, SDA, SCL, INT (ikke brukt), RST
A2_FUNK = {"1": "VDD", "2": "GND", "3": "SDA", "4": "SCL", "5": "INT (ikke brukt)", "6": "RST"}

# småkomponentene loddes fritt på pinnene der de hører hjemme (krympestrømpe over), ikke på hullkortet
SMADELER = [
    # (ref, verdi, nett 1, nett 2, hvor, hvordan)
    ("R3", "10 kΩ", "3V3", "INT", "MCP-modulen", "mellom VCC og INTA (pull-up for vekkelinja)"),
    ("R16", "1 MΩ", "3V3", "LCD_RES", "6p-adapteren", "mellom pinne 1 (VDD) og 6 (RST): holder RST høy i dyp søvn"),
    ("R8", "10 Ω", "3V3", "LED_A", "18p-adapteren", "mellom pinne 10 (VDD) og 11 (LED-A): baklysets strøm"),
    ("Q2", "AO3400A", "BL_G / GND / LED_K", "", "18p-adapteren", "på en SOT-23-til-DIP-adapter: G = BL_G, S = GND, D = LED_K (pinne 12–15)"),
    ("R6", "100 Ω", "LCD_BL", "BL_G", "Q2-adapteren", "fra ledningen fra D9 til G"),
    ("R7", "100 kΩ", "BL_G", "GND", "Q2-adapteren", "mellom G og S (holder baklyset av ved oppstart)"),
    ("R9", "1 MΩ", "VBAT", "VBAT_ADC", "XIAO-en", "fra BAT+-ledningen til D0"),
    ("R10", "1 MΩ", "VBAT_ADC", "GND", "XIAO-en", "fra D0 til GND-puten"),
    ("C3", "100 nF", "VBAT_ADC", "GND", "XIAO-en", "fra D0 til GND-puten (ved siden av R10)"),
    ("D1", "1N5819", "POGO", "VBUS", "XIAO-en", "anode til POGO+-ledningen, katode (stripen) til 5V-puten"),
    ("R11", "68 kΩ", "POGO", "DOKK", "MCP-modulen", "fra POGO+-ledningen til GPB7"),
    ("R12", "100 kΩ", "DOKK", "GND", "MCP-modulen", "fra GPB7 til GND"),
]
IR_KORT = [
    ("Q3", "AO3400A", "på SOT-23-til-DIP-adapter: G = IR_G, S = GND, D = IR_K"),
    ("R13", "100 Ω", "IR_TX → G"), ("R14", "100 kΩ", "G → GND"), ("R15", "6,8 Ω", "VBAT → IR_A"),
    ("C4", "100 µF 6,3 V", "VBAT → GND, liggende"), ("LED1, LED2", "IR 940 nm 5 mm", "i serie: IR_A → LED1 → LED2 → IR_K"),
    ("U3", "VS1838B", "OUT → IR_RX, GND, VCC → IR_STROM (MCP GPB6)"),
]

FARGE = {"GND": ("svart", "#1d1d1f"), "3V3": ("rød", "#d23a2c"), "VBAT": ("oransje", "#e8822a"), "VBUS": ("lilla", "#8a4fc0"),
         "SDA": ("blå", "#2f6fd0"), "SCL": ("gul", "#e3b82b"), "INT": ("hvit", "#e8e6e0"), "LCD_SCK": ("grønn", "#2f9a52"),
         "LCD_MOSI": ("lyseblå", "#6cb7e8"), "LCD_DC": ("brun", "#8b5a2b"), "LCD_RES": ("grå", "#8e8c87"),
         "LCD_BL": ("rosa", "#e07aa8"), "LED_A": ("rød/hvit", "#e06a5c"), "LED_K": ("svart/hvit", "#55545a"),
         "IR_TX": ("turkis", "#2bb3a8"), "IR_RX": ("lysegrønn", "#8fd16a"), "IR_STROM": ("oransje/hvit", "#f0a868"),
         "POGO": ("lilla/hvit", "#b68ad8"), "DOKK": ("fiolett", "#6a4aa8"), "VBAT_ADC": ("oransje/svart", "#b5651d")}
TASTEFARGER = [("brun", "#8b5a2b"), ("rød", "#d23a2c"), ("oransje", "#e8822a"), ("gul", "#e3b82b"), ("grønn", "#2f9a52"),
               ("blå", "#2f6fd0"), ("fiolett", "#6a4aa8"), ("grå", "#8e8c87")]   # fargekoden 1–8, GPA og GPB


def farge(nett):
    if nett.startswith("K_"):
        p = next(b[3] for b in BRYTERE if "K_" + b[0].upper() == nett)
        return TASTEFARGER[p % 8]
    return FARGE.get(nett, ("hvit", "#e8e6e0"))


# ---------- hullene, kuttene og ledningene på hullkortet ----------
def hullkart():
    """{(k, j): nett} for alle bein."""
    h = {}
    for b in BRYTERE:
        for k, j, nett in bein(b):
            assert paa_kortet(k, j), (b[0], k, j)
            assert (k, j) not in h, (b[0], k, j)
            h[(k, j)] = nett
    return h


def kutt_og_segmenter(h):
    """Stripene går langs x (én per rad). Kutt der to bein på samme stripe har ulike nett: i et ledig hull mellom dem
    (bor hullet med et 3,5 mm bor) eller, når de står inntil hverandre, en riss mellom hullene.
    Returnerer (kutt: [(k_kutt, j, «hull»|«riss»)], segmenter: [(j, k0, k1, nett)])."""
    kutt, seg = [], []
    for j in range(J_MIN, J_MAX + 1):
        ks = [k for k in range(K_MIN, K_MAX + 1) if paa_kortet(k, j)]
        if not ks:
            continue
        brukt = sorted((k, h[(k, j)]) for k in ks if (k, j) in h)
        start, forrige = ks[0], None
        for k, nett in brukt:
            if forrige and forrige[1] != nett:
                ledige = [q for q in range(forrige[0] + 1, k) if (q, j) not in h]
                if ledige:
                    q = ledige[len(ledige) // 2]
                    kutt.append((q, j, "hull"))
                    seg.append((j, start, q - 1, forrige[1]))
                    start = q + 1
                else:
                    kutt.append((k - 0.5, j, "riss"))
                    seg.append((j, start, k - 1, forrige[1]))
                    start = k
            forrige = (k, nett)
        seg.append((j, start, ks[-1], forrige[1] if forrige else None))
    return kutt, seg


def tilkoblingshull(h, seg):
    """Et ledig hull på hvert segment som har et nett (der ledningen loddes), så nær beinet som mulig."""
    ut = {}
    for j, k0, k1, nett in seg:
        if not nett:
            continue
        bein_k = [k for k in range(k0, k1 + 1) if (k, j) in h]
        ledige = [k for k in range(k0, k1 + 1) if (k, j) not in h and paa_kortet(k, j)]
        if ledige:
            ut[(j, k0, k1)] = min(ledige, key=lambda k: min(abs(k - b) for b in bein_k))
    return ut


def ledninger_paa_kortet():
    """Hullkortets ledninger: én fra hver tast (høyre side) til MCP-modulen, og en GND-kjede (svart) mellom alle
    GND-segmentene, med én GND-ledning videre til MCP-modulen. Ledningene loddes på kobbersiden.
    Returnerer [(nett, (k, j) | None, mål, beskrivelse)]."""
    h = hullkart()
    kutt, seg = kutt_og_segmenter(h)
    tk = tilkoblingshull(h, seg)
    ut = []
    # én ledning per tast: fra et ledig hull på tastens segment (den nedre raden) til MCP-pinnen
    for b in BRYTERE:
        nett = "K_" + b[0].upper()
        kand = [(j, k0, k1) for (j, k0, k1, nn) in seg if nn == nett]
        kand = [s for s in kand if s in tk]
        j, k0, k1 = max(kand, key=lambda s: s[0])
        ut.append((nett, (tk[(j, k0, k1)], j), f"MCP {mcp_pinne(b[3])}", f"{b[0]} → MCP {mcp_pinne(b[3])}"))
    # GND: hver bryters GND-side er ett nett (de to beina er koblet inni bryteren), men naboer på samme stripe kan dele
    # segment. Kjede: koble bryterne i rekkefølge (nærmeste nabo) med korte svarte ledninger
    grupper = []
    for b in BRYTERE:
        k, j = b[4], b[5]
        gs = [s for s in seg if s[3] == "GND" and s[0] in (j - 1, j + 2) and s[1] <= k - 1 <= s[2]]
        grupper.append((b[0], gs))
    # union av grupper som deler segment
    forelder = list(range(len(grupper)))

    def finn(i):
        while forelder[i] != i:
            i = forelder[i]
        return i
    for a in range(len(grupper)):
        for c in range(a + 1, len(grupper)):
            if set(grupper[a][1]) & set(grupper[c][1]):
                forelder[finn(a)] = finn(c)
    komp = {}
    for i in range(len(grupper)):
        komp.setdefault(finn(i), []).append(i)
    # punkt (hull) for hver komponent: et ledig hull på den nedre GND-raden
    punkt = []
    for rot, idx in komp.items():
        s = max((s for i in idx for s in grupper[i][1]), key=lambda s: s[0])
        punkt.append(((tk[(s[0], s[1], s[2])], s[0]), [grupper[i][0] for i in idx]))
    # nærmeste-nabo-kjede fra punktet nærmest MCP-modulen
    mcp = (19.25, 144.0)
    rest = sorted(punkt, key=lambda q: math.hypot(*(a - b for a, b in zip(hull_xy(*q[0]), mcp))))
    kjede = [rest.pop(0)]
    while rest:
        a = hull_xy(*kjede[-1][0])
        nxt = min(rest, key=lambda q: math.hypot(*(u - v for u, v in zip(hull_xy(*q[0]), a))))
        rest.remove(nxt)
        kjede.append(nxt)
    ut.append(("GND", kjede[0][0], "MCP GND", f"GND ({', '.join(kjede[0][1])}) → MCP GND"))
    for a, c in zip(kjede, kjede[1:]):
        ut.append(("GND", a[0], c[0], f"GND {'/'.join(a[1])} → {'/'.join(c[1])}"))
    return ut


# ---------- ledningene mellom delene (koblingsskjemaet) ----------
LEDNINGER = [
    # (nett, fra, til)
    ("VBAT", "Batteri + (JST-PH)", "XIAO BAT+"), ("GND", "Batteri − (JST-PH)", "XIAO BAT−"),
    ("3V3", "XIAO 3V3", "MCP VCC"), ("GND", "XIAO GND", "MCP GND"),
    ("SDA", "XIAO D4", "MCP SDA"), ("SCL", "XIAO D5", "MCP SCL"), ("INT", "XIAO D1", "MCP INTA"),
    ("SDA", "MCP SDA", "6p-adapter 3 (SDA)"), ("SCL", "MCP SCL", "6p-adapter 4 (SCL)"),
    ("3V3", "MCP VCC", "6p-adapter 1 (VDD)"), ("GND", "MCP GND", "6p-adapter 2 (GND)"),
    ("3V3", "6p-adapter 1 (VDD)", "18p-adapter 9+10 (VDD)"), ("GND", "6p-adapter 2 (GND)", "18p-adapter 1+5+8+16+18 (GND)"),
    ("LCD_SCK", "XIAO D8", "18p-adapter 3 (SCK)"), ("LCD_MOSI", "XIAO D10", "18p-adapter 6 (MOSI)"),
    ("LCD_DC", "XIAO D2", "18p-adapter 4 (D/C)"), ("LCD_RES", "XIAO D3", "18p-adapter 2 (RESET)"),
    ("LCD_RES", "18p-adapter 2 (RESET)", "6p-adapter 6 (RST)"), ("LCD_BL", "XIAO D9", "R6 → Q2 G"),
    ("LED_K", "Q2 D", "18p-adapter 12–15 (LED-K)"),
    ("IR_TX", "XIAO D6", "IR-kortet (R13)"), ("IR_RX", "XIAO D7", "IR-kortet (VS1838B OUT)"),
    ("VBAT", "XIAO BAT+", "IR-kortet (R15, C4)"), ("GND", "XIAO GND", "IR-kortet (GND)"),
    ("IR_STROM", "MCP GPB6", "IR-kortet (VS1838B VCC)"),
    ("POGO", "Pogo +", "D1 / R11"), ("GND", "Pogo −", "MCP GND"), ("VBUS", "D1 (katode)", "XIAO 5V"),
    ("DOKK", "R11 / R12", "MCP GPB7"),
]

# omtrentlige endepunkter (x, n) for lengdene og 3D-sidens ledninger
ENDEPUNKT = {
    "XIAO": (CX, XIAO_N0 + 8.0), "MCP": (19.25, 144.0), "6p-adapter": (36.0, 102.0), "18p-adapter": (26.3, 121.0),
    "IR-kortet": (CX, 8.0), "Batteri": (30.5, 62.5), "Pogo": (40.0, 159.0), "R6": (30.0, 121.0), "Q2": (32.0, 121.0),
    "D1": (34.0, 186.0), "R11": (28.0, 150.0),
}


def endepunkt(navn):
    for k, v in ENDEPUNKT.items():
        if navn.startswith(k):
            return v
    raise KeyError(navn)


def lengde(a, b):
    """Ledningslengde: langs gulvet (x + n) + 15 mm til lodding og slakk, rundet opp til nærmeste 10 mm."""
    (x0, n0), (x1, n1) = endepunkt(a), endepunkt(b)
    return int(math.ceil((abs(x1 - x0) + abs(n1 - n0) + 15) / 10.0) * 10)


if __name__ == "__main__":
    print(f"R0 = {R0}, H = {H:.1f} mm, kort: x {KANT_X0:.2f}–{KANT_X1:.2f}, n {KANT_N0:.2f}–{KANT_N1:.2f} "
          f"({K_MAX - K_MIN + 1} × {J_MAX - J_MIN + 1} hull)")
    for b in BRYTERE:
        print(f"{b[0]:12s} ({b[1]:6.2f}, {b[2]:6.2f}) → ({b[6]:6.2f}, {b[7]:6.2f})  avvik {b[8]:.2f} mm  k={b[4]} j={b[5]}")
    h = hullkart()
    kutt, seg = kutt_og_segmenter(h)
    print(len(kutt), "kutt;", len([s for s in seg if s[3]]), "segmenter med nett")
    for l in ledninger_paa_kortet():
        print(l)
