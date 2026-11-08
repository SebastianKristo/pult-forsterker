"""Skjold Fjernkontroll Enkel: bærekort med Seeed XIAO ESP32S3, MCP23017 og de 14 tastene i oppsett A.

Kortet har nesten bare store deler: XIAO-modulen loddes flatt med kantputene, MCP23017 i SOIC-28 (1,27 mm),
motstander og kondensatorer i 0805, to SOT-23 (AO3400/AO3401) og fire kontakter. De eneste vanskelige delene er
FPC-kontaktene (0,5 mm) til skjermen og berøringen, som JLC kan montere.
Ingen USB, lader, LDO eller ESP-brikke på kortet: XIAO-en lader batteriet (BAT-putene) og gir 3,3 V.
Koordinater: x tvers og n fra nesen, som i skjold_fjernkontroll.scad. «F» = oppsiden (tastene), «B» = undersiden.

XIAO ESP32S3-pinnene (Seeeds pinout, sjekk mot din modul):
  D0 GPIO1  VBAT (1 M / 1 M)        D6 GPIO43 IR_TX            5V   VBUS (USB, og dokken via Schottky)
  D1 GPIO2  INT fra MCP23017        D7 GPIO44 IR_RX            GND
  D2 GPIO3  skjerm DC               D8 GPIO7  skjerm SCK       3V3  3,3 V ut fra XIAO-en (≤ 700 mA)
  D3 GPIO4  skjerm RES + berøring RST  D9 GPIO8  baklys (PWM)
  D4 GPIO5  SDA                     D10 GPIO9 skjerm MOSI
  D5 GPIO6  SCL
  BAT+/BAT− (baksiden): batteriet, med to korte ledninger gjennom vinduet i bærekortet.
Berøringens INT er ikke koblet (ingen ledig pinne): fastvaren spør berøringen hvert 20. ms når skjermen er på."""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import taster  # noqa: E402

taster.bruk("kort")
W, L = 55.0, taster.L_KORT
EGEN = os.path.join(HER, "fotavtrykk.pretty")
FP = {
    "XIAO": EGEN + ":Seeed_XIAO_ESP32S3_SMD", "SW": EGEN + ":SW_Tact_4x4x1.5mm_SMD",
    "R": "Resistor_SMD:R_0805_2012Metric", "C": "Capacitor_SMD:C_0805_2012Metric", "C100u": "Capacitor_SMD:C_1210_3225Metric",
    "SOIC28": "Package_SO:SOIC-28W_7.5x17.9mm_P1.27mm", "SOT23": "Package_TO_SOT_SMD:SOT-23", "SOD123": "Diode_SMD:D_SOD-123",
    "PH2": "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    "SH5": "Connector_JST:JST_SH_SM05B-SRSS-TB_1x05-1MP_P1.00mm_Horizontal",
    "FPC18": "Connector_FFC-FPC:Hirose_FH12-18S-0.5SH_1x18-1MP_P0.50mm_Horizontal",
    "FPC6": "Connector_FFC-FPC:Hirose_FH12-6S-0.5SH_1x06-1MP_P0.50mm_Horizontal",
    "PUTE": "TestPoint:TestPoint_Pad_D2.0mm",
}
# LCSC-nummer fra hukommelsen, ikke slått opp: alle er merket «sjekk»
LCSC = {"10k": "C17414", "100k": "C17407", "4.7k": "C17673", "1M": "C17514", "68k": "C17801", "100R": "C17408", "10R": "C17415",
        "6.8R": "", "100nF": "C49678", "10uF": "C15850", "100uF": "", "AO3400A": "C20917", "AO3401A": "C15127", "B5819W": "C8598",
        "MCP23017-E/SO": "", "FH12-18S-0.5SH": "", "FH12-6S-0.5SH": "", "S2B-PH-SM4-TB": "", "SM05B-SRSS-TB": "",
        "XIAO_ESP32S3": "", "4x4x1.5": ""}
KOMP = []


def k(ref, fp, verdi, side, x, n, rot, puter):
    KOMP.append((ref, FP[fp], verdi, side, x, n, rot, puter))


# ---------- XIAO ESP32S3 i halen, under kortet (komponentsiden ned), USB-C mot halen ----------
XIAO_X, XIAO_N = W / 2, 188.9       # senter; modulen går til n 199,4, USB-C 1,0 mm til, like bak innerveggen
XIAO = {"1": "VBAT_ADC", "2": "INT", "3": "LCD_DC", "4": "LCD_RES", "5": "SDA", "6": "SCL", "7": "IR_TX",
        "8": "IR_RX", "9": "LCD_SCK", "10": "LCD_BL", "11": "LCD_MOSI", "12": "3V3", "13": "GND", "14": "VBUS"}
GPIO = {"VBAT_ADC": 1, "INT": 2, "LCD_DC": 3, "LCD_RES": 4, "SDA": 5, "SCL": 6, "IR_TX": 43, "IR_RX": 44,
        "LCD_SCK": 7, "LCD_BL": 8, "LCD_MOSI": 9}
k("U1", "XIAO", "XIAO_ESP32S3", "B", XIAO_X, XIAO_N, 0, XIAO)   # på undersiden speiles den: USB-C mot halen
# batteriet går til XIAO-ens BAT-puter på baksiden: to puter her, og korte ledninger gjennom vinduet i kortet
k("TP1", "PUTE", "BAT+", "B", 40.5, 181.5, 0, {"1": "VBAT"})
k("TP2", "PUTE", "BAT-", "B", 40.5, 185.0, 0, {"1": "GND"})

# ---------- tastene (oppsiden) og MCP23017 (0x20) ----------
TASTER = taster.tastekort_a()
for f, x, n, p in TASTER:
    k(f"SW{p + 1}", "SW", "4x4x1.5", "F", x, n, 0, {"1": f"K_{f.upper()}", "2": "GND"})
mpin = lambda p: str(21 + p) if p < 8 else str(p - 7)      # GPA0–7 = pinne 21–28, GPB0–7 = pinne 1–8
mcp = {"9": "3V3", "10": "GND", "12": "SCL", "13": "SDA", "15": "GND", "16": "GND", "17": "GND", "18": "MCP_RST", "20": "INT"}
for f, x, n, p in TASTER:
    mcp[mpin(p)] = f"K_{f.upper()}"
mcp[mpin(14)] = "SKJ"     # GPB6: skjermstrøm (utgang → AO3401)
mcp[mpin(15)] = "DOKK"    # GPB7: dokken (inngang)
k("U2", "SOIC28", "MCP23017-E/SO", "B", 30.0, 140.0, 0, mcp)
k("C1", "C", "100nF", "B", 22.6, 137.5, 90, {"1": "3V3", "2": "GND"})
k("R1", "R", "4.7k", "B", 39.0, 144.0, 90, {"1": "3V3", "2": "SDA"})
k("R2", "R", "4.7k", "B", 41.5, 144.0, 90, {"1": "3V3", "2": "SCL"})
k("R3", "R", "10k", "B", 44.0, 144.0, 90, {"1": "3V3", "2": "INT"})
k("R4", "R", "10k", "B", 39.0, 150.0, 90, {"1": "3V3", "2": "MCP_RST"})

# ---------- skjermstrøm, baklys og skjermens/berøringens kontakter ----------
k("Q1", "SOT23", "AO3401A", "B", 14.0, 98.0, 0, {"1": "SKJ", "2": "3V3", "3": "3V3_SW"})
k("R5", "R", "100k", "B", 9.5, 98.0, 90, {"1": "3V3", "2": "SKJ"})
k("C2", "C", "10uF", "B", 18.5, 98.0, 90, {"1": "3V3_SW", "2": "GND"})
k("Q2", "SOT23", "AO3400A", "B", 14.0, 104.5, 0, {"1": "BL_G", "2": "GND", "3": "LED_K"})
k("R6", "R", "100R", "B", 9.5, 104.5, 90, {"1": "LCD_BL", "2": "BL_G"})
k("R7", "R", "100k", "B", 18.5, 104.5, 90, {"1": "BL_G", "2": "GND"})
k("R8", "R", "10R", "B", 22.0, 104.5, 90, {"1": "3V3_SW", "2": "LED_A"})
FPC_X = W / 2 - 47.8 / 2 + 17.96 + 9.5 / 2
k("J2", "FPC18", "FH12-18S-0.5SH", "B", FPC_X, 8.4 + 66.5 + 37.0, 0, {
    "1": "GND", "2": "LCD_RES", "3": "LCD_SCK", "4": "LCD_DC", "5": "GND", "6": "LCD_MOSI", "8": "GND", "9": "3V3_SW",
    "10": "3V3_SW", "11": "LED_A", "12": "LED_K", "13": "LED_K", "14": "LED_K", "15": "LED_K", "16": "GND", "18": "GND",
    "MP": "GND"})   # ANTATT pinnerekkefølge (CS = 5 til GND) – sjekk mot selgerens tegning
k("J3", "FPC6", "FH12-6S-0.5SH", "B", W / 2 + 8.3, 8.4 + 66.5 + 29.0, 0, {
    "1": "3V3", "2": "GND", "3": "SDA", "4": "SCL", "6": "LCD_RES", "MP": "GND"})   # ANTATT; berøringen på 3V3 (ikke 3V3_SW): den deler I²C med MCP23017

# ---------- batteri, batterimåling og dokken ----------
k("J1", "PH2", "S2B-PH-SM4-TB", "B", 46.8, 84.5, 180, {"1": "VBAT", "2": "GND", "MP": "GND"})   # pinne 1 = +
k("R9", "R", "1M", "B", 13.0, 172.0, 90, {"1": "VBAT", "2": "VBAT_ADC"})
k("R10", "R", "1M", "B", 15.5, 172.0, 90, {"1": "VBAT_ADC", "2": "GND"})
k("C3", "C", "100nF", "B", 18.0, 172.0, 90, {"1": "VBAT_ADC", "2": "GND"})
k("R16", "R", "1M", "B", 44.0, 104.0, 90, {"1": "3V3", "2": "LCD_RES"})   # holder berøringens RST høy i dyp søvn (ellers flyter GPIO4)
k("TP3", "PUTE", "POGO+", "B", 48.5, 145.5, 0, {"1": "POGO"})
k("TP4", "PUTE", "POGO-", "B", 48.5, 149.5, 0, {"1": "GND"})
k("D1", "SOD123", "B5819W", "B", 44.5, 155.5, 90, {"1": "VBUS", "2": "POGO"})
k("R11", "R", "68k", "B", 47.5, 165.0, 90, {"1": "POGO", "2": "DOKK"})
k("R12", "R", "100k", "B", 47.5, 169.0, 90, {"1": "DOKK", "2": "GND"})

# ---------- IR: kortet i nesen (2 × IR-diode i serie, VS1838B) via JST-SH 5 p ----------
k("J4", "SH5", "SM05B-SRSS-TB", "B", 8.5, 84.5, 180, {"1": "IR_A", "2": "IR_K", "3": "IR_RX", "4": "3V3_SW", "5": "GND", "MP": "GND"})
k("Q3", "SOT23", "AO3400A", "B", 8.5, 91.5, 0, {"1": "IR_G", "2": "GND", "3": "IR_K"})
k("R13", "R", "100R", "B", 4.6, 95.0, 90, {"1": "IR_TX", "2": "IR_G"})
k("R14", "R", "100k", "B", 12.5, 91.5, 90, {"1": "IR_G", "2": "GND"})
k("R15", "R", "6.8R", "B", 16.0, 93.5, 0, {"1": "VBAT", "2": "IR_A"})    # 2 dioder i serie: (3,8 − 2,8) / 6,8 ≈ 150 mA puls
k("C4", "C100u", "100uF", "B", 16.5, 88.0, 0, {"1": "VBAT", "2": "GND"})


def netter():
    ut = {}
    for ref, fp, verdi, side, x, n, rot, puter in KOMP:
        for p, nett in puter.items():
            ut.setdefault(nett, []).append((ref, p))
    return ut
