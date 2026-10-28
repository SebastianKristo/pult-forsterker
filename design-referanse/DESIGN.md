# Handoff: Pultforsterker v2 – fastvare, OLED-grensesnitt og kabinett

## Overview
Pultforsterker v2 er en liten stereoforsterker. Den har en 2,42" OLED-skjerm, en volumknapp (EC11) med trykk for mute, fire inngangsknapper (AirPlay, Bluetooth, AUX, USB), en egen POWER-knapp foran og en hovedbryter bak. Kabinettet skal 3D-printes og bygger på et eksisterende lokk (`pultforsterker_lid.stl`).

Oppgaven for Claude Code har to deler:
1. **Fastvare** for ESP32-WROVER: lyd (AirPlay + Bluetooth via squeezelite-esp32 eller tilsvarende), knapper, encoder, LED-er og OLED-grensesnittet beskrevet her.
2. **Kabinett** (valgfritt): en parametrisk CAD-versjon (f.eks. OpenSCAD eller CadQuery) av kassen og lokkene med målene nedenfor, slik at hull kan justeres etter de faktiske komponentene.

## About the Design Files
Filene i denne pakken er **designreferanser laget i HTML/three.js**. De er en interaktiv 3D-prototype som viser utseende, mål og oppførsel, og er ikke produksjonskode. Skjermtegningen i `pultforsterker_v2.js` (`draw()`) er laget med Canvas 2D i et 128×64-koordinatsystem. Den skal gjenskapes med **U8g2** (C/C++) på ESP32, ikke kopieres direkte. Tilstandslogikken (`S`, `pDown/pUp`, `holdDown/holdUp`, `btOn/btOff`, `boot`) viser nøyaktig ønsket oppførsel.

Åpne `Pultforsterker v2.html` i nettleseren for å prøve: panelet oppe til venstre simulerer knappene. Siden laster three.js fra unpkg og krever nett.

## Fidelity
**High-fidelity** for oppførsel, skjermlayout og mekaniske mål. Skjermtegningen skal følge layouten piksel for piksel innenfor det U8g2-fontene tillater. Mekaniske mål er satt ut fra databladene, og må kontrolleres mot de innkjøpte delene.

## Maskinvare
- **MCU:** ESP32-WROVER (PSRAM er påkrevd for AirPlay)
- **DAC:** PCM5102A via I2S til et klasse D-forsterkerkort med mute/enable-pinne
- **Skjerm:** 2,42" OLED 128×64, SSD1309, I2C, hvit. Koble RES til en GPIO.
- **Encoder:** EC11 med trykk
- **Inngangsknapper:** 4 × 12 mm metallknapp, momentary, hvit LED-ring (5 V eller 3 V)
- **POWER:** 16 mm metallknapp, momentary, LED-ring med strømsymbol
- **Bak:** KCD1 vippebryter (hovedbryter, bryter all strøm), DC-inngang, USB-C (USB-lyd), 3,5 mm AUX, 4 høyttalerterminaler, SMA-antenne
- AUX og USB krever en analog/USB-lydvelger (f.eks. analog mux eller relé foran forsterkeren, eller USB-lyd via egen DAC). Velg løsning og dokumenter pinnebruk.
- LED-ringene drives fra GPIO via transistor. POWER-LED må støtte PWM (dimming i standby).

## Skjerm: layout (128×64, origo øverst til venstre, tekst vertikalt sentrert på y)
Farger: hvit = piksel på. «Dim» er for en monokrom OLED tenkt som 1-piksels prikkmønster eller tynnere strek. På SSD1309 kan man alternativt bruke `setContrast` for hele skjermen. I prototypen er dim `#7d8a94` og spor `#2a3036`.

### Hovedskjerm (normal drift)
- **Inngangsfelter, rad y 1–10.5:** fire felt «AIR», «BT», «AUX», «USB», fet 6,5 px, 3,5 px polstring, 2,5 px mellomrom, start x=2.
  - Aktiv inngang: fylt hvitt felt med svart tekst.
  - Inaktiv inngang: dim ramme og dim tekst.
  - BT når Bluetooth er av: stiplet ramme (1,2/1,2) og svært svak tekst.
  - BT tilkoblet men ikke aktiv: en prikk på 1,4×1,4 px øverst til høyre i feltet.
- **Tittel:** fet 11 px, x=2, y=21, klippet til y 14–28. Er teksten bredere enn 124 px, ruller den med 14 px/s og 30 px mellomrom mellom gjentakelsene.
- **Undertekst (artist/kilde):** 7 px, dim, x=2, y=31.
- **AirPlay/BT (har metadata):**
  - Play-trekant (2,37.5 → 7,40.5 → 2,43.5), eller to pausestreker på 1,8×6 px ved x 2 og 5.
  - Fremdriftsspor x 11–97, y 40, høyde 1,4. Fylt del i hvitt, med en markør på 2×4 px.
  - Medgått tid «m:ss», 6 px, høyrejustert ved x=126, y=40.8.
- **AUX/USB (ingen metadata):** nivåmeter med 22 søyler, 4 px brede med 5,6 px avstand, fra x=2. Høyde 1–7 px, bunn y=44.
- **Volum:** «VOL», fet 6 px, dim, x=2, y=55.5. 24 segmenter fra x=17 over 84 px. Hvert segment er 1 px smalere enn steget, og høyden er 3 + i·0,25 med bunn y=59. Påslåtte segmenter er hvite, resten i spor-farge. Tallet er fet 12 px, høyrejustert ved x=126, y=54.5.
- **Mute** (erstatter volumraden): høyttalerikon (firkant 4×5 + trapes til x 10), et kryss (13–19, 49.5–55.5), «MUTE» fet 12 px høyrejustert ved x=126, og «vol NN» 6 px dim ved x=26.

### Overlegg (sentrert tekst, x=64)
- **Holder AIRPLAY:** BT-ikon (64,20), «Slå på Bluetooth» eller «Slå av Bluetooth» (fet 9 px, y=38), «Hold AIRPLAY …» (6 px dim, y=47), fremdriftslinje x 24–104, y 54, høyde 2,5.
- **Parring:** BT-ikon (64,19) med tre ringer som pulserer utover (r 6→27, toner ut), «Parring.» / «..» / «...» (fet 10 px, y=41, punktene skifter hvert 0,5 s), «Synlig som «Pultforsterker»» (6,5 px dim, y=52), «Hold AIRPLAY for å avbryte» (5,5 px dim, y=60).
- **Tilkoblet (2,2 s):** BT-ikon og hake, «Tilkoblet» (fet 10 px, y=37), enhetsnavn (7 px dim, y=48).
- **Bluetooth av (2,2 s):** dimt BT-ikon med strek over, «Bluetooth av», «Hold AIRPLAY for å slå på».
- **BT trykket mens Bluetooth er av (2,2 s):** «Bluetooth er av» og «Hold AIRPLAY i 2 s for å slå på».
- **Holder POWER:** ring r=11 rundt (64,22) som fylles med klokka fra toppen, en omstartpil i midten, «Hold for omstart» (fet 9 px, y=44), «Slipp for å avbryte» (6 px dim, y=54).
- **Omstart (0–1,2 s):** «Starter på nytt …» (fet 10 px, y=30), «Lagrer innstillinger» (6 px dim, y=42). Deretter oppstartsskjermen.
- **Oppstart (1,6 s):** strømikon (64,20, r=7), «PULTFORSTERKER» (fet 9 px, 1,5 px sperring, y=40), fremdriftslinje x 34–94, y 50, høyde 2, statustekst (5,5 px dim, y=58): «Starter AirPlay» under 50 %, «Starter Bluetooth» under 90 %, deretter «Klar».
- **Standby / hovedbryter av:** skjermen er helt svart (`setPowerSave(1)`).

## Interactions & Behavior
- **Inngangsknapp (kort trykk):** velger inngangen og lukker eventuelle overlegg. LED-ringen på aktiv inngang lyser.
- **BT-knappen:** Er Bluetooth av, vises overlegget «Bluetooth er av», og inngangen endres ikke. Under parring ignoreres trykket.
- **AIRPLAY kort trykk (under ca. 0,3 s):** velger AirPlay.
- **AIRPLAY holdt:** etter 0,3 s vises hold-overlegget med fremdrift over 2 s.
  - Ved 2 s veksler Bluetooth: av → parring (synlig, LED-en på BT pulserer med ca. 1,1 Hz sinus). Ved tilkobling vises «Tilkoblet», inngangen bytter til BT, og etter 2,2 s vises hovedskjermen. På → av: vis «Bluetooth av». Var BT aktiv inngang, byttes det til AirPlay.
  - Slipper man etter at overlegget er vist, men før 2 s, avbrytes handlingen uten endring.
- **POWER kort trykk (slipp før hold-overlegget vises, ca. 0,5 s):** veksler mellom på og standby.
  - Standby: skjermen av, forsterkeren mutet/disabled, LED-er av, POWER-LED dimmet til ca. 10 % PWM.
  - Ut av standby: oppstartsskjermen.
- **POWER holdt:** etter 0,5 s vises ringen, som fylles over 3 s. Ved 3 s: omstart (lagre innstillinger, `esp_restart()`), deretter oppstartsskjermen. Slipper man før 3 s, avbrytes alt uten endring, også uten av/på.
- **Encoder:** vri for volum 0–100 (1 per detent, gjerne akselerert ved rask vridning). Trykk veksler mute. Volumendring mens mute er på skal oppheve mute. Dette er ikke vist i prototypen, men anbefales.
- **Hovedbryter bak:** fysisk strømbrudd.
- **Vedvarende lagring (NVS):** volum, siste inngang, BT på/av og mute.
- **Oppdateringsfrekvens:** 10 Hz på hovedskjermen, 30 Hz for hold-animasjoner.

## State Management
```
power        bool    (hovedbryter, kun maskinvare)
standby      bool
input        0=AirPlay 1=BT 2=AUX 3=USB
vol          0..100
muted        bool
playing      bool    (fra AirPlay/BT-metadata)
bt           'off' | 'pairing' | 'connected'
btDevice     string
track        {title, artist, durationS, positionS}   // AirPlay/BT
overlay      none | holdAirplay(progress) | pairing | connected | btOff | btNeeded | holdPower(progress) | restart | boot(progress)
```
Metadata kommer fra AirPlay (DMAP) og fra Bluetooth (AVRCP). Mangler det metadata, vises inngangsnavnet som tittel og kilden som undertekst: «Analog inngang» / «3,5 mm jack» og «USB-lyd» / «PC · 48 kHz».

## Kabinett – mål (mm, x høyre, y bakover, z opp; lokkets topp z=3)
- **Lokk (fra originalen):**
  - Plate 200 × 120, hjørneradius 6, 3 tykk, med avrundet toppkant (bevel 0,6).
  - Kant under: ytre 194,6 × 114,6 (r 3,3), indre 189,8 × 109,8, høyde 1,6, åpning på x ±15 bak.
  - Kabelutsparing på undersiden: x ±15, y 47–60, dybde 0,7.
  - 4 skruehull Ø3,4 ved (±90, ±50) med forsenkning Ø6,4.
  - Pultfeste-variant: 4 ører 19 × 22 (r 3) sentrert i (±108,5, ±40) med spor 10 × 4,6 sentrert i (±110, ±40).
- **Kasse:**
  - Høyde 48 under lokket, vegg 2,7, bunn 2,5.
  - Skruetårn Ø8 med hull Ø2,6 ved (±90, ±50), med ribber mot veggene.
  - Gummiføtter Ø14 ved (±85, ±45) i frittstående variant.
- **Front:**
  - Vegg 2,7 pluss påsatt frontplate 188 × 46 (r 3, 2 tykk, bevel 0,6), sentrert i z=−24.
  - OLED-vindu 57 × 30 i veggen. Forsenkning for akrylvindu 70 × 38 (r 2) i frontplaten.
  - Skjermsenter x=−30.
  - Inngangsknapper Ø12,2 i 2×2: x 20 og 37, z −24 ± 8,5. Øverst AIRPLAY og BT, nederst AUX og USB.
  - POWER Ø16,2 ved x=−80.
  - Encoder Ø7,5 ved x=70.
  - Etiketter under knappene: AIRPLAY, BT, AUX, USB, POWER og «VOL · PUSH MUTE».
- **Bak (z=−24):**
  - Vippebryter 19,2 × 12,8 ved x=76
  - DC Ø11,2 ved x=54
  - USB-C 9,4 × 3,6 ved x=36
  - AUX Ø6,2 ved x=20
  - SMA Ø6,6 ved x=−4
  - Høyttalerterminaler Ø5,2 ved x −30, −45 (R) og −65, −80 (L)
- **Materialer:** PLA Matte i antrasitt (`#2c2d30`), røykfarget akryl i vinduet, svart oksiderte metallknapper og en kjøpt volumknapp i aluminium (ca. 38 mm, 6 mm D-aksel).

## Design Tokens
- Kabinett: `#2c2d30` (skall), `#37383c` (frontplate), `#18181a` (knapp)
- Etiketter: `#a3a29d`, Helvetica Neue 500, store bokstaver, sperring på ca. 14 % av høyden
- OLED: hvit `#eef6ff`, dim `#7d8a94`, spor `#2a3036`, bakgrunn `#000`

## Assets
Ingen bildefiler. Strømsymbolet og BT-ikonet tegnes med vektorer (se `draw()` og `symC` i JS-filen). Lag dem som XBM-bitmaps til U8g2.

## Files
- `Pultforsterker v2.html`: prototypeside med kontrollpanel
- `pultforsterker_v2.js`: 3D-modell, skjermtegning (`draw()`), tilstandsmaskin og STL-eksport (lokk, kasse, vindu)
- `three-d-stage.js`: visningskomponent for 3D
- `PROJECT_NOTES.md`: prosjektnotater (komponenter, AliExpress-søk, materialer, utskrift)
- `pultforsterker_lid.stl`: originalt lokk (referanse for mål)
