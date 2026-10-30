# Kabinett i platemetall («Skjold S1»-designet) – slik det brukes i Pultforsterker

Designpakken i denne mappen (fra designhandoff 30.10.2026) er **gjeldende kabinett** for hovedkortet rev B: kasse i
sort eloksert aluminium fra PCBWay (sheet metal) og en 3D-printet frontplate med navnet i. Den printede kassen i
`kabinett/stl/v2_*_revb*.stl` er dermed bare referanse.

Designpakkens egen `README.md` beskriver *designet* (farger, skjerm-UI, knappelogikk). Der den sier noe annet enn
resten av repoet, gjelder repoet – de tidligere valgene står:

| Designpakken sier | Gjelder i Pultforsterker |
|---|---|
| Raspberry Pi Zero 2 W | **Pi 4** under hovedkortet (H5–H8, 20 mm avstandsstykker) |
| Termoblokk fra forsterkerbrikken ned til bunnplaten | TPA3116D2**DAD** har kjøleflaten på **toppen**: kjøleribbe 20 × 20 limes på. Hullene for termoblokken er fjernet, luftespaltene i bunnen går helt gjennom |
| SMA-antenne + én AUX bak | **To AUX** (J4/J20 på kortet): hullene på −26 og −14 bak er AUX 2 og AUX 1 (begge Ø6,4) |
| «Service»-USB-C bak | USB-C-forlenger fra en av Pi-ens USB-porter (samme kontakt som i den printede kassen) |
| Knapper AIRPLAY·BT / AUX / RADIO / USB | **AIRPLAY / BT / AUX / USB** som på kortet (J7). Radio velges med knappen for aktiv kilde + encoder/meny, HA eller Homey |
| Skjerm-UI og knappelogikk i `pultforsterker_revb_metall.js` | Pi-programvaren i `pi/` (daemon, `oled_display.py`, `tft_screen.py`) |

Endringene er gjort i `revb_features.js` og `cad/generate_print.js`, og alle filer er generert på nytt.

## Hva som bestilles

### Kasse – PCBWay «Sheet Metal Fabrication»
Filer: `platemetall/skjold_s1_avrundet/` (STEP av hele kassen + DXF-flatmønstre per del, se `LES_MEG.md` der).
- Materiale: aluminium 5052-H32, 1,5 mm. Bøyeradius: omslaget innvendig R7,5, panelene R1,5 (skriv det i kommentarfeltet).
- Overflate: **bead blast + anodized, black**.
- PEM-innsatser: CLS-M3-1 ×10, FHS-M3-8 ×4 (listet i `LES_MEG.md`).
- Velg `..._avrundet.step` for OLED eller `..._avrundet_tft.step` for 2,8" TFT (bare skjermhullet i fronten er forskjellig).
- USB-A-vinduene i venstre vegg, RJ45/DC bak og hodetelefonhullet (Ø6,2 ved (−76, 8)) er med.
- **Lasergravering under kassen:** `platemetall/skjold_s1_avrundet/skjold_s1_bunn_gravering.dxf` lastes opp som egen fil
  under «Surface Treatment → Laser engraving/marking» for bunnplaten. Lag `ENGRAVE` graveres (logo, SKJOLD · STREAMING
  AMPLIFIER, Skjold S1, «Designet av Sebastian Kristo Jemtland i Norge», 19–24 V ⎓ 3 A · Modell S1 · serienummer); lag `REF`
  er bunnplatens omriss og hull bare til plassering. Tegningen er sett fra undersiden (utsiden) av bunnplaten med fronten
  nederst, så teksten leses rett når kassen snus. Forhåndsvisning: `skjold_s1_bunn_gravering.png`. Nytt serienummer:
  `python3 tools/gravering.py SKJ-S1-0002`.

### Frontplate – PCBWay 3D-print (eller egen printer)
- **PCBWay (ett materiale):** `print/skjold_s1_frontplate_oled_khaki.stl` (eller `_tft_khaki.stl`). Teksten
  *PULTFORSTERKER*, AIRPLAY, BT, AUX, USB, POWER, ramme og hodetelefon-ikon ligger 0,4 mm **forsenket** i forsiden, så de
  er med i printet. Bestill MJF (PA12, farget) eller SLA og be om «paint fill» i forsenkningene hvis du vil ha dem mørke;
  STEP-utgaven uten tekst er `print/pultforsterker_v2_revb_frontplate_*_skjult_feste.step`.
- **Egen printer med to farger:** `print/skjold_s1_frontplate_oled.3mf` (plate + sort innlegg), se `print/LES_MEG_frontplate.md`.
- Akryl 2 mm røyksort, 72 × 40 mm (OLED) legges inn under printen (pause ved Z 3,2) eller limes bak etterpå.
- Festes innenfra med 4 × M3 i gjengeinnsatser Ø4.

### Montering mot hovedkortet
Kortet 180 × 100 ligger med oversiden på z 27,5 (25 mm M3-avstandsstykker på bunnplaten/skinnene), USB-A-portene ut
gjennom venstre vegg. Pi 4 under kortet. Frontkontakter (J7, J8, J9/J13, J10, J23) og bakkontakter (J1–J4, J11, J12,
J19–J21) som i `pcb/README.md` og TOTALINSTRUKS §9.

## Generere filene på nytt
```bash
cd kabinett/skjold-s1/tools && npm install
node run.mjs .. all          # cnc + platemetall + print (eller: sheet | cnc | print)
python3 gravering.py         # graverings-DXF for bunnen (fonter fra npm: @fontsource/sora, @fontsource/ibm-plex-mono)
```
Geometri endres bare i `revb_features.js`, tekst på frontplaten i `cad/generate_print.js`. STEP-generatorene skal melde `bad 0`.
