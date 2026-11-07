# Skjold Fjernkontroll

En universell fjernkontroll for hele stua: 2,8″ fargeberøringsskjerm øverst, nesten fra kant til kant, 44 taster under, IR foran og Wi-Fi inni. Den styrer Skjold direkte (volum, spill/pause, favoritter, kilder og rom), sender og lærer IR-koder til TV, projektor og annet, og kjører aktiviteter som «Se TV» og «God natt» som setter i gang IR, Skjold og Home Assistant i én operasjon. Alle tastene sendes også til Home Assistant, så du kan bruke hvilken som helst tast til hva du vil.

Den er laget for å bygges hjemme. Kabinettet printes på en Creality K2, delene kommer fra AliExpress, og fastvaren er ESPHome.

![Skjold Fjernkontroll, lys](render/01_skra_lys.png)

Bilder: [skrått, lys](render/01_skra_lys.png) · [ovenfra, lys](render/02_ovenfra_lys.png) · [eksplodert, lys](render/03_eksplodert_lys.png) · [skrått, mørk](render/04_skra_mork.png) · [ovenfra, mørk](render/05_ovenfra_mork.png) · [eksplodert, mørk](render/06_eksplodert_mork.png) · [fra siden](render/07_side_lys.png) · [nær, skjermen og D-paden](render/08_naer_lys.png) · [halen med USB-C](render/09_hale_lys.png).
Skjermen i bildene viser aktivitetslista slik fastvaren tegner den. Skjermbildene er laget med `lag_skjermbilder.py` (se [Skjermen](#skjermen)).

**Mål: 55 × 230 mm, 13,5 mm tykk.** Tastene står 1,2 mm opp (14,7 mm), og gullringen rundt OK står 1,5 mm opp (**15,0 mm på det tykkeste**). Den veier ca. 105–115 g med batteri (beregnet, ikke veid).

Første utgave hadde en 2,0″-skjerm i en 54 × 208 mm kropp, med mye tom ramme på hver side av skjermen. Nå sitter en 2,8″-skjerm der: kroppen er 1 mm bredere og 22 mm lengre, og alt under skjermen (taster, form og farger) er det samme som før.

Hvorfor 2,8″ og ikke 2,4″:
- **Kroppen må være ca. 54 mm bred uansett.** Det krever tre talltaster, vippene og D-paden med hjørnetastene.
- **2,4″ fyller ikke bredden.** Glasset er bare 43–44 mm bredt, så det ville fortsatt blitt nesten 7 mm tom ramme på hver side.
- **2,8″ fyller bredden.** Glasset er 50 mm bredt og fyller fronten med 4 mm ramme, mot 11 mm før.
- **Lengden øker mer med 2,8″,** fordi panelet er 69 mm langt.
- **Brede stavskjermer** (2,25″ og liknende) er for lave til lister og cover.

**Status: ikke bygget og ikke testet.** Modellen er kontrollert med `sjekk_modell.py`, og ESPHome-fila er validert med `esphome config` (ESPHome 2026.10.2). Fastvaren er ikke kompilert her: kompileringen trenger ESP-IDF-filer fra dl.espressif.com og komponentregisteret til Espressif, og de var blokkert i byggemiljøet. Se [Begrensninger](#begrensninger-og-hva-som-ikke-er-testet).

## To varianter: full og kort

| | **Full** | **Kort** |
|---|---|---|
| Mål | 55 × 230 mm | **55 × 187 mm** (43 mm kortere) |
| Tykkelse | 13,5 mm (15,0 mm med gullringen) | samme |
| Taster | 44 brytere, 39 hetter | **28 brytere, 23 hetter** |
| Uten | – | talltastene (1–9, −, 0, ↵) og smarthus-raden (lys, stikk, −, +) |
| TCA9555 | 3 (0x20, 0x21, 0x22) | **2** (0x20, 0x21); vibrator, skjermstrøm og lader på brikke B, P1_4–P1_6 |
| Tastekort | 48,6 × 141 mm (`tastekort/`) | 48,6 × 98 mm (`tastekort_kort/`) |
| ESPHome | `esphome/skjold-fjernkontroll.yaml` | `esphome/skjold-fjernkontroll-kort.yaml` |
| 3MF | `skjold-fjernkontroll-k2*.3mf` | `skjold-fjernkontroll-kort-k2*.3mf` |
| Pris | ca. 725 kr | ca. 715 kr |

Det er samme skjerm, samme bredde og samme formspråk i begge. Den korte varianten slutter med de fire fargetastene. De passer til TV-apper og kan styre ting i Home Assistant.

I kort variant ligger lys, stikk og ± på skjermen (Hjem-siden). De ligger også på **langt trykk på fargetastene**:
- rød: veksler lys
- grønn: veksler stikkontakt
- gul: demper lyset (−)
- blå: skrur lyset opp (+)

Det samme langtrykket virker også på full variant. Uten smarthus-raden ble fjernkontrollen 43 mm kortere. Med raden ville den bare blitt 34 mm kortere.

I kort variant ligger ESP-en til venstre foran laderen (n = 125–148 mm), fordi halen er kortere. Prisforskjellen er liten: delene som utgår er billige, og TCA9555 og bryterne kjøpes i pakker uansett. Det er ca. 10 kr i filament og kortflate.

Velg variant med `variant = "kort"` i `skjold_fjernkontroll.scad`, eller `-D 'variant="kort"'`. `lag_stl.sh` lager begge til `stl/` og `stl_kort/`.

Bilder av kort variant: [skrått, lys](render/11_skra_lys_kort.png) · [ovenfra, lys](render/12_ovenfra_lys_kort.png) · [eksplodert](render/13_eksplodert_lys_kort.png) · [skrått, mørk](render/14_skra_mork_kort.png) · [ovenfra, mørk](render/15_ovenfra_mork_kort.png) · [fra siden](render/16_side_lys_kort.png).

## Designet

Fjernkontrollen er en rett, flat plate. Den har myke R11-hjørner sett ovenfra og en 45°-fas på 1,4 mm rundt topp- og bunnkanten. Sidene går rett, uten innsnevring på midten. Toppen er lys og bunnen mørk, delt i en rett skjøt 7 mm opp på siden. Den mørke varianten har mørk topp og lys bunn.

Fra toppen og ned:
- **Skjermen** ligger øverst, rett bak IR-nesen. Vinduet (47,0 × 59,8 mm) er like stort som dekkglasset minus 1,5 mm kant på sidene og oppe, så den sorte glasskanten synes, og plastrammen ved siden av skjermen er bare 4 mm (inkludert fasen). Nede slutter vinduet 1,1 mm under det aktive området, slik at den brede glasskanten ved flatkabelen ligger skjult.
- **Tre runde taster** sitter rett under skjermen: av/på, **Skjold-tasten i gull** (aktiviteter, hold for rom) og meny.
- **D-paden** er en stor gullring (Ø 30 mm) med fire retninger og en mørk OK i midten. Den sitter høyt, der tommelen hviler. Fire små runde taster står på skrå rundt den: tilbake, info, guide og avslutt.
- **Volum og kanal/side** er to loddrette vipper, en på hver side. Mellom dem sitter demp og siste kanal.
- **Avspilling** har to rader med pilleformede taster: spol tilbake, spill/pause og spol frem, og under dem opptak, stopp og opptaksliste.
- **Fargetastene** er fire smale piller i rødt, grønt, gult og blått.
- **Talltastene** 1–9 står i tre kolonner, med −, 0 og ↵ i fjerde rad.
- **Smarthus-raden** nederst har fire lyse taster: lys, stikkontakt, − og +.
- **SKJOLD** er felt inn i gull nederst.

Designet er Skjolds eget. Det følger samme formspråk som Radio, Røst og Hjul S: myke hjørner, fas i stedet for avrundet «såpe», to toner, gull på det du bruker mest og SKJOLD i gull. Funksjonene er de samme som på andre universalfjernkontroller med skjerm, men formen og plasseringen er bevisst annerledes:
- Siden er rett, ikke innsnevret, og overflaten er matt og printet, ikke en blank, sort plate.
- D-paden sitter høyt, rett under skjermen.
- Volum og kanal er loddrette vipper ytterst.
- Avspillingstastene ligger under vippene.
- Det er ingen pilleknapper for «aktiviteter» og «enheter» ved skjermen. Det gjør den ene gull-tasten med Skjold-skjoldet.

Hver tast er en egen hette med flens under toppen. Den trykker rett på en lavprofil SMD-bryter (4 × 4 × 1,5 mm) på et 1,0 mm tastekort. Hettene står 0,1 mm over bryteren, så de ikke slarker og ikke trykker på forhånd. Symbolene er felt 0,4 mm inn og printet i kontrastfarge (lyse på mørke taster, mørke på lyse). Med CFS blir symbolene en del av samme utskrift.

## Elektronikk – hva og hvorfor

| Del | Hvorfor |
|---|---|
| **ESP32-S3 SuperMini** (ESP32-S3FH4R2, 4 MB flash, 2 MB PSRAM) | Det minste vanlige S3-kortet (22,5 × 18 mm). Det har Wi-Fi og nok minne til LVGL, pluss dyp søvn med vekking fra to pinner. Det koster rundt 45 kr. Det ligger under tastene, med antennen mot halen, der det bare er plast rundt. |
| **2,8″ IPS 240 × 320 med kapasitiv berøring** (ST7789 + FT6336U), naken FPC-modul med dekkglass, 50,0 × 69,2 × 3,8–4 mm (se også [Tre skjermvalg](#tre-skjermvalg)) | Den største skjermen som får plass i bredden. Glasset er 50 mm bredt, så kroppen trenger bare å vokse fra 54 til 55 mm, og skjermen fyller nesten hele fronten. Aktivt område 43,2 × 57,6 mm, dobbelt så stort som 2,0″ (30,6 × 40,8 mm). Samme oppløsning, så fastvaren er den samme med litt større skrift. Begge brikkene har ferdige drivere i ESPHome (`ili9xxx`, `ft63x6`). En naken FPC-modul er tynnere enn de røde kortene med stiftlist. |
| **3 × TCA9555** (16-bits I²C-utvider, interne pull-ups) | 44 taster blir 44 egne innganger, uten matrise, så det blir ingen spøkelsestrykk. Fire pinner er til overs for vibrator, skjermstrøm og ladestatus. INT-utgangene går sammen til én pinne som vekker ESP-en. Brikkene trekker ca. 1 µA hver i ro. |
| **44 × SMD-taktbryter 4 × 4 × 1,5 mm** | Lav profil gjør fjernkontrollen tynn: kort 1,0 + bryter 1,5 + hette over. De er billige i 100-pakker. |
| **3 × IR-diode 940 nm (3 mm) + AO3400** | Tre dioder i viften gir lang rekkevidde og bred spredning. AO3400 (logisk nivå) gir ca. 200 mA puls per diode fra batteriet. |
| **VS1838B** | IR-mottaker for å lære koder. Den har strøm bare når skjermen er på (trekker ca. 0,5 mA). |
| **LiPo 603450, 1200 mAh** | Flat (6,0 mm) og passer under skjermen. Gir 4–5 uker ved vanlig bruk (se [Batteritid](#batteritid)). |
| **TP4056 USB-C-modul med beskyttelse** (DW01 + FS8205) | Lader med USB-C i halen, med overladings-, utladings- og kortslutningsvern. Den viser rødt eller blått lys gjennom to små hull ved kontakten. CHRG-pinnen går til TCA9555, så skjermen viser ⚡ under lading. |
| **AO3401 (P-MOSFET)** | Slår av 3,3 V til skjerm, berøring og IR-mottaker i søvn, så de ikke trekker strøm. |
| **Vibrasjonsbryter SW-18010P** | Vekker fjernkontrollen når du løfter den, uten strøm og uten fastvare. Den er enklere og billigere enn et akselerometer (LIS3DH), og vekker like godt. |
| **Vibrasjonsmotor 1027** (myntcelle, valgfri) | Et kort «tikk» i fingeren på hvert tastetrykk. |

**Alternativ, færre deler:** Waveshare *ESP32-S3-Touch-LCD-2* har ESP32-S3, 2″-skjermen med berøring, lader og akselerometer på ett kort (ca. 300 kr). Kabinettet har plass til det, men pinnene er andre enn i oppsettet her. Bytt pinnene i ESPHome-fila etter Waveshares wiki.

### Tastekortet – to måter

**A. Bestilt kort fra JLCPCB (anbefalt).** 2-lags FR4, **1,0 mm** tykt, 48,6 × 141 mm. Mappa `tastekort/` har alt du trenger for å tegne det:
- `kort_omriss.dxf` er omrisset med hull og hakk for skruene (origo nede til venstre, halen ned).
- `plassering.csv` gir x/y for de 44 bryterne (oppside) og de tre TCA9555 (underside).
- `koblinger.csv` viser hvilken bryter som går til hvilken brikke og pinne.
- `bom.csv` er stykklista i JLC-format.

Det er ingen ferdige gerber-filer. Kortet tegnes på ca. 1–2 timer i EasyEDA (gratis, i nettleseren):
1. Importer DXF-en som kortomriss.
2. Plasser bryterne etter `plassering.csv`.
3. Koble hver bryter mellom pinnen sin og GND, og la autorouteren legge sporene.
4. Legg jordflate på undersiden, men **ingen kobberfylling i feltet 24–36 mm fra kortets nedre kant**, der ESP-antennen ligger under.

Hver TCA9555 skal ha 100 nF ved VCC og adressepinner slik: U1 A0–A2 = 000 (0x20), U2 = 100 (0x21, A0 høy), U3 = 010 (0x22, A1 høy). Kortet trenger også 10 kΩ pull-up på SDA, SCL og felles INT. Fem kort koster ca. 120 kr med billigste frakt. Med JLC-montering av de tre brikkene på undersiden blir det ca. 250 kr mer. Bryterne lodder du selv: fire store ben hver, så det går greit med vanlig loddebolt.

**B. Printet bryterbrett (uten kretskort).** `stl/bryterbrett.stl` har samme omriss som kortet, er 1,0 mm tykt og har to Ø 1,0 mm hull ved hver bryter.
- Lim bryterne på oppsiden med en dråpe superlim, med to ben ned i hullene.
- Lodd lakktråd (0,2 mm) fra ett ben på hver bryter til en felles jordtråd, og fra det andre til utvideren.
- Bruk tre ferdige **PCF8575-moduler** (eller TCA9555-moduler) uten stiftlister. De ligger i bunnen mellom batteriet og ESP-en.
- I ESPHome bytter du `tca9555:` med `pcf8574:` og `pcf8575: true`, og `tca9555:` med `pcf8574:` i pinnene.

Dette tar lengre tid, men er billigere og krever ingen bestilling.

## Deler fra AliExpress

Prisene er omtrentlige AliExpress-priser i november 2026, inkludert billigste frakt. Mange deler kommer i pakker med flere, så du får reservedeler.

| Del | Søkeord | Antall | Ca. pris |
|---|---|---|---|
| ESP32-S3 SuperMini | «ESP32-S3 SuperMini» | 1 | 45 kr |
| 2,8″ IPS 240 × 320 berøringsskjerm, ST7789 + FT6336U (naken FPC med dekkglass, ikke rødt kort) | «2.8 inch IPS capacitive touch 240x320 ST7789 FT6336U» | 1 | 150 kr |
| LiPo 603450 1200 mAh med JST-PH 2.0 | «603450 lipo 1200mAh» | 1 | 60 kr |
| TP4056 USB-C med beskyttelse (5 stk) | «TP4056 type-c protection» | 1 pk | 25 kr |
| Tastekort fra JLCPCB, 1,0 mm, 5 stk (uten montering) | jlcpcb.com | 1 bestilling | 120 kr |
| TCA9555PWR TSSOP-24 (5 stk) | «TCA9555PWR» | 1 pk | 40 kr |
| SMD-taktbryter 4 × 4 × 1,5 mm (100 stk) | «4x4x1.5 SMD tactile switch» | 1 pk | 30 kr |
| IR-diode 940 nm, 3 mm (50 stk) | «IR LED 940nm 3mm» | 1 pk | 20 kr |
| VS1838B IR-mottaker (10 stk) | «VS1838B» | 1 pk | 15 kr |
| AO3400 og AO3401 SOT-23 (50 + 50) | «AO3400 SOT-23», «AO3401 SOT-23» | 2 pk | 25 kr |
| Motstander og kondensatorer 0603/0805 (sett) | «0805 resistor kit», «0805 capacitor kit» | 2 sett | 30 kr |
| Vibrasjonsbryter SW-18010P (10 stk) | «SW-18010P» | 1 pk | 15 kr |
| Vibrasjonsmotor 1027 (10 stk, valgfri) | «1027 coin vibration motor» | 1 pk | 30 kr |
| Hullkort, tynt (for IR-kortet i nesen) | «0.8mm perfboard» | 1 pk | 20 kr |
| Silikontråd 30 AWG og lakktråd 0,2 mm | «30AWG silicone wire», «0.2mm enameled copper wire» | 2 | 40 kr |
| M2 × 10 selvgjengende skruer, linsehode (5 stk brukes) | «M2x10 self tapping pan head» | 1 pk | 20 kr |
| Dobbeltsidig skumtape 1 mm | «1mm double sided foam tape» | 1 rull | 20 kr |
| Filament, ca. 50 g (PLA eller PETG) | | | 20 kr |
| **Sum** | | | **ca. 725 kr** |

Valgfritt:
- **IR-akryl, 1 mm** («IR transmitting acrylic sheet», ca. 35 kr) i stedet for printet IR-vindu.
- **JLC-montering** av TCA9555 (ca. +250 kr).
- **Variant B** med printet bryterbrett og tre PCF8575-moduler (ca. 60 kr i stedet for kortet og TCA9555): totalt **ca. 625 kr**.

## Kobling

Alle tastene går til TCA9555-brikkene (tabellen under). Resten kobles slik til SuperMini-en:

| SuperMini | Til | Merknad |
|---|---|---|
| 5V | TP4056 OUT+ (batteriet, 3,0–4,2 V) | Går inn på LDO-en på kortet. **Koble aldri USB til SuperMini-en mens batteriet er tilkoblet** (bare for første flashing, se under). |
| GND | felles jord (TP4056 OUT−, tastekortet, skjermen, IR-kortet) | |
| 3V3 | TCA9555 VCC, pull-ups, AO3401 source, vibrasjonsbryteren | |
| GPIO1 | VBAT via 220 kΩ / 220 kΩ, 100 nF til GND | batterispenning (ADC) |
| GPIO2 | INT fra alle tre TCA9555 (sammenkoblet) + 10 kΩ til 3V3 | vekker ved tastetrykk |
| GPIO3 | berøring SCL | egen I²C-buss for berøringen |
| GPIO4 | vibrasjonsbryter til 3V3, 1 MΩ til GND | vekker når du løfter den |
| GPIO5 / GPIO6 | SDA / SCL til tastekortet | |
| GPIO7 | berøring INT | |
| GPIO8 | berøring SDA | |
| GPIO9 / GPIO10 | skjerm SCL (SCK) / SDA (MOSI) | SPI |
| GPIO11 | skjerm DC | |
| GPIO12 | skjerm RES og berøring RST | |
| GPIO13 | skjerm BL | baklys (PWM) |
| GPIO43 | 1 kΩ → AO3400 gate (100 kΩ gate–GND) | AO3400 drain → 3 × (IR-diode + 10 Ω) → VBAT |
| GPIO44 | VS1838B OUT | |
| — | skjerm CS → GND | eneste enhet på SPI |
| — | skjerm VCC, berøring VCC, VS1838B VCC → **3V3_SW** (AO3401 drain) | gate til TCA C P1_5 + 100 kΩ til 3V3 |
| — | vibrasjonsmotor: VBAT → motor → AO3400 drain, gate fra TCA C P1_4 (1 kΩ), 1N4148 over motoren | |
| — | TP4056 CHRG → TCA C P1_6 | ladestatus |

### Tastene på TCA9555

Hver bryter kobles mellom pinnen sin og GND. TCA9555 har innebygde pull-ups, så ingen motstander trengs. Tabellen lages av `taster.py`, og den samme lista står i `tastekort/koblinger.csv` og i ESPHome-fila.

| Tast | Bryter-id | Brikke | Adresse | Pinne |
|---|---|---|---|---|
| Av-på | `av` | A | 0x20 | P0_0 |
| Skjold (aktiviteter) | `hjem` | A | 0x20 | P0_1 |
| Meny | `meny` | A | 0x20 | P0_2 |
| Tilbake | `tilbake` | A | 0x20 | P0_3 |
| Info | `info` | A | 0x20 | P0_4 |
| Guide | `guide` | A | 0x20 | P0_5 |
| Avslutt | `avslutt` | A | 0x20 | P0_6 |
| Opp | `opp` | A | 0x20 | P0_7 |
| Ned | `ned` | A | 0x20 | P1_0 |
| Venstre | `venstre` | A | 0x20 | P1_1 |
| Høyre | `hoyre` | A | 0x20 | P1_2 |
| OK | `ok` | A | 0x20 | P1_3 |
| Volum + | `vol_opp` | A | 0x20 | P1_4 |
| Volum − | `vol_ned` | A | 0x20 | P1_5 |
| Kanal + | `kan_opp` | A | 0x20 | P1_6 |
| Kanal − | `kan_ned` | A | 0x20 | P1_7 |
| Demp | `demp` | B | 0x21 | P0_0 |
| Siste kanal | `siste` | B | 0x21 | P0_1 |
| Spol tilbake | `spol_tilbake` | B | 0x21 | P0_2 |
| Spill-pause | `spill_pause` | B | 0x21 | P0_3 |
| Spol frem | `spol_frem` | B | 0x21 | P0_4 |
| Ta opp | `opptak` | B | 0x21 | P0_5 |
| Stopp | `stopp` | B | 0x21 | P0_6 |
| Opptak (liste) | `dvr` | B | 0x21 | P0_7 |
| Rød | `rod` | B | 0x21 | P1_0 |
| Grønn | `gronn` | B | 0x21 | P1_1 |
| Gul | `gul` | B | 0x21 | P1_2 |
| Blå | `bla` | B | 0x21 | P1_3 |
| Tall 1 | `tall_1` | B | 0x21 | P1_4 |
| Tall 2 | `tall_2` | B | 0x21 | P1_5 |
| Tall 3 | `tall_3` | B | 0x21 | P1_6 |
| Tall 4 | `tall_4` | B | 0x21 | P1_7 |
| Tall 5 | `tall_5` | C | 0x22 | P0_0 |
| Tall 6 | `tall_6` | C | 0x22 | P0_1 |
| Tall 7 | `tall_7` | C | 0x22 | P0_2 |
| Tall 8 | `tall_8` | C | 0x22 | P0_3 |
| Tall 9 | `tall_9` | C | 0x22 | P0_4 |
| Strek | `strek` | C | 0x22 | P0_5 |
| Tall 0 | `tall_0` | C | 0x22 | P0_6 |
| Enter | `enter` | C | 0x22 | P0_7 |
| Lys | `lys` | C | 0x22 | P1_0 |
| Stikkontakt | `stikk` | C | 0x22 | P1_1 |
| Minus (dempe lys) | `minus` | C | 0x22 | P1_2 |
| Pluss (mer lys) | `pluss` | C | 0x22 | P1_3 |
| utgang: vibrasjonsmotor (via AO3400) | `vibrator` | C | 0x22 | P1_4 |
| utgang: 3V3 til skjerm og IR-mottaker (lav = på, AO3401) | `strom_skjerm` | C | 0x22 | P1_5 |
| inngang: TP4056 CHRG (lav = lader) | `lader` | C | 0x22 | P1_6 |
| ledig | `ledig` | C | 0x22 | P1_7 |

## Print (Creality K2)

Tre ferdige plater. Filamentnumrene står i 3MF-fila (Creality Print / OrcaSlicer), så med CFS printes hver plate i én omgang. Ingen deler trenger støtte.

| Plate | Innhold | Filament |
|---|---|---|
| `skjold-fjernkontroll-k2.3mf` | Toppen (forsiden ned), SKJOLD i gull felt inn i toppen, og bunnen | 1 = lys (topp), 2 = mørk (bunn), 3 = gull (logo) |
| `skjold-fjernkontroll-k2-taster.3mf` | Alle hettene (flensen ned) i samme mønster som de sitter, med symbolene felt inn, gullringen og Skjold-tasten, smarthus-tastene, og IR-vinduet | 1 = lys, 2 = mørk, 3 = gull, 4 = klar/natur PETG (IR-vinduet) |
| `skjold-fjernkontroll-k2-farger.3mf` | De fire fargetastene | 1 = rød, 2 = grønn, 3 = gul, 4 = blå |

**Innstillinger:**
- Topp og bunn: PLA eller PETG, 0,2 mm lag, 3 vegger, 25 % fyll.
- Hettene: 0,12 mm lag, så symbolene blir skarpe (de er 0,4 mm dype, dvs. 3–4 lag). Bruk 100 % fyll.
- Teksturert PEI gir matt topp, siden toppen printes med forsiden ned.

**Mørk variant:** bytt filament 1 og 2 i sliceren. Da blir toppen mørk, bunnen lys og smarthus-tastene mørke med lyse symboler.

**IR-vinduet** må slippe gjennom 940 nm. Klar eller natur PETG fungerer best. Sort PLA stopper ofte IR (sotpigment). Du kan teste med mobilkameraet: hold vinduet foran en IR-fjernkontroll og trykk, og se om lyset synes. Et 1 mm IR-akrylvindu (30 × 3,5 mm) kan limes inn i stedet.

**Med én farge (uten CFS):** print alt i én farge og slett symbol-, logo- og fargedelene i sliceren. Symbolene og SKJOLD blir da felt inn 0,4–0,5 mm. Fyll dem med akrylmaling eller en tusj, og tørk av overflaten. Fargetastene kan males, eller printes en og en i hver sin farge.

Bruk `lag_stl.sh` for å eksportere alt på nytt (STL, sjekk og 3MF) etter endringer, og `xvfb-run -a ./lag_render.sh` for bildene. Tastene flytter du i `taster.py`. Den oppdaterer modellen, tastekortdataene og ESPHome-fila samtidig.

## Montering

1. **Tastekortet:** lodd de 44 bryterne (variant A), eller lim dem på bryterbrettet og trå lakktråden (variant B). Mål med multimeter at hver tast kortslutter pinnen sin mot GND.
2. **IR-kortet:** lodd de tre IR-diodene liggende (de peker ut gjennom nesen), VS1838B og AO3400 på en 34 × 7 mm hullkortbit. Kortet står i sporet i nesen, med diodene mot vinduet.
3. **IR-vinduet:** trykk det inn i nesen fra innsiden (kragen inn) og fest med en dråpe lim.
4. **Lader og ESP:** legg TP4056 i lomma i halen med USB-C ut gjennom hullet. Legg SuperMini-en i lomma foran (antennen mot halen). Lodd ledningene etter tabellen. Bruk kort silikontråd og legg den flatt.
5. **Batteriet:** legg det i lomma under skjermen, med kabelen mot nesen, og koble til TP4056 B+/B−. **Flash fastvaren før dette** (se under).
6. **Skjermen:** legg en 1 mm skumtape på batteriet og legg skjermen med glasset ned i lomma i toppen (flatkabelen mot tastene). Lomma går nesten helt ut til sideveggene; leppa på bunnen er derfor kuttet langs skjermen.
7. **Hettene:** legg toppen med forsiden ned og sett alle hettene i hullene sine fra innsiden. OK settes inn i gullringen nedenfra før ringen legges i. Flensen holder dem på plass.
8. **Lukk:** legg tastekortet over hettene (bryterne ned mot hettene). Legg bunnen med all innmaten over, og skru sammen med 5 × M2 × 10 fra undersiden: fire i hjørnene og én i midten, som også klemmer tastekortet.

## Fastvare

`esphome/skjold-fjernkontroll.yaml`. Gjør klar:
- Sett `skjold_host` til Skjold-enheten din.
- Sett Home Assistant-entitetene og scenene under `substitutions`.
- Legg inn `wifi_ssid`, `wifi_password` og `skjold_fjernkontroll_api_key` i `secrets.yaml`.

**Første gang**, før batteriet er koblet til, kobler du SuperMini-en til PC-en med USB-C:

```bash
esphome run esphome/skjold-fjernkontroll.yaml
```

Etter det oppdateres den trådløst. Slå på «Hold våken (for oppdatering)» i Home Assistant, ellers sovner den midt i oppdateringen.

**Ladeporten** i halen er TP4056-en. Den lader bare, den har ingen data.

### Hva fastvaren gjør

- **Skjermen (LVGL):** fire faner nederst.
  - *Aktiviteter*: Se TV, Musikk, Film, God morgen, God natt. Den aktive får gullkant.
  - *Spiller*: cover fra `/api/cover?w=120`, tittel og artist (eller radiokanalen), spill/pause, forrige/neste og volum som glidebryter.
  - *Kilder*: Radio, AirPlay, Bluetooth, Spotify og radiofavoritt 1–6 med navn fra `/api/presets`.
  - *Hjem*: fire lys og fire scener i Home Assistant, og «Lær IR-kode».
  - *Rom* (hold Skjold-tasten): de andre Skjold-enhetene på nettet, fra `/api/rom`. Velg hvilken du vil styre, og valget huskes.
- **Skjold** styres med det vanlige API-et på port 8765, det samme som appen bruker:
  - `/api/status` hvert 3. sekund når den er våken
  - `/api/volume` (`delta` eller `volume`)
  - `/api/mute`
  - `/api/transport` (`playpause`, `next`, `previous`, `stop`, `pause`)
  - `/api/preset` (`n`)
  - `/api/presets`
  - `/api/input`
  - `/api/power`
  - `/api/rom`
  - `/api/cover`

  Det er ingen nye endepunkter i Skjold.
- **Tastene:**
  - I *Musikk* (Skjold): volum, demp, spill/pause, stopp, spol/kanal (neste/forrige), D-pad (opp/ned = volum, venstre/høyre = forrige/neste, OK = spill/pause) og tall 1–9 (favoritt 1–9) går til Skjold.
  - I *TV* og *Film* sendes den lærte IR-koden for tasten. Har tasten ingen kode, gjør den det samme som i musikkmodus. For eksempel går volumet til Skjold hvis TV-lyden går gjennom Skjold.
  - Smarthus-raden går alltid til Home Assistant: lys veksler `ha_lys`, stikk veksler `ha_stikk`, og − og + demper lyset 10 % opp eller ned.
  - Skjold-tasten viser aktivitetene (hold for rom). Av slår av Skjold (hold = «alt av»).
  - Volum, kanal, D-pad og ± gjentas så lenge du holder dem inne.
- **IR-læring:** Hjem → «Lær IR-kode».
  1. Trykk tasten som skal lære, eller velg en av makroene TV på, TV av, HDMI eller Ekstra.
  2. Pek den gamle fjernkontrollen mot nesen og trykk.
  3. Trykk «Lagre».

  Koden lagres i flash (48 plasser: én per tast og fire makroer). Fjernkontrollen forstår NEC, Samsung, Sony, RC5 og LG. Det dekker de fleste TV-er, men ikke for eksempel klimaanlegg.
- **Aktivitetene** er skript i YAML-fila (`akt_se_tv`, `akt_film` …), og stegene står rett etter hverandre. «Se TV» gjør dette:
  1. TV på (makro 1)
  2. HDMI (makro 3)
  3. Skjold på
  4. Skjold-inngang `tv_kilde`
  5. `scene_tv` i Home Assistant

  Endre stegene som du vil.
- **Søvn:** etter 40 s uten tast eller berøring slukker baklyset, skjermen og IR-mottakeren mister strømmen, og ESP-en går i dyp søvn. Den våkner av en tast (felles INT fra TCA9555 til GPIO2) eller av at du løfter den (vibrasjonsbryteren på GPIO4). Batteriprosenten og ⚡ for lading står øverst til høyre.

## Home Assistant

ESPHome-integrasjonen finner fjernkontrollen. Slå på **«Tillat enheten å utføre handlinger i Home Assistant»** i integrasjonsvalgene, ellers virker ikke lys, stikk og scener.

**Hver tast er en hendelse.** Det finnes to måter å fange den på:
- **Event-entiteten `event.skjold_fjernkontroll_tast`** har én hendelsestype per tast: `rod`, `tall_1`, `lys` … og `<tast>_lang` for langt trykk. Den er lettest å bruke i automasjonsredigereren.
- **Hendelsen `esphome.skjold_fjernkontroll`** har `tast` og `lang` i data:

```yaml
automation:
  - alias: Rød tast tenner kjøkkenet
    triggers:
      - trigger: state
        entity_id: event.skjold_fjernkontroll_tast
        attribute: event_type
        to: rod
    actions:
      - action: light.toggle
        target: { entity_id: light.kjokken }
```

**Handlinger** (Utviklerverktøy → Handlinger):
- `esphome.skjold_fjernkontroll_send_ir` med `plass` 0–47 sender en lært kode.
- `esphome.skjold_fjernkontroll_send_nec` med `adresse` og `kommando` sender en NEC-kode direkte.
- `esphome.skjold_fjernkontroll_slett_ir` sletter en plass.

**Entiteter:** Batteri (%), Batterispenning, Lader, Wi-Fi-signal, Skjermlys og «Hold våken».

## Batteritid

Dette er et overslag, ikke målt.

**I søvn** trekker den ca. 70–90 µA, eller ca. 2 mAh i døgnet:

| Hva | Strøm |
|---|---|
| ESP32-S3 i dyp søvn med to vekkepinner | ca. 10 µA |
| LDO-en på SuperMini | 40–60 µA (avhenger av kortet) |
| 3 × TCA9555 | ca. 3 µA |
| Batterideleren (2 × 220 kΩ) | 9,5 µA |
| TP4056/DW01 fra batteriet | 3–6 µA |
| Skjerm, berøring og IR-mottaker | 0 (strømmen er av) |

**Våken** trekker den ca. 85 mA i snitt: Wi-Fi med lett strømsparing ca. 45 mA, baklys ca. 30 mA (2,8″ har flere lysdioder enn 2,0″) og skjerm og resten ca. 10 mA. Det tar ca. 1,5 s å koble til Wi-Fi etter søvn.

| Bruk | Våken per døgn | Forbruk per døgn | 1200 mAh (85 % brukbart) |
|---|---|---|---|
| Lite: 10 løft à 30 s | 5 min | ca. 9 mAh | ca. 3–4 måneder |
| Vanlig: 30 løft à 45 s | 22 min | ca. 34 mAh | **ca. 4 uker** |
| Mye: 2 timer med skjermen på | 120 min | ca. 170 mAh | ca. 6 dager |

Du får mer ut av batteriet hvis du:
- setter fast IP (`manual_ip`), som gir raskere oppkobling;
- setter `sovn_etter` til 20 s;
- skrur ned baklyset;
- bytter LDO-en på SuperMini til en med lav hvilestrøm (f.eks. HT7833, 4 µA);
- bruker et større batteri. Under 2,8″-skjermen er det plass til et LiPo på 6 × 40 × 60 mm (604060, ca. 2000 mAh) hvis du justerer `bat` og ribbene i modellen.

## Begrensninger og hva som ikke er testet

- **Ingenting er bygget eller målt.** Modellen er sjekket for kollisjoner, veggtykkelse og tastehull. Fastvaren er validert med `esphome config`, men ikke kompilert eller kjørt. C++-koden i lambdaene (IR-sending, JSON og LVGL-kall) kan trenge småjusteringer ved første kompilering.
- **Mål skjermmodulen før du printer.** 2,8″-modulene på AliExpress varierer. Modellen følger måltegningen til budsjett-panelet: glass 50,00 × 69,20 ± 0,2 mm, aktivt område 43,2 × 57,6 mm som begynner 2,6 mm fra overkanten (motsatt flatkabelen), og 3,8 mm tykt med berøring. IPS-panelene med samme omriss har normalt samme oppsett. Juster `modW`, `modH`, `modT`, `modN0`, `aktivTopp` og `scrAW`/`scrAH` i `skjold_fjernkontroll.scad` hvis din er annerledes. Er modulen tykkere enn 4 mm, bruk tynnere skumtape (eller ingen) mellom batteriet og skjermen, opptil 5 mm.
- **SuperMini-kortene varierer litt** (pinnerekkefølge, LDO). Sjekk at GPIO 1–13, 43 og 44 er ført ut på ditt kort.
- **4 MB flash er nok, men ikke romslig.** LVGL, tre skrifter og online_image tar plass, og OTA trenger to like store partisjoner. Blir bygget for stort, bruk færre glyfer, dropp `f_tittel` eller velg et S3-kort med 8–16 MB.
- **Det første trykket etter søvn** når fram hvis du holder tasten litt (ESP-en bruker ca. 0,3 s på å våkne og leser tasten når den starter). Et veldig kort trykk vekker bare skjermen. Kommandoer til Skjold sendes så snart Wi-Fi er oppe (ca. 1,5 s).
- **IR-læring** fanger bare koder ESPHome kan tolke (NEC, Samsung, Sony, RC5, LG). Råkoder og klimaanlegg støttes ikke.
- **Kilder** som ikke finnes på din Skjold-modell (f.eks. Spotify) gir bare en feilmelding i loggen.
- **Ingen USB-data i ladeporten.** Første flashing skjer via USB-C på SuperMini-en, med batteriet frakoblet.
- **Tastekortet** er levert som data (omriss, plassering, koblinger, stykkliste), ikke som gerber-filer.

## Filer

| Fil | Hva |
|---|---|
| `skjold_fjernkontroll.scad` | Modellen (parametrisk OpenSCAD) |
| `taster.py` → `taster.scad` | Tastene: plassering, form, symbol, farge og bryter. Oppdaterer også `tastekort/` og ESPHome-fila |
| `lag_stl.sh` | Eksporterer STL-er, kjører sjekken og lager 3MF |
| `sjekk_modell.py` | Kontroll: vanntett, ingen overlapp, vegger ≥ 1,6 mm, materiale mellom tastehullene, forvandring, tykkelse |
| `lag_3mf.py` | 3MF-plater for K2 med filamentnumre |
| `lag_render.sh`, `skjerm_i_render.py`, `lag_skjermbilder.py` | Bildene i `render/`, med skjermbildet lagt inn |
| `tastekort/`, `tastekort_kort/` | Omriss (DXF), plassering, koblinger og stykkliste for tastekortet, full og kort |
| `stl/`, `stl_kort/` | Alle utskriftsdelene for full og kort variant, inkludert `bryterbrett.stl` |

## Tre skjermvalg

| | **IPS med kapasitiv berøring** (standard) | **Budsjett-skjerm** (TN, resistiv) | **Waveshare ESP32-S3-Touch-LCD-2.8** |
|---|---|---|---|
| Hva | 2,8″ IPS, ST7789 + FT6336U, naken FPC | 2,8″ TN, ST7789V + 4-tråds resistiv berøring, 18-pinners FPC ([AliExpress 1005005780989629](https://www.aliexpress.com/item/1005005780989629.html)) | ESP32-S3, 2,8″ IPS og berøring på ett kort |
| Pris | ca. 150 kr | ca. 40 kr + XPT2046 og FPC-kontakt ca. 10 kr | ca. 280 kr (erstatter også SuperMini og TP4056) |
| Totalpris full / kort | ca. 725 / 715 kr | **ca. 625 / 615 kr** | ca. 785 kr, men ikke tegnet inn (se under) |
| Bilde | Godt fra alle vinkler | TN: farger og kontrast endrer seg når du vipper fjernkontrollen | IPS |
| Berøring | Lett trykk og sveip, som på en telefon | Må trykkes litt; sveip går dårligere; må kalibreres | Kapasitiv, men V2 har CST3530 uten ESPHome-driver |
| Passer i modellen | Ja | **Ja**, samme omriss og tykkelse (3,8 mm) | Ukjent: mål og pinner er ikke bekreftet |
| Ekstra deler | – | XPT2046 (TSSOP-16) + 1 µF på tastekortet | – |
| ESPHome | `skjold-fjernkontroll.yaml` (eller `-kort`) | `skjold-fjernkontroll-budsjett.yaml` (pakke over hovedfila) | egen fil måtte lages |

**IPS med GT911-berøring (også kapasitiv):** mange IPS-paneler selges med GT911 i stedet for FT6336U, f.eks. «IPS 2.8 inch RGB565 18PIN SPI TFT LCD Capacitive Screen ST7789V 6P GT911» (Ecyberspaces, ca. 100 kr + frakt, velg «IPS Screen with TP»). Skjermdelen er den samme (ST7789V, 18-pinners FPC). Berøringen har egen 6-pinners flatkabel (VCC, GND, SDA, SCL, INT, RST) som kobles til I²C-bus B, INT til GPIO7 og RST til GPIO12, akkurat som FT6336U. Bruk [`esphome/skjold-fjernkontroll-gt911.yaml`](../../esphome/skjold-fjernkontroll-gt911.yaml), som bytter `ft63x6` med `gt911`. Be selgeren om måltegningen og sjekk at den er ca. 50 × 69,2 mm med aktivt område 43,2 × 57,6 mm før du printer.

**Anbefaling:** IPS med kapasitiv berøring er fortsatt standard, siden den har bedre bilde og føles bedre. Budsjett-skjermen er et godt valg hvis prisen betyr mest, og sparer ca. 100 kr.

**Budsjett-skjermen passer i modellen.** Tegningen gir:
- **Omriss:** 50,00 × 69,20 ± 0,2 mm. Lomma er 50,6 × 69,8 mm (0,3 mm klaring rundt, større enn toleransen).
- **Tykkelse:** 3,8 mm med berøring, inntil 4,0 mm med tapen. Modellen gir plass til 4,0 mm.
- **Aktivt område:** 43,2 × 57,6 mm, 2,6 mm fra overkanten. Modellen og vinduet følger dette.
- **Styrepinnene** bak (Ø 0,95 mm) trykkes ned i skumtapen på batteriet.
- **Flatkabelen** er 19,16 mm og kommer ut i nedre kant mot tastene. Den bøyes rett ned i spalten mellom glasset og tastekortet, og inn i en 18-pinners 0,8 mm FPC-kontakt (bunnkontakt) på undersiden av tastekortet, rett bak skjermen. Kontakten er tegnet inn i modellen (`fpcN`), og veien er ca. 12 mm, så kabelen er lang nok. Kontaktområdet er 39,6 mm bredt og får plass i kortets 48,6 mm.
- **Kortkoblinger:** fra kontakten går skjermsignalene til SuperMini som før (SCK 9, MOSI 10, DC 11, RES 12, BL 13, CS til GND).

XPT2046 sitter ved siden av FPC-kontakten og bruker samme SPI:
- MISO til GPIO8
- CS til GPIO3
- PENIRQ til GPIO7

Disse pinnene er ledige, fordi I²C-bussen for kapasitiv berøring ikke brukes. XL, XR, YU og YD fra panelet går til X+, X−, Y+ og Y− på XPT2046.

Begge kortvariantene (`tastekort/` og `tastekort_kort/`) har FPC-kontakten (J1) og XPT2046 (U9, monteres bare for budsjett-skjermen) i plasseringen og stykklista. Den kapasitive IPS-modulen har ofte egen, liten flatkabel for berøringen. Den kobles med ledninger til I²C-bus B som før.

## Vurdert: Waveshare ESP32-S3-Touch-LCD-2.8 («alt i ett», ca. 280 kr)

Dette kortet har ESP32-S3, en 2,8″ IPS-skjerm (240 × 320, ST7789) og kapasitiv berøring på ett kort, i tillegg til høyttaler, lader og SD. Det kunne erstattet SuperMini, skjermpanelet og TP4056.

**Konklusjon: passer ikke som standard nå.** De vanlige delene er fortsatt standard.

Hvorfor:
- **Berøringen er byttet.** Ifølge Waveshare sendes kortet fra 5. juni 2026 i versjon 2, med CST3530 i stedet for CST328. ESPHome har driver for CST328 (`cst328`, med et eksempel for dette kortet: I²C på GPIO6/7, INT GPIO8, RST GPIO17), men ikke for CST3530. Med en ny V2 må berøringen skrives som egen komponent (external component). Det er hovedgrunnen.
- **Ukjente mål.** Jeg fikk ikke hentet målene, pinnetabellen og skjemaet fra Waveshare-wikien, fordi docs.waveshare.com og esphome.io var blokkert i byggemiljøet. Kortet er større enn glasset, og ESP-modul, høyttaler og kontakter sitter under skjermen. Totalt er det trolig 8–10 mm tykt. Da kan batteriet ikke ligge under skjermen, og lomma må tegnes etter målene. Det går ikke uten tegningen.
- **Få ledige pinner.** Det ser ut som det bare er en 12-pinners SH1.0-kontakt (I²C, UART og noen få GPIO). TCA9555-brikkene kan dele I²C med berøringen. IR inn, IR ut, tastevekking (INT) og vibrasjonsbryteren trenger fire pinner til, og det er usikkert om de finnes.
- **Høyere hvilestrøm.** Lader, LDO, lydforsterker, IMU og baklysdriver er alltid tilkoblet, og skjermstrømmen kan ikke slås av. Erfaringsmessig gir slike kort 0,5–3 mA i dyp søvn, mot ca. 0,08 mA her. Det gir dager til et par uker på 1200 mAh i stedet for ca. 4 uker.
- **Pris.** Ca. 280 kr, mot ca. 200 kr for SuperMini, panel og TP4056. Til gjengjeld blir det mindre lodding.
- **IMU-en (QMI8658) som løftevekker.** Bare 2.8B-utgaven er bekreftet å ha QMI8658. ESPHome leser den (`qmi8658`), men har ikke «wake on motion». Det måtte settes opp med registerskriving i en lambda, og INT-pinnen må gå til en RTC-GPIO. Det er ikke bekreftet.

Hvis du har et V1-kort (CST328, se merket bak) og målene fra Waveshare, er det mulig å bruke det. Lag i så fall en lomme for kortet i stedet for `modW`/`modH`, legg batteriet under tastene, og bytt pinnene i ESPHome etter wikien.

## Lisens

Kabinettet og tastekortdataene er lisensiert under **CC BY-NC-SA 4.0**, se [LISENS-MASKINVARE.md](../../LISENS-MASKINVARE.md). Fastvaren følger lisensen til resten av prosjektet, se [LISENS.md](../../LISENS.md).
