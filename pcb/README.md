# KI Pultforsterker – hovedkort rev A

Ett kort (150 × 100 mm, 2 lag) som erstatter alle modulene: forsterker, DAC, volum, inngangsvalg, strømforsyning, LED-drivere og alle kontakter. Raspberry Pi 4 kobles til med 40-pinners flatkabel; frontdelene (knapper, encoder, OLED) med JST XH-plugger.

**Status: rev A er ikke prøvd i praksis.** Kortet er tegnet og autorutet med KiCad 7 og Freerouting, DRC er ren, men ingen har bygget det ennå. Regn med at første utgave kan trenge en jumper eller to. Modulbygget i resten av repoet er den sikre veien; kortet er oppgraderingen.

## Blokker

| Blokk | Krets | Merknad |
|---|---|---|
| 24 V inn | skruterminal → sikring 5 A (5×20, THT) → TVS SMBJ33A → 2200 µF (THT) | KCD1 hovedbryter i serie utenfor kortet |
| 5 V / 5 A | TPS54560 buck, 400 kHz, 10 µH, 3 × 47 µF | forsyner Pi 4 (egen terminal «5V PI»), relé, LED-ringer, PGA2311 |
| 3,3 V | AMS1117-3.3 | DAC, pull-ups, OLED |
| −5 V | ICL7660 ladepumpe | PGA2311 VA− |
| DAC | PCM5102A, I2S fra Pi | 100 Ω + 2,2 nF ut |
| Inngangsvalg | Omron G6K-2P-Y DPDT-relé, AO3400-driver | NC = DAC, NO = AUX. GPIO 22 |
| Volum | PGA2311 (±5 V), SPI0 fra Pi | 0,5 dB-trinn, −95,5…+31,5 dB |
| Forsterker | TPA3116D2, 26 dB, BD-modus, 400 kHz, 10 µH + 680 nF + snubber 18 Ω/330 pF per utgang | SDZ fra GPIO 27 = standby (erstatter relé 3). PLIMIT = GVDD (R18 for begrensning) |
| LED-ringer | 5 × AO3400 low-side, 100 Ω gate, 100 k pulldown | POWER-ring på GPIO 12 (PWM0) |
| Knapper/encoder | 10 k pull-up + 100 nF | |

## GPIO-kart (hovedkort)

Samme som modulbygget bortsett fra: knapper AUX/USB på **GPIO 14/15**, LED-ringer AIR/BT/AUX/USB på **7/9/17/20**, POWER-ring **12** (PWM), PGA2311 på **SPI0** (MOSI 10, SCLK 11, CE0 8), DAC XSMT på **26**, forsterker SDZ på **27**. X9C utgår. Sett `KI_AMP_BOARD=main` i `/etc/ki-amp.env`.

## Kontakter

| Ref | Type | Pinner |
|---|---|---|
| J1 | skruterminal 5,08 | 24 V +, GND (fra DC-099 via KCD1) |
| J2 / J3 | skruterminal 5,08 | SPK L + −, SPK R + − |
| J4 | JST XH 3 | AUX L, R, GND (fra PJ392) |
| J5 | 2×20 header | Raspberry Pi 40-pin (flatkabel) |
| J6 | skruterminal 5,08 | 5 V, GND → Pi 4 header pinne 2/6 (18 AWG) |
| J7 | JST XH 6 | AIR, BT, AUX, USB, POWER, GND (bryterne) |
| J8 | JST XH 5 | CLK, DT, SW, 3V3, GND (encoder) |
| J9 | JST XH 5 | 3V3, GND, SDA, SCL, RES (OLED) |
| J10 | JST XH 6 | 5 V, AIR−, BT−, AUX−, USB−, POWER− (LED-ringer) |

## Filer

- `build_board.py` – hele kortet (deler, netliste, plassering) som Python mot pcbnew. Kjør for å regenerere `.kicad_pcb`.
- `board.dsn` / `board.ses` – autoruting (Freerouting): `xvfb-run java -jar freerouting.jar -de board.dsn -do board.ses -mp 40`
- `export.py` – importerer SES, fyller GND-soner, kjører DRC, lager `produksjon/`.
- `produksjon/ki_pultforsterker_main_gerber.zip` – last opp til JLCPCB/PCBWay (2 lag, 1,6 mm, HASL eller ENIG, 1 oz).
- `produksjon/ki_pultforsterker_main_bom.csv` + `_cpl.csv` – for SMT-montering (JLCPCB-format, LCSC-numre).
- `bom.csv` – full deleliste per referanse.

## Bestilling

1. JLCPCB → «Add gerber file» → zip-en. 2 lag, 150 × 100 mm, grønn/svart, HASL (lead free).
2. Huk av «PCB Assembly», Top side, 2 stk. Last opp BOM og CPL.
3. Kontroller at alle LCSC-numre finnes på lager; bytt tilsvarende hvis noen er tomme (verdiene står i BOM).
4. THT-deler loddes selv etter levering: J1–J3, J6 (skruterminaler), J4/J7–J10 (JST), J5 (header), F1 (sikringsklips), C1 (2200 µF), K1 (relé – kan også monteres av JLC som THT).

## Kjente kompromisser i rev A

- Én felles GND-sone; analog og klasse D deler plan. Forsterkerdelen ligger øverst til høyre, DAC/PGA nederst – holdt adskilt, men ikke stjernejordet.
- Freerouting-ruting er funksjonell, ikke optimal. Sjekk at 24 V- og høyttalersporene (2,0 / 1,5 mm) ikke har unødvendige vias.
- TPS54560 kompensasjon (13,3 k / 3,3 nF / 47 pF) er fra datablad-eksempelet for 5 V; ikke målt.
