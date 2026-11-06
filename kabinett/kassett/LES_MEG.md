# Skjold Kassett

En liten spiller der du setter inn en «kassett» med en NFC-brikke. Skjold spiller det kassetten er koblet til:
en radiokanal, en NRK-serie, et Navidrome-album eller en spilleliste, noe fra Music Assistant eller en rutine.
Når du tar kassetten ut, pauses musikken (kan slås av per kassett).

![Spiller med kassett](render/02_med_kassett.png)

Bilder: [spiller](render/01_spiller.png) · [med kassett](render/02_med_kassett.png) · [kassett](render/03_kassett.png) · [kassett bakfra](render/05_kassett_bak.png) · [eksplodert](render/04_eksplodert.png) · [snitt](render/06_snitt.png)

## Deler

| Del | Antall | Merknad |
|---|---|---|
| Waveshare ESP32-S3 Zero | 1 | klikkes i vugga på bunnen, USB-C mot hullet bak |
| PN532 NFC-modul V3 (I²C), 42,7 × 40,5 mm | 1 | skyves inn i skinnene bak sporet, antennesiden mot sporet, pinnene ned. DIP: 1=ON, 2=OFF |
| WS2812B-stripe 10 mm, 60 LED/m | 5 LED (ca. 85 mm) | står på høykant i kanalen rundt sporet: venstre side, front, høyre side |
| Passiv piezo-summer 12 mm | 1 | valgfri, ligger med lydhullet ned i ringen på bunnen |
| NTAG215 NFC-klistremerke, 25 mm | 1 per kassett | NTAG213/216 virker også |
| Neodymmagnet 6 × 3 mm | 1 i spilleren + 1 per kassett | sjekk polaritet før liming |
| M3 innpressmutter (heat-set), M3 × 5,7 mm, Ø ≤ 4,6 mm | 4 | hull Ø 4,0 × 6,5 mm i skruetårnene |
| M3 × 8 mm senkehodeskrue (DIN 7991) | 4 | fra undersiden |
| Selvklebende gummiføtter Ø 10 mm | 4 | i de grunne forsenkningene under |
| Tynn silikonledning (26–28 AWG) | litt | |
| USB-C-kabel og 5 V-lader | 1 | |

## Kobling

| Fra | Til ESP32-S3 Zero |
|---|---|
| PN532 VCC / GND | 3V3 / GND |
| PN532 SDA | GPIO5 |
| PN532 SCL | GPIO6 |
| WS2812 DIN | GPIO4 (5 V og GND fra 5V-pinnen) |
| Piezo + | GPIO7 (– til GND) |

## Slik er spilleren bygd

![Snitt gjennom sporet](render/06_snitt.png)

- **Lokk og bunn skrus sammen** med fire M3-skruer fra undersiden inn i innpressmuttere i skruetårnene i hjørnene.
  Bunnen ligger inne i lokket og presses mot en skrå hylle innvendig: skjøten blir en labyrint (lystett og uten synlig
  spalte på sidene), og bunnen flukter med lokkets underkant.
- **Sporet** er en lomme som heller 12° bakover, med vannrett bunn. Kassetten står 38 mm ned, slik at NFC-brikken
  havner foran PN532-antennen. Klaring 0,6 mm rundt kassetten.
- **Magneten** trykkes inn nedenfra i et tårn under sporbunnen (0,6 mm vegg mot kassettens magnet).
- **LED-kanalen** går rundt sporet foran og på sidene, 15 mm dyp: stripa står på høykant mot lommeveggen med lysene utover,
  og lyset kommer opp gjennom lyslederen, som ligger flatt i toppen (flukter med lokket) og hviler på en liten avsats.
  Bak sporet er kanalen bare 5 mm dyp, så PN532-modulen får plass rett bak lommeveggen. Ledningene går ned gjennom et
  hull i kanalbunnen på høyre side.
- **PN532** skyves inn nedenfra i to skinner på baksiden av sporlomma og stopper øverst. En dråpe varmlim nederst holder den.
- **ESP32-S3 Zero** klikkes ned i vugga bak; USB-C-hullet i bakveggen er stort nok til vanlige plugger.
- **Summeren** ligger med lydhullet ned over seks små hull i bunnen. Tre små kabelbuer på bunnen holder ledningene på plass.

Kontrollert i modellen (trimesh/manifold): alle STL-er er vanntette, én sammenhengende del hver, og ingen deler
overlapper i montert stilling (lokk, bunn, lysleder, kassett, PN532 og ESP). Minste avstand kassett–spor er 0,1 mm
i de skrå hjørnene og 0,6 mm på sidene.

## Utskrift (Creality K2 / K2 Pro / K2 Plus, 0,4 mm dyse)

Hovedfila er **`skjold-kassett-k2.3mf`**: én plate (244 × 240 mm, passer alle K2-modellene) med lokk, bunn, lysleder og
fire kassetter, ferdig orientert. Delene har fått hvert sitt filamentnummer, så med CFS printes alt på én gang:

| Filament | Deler | Forslag |
|---|---|---|
| 1 | Lokk | Lys PETG (eller PLA) |
| 2 | Bunn og kassettenes bakside | Sort PETG/PLA |
| 3 | Kassettenes forside | Sennep/gull PLA |
| 4 | Lysleder | Klar eller natur PETG |

Uten CFS: velg delene for én farge om gangen (eller slett resten) og print i flere omganger. Hvis slicer-en ikke
henter filamentnummeret fra fila, setter du det per objekt i lista. Enkeltdelene ligger også i `stl/`, allerede
snudd riktig vei.

Anbefalte innstillinger (Creality Print 6 / OrcaSlicer, K2-profilen for 0,4 mm):

| Innstilling | Verdi |
|---|---|
| Lag | 0,20 mm (0,16 mm for kassettene gir penere tekst) |
| Vegger | 3 (lokket: 4) |
| Topp/bunn | 5 / 4 lag |
| Fyll | 15 % gyroid |
| Støtte | **av** – ingen deler trenger støtte |
| Brim | av (lokket: 3 mm brim hvis platen er glatt og du printer PETG) |
| Søm | bak (aligned/back) |
| Ytre vegg | ca. 150 mm/s for penest overflate, resten med standardprofilen |
| PLA | 210–220 °C, plate 55 °C |
| PETG | 235–245 °C, plate 70 °C, kjøling 40–60 % |
| Plate | teksturert PEI gir en matt, jevn toppflate på lokket |

Utskriftsretning og hvorfor:

- **Lokket printes med toppen ned.** Toppflaten blir den første flaten mot platen – helt plan og jevn (teksturert PEI
  gir et fint mønster). Toppkanten har 45°-fas i stedet for rund kant, så den printes uten støtte og uten elefantfot.
  Sporbunnen, LED-kanalens bunn og avsatsen for lyslederen er vannrette broer (maks ca. 12 mm). Skinnene for PN532
  har 45°-fas i enden.
- **Bunnen** printes flat, med 0,4 mm fas nederst mot elefantfot.
- **Lyslederen** printes med toppen ned (flaten som synes ligger mot platen).
- **Kassetthalvdelene** printes med utsiden ned (uendret fra før).

Ingen pause trengs: NFC-brikken og magneten legges i kassetten når halvdelene settes sammen (lommene er åpne innover),
magneten i spilleren trykkes inn nedenfra etter print, og innpressmutterne smeltes inn med loddebolt (ca. 220 °C).

Vekt (fra STL-volum, PETG 1,27 / PLA 1,24 g/cm³, 100 % fylt – med 3 vegger og 15 % fyll blir det litt mindre):
lokk ≈ 130 g, bunn ≈ 30 g, lysleder ≈ 2 g, kassett ≈ 16,5 g. Hele plata ≈ 230 g. Tid er ikke slicet – regn med
flere timer for hele plata; slicer-en viser riktig tid.

### Kassetten

Kassetten er formet som en gammel kompaktkassett: etikettfelt øverst, trapes med to styrehull og SKJOLD nederst
foran, og bak to spolevinduer med tannhjulsnav, et lite sentervindu og «skruer» i hjørnene. Navene står på fremre
halvdel og stikker gjennom vinduene i bakre – de fungerer også som styring når halvdelene settes sammen.

Den er bygd som to tynne skall (1,2 mm hud, 1,6 mm vegg) med ribber i stedet for massive plater:

| | Før | Nå |
|---|---|---|
| Front | 20,5 g | 8,6 g |
| Bak | 20,9 g | 7,8 g |
| **Per kassett** | **41,4 g** | **16,4 g** (≈ 60 % mindre) |

Ytre mål 50 × 70 × 10 mm. NFC-brikken (NTAG215, 25 mm) ligger i en ring rett innenfor bakhuden, og magneten (6 × 3 mm)
sitter i bunnkanten midt i skjøten. Etikettene (43,2 × 51,2 mm) limes på feltet som er markert med en tynn linje.

## Montering

1. Smelt de fire innpressmutterne inn i skruetårnene i lokket (loddebolt, rett ned, ikke for dypt).
2. Trykk magneten inn i tårnet under sporbunnen fra innsiden. Sjekk polariteten mot en kassett først, og lim.
3. Lodd ledninger på LED-stripa, trekk dem gjennom hullet i kanalbunnen på høyre side, og fest stripa på høykant mot
   lommeveggen (tapen på baksiden) – venstre side, front, høyre side. Trykk lyslederen ned i åpningen fra toppen.
4. Skyv PN532 inn i skinnene nedenfra, antennesiden mot sporet og pinnene ned. Prikk varmlim nederst.
5. Klikk ESP32-S3 Zero ned i vugga på bunnen med USB-C bakover, legg summeren i ringen, og lodd etter tabellen over.
   Legg ledningene under kabelbuene.
6. Sett bunnen inn i lokket og skru fast med fire M3 × 8 senkeskruer. Fest gummiføttene.
7. Kassett: legg NFC-brikken i ringen i bakre halvdel og magneten i lomma nederst, og trykk halvdelene sammen
   (tappene i hjørnene holder; en dråpe lim gjør den permanent).

## Fastvare

`esphome/skjold-kassett.yaml`. Fyll inn Wi-Fi og adressen til Skjold (`skjold_host`), og flash:

```bash
esphome run esphome/skjold-kassett.yaml
```

Spilleren sender `POST /api/nfc/scan` og `/api/nfc/remove` til Skjold-daemonen.

## Koble kassetter

I Skjold-appen: **Innstillinger → Integrasjoner → Skjold Kassett**. Trykk «Koble ny kassett», velg hva som skal spilles
(eller «det som spiller nå»), rom og volum, og sett inn kassetten innen 60 sekunder. Under «Skriv ut etiketter»
får du et A4-ark med 44×52 mm-etiketter med omslag. Ferdige etikettmaler ligger også i `etiketter_a4.svg/pdf/dxf`.

## Lag kassett med telefonen

Du trenger ikke spilleren for å koble kassetter:

1. Gå til **Innstillinger → Kassetter → Lag kassett** i Skjold-appen på mobilen.
2. Velg en radiofavoritt, en spilleliste eller en podkast.
3. Hold telefonen mot NFC-brikken. Appen leser UID-en og skriver lenken `skjold://kassett/<UID>` på brikken. Kassetten registreres på Skjold.
4. Du får en ferdig etikett som PDF med samme mål og kuttlinjer som `etiketter_a4.svg`.

Skjold lager etiketten selv på `GET /api/nfc/label?uids=…`. Coveret er bakt inn i arket, så det kan skrives ut uten nett.

På iPhone krever NFC-skriving en betalt Apple-utviklerkonto. Uten den bruker appen spilleren i læremodus, se `skjold/ios/Entitlements/Skjold-NFC.entitlements`. På Android virker det på alle telefoner med NFC.

## Kreditering og lisens

Idéen er inspirert av TheStockPots «ESPHome Cartridge Player» (CC BY-NC 4.0). Ingen geometri er kopiert –
kabinettet er tegnet på nytt fra bunnen i OpenSCAD.

Maskinvaren (denne mappen) er lisensiert under **CC BY-NC-SA 4.0**, se [LISENS-MASKINVARE.md](../../LISENS-MASKINVARE.md).
