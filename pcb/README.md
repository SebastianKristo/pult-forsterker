# Pultforsterker – hovedkort rev B

Ett kort (180 × 100 mm, 2 lag) som erstatter alle modulene, og som i tillegg har USB-delingsswitch, to AUX-innganger som
digitaliseres (så alt kan mikses), «smart relé» for strømmen til forsterkerdelen, hodetelefonutgang i fronten med
auto-demping, og plass til en 2,8" SPI-TFT med touch.
Raspberry Pi 4 kobles til med 40-pinners flatkabel; frontdelene med JST XH-plugger; alle bakkontakter er panelmonterte med
korte kabler til kortet.

**Status: rev B er ikke prøvd i praksis.** Kortet er tegnet og autorutet med KiCad 7 og Freerouting, DRC er fri for koblings- og
klaringsfeil, men ingen har bygget det. Regn med at første utgave kan trenge en jumper eller to. Programvaren for rev B (I2S-slave,
MCP23017, per-kilde-nivå, TFT) er skrevet, men kan bare testes på et ferdig kort.

## Blokker

| Blokk | Krets | Merknad |
|---|---|---|
| 24 V inn | skruterminal → sikring 5 A (5×20, THT) → TVS SMBJ33A → 2 × 1000 µF Ø10 (THT, maks 16 mm høye – kassen er 48 mm) | KCD1 hovedbryter i serie utenfor kortet |
| 5 V / 5 A (alltid) | TPS54560 buck, 400 kHz, 10 µH, 3 × 47 µF, satt til 5,2 V (56k/10,2k) mot fall i flatkabel/terminal | Pi 4 («5V PI»), USB-hub, relé-spole |
| **Smart relé** | SRD-05VDC-SL-C (24 V → forsterker) + AO3401 P-MOSFET (5 V → 5V_SW) fra GPIO 27 via AO3400 | 5V_SW: LED-ringer, PGA2311 (±5 V), ADC-analog, hodetelefonforsterker, TFT-baklys. Av = helt stille og mørkt. Knapp bak på GPIO 15 |
| 3,3 V (alltid) | AMS1117-3.3 | MCP23017, pull-ups, encoder, **DAC, ADC-digital, oscillator, OLED og TFT-logikk** (Pi-ens I2C/SPI/I2S må aldri drive inn i strømløse kretser; skjermen slukkes i programvare) |
| 3,3 V_SW | AMS1117-3.3 fra 5V_SW | bare TFT-baklyset (Q9/Q10) |
| −5 V | LM2662 (FC = V+, 150 kHz), 10 µF inn/fly/ut | PGA2311 VA− (10–12 mA) |
| DAC | PCM5102A, I2S-slave, SCK = GND (intern PLL), FLT/DEMP/FMT = GND, XSMT fra GPIO 26 | 100 Ω + 2,2 nF ut |
| **ADC AUX 1** | PCM1808, I2S-master 256 fs fra 12,288 MHz-oscillator (48 kHz) | Pi-en er I2S-slave. Inngang 10k/10k-deler, 4,7 µF, 1 kΩ + 1 nF |
| **USB-kodek AUX 2** | PCM2900C, 12 MHz-krystall, bus-powered fra en USB-port på Pi-en (J19) | Inngang 10k/4,7k-deler, 4,7 µF. Vises som «USB Audio CODEC» |
| Volum | PGA2311 (±5 V), bit-banget fra GPIO 0 (SDI), 1 (SCLK), 16 (CS) – header 27/28/36, 5 V via ferritt + 10 µF | fast nivå; volum og nivå per kilde gjøres digitalt |
| Forsterker | TPA3116D2DAD, 26 dB (100k/20k), BD-modus (MODSEL = GND), 400 kHz (AM = 000), MUTE = GND, SYNC åpen, PLIMIT = GVDD, 10 µH + 680 nF + snubber per utgang | **Kjøleflaten er på toppen**: ingen loddepasta under, kjøleribbe 20 × 20 limes på. SDZ fra GPIO 22 |
| **USB-switch** | FE1.1s 4-ports hub + TS3USB221 2:1-mux. 2 × USB-C (PC 1/PC 2) på kortet, 4 × USB-A i venstre kant, polyfuse 2 A | Mux-valg fra MCP23017 GPB4 (lav = PC 1). CC-pinnene har 5,1 k, så USB-C–USB-C-kabel virker |
| I/O-ekspander | MCP23017 (I2C 0x20), INT → GPIO 14 | GPA0-4 knapper AIR/BT/AUX/USB/PWR, GPA5 jack-deteksjon, GPA6 HP-EN, GPB0-3 LED-ringer, GPB4 USB-mux, GPA7/GPB5 ledige på «EXP» |
| LED-ringer | 5 × AO3400 low-side | POWER-ring på GPIO 12 (PWM) |
| **Hodetelefoner** | TPA6132A2 (DirectPath, −6 dB) etter PGA2311, 1 µF inn, 5V_SW. EN fra MCP23017 GPA6; jack-bryteren (DET) via 10 k til GPA5, 10 k pulldown på OUTL gir sikker «lav» uten plugg | 3,5 mm PJ-392 i fronten under POWER (J23). Ved innplugging dempes TPA3116 (SDZ) – kan slås av i HA/Homey |
| TFT | 14-pinners header (standard 2,4"/2,8" ILI9341/ST7789V-modul med XPT2046) | SPI0 CE0 (GPIO 8) = TFT, CE1 (GPIO 7) = touch med 10 k pull-up, DC 5, RST 6, IRQ 17, baklys GPIO 13 (PWM) via AO3400 + AO3401 fra 3V3_SW |

## GPIO-kart (hovedkort rev B)

| GPIO | Bruk | GPIO | Bruk |
|---|---|---|---|
| 2, 3 | I2C: OLED, MCP23017 | 18, 19, 21, 20 | I2S BCK, LRCK, DAC-data, ADC-data (Pi er slave) |
| 4 | OLED RES | 22 | TPA3116 SDZ (høy = på) |
| 5, 6, 13 | TFT DC, RST, baklys (PWM) | 23, 24, 25 | encoder CLK, DT, SW |
| 7, 8 | SPI0 CE1 touch, CE0 TFT | 26 | DAC XSMT |
| 0, 1 (header 27/28) | PGA2311 SDI, SCLK (ID-EEPROM-pinnene – ingen HAT-EEPROM på kortet) | 16 | PGA2311 CS |
| 9, 10, 11 | SPI0 MISO, MOSI, SCLK (TFT + touch) | 27 | strømrelé + 5V_SW |
| 12 | POWER-ring (PWM) | | |
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
| J7 | JST XH 6 | knapp 1 «BT» (AirPlay + Bluetooth), knapp 2 «RADIO», AUX, USB, POWER, GND (bryterne) |
| J8 | JST XH 5 | CLK, DT, SW, 3V3, GND (encoder) |
| J9 | JST XH 5 | 3V3_SW, GND, SDA, SCL, RES (OLED) |
| J10 | JST XH 6 | 5V_SW, AIR−, BT−, AUX−, USB−, POWER− (LED-ringer) |
| J11 / J12 | USB-C på kortet | PC 1 / PC 2 → panelmontert USB-C bak med 15 cm kabel |
| J13 | 1×14 header 2,54 | TFT: VCC GND CS RST DC MOSI SCK LED MISO T_CLK T_CS T_DIN T_DO T_IRQ (samme rekkefølge som modulen) |
| J15–J18 | USB-A | 4 × USB-A ut gjennom venstre vegg |
| J19 | JST XH 4 | 5V, D−, D+, GND fra en USB-A-port på Pi-en (USB-kodeken) |
| J21 | JST XH 2 | strømknapp bak (momentan), GND |
| J22 | JST XH 6 | EXP: MCP GPA5 (= jack-deteksjon via 10 k), GPA6 (= HP-EN), GPA7, GPB5, 3V3, GND |
| J23 | JST XH 4 | Hodetelefonjack i fronten (PJ392 med bryter, under POWER): L, R, GND, DET (jackens bryterkontakt for L: ligger mot L uten plugg, åpen med plugg) |

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
   FE1.1s (C6706491), PCM1808 (C7436), PCM2900C (C180425), TS3USB221 (C130085), MCP23017 (C506653), SRD-05VDC (C35449),
   TPA6132A2 (C69901).
4. Festehull: H1–H4 M3 (stolper i kassen), H5–H8 M2,5 (Raspberry Pi 4 under kortet).
5. THT-deler loddes selv etter levering: J1–J3, J6 (skruterminaler), J4/J7–J10/J19–J22 (JST), J5, J13 (headere), F1 (sikringsklips),
   C1 + C110 (1000 µF), K1 (relé), J15–J18 (USB-A), J23 (JST).
6. Kjøleribbe 20 × 20 × 10 mm med termisk tape (1,5–2 mm) på toppen av TPA3116.

## Slik virker kortet – funksjoner, innganger og utganger

**Innganger (lydkilder)**

| Kilde | Vei inn | Hvor lyden går | Nivå/volum |
|---|---|---|---|
| AirPlay 2 | nettverk → Pi (Shairport Sync) | ALSA softvol «KI AirPlay» → dmix → CamillaDSP → I2S → PCM5102A (DAC) | nivå per kilde + hovedvolum digitalt |
| Bluetooth A2DP | Pi-ens BT → bluealsa | «KI Bluetooth» → samme vei | samme |
| USB-lyd fra PC 1/PC 2 | USB-C bak → TS3USB221-mux (MCP GPB4 velger PC) → FE1.1s-hub → Pi (USB-gadget, Pi er lydkort for PC-en) | «KI USB» → samme vei | samme |
| Radio (Lyrion) | nettverk → squeezelite | «KI Radio» → samme vei | samme |
| AUX 1 (Mac) | 3,5 mm bak → J4 → 10k/10k-deler → PCM1808 ADC (I2S-master 48 kHz) → Pi (I2S inn) | alsaloop → «KI AUX1» → samme vei | samme |
| AUX 2 (PC) | 3,5 mm bak → J20 → 10k/4,7k-deler → PCM2900C USB-kodek → Pi-ens USB (J19) | alsaloop → «KI AUX2» → samme vei | samme |

Alle kildene ender altså digitalt i Pi-en og mikses der («Miks» i HA/Homey lar flere spille samtidig, hver med eget nivå). Én felles
DAC (PCM5102A, 48 kHz) gir analog lyd videre.

**Analog vei etter DAC:** DAC → 100 Ω/2,2 nF → 10 µF kobling → **PGA2311** (fast 0 dB-nivå; mutes ved standby) → to grener:
1. **TPA3116D2** klasse D, 26 dB, 2 × 50 W i 4–8 Ω → 10 µH/680 nF-filter → J2/J3 → høyttalerpoler bak.
2. **TPA6132A2** hodetelefonforsterker (−6 dB) → J23 → 3,5 mm i fronten. EN styres av MCP GPA6 (på bare når plugg står i).

**Utganger**

| Utgang | Kontakt | Merknad |
|---|---|---|
| Høyttalere L/R | 4 mm poler bak (J2/J3) | 2 × 50 W, BD-modus, dempes med SDZ (GPIO 22) ved hodetelefoner/standby |
| Hodetelefoner | 3,5 mm foran (J23) | auto-demping av høyttalerne, kan slås av i HA/Homey |
| 4 × USB-A | venstre side (J15–J18) | tastatur/mus/disk fra den valgte PC-en; 5 V via 2 A polyfuse; **Pi-en er ikke på huben** |
| LED-ringer | J10 | AIR/BT, RADIO, AUX, USB fra MCP GPB0-3 (low-side AO3400), POWER fra GPIO 12 (PWM) |
| Skjerm | J9 (OLED I2C) eller J13 (TFT SPI + touch) | OLED/TFT-logikk på alltid-3,3 V, TFT-baklys på 5V_SW |
| 5 V til Pi | J6 | 5,2 V/5 A fra bucken til header-pinne 2/6 |
| Talemeldinger | gjennom DAC/høyttalere | Kokoro (en) / Piper (no, trøndersk) |

**Styring**

| Funksjon | Hvordan |
|---|---|
| Strøm («smart relé») | GPIO 27 → Q7 → relé K1 (24 V til forsterkeren) og Q8 (5V_SW). Pi, hub, MCP23017, DAC, ADC-digital og skjermlogikk har strøm alltid, så alt våkner fra HA/Homey/AirPlay. Knapp bak (GPIO 15) og POWER foran (MCP GPA4) veksler |
| Knapper foran | MCP23017 GPA0-4 (BT, RADIO, AUX, USB, POWER) med 100 nF debounce; INT → GPIO 14 |
| Encoder | GPIO 23/24/25 (volum, trykk = mute, hold = kanalmeny) |
| USB-switch | MCP GPB4 → TS3USB221 S-pinne (lav = PC 1); fra USB-knappen, HA, Homey eller `/api/usbsw` |
| Hodetelefoner | jack-bryteren → MCP GPA5; GPA6 slår på TPA6132A2; SDZ demper TPA3116 |
| Volum | PGA2311 på fast nivå; hovedvolum og loudness i CamillaDSP, nivå per kilde i ALSA softvol |
| API/integrasjoner | daemon på port 8765 (`/api/status`, `/api/power`, `/api/input`, `/api/volume`, `/api/level`, `/api/mix`, `/api/usbsw`, `/api/hp_automute`, `/api/voice` …), HA-integrasjon 2.11, Homey-app 2.12 |

**Strømforsyning:** 19–24 V DC inn → KCD1 → 5 A sikring → TVS 33 V → 2 × 1000 µF → (a) relé → 24V_AMP til TPA3116, (b) TPS54560 buck → 5 V/5 A
(Pi, hub, relé-spole, Q8) → AMS1117 → 3,3 V (alltid). 5V_SW (bak Q8) → AMS1117 → 3V3_SW (TFT-baklys), LM2662 → −5 V og ferritt → 5VA
for PGA2311, PCM1808-analog, TPA6132A2, LED-ringer.

## Kjente kompromisser i rev B

- Én felles GND-sone; analog, USB og klasse D deler plan.
- AMS1117 har 10 µF keramisk på utgangen; blir den ustabil (støy på 3,3 V), lodd en 22 µF tantal/elektrolytt over C13.
- C1/C110: kjøp 1000 µF/35 V Ø10 med høyde ≤ 16 mm (kassen er 48 mm innvendig 43,5).
- USB-banene er ikke impedanskontrollerte (2 lag), men korte. Full speed/high speed over få cm går normalt fint.
- Freerouting-ruting er funksjonell, ikke optimal. Sjekk at 24 V- og høyttalersporene ikke har unødvendige vias.
- Relé-pinner: 1–2 spole, 4 COM, 5 NO (3 NC ubrukt) etter KiCad-footprinten for SRD. Mål med multimeter før første gang.
- TPS54560-kompensasjon er fra datablad-eksempelet; ikke målt.
- TPA6132A2 går på fast −6 dB; høyttalervolumet og hodetelefonvolumet følger hverandre (samme PGA2311/CamillaDSP-volum).
- PCM2900C: 1,5 kΩ pull-up på D+ til VCCCI er lagt til i tillegg til eventuell intern – sjekk at enumerasjon virker.
