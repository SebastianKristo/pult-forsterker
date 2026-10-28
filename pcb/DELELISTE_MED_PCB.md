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
| 40-pin IDC flatkabel hunn–hunn, 15–20 cm | 1 | [40 pin IDC ribbon cable female 2x20](https://www.aliexpress.com/w/wholesale-40-pin-idc-ribbon-cable-female-2x20.html) – Pi ↔ J5 |
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
