"""Skjold Fjernkontroll – hovedkortet («alt på ett kort»): komponentliste og nettliste.

Én kilde for kretskortet: lag_hovedkort.py plasserer og ruter dette, sjekk_netliste.py kontrollerer det.
Koordinater: x tvers (0 … 55 mm, venstre kant = 0) og n fra nesen, samme som i skjold_fjernkontroll.scad.
Side: «F» = oppsiden (tastene), «B» = undersiden (alt annet).

Hovedvalg (se LES_MEG, «Hovedkort»):
- ESP32-S3-WROOM-1-N4R2 (KiCad-biblioteket har ikke MINI-1-fotavtrykket; WROOM-1 har Espressifs fotavtrykk med
  antennefri sone). Antennen ligger ut mot venstre kortkant, nær halen.
- USB-C (HRO TYPE-C-31-M-12) med 5,1 kΩ på CC1/CC2, USBLC6-2SC6 og innebygd USB (GPIO19/20) for flashing og logg.
- TP4056 lader (PROG 2,4 kΩ ≈ 500 mA). Batteriet må ha egen beskyttelseskrets (603450-cellene på AliExpress har det).
- Lastdeling: VBUS → Schottky → VSYS, batteri → AO3401 → VSYS (av når USB står i).
- RT9080-33 LDO (2 µA hvilestrøm, 600 mA) fra VSYS til 3V3.
- 3 × TCA9555 for de 43 bryterne (8 faste + 35 i rutenettet), samme som håndkoblet versjon."""
import os
import sys

HER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HER))
import taster  # noqa: E402

taster.bruk("kort")
W = 55.0
L = taster.L_KORT

FP = {
    "R": "Resistor_SMD:R_0402_1005Metric", "C": "Capacitor_SMD:C_0402_1005Metric", "C10u": "Capacitor_SMD:C_0603_1608Metric",
    "C100u": "Capacitor_SMD:C_1210_3225Metric", "SOT23": "Package_TO_SOT_SMD:SOT-23", "SOT23-5": "Package_TO_SOT_SMD:SOT-23-5",
    "SOT23-6": "Package_TO_SOT_SMD:SOT-23-6", "ESOP8": "Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm",
    "TSSOP24": "Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm", "SOD123": "Diode_SMD:D_SOD-123",
    "WROOM": "RF_Module:ESP32-S3-WROOM-1", "USBC": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
    "FPC18": "Connector_FFC-FPC:Hirose_FH12-18S-0.5SH_1x18-1MP_P0.50mm_Horizontal",
    "FPC6": "Connector_FFC-FPC:Hirose_FH12-6S-0.5SH_1x06-1MP_P0.50mm_Horizontal",
    "PH2": "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal",
    "SH5": "Connector_JST:JST_SH_SM05B-SRSS-TB_1x05-1MP_P1.00mm_Horizontal",
    "SW": "Button_Switch_SMD:SW_Push_1P1T_NO_CK_KMR2", "KNAPP": "Button_Switch_SMD:SW_SPST_PTS810",
    "TP": "TestPoint:TestPoint_Pad_D1.0mm", "PUTE": "TestPoint:TestPoint_Pad_D1.5mm",
}
# LCSC-nummer er fra minnet og IKKE bekreftet her (lcsc.com/jlcpcb.com var ikke tilgjengelig); alle er merket «sjekk».
LCSC = {
    "10k": "C25744", "100k": "C25741", "1k": "C11702", "5.1k": "C25905", "4.7k": "C25900", "1M": "C26083", "100R": "C25076",
    "2.4k": "", "68k": "", "10R": "C25077", "100nF": "C1525", "1uF": "C52923", "10uF": "C19702", "100uF": "",
    "AO3400A": "C20917", "AO3401A": "C15127", "USBLC6-2SC6": "C7519", "TP4056": "C16581", "B5819W": "C8598",
    "TYPE-C-31-M-12": "C165948", "TCA9555PWR": "", "RT9080-33GJ5": "", "ESP32-S3-WROOM-1-N4R2": "",
    "FH12-18S-0.5SH": "", "FH12-6S-0.5SH": "", "S2B-PH-SM4-TB": "", "SM05B-SRSS-TB": "", "KMR221G": "", "PTS810": "",
}

KOMP = []   # (ref, fotavtrykk, verdi, side, x, n, rot, {pute: nett})


def k(ref, fp, verdi, side, x, n, rot, puter):
    KOMP.append((ref, FP[fp], verdi, side, x, n, rot, puter))


# ---------- ESP32-S3-WROOM-1 (antennen mot venstre kortkant) ----------
ESP_X, ESP_N = 2.3 + 12.75, 177.0   # antennen stikker 0,9 mm ut over kortkanten (anbefalt)      # modulens senter; rotert 90°: antennen (fotavtrykkets −y) peker mot −x
ESP = {"1": "GND", "2": "3V3", "3": "EN", "4": "IR_TX", "5": "IR_RX", "6": "VIB_SW", "7": "TCA_INT", "8": "SKJ_PA",
       "9": "MOTOR", "10": "CHRG", "11": "T_SDA", "12": "SDA", "13": "USB_DN", "14": "USB_DP", "15": "", "16": "", "17": "SCL",
       "18": "T_INT", "19": "LCD_MOSI", "20": "LCD_SCK", "21": "LCD_DC", "22": "LCD_RES", "23": "LCD_BL", "24": "", "25": "",
       "26": "", "27": "BOOT", "28": "", "29": "", "30": "", "31": "T_SCL", "32": "", "33": "DOKK", "34": "", "35": "",
       "36": "U0RXD", "37": "U0TXD", "38": "T_RST", "39": "VBAT_ADC", "40": "GND", "41": "GND"}
# GPIO: IR_TX 4 · IR_RX 5 · VIB_SW 6 (RTC, vekking) · TCA_INT 7 (RTC, vekking) · SKJ_PA 15 (3V3_SW av/på) · MOTOR 16 ·
# CHRG 17 · SDA 8 · SCL 9 · T_SDA 18 · T_SCL 38 · DOKK 40 · T_INT 10 · MOSI 11 · SCK 12 · DC 13 · RES 14 · BL 21 · USB 19/20 · BOOT 0 · T_RST 2 · VBAT 1
GPIO = {"IR_TX": 4, "IR_RX": 5, "VIB_SW": 6, "TCA_INT": 7, "SKJ_PA": 15, "MOTOR": 16, "CHRG": 17, "SDA": 8, "SCL": 9, "T_SDA": 18, "T_SCL": 38, "DOKK": 40,
        "T_INT": 10, "LCD_MOSI": 11, "LCD_SCK": 12, "LCD_DC": 13, "LCD_RES": 14, "LCD_BL": 21, "USB_DN": 19, "USB_DP": 20,
        "BOOT": 0, "T_RST": 2, "VBAT_ADC": 1, "U0TXD": 43, "U0RXD": 44}
k("U1", "WROOM", "ESP32-S3-WROOM-1-N4R2", "B", ESP_X, ESP_N, 90, {p: n for p, n in ESP.items() if n})
k("C1", "C10u", "10uF", "B", 14.8, 166.0, 0, {"1": "3V3", "2": "GND"})
k("C2", "C", "100nF", "B", 12.0, 166.0, 0, {"1": "3V3", "2": "GND"})
k("R1", "R", "10k", "B", 30.8, 176.5, 0, {"1": "3V3", "2": "EN"})          # EN: 10 kΩ / 1 µF (Espressif)
k("C3", "C", "1uF", "B", 30.8, 178.5, 0, {"1": "EN", "2": "GND"})
k("SW44", "KNAPP", "PTS810 RESET", "B", 33.5, 183.5, 0, {"1": "EN", "2": "GND"})
k("SW45", "KNAPP", "PTS810 BOOT", "B", 31.0, 194.0, 0, {"1": "BOOT", "2": "GND"})
k("R2", "R", "10k", "B", 30.8, 169.0, 0, {"1": "3V3", "2": "BOOT"})

# ---------- USB-C, ESD, lader, lastdeling og LDO (halen, til høyre) ----------
USB_X, USB_N = 27.5 + 12.0, L - 2.15 - 4.2   # munningen 0,35 mm bak innerveggen (stikker 1,05 mm ut over kortkanten)
k("J1", "USBC", "TYPE-C-31-M-12", "B", USB_X, USB_N, 180,
  {"A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS", "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
   "A5": "CC1", "B5": "CC2", "A6": "USB_DP", "B6": "USB_DP", "A7": "USB_DN", "B7": "USB_DN"})
k("R3", "R", "5.1k", "B", 37.0, 189.5, 90, {"1": "CC1", "2": "GND"})
k("R4", "R", "5.1k", "B", 46.0, 189.0, 90, {"1": "CC2", "2": "GND"})
k("C14", "C", "100nF", "B", 42.4, 186.5, 90, {"1": "VBUS", "2": "GND"})
k("C15", "C", "100nF", "B", 39.6, 182.8, 0, {"1": "VBUS", "2": "GND"})
k("U2", "SOT23-6", "USBLC6-2SC6", "B", 39.5, 186.5, 0, {"1": "USB_DP", "6": "USB_DP", "3": "USB_DN", "4": "USB_DN", "2": "GND", "5": "VBUS"})
k("U3", "ESOP8", "TP4056", "B", 41.5, 178.5, 90, {"1": "GND", "2": "PROG", "3": "GND", "4": "VBUS", "5": "VBAT", "6": "", "7": "CHRG", "8": "VBUS", "9": "GND"})
k("R5", "R", "2.4k", "B", 36.0, 178.0, 90, {"1": "PROG", "2": "GND"})
k("C4", "C10u", "10uF", "B", 47.0, 178.5, 90, {"1": "VBUS", "2": "GND"})
k("C5", "C10u", "10uF", "B", 41.5, 173.0, 0, {"1": "VBAT", "2": "GND"})
k("R6", "R", "10k", "B", 36.0, 174.5, 90, {"1": "3V3", "2": "CHRG"})
k("D1", "SOD123", "B5819W", "B", 47.0, 171.0, 90, {"1": "VSYS", "2": "VBUS"})
k("Q1", "SOT23", "AO3401A", "B", 41.5, 167.0, 0, {"1": "VBUS_G", "3": "VBAT", "2": "VSYS"})   # P: G, S=VSYS, D=VBAT
k("R7", "R", "100k", "B", 36.5, 167.0, 90, {"1": "VBUS_G", "2": "GND"})
k("R8", "R", "0R", "B", 45.5, 166.5, 90, {"1": "VBUS", "2": "VBUS_G"})                       # gate til VBUS (0 Ω-bro)
k("U4", "SOT23-5", "RT9080-33GJ5", "B", 41.5, 160.5, 0, {"1": "VSYS", "2": "GND", "3": "VSYS", "5": "3V3"})
k("C6", "C", "1uF", "B", 37.0, 160.5, 90, {"1": "VSYS", "2": "GND"})
k("C7", "C10u", "10uF", "B", 46.0, 160.5, 90, {"1": "3V3", "2": "GND"})
k("R9", "R", "1M", "B", 36.5, 156.0, 90, {"1": "VBAT", "2": "VBAT_ADC"})                     # VBAT-deler 1 M / 1 M
k("R10", "R", "1M", "B", 38.5, 156.0, 90, {"1": "VBAT_ADC", "2": "GND"})
k("C8", "C", "100nF", "B", 40.5, 156.0, 90, {"1": "VBAT_ADC", "2": "GND"})
k("J2", "PH2", "S2B-PH-SM4-TB", "B", 46.8, 84.5, 180, {"1": "VBAT", "2": "GND", "MP": "GND"})   # batteri: 1 = +, 2 = −

# ---------- skjerm og berøring ----------
k("J3", "FPC18", "FH12-18S-0.5SH", "B", W/2 - 47.8/2 + 17.96 + 9.5/2, 8.4 + 66.5 + 37.0, 0, {
    "1": "GND", "2": "LCD_RES", "3": "LCD_SCK", "4": "LCD_DC", "5": "GND", "6": "LCD_MOSI", "7": "", "8": "GND", "9": "3V3_SW",
    "10": "3V3_SW", "11": "LED_A", "12": "LED_K", "13": "LED_K", "14": "LED_K", "15": "LED_K", "16": "GND", "17": "", "18": "GND",
    "MP": "GND"})   # ANTATT pinnerekkefølge (CS = 5 til GND) – sjekk mot selgerens tegning!
k("J4", "FPC6", "FH12-6S-0.5SH", "B", W/2 + 10.6, 8.4 + 66.5 + 29.0, 0, {
    "1": "3V3_SW", "2": "GND", "3": "T_SDA", "4": "T_SCL", "5": "T_INT", "6": "T_RST", "MP": "GND"})   # ANTATT – sjekk
k("Q2", "SOT23", "AO3401A", "B", 14.0, 98.0, 0, {"1": "SKJ_PA", "2": "3V3", "3": "3V3_SW"})      # 3V3 til skjerm, berøring, IR-mottaker
k("R11", "R", "100k", "B", 10.0, 98.0, 90, {"1": "3V3", "2": "SKJ_PA"})
k("C9", "C10u", "10uF", "B", 18.0, 98.0, 90, {"1": "3V3_SW", "2": "GND"})
k("Q3", "SOT23", "AO3400A", "B", 14.0, 104.0, 0, {"1": "BL_G", "2": "GND", "3": "LED_K"})         # baklys (PWM)
k("R12", "R", "100R", "B", 10.0, 104.0, 90, {"1": "LCD_BL", "2": "BL_G"})
k("R13", "R", "100k", "B", 18.0, 104.0, 90, {"1": "BL_G", "2": "GND"})
k("R14", "R", "10R", "B", 22.0, 104.0, 90, {"1": "3V3_SW", "2": "LED_A"})                        # baklys-motstand (sjekk panelets LED-spec)

# ---------- I²C, TCA9555 × 3 og tastene ----------
k("R15", "R", "4.7k", "B", 24.0, 130.0, 90, {"1": "3V3", "2": "SDA"})
k("R16", "R", "4.7k", "B", 26.0, 130.0, 90, {"1": "3V3", "2": "SCL"})
k("R17", "R", "10k", "B", 28.0, 130.0, 90, {"1": "3V3", "2": "TCA_INT"})
k("R18", "R", "10k", "B", 30.0, 130.0, 90, {"1": "3V3_SW", "2": "T_INT"})
# berøringen har egen buss (GPIO18/38) med pull-up til 3V3_SW: en avslått berøringsbrikke på TCA-bussen ville
# trukket SDA/SCL ned gjennom vernediodene og kostet ~1 mA i dyp søvn
k("R24", "R", "4.7k", "B", 32.0, 130.0, 90, {"1": "3V3_SW", "2": "T_SDA"})
k("R25", "R", "4.7k", "B", 34.0, 130.0, 90, {"1": "3V3_SW", "2": "T_SCL"})
TCA = [("U5", 0x20, 18.0, 145.0), ("U6", 0x21, 27.5, 145.0), ("U7", 0x22, 37.0, 145.0)]
brytere = taster.brytere()
for ci, (ref, adr, x, n) in enumerate(TCA):
    a = adr - 0x20
    p = {"1": "TCA_INT", "2": "3V3" if a & 2 else "GND", "3": "3V3" if a & 4 else "GND", "21": "3V3" if a & 1 else "GND",
         "22": "SCL", "23": "SDA", "24": "3V3", "12": "GND"}
    for pin in range(16):
        i = ci * 16 + pin
        pute = str(4 + pin) if pin < 8 else str(13 + pin - 8)
        if i < len(brytere):
            p[pute] = f"K_{brytere[i][0]}"
    k(ref, "TSSOP24", "TCA9555PWR", "B", x, n, 0, p)
    k(f"C{10 + ci}", "C", "100nF", "B", x + 2.9, n + 5.6, 0, {"1": "3V3", "2": "GND"})
for i, (bid, nv, x, n, hid) in enumerate(brytere):
    k(f"SW{i + 1}", "SW", "KMR221G", "F", x, n, 90, {"1": f"K_{bid}", "2": "GND"})

# ---------- IR (diodene og mottakeren sitter på IR-kortet i nesen), motor og vibrasjonsbryter ----------
k("J5", "SH5", "SM05B-SRSS-TB", "B", 8.5, 84.5, 180, {"1": "VSYS", "2": "IR_K", "3": "IR_RX", "4": "3V3_SW", "5": "GND", "MP": "GND"})
k("Q4", "SOT23", "AO3400A", "B", 8.5, 90.5, 0, {"1": "IR_G", "2": "GND", "3": "IR_K"})
k("R19", "R", "100R", "B", 4.5, 90.5, 90, {"1": "IR_TX", "2": "IR_G"})
k("R20", "R", "100k", "B", 12.5, 90.5, 90, {"1": "IR_G", "2": "GND"})
k("C13", "C100u", "100uF", "B", 16.5, 85.5, 0, {"1": "VSYS", "2": "GND"})
k("Q5", "SOT23", "AO3400A", "B", 40.0, 114.5, 0, {"1": "MOT_G", "2": "GND", "3": "MOT_K"})
k("R21", "R", "1k", "B", 36.5, 114.5, 90, {"1": "MOTOR", "2": "MOT_G"})
k("R22", "R", "100k", "B", 43.5, 114.5, 90, {"1": "MOT_G", "2": "GND"})
k("D2", "SOD123", "B5819W", "B", 40.0, 110.5, 0, {"1": "VSYS", "2": "MOT_K"})
k("TP1", "PUTE", "MOT+", "B", 47.0, 106.5, 0, {"1": "VSYS"})
k("TP2", "PUTE", "MOT-", "B", 50.0, 106.5, 0, {"1": "MOT_K"})
k("TP3", "PUTE", "VIB 3V3", "B", 47.0, 122.5, 0, {"1": "3V3"})
k("TP4", "PUTE", "VIB", "B", 50.0, 122.5, 0, {"1": "VIB_SW"})
k("R23", "R", "1M", "B", 47.0, 126.0, 0, {"1": "VIB_SW", "2": "GND"})
# dokken: magnetisk pogo-kontakt (hunndelen i bunnen, rett under) → Schottky → VBUS, så USB-C og dokken ikke mater
# hverandre; 68 k / 100 k til GPIO40 forteller fastvaren at den står i dokken (5 V → 3,0 V)
k("TP16", "PUTE", "POGO+", "B", 48.5, 143.0, 0, {"1": "POGO"})
k("TP17", "PUTE", "POGO-", "B", 48.5, 146.5, 0, {"1": "GND"})
k("D3", "SOD123", "B5819W", "B", 45.5, 151.5, 90, {"1": "VBUS", "2": "POGO"})
k("R26", "R", "68k", "B", 48.5, 151.0, 90, {"1": "POGO", "2": "DOKK"})
k("R27", "R", "100k", "B", 48.5, 154.0, 90, {"1": "DOKK", "2": "GND"})
# testpunkter
for i, (nett, x, n) in enumerate([("3V3", 26.0, 160.0), ("VBAT", 28.5, 160.0), ("GND", 31.0, 160.0), ("EN", 26.0, 163.0), ("BOOT", 28.5, 163.0),
                                   ("U0TXD", 31.0, 163.0), ("U0RXD", 26.0, 166.0), ("SDA", 28.5, 166.0), ("SCL", 31.0, 166.0),
                                   ("VSYS", 33.5, 160.0), ("VBUS", 33.5, 163.0)], start=5):
    k(f"TP{i}", "TP", nett, "B", x, n, 0, {"1": nett})


def netter():
    ut = {}
    for ref, fp, verdi, side, x, n, rot, puter in KOMP:
        for p, nett in puter.items():
            ut.setdefault(nett, []).append((ref, p))
    return ut
