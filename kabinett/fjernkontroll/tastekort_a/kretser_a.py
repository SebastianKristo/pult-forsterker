"""Tastekort A («bare knapper»): komponentliste og nettliste for den håndkoblede utgaven med tasteoppsett A.

14 taster (av/på, Skjold, meny, D-pad med OK, tilbake, avslutt, spill/pause, demp, volum + og −) på oppsiden,
nøyaktig der taster.py plasserer dem i oppsett A, og én TCA9555 (0x20) med pull-ups og avkobling på undersiden.
JST-SH 5 p (3V3, GND, SDA, SCL, INT) til SuperMini-en, og loddeputer for de samme pluss skjermstrøm (P1_6),
dokken (POGO+ → 68 k / 100 k → P1_7) og skjermens og berøringens FPC-kontakter (som på det gamle tastekortet).
Koordinater: x tvers og n fra nesen (som i skjold_fjernkontroll.scad). Side «F» = oppsiden (tastene), «B» = undersiden."""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import taster  # noqa: E402

taster.bruk("kort")
W, L = 55.0, taster.L_KORT
FP = {
    "SW": os.path.join(HER, "fotavtrykk.pretty") + ":SW_Tact_4x4x1.5mm_SMD",
    "R": "Resistor_SMD:R_0402_1005Metric", "C": "Capacitor_SMD:C_0402_1005Metric",
    "TSSOP24": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm",
    "SH5": "Connector_JST:JST_SH_SM05B-SRSS-TB_1x05-1MP_P1.00mm_Horizontal",
    "FPC18": "Connector_FFC-FPC:Hirose_FH12-18S-0.5SH_1x18-1MP_P0.50mm_Horizontal",
    "FPC6": "Connector_FFC-FPC:Hirose_FH12-6S-0.5SH_1x06-1MP_P0.50mm_Horizontal",
    "PUTE": "TestPoint:TestPoint_Pad_D1.5mm",
}
# LCSC-nummer fra hukommelsen, ikke slått opp (lcsc.com/jlcpcb.com var ikke tilgjengelig): alle er merket «sjekk»
LCSC = {"10k": "C25744", "100k": "C25741", "68k": "", "100nF": "C1525", "TCA9555PWR": "", "SM05B-SRSS-TB": "",
        "FH12-18S-0.5SH": "", "FH12-6S-0.5SH": "", "4x4x1.5": ""}
KOMP = []


def k(ref, fp, verdi, side, x, n, rot, puter):
    KOMP.append((ref, FP[fp], verdi, side, x, n, rot, puter))


# ---------- tastene (oppsiden), i TCA9555-rekkefølge ----------
TASTER = taster.tastekort_a()
for f, x, n, p in TASTER:
    k(f"SW{p + 1}", "SW", "4x4x1.5", "F", x, n, 0, {"1": f"K_{f.upper()}", "2": "GND"})

# ---------- TCA9555 (0x20) ----------
pute = lambda pin: str(4 + pin) if pin < 8 else str(13 + pin - 8)   # P0_0 … P1_7 → TSSOP-pinne
tca = {"1": "INT", "2": "GND", "3": "GND", "21": "GND", "22": "SCL", "23": "SDA", "24": "3V3", "12": "GND"}
for f, x, n, p in TASTER:
    tca[pute(p)] = f"K_{f.upper()}"
tca[pute(14)] = "SKJ"     # P1_6: skjermstrøm (utgang til AO3401-gaten)
tca[pute(15)] = "DOKK"    # P1_7: dokken (inngang, høy = i dokken)
k("U1", "TSSOP24", "TCA9555PWR", "B", 40.5, 145.0, 0, tca)
k("C1", "C", "100nF", "B", 45.2, 145.0, 90, {"1": "3V3", "2": "GND"})
k("R1", "R", "10k", "B", 34.0, 138.0, 90, {"1": "3V3", "2": "SDA"})
k("R2", "R", "10k", "B", 35.5, 138.0, 90, {"1": "3V3", "2": "SCL"})
k("R3", "R", "10k", "B", 37.0, 138.0, 90, {"1": "3V3", "2": "INT"})
k("R4", "R", "68k", "B", 44.0, 138.0, 90, {"1": "POGO", "2": "DOKK"})
k("R5", "R", "100k", "B", 45.5, 138.0, 90, {"1": "DOKK", "2": "GND"})

# ---------- til SuperMini-en ----------
k("J1", "SH5", "SM05B-SRSS-TB", "B", 14.0, 160.0, 180, {"1": "3V3", "2": "GND", "3": "SDA", "4": "SCL", "5": "INT", "MP": "GND"})

# ---------- skjermens og berøringens FPC-kontakter (samme sted som på det gamle tastekortet) ----------
FPC_X = W / 2 - 47.8 / 2 + 17.96 + 9.5 / 2
k("J2", "FPC18", "FH12-18S-0.5SH", "B", FPC_X, 8.4 + 66.5 + 37.0, 0, {
    "1": "GND", "2": "LCD_RES", "3": "LCD_SCK", "4": "LCD_DC", "5": "GND", "6": "LCD_MOSI", "8": "GND", "9": "VCC_SKJ",
    "10": "VCC_SKJ", "11": "LED_A", "12": "LED_K", "13": "LED_K", "14": "LED_K", "15": "LED_K", "16": "GND", "18": "GND",
    "MP": "GND"})   # ANTATT pinnerekkefølge (CS = 5 til GND) – sjekk mot selgerens tegning
k("J3", "FPC6", "FH12-6S-0.5SH", "B", W / 2 + 8, 8.4 + 66.5 + 29.0, 0, {
    "1": "VCC_SKJ", "2": "GND", "3": "T_SDA", "4": "T_SCL", "5": "T_INT", "6": "T_RST", "MP": "GND"})   # ANTATT – sjekk

# ---------- loddeputer (undersiden, to rader foran) ----------
PUTER = ["3V3", "GND", "SDA", "SCL", "INT", "SKJ", "POGO", "VCC_SKJ", "GND",
         "LCD_RES", "LCD_SCK", "LCD_DC", "LCD_MOSI", "LED_A", "LED_K", "T_SDA", "T_SCL", "T_INT", "T_RST"]
TEKST = {"POGO": "POGO+", "VCC_SKJ": "VCC"}
for i, nett in enumerate(PUTER):
    rad, kol = divmod(i, 10)
    k(f"TP{i + 1}", "PUTE", TEKST.get(nett, nett), "B", 6.5 + kol * 4.6, 88.0 + rad * 4.2, 0, {"1": nett})


def netter():
    ut = {}
    for ref, fp, verdi, side, x, n, rot, puter in KOMP:
        for p, nett in puter.items():
            ut.setdefault(nett, []).append((ref, p))
    return ut
