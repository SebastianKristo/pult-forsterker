#!/usr/bin/env python3
"""Pultforsterker – hovedkort (rev. B). Bygger kicad_pcb med pcbnew-API-et (KiCad 7). Kortet er 180 × 100 mm.

Rev B (alt digitalt gjennom Pi-en, ingen analog AUX-vei):
  * AUX 1 -> PCM1808 I2S-ADC (master 256 fs fra 12,288 MHz-oscillator, Pi er I2S-slave). AUX 2 -> PCM2900C USB-kodek (kabel til en
    USB-port på Pi-en). Begge mikses i CamillaDSP med hvert sitt volum. Reléet for DAC/AUX er borte.
  * USB-delingsswitch: FE1.1s 4-ports hub + TS3USB221 2:1-mux. 2 × USB-C inn fra PC-ene (panelkabler), 4 × USB-A ut i høyre kant.
  * «Smart relé»: SRD-05VDC bryter 24 V til forsterkeren, og en P-MOSFET bryter 5 V_SW (LED-ringer, PGA, ADC, DAC, OLED/TFT).
    Pi-en, huben og I/O-ekspanderen har strøm hele tiden. Styres av Pi GPIO 27 (fra HA/Homey) + egen knapp bak (GPIO 15).
  * MCP23017 I2C-ekspander tar frontknappene, LED-ringene og mux-valget, så Pi-en har pinner til SPI-TFT (ILI9341/ST7789V) med touch.
  * LM2662 i stedet for ICL7660 (−5 V tåler 10–12 mA, 150 kHz), ingen loddepasta under TPA3116 (DAD = kjøleflate på toppen),
    ferritt + 10 µF foran PGA2311 VA+.

GPIO-kart (BCM): I2C 2/3 (OLED, MCP23017) · 4 OLED RES · 14 MCP INT · 15 knapp bak · 17 touch IRQ · I2S 18 BCK, 19 LRCK, 21 DAC, 20 ADC
  · 27 strømrelé · 22 TPA SDZ · 23/24/25 encoder · SPI0 10/9/11, CE0 8 PGA2311, CE1 7 TFT · 5 TFT DC · 6 TFT RST · 13 TFT BL (PWM)
  · 16 touch CS · 12 POWER-ring (PWM) · 26 DAC XSMT.   MCP23017 0x20: GPA0-4 knapper AIR/BT/AUX/USB/PWR, GPB0-3 LED-ringer, GPB4 USB-mux.

Koordinater i mm, origo øverst til venstre på kortet, y nedover. Bakkant = y 0 (mot bakveggen).
"""
import os, sys, csv, json
import pcbnew
from pcbnew import VECTOR2I_MM as MM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "ki_pultforsterker_main.kicad_pcb")
FP = "/usr/share/kicad/footprints"
BW, BH = 180.0, 100.0          # kortstørrelse (rev B: 30 mm bredere, USB-blokken til høyre)

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
part("D1", "Diode_SMD", "D_SMB", "SMBJ33A", "C118215", 50, 14, 0, "TVS 33 V")
part("C1", "Capacitor_THT", "CP_Radial_D13.0mm_P5.00mm", "2200u/35V", "C5779", 94, 7, 0, "Bulk elektrolytt (THT, loddes selv)")
part("J2", "TerminalBlock", "TerminalBlock_bornier-2_P5.08mm", "SPK L", "C8465", 108, 6, 0, "Høyttaler venstre + / -")
part("J3", "TerminalBlock", "TerminalBlock_bornier-2_P5.08mm", "SPK R", "C8465", 134, 6, 0, "Høyttaler høyre + / -")

# --- strømrelé (24 V til forsterker) + P-MOSFET (5 V_SW) – «smart relé» styrt av GPIO 27 ---
part("K1", "Relay_THT", "Relay_SPDT_SANYOU_SRD_Series_Form_C", "SRD-05VDC-SL-C", "C35449", 60, 20, 0, "Relé 10 A: bryter 24 V til forsterkeren (1-2 spole, 4 COM, 5 NO)")
part("Q7", TO, "SOT-23-3", "AO3400A", "C20917", 60, 34, 0, "Relédriver + styrer Q8"); part("D4", "Diode_SMD", "D_SOD-123", "1N4148W", "C81598", 66, 34, 0, "Flyback relé")
part("R52", R_, R0603, "100", "C22775", 60, 38, 0, "Gate Q7"); part("R53", R_, R0603, "100k", "C25803", 64, 38, 0, "Gate pulldown Q7")
part("Q8", TO, "SOT-23-3", "AO3401A", "C15127", 62, 42, 0, "P-MOSFET 5 V -> 5V_SW"); part("R54", R_, R0603, "10k", "C25804", 66, 42, 0, "Q8 gate fra Q7"); part("R55", R_, R0603, "100k", "C25803", 62, 46, 0, "Q8 gate pull-up")

# --- buck TPS54560 (x 8–48, y 18–48) ---
part("U1", SO, "HSOP-8-1EP_3.9x4.9mm_P1.27mm_EP2.3x2.3mm", "TPS54560BDDA", "C83010", 22, 30, 0, "Buck 60 V 5 A")
part("C2", C_, C1210, "4.7u/50V", "C76838", 12, 22, 0, "Cin"); part("C3", C_, C1210, "4.7u/50V", "C76838", 12, 26, 0, "Cin")
part("C4", C_, C0603, "100n/50V", "C14663", 12, 30, 0, "Cin HF")
part("C5", C_, C0603, "100n", "C14663", 30, 24, 90, "Boot")
part("R1", R_, R0603, "150k", "C25800", 14, 36, 0, "EN divider"); part("R2", R_, R0603, "51k", "C23184", 14, 39, 0, "EN divider")
part("R3", R_, R0603, "243k", "C22999", 14, 42, 0, "RT 400 kHz")
part("R4", R_, R0603, "53.6k", "C25798", 30, 36, 0, "FB top"); part("R5", R_, R0603, "10.2k", "C25744", 30, 39, 0, "FB bottom")
part("R6", R_, R0603, "13.3k", "C22791", 30, 42, 0, "Comp R"); part("C6", C_, C0603, "3.3n", "C1588", 30, 45, 0, "Comp C"); part("C7", C_, C0603, "47p", "C1671", 34, 45, 0, "Comp Cp")
part("L1", "Inductor_SMD", "L_Bourns_SRP1245A", "10uH 6A", "C135446", 44, 30, 0, "Buck-spole 10 µH")
part("D2", "Diode_SMD", "D_SMB", "SS56", "C32569", 34, 20, 0, "Catch-diode 60 V 5 A")
part("C8", C_, C1210, "47u/10V", "C45783", 54, 38, 90, "Cout"); part("C9", C_, C1210, "47u/10V", "C45783", 54, 42.5, 90, "Cout"); part("C10", C_, C1210, "47u/10V", "C45783", 54, 47, 90, "Cout")
part("C11", C_, C0603, "100n", "C14663", 54, 51, 90, "Cout HF")

# --- 3,3 V (alltid), -5 V, 3,3 V_SW (x 8–56, y 52–72) ---
part("U2", TO, "SOT-223-3_TabPin2", "AMS1117-3.3", "C6186", 20, 56, 0, "LDO 3,3 V (alltid på: MCP23017, pull-ups)")
part("C12", C_, C0805, "10u", "C15850", 14, 56, 90, "LDO in"); part("C13", C_, C0805, "10u", "C15850", 26, 56, 90, "LDO out"); part("C14", C_, C0603, "100n", "C14663", 28, 61, 0, "LDO out HF")
part("U3", SO, "SOIC-8_3.9x4.9mm_P1.27mm", "LM2662MX", "C129316", 40, 56, 0, "Ladepumpe -5 V, 150 kHz (FC til V+), 200 mA")
part("C15", C_, C0805, "10u", "C15850", 34, 62, 0, "Flykondensator"); part("C16", C_, C0805, "10u", "C15850", 46, 62, 0, "-5 V ut")
part("U9", TO, "SOT-223-3_TabPin2", "AMS1117-3.3", "C6186", 46, 68, 0, "LDO 3,3 V_SW (DAC, ADC, OLED/TFT) fra 5V_SW")
part("C75", C_, C0805, "10u", "C15850", 52, 66, 90, "LDO_SW in"); part("C76", C_, C0805, "10u", "C15850", 52, 70, 90, "LDO_SW out")

# --- Pi-header (venstre kant) + I2C-ekspander ---
part("J5", "Connector_PinHeader_2.54mm", "PinHeader_2x20_P2.54mm_Vertical", "RPi 40-pin", "C50982", 7, 40, 0, "Raspberry Pi 40-pin (flatkabel)")
part("J6", "TerminalBlock", "TerminalBlock_bornier-2_P5.08mm", "5V -> PI", "C8465", 59, 94, 0, "5 V til Pi 4 (18 AWG til header pinne 2/6)")
part("U12", SO, "SSOP-28_5.3x10.2mm_P0.65mm", "MCP23017-E/SS", "C506653", 28, 72, 0, "I2C I/O-ekspander 0x20: knapper, LED-ringer, USB-mux")
part("R56", R_, R0603, "10k", "C25804", 34, 78, 0, "MCP RESET pull-up"); part("C74", C_, C0603, "100n", "C14663", 38, 78, 0, "MCP VDD")
part("R43", R_, R0603, "4.7k", "C23162", 38, 70, 0, "I2C pull-up SDA"); part("R44", R_, R0603, "4.7k", "C23162", 38, 73, 0, "I2C pull-up SCL")

# --- DAC PCM5102A (x 55–75, y 55–70) ---
part("U4", SO, "TSSOP-20_4.4x6.5mm_P0.65mm", "PCM5102APW", "C107506", 66, 62, 0, "I2S-DAC")
part("C17", C_, C0603, "2.2u", "C23630", 58, 56, 0, "CAPP-CAPM"); part("C18", C_, C0603, "2.2u", "C23630", 58, 59, 0, "VNEG")
part("C19", C_, C0603, "2.2u", "C23630", 74, 56, 0, "LDOO"); part("C20", C_, C0603, "100n", "C14663", 74, 59, 0, "DVDD"); part("C21", C_, C0603, "100n", "C14663", 58, 65, 0, "AVDD/CPVDD")
part("C22", C_, C0805, "10u", "C15850", 74, 65, 0, "3V3 bulk DAC")
part("R7", R_, R0603, "10k", "C25804", 74, 69, 0, "XSMT pull-up")
part("R8", R_, R0603, "100", "C22775", 62, 70, 0, "DAC L serie"); part("R9", R_, R0603, "100", "C22775", 66, 70, 0, "DAC R serie")
part("C23", C_, C0603, "2.2n", "C1594", 62, 73, 0, "DAC L LP"); part("C24", C_, C0603, "2.2n", "C1594", 66, 73, 0, "DAC R LP")

# --- ADC PCM1808 (AUX 1) med 12,288 MHz-oscillator (x 80–106, y 50–78) ---
part("U10", SO, "TSSOP-14_4.4x5mm_P0.65mm", "PCM1808PW", "C7436", 94, 60, 0, "I2S-ADC AUX 1, master 256 fs (MD1=MD0=1, FMT=0)")
part("X1", "Oscillator", "Oscillator_SMD_Abracon_ASE-4Pin_3.2x2.5mm", "12.288MHz", "C437124", 100, 52, 0, "Oscillator 3,3 V -> SCKI (48 kHz)")
part("C77", C_, C0603, "100n", "C14663", 106, 57, 90, "Osc VDD")
part("C78", C_, C0805, "10u", "C15850", 86, 54, 90, "VREF"); part("C79", C_, C0603, "100n", "C14663", 86, 58, 90, "VREF HF")
part("C80", C_, C0805, "10u", "C15850", 86, 63, 90, "ADC VCC"); part("C81", C_, C0603, "100n", "C14663", 86, 67, 90, "ADC VCC HF"); part("C82", C_, C0603, "100n", "C14663", 102, 62, 90, "ADC VDD")
part("R57", R_, R0603, "10k", "C25804", 82, 72, 0, "AUX1 L deler"); part("R58", R_, R0603, "10k", "C25804", 82, 75, 0, "AUX1 L deler GND")
part("R59", R_, R0603, "10k", "C25804", 100, 72, 0, "AUX1 R deler"); part("R60", R_, R0603, "10k", "C25804", 100, 75, 0, "AUX1 R deler GND")
part("C83", C_, C0805, "4.7u", "C1779", 88, 72, 0, "AUX1 L kobling"); part("C84", C_, C0805, "4.7u", "C1779", 94, 72, 0, "AUX1 R kobling")
part("R61", R_, R0603, "1k", "C21190", 88, 75, 0, "AUX1 L serie"); part("R62", R_, R0603, "1k", "C21190", 94, 75, 0, "AUX1 R serie")
part("C85", C_, C0603, "1n", "C1588", 88, 78, 0, "AUX1 L LP"); part("C86", C_, C0603, "1n", "C1588", 94, 78, 0, "AUX1 R LP")

# --- volum PGA2311 (x 104–136, y 52–78) ---
part("C25", C_, C1206, "10u", "C13585", 104, 56, 90, "Kobling L"); part("C26", C_, C1206, "10u", "C13585", 104, 62, 90, "Kobling R")
part("R12", R_, R0603, "100k", "C25803", 108, 56, 90, "Bias L"); part("R13", R_, R0603, "100k", "C25803", 108, 62, 90, "Bias R")
part("U5", SO, "SOIC-16W_7.5x10.3mm_P1.27mm", "PGA2311UA", "C168915", 118, 62, 90, "Volumkontroll ±5 V")
part("C27", C_, C0603, "100n", "C14663", 112, 70, 0, "VD+"); part("C28", C_, C0603, "100n", "C14663", 124, 70, 0, "VA+"); part("C29", C_, C0603, "100n", "C14663", 124, 73, 0, "VA-")
part("C30", C_, C0805, "10u", "C15850", 128, 70, 0, "VA+ bulk"); part("C31", C_, C0805, "10u", "C15850", 128, 74, 0, "VA- bulk")
part("FB1", "Inductor_SMD", "L_0805_2012Metric", "600R@100MHz", "C18305", 132, 66, 0, "Ferritt 5V_SW -> PGA2311 VA+ (filter)")
part("R14", R_, R0603, "10k", "C25804", 108, 70, 0, "MUTE pull-up")

# --- forsterker TPA3116D2 (x 60–135, y 18–48) ---
part("U6", SO, "HTSSOP-32-1EP_6.1x11mm_P0.65mm_EP5.2x11mm_Mask4.11x4.36mm_ThermalVias", "TPA3116D2DAD", "C101108", 84, 34, 0, "Klasse D 2x50 W (kjøleflate på toppen – kjøleribbe!)")
part("C32", C_, C0805, "220n/50V", "C45790", 98, 36.9, 0, "BSNL"); part("C33", C_, C0805, "220n/50V", "C45790", 94, 34.3, 0, "BSPL")
part("C34", C_, C0805, "220n/50V", "C45790", 98, 33.0, 0, "BSNR"); part("C35", C_, C0805, "220n/50V", "C45790", 94, 30.4, 0, "BSPR")
part("C36", C_, C0603, "100n/50V", "C14663", 92, 27, 0, "PVCC HF"); part("C37", C_, C0805, "1u/50V", "C28323", 96, 27, 0, "PVCC"); part("C38", C_, C0603, "100n/50V", "C14663", 92, 41, 0, "PVCC HF"); part("C39", C_, C0805, "1u/50V", "C28323", 96, 41, 0, "PVCC")
part("C40", "Capacitor_SMD", "CP_Elec_10x10.5", "220u/35V", "C134754", 86, 20, 0, "PVCC bulk"); part("C41", "Capacitor_SMD", "CP_Elec_10x10.5", "220u/35V", "C134754", 100, 20, 0, "PVCC bulk")
part("C42", C_, C0805, "1u/50V", "C28323", 75.5, 43.2, 0, "AVCC"); part("C43", C_, C0805, "10u/50V", "C96446", 75.5, 45.8, 0, "AVCC bulk")
part("C44", C_, C0805, "1u", "C28323", 75.5, 40.6, 0, "GVDD")
part("R15", R_, R0603, "100k", "C25803", 71, 30.2, 0, "GAIN top"); part("R16", R_, R0603, "20k", "C25765", 71, 32.8, 0, "GAIN bottom (26 dB)")
part("R17", R_, R0603, "0", "C21189", 71, 35.4, 0, "PLIMIT -> GVDD (ingen begrensning)"); part("R18", R_, R0603, "DNP", "", 71, 38, 0, "PLIMIT til GND (valgfri)")
part("R19", R_, R0603, "1k", "C21190", 71, 40.6, 0, "SDZ serie"); part("R20", R_, R0603, "100k", "C25803", 71, 43.2, 0, "SDZ pulldown")
part("C45", C_, C0805, "1u", "C28323", 75.5, 35.4, 0, "LINP kobling"); part("C46", C_, C0805, "1u", "C28323", 75.5, 38, 0, "LINN til GND")
part("C47", C_, C0805, "1u", "C28323", 75.5, 30.2, 0, "RINP kobling"); part("C48", C_, C0805, "1u", "C28323", 75.5, 32.8, 0, "RINN til GND")
part("L2", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 118, 43, 0, "Utgangsfilter OUTNL"); part("L3", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 118, 29.5, 0, "Utgangsfilter OUTPL")
part("L4", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 132, 29.5, 0, "Utgangsfilter OUTNR"); part("L5", "Inductor_SMD", "L_12x12mm_H8mm", "10uH 7A", "C182272", 132, 43, 0, "Utgangsfilter OUTPR")
part("C49", C_, C1206, "680n/50V", "C13594", 108, 14, 90, "Filter OUTNL"); part("C50", C_, C1206, "680n/50V", "C13594", 112, 14, 90, "Filter OUTPL")
part("C51", C_, C1206, "680n/50V", "C13594", 124, 14, 90, "Filter OUTNR"); part("C52", C_, C1206, "680n/50V", "C13594", 128, 14, 90, "Filter OUTPR")
part("R21", R_, R1206, "18", "C17949", 105, 39, 0, "Snubber NL"); part("C53", C_, C0603, "330p/50V", "C1664", 109.5, 39, 0, "Snubber NL")
part("R22", R_, R1206, "18", "C17949", 105, 35.5, 0, "Snubber PL"); part("C54", C_, C0603, "330p/50V", "C1664", 109.5, 35.5, 0, "Snubber PL")
part("R23", R_, R1206, "18", "C17949", 105, 32, 0, "Snubber NR"); part("C55", C_, C0603, "330p/50V", "C1664", 109.5, 32, 0, "Snubber NR")
part("R24", R_, R1206, "18", "C17949", 105, 28.5, 0, "Snubber PR"); part("C56", C_, C0603, "330p/50V", "C1664", 109.5, 28.5, 0, "Snubber PR")

# --- USB-kodek PCM2900C (AUX 2) – bus-powered fra Pi-ens USB-port (J19) ---
part("U11", SO, "SSOP-28_5.3x10.2mm_P0.65mm", "PCM2900CDB", "C180425", 114, 84, 0, "USB-lydkodek AUX 2 (ADC)")
part("Y2", "Crystal", "Crystal_SMD_3225-4Pin_3.2x2.5mm", "12MHz", "C9002", 122, 79, 0, "Kodek-krystall")
part("C87", C_, C0603, "20p", "C1653", 118, 76, 0, "XTI last"); part("C88", C_, C0603, "20p", "C1653", 126, 76, 0, "XTO last"); part("R63", R_, R0603, "1M", "C22935", 122, 75, 0, "Krystall tilbakekobling")
part("C89", C_, C0805, "10u", "C15850", 106, 80, 90, "VCCCI"); part("C90", C_, C0805, "10u", "C15850", 106, 88, 90, "VCOM")
part("C91", C_, C0603, "1u", "C15849", 110, 75, 0, "VCCP1I"); part("C92", C_, C0603, "1u", "C15849", 114, 75, 0, "VCCP2I"); part("C93", C_, C0603, "1u", "C15849", 130, 80, 90, "VCCXI"); part("C94", C_, C0603, "1u", "C15849", 130, 84, 90, "VDDI")
part("C95", C_, C0805, "10u", "C15850", 106, 72, 0, "VBUS"); part("C96", C_, C0603, "100n", "C14663", 110, 72, 0, "VBUS HF")
part("R64", R_, R0603, "22", "C25092", 115, 72, 0, "D+ serie"); part("R65", R_, R0603, "22", "C25092", 119, 72, 0, "D- serie"); part("R66", R_, R0603, "1.5k", "C22843", 120, 68.5, 0, "D+ pull-up (full speed)")
part("R67", R_, R0603, "10k", "C25804", 134, 76, 0, "AUX2 L deler"); part("R68", R_, R0603, "4.7k", "C23162", 134, 79, 0, "AUX2 L deler GND")
part("R69", R_, R0603, "10k", "C25804", 138, 76, 0, "AUX2 R deler"); part("R70", R_, R0603, "4.7k", "C23162", 138, 79, 0, "AUX2 R deler GND")
part("C97", C_, C0805, "4.7u", "C1779", 134, 83, 0, "AUX2 L kobling"); part("C98", C_, C0805, "4.7u", "C1779", 138, 83, 0, "AUX2 R kobling")

# --- front: kontakter (y ~ 94) og LED-drivere ---
part("J7", "Connector_JST", "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "KNAPPER", "C144397", 12, 94, 0, "AIR BT AUX USB PWR GND (til MCP23017)")
part("J8", "Connector_JST", "JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical", "ENCODER", "C144396", 31.5, 94, 0, "CLK DT SW 3V3 GND")
part("J21", "Connector_JST", "JST_XH_B2B-XH-A_1x02_P2.50mm_Vertical", "PWR BAK", "C144394", 48.5, 94, 0, "Strømknapp bak (GPIO 15, GND)")
part("J9", "Connector_JST", "JST_XH_B5B-XH-A_1x05_P2.50mm_Vertical", "OLED", "C144396", 70, 94, 0, "3V3_SW GND SDA SCL RES")
part("J13", "Connector_PinHeader_2.54mm", "PinHeader_1x14_P2.54mm_Vertical", "TFT", "C50981", 85, 94, 90, "2,8\" SPI TFT ILI9341/ST7789V + XPT2046: VCC GND CS RST DC MOSI SCK LED MISO T_CLK T_CS T_DIN T_DO T_IRQ")
part("Q9", TO, "SOT-23-3", "AO3400A", "C20917", 46, 77, 0, "TFT-baklys (fra GPIO 13 PWM)"); part("Q10", TO, "SOT-23-3", "AO3401A", "C15127", 52, 77, 0, "TFT-baklys høyside 3V3_SW")
part("R71", R_, R0603, "100", "C22775", 42, 78, 0, "Gate Q9"); part("R72", R_, R0603, "100k", "C25803", 46, 80, 0, "Pulldown Q9"); part("R73", R_, R0603, "10k", "C25804", 52, 80, 0, "Q10 gate"); part("R74", R_, R0603, "100k", "C25803", 56, 80, 0, "Q10 gate pull-up")
part("J10", "Connector_JST", "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "LED-RINGER", "C144397", 123, 94, 0, "5V_SW AIR BT AUX USB PWR (-)")
part("J4", "Connector_JST", "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical", "AUX1", "C144395", 142, 94, 0, "AUX 1 fra PJ392 bak: L, R, GND")
part("J20", "Connector_JST", "JST_XH_B3B-XH-A_1x03_P2.50mm_Vertical", "AUX2", "C144395", 153, 94, 0, "AUX 2 fra PJ392 bak: L, R, GND")
part("J19", "Connector_JST", "JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical", "USB PI", "C144393", 164.5, 96, 0, "Fra en USB-port på Pi-en: 5V D- D+ GND (kodek)")
part("J22", "Connector_JST", "JST_XH_B6B-XH-A_1x06_P2.50mm_Vertical", "EXP", "C144397", 57, 85, 0, "Ledige MCP-pinner GPA5 GPA6 GPA7 GPB5 + 3V3 GND")
for i, (nm, x) in enumerate([("AIR", 76), ("BT", 82), ("AUX", 88), ("USB", 94), ("PWR", 100)]):
    part(f"Q{i+2}", TO, "SOT-23-3", "AO3400A", "C20917", x, 84, 0, f"LED-ring {nm}")
    part(f"R{25+i}", R_, R0603, "100", "C22775", x, 80, 0, f"Gate {nm}"); part(f"R{30+i}", R_, R0603, "100k", "C25803", x - 3, 80, 90, f"Pulldown {nm}")
for i, x in enumerate([14, 18, 22, 26, 30]):
    part(f"C{57+i}", C_, C0603, "100n", "C14663", x, 86, 90, "Debounce knapp")
for i, x in enumerate([34, 38, 42]):
    part(f"R{40+i}", R_, R0603, "10k", "C25804", x, 82, 90, "Pull-up encoder"); part(f"C{62+i}", C_, C0603, "100n", "C14663", x, 86, 90, "Debounce encoder")
part("R45", R_, R0603, "10k", "C25804", 46, 82, 90, "Pull-up knapp bak"); part("C65", C_, C0603, "100n", "C14663", 46, 86, 90, "Debounce knapp bak")
part("C99", C_, C0603, "100n", "C14663", 74, 89, 0, "3V3_SW ved OLED")

# --- USB-delingsswitch (x 140–180): 2 × USB-C inn (til panelkontakter bak med korte kabler), mux, hub, 4 × USB-A ut i høyre kant ---
part("U7", SO, "SSOP-28_5.3x10.2mm_P0.65mm", "FE1.1s", "C6706491", 149, 46, 90, "USB 2.0 4-ports hub")
part("Y1", "Crystal", "Crystal_SMD_3225-4Pin_3.2x2.5mm", "12MHz", "C9002", 149, 37, 90, "Hub-krystall (lastkondensatorer innebygd)")
part("C67", C_, C0805, "10u", "C15850", 141, 34, 90, "VD18_O"); part("C69", C_, C0603, "100n", "C14663", 141, 38, 90, "VD18")
part("R75", R_, R0603, "2.7k", "C25772", 141, 42, 90, "REXT (1 %)"); part("R46", R_, R0603, "10k", "C25804", 141, 50, 90, "OVCJ/XRSTJ pull-up")
part("C66", C_, C0805, "10u", "C15850", 141, 54, 90, "VD33_O"); part("C73", C_, C0603, "100n", "C14663", 141, 58, 90, "VD33")
part("C68", C_, C0603, "100n", "C14663", 141, 62, 90, "VDD5")
part("U8", "Package_DFN_QFN", "UQFN-10_1.4x1.8mm_P0.4mm", "TS3USB221", "C130085", 147, 62, 0, "USB 2:1-mux PC1/PC2 (S fra MCP GPB4)")
part("C70", C_, C0603, "100n", "C14663", 150, 70, 0, "Mux VCC"); part("R47", R_, R0603, "100k", "C25803", 150, 66, 0, "S pulldown (= PC 1)")
part("J11", "Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "PC1", "C2765186", 150, 76, 0, "USB-C fra PC 1 (via panelkabel)")
part("J12", "Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "PC2", "C2765186", 150, 86, 0, "USB-C fra PC 2 (via panelkabel)")
part("R48", R_, R0603, "5.1k", "C23186", 160, 72, 0, "CC1 PC1"); part("R49", R_, R0603, "5.1k", "C23186", 160, 75, 0, "CC2 PC1")
part("R50", R_, R0603, "5.1k", "C23186", 160, 82, 0, "CC1 PC2"); part("R51", R_, R0603, "5.1k", "C23186", 160, 85, 0, "CC2 PC2")
for i, y in enumerate((16.2, 33.7, 51.2, 68.7)):
    part(f"J{15+i}", "Connector_USB", "USB_A_Molex_67643_Horizontal", f"USB{i+1}", "C2765194", 167.3, y, 90, f"USB-A ut {i+1} (høyre kant)")
part("F2", "Fuse", "Fuse_1812_4532Metric", "2A PTC", "C545213", 143, 72, 90, "Polyfuse 5 V til USB-portene")
part("C71", C_, C1206, "10u", "C13585", 143, 78, 90, "5V_USB"); part("C72", "Capacitor_SMD", "CP_Elec_10x10.5", "220u/35V", "C134754", 146, 16, 0, "5V_USB bulk")
for i, (x, y) in enumerate([(4, 4), (176, 4), (4, 96), (176, 96)]):
    part(f"H{i+1}", "MountingHole", "MountingHole_3.2mm_M3", "M3", "", x, y, 0, "Festehull M3 (stolper i kassen)")
# Raspberry Pi 4 skrus fast under kortet med 4 × M2,5-avstandsstykker (20 mm): Pi-ens hullmønster 58 × 49, kortet 85 × 56 med
# portene mot +x (pluggene får plass under kortet). Pi-en ligger fra x 17,5 til 102,5, y 10,5 til 66,5 – SD-kortet mot venstre kant.
PI_X0, PI_Y0 = 17.5, 10.5
for i, (x, y) in enumerate([(PI_X0 + 3.5, PI_Y0 + 3.5), (PI_X0 + 61.5, PI_Y0 + 3.5), (PI_X0 + 3.5, PI_Y0 + 52.5), (PI_X0 + 61.5, PI_Y0 + 52.5)]):
    part(f"H{i+5}", "MountingHole", "MountingHole_2.7mm_M2.5", "M2.5", "", x, y, 0, "Festehull M2,5 for Raspberry Pi 4 (avstandsstykke 20 mm under kortet)")

# ---------------------------------------------------------------- USB-blokken til venstre: speil USB-delen (x >= 140 -> 180 - x), flytt resten 40 mm til høyre
for p in P:
    if p["ref"].startswith("H"):
        continue
    if p["x"] >= 139.5:
        p["x"] = BW - p["x"]
        if p["fp"].startswith("USB_A_"):
            p["rot"] = 270                        # åpningen mot venstre kant
        elif p["fp"].startswith("USB_C_"):
            pass
        elif p["rot"] in (0, 180):
            pass
    else:
        p["x"] += 40.0
SILK_SHIFT = lambda x: (BW - x) if x >= 139.5 else x + 40.0
# etterjusteringer: høyttalerterminal R innenfor kanten, frontkontaktene litt tettere, AUX 1/2 og USB-PI på høyre kant
_fix = {"J3": (164, 6, 0), "J7": (46, 94, 0), "J8": (65.5, 94, 0), "J21": (82.5, 94, 0), "J6": (93, 94, 0), "J9": (104, 94, 0), "J13": (119, 94, 90), "J10": (157, 94, 0),
        "J4": (176, 58, 90), "J20": (176, 70, 90), "J19": (176, 84, 90), "FB1": (167, 66, 0),
        "R67": (166, 52, 0), "R68": (166, 55, 0), "R69": (170, 52, 0), "R70": (170, 55, 0), "C93": (166, 83, 90), "C94": (170, 84, 90), "C97": (166, 88, 0), "C98": (170, 88, 0)}
for p in P:
    if p["ref"] in _fix:
        p["x"], p["y"], p["rot"] = _fix[p["ref"]]

# ---------------------------------------------------------------- netliste
N = {}
def net(name, *pins):
    N.setdefault(name, []).extend(pins)

GND = "GND"
# 24 V inn -> sikring -> VIN24 (buck, TVS, bulk) ; relé K1 -> 24V_AMP (forsterker)
net("24V_IN", ("J1", 1), ("F1", 1)); net(GND, ("J1", 2))
net("VIN24", ("F1", 2), ("D1", 1), ("C1", 1), ("C2", 1), ("C3", 1), ("C4", 1), ("U1", 2), ("R1", 1), ("K1", 4))
net("24V_AMP", ("K1", 5), ("C36", 1), ("C37", 1), ("C38", 1), ("C39", 1), ("C40", 1), ("C41", 1), ("U6", 18), ("U6", 19), ("U6", 31), ("U6", 32), ("U6", 17), ("C42", 1), ("C43", 1))
net(GND, ("D1", 2), ("C1", 2), ("C2", 2), ("C3", 2), ("C4", 2), ("U1", 7), ("U1", 9), ("R2", 2), ("R3", 2), ("R5", 2), ("C6", 2), ("C7", 2), ("D2", 2),
    ("C8", 2), ("C9", 2), ("C10", 2), ("C11", 2))
# buck
net("BUCK_BOOT", ("U1", 1), ("C5", 1)); net("BUCK_SW", ("U1", 8), ("C5", 2), ("L1", 1), ("D2", 1))
net("BUCK_EN", ("U1", 3), ("R1", 2), ("R2", 1)); net("BUCK_RT", ("U1", 4), ("R3", 1))
net("BUCK_FB", ("U1", 5), ("R4", 2), ("R5", 1)); net("BUCK_COMP", ("U1", 6), ("R6", 1), ("C7", 1)); net("BUCK_COMPC", ("R6", 2), ("C6", 1))
# 5 V (alltid): Pi, hub, relé-spole, Q8-kilde
net("5V", ("L1", 2), ("R4", 1), ("C8", 1), ("C9", 1), ("C10", 1), ("C11", 1), ("U2", 3), ("C12", 1), ("J6", 1), ("J5", 2), ("J5", 4),
    ("U7", 20), ("U7", 18), ("C68", 1), ("F2", 1), ("C72", 1), ("K1", 1), ("D4", 1), ("Q8", 2), ("R55", 1))
# smart relé: GPIO 27 -> Q7 -> relé + Q8 (5V_SW)
net("PWR_G", ("J5", 13), ("R52", 1)); net("PWR_GATE", ("R52", 2), ("Q7", 1), ("R53", 1)); net(GND, ("Q7", 2), ("R53", 2))
net("RLY_LOW", ("Q7", 3), ("K1", 2), ("D4", 2), ("R54", 1)); net("Q8_GATE", ("R54", 2), ("Q8", 1), ("R55", 2))
net("5V_SW", ("Q8", 3), ("U3", 8), ("U3", 1), ("U5", 4), ("U5", 1), ("C27", 1), ("R14", 1), ("J10", 1), ("FB1", 1), ("U9", 3), ("C75", 1), ("U10", 3), ("C80", 1), ("C81", 1))
net("5VA", ("FB1", 2), ("U5", 12), ("C28", 1), ("C30", 1))
# 3,3 V alltid (U2): MCP23017, pull-ups, encoder, hub-mux via VD33
net(GND, ("U2", 1), ("C12", 2), ("C13", 2), ("C14", 2))
net("3V3", ("U2", 2), ("C13", 1), ("C14", 1), ("J8", 4), ("R43", 1), ("R44", 1), ("U12", 9), ("R56", 1), ("C74", 1), ("R45", 1), ("J22", 5),
    *[(f"R{40+i}", 1) for i in range(3)])
# 3,3 V_SW (U9): DAC, ADC digital, oscillator, OLED, TFT
net(GND, ("U9", 1), ("C75", 2), ("C76", 2))
net("3V3_SW", ("U9", 2), ("C76", 1), ("U4", 1), ("U4", 8), ("U4", 20), ("C20", 1), ("C21", 1), ("C22", 1), ("R7", 1),
    ("J9", 1), ("C99", 1), ("U10", 4), ("C82", 1), ("U10", 10), ("U10", 11), ("X1", 4), ("C77", 1), ("J13", 1), ("Q10", 2), ("R74", 1))
# -5 V
net(GND, ("U3", 3), ("C16", 2)); net("CP_PLUS", ("U3", 2), ("C15", 1)); net("CP_MINUS", ("U3", 4), ("C15", 2))
net("VNEG", ("U3", 5), ("C16", 1), ("U5", 13), ("C29", 1), ("C31", 1))
# Pi header GND
for p in (6, 9, 14, 20, 25, 30, 34, 39):
    net(GND, ("J5", p))
# I2C: OLED + MCP23017
net("SDA", ("J5", 3), ("J9", 3), ("R43", 2), ("U12", 13)); net("SCL", ("J5", 5), ("J9", 4), ("R44", 2), ("U12", 12)); net("OLED_RES", ("J5", 7), ("J9", 5))
net(GND, ("J9", 2), ("C99", 2))
# MCP23017: 0x20, RESET pull-up, INTA -> GPIO 14
net(GND, ("U12", 10), ("U12", 15), ("U12", 16), ("U12", 17), ("C74", 2)); net("MCP_RST", ("U12", 18), ("R56", 2)); net("MCP_INT", ("U12", 20), ("J5", 8))
# knapper (MCP GPA0-4, interne pull-ups) + debounce
for i, (nm, gpa) in enumerate([("AIR", 21), ("BT", 22), ("AUX", 23), ("USB", 24), ("PWR", 25)]):
    net(f"BTN_{nm}", ("U12", gpa), ("J7", i + 1), (f"C{57+i}", 1))
net(GND, ("J7", 6), *[(f"C{57+i}", 2) for i in range(5)])
net("EXP_A5", ("U12", 26), ("J22", 1)); net("EXP_A6", ("U12", 27), ("J22", 2)); net("EXP_A7", ("U12", 28), ("J22", 3)); net("EXP_B5", ("U12", 6), ("J22", 4)); net(GND, ("J22", 6))
# knapp bak -> GPIO 15
net("BTN_BAK", ("J5", 10), ("J21", 1), ("R45", 2), ("C65", 1)); net(GND, ("J21", 2), ("C65", 2))
# encoder -> GPIO 23/24/25
net("ENC_CLK", ("J5", 16), ("J8", 1), ("R40", 2), ("C62", 1)); net("ENC_DT", ("J5", 18), ("J8", 2), ("R41", 2), ("C63", 1)); net("ENC_SW", ("J5", 22), ("J8", 3), ("R42", 2), ("C64", 1))
net(GND, ("J8", 5), ("C62", 2), ("C63", 2), ("C64", 2))
# SPI0: PGA2311 (CE0) og TFT (CE1) + touch
net("SPI_MOSI", ("J5", 19), ("U5", 3), ("J13", 6), ("J13", 12)); net("SPI_SCLK", ("J5", 23), ("U5", 6), ("J13", 7), ("J13", 10)); net("SPI_CS", ("J5", 24), ("U5", 2))
net("SPI_MISO", ("J5", 21), ("J13", 9), ("J13", 13)); net("TFT_CS", ("J5", 26), ("J13", 3)); net("TFT_DC", ("J5", 29), ("J13", 5)); net("TFT_RST", ("J5", 31), ("J13", 4))
net("TOUCH_CS", ("J5", 36), ("J13", 11)); net("TOUCH_IRQ", ("J5", 11), ("J13", 14)); net(GND, ("J13", 2))
net("TFT_BL_G", ("J5", 33), ("R71", 1)); net("TFT_BL_GATE", ("R71", 2), ("Q9", 1), ("R72", 1)); net(GND, ("Q9", 2), ("R72", 2))
net("TFT_BL_LOW", ("Q9", 3), ("R73", 1)); net("Q10_GATE", ("R73", 2), ("Q10", 1), ("R74", 2)); net("TFT_LED", ("Q10", 3), ("J13", 8))
# LED-ringer: AIR/BT/AUX/USB fra MCP GPB0-3, POWER fra GPIO 12 (PWM)
for i, nm in enumerate(["AIR", "BT", "AUX", "USB"]):
    net(f"LED_{nm}_G", ("U12", i + 1), (f"R{25+i}", 1))
net("LED_PWR_G", ("J5", 32), ("R29", 1))
for i, nm in enumerate(["AIR", "BT", "AUX", "USB", "PWR"]):
    q, rg, rp = f"Q{i+2}", f"R{25+i}", f"R{30+i}"
    net(f"LED_{nm}_GATE", (q, 1), (rg, 2), (rp, 1)); net(GND, (q, 2), (rp, 2)); net(f"LED_{nm}_K", (q, 3), ("J10", i + 2))
# forsterker-styring
net("AMP_SD_G", ("J5", 15), ("R19", 1)); net("DAC_XSMT", ("J5", 37), ("U4", 17), ("R7", 2))
# I2S: PCM1808 er master (BCK/LRCK), Pi slave, DAC slave
net("I2S_BCK", ("J5", 12), ("U4", 13), ("U10", 8)); net("I2S_LRCK", ("J5", 35), ("U4", 15), ("U10", 7)); net("I2S_DIN", ("J5", 40), ("U4", 14)); net("I2S_ADC", ("J5", 38), ("U10", 9))
# DAC
net("DAC_CAPP", ("U4", 2), ("C17", 1)); net("DAC_CAPM", ("U4", 4), ("C17", 2)); net("DAC_VNEG", ("U4", 5), ("C18", 1)); net("DAC_LDOO", ("U4", 18), ("C19", 1))
net(GND, ("U4", 3), ("U4", 9), ("U4", 10), ("U4", 11), ("U4", 12), ("U4", 16), ("U4", 19), ("C18", 2), ("C19", 2), ("C20", 2), ("C21", 2), ("C22", 2), ("C23", 2), ("C24", 2))
net("DAC_L", ("U4", 6), ("R8", 1)); net("DAC_R", ("U4", 7), ("R9", 1))
net("DAC_L_F", ("R8", 2), ("C23", 1), ("C25", 1)); net("DAC_R_F", ("R9", 2), ("C24", 1), ("C26", 1))
net("VOL_INL", ("C25", 2), ("R12", 1), ("U5", 16)); net("VOL_INR", ("C26", 2), ("R13", 1), ("U5", 9))
net(GND, ("R12", 2), ("R13", 2), ("U5", 5), ("U5", 10), ("U5", 15), ("C27", 2), ("C28", 2), ("C29", 2), ("C30", 2), ("C31", 2))
net("PGA_MUTE", ("U5", 8), ("R14", 2))
net("VOL_OUTL", ("U5", 14), ("C45", 1)); net("VOL_OUTR", ("U5", 11), ("C47", 1))
# ADC PCM1808 (AUX 1): deler 10k/10k -> 4,7 µF -> 1k -> VIN (1 nF), VREF 10 µ + 100 n, FMT=0, MD1=MD0=1
net("AUX1_L", ("J4", 1), ("R57", 1)); net("AUX1_R", ("J4", 2), ("R59", 1)); net(GND, ("J4", 3), ("R58", 2), ("R60", 2), ("C85", 2), ("C86", 2))
net("AUX1_L_D", ("R57", 2), ("R58", 1), ("C83", 1)); net("AUX1_R_D", ("R59", 2), ("R60", 1), ("C84", 1))
net("AUX1_L_C", ("C83", 2), ("R61", 1)); net("AUX1_R_C", ("C84", 2), ("R62", 1))
net("ADC_VINL", ("R61", 2), ("C85", 1), ("U10", 13)); net("ADC_VINR", ("R62", 2), ("C86", 1), ("U10", 14))
net("ADC_VREF", ("U10", 1), ("C78", 1), ("C79", 1)); net(GND, ("U10", 2), ("U10", 5), ("U10", 12), ("C78", 2), ("C79", 2), ("C80", 2), ("C81", 2), ("C82", 2), ("X1", 2), ("C77", 2))
net("ADC_SCKI", ("U10", 6), ("X1", 3))
# USB-kodek PCM2900C (AUX 2), bus-powered fra J19
net("USB_PI_VBUS", ("J19", 1), ("U11", 3), ("C95", 1), ("C96", 1)); net("USB_PI_DM", ("J19", 2), ("R65", 1)); net("USB_PI_DP", ("J19", 3), ("R64", 1)); net(GND, ("J19", 4), ("C95", 2), ("C96", 2))
net("CODEC_DP", ("R64", 2), ("U11", 1), ("R66", 1)); net("CODEC_DM", ("R65", 2), ("U11", 2))
net("CODEC_VCCCI", ("U11", 10), ("C89", 1), ("U11", 8), ("U11", 9), ("R66", 2)); net("CODEC_VCOM", ("U11", 14), ("C90", 1))
net("CODEC_VCCP1", ("U11", 17), ("C91", 1)); net("CODEC_VCCP2", ("U11", 19), ("C92", 1)); net("CODEC_VCCX", ("U11", 23), ("C93", 1)); net("CODEC_VDD", ("U11", 27), ("C94", 1))
net("CODEC_XTI", ("U11", 21), ("Y2", 1), ("C87", 1), ("R63", 1)); net("CODEC_XTO", ("U11", 20), ("Y2", 3), ("C88", 1), ("R63", 2))
net(GND, ("U11", 4), ("U11", 11), ("U11", 18), ("U11", 22), ("U11", 24), ("U11", 26), ("Y2", 2), ("Y2", 4), ("C87", 2), ("C88", 2), ("C89", 2), ("C90", 2), ("C91", 2), ("C92", 2), ("C93", 2), ("C94", 2))
net("AUX2_L", ("J20", 1), ("R67", 1)); net("AUX2_R", ("J20", 2), ("R69", 1)); net(GND, ("J20", 3), ("R68", 2), ("R70", 2))
net("AUX2_L_D", ("R67", 2), ("R68", 1), ("C97", 1)); net("AUX2_R_D", ("R69", 2), ("R70", 1), ("C98", 1))
net("CODEC_VINL", ("C97", 2), ("U11", 12)); net("CODEC_VINR", ("C98", 2), ("U11", 13))
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
# USB-delingsswitch
net("5V_USB", ("F2", 2), ("C71", 1), *[(f"J{15+i}", 1) for i in range(4)]); net(GND, ("C71", 2), ("C72", 2))
net("USB_VD33", ("U7", 21), ("U7", 13), ("U7", 19), ("C66", 1), ("C73", 1), ("R46", 1), ("U8", 1), ("C70", 1))
net("USB_VD18", ("U7", 12), ("U7", 28), ("C67", 1), ("C69", 1))
net("USB_REXT", ("U7", 14), ("R75", 1)); net("USB_RSTJ", ("U7", 17), ("U7", 26), ("R46", 2))
net("USB_XIN", ("U7", 3), ("Y1", 1)); net("USB_XOUT", ("U7", 2), ("Y1", 3))
net(GND, ("U7", 1), ("Y1", 2), ("Y1", 4), ("R75", 2), ("C66", 2), ("C67", 2), ("C68", 2), ("C69", 2), ("C73", 2), ("C70", 2), ("U8", 5), ("U8", 10), ("R47", 2))
net("USB_UP_DP", ("U7", 16), ("U8", 3)); net("USB_UP_DM", ("U7", 15), ("U8", 4))
net("USB_SEL", ("U12", 5), ("U8", 2), ("R47", 1))   # MCP GPB4: lav = PC 1, høy = PC 2
net("PC1_DP", ("U8", 6), ("J11", "A6"), ("J11", "B6")); net("PC1_DM", ("U8", 7), ("J11", "A7"), ("J11", "B7"))
net("PC2_DP", ("U8", 8), ("J12", "A6"), ("J12", "B6")); net("PC2_DM", ("U8", 9), ("J12", "A7"), ("J12", "B7"))
net("PC1_CC1", ("J11", "A5"), ("R48", 1)); net("PC1_CC2", ("J11", "B5"), ("R49", 1)); net("PC2_CC1", ("J12", "A5"), ("R50", 1)); net("PC2_CC2", ("J12", "B5"), ("R51", 1))
net(GND, ("R48", 2), ("R49", 2), ("R50", 2), ("R51", 2), *[(j, p) for j in ("J11", "J12") for p in ("A1", "B1", "A12", "B12", "S1")])
for i, (dp, dm) in enumerate(((11, 10), (9, 8), (7, 6), (5, 4))):
    net(f"USB{i+1}_DP", ("U7", dp), (f"J{15+i}", 3)); net(f"USB{i+1}_DM", ("U7", dm), (f"J{15+i}", 2)); net(GND, (f"J{15+i}", 4), (f"J{15+i}", 5))

POWER_NETS = {"5V_USB": 1.0, "5VA": 0.5, "5V_SW": 0.8, "3V3_SW": 0.5, "24V_AMP": 2.0, "VIN24": 2.0, "24V_IN": 2.0, "5V": 1.2, "BUCK_SW": 1.5, "OUTNL": 1.5, "OUTPL": 1.5, "OUTNR": 1.5, "OUTPR": 1.5,
              "SPK_LN": 1.5, "SPK_LP": 1.5, "SPK_RN": 1.5, "SPK_RP": 1.5, "3V3": 0.5, "VNEG": 0.4}

# ---------------------------------------------------------------- bygg kortet
def build():
    board = pcbnew.BOARD()
    ds = board.GetDesignSettings()
    ds.SetCopperLayerCount(2)
    ds.m_TrackMinWidth = pcbnew.FromMM(0.2); ds.m_ViasMinSize = pcbnew.FromMM(0.5); ds.m_MinClearance = pcbnew.FromMM(0.127)
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
    nc_ok = {("U3", "6"), ("U3", "7"), ("U7", "22"), ("U7", "23"), ("U7", "24"), ("U7", "25"), ("U7", "27"), ("K1", "3"),
             ("U11", "5"), ("U11", "6"), ("U11", "7"), ("U11", "15"), ("U11", "16"), ("U11", "25"), ("U11", "28"), ("U12", "11"), ("U12", "14"), ("U12", "19"),
             ("U12", "7"), ("U12", "8"), ("X1", "1"), ("U5", "7"), ("U6", "3"), ("U6", "16"), ("J5", "1"), ("J5", "17"), ("J5", "27"), ("J5", "28"), ("U1", "0")}
    for ref in ("U1", "U6"):   # termiske via-pads uten nummer -> GND
        for pd in fps[ref].Pads():
            if pd.GetNumber() == "":
                pd.SetNet(nets[GND])
    for pd in fps["U6"].Pads():   # TPA3116D2DAD har kjøleflaten på TOPPEN – ingen pasta under brikken
        if pd.GetNumber() in ("", "33"):
            ls = pd.GetLayerSet(); ls.RemoveLayer(pcbnew.F_Paste); pd.SetLayerSet(ls)
    for ref in ("J11", "J12"):   # USB-C: skjermpads uten nummer -> GND
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
        z.SetLocalClearance(pcbnew.FromMM(0.2)); z.SetMinThickness(pcbnew.FromMM(0.2))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)   # direkte tilkobling: ingen «starved thermal» ved tette IC-pads
        ol = z.Outline(); ol.NewOutline()
        for (x, y) in [(1, 1), (BW - 1, 1), (BW - 1, BH - 1), (1, BH - 1)]:
            ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
        board.Add(z)
    # nettklasser (bredde brukes av Freerouting via DSN)
    try:
        ncs = ds.m_NetSettings.m_NetClasses
        default = ds.m_NetSettings.m_DefaultNetClass
        default.SetTrackWidth(pcbnew.FromMM(0.25)); default.SetClearance(pcbnew.FromMM(0.15)); default.SetViaDiameter(pcbnew.FromMM(0.8)); default.SetViaDrill(pcbnew.FromMM(0.4))
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
    t = pcbnew.PCB_TEXT(board); t.SetText("Pultforsterker  rev B  2026"); t.SetPosition(MM(115, 78)); t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(1.5), pcbnew.FromMM(1.5))); board.Add(t)
    for txt, x, y in [("SPK R", 170, 12), ("KNAPPER", 50, 98.5), ("ENC", 70, 98.5), ("PWR", 84, 98.5), ("5V PI", 93, 98.5), ("OLED", 108, 98.5), ("TFT", 134, 98.5), ("LED", 162, 98.5),
                      ("AUX1", 171, 54), ("AUX2", 171, 66), ("USB PI", 171, 78), ("PC1", 37, 76), ("PC2", 37, 86), ("USB 1-4", 20, 10), ("EXP", 97, 81),
                      ("24V IN", 54, 12), ("SPK L", 148, 12), ("Pi 40", 54, 90)]:
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
