# Handoff: Skjold S1 – streamingforsterker (Pultforsterker v2 rev C)

## Oversikt
Skjold S1 er en kompakt stereo-streamingforsterker for skrivebordet. Den bygges på et eget hovedkort (PCBWay) med Raspberry Pi Zero 2 W (Lyrion/Squeezelite), klasse-D-forsterker 2 × 50 W og USB-hub/-switch.

Pakken inneholder:
- en interaktiv 3D-prototype av hele produktet: kabinett, frontpanel, komponenter og skjerm-UI
- ferdige produksjonsfiler: STEP/DXF for platemetall og CNC, og 3MF/STL for den printede frontplaten
- generatorskriptene som lager filene ut fra én felles fil med geometri

## Om designfilene
`Pultforsterker v2 revB metall.html` med `pultforsterker_revb_metall.js` er **designreferanser laget i HTML/three.js**. De viser tiltenkt utseende og oppførsel, ikke produksjonskode.

Oppgavene er:
1. **Fastvare/UI:** gjenskape skjerm-UI og knappelogikk på målplattformen. Anbefalt: Python-tjeneste på Pi-en som tegner til SSD1309 (luma.oled) eller ILI9341, leser GPIO og snakker med Lyrion via JSON-RPC/CLI.
2. **Mekanikk:** bruke CAD-filene direkte. De er produksjonsklare, men bør åpnes og kontrolleres i Fusion eller FreeCAD før bestilling.
3. **Endringer i geometri:** gjøres i `revb_features.js`. Kjør deretter generatorene i `cad/` på nytt (se under). Rediger aldri STEP-filene for hånd.

## Fidelity
**High-fidelity.** Mål, farger, typografi, LED-oppførsel og skjermlayout er endelige. Volumvisning, navn på radiofavoritter og eksempelspor er plassholdere.

---

## Mekanikk

### Hovedmål (`revb_features.js` → `REVB`)
- **Kasse:** 190 × 160 × 48 mm (B × D × H). Origo er i senter av bunnen, z opp, fronten er −y.
- **Form:** avrundet med R9 på kantene langs dybden, både oppe og nede. Sidene er rette fra z 9 til 39.
- **Platemetall (valgt):** aluminium 5052-H32, 1,5 mm. Omslaget (topp og sider i ett) bøyes med innvendig radius R7,5. Panelene bøyes med R1,5. K-faktor 0,44.
- **Overflate:** glassperleblåst og sort eloksert («Bead blast + Anodized color, Black» hos JLC).
- **Frontplate:** printet PETG Matte Light Khaki med sort tekst lagt inn, 4 mm tykk, festet med skjulte skruer innenfra.

### Hull i fronten
Koordinater (x, z) i mm, hele kassen:

| Del | Posisjon | Hull |
|---|---|---|
| Skjermhull (felles for OLED og TFT) | (−27, 24) | 62 × 39, R2 |
| Power, 16 mm knapp | (−76, 24) | Ø16,4 |
| Hodetelefon PJ-392 (nikkel) | (−76, 8) | Ø6,2 i metallet. I frontplaten: Ø6,4 foran og en forsenkning bak på Ø10,4 × 2,4 for mutteren |
| AirPlay·BT, 12 mm | (22, 32,5) | Ø12,4 |
| AUX, 12 mm | (38, 32,5) | Ø12,4 |
| RADIO, 12 mm | (22, 15,5) | Ø12,4 |
| USB, 12 mm | (38, 15,5) | Ø12,4 |
| Volum EC11, knapp 30 × 17, D-aksel | (66, 24) | Ø7,4 |
| Frontplateskruer M3 innenfra | (±83, 7 / 41) og (12, 8,5 / 39,5) | Ø3,4 i metallet. Ø4 × 3,2 gjengeinnsatser i frontplaten |

### Bakpanel
Koordinater (x, z):
- **Høyttalerpoler:** L+ −84, L− −70, R+ −54, R− −40 (Ø6,4, z 24)
- **SMA til BT/Wi-Fi-antenne:** −26 (Ø6,4)
- **AUX inn 3,5 mm:** −14 (Ø6,4)
- **USB-C ×3 stablet ved x 6, z 34/24/14:** PC 1, PC 2 og service. Hvert hull er 9,6 × 3,8, med skruehull Ø2,7 ved x −3,5 og 15,5.
- **RJ45:** (34, 13,5), 17 × 15,6, med to avlange festehull ved x 21 og 47
- **DC 19–24 V:** (34, 34), Ø11,4
- **Jordpunkt M3:** (52, 40), Ø3,4. Stjernejord: kassen kobles til signaljord bare her.
- **Vippebryter:** (70, 24), 19,4 × 13

### Sider og bunn
- **Venstre side:** 4 × USB-A, 14,8 × 8 ved y −32,1 / −14,6 / 2,9 / 20,4, z 32,6. Portene sitter på hovedkortet.
- **Høyre side:** 26 luftespalter, 2,4 × 24, z 26,5, y fra −43,8 med 3,6 mm mellomrom.
- **Bunn:** luftespalter 2,4 × 40 ved y −14, x fra −55 til 55 med 5 mm mellomrom, med åpning under termoblokken. 2 × Ø3,4 for termoblokken ved (24, −5) og (36, −5).
- **Hovedkort:** 180 × 100 × 1,6 mm, M3-hull med senteravstand 172 × 92 ved (−88,3 / 83,7, −44,3 / 47,7). Kortet ligger med topp på z 27,5.
- **Termoblokk:** aluminium 24 × 24 mm med termoputer, mellom forsterkerbrikken og bunnplaten.

### Printet frontplate (K2 + CFS)
- Mål 186 × 44 × 4 mm, R7-hjørner. Printes med forsiden ned.
- **Lag fra baksiden:** bak 1,0 mm, hulrom for akryl 2,2 mm, leppe foran 0,8 mm.
- **Akryl:** røyksort 2 mm, 72 × 40 mm. Printes inn med pause ved Z 3,2 mm.
- **Sort innlegg (0,4 mm):** tekst (Helvetica Bold), en ramme på 2 mm rundt skjermvinduet og hodetelefon-ikonet.

### Montering (platemetall, avrundet)
Se `platemetall/skjold_s1_avrundet/LES_MEG.md`. Kort fortalt:
- **Deler:** omslag med 12 mm flens nederst, front- og bakpanel med 10 mm flens, bunnplate og 2 innvendige vinkelskinner.
- **Skruer:** alle skruene sitter på undersiden.
- **Gjengedeler:** PEM CLS-M3-1 og FHS-M3-8.

---

## Skjerm-UI (OLED 2,42″ 128×64 SSD1309 I2C hvit, eller TFT 2,4″ 320×240 ILI9341 + XPT2046)
TFT-versjonen er OLED-layouten skalert ×2,5 og sentrert, i tillegg til en egen visning for avspilling. Se `drawOLED()`, `drawTFT()` og `overlay()` i JS-filen.

**Oppstartsbilde (2,6 s):**
- Skjold-merket, fem strekker som kommer til syne én etter én.
- Deretter «SKJOLD» (Sora 600) og «STREAMING AMPLIFIER» (IBM Plex Mono).
- Utgangen er dempet mens den starter. Volumet går fra 0 til lagret nivå over 1,2 s (myk start).

**Hovedskjerm (OLED):**
- **Fanelinje:** AIR/BT, AUX, RADIO, USB i bold 7 px. Aktiv fane har lys bakgrunn #f2f2ee og sort tekst. Øvrige er grå #8b8b86.
- **Tittel:** bold 12 px.
- **Undertittel:** 7 px grå.
- **Volum:** «VOL» og 24 segmenter (bredde 2,6 px, steg 3,6 px), med tall til høyre.
- **Indikator:** «HP» oppe til høyre når hodetelefoner er plugget inn.

**Overlegg:**
- **BT-paring:** «BLUETOOTH», animerte ringer og et BT-ikon, teksten «Paring…» og «Synlig som «Skjold S1»», og en fremdriftsstripe over 6 s. Deretter vises «Tilkoblet · Sebastians iPhone» i 2,2 s.
- **Radiomeny (2,6 s etter trykk):**
  - Overskrift «RADIO · FAVORITTER» og «n/6».
  - 3 rader. Raden i midten er markert og viser valgt favoritt.
  - Favoritter: NRK P1, NRK P2, NRK P3, P4 Norge, Radio Norge, NRK Klassisk.
- **Omstart:** en spinner med 12 streker og «Starter på nytt · Raspberry Pi · Lyrion» i 3,2 s, deretter oppstartsbildet.

## Knapper og oppførsel
| Knapp | Trykk | Hold (1,2 s) |
|---|---|---|
| AirPlay · BT | Velg trådløst. Trykk igjen veksler mellom AirPlay og BT, hvis BT er paret. Avbryter paring. | Start BT-paring: overlegg vises og LED-ringen blinker hvert 350. ms |
| AUX | Velg AUX-inngangen bak | – |
| RADIO | Første trykk velger radio. Neste trykk går til neste favoritt (6, rundt). Menyen vises. | – |
| USB | USB-lyd fra PC 1/2 via USB-C bak | – |
| Power (16 mm) | På/standby, starter oppstartsbildet | Omstart av Pi: spinner, og LED-en pulserer |
| Volum (EC11) | Trykk: mute | Vri: ±2 per steg |
| Vippebryter bak | Hovedstrøm | – |

**LED-ringer:** hvite, 12–24 V-varianter.
- Aktiv inngang lyser.
- Power-ringen og power-symbolet lyser når den er på. I standby er de dempet til ca. 25 %.

## Tilstand
```
power, main, input(0..3), wl('air'|'bt'), btPaired, pairT, preset(0..5), menuT, toastT,
rebootT, vol(0..100), muted, hp(plugget inn), boot-tidspunkt
```

## Designtokens
- **Kasse (sort, perleblåst og eloksert):** #1a1a1c. I prototypen er roughness 0,5 og metalness 0,7.
- **Frontplate (PETG khaki):** #cbbd9e. Tekst og ramme i sort innlegg: #161617.
- **Gravert tekst på metall:** #d2d4d7 på mørk kasse, #3a3b3e på lys.
- **Skjerm:** hvit #f2f2ee, grå #8b8b86, aksent på TFT #d9a441.
- **Fonter:**
  - Logo: Sora 600 og IBM Plex Mono 400.
  - Skjerm: Helvetica Neue / Arial bold.
  - Frontplate: Helvetica Bold.
- **Logo:** `logo/skjold_logo.svg` og `logo/skjold_merke.svg`. Merket er fem avrundede streker med høyde 22/33/42/33/22 og bredde 4,6.

## Innkjøpsliste (viktigste deler)
- **Knapper:** 4 × 12 mm metallknapp, sortoksidert, hvit LED-ring, 12–24 V.
- **Power:** 1 × 16 mm, sort hus, hvit LED-ring og power-symbol.
- **Volum:** EC11-enkoder med 20 mm D-aksel og aluknapp 30 × 17 mm.
- **Skjerm:** SSD1309 2,42″ I2C hvit eller ILI9341 2,4″, og røyksort akryl 2 mm.
- **Hodetelefon:** PJ-392 i nikkel.
- **Bakpanel:** 4 × 4 mm høyttalerpoler, SMA, 3,5 mm AUX, 3 × USB-C panelkontakt, RJ45 panelkontakt, DC-kontakt 5,5/2,5 og vippebryter.
- **Feste:** PEM CLS-M3-1 og FHS-M3-8, M3-skruer og avstandsstykker, 4 × M3 gjengeinnsatser Ø4 for frontplaten og selvklebende gummiføtter Ø12,7 × 3,5.

## Filer
| Sti | Innhold |
|---|---|
| `Pultforsterker v2 revB metall.html` + `pultforsterker_revb_metall.js` | Interaktiv 3D-prototype. Må serveres over http, for eksempel med `npx serve`. |
| `revb_features.js` | **Én felles kilde** for all geometri: hull, skruer, plate og braketter |
| `cad/generate.js` | CNC- og rettkantet platemetall, STEP for frontplate og lokk, DXF |
| `cad/generate_sheet_round.js` | Avrundet platemetall: STEP-sammenstilling og DXF-flatmønstre (bruker hjelpefunksjoner fra generate.js) |
| `cad/generate_print.js` | 3MF og STL for frontplaten (manifold-3d, three FontLoader, fflate) |
| `platemetall/skjold_s1_avrundet/` | **Bestillingsfiler** for valgt utgave, med LES_MEG.md |
| `print/skjold_s1_frontplate_*.3mf` | Frontplate til K2/CFS, med LES_MEG_frontplate.md |
| `cnc/` | Alternativ CNC-utgave |
| `logo/` | SVG-logoer |
| `Pultforsterker Logo.dc.html` | Logoskisser. Valgt logo er 2c. |
| `uploads/v2_*.stl` | Opprinnelig printet kasse (rev B, 215 mm), kun til referanse |

### Kjøre generatorene på nytt
Skriptene er funksjonskropper som får `REVB`, `saveFile` og `log` som argumenter. I Node:
1. Les `revb_features.js` og ta ut `REVB`.
2. Kjør `new Function('REVB','saveFile','log', src)(REVB, (p,d)=>fs.writeFileSync(p,d), console.log)`.
3. For `generate_sheet_round.js`: hent hjelpefunksjonene `StepDoc`, `fpoly`, `rrect`, `rev`, `circ`, `hole`, `fr`, `FZ`/`FF`/`FB`/`FL`/`FRt`/`FY` og `DXF` fra `generate.js` og send dem inn som `LIB`.

Utskriften fra STEP-generatorene skal vise `bad 0`, som betyr at topologien er tett.
