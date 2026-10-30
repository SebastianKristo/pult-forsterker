# Pultforsterker – hovedkort rev B

Ett kort (180 × 100 mm, 2 lag) som erstatter alle modulene, og som i tillegg har USB-delingsswitch, to AUX-innganger som
digitaliseres (så alt kan mikses), «smart relé» for strømmen til forsterkerdelen, og plass til en 2,8" SPI-TFT med touch.
Raspberry Pi 4 kobles til med 40-pinners flatkabel; frontdelene med JST XH-plugger; alle bakkontakter er panelmonterte med
korte kabler til kortet.

**Status: rev B er ikke prøvd i praksis.** Kortet er tegnet og autorutet med KiCad 7 og Freerouting, DRC er fri for koblings- og
klaringsfeil, men ingen har bygget det. Regn med at første utgave kan trenge en jumper eller to. Programvaren for rev B (I2S-slave,
MCP23017, per-kilde-nivå, TFT) er skrevet, men kan bare testes på et ferdig kort.

## Blokker

| Blokk | Krets | Merknad |
|---|---|---|
| 24 V inn | skruterminal → sikring 5 A (5×20, THT) → TVS SMBJ33A → 2200 µF (THT) | KCD1 hovedbryter i serie utenfor kortet |
| 5 V / 5 A (alltid) | TPS54560 buck, 400 kHz, 10 µH, 3 × 47 µF | Pi 4 («5V PI»), USB-hub, relé-spole |
| **Smart relé** | SRD-05VDC-SL-C (24 V → forsterker) + AO3401 P-MOSFET (5 V → 5V_SW) fra GPIO 27 via AO3400 | 5V_SW: LED-ringer, PGA2311, ADC, DAC, OLED/TFT. Av = helt stille og mørkt. Knapp bak på GPIO 15 |
| 3,3 V (alltid) | AMS1117-3.3 | MCP23017, pull-ups, encoder |
| 3,3 V_SW | AMS1117-3.3 fra 5V_SW | DAC, ADC digital, oscillator, OLED/TFT |
| −5 V | LM2662 (FC = V+, 150 kHz) | PGA2311 VA− (10–12 mA) |
| DAC | PCM5102A, I2S-slave | 100 Ω + 2,2 nF ut |
| **ADC AUX 1** | PCM1808, I2S-master 256 fs fra 12,288 MHz-oscillator (48 kHz) | Pi-en er I2S-slave. Inngang 10k/10k-deler, 4,7 µF, 1 kΩ + 1 nF |
| **USB-kodek AUX 2** | PCM2900C, 12 MHz-krystall, bus-powered fra en USB-port på Pi-en (J19) | Inngang 10k/4,7k-deler, 4,7 µF. Vises som «USB Audio CODEC» |
| Volum | PGA2311 (±5 V), bit-banget SPI fra GPIO 0/1/16, 5 V via ferritt + 10 µF | fast nivå; volum og nivå per kilde gjøres digitalt |
| Forsterker | TPA3116D2DAD, 26 dB, 400 kHz, 10 µH + 680 nF + snubber per utgang | **Kjøleflaten er på toppen**: ingen loddepasta under, kjøleribbe 20 × 20 limes på. SDZ fra GPIO 22 |
| **USB-switch** | FE1.1s 4-ports hub + TS3USB221 2:1-mux. 2 × USB-C (PC 1/PC 2) på kortet, 4 × USB-A i venstre kant, polyfuse 2 A | Mux-valg fra MCP23017 GPB4 (lav = PC 1). CC-pinnene har 5,1 k, så USB-C–USB-C-kabel virker |
| I/O-ekspander | MCP23017 (I2C 0x20), INT → GPIO 14 | GPA0-4 knapper AIR/BT/AUX/USB/PWR, GPB0-3 LED-ringer, GPB4 USB-mux, 4 ledige på «EXP» |
| LED-ringer | 5 × AO3400 low-side | POWER-ring på GPIO 12 (PWM) |
| TFT | 14-pinners header (standard 2,8" ILI9341/ST7789V-modul med XPT2046) | SPI0 CE0 = TFT, CE1 = touch, DC 5, RST 6, IRQ 17, baklys GPIO 13 (PWM) via AO3400 + AO3401 |

## GPIO-kart (hovedkort rev B)

| GPIO | Bruk | GPIO | Bruk |
|---|---|---|---|
| 2, 3 | I2C: OLED, MCP23017 | 18, 19, 21, 20 | I2S BCK, LRCK, DAC-data, ADC-data (Pi er slave) |
| 4 | OLED RES | 22 | TPA3116 SDZ (høy = på) |
| 5, 6, 13 | TFT DC, RST, baklys (PWM) | 23, 24, 25 | encoder CLK, DT, SW |
| 7, 8 | SPI0 CE1 touch, CE0 TFT | 26 | DAC XSMT |
| 9, 10, 11 | SPI0 MISO, MOSI, SCLK (TFT + touch) | 27 | strømrelé + 5V_SW |
| 12 | POWER-ring (PWM) | 0, 1, 16 | PGA2311 MOSI, SCLK, CS (bit-bang) |
| 14 | MCP23017 INT | 15 | strømknapp bak |
| 17 | touch IRQ | | |

Sett `KI_AMP_BOARD=main` i `/etc/ki-amp.env` (gjøres av `KI_AMP_BOARD=main bash install.sh`).

## Kontakter

| Ref | Type | Pinner |
|---|---|---|
| J1 | skruterminal 5,08 | 24 V +, GND (fra DC-099 via KCD1) |
| J2 / J3 | skruterminal 5,08 | SPK L + −, SPK R + − |
| J4 / J20 | JST XH 3 | AUX 1 / AUX 2: L, R, GND (fra PJ392 bak) |
| J5 | 2×20 header | Raspberry Pi 40-pin (flatkabel 5–10 cm). Pi-en skrus under kortet i H5–H8 (M2,5, 20 mm avstandsstykker), portene mot høyre |
| J6 | skruterminal 5,08 | 5 V, GND → Pi 4 header pinne 2/6 (18 AWG) |
| J7 | JST XH 6 | AIR, BT, AUX, USB, POWER, GND (bryterne) |
| J8 | JST XH 5 | CLK, DT, SW, 3V3, GND (encoder) |
| J9 | JST XH 5 | 3V3_SW, GND, SDA, SCL, RES (OLED) |
| J10 | JST XH 6 | 5V_SW, AIR−, BT−, AUX−, USB−, POWER− (LED-ringer) |
| J11 / J12 | USB-C på kortet | PC 1 / PC 2 → panelmontert USB-C bak med 15 cm kabel |
| J13 | 1×14 header 2,54 | TFT: VCC GND CS RST DC MOSI SCK LED MISO T_CLK T_CS T_DIN T_DO T_IRQ (samme rekkefølge som modulen) |
| J15–J18 | USB-A | 4 × USB-A ut gjennom venstre vegg |
| J19 | JST XH 4 | 5V, D−, D+, GND fra en USB-A-port på Pi-en (USB-kodeken) |
| J21 | JST XH 2 | strømknapp bak (momentan), GND |
| J22 | JST XH 6 | EXP: MCP GPA5, GPA6, GPA7, GPB5, 3V3, GND (ledige) |

## Filer

- `build_board.py` – hele kortet (deler, netliste, plassering) som Python mot pcbnew. Kjør for å regenerere `.kicad_pcb`.
- `route.py` – eksporterer DSN og kjører Freerouting (`FREEROUTING=/sti/freerouting.jar python3 route.py`).
- `export.py` – importerer SES, fyller GND-soner, kjører DRC, lager `produksjon/`.
- `produksjon/ki_pultforsterker_main_gerber.zip` – last opp til JLCPCB/PCBWay (2 lag, 1,6 mm, HASL eller ENIG, 1 oz).
- `produksjon/ki_pultforsterker_main_bom.csv` + `_cpl.csv` – for SMT-montering (LCSC-numre).
- `bom.csv` – full deleliste per referanse.

## Bestilling

1. JLCPCB → «Add gerber file» → zip-en. 2 lag, 180 × 100 mm, grønn/svart, HASL (lead free).
2. Huk av «PCB Assembly», Top side, 2 stk. Last opp BOM og CPL.
3. Kontroller at alle LCSC-numre finnes på lager; bytt tilsvarende hvis noen er tomme (verdiene står i BOM). Sjekk spesielt
   FE1.1s (C6706491), PCM1808 (C7436), PCM2900C (C180425), TS3USB221 (C130085), MCP23017 (C506653), SRD-05VDC (C35449).
4. Festehull: H1–H4 M3 (stolper i kassen), H5–H8 M2,5 (Raspberry Pi 4 under kortet).
5. THT-deler loddes selv etter levering: J1–J3, J6 (skruterminaler), J4/J7–J10/J19–J22 (JST), J5, J13 (headere), F1 (sikringsklips),
   C1 (2200 µF), K1 (relé), J15–J18 (USB-A).
6. Kjøleribbe 20 × 20 × 10 mm med termisk tape (1,5–2 mm) på toppen av TPA3116.

## Kjente kompromisser i rev B

- Én felles GND-sone; analog, USB og klasse D deler plan.
- USB-banene er ikke impedanskontrollerte (2 lag), men korte. Full speed/high speed over få cm går normalt fint.
- Freerouting-ruting er funksjonell, ikke optimal. Sjekk at 24 V- og høyttalersporene ikke har unødvendige vias.
- Relé-pinner: 1–2 spole, 4 COM, 5 NO (3 NC ubrukt) etter KiCad-footprinten for SRD. Mål med multimeter før første gang.
- TPS54560-kompensasjon er fra datablad-eksempelet; ikke målt.
- PCM2900C: 1,5 kΩ pull-up på D+ til VCCCI er lagt til i tillegg til eventuell intern – sjekk at enumerasjon virker.
