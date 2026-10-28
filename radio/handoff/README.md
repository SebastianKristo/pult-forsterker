# Handoff: Pultforsterker Radio Retro (mono)

## Overview
Mono nettradio/forsterker i retro-stil, bygget rundt et ferdig 3D-printet skall (`source/Shells.3mf`, "Deep Shell – with button", 244 × 104 × 155 mm). Nye deler foran og bak: faceplate med 2,8" fargeskjerm, 6 favorittaster, SOURCE/◀◀/▶▶, volumknapp, en domet perforert grill med magnetfeste, bakplate med tilkoblinger, skillevegg og bein. POWER er en 12 mm metallknapp i det eksisterende hullet på toppen av skallet.

Elektronikk: to ferdige kort fra PCBWay (kort 1: ESP32-S3 + I2S-DAC, kort 2: forsterker), ett 78 mm fullregister-element. Programvare: squeezelite-esp32 mot Lyrion Music Server (nettradio, AirPlay, Bluetooth, albumcover).

## Om filene
`Pultforsterker Radio Retro.html` er en **designreferanse**: en three.js-modell som viser geometri, mål, farger og skjerm-UI. Den er ikke produksjons-CAD eller fastvare. Oppgavene videre:
1. **Mekanikk:** gjenskape de nye delene i et ordentlig CAD-verktøy (Fusion, FreeCAD, OpenSCAD/CadQuery), slik at de blir lukkede og printbare. STL-knappene i modellen gir en grov, ikke-manifold eksport.
2. **Fastvare:** implementere skjerm-UI og knappelogikk på ESP32-S3 (squeezelite-esp32 eller egen LVGL/TFT_eSPI-app).

Åpne HTML-filen via en lokal webserver (`npx serve .`), siden den henter `retro/*.stl` og `retro/shell_contours.json`.

## Fidelity
Mekanikk er **mid-fi**: mål og plassering gjelder, men utsparinger, klips og toleranser må verifiseres mot det printede skallet. Skjerm-UI er **hi-fi**: farger, layout og innhold er ment slik.

## Koordinater og hovedmål
Enheter i mm. Koordinatene er skallets egne (fra 3MF): x mot høyre, y er dybde (front = −y), z opp, origo midt i skallet.
- Skall, dyp variant: y −52…+52, z ±77,5, x ±122
- Innvendig frontåpning: kontur i `retro/shell_contours.json` → `deep.inner` (180 punkter, x/z). Tilnærmet x ±116, z ±71,6. Bunnen er flatere enn toppen (r = 101 ved 225° mot 91,6 ved 135°).
- Bakåpning: `deep.recess`. Nedre halvdel er rekonstruert, fordi bunnslissene forstyrrer snittet. **Mål på det printede skallet.**
- Hull på toppen (POWER): Ø ca. 12 i x 0, y +5,5

## Deler (nye)
| Del | Posisjon | Tykkelse | Notat |
|---|---|---|---|
| Faceplate | front y = −40 (YMIN+12) | 3 + 6 mm krage bak | Innvendig kontur − 0,35. Hull: skjerm 60 × 46 @ (50, 6), 9 × taster 11,6 × 7,2, Ø8 volum @ (98, −8), Ø72 høyttaler @ (−52, 0), 4 × Ø6,2 magneter |
| Grill | ligger på faceplaten, y −51,6…−40 | 1,6 skall, kuppel 10 | Kontur = innvendig − 0,75 minus utsparing K. Kuppelhøyde = 10 · smoothstep(avstand til kant / 28). Perforering Ø3,2, hex, pitch 5,4, 4 mm fra kant |
| Utsparing K | avrundet rektangel, senter (68, −20), 124 × 112, r 24 | – | Viser faceplaten nede til høyre |
| Bakplate | i bakåpningen, y 49…51,7 | 2,7 | Tilkoblinger i z −34: POWER-vippebryter (44), DC (22), USB-C (6), AUX (−8), poler (−26, −40), INT/EXT (−58). Ventilasjonsslisser 7 × 2 i z 20 og 34. 4 × M3 inn i ringen |
| Skillevegg | x 4,8…7,2 | 2,4 | Fra faceplate til bakplate − 0,2. Lukket kammer til venstre (høyttaler), elektronikk til høyre. Kabelhull Ø8 |
| Tastehetter | 6 + 3 | 6 høye | 10,4 × 6,2, r 1,8, med tall/ikon trykt eller gravert |
| Skjermvindu | 64 × 50 | 1 | Røykfarget akryl |
| Bein | (±82, ±28) under skallet | Ø8 → Ø5,2, 24 lange | Vinklet ca. 7–9° utover |
| Magneter | 4 × Ø6 × 2 i grill + 4 i faceplate | – | (−96, ±40), (−18, ±56). Sjekk polaritet |

Plassering av kontroller (x, z) på faceplaten:
- Favoritter 1–6: x 20, 32, 44, 56, 68, 80, z −30. LED-punkt 5,2 over hver tast.
- SOURCE (22, −44), ◀◀ (36, −44), ▶▶ (50, −44)
- Volumknapp: Ø28, 16 dyp, riflet, (98, −8). EC11 med trykk = mute.
- Etiketter: «SOURCE» under SOURCE, «VOLUME · PUSH MUTE» under knappen, Helvetica 500, 1,8 mm høy, sperret

## Fargetemaer
| Tema | Skall | Grill | Faceplate | Taster | Tastetekst | Etiketter |
|---|---|---|---|---|---|---|
| Sennep | #D9A21B | #DCCBA0 | #5B4636 | #EFE6D0 | #4A3A2C | #E9DCC0 |
| Mint | #9FCFBF | #F1EAD8 | #3E3A36 | #F4EFE2 | #3E3A36 | #E8E2D2 |
| Kirsebær | #A3262A | #E7DCC4 | #2B2523 | #EFE7D6 | #2B2523 | #E0D6C4 |
| Sort | #222224 | #9A9893 | #121213 | #D9D7D1 | #1D1D1E | #B9B7B1 |
Knapp og bein: aluminium (#D4D3CE).

## Skjerm-UI (2,8" IPS, 320 × 240, ILI9341/ST7789)
Bakgrunn #0B0C0E. Tekst #F4F6F8, dempet #8B939B, inaktiv #2A2F35, aksent #FFB547. Font: Helvetica Neue / Arial.
- **Topplinje** (y 14): «RADIO · n/6» i aksentfarge (bold 11 px, sperret 1,2 px), eller kildenavn i dempet farge. Klokke til høyre.
- **Cover:** 128 × 128 @ (12, 28), r 8. Albumcover fra Lyrion (`artwork_url`). Når cover mangler eller under tilkobling: animert nivåmeter (12 søyler).
- **Tekst** fra x 152, bredde 156, ruller hvis den er for lang (20 px/s): stasjon/tittel bold 20 px (y 44), låt 15 px (y 74), artist 13 px dempet (y 94). Under tilkobling: «Kobler til…».
- Radio: «192 kbps · Lyrion» 11 px (y 148). AirPlay/BT: fremdriftslinje 3 px (y 140) og tider.
- **Kildelinje** (y 172, h 20, r 10): RAD, AIR, BT, AUX, USB. Aktiv er fylt hvit med mørk tekst, inaktive har kontur.
- **Volum** (y 206–226): «VOL» (eller «EXT» når eksterne høyttalere er valgt), 30 segmenter som blir høyere mot høyre, tallet bold 20 px til høyre.

## Oppførsel
- **POWER (topp):** kort trykk = standby av/på. Hold 3 s = omstart. LED-ringen lyser når enheten er på og dimmes i standby.
- **SOURCE:** går til neste kilde (Radio → AirPlay → Bluetooth → AUX → USB). LED-ringen blinker 500 ms.
- **Favoritt 1–6:** kort trykk spiller Lyrion-favoritt n og bytter til Radio. Hold 2 s lagrer stasjonen som spiller. LED over aktiv favoritt lyser.
- **◀◀ / ▶▶:** forrige/neste favoritt i radio, forrige/neste låt i AirPlay/BT.
- **Volumknapp:** vri = volum 0–100, trykk = mute.
- **Stasjonsbytte:** «Kobler til…» i ca. 900 ms, deretter metadata.
- **INT/EXT (bak):** velger innebygd høyttaler eller polene. Skjermen viser «EXT».

## State
`input` (0–4), `station` (0–5), `volume` (0–100), `muted`, `extSpeaker`, `power`, `tuningSince`, og metadata (`title`, `artist`, `artworkUrl`, `bitrate`, `elapsed`, `duration`).

## Filer
- `Pultforsterker Radio Retro.html`: modell og kontrollpanel
- `pultforsterker_radio_retro.js`: all geometri (`build()`), skjermtegning (`draw()`) og interaksjon
- `three-d-stage.js`: viewer
- `retro/deep.stl`, `retro/shell.stl`: skallene, konvertert fra 3MF uten endringer
- `retro/shell_contours.json`: snittkonturer av skallet (inner, outer, recess, ring)
- `source/Shells.3mf`: originalt skall (brukerens fil)
