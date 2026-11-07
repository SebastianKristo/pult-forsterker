# Skjold Radio

En bordradio med 4,3″ skjerm, seks favorittknapper, et stort navigasjonshjul, en liten volumknott og stereolyd. Inni sitter en Raspberry Pi 4 med vanlig Skjold-programvare. Radioen er altså en Skjold-spiller med alt Skjold kan (nettradio, AirPlay, Spotify Connect, Bluetooth, Lyrion, multirom, appen og Home Assistant), bare bygget inn i en kasse med knapper.

![Skjold Radio, lys](render/02_skra_lys.png)

Bilder: [forfra, lys](render/01_forfra_lys.png) · [skrått, lys](render/02_skra_lys.png) · [eksplodert, lys](render/03_eksplodert_lys.png) · [forfra, mørk](render/04_forfra_mork.png) · [skrått, mørk](render/05_skra_mork.png) · [eksplodert, mørk](render/06_eksplodert_mork.png) · [bak](render/07_bak_lys.png)

Mål: 236 × 152 mm, 100 mm høy foran og 128 mm bak (B × D × H, uten knotter og gummiføtter). Hjulet stikker 15,6 mm over toppen, volumknotten 14 mm ut på høyre side.

## Designet

Radioen er en lav, bred «pult»: hele toppen heller ca. 10,6° ned mot deg, som et skråstilt dashbord. Skjermen, favorittknappene og hjulet sitter på skråflaten, så du ser og når alt fra sofaen eller fra stolen ved kjøkkenbenken.

- **Fronten er bare lyd.** En mørk grill med vannrette spalter dekker hele fronten og går helt ned til bordet. Kroppen rammer den inn på sidene og oppe.
- **Toppen er alt du trenger.** Seks favorittknapper ligger i en rad langs forkanten, med skjermen bak. Av/på sitter alene bak til venstre, så du ikke trykker på den ved et uhell.
- **Gullhjulet (Ø 46 mm) er særpreget.** Det er det største elementet på radioen og sitter til høyre for skjermen, nær nok til å drives med tommelen. Drei for å bla i favorittene, trykk for spill/pause.
- **Volumknotten er en liten gullknott på høyre side**, der hånda faller naturlig.
- **Skjold-formspråket:** myke vertikale hjørner (R14, som Node og Røst), faset toppkant hele veien rundt, lys kropp med mørk grill og mørke knapper, gull hjul, og SKJOLD preget i toppen bak hjulet.
- **Mørk variant:** sort kropp, grafittgrå grill og gullknapper. Bare filamentet byttes.

Designet er laget fra bunnen av for Skjold. Det er ikke en kopi av noen eksisterende radio: proporsjoner, plassering av knapper og detaljer er egne. Den skrå pulten med grill helt ned til bordet er Skjold Radios kjennetegn.

## Elektronikk – hva og hvorfor

| Del | Hvorfor |
|---|---|
| **Raspberry Pi 4 (2 GB)** | Kjører hele Skjold (squeezelite, AirPlay, Spotify, Bluetooth, CamillaDSP og skjold-ui). Har DSI-kontakt for skjermen, så ingen GPIO går med til den. 2 GB er nok. |
| **Waveshare 4,3″ DSI LCD (800 × 480, kapasitiv touch)** | DSI-skjermen kobles med flatkabel, uten driverkort og uten HDMI-kabel i kassa. Den er skarp, lys nok og rimelig. Touch fungerer som bonus. |
| **PCM5102A I²S DAC** (samme som Skjold Kit) | God lyd for pengene. Radioen bruker `KI_AMP_BOARD=kit`, så daemonen styrer XSMT (myk demping uten smell) og forsterkeren uten endringer. |
| **TPA3116D2 2 × 50 W stereoforsterker** | Rikelig med reserve på 19–24 V for to 3″-elementer. Kjører kjølig og er den samme brikken som i Kit og S1. |
| **2 × Dayton Audio RS75-4 (3″ fullrange, 4 Ω)** | Gode, rene 3″-elementer med bred spredning, uten delefilter. Hvert element sitter i et eget lukket kammer på ca. 0,47 l (stereo med skillevegg). Lukket kasse gir stram bass og tåler å stå inntil veggen. |
| **19–24 V / 3 A strømadapter + 5 V / 5 A nedtrapper** | Én adapter for alt. Forsterkeren får hele spenningen, og Pi-en får 5 V via GPIO-pinnene 2/4 (ikke via USB-C). Nedtrapperen må tåle 5 A, fordi Pi 4 med skjerm trekker opptil 3 A ved oppstart. |
| **Relémodul 1-kanal, 3,3 V-styrt (jumper H)** | Som i Kit: GPIO 27 slår forsterkeren av og på uten smell. |
| **2 × EC11 dreieknapp med trykk** | Hjulet (20 mm aksel) og volum (15 mm aksel). Billige, holdbare og med tydelige hakk. |
| **7 × taktbryter 6 × 6 × 4,3 mm** | Under de printede knappehettene. Nuppen på hetta treffer bryteren med 0,1 mm forspenning. |

Strømtrekket er normalt 6–15 W. Pi-en og skjermen trekker ca. 4–5 W alene.

## Kobling

Alle knapper og dreieknapper går til GND og bruker Pi-ens interne pull-up. Pinnene står i [`pi/config/radio_pins.yaml`](../../pi/config/radio_pins.yaml) og kan endres der.

| Fra | Til (Raspberry Pi, BCM / fysisk pinne) |
|---|---|
| Favoritt 1 · 2 · 3 · 4 · 5 · 6 | GPIO 5 (29) · 6 (31) · 12 (32) · 13 (33) · 16 (36) · 17 (11) |
| Av/på | GPIO 4 (7) |
| Hjulet A · B · trykk | GPIO 22 (15) · 23 (16) · 24 (18) |
| Volum A · B · trykk | GPIO 25 (22) · 9 (21) · 7 (26) |
| Felles for knapper og EC11 (C og den andre trykkpinnen) | GND (6, 9, 14, 20, 25, 30, 34, 39) |
| PCM5102A BCK · LCK · DIN | GPIO 18 (12) · 19 (35) · 21 (40) |
| PCM5102A XSMT | GPIO 26 (37). Høy = lyd. Kit-profilen demper DAC-en før forsterkeren slås av. |
| PCM5102A VIN · GND · SCK · FMT/FLT/DEMP | 5 V · GND · GND · GND |
| PCM5102A L · R · G | TPA3116D2 inn L · R · GND (skjermet kabel, kort) |
| Relémodul IN · VCC · GND | GPIO 27 (13) · 5 V · GND. Releet bryter + fra DC-kontakten til forsterkeren. |
| DC-kontakt 19–24 V | Nedtrapper inn, og releet → TPA3116D2 VIN |
| Nedtrapper ut 5,0 V | Pi pinne 2 (5 V) og 6 (GND). **Still inn 5,1 V før du kobler til Pi-en.** |
| TPA3116D2 ut L · R | Venstre og høyre element. Kablene går gjennom hullene i kammergulvet, som tettes med silikon. |
| Skjerm | DSI-flatkabel til Pi-ens DSI-kontakt (touch går over I²C i samme kabel) |
| 3,5 mm-kontakt bak (linje ut) | PCM5102A L/R/G i parallell med forsterkeren, til en ekstern forsterker eller aktive høyttalere. Ikke for hodetelefoner. |
| USB-C bak (service) | Panelmontert USB-C-skjøt til en av Pi-ens USB-A-porter, for minnepinne eller tastatur |

## Deler og priser

Prisene er **anslag i norske kroner per november 2026**, med frakt fra AliExpress inkludert der det er vanlig. Sjekk dagens pris.

| Del | Ant. | Søkeord | Ca. pris |
|---|---|---|---|
| Raspberry Pi 4 Model B 2 GB | 1 | «Raspberry Pi 4 2GB» (Kjell, Elfa, Pimoroni) | 650 kr |
| microSD 32 GB A1 | 1 | «SanDisk Ultra 32GB A1» | 80 kr |
| Waveshare 4,3″ DSI LCD 800×480 | 1 | AliExpress: «Waveshare 4.3inch DSI LCD capacitive» | 400–500 kr |
| PCM5102A I²S DAC-kort | 1 | AliExpress: «PCM5102A I2S DAC GY-PCM5102» | 40 kr |
| TPA3116D2 2 × 50 W stereokort | 1 | AliExpress: «TPA3116D2 2x50W stereo amplifier board» | 70–120 kr |
| Dayton Audio RS75-4 | 2 | Soundimports: «Dayton Audio RS75-4» | 2 × 300 kr |
| Strømadapter 19 V / 3,42 A (5,5 × 2,5 mm) | 1 | «19V 3.42A laptop adapter» (eller 24 V / 3 A) | 150–250 kr |
| DC-DC nedtrapper 5 V / 5 A | 1 | AliExpress: «DC-DC buck 24V to 5V 5A module» | 40 kr |
| Relémodul 1-kanal, H/L-jumper | 1 | AliExpress: «1 channel relay module 3.3V high low level trigger» | 20 kr |
| DC-kontakt for panel 5,5 × 2,1/2,5 mm (Ø 8 mm) | 1 | «DC-022 panel jack» | 15 kr |
| 3,5 mm stereokontakt for panel (Ø 6 mm) | 1 | «PJ-392 3.5mm panel jack» | 10 kr |
| USB-C panelskjøt (hunn til USB-A) | 1 | AliExpress: «USB C female panel mount to USB A male» | 40 kr |
| EC11 med trykk, 20 mm D-aksel | 1 | AliExpress: «EC11 rotary encoder 20mm D shaft» | 15 kr |
| EC11 med trykk, 15 mm D-aksel | 1 | Samme | 15 kr |
| Taktbryter 6 × 6 × 4,3 mm | 7 | «tactile switch 6x6x4.3 THT» | 10 kr |
| Hullkort 2 × (ca. 150 × 20 og 40 × 20 mm) | 1 | «perfboard 5x15 cm» | 20 kr |
| M3 innpressmutter (M3 × 5,7, Ø 4,0 hull) | 16 | «M3 heat set insert 5.7mm» | 40 kr |
| M3 × 10 senkeskrue | 8 | Bunnplata (4 hjørner + 4 kammerører) | 20 kr |
| M3 × 8 skrue | 8 | Lokket på kammeret | 15 kr |
| M3 × 10 selvgjengende | 8 | Elementene | 15 kr |
| M2,5 × 6 selvgjengende | 12 | Skjermbrakett, knappekort, av/på-kort, Pi | 15 kr |
| Gummiføtter Ø 12 mm, selvklebende | 4 | «bumpon 12mm» | 20 kr |
| Skumtape 1–2 mm, 6 mm bred | 1 m | Tetning rundt kammerlokket | 30 kr |
| Akustisk grillduk, mørk, ca. 230 × 100 mm | 1 | «speaker grill cloth black» | 40 kr |
| Dempeull / polyfill | ca. 10 g | Løst i kamrene | 30 kr |
| Ledning, skjermet lydkabel, krympestrømpe | – | | 50 kr |
| **Elektronikk totalt** | | | **ca. 2 500–2 800 kr** |
| PETG/ASA-filament (FDM) | ca. 1,0 kg | 3 farger: kropp, sort, gull | 200–300 kr |

## Kabinettet

Kabinettet er tegnet i [`skjold_radio.scad`](skjold_radio.scad) (OpenSCAD, parametrisk). [`lag_stl.sh`](lag_stl.sh) eksporterer alle STL-er, sjekker modellen ([`sjekk_modell.py`](sjekk_modell.py)) og lager 3MF-platene ([`lag_3mf.py`](lag_3mf.py)).

| Del | STL | Volum | Print (FDM) |
|---|---|---|---|
| Kropp (ett skall: sider, bak og skrå topp) | `stl/kropp.stl` | 285 cm³ | Toppflaten ned på platen. Glatt topp, ingen støtte. 236 × 173 × 130 mm. |
| Lydkammer (baffel, skillevegg, ører) | `stl/kammer.stl` | 219 cm³ | Baffelen ned. 100 % fyll i baffelen gir minst resonans. |
| Lokk for kammeret | `stl/lokk.stl` | 51 cm³ | Flatt |
| Grill | `stl/grill.stl` | 43 cm³ | Forsiden ned (glatt mot platen) |
| Bunnplate (Pi-tårn, lufting) | `stl/bunn.stl` | 128 cm³ | Undersiden ned |
| Skjermbrakett | `stl/brakett.stl` | 11 cm³ | Flatt |
| Navigasjonshjul Ø 46 | `stl/knott.stl` | 8,6 cm³ | Toppen opp. Hult nedenfra. |
| Volumknott Ø 22 | `stl/volum.stl` | 2,8 cm³ | Toppen opp |
| Knappehetter 1–6 og av/på | `stl/knapp.stl` | 4,0 cm³ | Toppen ned (sju hetter) |

3MF-plater for Creality K2 (250 × 250 mm, filament 1 = kroppsfarge, 2 = sort, 3 = gull):

- `skjold-radio-k2.3mf`: kropp, hjul, volumknott og knappehetter
- `skjold-radio-k2-kammer.3mf`: lydkammer og lokk
- `skjold-radio-k2-grill.3mf`: grill og skjermbrakett
- `skjold-radio-k2-bunn.3mf`: bunnplate

Tips for FDM: 0,16 mm lag, 3 vegger, 15 % gyroid. Bruk teksturert PEI for kroppen, så skråflaten får en jevn, matt struktur. Varm innpressmutterne inn med 220–240 °C.

**Sjekket med `sjekk_modell.py`:** alle delene er vanntette og hver er ett legeme (knapp-fila har sju hetter). Alle ligger på platen og passer i K2. Ingen deler kolliderer i montert stilling. Begge kamrene er lukket i alle retninger når lokket og elementene er på, med ca. 0,48 l netto hver. Ytterveggen er minst 2 mm overalt utenom de tiltenkte hullene.

**Lydkammeret** er en egen boks med baffel (7 mm), skillevegg og lokk med skumtape. Kroppen trenger derfor ikke være tett, og ventilasjonen til Pi-en og forsterkeren påvirker ikke bassen. Elementene skrus på baffelen forfra. Rammen havner da 1 mm bak grillens flens. Med 0,47 l per element blir Qtc ca. 1,1. Det gir en litt fyldig, «radioaktig» bass. Litt dempeull løst i kamrene gjør bassen strammere.

## Montering

1. **Innpressmuttere:** 4 i hjørnetårnene i kroppen (nedenfra), 8 bak i kammeret (lokket) og 4 i kammerørene (nedenfra).
2. **Kammeret:** trekk høyttalerkablene gjennom hullene i gulvet og tett med silikon. Skru elementene på baffelen (M3 × 10 selvgjengende). Legg i litt dempeull. Legg skumtape rundt kanten og skru på lokket (8 × M3 × 8).
3. **Toppen:** lim grillduken på baksiden av grillen. Sett grillen inn fra undersiden av kroppen (flensen legger seg i falsen på sidene og oppe).
4. **Skjermen:** legg skjermmodulen i lomma under vinduet, med 1 mm skumtape mot kanten. Skru skjermbraketten over med 4 × M2,5.
5. **Knappene:** sett de seks favoritthettene og av/på-hetta i hullene fra innsiden. Lodd taktbryterne på hullkortene med 23 mm mellom bryterne (favoritter). Skru kortene på tårnene under toppen (M2,5).
6. **EC11:** hjulet monteres gjennom toppen og volumknotten gjennom høyre side, med mutter. Trykk på knottene.
7. **Bunnplata:** skru Pi-en på tårnene (M2,5) med USB-C/HDMI-kanten mot bakveggen. Fest forsterkeren, nedtrapperen og releet med dobbeltsidig tape over luftespaltene. Monter DC-, 3,5 mm- og USB-C-kontaktene i bakveggen.
8. **Kammeret på bunnplata:** 4 × M3 × 10 senkeskrue nedenfra i ørene. Kammeret holder grillen på plass via midtribben.
9. **Kobl til** etter tabellen over. Sett kroppen ned over alt og skru bunnplata fast i hjørnene (4 × M3 × 10). Sett på gummiføttene i forsenkningene.

## Programvare

Radioen bruker vanlig Skjold med Kit-profilen, med knappene som en liten egen tjeneste ([`pi/skjold_radio_knapper.py`](../../pi/skjold_radio_knapper.py)). Daemonen trenger ingen endringer.

```bash
cd pult-forsterker/pi && KI_AMP_BOARD=kit KI_AMP_NAME="Skjold Radio" bash install.sh
```

```bash
sudo install -m 755 skjold_radio_knapper.py /usr/local/bin/ && sudo install -m 644 skjold-radio-knapper.service /etc/systemd/system/
```

```bash
sudo mkdir -p /etc/skjold && sudo cp config/radio_pins.yaml /etc/skjold/ && sudo systemctl daemon-reload && sudo systemctl enable --now skjold-radio-knapper
```

```bash
sudo bash install_skjold_ui.sh
```

- **Skjermen:** legg inn DSI-linja fra Waveshares wiki for «4.3inch DSI LCD» i `/boot/firmware/config.txt`. skjold-ui viser da Skjold-skjermen i Chromium. skjold-ui er tegnet for 960 × 320 (S1). På 800 × 480 vises den, men oppsettet er ikke tilpasset ennå.
- **Favoritt 1–6:** kort trykk spiller favoritten, hold 2 s lagrer det som spiller.
- **Hjulet:** drei for å bla i favorittene (starter etter 0,6 s ro), trykk for spill/pause.
- **Volumknotten:** drei for volum ±2, trykk for å dempe.
- **Av/på:** kort trykk for av/på, hold 3 s for omstart.
- **Endre pinner:** rediger `/etc/skjold/radio_pins.yaml` og kjør `sudo systemctl restart skjold-radio-knapper`.

## Bestille print

Du kan bestille alle delene i resin (SLA) eller nylon (MJF) i stedet for å printe dem selv. Last opp STL-ene fra `stl/` direkte; de er allerede orientert, men tjenestene snur dem selv.

**Kan resin bli like pent som sprøytestøpt plast?** Nesten. SLA-resin har ingen synlige lag. Med 0,05 mm lag og en god resin som JLC 8001 eller 9600 blir overflaten glatt og matt, og kantene skarpe. Det skiller seg fra sprøytestøpt plast på tre punkter:

1. **Støttemerker:** små prikker der støttene satt. Be om at de plasseres på innsiden. Kroppen er et åpent skall, så det går fint.
2. **Overflaten:** den er glatt, men ikke helt «støpt». Etter sliping (400 → 800 → 1500 vått), sprøyteprimer, ny sliping og 2–3 lag lakk (matt eller silkematt 2K/akryl) er det svært vanskelig å se forskjell på 30 cm avstand.
3. **Holdbarhet:** standardresin er hardere, men sprøere enn ABS/PC. Den kan sprekke hvis radioen faller i gulvet. Resin gulner også litt i sol over tid; lakk med UV-filter hjelper. Innpressmuttere fungerer dårlig i resin, så **lim M3-muttere (epoksy) i stedet**, eller bruk selvgjengende skruer.

**MJF (HP Multi Jet Fusion) i PA12, farget sort** er det andre gode valget. Det er seigt som sprøytestøpt nylon, tåler fall og innpressmuttere, og har en jevn, litt sandaktig matt overflate. Det ser ut som et ferdig produkt rett fra maskinen. Det kan ikke bli blankt eller lyst uten maling, og det er bare grått eller sort. For den lyse varianten må du slipe og male.

| Prosess | Overflate | Styrke | Detaljer | Etterarbeid for «støpt» look |
|---|---|---|---|---|
| **SLA resin** (JLC 8001/9600, sort/hvit resin) | Glattest, ingen lag | Hard, sprø | Skarpest (0,05 mm) | Fjern støttemerker, slip, primer, lakk |
| **MJF PA12, farget sort** | Jevn matt sandstruktur | Best (seig nylon) | Gode (0,08 mm) | Ingen for mørk variant; ev. damping/«vapor smoothing» for halvblank |
| **FDM PETG/ASA** (egen K2) | Lag synlige på sidene; toppflaten glatt (mot PEI) | God | OK (0,4 mm dyse) | Mye: sparkel, primer, sliping, lakk |

**Tjenester:**

- **JLC3DP (JLCPCB):** billigst for SLA og MJF, rask frakt til Norge (DHL/FedEx, ca. 5–8 dager). Resinene 8001 (gjennomskinnelig), 9600 (hvit, grei), Imagine Black (sort) og LEDO 6060 (seigere). MJF PA12 i grått, farget sort ved bestilling.
- **PCBWay:** samme prosesser og ofte litt dyrere, men flere materialer: tåleligere resin, MJF, SLS og ferdig lakkering («painting/spraying» som tilleggstjeneste).
- **Craftcloud (All3DP):** sammenligner mange verksteder, også i Europa. Det gir kortere vei og ofte ingen toll, men pris og kvalitet varierer.

**Prisanslag per del (november 2026, uten frakt og MVA).** Dette er anslag ut fra volum og størrelse, ikke tilbud. Last opp STL-ene for eksakt pris.

| Del | SLA resin (JLC3DP) | MJF PA12 sort (JLC3DP) | Craftcloud (EU, SLA/MJF) |
|---|---|---|---|
| Kropp (285 cm³, 236 × 173 × 130) | 700–1 300 kr | 800–1 500 kr | 1 500–3 000 kr |
| Grill (43 cm³) | 120–250 kr | 150–300 kr | 300–600 kr |
| Hjul + volumknott + 7 knappehetter (15 cm³) | 60–150 kr | 80–180 kr | 200–400 kr |
| Lydkammer + lokk (270 cm³, usynlig) | 600–1 100 kr | 700–1 300 kr | – (print selv) |
| Bunnplate + brakett (139 cm³, usynlig) | 300–600 kr | 350–700 kr | – (print selv) |
| Frakt til Norge | 200–350 kr | 200–350 kr | 0–200 kr |

Legg til 25 % MVA (og eventuelt fortollingsgebyr på ca. 100–200 kr fra Kina).

**Anbefaling:** bestill bare de synlige delene i resin eller MJF (kropp, grill, hjul, volumknott og knappehetter, ca. 1 100–2 000 kr med frakt og MVA). Print lydkammeret, lokket, bunnplata og braketten selv på K2. De synes ikke, og kammeret blir faktisk bedre i tett PETG enn i hul resin. Velg MJF sort for den mørke varianten uten maling, og SLA med sliping, primer og lakk for den lyse varianten som skal se mest mulig sprøytestøpt ut.

## Lisens

Maskinvare: CC BY-NC-SA 4.0 (se [LISENS-MASKINVARE.md](../../LISENS-MASKINVARE.md)).
