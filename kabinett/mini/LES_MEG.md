# Skjold Mini

En liten aktiv høyttaler for bad, barnerom og kjøkken. Den har et 3″ fullrange-element i et bassrefleks-kabinett, en ESP32-S3 og en klasse D-forsterker. Mini er en vanlig Squeezebox-spiller i Lyrion, så den spiller synkront med S1, Node og Touch.

![Skjold Mini](render/01_mini.png)

Bilder: [mini](render/01_mini.png) · [eksplodert](render/02_eksplodert.png) · [bak](render/03_bak.png) · [kroppen innvendig](render/04_kropp_innside.png)

Mål: 100 × 106 × 144 mm (B × D × H, med grill og bunn). Fastvare og oppsett: [`firmware/mini/`](../../firmware/mini/LES_MEG.md).

## Hvorfor disse komponentene

- **PCM5102A (DAC) + TPA3118D2 i mono (PBTL)** i stedet for MAX98357A. MAX98357A gir bare ca. 3 W fra 5 V og blir fort hard på et 3″-element. TPA3118 på 12 V gir ca. 15 W rent i 4 Ω, med god margin og lav støy. PCM5102A er en vanlig I²S-DAC som både squeezelite-esp32 og snapclient støtter uten egen driver. TAS5805M-kort høres også bra ut, men krever egen driver/oppsett over I²C, og er ikke støttet som standard.
- **ESP32-S3 N16R8:** PSRAM gir squeezelite-esp32 god buffer for strømming over Wi-Fi.
- **12 V / 2 A-adapter** med en MP1584-nedtrapper til 5 V for ESP-en. USB-C bak er bare til ESP-en (flashing og logg).

## Deler

| Del | Antall | Merknad |
|---|---|---|
| 3″ fullrange-element, 4 Ω (f.eks. Dayton Audio RS75-4 eller Tang Band W3-871SC) | 1 | Utsparing Ø72 mm, ramme inntil Ø86 mm, 4 skruer på Ø82 mm hullsirkel. Sjekk ditt element og juster `drvCut`/`drvPCD`. |
| ESP32-S3-DevKitC-1 N16R8 | 1 | |
| PCM5102A I²S DAC-kort | 1 | SCK til GND, XSMT til 3V3, FMT/FLT/DEMP til GND |
| TPA3118D2 mono PBTL-forsterkerkort | 1 | 12–24 V inn |
| MP1584EN nedtrapper 12 V → 5 V | 1 | |
| DC-kontakt 5,5/2,1 mm for panel (Ø8 mm) | 1 | |
| Strømadapter 12 V / 2 A | 1 | |
| EC11 dreieknapp med trykk, 20 mm D-aksel | 1 | |
| LED 3 mm, to farger (grønn/rød, felles katode) | 1 | + 2 × 220 Ω |
| INMP441 I²S-mikrofon | 1 | Valgfri |
| M3 innpressmutter (M3 × 5,7, Ø4,0 hull) | 8 | 4 i front, 4 i bunn |
| M3 × 10 senkeskrue | 8 | |
| M3 × 10 selvgjengende (element) | 4 | |
| Magneter: ingen. Grillen holdes av 4 tapper. | | |
| Tetningslist, skumtape 1 × 5 mm | ca. 0,5 m | Mellom frontplate og kropp |
| Gummiføtter Ø10 mm | 4 | |
| Polyfill / dempeull | ca. 5 g | Løst i kammeret, ikke foran porten |

## Kobling (ESP32-S3)

| Fra | Til |
|---|---|
| PCM5102A BCK / LCK (WS) / DIN | GPIO4 / GPIO5 / GPIO6 |
| PCM5102A VIN / GND | 5V / GND |
| PCM5102A OUT L (eller L+R via 2 × 1 kΩ) | TPA3118 inn |
| TPA3118 SDZ (forsterker på) | GPIO7 |
| TPA3118 PVCC / GND | 12 V / GND (fra DC-kontakten) |
| TPA3118 ut + / − | Element + / − |
| EC11 A / B / trykk (C og trykk-retur til GND) | GPIO15 / GPIO16 / GPIO17 |
| LED grønn / rød (via 220 Ω) | GPIO1 / GPIO2 |
| INMP441 SCK / WS / SD, L/R til GND | GPIO41 / GPIO42 / GPIO40 |
| MP1584 ut 5 V | ESP32 5V |

Ikke bruk GPIO0, 3, 45 eller 46 (oppstartspinner) eller GPIO35–37 (PSRAM).

## Akustikk

- Lydkammer: ca. 1,0 l brutto, ca. 0,89 l netto (minus element, port og skruetårn).
- Bassrefleks: port Ø16 mm, 79 mm lang (inkludert baffel), avrundet munning foran. Det gir en tuning på ca. 86 Hz.
- Dette er et utgangspunkt beregnet ut fra volum og port, ikke målt. Simuler ditt element i WinISD eller VituixCAD. Endre `portL` (lengre port = lavere tuning) eller tett porten for et lukket kabinett.
- Elektronikken ligger i et eget rom under gulvet. Kabelen til elementet går gjennom et Ø6-hull i gulvet, og det må tettes med lim, ellers lekker kammeret.
- Tett også rundt EC11-akselen inne i kammeret med en dråpe lim, og legg skumtape mellom frontplaten og kroppen.

## Utskrift (Creality K2)

`skjold-mini-k2.3mf` har alle delene på én plate (246 × 248 mm). Den passer K2, K2 Pro og K2 Plus. Filamentnummer: 1 = lys (kropp), 2 = sort (front, grill, bunn), 3 = gull (knott). Setter ikke Creality Print fargene selv, sett filament per del.

| Del | Retning | Støtte | Ca. vekt (PLA) |
|---|---|---|---|
| `kropp.stl` | Bakveggen ned, åpen front opp | Nei | 210 g |
| `front.stl` | Forsiden ned (porten står opp) | Nei | 75 g |
| `grill.stl` | Forsiden ned | Nei | 19 g |
| `bunn.stl` | Flat | Nei | 45 g |
| `knott.stl` | Toppen ned | Nei | 15 g |

Totalt ca. 365 g. Utskriftstid er ikke slicet.

Anbefalte innstillinger: 0,2 mm lag, 0,4 mm dyse, 4 vegger (tette, stive vegger gir mindre resonans), 20 % gyroid fyll, PETG 240 °C / 75 °C seng eller PLA 215 °C / 60 °C. Teksturert PEI gir pen matt front.

## Montering

1. Varm inn 8 M3-innpressmuttere: 4 i fronten av kroppens skruetårn, 4 i tårnene under.
2. Monter EC11 gjennom toppen innenfra og trykk på knotten. Tett rundt akselen med lim.
3. Legg elektronikken i rommet under gulvet: DC-kontakt og ESP32 (USB-C) mot hullene bak, forsterker over luftespaltene i bunnen. Fest kortene med dobbeltsidig tape eller lim (det er ikke modellert standoffs).
4. Trekk elementkabelen gjennom hullet i gulvet og tett med lim.
5. Skru elementet fast i frontplaten, legg litt dempeull i kammeret (ikke foran porten), sett skumtape på kanten og skru frontplaten fast med 4 senkeskruer.
6. Klikk grillen på med de 4 tappene, skru på bunnen med 4 senkeskruer og sett på gummiføttene.

## Sjekket og ikke sjekket

- Sjekket i modellen: alle STL-er er vanntette og består av én del, og ingen deler overlapper når de er montert.
- Ikke testet: ingenting er printet eller bygget. Passformen til element, innpressmuttere, grilltapper og knott, lyden, porttuningen og om squeezelite-esp32-innstillingene virker på S3 må prøves.

Lisens: CC BY-NC-SA 4.0.
