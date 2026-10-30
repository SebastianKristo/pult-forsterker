# Kabinett i platemetall («Skjold S1»-designet) – slik det brukes i Pultforsterker

Designpakken i denne mappen (fra designhandoff 30.10.2026) er **gjeldende kabinett** for hovedkortet rev B: kasse i
sort eloksert aluminium fra PCBWay (sheet metal) og en 3D-printet frontplate med navnet i. Den printede kassen i
`kabinett/stl/v2_*_revb*.stl` er dermed bare referanse.

Designpakkens egen `README.md` beskriver *designet* (farger, skjerm-UI, knappelogikk). Der den sier noe annet enn
resten av repoet, gjelder repoet – de tidligere valgene står:

| Designpakken sier | Gjelder i Pultforsterker |
|---|---|
| Printet frontplate (PETG khaki, sort innlegg) | **Aluminium 3 mm**, sort eloksert med lasergravert tekst, som kassen (`skjold_s1_frontplate_alu*.dxf`) |
| Raspberry Pi Zero 2 W | **Pi 4** under hovedkortet (H5–H8, 20 mm avstandsstykker) |
| Termoblokk fra forsterkerbrikken ned til bunnplaten | TPA3116D2**DAD** har kjøleflaten på **toppen**: kjøleribbe 20 × 20 limes på. Hullene for termoblokken er fjernet, luftespaltene i bunnen går helt gjennom |
| SMA-antenne + én AUX bak | **To AUX** (J4/J20 på kortet): hullene på −26 og −14 bak er AUX 2 og AUX 1 (begge Ø6,4) |
| «Service»-USB-C bak | USB-C-forlenger fra en av Pi-ens USB-porter (samme kontakt som i den printede kassen) |
| Knapper AIRPLAY·BT / AUX / RADIO / USB | **BT** (AirPlay + Bluetooth) og **RADIO** oppe, **AUX** og **USB** nede – daemonen er lagt om slik (J7 knapp 1 = BT, knapp 2 = RADIO) |
| Skjerm-UI og knappelogikk i `pultforsterker_revb_metall.js` | Pi-programvaren i `pi/` (daemon, `oled_display.py`, `tft_screen.py`) |

Endringene er gjort i `revb_features.js` og `cad/generate_print.js`, og alle filer er generert på nytt.

## Hva som bestilles

Alt som bestilles hos PCBWay (kasse, frontplate, gravering) ligger i `platemetall/skjold_s1_avrundet/`.

### Kasse – PCBWay «Sheet Metal Fabrication»
Filer: `platemetall/skjold_s1_avrundet/` (STEP av hele kassen + DXF-flatmønstre per del, se `LES_MEG.md` der).
- Materiale: aluminium 5052-H32, 1,5 mm. Bøyeradius: omslaget innvendig R7,5, panelene R1,5 (skriv det i kommentarfeltet).
- Overflate: **bead blast + anodized, black**.
- PEM-innsatser: CLS-M3-1 ×10, FHS-M3-8 ×4 (listet i `LES_MEG.md`).
- Velg `..._avrundet.step` for OLED eller `..._avrundet_tft.step` for 2,8" TFT (bare skjermhullet i fronten er forskjellig).
- USB-A-vinduene i venstre vegg, RJ45/DC bak og hodetelefonhullet (Ø6,2 ved (−76, 8)) er med.
- **Lasermerking på kassen** (designpakkens filer i `marking/`, lag MARKING, én DXF per flate, tegnet på den ferdige flaten):
  `skjold_s1_merking_bunnplate.dxf` (logo, Skjold S1, designer, 19–24 V DC 3 A, serienr. – sett fra undersiden),
  `skjold_s1_merking_bakpanel_revb.dxf` (bakpanelet med AUX 1/AUX 2 i stedet for designets BT/AUX; originalen ligger ved siden av),
  `skjold_s1_merking_venstre_side.dxf` (USB 1–4). Se `marking/LES_MEG.md`. Serienummeret SKJ-S1-0001 er en plassholder.

### Frontplate – PCBWay Sheet Metal, aluminium (valgt)
Filer i `platemetall/skjold_s1_avrundet/`:
- `skjold_s1_frontplate_alu.dxf` (OLED) / `skjold_s1_frontplate_alu_tft.dxf` – kuttefil, lag CUT. Flat plate 178 × 46 mm, R3, **3 mm 5052-H32**.
  Vindu 62 × 38 for skjermen, Ø16,4 POWER, 4 × Ø12,4 knapper, Ø7,4 encoder, Ø6,4 hodetelefonjack, 6 × Ø3,0 for studs.
- `skjold_s1_frontplate_alu_merking.dxf` – lag MARKING: BT, RADIO, AUX, USB (små, 1,8 mm), ramme rundt vinduet, hodetelefon-ikon og SKJOLD-logoen under volumknotten (ingen tekst
  ved POWER, intet navn på fronten). Sett forfra; lag OUTLINE/HOLES til plassering. Lastes opp under «Surface Treatment → laser
  marking». Forhåndsvisning: `skjold_s1_frontplate_alu.png`.
- Overflate: **bead blast + anodized, black** – samme som kassen.
- Innpressede deler: **6 × FH-M3-8 selvklinkende studs** fra baksiden (hull Ø3,0). De går gjennom Ø3,4-hullene i frontpanelet og
  festes med M3-mutter innenfra – ingen synlige skruer. Studsene og hodetelefonjacken sitter i platen; frontpanelet har Ø10,6 ved
  jacken så mutteren får plass bak platen.
- Akryl: røyksort 2 mm, skjæres til 61,6 × 37,6 (R1,3) og limes inn i vinduet fra baksiden, 1 mm forsenket (`print/pultforsterker_v2_revb_akryl_skjermglass_*_2mm.dxf` kan brukes som utgangspunkt, trekk fra 0,2 mm).
- Generer på nytt: `python3 tools/frontplate_metall.py` (tekst/posisjoner øverst i filen).

Alternativ (ikke valgt): printet frontplate med to farger, `print/skjold_s1_frontplate_*.3mf`, se `print/LES_MEG_frontplate.md`.

### Montering mot hovedkortet
Kortet 180 × 100 ligger med oversiden på z 27,5 (25 mm M3-avstandsstykker på bunnplaten/skinnene), USB-A-portene ut
gjennom venstre vegg. Pi 4 under kortet. Frontkontakter (J7, J8, J9/J13, J10, J23) og bakkontakter (J1–J4, J11, J12,
J19–J21) som i `pcb/README.md` og TOTALINSTRUKS §9.

## Render av produktet
`render/pultforsterker_*.png` er 3D-renderinger (three.js i headless Chromium) av hele produktet med alle mål fra `revb_features.js`
og merkingen rett fra DXF-filene: `front34`/`back34` (skrått forfra/bakfra), `front`/`back`/`left`/`bottom` (ortografisk).
Lag på nytt: `python3 tools/render_textures.py && python3 tools/render3d.py`.

## Generere filene på nytt
```bash
cd kabinett/skjold-s1/tools && npm install
node run.mjs .. all          # cnc + platemetall + print (eller: sheet | cnc | print)
python3 frontplate_metall.py # frontplate i aluminium: kutt + merking
python3 merking_bakpanel.py  # bakpanel-merking tilpasset AUX 1/AUX 2
```
Geometri endres bare i `revb_features.js`, tekst på frontplaten i `cad/generate_print.js`. STEP-generatorene skal melde `bad 0`.
