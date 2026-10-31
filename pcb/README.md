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
| 24 V inn | skruterminal → sikring 5 A (5×20, THT) → reverspolaritets-FET → TVS SMBJ28A → 2 × 1000 µF Ø10 (THT, maks 16 mm høye – kassen er 48 mm) | KCD1 hovedbryter i serie utenfor kortet |
| 5 V / 5 A (alltid) | TPS54560 buck, 400 kHz, 10 µH, 3 × 47 µF, satt til 5,06 V (33k/6,2k) | Pi 4 («5V PI»), USB-hub, relé-spole |
| **Smart relé** | SRD-05VDC-SL-C (24 V → forsterker) + AO3401 P-MOSFET (5 V → 5V_SW) fra GPIO 27 via AO3400 | 5V_SW: LED-ringer, ADC-analog, TFT-baklys (PGA2311 og hodetelefonforsterkeren er alltid på, men mutet i standby). Av = helt stille og mørkt. Knapp bak på GPIO 15 |
| 3,3 V (alltid) | AMS1117-3.3 | MCP23017, pull-ups, encoder, **DAC, ADC-digital, oscillator, OLED og TFT-logikk** (Pi-ens I2C/SPI/I2S må aldri drive inn i strømløse kretser; skjermen slukkes i programvare) |
| 3,3 V_SW | AMS1117-3.3 fra 5V_SW | bare TFT-baklyset (Q9/Q10) |
| −5 V | LM2662 (FC = V+, 150 kHz) fra alltid-på 5 V, 10 µF inn/fly/ut | PGA2311 VA− (10–12 mA) |
| DAC | PCM5102A, I2S-slave, SCK = GND (intern PLL), FLT/DEMP/FMT = GND, XSMT fra GPIO 26 | 100 Ω + 2,2 nF ut |
| **ADC AUX 1** | PCM1808, I2S-master 256 fs fra 12,288 MHz-oscillator (48 kHz) | Pi-en er I2S-slave. Inngang 10k/10k-deler, 4,7 µF, 1 kΩ + 1 nF |
| **USB-kodek AUX 2** | PCM2900C, 12 MHz-krystall, bus-powered fra en USB-port på Pi-en (J19) | Inngang 10k/4,7k-deler, 4,7 µF. Vises som «USB Audio CODEC» |
| Volum | PGA2311 (±5 V), bit-banget fra GPIO 0 (SDI), 1 (SCLK), 16 (CS) – header 27/28/36, 5 V via ferritt + 10 µF | fast nivå; volum og nivå per kilde gjøres digitalt |
| Forsterker | TPA3116D2DAD, 26 dB (100k/20k), BD-modus (MODSEL = GND), 400 kHz (AM = 000), MUTE = GND, SYNC åpen, PLIMIT = GVDD, 10 µH + 680 nF + snubber per utgang | **Kjøleflaten er på toppen**: ingen loddepasta under, kjøleribbe 20 × 20 limes på. SDZ fra GPIO 22 |
| **USB-switch** | FE1.1s 4-ports hub + TS3USB221 2:1-mux (OE = GND). 2 × USB-C (PC 1/PC 2) på kortet, 4 × USB-A i venstre kant, polyfuse 2 A | Mux-valg fra MCP23017 GPB4 (S lav = PC 1). CC-pinnene har 5,1 k, så USB-C–USB-C-kabel virker. Huben og muxen går på alltid-5 V |
| I/O-ekspander | MCP23017 (I2C 0x20), INT → GPIO 14 | GPA0-4 knapper AIR/BT/AUX/USB/PWR, GPA5 jack-deteksjon, GPA6 HP-EN, GPB0-3 LED-ringer, GPB4 USB-mux, **GPB5 overtemperatur (NTC)**; GPA7 ligger på «EXP» men kan bare brukes som utgang (Microchip-errata: GPA7/GPB7 er ikke innganger) |
| **Overtemperaturvakt** | NTC 10 k (B 3950) på kjøleribben → J24 → 3,3 k-deler → 74LVC1G14 Schmitt-inverter (U14) → MCP GPB5. 100 k pull-down så «kald» hvis U14 mangler | Vipper ved ca. 75 °C, tilbake ved ca. 50 °C. Daemonen demper TPA3116 (SDZ) mens den er varm og melder i loggen/`/api/state` (`overtemp`) |
| LED-ringer | 5 × AO3400 low-side | POWER-ring på GPIO 12 (PWM) |
| **Hodetelefoner** | TPA6132A2 (DirectPath, +6 dB) etter PGA2311, 1 µF inn, alltid-på 5 V (EN kommer fra alltid-på MCP, og må aldri være høyere enn VDD). EN fra MCP23017 GPA6; jack-bryteren (DET) via 10 k til GPA5, 10 k pulldown på OUTL gir sikker «lav» uten plugg | 3,5 mm PJ-392 i fronten under POWER (J23). Ved innplugging dempes TPA3116 (SDZ) – kan slås av i HA/Homey |
| TFT | 14-pinners header (standard 2,4"/2,8" ILI9341/ST7789V-modul med XPT2046) | SPI0 CE0 (GPIO 8) = TFT, CE1 (GPIO 7) = touch med 10 k pull-up, DC 5, RST 6, IRQ 17, baklys GPIO 13 (PWM) via AO3400 + AO3401 fra 3V3_SW |

## GPIO-kart (hovedkort rev B)

| GPIO | Bruk | GPIO | Bruk |
|---|---|---|---|
| 2, 3 | I2C: OLED, MCP23017 | 18, 19, 21, 20 | I2S BCK, LRCK, DAC-data, ADC-data (Pi er slave) |
| 4 | OLED RES | 22 | TPA3116 SDZ (høy = på) |
| 5, 6, 13 | TFT DC, RST, baklys (PWM) | 23, 24, 25 | encoder CLK, DT, SW |
| 7, 8 | SPI0 CE1 touch, CE0 TFT | 26 | DAC XSMT |
| 0, 1 (header 27/28) | PGA2311 SDI, SCLK (ID-EEPROM-pinnene – ingen HAT-EEPROM på kortet) | 16 | PGA2311 CS |
| 9, 10, 11 | SPI0 MISO (bare touch – TFT-ens SDO er ikke koblet), MOSI, SCLK | 27 | strømrelé + 5V_SW |
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
| J11 / J12 | USB-C på kortet, i bakkanten (åpningen mot bakpanelet) | PC 1 / PC 2 → panelmontert USB-C bak; panelkabelens hann-plugg settes rett i, 15–20 cm |
| J13 | 1×14 header 2,54 | TFT: VCC GND CS RST DC MOSI SCK LED (MISO ikke koblet) T_CLK T_CS T_DIN T_DO T_IRQ (samme rekkefølge som modulen) |
| J15–J18 | USB-A | 4 × USB-A ut gjennom venstre vegg |
| J19 | JST XH 4 | 5V, D−, D+, GND fra en USB-A-port på Pi-en (USB-kodeken) |
| J21 | JST XH 2 | strømknapp bak (momentan), GND |
| J22 | JST XH 6 | EXP: MCP GPA5 (= jack-deteksjon via 10 k), GPA6 (= HP-EN), GPA7 (ledig, bare utgang), GPB5 (= overtemperatur fra U14 – ikke driv den), 3V3, GND |
| J24 | JST XH 2 | NTC 10 k (B 3950) festet på kjøleribben (ikke polarisert) |
| J23 | JST XH 4 | Hodetelefonjack i fronten (PJ392 med bryter, under POWER): L, R, GND, DET (jackens bryterkontakt for L: ligger mot L uten plugg, åpen med plugg) |

## Filer

- `build_board.py` – hele kortet (deler, netliste, plassering) som Python mot pcbnew. Kjør for å regenerere `.kicad_pcb`.
- `build_schematic.py` – lager skjemaet `ki_pultforsterker_main.kicad_sch` (ett A1-ark, delene gruppert i blokker, globale etiketter med nettnavnene) fra kortet, pluss egne symboler i `ki_pultforsterker.kicad_sym`; verifiserer netlisten pinne for pinne mot `.kicad_pcb` (må gi 0 avvik), kjører ERC og lager `produksjon/skjema.pdf`/`.svg`. Kjør `python3 build_schematic.py` for å regenerere (etter `build_board.py`/`export.py`).
- `route.py` – eksporterer DSN og kjører Freerouting (`FREEROUTING=/sti/freerouting.jar python3 route.py`).
- `export.py` – importerer SES, fyller GND-soner, kjører DRC, lager `produksjon/`.
- `produksjon/ki_pultforsterker_main_gerber.zip` – last opp til JLCPCB/PCBWay (2 lag, 1,6 mm, HASL eller ENIG, 1 oz).
- `produksjon/ki_pultforsterker_main_bom.csv` + `_cpl.csv` – for SMT-montering (LCSC-numre).
- `bom.csv` – full deleliste per referanse.

## Bestilling

1. JLCPCB → «Add gerber file» → zip-en. 2 lag, 180 × 100 mm, grønn/svart, HASL (lead free).
2. Huk av «PCB Assembly», Top side, 2 stk. Last opp BOM og CPL.
3. Kontroller at alle LCSC-numre finnes på lager; bytt tilsvarende hvis noen er tomme (verdiene står i BOM). Alle koder i BOM-en er
   verifisert mot lcsc.com/jlcpcb.com i granskningen (se `GRANSKNING_REV_B.md`), men lager endrer seg – **les beskrivelsen JLCPCB viser
   per linje** og sammenlign med Comment-kolonnen (verdi, spenning, pakke). IC-ene: TPS54560DDAR (C31966), PCM5102APWR (C107671),
   PCM1808PWR (C55513), TPA3116D2DADR (C50144), PGA2311UA (C486061), FE1.1s (C9359), PCM2900C (C180425), TS3USB221RSER (C130085),
   MCP23017 (C506653), TPA6132A2 (C69901), 12,288 MHz-oscillator (C437124, lite lager – reserve C789111 SiTime 3225 eller C253724 KDS), L1 SRP1245A-100M (C2042471; alternativ CEC SMRH125-100M C241221 på samme pads).
   Alle linjer har nå kode som var på lager hos JLCPCB 31.10.2026 (sjekket i JLCPCBs eget søk): U7 FE1.1s = C9359 (C6706491 var utsolgt),
   L2–L5 Bourns SRR1260-100M = C3221699 (samme pad-mønster som footprinten), R3 243 k = C100895, D5 BZT52C12 = C43491, Q11 AOD409 = C36220,
   R21–R24 18 Ω 1206 = C2907439, U14 SN74LVC1G14DBVR = C7835, D1 SMBJ28A = C20623778, D2 SS56 SMB = C4154973. **L1 (C2042471) har lite lager** –
   alternativ på samme pads: CEC SMRH125-100M (C241221) eller Bourns SRR1260-100M (C3221699, 5,5 A – nok for bucken).
   Alle IC-ene er «extended parts» (engangsgebyr per type).
   **THT-deler er ikke i BOM/CPL** – de står i `ki_pultforsterker_main_tht_handlodding.csv` og loddes selv (punkt 5).
4. Festehull: H1–H4 M3 (stolper i kassen), H5–H8 M2,5 (Raspberry Pi 4 under kortet).
5. THT-deler loddes selv etter levering: J1–J3, J6 (skruterminaler), J4/J7–J10/J19–J22 (JST), J5 (2×20 **hann**-header, C50980), J13 (header), F1 (sikringsklips
   for 5×20, f.eks. Keystone 3512 eller C3130 + sikring 5 A), C1 + C110 (1000 µF), K1 (relé), J15–J18 (USB-A), J23 (JST). Liste: `produksjon/ki_pultforsterker_main_tht_handlodding.csv`; ferdig LCSC-bestilling (kode, antall, MOQ) i `produksjon/lcsc_bestilling_tht.csv` – legg den i samme sending som JLCPCB-ordren («Combine with LCSC order»). Flatkabel 2×20 15–20 cm finnes ikke på LCSC (AliExpress/Kjell).
6. Alle gjennompletterte pads har termisk avlastning mot jordplanet (lar seg håndlodde). Kassens fire M3-hull har kobberfri sone – kortet jordes til kassen bare via jordpunktet bak.
7. Kjøleribbe 20 × 20 × 10 mm med termisk tape (1,5–2 mm) på toppen av TPA3116. NTC-en (10 k, B 3950, glass- eller epoksyperle) limes/teipes på ribbens side med varmeledende lim eller Kapton, ledning til J24.

## Slik virker kortet – funksjoner, innganger og utganger

**Innganger (lydkilder)**

| Kilde | Vei inn | Hvor lyden går | Nivå/volum |
|---|---|---|---|
| AirPlay 2 | nettverk → Pi (Shairport Sync) | ALSA softvol «KI AirPlay» → dmix → CamillaDSP → I2S → PCM5102A (DAC) | nivå per kilde + hovedvolum digitalt |
| Bluetooth A2DP | Pi-ens BT → bluealsa | «KI Bluetooth» → samme vei | samme |
| USB-lyd fra én PC | tredje USB-C bak («Pi») → forlenger rett til Pi-ens USB-C-port (Pi er USB-lydkort/UAC2-gadget). **Uavhengig av USB-switchen** – den PC-en som står i denne kontakten får USB-lyd | «KI USB» → samme vei | samme |
| Radio (Lyrion) | nettverk → squeezelite | «KI Radio» → samme vei | samme |
| AUX 1 (Mac) | 3,5 mm bak → J4 → 10k/10k-deler → PCM1808 ADC (I2S-master 48 kHz) → Pi (I2S inn) | alsaloop → «KI AUX1» → samme vei | samme |
| AUX 2 (PC) | 3,5 mm bak → J20 → 10k/4,7k-deler → PCM2900C USB-kodek → Pi-ens USB (J19) | alsaloop → «KI AUX2» → samme vei | samme |

Alle kildene ender altså digitalt i Pi-en og mikses der («Miks» i HA/Homey lar flere spille samtidig, hver med eget nivå). Én felles
DAC (PCM5102A, 48 kHz) gir analog lyd videre.

**Analog vei etter DAC:** DAC → 100 Ω/2,2 nF → 10 µF kobling → **PGA2311** (fast 0 dB-nivå; mutes ved standby) → to grener:
1. **TPA3116D2** klasse D, 26 dB, 2 × 50 W i 4–8 Ω → 10 µH/680 nF-filter → J2/J3 → høyttalerpoler bak.
2. **TPA6132A2** hodetelefonforsterker (+6 dB) → J23 → 3,5 mm i fronten. EN styres av MCP GPA6 (på bare når plugg står i).

**Utganger**

| Utgang | Kontakt | Merknad |
|---|---|---|
| Høyttalere L/R | 4 mm poler bak (J2/J3) | 2 × 50 W, BD-modus, dempes med SDZ (GPIO 22) ved hodetelefoner/standby |
| Hodetelefoner | 3,5 mm foran (J23) | auto-demping av høyttalerne, kan slås av i HA/Homey |
| 4 × USB-A | venstre side (J15–J18) | tastatur/mus/disk fra den valgte PC-en (USB-C PC 1/PC 2 bak → TS3USB221-mux → FE1.1s-hub); 5 V via 2 A polyfuse; **Pi-en er ikke på huben** – ingen lyd går gjennom switchen |
| LED-ringer | J10 | AIR/BT, RADIO, AUX, USB fra MCP GPB0-3 (low-side AO3400), POWER fra GPIO 12 (PWM) |
| Skjerm | J9 (OLED I2C) eller J13 (TFT SPI + touch) | OLED/TFT-logikk på alltid-3,3 V, TFT-baklys på 5V_SW |
| 5 V til Pi | J6 | 5,06 V/5 A fra bucken til header-pinne 2/6 |
| Talemeldinger | gjennom DAC/høyttalere | Kokoro (en) / Piper (no, trøndersk) |

**Styring**

| Funksjon | Hvordan |
|---|---|
| Strøm («smart relé») | GPIO 27 → Q7 → relé K1 (24 V til forsterkeren) og Q8 (5V_SW). Pi, hub, MCP23017, DAC, PGA2311, hodetelefonforsterker, ADC-digital og skjermlogikk har strøm alltid, så alt våkner fra HA/Homey/AirPlay. Knapp bak (GPIO 15) og POWER foran (MCP GPA4) veksler |
| Knapper foran | MCP23017 GPA0-4 (BT, RADIO, AUX, USB, POWER) med 100 nF debounce; INT → GPIO 14 |
| Encoder | GPIO 23/24/25 (volum, trykk = mute, hold = kanalmeny) |
| USB-switch | MCP GPB4 → TS3USB221 S-pinne (lav = PC 1); fra USB-knappen, HA, Homey eller `/api/usbsw` |
| Hodetelefoner | jack-bryteren → MCP GPA5; GPA6 slår på TPA6132A2; SDZ demper TPA3116 |
| Volum | PGA2311 på fast nivå; hovedvolum og loudness i CamillaDSP, nivå per kilde i ALSA softvol |
| API/integrasjoner | daemon på port 8765 (`/api/status`, `/api/power`, `/api/input`, `/api/volume`, `/api/level`, `/api/mix`, `/api/usbsw`, `/api/hp_automute`, `/api/voice` …), HA-integrasjon 2.11, Homey-app 2.12 |

**Strømforsyning:** 19–24 V DC inn → KCD1 → 5 A sikring → reverspolaritets-FET → TVS 28 V → 2 × 1000 µF → (a) relé → 24V_AMP til TPA3116, (b) TPS54560 buck → 5 V/5 A
(Pi, hub, relé-spole, Q8) → AMS1117 → 3,3 V (alltid). 5V_SW (bak Q8) → AMS1117 → 3V3_SW (TFT-baklys), LM2662 → −5 V og ferritt → 5VA
for PGA2311, PCM1808-analog, TPA6132A2, LED-ringer.

## Sikkerhet og vern

| Fare | Vern på kortet | Merknad |
|---|---|---|
| Feil polaritet på 24 V | **P-MOSFET Q11** i pluss-linjen etter sikringen (body-dioden leder ved riktig polaritet, FET-en slår på; feil vei = brudd). Zener 12 V + 100 k beskytter gaten | Kortet tåler reversert adapter uten skade. DC-kontakten er senter-pluss |
| Overspenning/transienter på 24 V | TVS SMBJ28A etter FET-en, 2 × 1000 µF | Står av ved 28 V, klemmer ved ca. 45 V; TPA3116 abs. maks 30 V, bucken 60 V. Bruk en adapter på 19–24 V – 28 V-adapter går ikke |
| Overstrøm 24 V | Sikring 5 A treg (5 × 20) | Full styrke på begge kanaler + Pi 3 A ≈ 5,5 A kortvarig; normal bruk < 1 A. Er sikringen plagsom: 6,3 A T |
| Kortslutning på høyttalerutgang / mot kassen | TPA3116 har intern kortslutnings-, DC- og overtemperaturbeskyttelse (FAULT) | Utgangene ligger på ca. 12 V DC mot GND (BD-modus) – høyttalerpolene **må** være isolert fra den metalliske kassen (isolerende krage/krympestrømpe) |
| Kortslutning på hodetelefonutgang | TPA6132A2 har kortslutningsvern | |
| Overstrøm USB-A | Polyfuse 2 A (F2) på 5V_USB | Hub-brikken har også OVCJ |
| ESD på USB-kontaktene | **USBLC6-2SC6 på alle seks** (4 × USB-A, 2 × USB-C) | Viktig i metallkasse med tilgjengelige porter |
| 5 V til Pi | Bucken strømbegrenser (~7 A) | **Aldri USB-C-strøm i Pi-en samtidig med J6** – to forsyninger i parallell uten dioder. Dette gjelder også «SERV»-kontakten bak: en PC legger 5 V på VBUS. Bruk en SERV-hale med **VBUS brutt** (klipp den røde lederen, eller en data-only-adapter) så Pi-en bare får 5 V fra J6 |
| Overtemperatur | NTC på kjøleribben → U14 → MCP GPB5 | Daemonen demper forsterkeren over ca. 75 °C og slipper den ved ca. 50 °C. TPA3116 har i tillegg eget 150 °C-vern |
| Overtemperatur | TPA3116 og TPS54560 har termisk nedstenging | Kjøleribben på TPA3116: 20 × 20 × 15 mm med 1 mm termisk pute mot lokket gjør kassen til kjøleribbe (lokkets innside er 46,5 mm over bunnen) |
| Plopp/klikk i høyttalerne | Programvaren slår av SDZ og XSMT før releet, og på i motsatt rekkefølge med pause; PGA2311 mutes i standby | |
| Klipping/for høyt nivå | PGA2311 står fast på −9 dB (`KI_AMP_PGA_DB`): full digital styrke = 0,74 Vrms inn på TPA3116 = like under klipping ved 24 V. Hodetelefonforsterkeren har +6 dB (≈ 20 mW i 32 Ω) | Volumramp fra 0 ved oppstart i programvaren |
| Jordløkker/brum | Én jordsone; kassen kobles til signal-GND bare i jordpunktet bak (stjernejord) | DC-kontakten bak **må** ha plastisolert krage (DC-099/DC-022 med nylonhylse), ellers blir dens hylse et ekstra jordpunkt. Høyttalerpolene isoleres fra panelet. USB-isolator på SERV-kabelen hvis det brummer med PC tilkoblet |
| Strømløse kretser på aktive busser | DAC, ADC-digital, OLED/TFT-logikk og MCP23017 går på alltid-3,3 V | Ingen backfeed gjennom ESD-dioder når 5V_SW er av |

**Ikke med (vurdert):** inrush-begrenser på 24 V (2 × 1000 µF gir kort inrush som adapteren tåler), separat sikring på 5 V til Pi (bucken begrenser), relé-kontaktvern (24 V DC 4,7 A er innenfor 10 A/30 VDC).

**Alltid-på vs. svitsjet (regel: ingen logikk fra alltid-på-siden skal drive inn i en strømløs krets):** PGA2311 VD+/ZCEN, TPA6132A2 VDD/G0/G1, MCP23017, DAC, ADC-digital, OLED og TFT-logikk går på alltid-på 5 V/3,3 V. 5V_SW: PGA2311 VA+ (og −5 V), ADC-analog, LED-ringer, TFT-bakgrunnslys. SDZ til TPA3116 går via 1 k og holdes lav i standby. Bucken slår på ved ca. 9 V inn (330 k/51 k på EN) så EN tåler en TVS-klemming.

**Første oppstart – sjekkliste:** (1) uten Pi og uten høyttalere: 24 V på J1 → mål 5,0–5,1 V på J6, 3,3 V på J22 pinne 5, 0 V på LED-ringkontakten J10 pinne 1 (5V_SW av). (2) Relé: brudd mellom K1 pinne 1 og 3 uten spole. (3) Sett i Pi, start; slå på fra HA → 5V_SW 5 V, −5 V på C16, 24V_AMP på C40. (4) Høyttalere på, volum 15 %.

## Kjente kompromisser i rev B

- Én felles GND-sone; analog, USB og klasse D deler plan.
- AMS1117 har 10 µF keramisk på utgangen; blir den ustabil (støy på 3,3 V), lodd en 22 µF tantal/elektrolytt over C13.
- C1/C110: kjøp 1000 µF/35 V Ø10 med høyde ≤ 16 mm (kassen er 48 mm innvendig 43,5).
- USB-banene er ikke impedanskontrollerte (2 lag), men korte. Full speed/high speed over få cm går normalt fint.
- Freerouting-ruting er funksjonell, ikke optimal. Sjekk at 24 V- og høyttalersporene ikke har unødvendige vias.
- Relé-pinner etter KiCad-footprinten for SRD: **2 og 5 = spole, 1 = COM (den forskjøvede), 3 = NO (24 V inn), 4 = NC (ubrukt)**. Mål med multimeter
  før første gang: uten strøm på spolen skal det være brudd mellom pinne 1 og 3. Er det kortslutning, er NO/NC byttet – flytt 24 V-inn til pinne 4 med en jumper.
- TPS54560-kompensasjon (13,3 k/3,3 n/47 p) gir ca. 24 kHz crossover med 10 µH/3 × 47 µF – stabil, men TI-eksempelet bruker 16,9 k/4,7 n. Ikke målt.
- Ingen fiducialer på kortet; JLCPCB krever det ikke. CPL-filen har JLCPCBs rotasjonskorreksjoner (SOT-23/SOT-223/elektrolytt +180°, SOIC/SSOP/TSSOP/QFN +270°),
  men sjekk pinne-1-prikken og «+» på C40/C41/C72 i CPL-forhåndsvisningen – JLCPCB plasserer etter bildet.
- Buck-utgangen er 5,06 V (33 k/6,2 k, begge Basic-deler) – innenfor PGA2311/PCM1808/USB-kravet (≤ 5,25 V) og Pi 4-kravet (≥ 4,75 V ved headeren).
- PGA2311 (VD+, VA+ via FB1, VA− fra LM2662) og MUTE-pullupen går på alltid-på 5 V, ikke 5V_SW: VA+ og VD+ må følge hverandre, og DAC-en
  (alltid på) ville ellers drive inn i en strømløs PGA i standby. Standby-stillhet gis av SDZ (TPA3116), EN (TPA6132A2) og PGA-mute i programvaren.
- Høyttalersporene (OUT*/SPK_*) har strekninger på 0,4–0,5 mm der naborutingen ikke ga plass til mer. Bestill **2 oz kobber** – da tåler de
  full effekt uten nevneverdig oppvarming (1 oz holder til normal lytting).
- TPA6132A2 går på fast +6 dB; høyttalervolumet og hodetelefonvolumet følger hverandre (samme PGA2311/CamillaDSP-volum).
- PCM2900C: 1,5 kΩ pull-up på D+ til VCCCI er lagt til i tillegg til eventuell intern – sjekk at enumerasjon virker.
