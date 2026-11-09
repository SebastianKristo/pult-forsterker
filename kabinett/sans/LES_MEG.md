# Skjold Sans – multisensor for vegg

Bevegelse, temperatur, fuktighet og lys i et lite kabinett på 56 × 80 × 26 mm, laget for å tåle bad. Det passer
delene fra en vanlig D1 mini-multisensor: Wemos D1 mini, AM312 PIR, en temperatur- og fuktsensor (DHT11 eller
bedre) og et lite lyskort.

![Montert](render/montert.png)

## Hva er bedre enn i en vanlig multisensor

- **Eget sensorkammer.** Temperatur- og fuktsensoren sitter nede til venstre, skilt fra ESP-en med dobbel vegg og
  luftspalte. Kammeret har egne lameller i siden og spalter i bunnen. ESP8266 varmer kabinettet 1–3 °C, så en
  sensor ved siden av den måler for høyt og for tørt.
- **Pipeeffekt.** ESP-en sitter i et eget rom med luft inn nede (ved kabelen) og ut gjennom lameller oppe til høyre.
  Varmen stiger bort fra sensoren.
- **Sprutsikre lameller.** Alle lamellene heller 45° nedover utover, så vann ikke treffer rett inn. Det er ingen
  åpninger på toppen.
- **Ingen synlige skruer.** Bakplata skrus i veggen. Kroppen klikkes på (to rygger) og trekkes rett ut for service.
- **Alt printes uten støtte.** Kroppen printes med forsiden ned (fin, glatt front) og bakplata med baksiden ned.
- **Lite gullskjold** i forsiden, som på resten av Skjold-familien. Det printes i samme jobb som kroppen.

![Eksplodert](render/eksplodert.png)

## Deler

| Del | Antall | Merknad |
|---|---|---|
| Wemos D1 mini (ESP8266) | 1 | ESP-modulen vender mot bakplata, USB-kontakten ned |
| AM312 mini-PIR | 1 | kuppel ca. Ø12, trykkes inn i røret bak hullet (tre ribber holder den, en dråpe lim om den er løs) |
| **SHT40**-modul (anbefalt), eller SHT31 / BME280 / DHT22 / DHT11 | 1 | står i sporet i sensorkammeret med sensoren mot lamellene |
| BH1750 (GY-302) eller TEMT6000 | 1 | i rammen bak lysvinduet. Rammen er 11,5 × 18,5 mm: **mål ditt kort** og endre `lysB`/`lysL` |
| Micro-USB-kabel + 5 V-lader | 1 | kabelen går rett ned gjennom sporet i bunnen |
| Senkeskrue Ø3–3,5 × 25 + plugg | 2 | bakplata i veggen (eller dobbeltsidig monteringstape) |

**På bad: bytt ut DHT11.** Den måler bare 20–80 %RH (±5 %) og henger seg opp etter dusjing. SHT40 måler 0–100 %RH
(±1,8 %), tåler kondens og koster omtrent det samme.

## Utskrift (Creality K2)

`skjold-sans-k2.3mf` har kropp og bakplate på én plate. Innstillingene ligger i fila (ingen støtte, sakte første
lag).

- **Kropp:** lys PETG/ASA, forsiden ned. Skjoldet er filament 3 (gull), så det blir ett filamentbytte i de første
  lagene.
- **Bakplate:** lys PETG/ASA, baksiden ned.
- Bruk **PETG eller ASA på bad**, ikke PLA. PLA blir myk av varm, fuktig luft over tid.
- Ca. 16 g + 9 g.

## Montering

1. Lodd ledninger på sensorene og D1 mini (se kobling under). Hold dem korte.
2. Sett D1 mini i holderen på bakplata: ESP-modulen ned mot plata, kortet mellom de fire hjørnestøttene og
   stoppene over og under.
3. Sett sensorkortet i sporet i kammeret, med sensoren mot venstre (mot lamellene). Ledningene går gjennom
   åpningen øverst ved bakkanten av skilleveggen.
4. Trykk PIR-en inn i røret bak hullet, og lyskortet inn i rammen bak lysvinduet (i kroppen).
5. Skru bakplata i veggen. Sett USB-kabelen i D1 mini.
6. Før kabelen inn i sporet i bunnen og klikk kroppen på.

**Plassering på bad:** utenfor sone 1 og 2 (ikke over badekar eller i dusjen), helst høyt på veggen ved døra, der
PIR-en ser hele rommet. Laderen skal sitte i en vanlig stikkontakt utenfor våtsonen.

![Innsiden av kroppen](render/bakfra_inni.png) ![Bakplata med D1 mini og sensorkort](render/bakplate.png)

## Kobling og fastvare

ESPHome-oppsettet ligger i [`esphome/skjold-sans.yaml`](../../esphome/skjold-sans.yaml) (SHT40 + BH1750 + AM312,
med DHT og TEMT6000 som kommenterte alternativer).

| D1 mini | Til |
|---|---|
| 3V3 | VCC på alle sensorene |
| G | GND på alle sensorene |
| D5 (GPIO14) | AM312 OUT |
| D2 (GPIO4) | SDA (SHT40, BH1750) |
| D1 (GPIO5) | SCL (SHT40, BH1750) |
| D6 (GPIO12) | DHT DATA (om du bruker DHT) |
| A0 | TEMT6000 SIG (om du bruker den) |

Ekstra for bad:
- **Dusj pågår:** slår seg på når fuktigheten er 8 %-poeng over snittet den siste timen, og holder 5 min etterpå.
  Fin til å styre avtrekksvifta.
- **Fuktstigning:** %-poeng per minutt. Gjør at vifta kan starte før speilet dugger.
- **Duggpunkt** og **absolutt fuktighet.**

Juster `temp_offset` mot et kjent termometer etter en times drift.

## Bygg selv

```bash
python3 lag_sans.py
```

Kommandoen eksporterer STL-ene, sjekker at delene er tette og ikke kolliderer (kjøpte deler er med), at det ikke er
overheng som trenger støtte, og skriver 3MF-fila. Målene står øverst i `skjold_sans.scad`.
