# Deleliste når hovedkortet brukes

Hovedkortet (PCBWay, ferdig montert) erstatter: XH-M562, PCM5102A-modul, X9C103S ×2, relékort 4-ch, 1-ch relé, MOSFET-kort ×2, buck-moduler, 2200 µF (sitter på kortet), inline sikringsholder (klips på kortet), Dupont-ledninger, VHB-tape, nylon-avstandsstykker, M2.5-skruer til moduler.

## Fortsatt nødvendig (fra AliExpress-kurven)

| Del | Antall | Merknad |
|---|---|---|
| Raspberry Pi 4 B | 1 | har |
| OLED 2,42" SSD1309 I2C | 1 | |
| 12 mm LED-knapp | 4 | |
| 16 mm POWER-knapp | 1 | |
| KY-040 encoder (gjenget) + knott 30 × 17 | 1 + 1 | |
| Akryl 70 × 38 × 2 røykfarget | 1 | |
| KCD1 vippebryter | 1 | |
| DC-099 kontakt | 1 | |
| USB-C panelflens → **USB-C hann** 0,5 m | 1 | til Pi 4 |
| RJ45 panelforlenger 30 cm | 1 | |
| PJ392 3,5 mm jack | 1 | |
| Bananterminal ×4, bananplugg ×4 | | |
| 24 V 4 A adapter | 1 | |
| USB-isolator ADuM4160 | 1 | ved PC-en |
| Ferrittklips | 2 | |
| Kjøleribber Pi 4 | 1 sett | |
| M3 varmeinnsats ×4, M3 × 8 senkskrue ×8 | | lokk + frontplate |
| M3 × 6 skrue ×4 | | hovedkortet på stolpene (ny: kortet bruker M3, ikke M2,5) |
| M2,5 × 6 ×4 | | Pi 4 |
| M2 avstandsstykke 6 mm + mutter ×4 | | OLED |
| 18 AWG rød/svart | 1 m | 24 V inn, høyttalere, 5 V til Pi |
| Skjermet lydkabel | 0,5 m | PJ392 → J4 |
| Treskrue 4 × 25 ×4, gummiføtter | | |

## Nytt – legg til

| Del | Antall | Søk |
|---|---|---|
| JST XH 2,54 mm… **2,5 mm** ferdigkrimpet kabel-sett (2–6 pinner, 20–30 cm, hunn-hus) | 1 sett | [JST XH 2.5mm pre-crimped cable kit](https://www.aliexpress.com/w/wholesale-jst-xh-2.5mm-pre-crimped-cable-kit.html) – til J4, J7, J8, J9, J10 |
| 40-pin IDC flatkabel hunn–hunn, 10 cm | 1 | [40 pin IDC ribbon cable female 2x20](https://www.aliexpress.com/w/wholesale-40-pin-idc-ribbon-cable-female-2x20.html) – Pi ↔ J5 |
| Flatstifthylser 4,8 mm | 2 | KCD1 (har i kurven) |
| Sikring 5 × 20 mm 5 A | 2 | følger inline-settet; brukes i F1-klipsene på kortet |
| M3 messing-avstandsstykke 6 mm hunn–hunn ×4 | valgfritt | hvis kortet skal sitte høyere enn stolpene (ikke nødvendig) |

## Kabling (panel → kort)

| Panel | Kortet |
|---|---|
| DC-099 + → KCD1 → J1 pinne 1 (+), DC-099 − → J1 pinne 2 | 18 AWG |
| Høyttalerterminaler R → J3 (+ −), L → J2 (+ −) | 18 AWG |
| PJ392 tip/ring/sleeve → J4 1/2/3 | skjermet |
| Knappenes bryter (C) → J7 1–5, NO → J7 6 (GND, samles) | JST XH 6 |
| Knappenes LED-ring + → J10 1 (5 V), − → J10 2–6 | JST XH 6 |
| KY-040 CLK/DT/SW/+/GND → J8 1–5 | JST XH 5 |
| OLED VCC/GND/SDA/SCL/RES → J9 1–5 (DC og CS på OLED til GND) | JST XH 5 |
| J6 (5 V, GND) → Pi 4 header pinne 2 og 6 | 18 AWG, Dupont-hunn i enden |
| J5 → Pi 4 GPIO | 40-pin flatkabel |
| USB-C flens → Pi 4 USB-C · RJ45-forlenger → Pi 4 Ethernet | |

## Plugger til hovedkortets kontakter

Kortet har JST XH (2,5 mm) hann-lister, skruterminaler og en 2×20 header. Det du trenger på kabelsiden:

| Kontakt på kortet | Plugg | Antall | Andre enden | Søk på AliExpress |
|---|---|---|---|---|
| J7 KNAPPER (XH 6-pin) | XH hunn-hus 6-pin m/ledninger | 1 | loddes på knappenes bryterpinner (C og NO) | [JST XH 2.5mm 6 pin female cable 30cm](https://www.aliexpress.com/w/wholesale-jst-xh-2.5mm-6-pin-female-cable-30cm.html) |
| J10 LED-RINGER (XH 6-pin) | XH hunn-hus 6-pin m/ledninger | 1 | loddes på knappenes LED + / − | samme søk |
| J8 ENCODER (XH 5-pin) | XH hunn-hus 5-pin → Dupont hunn 5-pin | 1 | KY-040 har hann-pinner | [JST XH 2.5mm to Dupont female cable](https://www.aliexpress.com/w/wholesale-jst-xh-2.5mm-to-dupont-female-cable.html) |
| J9 OLED (XH 5-pin) | XH hunn-hus 5-pin → Dupont hunn | 1 | OLED-modulen har hann-pinner (7; DC og CS lenkes til GND med to korte Dupont) | samme søk |
| J4 AUX (XH 3-pin) | XH hunn-hus 3-pin m/ledninger | 1 | loddes på PJ392 (L, R, GND) | [JST XH 2.5mm 3 pin female cable](https://www.aliexpress.com/w/wholesale-jst-xh-2.5mm-3-pin-female-cable.html) |
| J5 Pi (2×20 header) | 40-pin IDC flatkabel hunn–hunn 10 cm | 1 | Pi 4 GPIO | [40 pin GPIO ribbon cable female 10cm](https://www.aliexpress.com/w/wholesale-40-pin-gpio-ribbon-cable-female-10cm.html) |
| J1 24 V, J2/J3 SPK, J6 5 V (skruterminal 5,08) | ingen plugg – avisolert 18 AWG rett i skruen | – | DC-099/KCD1, bananterminaler, Pi header pinne 2/6 (Dupont hunn 18 AWG eller lodd) | [18 AWG silicone wire red black](https://www.aliexpress.com/w/wholesale-18-awg-silicone-wire-red-black.html) |

Enklest er et **ferdigkrimpet XH-sett** («JST XH 2.5mm pre-crimped cable kit», 2–6 pinner, 20–30 cm, hus på én side, åpen ende på den andre): da lodder du den åpne enden rett på knapper/jack, og setter Dupont-hunn på de som skal på encoder/OLED (krimpes med «SN-28B»-tang, eller kjøp kabler som har XH i én ende og Dupont i den andre). Ta med litt 2 mm krympestrømpe. Vil du slippe lodding på knappene finnes 12/16 mm metallknapper med ferdig pigtail (søk «12mm metal push button with wire harness»).

Pinnerekkefølge (pinne 1 er merket med firkantet pad / strek på silketrykket): J7 = AIR, BT, AUX, USB, POWER, GND · J10 = 5 V, AIR−, BT−, AUX−, USB−, POWER− · J8 = CLK, DT, SW, 3V3, GND · J9 = 3V3, GND, SDA, SCL, RES · J4 = L, R, GND.
