#!/usr/bin/env python3
"""KI Pultforsterker – hovedkort (rev. A). Bygger kicad_pcb med pcbnew-API-et (KiCad 7).

Alt unntatt Raspberry Pi 4 og frontdelene: 24 V inn (sikring, TVS, bulk), TPS54560 5 V/5 A buck,
AMS1117 3,3 V, ICL7660 -5 V, PCM5102A DAC, G6K-2P relé (DAC/AUX), PGA2311 volum, TPA3116D2 2x50 W,
LED-drivere (AO3400), kontakter til Pi (2x20), front (JST XH) og bak (skruterminaler).

Koordinater i mm, origo øverst til venstre på kortet, y nedover. Bakkant = y 0 (mot bakveggen).
"""
import os, sys, csv, json
import pcbnew
from pcbnew import VECTOR2I_MM as MM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ki_pultforsterker_main.kicad_pcb")
FP = "/usr/share/kicad/footprints"
BW, BH = 150.0, 100.0          # kortstørrelse

# ---------------------------------------------------------------- deler
# (ref, lib, footprint, value, lcsc, x, y, rot, beskrivelse)
P = []
def part(ref, lib, fp, value, lcsc, x, y, rot=0, desc=""):
    P.append(dict(ref=ref, lib=lib, fp=fp, value=value, lcsc=lcsc, x=x, y=y, rot=rot, desc=desc))

SO, SMD, R_, C_, TO = "Package_SO", "Package_SO", "Resistor_SMD", "Capacitor_SMD", "Package_TO_SOT_SMD"
R0603, C0603, C0805, C1206, C1210 = "R_0603_1608Metric", "C_0603_1608Metric", "C_0805_2012Metric", "C_1206_3216Metric", "C_1210_3225Metric"
R1206 = "R_1206_3216Metric"

# --- bakkant: kontakter (y ~ 6) ---
part("J1", "TerminalBlock", "TerminalBlock_bornier-2_P5.08mm", "24V IN", "C8465", 14, 6, 0, "24 V inn fra DC-099 via KCD1 (skruterminal 5,08)")
part("F1", "Fuse", "Fuseholder_Clip-5x20mm_Keystone_3512P_Inline_P23.62x7.27mm_D1.02x2.41x1.02x1.57mm_Horizontal", "5A 5x20", "C70283", 38, 7, 0, "Sikringsholder 5x20 (klips, THT) + sikring 5 A")
part("D1", "Diode_SMD", "D_SMB", "SMBJ33A", "C118215", 56, 15, 90, "TVS 33 V")
part("C1", "Capacitor_THT", "CP_Radial_D13.0mm_P5.00mm", "2200u/35V", "C5779", 70, 14, 0, "Bulk elektrolytt (THT, loddes selv)")
part("J2", "TerminalBlock", "TerminalBlock_bornier-2_P5.08mm", "SPK L", "C8465", 108, 6, 0, "Høyttaler venstre + / -")
part("J3", "TerminalBlock", "TerminalBlock_bornier-2_P5.08mm", "SPK R", "C8465", 134, 6, 0, "Høyttaler høyre + / -")
part("J4", "Connector_JST", "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical", "AUX", "C144395", 122, 6, 0, "AUX fra PJ392: L, R, GND")

# --- buck TPS54560 (x 8–48, y 18–48) ---
part("U1", SO, "HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm_ThermalVias", "TPS54560BDDA", "C83010", 22, 30, 0, "Buck 60 V 5 A")
part("C2", C_, C1210, "4.7u/50V", "C76838", 12, 22, 0, "Cin"); part("C3", C_, C1210, "4.7u/50V", "C76838", 12, 26, 0, "Cin")
part("C4", C_, C0603, "100n/50V", "C14663", 12, 30, 0, "Cin HF")
part("C5", C_, C0603, "100n", "C14663", 30, 24, 90, "Boot")
part("R1", R_, R0603, "150k", "C25800", 14, 36, 0, "EN divider"); part("R2", R_, R0603, "51k", "C23184", 14, 39, 0, "EN divider")
part("R3", R_, R0603, "243k", "C22999", 14, 42, 0, "RT 400 kHz")
part("R4", R_, R0603, "53.6k", "C25798", 30, 36, 0, "FB top"); part("R5", R_, R0603, "10.2k", "C25744", 30, 39, 0, "FB bottom")
part("R6", R_, R0603, "13.3k", "C22791", 30, 42, 0, "Comp R"); part("C6", C_, C0603, "3.3n", "C1588", 30, 45, 0, "Comp C"); part("C7", C_, C0603, "47p", "C1671", 34, 45, 0, "Comp Cp")
part("L1", "Inductor_SMD", "L_Bourns_SRP1245A", "10uH 6A", "C135446", 44, 30, 0, "Buck-spole 10 µH")
part("D2", "Diode_SMD", "D_SMB", "SS56", "C32569", 34, 20, 0, "Catch-diode 60 V 5 A")
part("C8", C_, C1210, "47u/10V", "C45783", 54, 24, 90, "Cout"); part("C9", C_, C1210, "47u/10V", "C45783", 54, 29, 90, "Cout"); part("C10", C_, C1210, "47u/10V", "C45783", 54, 34, 90, "Cout")
part("C11", C_, C0603, "100n", "C14663", 54, 39, 90, "Cout HF")

# --- 3,3 V og -5 V (x 8–48, y 52–64) ---
part("U2", TO, "SOT-223-3_TabPin2", "AMS1117-3.3", "C6186", 20, 56, 0, "LDO 3,3 V")
part("C12", C_, C0805, "10u", "C15850", 14, 56, 90, "LDO in"); part("C13", C_, C0805, "10u", "C15850", 26, 56, 90, "LDO out"); part("C14", C_, C0603, "100n", "C14663", 28, 61, 0, "LDO out HF")
part("U3", SO, "SOIC-8_3.9x4.9mm_P1.27mm", "ICL7660", "C7439", 40, 56, 0, "Ladepumpe -5 V")
part("C15", C_, C0805, "10u", "C15850", 34, 62, 0, "Flykondensator"); part("C16", C_, C0805, "10u", "C15850", 46, 62, 0, "-5 V ut")

# --- Pi-header (venstre kant) ---
part("J5", "Connector_PinHeader_2.54mm", "PinHeader_2x20_P2.54mm_Vertical", "RPi 40-pin", "C50982", 7, 40, 0, "Raspberry Pi 40-pin (flatkabel)")
part("J6", "TerminalBlock", "TerminalBlock_bornier-2_P5.08mm", "5V -> PI", "C8465", 62, 94, 0, "5 V til Pi 4 (18 AWG til header pinne 2/6)")

# --- DAC PCM5102A (x 55–75, y 55–70) ---
part("U4", SO, "TSSOP-20_4.4x6.5mm_P0.65mm", "PCM5102APW", "C107506", 66, 62, 0, "I2S-DAC")
part("C17", C_, C0603, "2.2u", "C23630", 58, 56, 0, "CAPP-CAPM"); part("C18", C_, C0603, "2.2u", "C23630", 58, 59, 0, "VNEG")
part("C19", C_, C0603, "2.2u", "C23630", 74, 56, 0, "LDOO"); part("C20", C_, C0603, "100n", "C14663", 74, 59, 0, "DVDD"); part("C21", C_, C0603, "100n", "C14663", 58, 65, 0, "AVDD/CPVDD")
part("C22", C_, C0805, "10u", "C15850", 74, 65, 0, "3V3 bulk DAC")
part("R7", R_, R0603, "10k", "C25804", 74, 69, 0, "XSMT pull-up")
part("R8", R_, R0603, "100", "C22775", 62, 70, 0, "DAC L serie"); part("R9", R_, R0603, "100", "C22775", 66, 70, 0, "DAC R serie")
part("C23", C_, C0603, "2.2n", "C1594", 62, 73, 0, "DAC L LP"); part("C24", C_, C0603, "2.2n", "C1594", 66, 73, 0, "DAC R LP")

# --- relé + volum (x 82–118, y 52–78) ---
part("K1", "Relay_THT", "Relay_DPDT_Omron_G6K-2P-Y", "G6K-2P-Y 5VDC", "C113107", 86, 58, 0, "Signalrelé DAC/AUX (DPDT)")
part("Q1", TO, "SOT-23-3", "AO3400A", "C20917", 96, 54, 0, "Relédriver"); part("R10", R_, R0603, "100", "C22775", 96, 58, 0, "Gate"); part("R11", R_, R0603, "100k", "C25803", 96, 61, 0, "Gate pulldown")
part("D3", "Diode_SMD", "D_SOD-123", "1N4148W", "C81598", 92, 50, 0, "Flyback relé")
part("C25", C_, C1206, "10u", "C13585", 104, 56, 90, "Kobling L"); part("C26", C_, C1206, "10u", "C13585", 104, 62, 90, "Kobling R")
part("R12", R_, R0603, "100k", "C25803", 108, 56, 90, "Bias L"); part("R13", R_, R0603, "100k", "C25803", 108, 62, 90, "Bias R")
part("U5", SO, "SOIC-16W_7.5x10.3mm_P1.27mm", "PGA2311UA", "C168915", 118, 62, 90, "Volumkontroll ±5 V")
part("C27", C_, C0603, "100n", "C14663", 112, 70, 0, "VD+"); part("C28", C_, C0603, "100n", "C14663", 124, 70, 0, "VA+"); part("C29", C_, C0603, "100n", "C14663", 124, 73, 0, "VA-")
part("C30", C_, C0805, "10u", "C15850", 128, 70, 0, "VA+ bulk"); part("C31", C_, C0805, "10u", "C15850", 128, 74, 0, "VA- bulk")
part("R14", R_, R0603, "10k", "C25804", 112, 73, 0, "MUTE pull-up")

# --- forsterker TPA3116D2 (x 60–135, y 18–48) ---
part("U6", SO, "HTSSOP-32-1EP_6.1x11mm_P0.65mm_EP5.2x11mm_Mask4.11x4.36mm_ThermalVias", "TPA3116D2DAD", "C101108", 84, 34, 0, "Klasse D 2x50 W")
part("C32", C_, C0805, "220n/50V", "C45790", 100, 39, 90, "BSNL"); part("C33", C_, C0805, "220n/50V", "C45790", 100, 35.5, 90, "BSPL")
part("C34", C_, C0805, "220n/50V", "C45790", 100, 32, 90, "BSNR"); part("C35", C_, C0805, "220n/50V", "C45790", 100, 28.5, 90, "BSPR")
part("C36", C_, C0603, "100n/50V", "C14663", 92, 27, 0, "PVCC HF"); part("C37", C_, C0805, "1u/50V", "C28323", 96, 27, 0, "PVCC"); part("C38", C_, C0603, "100n/50V", "C14663", 92, 41, 0, "PVCC HF"); part("C39", C_, C0805, "1u/50V", "C28323", 96, 41, 0, "PVCC")
part("C40", "Capacitor_SMD", "CP_Elec_10x10.5", "220u/35V", "C134754", 86, 17, 0, "PVCC bulk"); part("C41", "Capacitor_SMD", "CP_Elec_10x10.5", "220u/35V", "C134754", 100, 17, 0, "PVCC bulk")
part("C42", C_, C0805, "1u/50V", "C28323", 73, 40, 0, "AVCC"); part("C43", C_, C0805, "10u/50V", "C96446", 73, 42.6, 0, "AVCC bulk")
part("C44", C_, C0805, "1u", "C28323", 73, 37.4, 0, "GVDD")
part("R15", R_, R0603, "100k", "C25803", 67, 27, 0, "GAIN top"); part("R16", R_, R0603, "20k", "C25765", 67, 29.6, 0, "GAIN bottom (26 dB)")
part("R17", R_, R0603, "0", "C21189", 67, 32.2, 0, "PLIMIT -> GVDD (ingen begrensning)"); part("R18", R_, R0603, "DNP", "", 67, 34.8, 0, "PLIMIT til GND (valgfri)")
part("R19", R_, R0603, "1k", "C21190", 67, 37.4, 0, "SDZ serie"); part("R20", R_, R0603, "100k", "C25803", 67, 40, 0, "SDZ pulldown")
part("C45", C_, C0805, "1u", "C28323", 73, 32.2, 0, "LINP kobling"); part("C46", C_, C0805, "1u", "C28323", 73, 34.8, 0, "LINN til GND")
part("C47", C_, C0805, "1u", "C28323", 73, 27, 0, "RINP kobling"); part("C48", C_, C0805, "1u", "C28323", 73, 29.6, 0, "RINN til GND")
part("L2", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 118, 43, 0, "Utgangsfilter OUTNL"); part("L3", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 118, 29.5, 0, "Utgangsfilter OUTPL")
part("L4", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 132, 29.5, 0, "Utgangsfilter OUTNR"); part("L5", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 132, 43, 0, "Utgangsfilter OUTPR")
part("C49", C_, C1206, "680n/50V", "C13594", 108, 14, 90, "Filter OUTNL"); part("C50", C_, C1206, "680n/50V", "C13594", 112, 14, 90, "Filter OUTPL")
part("C51", C_, C1206, "680n/50V", "C13594", 124, 14, 90, "Filter OUTNR"); part("C52", C_, C1206, "680n/50V", "C13594", 128, 14, 90, "Filter OUTPR")
part("R21", R_, R1206, "18", "C17949", 105, 39, 0, "Snubber NL"); part("C53", C_, C0603, "330p/50V", "C1664", 109.5, 39, 0, "Snubber NL")
part("R22", R_, R1206, "18", "C17949", 105, 35.5, 0, "Snubber PL"); part("C54", C_, C0603, "330p/50V", "C1664", 109.5, 35.5, 0, "Snubber PL")
part("R23", R_, R1206, "18", "C17949", 105, 32, 0, "Snubber NR"); part("C55", C_, C0603, "330p/50V", "C1664", 109.5, 32, 0, "Snubber NR")
part("R24", R_, R1206, "18", "C17949", 105, 28.5, 0, "Snubber PR"); part("C56", C_, C0603, "330p/50V", "C1664", 109.5, 28.5, 0, "Snubber PR")

# --- front: kontakter (y ~ 94) og LED-drivere ---
part("J7", "Connector_JST", "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "KNAPPER", "C144397", 24, 94, 0, "AIR BT AUX USB PWR GND")
part("J8", "Connector_JST", "JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical", "ENCODER", "C144396", 44, 94, 0, "CLK DT SW 3V3 GND")
part("J9", "Connector_JST", "JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical", "OLED", "C144396", 84, 94, 0, "3V3 GND SDA SCL RES")
part("J10", "Connector_JST", "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "LED-RINGER", "C144397", 118, 94, 0, "5V AIR BT AUX USB PWR (-)")
for i, (nm, x) in enumerate([("AIR", 100), ("BT", 108), ("AUX", 116), ("USB", 124), ("PWR", 132)]):
    part(f"Q{i+2}", TO, "SOT-23-3", "AO3400A", "C20917", x, 84, 0, f"LED-ring {nm}")
    part(f"R{25+i}", R_, R0603, "100", "C22775", x, 80, 0, f"Gate {nm}"); part(f"R{30+i}", R_, R0603, "100k", "C25803", x - 3, 80, 90, f"Pulldown {nm}")
for i, x in enumerate([24, 28, 32, 36, 40]):
    part(f"R{35+i}", R_, R0603, "10k", "C25804", x, 81, 90, "Pull-up knapp"); part(f"C{57+i}", C_, C0603, "100n", "C14663", x, 85, 90, "Debounce knapp")
for i, x in enumerate([44, 48, 52]):
    part(f"R{40+i}", R_, R0603, "10k", "C25804", x, 81, 90, "Pull-up encoder"); part(f"C{62+i}", C_, C0603, "100n", "C14663", x, 85, 90, "Debounce encoder")
part("R43", R_, R0603, "4.7k", "C23162", 80, 86, 0, "I2C pull-up SDA"); part("R44", R_, R0603, "4.7k", "C23162", 80, 89, 0, "I2C pull-up SCL")
part("C65", C_, C0603, "100n", "C14663", 88, 86, 0, "3V3 ved OLED")
for i, (x, y) in enumerate([(4, 4), (146, 4), (4, 96), (146, 96)]):
    part(f"H{i+1}", "MountingHole", "MountingHole_3.2mm_M3", "M3", "", x, y, 0, "Festehull")

# ---------------------------------------------------------------- netliste
N = {}
def net(name, *pins):
    N.setdefault(name, []).extend(pins)

GND = "GND"
# 24 V inn
net("24V_IN", ("J1", 1), ("F1", 1)); net(GND, ("J1", 2))
net("VIN24", ("F1", 2), ("D1", 1), ("C1", 1), ("C2", 1), ("C3", 1), ("C4", 1), ("U1", 2), ("R1", 1),
    ("C36", 1), ("C37", 1), ("C38", 1), ("C39", 1), ("C40", 1), ("C41", 1), ("U6", 18), ("U6", 19), ("U6", 31), ("U6", 32), ("U6", 17), ("C42", 1), ("C43", 1))
net(GND, ("D1", 2), ("C1", 2), ("C2", 2), ("C3", 2), ("C4", 2), ("U1", 7), ("U1", 9), ("R2", 2), ("R3", 2), ("R5", 2), ("C6", 2), ("C7", 2), ("D2", 2),
    ("C8", 2), ("C9", 2), ("C10", 2), ("C11", 2))
# buck
net("BUCK_BOOT", ("U1", 1), ("C5", 1)); net("BUCK_SW", ("U1", 8), ("C5", 2), ("L1", 1), ("D2", 1))
net("BUCK_EN", ("U1", 3), ("R1", 2), ("R2", 1)); net("BUCK_RT", ("U1", 4), ("R3", 1))
net("BUCK_FB", ("U1", 5), ("R4", 2), ("R5", 1)); net("BUCK_COMP", ("U1", 6), ("R6", 1), ("C7", 1)); net("BUCK_COMPC", ("R6", 2), ("C6", 1))
net("5V", ("L1", 2), ("R4", 1), ("C8", 1), ("C9", 1), ("C10", 1), ("C11", 1), ("U2", 3), ("C12", 1), ("U3", 8), ("J6", 1), ("J5", 2), ("J5", 4),
    ("K1", 1), ("D3", 1), ("U5", 4), ("U5", 12), ("U5", 1), ("C27", 1), ("C28", 1), ("C30", 1), ("R14", 1), ("J10", 1))
# 3,3 V
net(GND, ("U2", 1), ("C12", 2), ("C13", 2), ("C14", 2))
net("3V3", ("U2", 2), ("C13", 1), ("C14", 1), ("U4", 1), ("U4", 8), ("U4", 20), ("C20", 1), ("C21", 1), ("C22", 1), ("R7", 1),
    ("J8", 4), ("J9", 1), ("R43", 1), ("R44", 1), ("C65", 1), *[(f"R{35+i}", 1) for i in range(5)], *[(f"R{40+i}", 1) for i in range(3)])
# -5 V
net(GND, ("U3", 3), ("C16", 2)); net("CP_PLUS", ("U3", 2), ("C15", 1)); net("CP_MINUS", ("U3", 4), ("C15", 2))
net("VNEG", ("U3", 5), ("C16", 1), ("U5", 13), ("C29", 1), ("C31", 1))
# Pi header GND + signaler (BCM -> fysisk pinne)
for p in (6, 9, 14, 20, 25, 30, 34, 39):
    net(GND, ("J5", p))
net("SDA", ("J5", 3), ("J9", 3), ("R43", 2)); net("SCL", ("J5", 5), ("J9", 4), ("R44", 2)); net("OLED_RES", ("J5", 7), ("J9", 5))
net("I2S_BCK", ("J5", 12), ("U4", 13)); net("I2S_LRCK", ("J5", 35), ("U4", 15)); net("I2S_DIN", ("J5", 40), ("U4", 14))
net("BTN_AIR", ("J5", 29), ("J7", 1), ("R35", 2), ("C57", 1)); net("BTN_BT", ("J5", 31), ("J7", 2), ("R36", 2), ("C58", 1))
net("BTN_AUX", ("J5", 8), ("J7", 3), ("R37", 2), ("C59", 1)); net("BTN_USB", ("J5", 10), ("J7", 4), ("R38", 2), ("C60", 1))
net("BTN_PWR", ("J5", 36), ("J7", 5), ("R39", 2), ("C61", 1)); net(GND, ("J7", 6), *[(f"C{57+i}", 2) for i in range(5)])
net("ENC_CLK", ("J5", 16), ("J8", 1), ("R40", 2), ("C62", 1)); net("ENC_DT", ("J5", 18), ("J8", 2), ("R41", 2), ("C63", 1)); net("ENC_SW", ("J5", 22), ("J8", 3), ("R42", 2), ("C64", 1))
net(GND, ("J8", 5), ("C62", 2), ("C63", 2), ("C64", 2), ("J9", 2), ("C65", 2))
net("SPI_MOSI", ("J5", 19), ("U5", 3)); net("SPI_SCLK", ("J5", 23), ("U5", 6)); net("SPI_CS", ("J5", 24), ("U5", 2))
net("LED_AIR_G", ("J5", 26), ("R25", 1)); net("LED_BT_G", ("J5", 21), ("R26", 1)); net("LED_AUX_G", ("J5", 11), ("R27", 1)); net("LED_USB_G", ("J5", 38), ("R28", 1)); net("LED_PWR_G", ("J5", 32), ("R29", 1))
net("RLY_G", ("J5", 15), ("R10", 1)); net("AMP_SD_G", ("J5", 13), ("R19", 1)); net("DAC_XSMT", ("J5", 37), ("U4", 17), ("R7", 2))
# LED-drivere
for i, nm in enumerate(["AIR", "BT", "AUX", "USB", "PWR"]):
    q, rg, rp = f"Q{i+2}", f"R{25+i}", f"R{30+i}"
    net(f"LED_{nm}_GATE", (q, 1), (rg, 2), (rp, 1)); net(GND, (q, 2), (rp, 2)); net(f"LED_{nm}_K", (q, 3), ("J10", i + 2))
# relé
net("RLY_GATE", ("Q1", 1), ("R10", 2), ("R11", 1)); net(GND, ("Q1", 2), ("R11", 2)); net("RLY_LOW", ("Q1", 3), ("K1", 8), ("D3", 2))
# DAC
net("DAC_CAPP", ("U4", 2), ("C17", 1)); net("DAC_CAPM", ("U4", 4), ("C17", 2)); net("DAC_VNEG", ("U4", 5), ("C18", 1)); net("DAC_LDOO", ("U4", 18), ("C19", 1))
net(GND, ("U4", 3), ("U4", 9), ("U4", 10), ("U4", 11), ("U4", 12), ("U4", 16), ("U4", 19), ("C18", 2), ("C19", 2), ("C20", 2), ("C21", 2), ("C22", 2), ("C23", 2), ("C24", 2))
net("DAC_L", ("U4", 6), ("R8", 1)); net("DAC_R", ("U4", 7), ("R9", 1))
net("DAC_L_F", ("R8", 2), ("C23", 1), ("K1", 2)); net("DAC_R_F", ("R9", 2), ("C24", 1), ("K1", 7))
net("AUX_L", ("J4", 1), ("K1", 4)); net("AUX_R", ("J4", 2), ("K1", 5)); net(GND, ("J4", 3))
net("SEL_L", ("K1", 3), ("C25", 1)); net("SEL_R", ("K1", 6), ("C26", 1))
net("VOL_INL", ("C25", 2), ("R12", 1), ("U5", 16)); net("VOL_INR", ("C26", 2), ("R13", 1), ("U5", 9))
net(GND, ("R12", 2), ("R13", 2), ("U5", 5), ("U5", 10), ("U5", 15), ("C27", 2), ("C28", 2), ("C29", 2), ("C30", 2), ("C31", 2))
net("PGA_MUTE", ("U5", 8), ("R14", 2))
net("VOL_OUTL", ("U5", 14), ("C45", 1)); net("VOL_OUTR", ("U5", 11), ("C47", 1))
# forsterker
net("AMP_LINP", ("C45", 2), ("U6", 10)); net("AMP_LINN", ("C46", 1), ("U6", 11)); net("AMP_RINP", ("C47", 2), ("U6", 4)); net("AMP_RINN", ("C48", 1), ("U6", 5))
net(GND, ("C46", 2), ("C48", 2), ("U6", 1), ("U6", 9), ("U6", 12), ("U6", 13), ("U6", 14), ("U6", 15), ("U6", 22), ("U6", 25), ("U6", 28), ("U6", 33),
    ("C36", 2), ("C37", 2), ("C38", 2), ("C39", 2), ("C40", 2), ("C41", 2), ("C42", 2), ("C43", 2), ("C44", 2), ("R16", 2), ("R18", 2), ("R20", 2))
net("GVDD", ("U6", 7), ("C44", 1), ("R15", 1), ("R17", 1)); net("AMP_GAIN", ("U6", 8), ("R15", 2), ("R16", 1)); net("AMP_PLIMIT", ("U6", 6), ("R17", 2), ("R18", 1))
net("AMP_SDZ", ("U6", 2), ("R19", 2), ("R20", 1))
net("BSNL", ("U6", 20), ("C32", 1)); net("BSPL", ("U6", 24), ("C33", 1)); net("BSNR", ("U6", 26), ("C34", 1)); net("BSPR", ("U6", 30), ("C35", 1))
net("OUTNL", ("U6", 21), ("C32", 2), ("L2", 1), ("R21", 1)); net("OUTPL", ("U6", 23), ("C33", 2), ("L3", 1), ("R22", 1))
net("OUTNR", ("U6", 27), ("C34", 2), ("L4", 1), ("R23", 1)); net("OUTPR", ("U6", 29), ("C35", 2), ("L5", 1), ("R24", 1))
net("SNUB_NL", ("R21", 2), ("C53", 1)); net("SNUB_PL", ("R22", 2), ("C54", 1)); net("SNUB_NR", ("R23", 2), ("C55", 1)); net("SNUB_PR", ("R24", 2), ("C56", 1))
net(GND, ("C53", 2), ("C54", 2), ("C55", 2), ("C56", 2), ("C49", 2), ("C50", 2), ("C51", 2), ("C52", 2))
net("SPK_LN", ("L2", 2), ("C49", 1), ("J2", 2)); net("SPK_LP", ("L3", 2), ("C50", 1), ("J2", 1))
net("SPK_RN", ("L4", 2), ("C51", 1), ("J3", 2)); net("SPK_RP", ("L5", 2), ("C52", 1), ("J3", 1))
net(GND, ("J6", 2))

POWER_NETS = {"VIN24": 2.0, "24V_IN": 2.0, "5V": 1.2, "BUCK_SW": 1.5, "OUTNL": 1.5, "OUTPL": 1.5, "OUTNR": 1.5, "OUTPR": 1.5,
              "SPK_LN": 1.5, "SPK_LP": 1.5, "SPK_RN": 1.5, "SPK_RP": 1.5, "3V3": 0.5, "VNEG": 0.4}

# ---------------------------------------------------------------- bygg kortet
def build():
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = pcbnew.FromMM(0.2); ds.m_ViasMinSize = pcbnew.FromMM(0.5); ds.m_MinClearance = pcbnew.FromMM(0.15)
    # omriss
    for (x0, y0, x1, y1) in [(0, 0, BW, 0), (BW, 0, BW, BH), (BW, BH, 0, BH), (0, BH, 0, 0)]:
        s = pcbnew.PCB_SHAPE(board); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(MM(x0, y0)); s.SetEnd(MM(x1, y1))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(pcbnew.FromMM(0.1)); board.Add(s)
    # nett
    nets = {}
    for name in sorted(N):
        ni = pcbnew.NETINFO_ITEM(board, name); board.Add(ni); nets[name] = ni
    # deler
    fps = {}
    for p in P:
        fp = pcbnew.FootprintLoad(os.path.join(FP, p["lib"] + ".pretty"), p["fp"])
        if fp is None:
            raise SystemExit(f"Fant ikke footprint {p['lib']}:{p['fp']}")
        fp.SetReference(p["ref"]); fp.SetValue(p["value"])
        fp.SetPosition(MM(p["x"], p["y"])); fp.SetOrientationDegrees(p["rot"])
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(0.8), pcbnew.FromMM(0.8))); fp.Reference().SetTextThickness(pcbnew.FromMM(0.12))
        fp.Value().SetVisible(False)
        board.Add(fp); fps[p["ref"]] = fp
    # pad -> nett
    for name, pins in N.items():
        for ref, pad in pins:
            fp = fps[ref]; found = False
            for pd in fp.Pads():
                if pd.GetNumber() == str(pad):
                    pd.SetNet(nets[name]); found = True
            if not found:
                raise SystemExit(f"{ref} har ingen pad {pad}")
    # ubrukte pads sjekk: alle pads på IC-er skal ha nett (unntatt NC)
    nc_ok = {("U3", "1"), ("U3", "6"), ("U3", "7"), ("U5", "7"), ("U6", "3"), ("U6", "16"), ("J5", "1"), ("J5", "17"), ("J5", "27"), ("J5", "28"), ("U1", "0")}
    for ref in ("U1", "U6"):   # termiske via-pads uten nummer -> GND
        for pd in fps[ref].Pads():
            if pd.GetNumber() == "":
                pd.SetNet(nets[GND])
    for ref, fp in fps.items():
        for pd in fp.Pads():
            if pd.GetNetCode() <= 0 and not ref.startswith("H") and (ref, pd.GetNumber()) not in nc_ok and ref.startswith(("U", "K", "Q")):
                print("ADVARSEL: pad uten nett", ref, pd.GetNumber(), pd.GetPadName())
    # GND-soner på begge lag
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(board); z.SetLayer(layer); z.SetNet(nets[GND]); z.SetIsFilled(False)
        z.SetLocalClearance(pcbnew.FromMM(0.25)); z.SetMinThickness(pcbnew.FromMM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL); z.SetThermalReliefGap(pcbnew.FromMM(0.4)); z.SetThermalReliefSpokeWidth(pcbnew.FromMM(0.5))
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in [(1, 1), (BW - 1, 1), (BW - 1, BH - 1), (1, BH - 1)]:
            ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        board.Add(z)
    # nettklasser (bredde brukes av Freerouting via DSN)
    try:
        ncs = ds.m_NetSettings.m_NetClasses
        default = ds.m_NetSettings.m_DefaultNetClass
        default.SetTrackWidth(pcbnew.FromMM(0.3)); default.SetClearance(pcbnew.FromMM(0.2)); default.SetViaDiameter(pcbnew.FromMM(0.8)); default.SetViaDrill(pcbnew.FromMM(0.4))
        for cname, w in [("Power", 2.0), ("Power5V", 1.2), ("Out", 1.5), ("Mid", 0.5)]:
            nc = pcbnew.NETCLASS(cname); nc.SetTrackWidth(pcbnew.FromMM(w)); nc.SetClearance(pcbnew.FromMM(0.3 if w >= 1.2 else 0.2))
            nc.SetViaDiameter(pcbnew.FromMM(1.2 if w >= 1.2 else 0.8)); nc.SetViaDrill(pcbnew.FromMM(0.6 if w >= 1.2 else 0.4))
            ncs[cname] = nc
        for n, w in POWER_NETS.items():
            cname = "Power" if w >= 2.0 else ("Out" if w >= 1.5 else ("Power5V" if w >= 1.2 else "Mid"))
            ds.m_NetSettings.m_NetClassPatternAssignments.append(pcbnew.NETCLASS_PATTERN_PAIR(n, cname)) if hasattr(pcbnew, "NETCLASS_PATTERN_PAIR") else None
    except Exception as e:
        print("Nettklasser:", e)
    # tekst
    t = pcbnew.PCB_TEXT(board); t.SetText("KI Pultforsterker  rev A  2026"); t.SetPosition(MM(75, 78)); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.5), pcbnew.FromMM(1.5))); board.Add(t)
    for txt, x, y in [("24V IN", 14, 12), ("SPK L", 108, 12), ("SPK R", 134, 12), ("AUX", 122, 12), ("Pi 40", 14, 90), ("KNAPPER", 24, 98.5), ("ENC", 44, 98.5), ("5V PI", 62, 98.5), ("OLED", 84, 98.5), ("LED", 118, 98.5)]:
        t = pcbnew.PCB_TEXT(board); t.SetText(txt); t.SetPosition(MM(x, y)); t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.0), pcbnew.FromMM(1.0))); board.Add(t)
    pcbnew.SaveBoard(OUT, board)
    print("Lagret", OUT, "deler:", len(P), "nett:", len(N))
    with open(os.path.join(HERE, "bom.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["Designator", "Value", "Footprint", "LCSC", "Beskrivelse"])
        for p in P:
            if not p["ref"].startswith("H"):
                w.writerow([p["ref"], p["value"], p["fp"], p["lcsc"], p["desc"]])
    with open(os.path.join(HERE, "netlist.json"), "w") as fh:
        json.dump(N, fh, ensure_ascii=False, indent=1)
    return board


if __name__ == "__main__":
    build()
