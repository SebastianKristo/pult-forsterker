# KI Pultforsterker – Byggeveiledning

Oct 28, 2026 · @Sebastian

Steg-for-steg fra deler i posen til ferdig forsterker under pulten. Deleliste, koblingsskjema og kode står i hoveddokumentet; dette er monteringen.

## Før du starter

Sett av to kvelder: én til elektronikken på bordet, én til kabinettet. Alt testes før det skrus fast, så feil er billige å rette.

**Verktøy**: loddebolt (med flat spiss til varmeinnsatsene), loddetinn, avbiter, avisoleringstang, liten stjerne- og unbrakonøkkel (2 mm til M3 senkskruer, 1,5 mm til knottens settskrue), multimeter, 2,5 mm og 3 mm bor, hobbykniv, og en 3D-printer.

**Deler**: se delelisten i hoveddokumentet. Pakk ut alt og legg det i rekkefølgen under – da ser du med én gang om noe mangler.

**Sikkerhet**: 24 V DC er ufarlig å ta på, men forsterkerkortet kan levere 4 A – en kortslutning smelter en tynn ledning. Koble aldri 24 V-adapteren til før alle 24 V-ledninger er ferdig loddet og krympet. Pi-en tåler ikke mer enn 5,25 V; mål buck-utgangen hver gang før du kobler den til.

&#91;image: Delene: kasse, frontplate og lokk\]

Kabinettet er tre printede deler. Kassen rommer all elektronikk, frontplaten skrus utenpå fronten og klemmer akrylvinduet, og lokket skrus i pulten – kassen henger i lokket med fire M3-skruer i varmeinnsatser.

## Steg 1 – Elektronikken på bordet

Målet med steget: Pi-en spiller AirPlay og Bluetooth gjennom DAC-en, og skjermen viser oppstartsbildet. Ingenting er skrudd fast ennå.

1. **Skriv SD-kortet.** Raspberry Pi Imager → Raspberry Pi OS Lite (64-bit). Under «OS customisation»: vertsnavn `pultamp`, brukernavn/passord, Wi-Fi (2,4 GHz) og SSH på.
2. **Lodd DAC-kortet.** Snu PCM5102A-kortet. Lodd broene: **FLT → L, DMP → L, XMT → H, FMT → L**. Sjekk med multimeter at **SCK** har kontakt til GND (lodd en bro hvis ikke). Lodd pinnelisten på (eller bruk Dupont rett i hullene midlertidig).
3. **Koble DAC til Pi** med fem Dupont-ledninger: Pi pinne 4 (5 V) → VIN, pinne 6 (GND) → GND, pinne 12 (GPIO 18) → BCK, pinne 35 (GPIO 19) → LCK, pinne 40 (GPIO 21) → DIN.
4. **Koble OLED** med fem ledninger: pinne 1 (3,3 V) → VCC, pinne 9 (GND) → GND, pinne 3 → SDA, pinne 5 → SCL, pinne 7 (GPIO 4) → RES. OLED-ens DC og CS kobles til GND.
5. **Start Pi-en** fra en vanlig USB-lader i PWR-porten, vent 1–2 min, `ssh <bruker>@pultamp.local`.
6. **Kopier programvaren**: `scp -r software <bruker>@pultamp.local:~` fra PC-en, så `bash ~/software/install.sh` på Pi-en. Det tar 20–30 min. `sudo reboot` etterpå.
7. **Test**: `aplay -l` skal vise `sndrpihifiberry`, `i2cdetect -y 1` skal vise `3c`. Sett hodetelefoner i DAC-ens 3,5 mm-utgang og spill AirPlay til «Pultforsterker» fra en iPhone. Skjermen skal vise oppstartsbildet, så tittel og artist.
8. **Koble knappene løst**: hver inngangsknapp har 4 pinner – de to på bryterdelen (merket C/NO, eller de to lengst fra LED-merkene) går til GPIO og GND. Test at trykk bytter felt på skjermen. Encoderen: CLK/DT/SW/+/GND → GPIO 23/24/25, 3,3 V, GND; vri skal endre VOL-tallet.

Når alt dette virker, har du verifisert Pi, DAC, OLED, knapper og programvare – resten er mekanikk og strøm.

## Steg 2 – Print og klargjør kabinettet

Mål først, print så. Åpne `pultforsterker_v2.scad` og kontroller disse fire parametrene mot delene du har fått:

| Parameter | Mål på delen | Standard i filen |
| --- | --- | --- |
| `amp_holes` | avstand mellom de to hullene på XH-M562 (x og y) | 50 × 42 |
| `post_d` | gjengediameter på bananterminalene + 0,4 | 6,4 |
| `oled_x`, `oled_w/h` | glassets senter i forhold til kortet | −30, 57 × 30 |
| `btn_d`, `pwr_d` | gjengediameter på 12 og 16 mm-knappene + 0,4 | 12,4 / 16,4 |

**Print i denne rekkefølgen**

1. **Frontplaten først** (10 min, forsiden ned mot platen, 0,16 mm lag). Prøv alle fem knappene, encoderen og akrylet i den før du printer resten – passer det her, passer det i kassen.
2. **Kassen** (ca. 6 t, åpningen opp, 0,2 mm lag, 4 perimetere, 25 % gyroid, ingen støtte). PLA Matte antrasitt; PETG hvis du vet at forsterkeren kommer til å gå hardt.
3. **Lokket** (ca. 2 t, flatt med ørene ned, 0,16 mm lag).

**Etterarbeid**

- Rens alle hull med et bor i riktig diameter (ikke driv boret, bare rotér for hånd).
- **Varmeinnsatser**: sett loddebolten på 200–220 °C, legg en M3-innsats på hvert av de fire tårnene i kassen, trykk den rett ned til den er plan med toppen. Fire stykker. La det kjøle 30 s før du skrur i.
- Skjær akrylet til **70 × 38 mm** med hobbykniv (riss 5–6 ganger, knekk over en kant) eller få det laserkuttet. Rund hjørnene lett med fil. La beskyttelsesfolien stå på til siste steg.

## Steg 3 – Bakveggen

&#91;image: Bakvegg med nummererte hull\]

Monter bakfra og innover, i nummerrekkefølgen på bildet. Alle kontaktene skal ha ledningene loddet på **før** de settes i veggen – det er trangt å lodde inne i kassen.

1. **KCD1 hovedbryter** – krymp to flatstifthylser 4,8 mm på hver sin 18 AWG rød (15 cm), sett dem på bryteren, og trykk bryteren inn i utsparingen til den klikker. Den sitter med fjærklemmene; ingen skruer. Merkingen «I/O» vendes slik at I er opp.
2. **DC-099** – lodd 18 AWG rød (10 cm) på senterpinnen og 18 AWG svart (20 cm) på hylsen (den lengste tungen); den tredje tungen lar du stå. Krymp. Stikk inn fra utsiden, mutter innvendig, stram med fingrene + en kvart omdreining med tang.
3. **USB-C-flens** – fra innsiden: før USB-C-enden ut gjennom det rektangulære hullet, og skru de to ørene fast med M2,5 × 6 i de to små hullene (forbor 2 mm). Micro-USB-enden ligger løs inni foreløpig.
4. **AUX-jack PJ392** – lodd skjermet kabel (20 cm): leder 1 → tip, leder 2 → ring, skjerm → sleeve (den lange tungen). Krymp. Inn fra utsiden, mutter innvendig.
5. **Høyre høyttaler** – rød terminal i hullet ved x −30, svart ved x −45. Lodd 18 AWG (15 cm) på hver (rød på rød, svart på svart) før montering, eller bruk loddetungen innvendig etterpå. Isolasjonsskivene skal sitte på begge sider av veggen – terminalkroppen må ikke berøre noe metall.
6. **Venstre høyttaler** – samme ved x −65 (rød) og −80 (svart).

Sjekk med multimeter: ingen kontakt mellom noen av de fire terminalene, og ingen kontakt mellom DC-099-senter og hylse.

## Steg 4 – Fronten

&#91;image: Front med nummererte posisjoner\]

Fronten bygges i to lag: først OLED-kortet på innsiden av kasseveggen, så akryl og frontplate utenpå, og til slutt knappene gjennom begge.

1. **OLED-kortet (innvendig).** Skru fire M2-avstandsstykker (6 mm) i kortets hjørnehull med M2-muttere. Hold kortet mot innsiden av frontveggen med glasset sentrert i vinduet (x = −30). Marker hvor avstandsstykkene treffer veggen, sett en dråpe superlim eller en bit VHB på hver, og trykk kortet på plass. Glasset skal ligge 1–2 mm bak veggen – ikke presse mot akrylet. Lodd ledningene (7 stk, 20 cm) på kortet **før** du limer.
2. **Akryl (2).** Ta folien av én side, legg akrylet i forsenkningen på baksiden av frontplaten med den avdekkede siden mot platen. Det skal ligge plant; sitter det stramt, fil kantene litt.
3. **Frontplaten** – hold den mot fronten med akrylet innerst, sett de fire **M3 × 8 senkskruene** (8) i hjørnene og skru rett i veggens 2,6 mm-hull. Stram jevnt, kryssvis, til platen ligger an – ikke mer; plasten gjenger seg selv.
4. **POWER-knappen (1)** – skru av mutteren, stikk knappen gjennom hullet ved x −80 (den kommer med Dupont-ledninger på), mutter innvendig. Drei knappen så strømsymbolet står rett før du strammer.
5. **Inngangsknappene (3–6)** – AIRPLAY øverst venstre, BT øverst høyre, AUX nederst venstre, USB nederst høyre. Lodd fire ledninger på hver (2 til bryteren, 2 til LED-ringen, 20 cm) **før** du monterer, merk dem med tape (A/B/X/U). Gjennom hullet, mutter innvendig. Gjengelengden er 8–10 mm, frontplate + vegg er 4,7 – det er god margin.
6. **Encoder (7)** – KY-040-kortet legges i utsparingen på innsiden ved x 70 med akselen ut gjennom hullet; mutter utvendig under knotten. Sett knotten på D-akselen, trykk den inn til 1 mm fra platen, stram settskruen mot flaten på akselen.

Ta den siste folien av akrylet nå. Prøv alle knappene – de skal gå fritt og klikke tydelig.

## Steg 5 – Kort og moduler inni

&#91;image: Innvendig plassering sett ovenfra\]

Plasseringen er valgt så strøm holder seg bak til høyre, lyd i midten, og Pi-en bak til venstre nær USB-C. Lodd alle ledninger på modulene på bordet før de festes.

|  | Modul | Feste | Plassering og retning |
| --- | --- | --- | --- |
| A | Forsterker XH-M562 | 2 × M3 × 6 i stolpene (de to som matcher kortets hull) | høyre side, pinnelisten (IN/SP/VCC) mot bakveggen – kort vei til terminalene |
| B | Pi Zero 2 W | 4 × M2,5 × 6 i stolpene | venstre bak, micro-USB-portene mot bakveggen, SD-kortet mot sideveggen |
| C | DAC PCM5102A | VHB-tape | foran Pi-en, pinnene mot Pi-en |
| D | Buck 24 → 5 V | VHB-tape | i hjørnet ved DC-099 |
| E | Relékort 4-ch | VHB (eller M3 + nylon-avstandsstykker) | midt bak, skrueterminalene mot forsterkeren |
| F | MOSFET-kort × 2 | VHB, kort 2 stablet oppe på kort 1 med nylon-avstandsstykker | foran til høyre under knottene |
| G | X9C × 2 | VHB, side om side | midt i kassen, rett foran forsterkerens IN-pinner |
| H | OLED | allerede montert i steg 4 |  |

**Rekkefølge**: A og B først (skrudd), så E, deretter D, C, G og F. VHB-tape: trykk hardt i 10 s, ikke flytt etterpå. Legg et stykke isolasjonstape under Pi-en og DAC-en hvis de ligger nær et skruetårn – ingen loddepunkter skal kunne berøre metall.

Micro-USB-enden av USB-C-kabelen settes i Pi-ens **innerste** micro-USB (merket USB, ikke PWR) nå.

## Steg 6 – Ledninger

Tre grupper, i denne rekkefølgen: **24 V**, så **5 V**, så **signal**. Hold 24 V- og høyttalerledningene langs høyre side av kassen, lydkablene i midten, og fest med kabelstrips med klebefot.

**24 V (18 AWG rød/svart)**

| Fra | Til |
| --- | --- |
| DC-099 senterpinne (+) | KCD1 pinne 1 |
| KCD1 pinne 2 | Relékort **COM 3** *og* buck **IN+** (to ledninger fra samme punkt) |
| Relékort **NO 3** | Forsterker **VCC** |
| DC-099 hylse (−) | Forsterker **GND**, buck **IN−**, og relékortets GND-skinne |
| Forsterker SPR+ / SPR− | Høyre rød / svart terminal |
| Forsterker SPL+ / SPL− | Venstre rød / svart terminal |

Aldri koble SPL− og SPR− sammen eller til jord – forsterkeren er bro-koblet.

**5 V (22 AWG)** – slå på hovedbryteren med adapteren tilkoblet og **mål 5,0 V på buck OUT** før du går videre. Slik av igjen.

| Fra buck OUT+ / OUT− | Til |
| --- | --- |
|  | Pi pinne 2 (5 V) og pinne 6 (GND) – eller PP1/PP6 på undersiden |
|  | Relékort VCC og GND (jumper VCC–JD-VCC på) |
|  | MOSFET-kort 1 og 2: VCC og GND på lastsiden |
|  | LED-ringenes **+** på alle fem knappene (samle dem i én ledning) |

**Signal (Dupont hunn–hunn fra Pi-ens header)**

| Pi-pinne | GPIO | Til |
| --- | --- | --- |
| 3 / 5 / 7 | 2 / 3 / 4 | OLED SDA / SCL / RES |
| 12 / 35 / 40 | 18 / 19 / 21 | DAC BCK / LCK / DIN (+ pinne 4 → VIN, pinne 6 → GND) |
| 29 / 31 / 32 / 33 | 5 / 6 / 12 / 13 | Knapp AIRPLAY / BT / AUX / USB (andre bryterpinne → GND) |
| 36 | 16 | POWER-knappens bryter (andre → GND) |
| 16 / 18 / 22 | 23 / 24 / 25 | Encoder CLK / DT / SW (+ → pinne 1, GND → GND) |
| 26 / 24 / 21 / 19 | 7 / 8 / 9 / 10 | MOSFET-kort 1 IN1–IN4 (ring AIRPLAY / BT / AUX / USB) |
| 23 | 11 | MOSFET-kort 2 IN1 (ring POWER) |
| 15 | 22 | Relékort IN1 og IN2 (brø dem sammen) |
| 13 | 27 | Relékort IN3 |
| 37 / 8 / 10 | 26 / 14 / 15 | X9C INC / U/D / CS – begge modulene parallelt |

MOSFET-kortenes jumper på **3.3V**; GND på signalsiden til Pi GND. LED-ringenes **−** til MOSFET OUT− på sin kanal.

**Lyd (skjermet kabel)**: AUX tip/ring → relé 1 NO / relé 2 NO. DAC L/R → relé 1 NC / relé 2 NC. Relé 1 COM → X9C-A VH, relé 2 COM → X9C-B VH. X9C-A VW → forsterker INL, X9C-B VW → INR. X9C VL begge → forsterker GND (IN-siden). Skjermen i alle lydkabler kobles til jord **bare** i forsterker-enden. X9C VCC/GND fra Pi 5 V/GND.

## Steg 7 – Test, lokk og montering

**Test i åpen kasse** (lokket av, høyttalere tilkoblet, volum på 0):

1. Hovedbryter på. POWER-ringen lyser, skjermen viser oppstartsbildet, så hovedskjermen. Relé 3 klikker (forsterkeren får strøm).
2. Trykk gjennom AIRPLAY → BT → AUX → USB. Feltet på skjermen og LED-ringen skal følge; på AUX klikker relé 1+2.
3. Spill AirPlay fra telefonen, vri volumet sakte opp. Lyd i begge kanaler? Trykk knotten – MUTE.
4. Hold AIRPLAY 2 s: BT-ringen pulserer, skjermen viser «Parring». Parr telefonen, spill – tittel skal vises.
5. Koble PC-en til USB-C bak, velg «UAC2 Gadget» som lydenhet, trykk USB. Spill.
6. Sett 3,5 mm-kabel fra PC/Mac i AUX, trykk AUX. Spill.
7. Kort trykk på POWER: skjerm av, relé av, POWER-ring dimmet. Trykk igjen: oppstart.
8. Maks volum uten signal: skal være stille. Svak sus er normalt; brum betyr jordsløyfe (se feilsøking).

**Lokk**: legg lokket på, fire **M3 × 8 senkskruer** i hjørnene ned i innsatsene, kryssvis. Ledningene til bakveggen må ikke ligge i klem under kanten.

**Under pulten**: hold lokket mot undersiden der du vil ha det (fronten mot deg, 2–3 cm inn fra forkanten), merk de fire slissene, forbor 3 mm, skru lokket fast med **4 × 25 mm treskruer**. Heng kassen i lokket og skru de fire M3-skruene fra undersiden. Kabler til adapter, høyttalere og PC føres bakover langs pulten gjennom kabelutsparingen i lokket.

## Daglig bruk

| Handling | Gjør |
| --- | --- |
| Velg kilde | trykk AIRPLAY / BT / AUX / USB – ringen lyser på aktiv |
| Volum | vri knotten (2 %/klikk); trykk = mute |
| Standby | kort trykk POWER; kort trykk igjen = på |
| Omstart | hold POWER 3 s (ring fylles på skjermen) |
| Bluetooth-parring | hold AIRPLAY 2 s; synlig som «Pultforsterker» i 2 min |
| Helt av | hovedbryter bak |
| Fra Home Assistant / Homey | kilde, volum, mute, av/på og BT-parring fra appene |

**Feilsøking**

| Symptom | Sjekk |
| --- | --- |
| Skjermen svart | `i2cdetect -y 1` viser `3c`? RES på GPIO 4? `systemctl status oled-display` |
| Ingen lyd på AirPlay/BT/USB, lyd på AUX | DAC-broer (SCK til GND), `aplay -l` viser hifiberry, relé 1+2 i NC |
| Ingen lyd på AUX | relé 1+2 trekker (klikk)? AUX-jackens sleeve til jord |
| Lyd bare i én kanal | X9C-modulen for den kanalen: VH/VW/VL riktig vei, INC/UD/CS koblet |
| Volum går ikke å stille | `journalctl -u ki-amp`; serial console må være av (GPIO 14/15) |
| Brum på AUX/USB | jordsløyfe mot PC-en: ground-loop-isolator på AUX, USB-isolator på USB |
| Pi starter på nytt tilfeldig | buck-utgang under 4,8 V under last – tykkere 5 V-ledning eller bedre buck |
| LED-ring lyser ikke | MOSFET-jumper på 3.3V, ring + på 5 V, − på OUT− |
| Finner ikke forsterkeren i HA/Homey | `curl http://pultamp.local:8765/api/status`; samme Wi-Fi/VLAN som HA |

**Interaktiv 3D-modell av det ferdige produktet:** [KI Pultforsterker 3D](https://claude.ai/artifact/RJJtac14L9A3EkNhTBcTzU) – roter, se front/bak/ovenfra, løft lokket, og klikk på knapper og kontakter for forklaring.
