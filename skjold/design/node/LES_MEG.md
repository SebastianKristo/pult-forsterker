# Skjold Node – 3D-printet kasse (rev B)

Ytre mål 91 × 74 × 34 mm. Brukeren står på siden uten porter. Kablene går ut bak og på høyre side. Skjermbildet roteres 180° i programvaren.

## Filer
- `skjold_node_1_bunn_pi4.3mf` / `_pi3.3mf`: bunn + logo-innlegg som to objekter. Gi bunnen én farge og innlegget sort (AMS). Printes med bunnen ned, og logoen ligger i de første 0,4 mm.
- `skjold_node_2_lokk_forside_ned.3mf`: lokk + innlegg (logo og knappetekst). Printes med forsiden ned. Innlegget ligger i de første 0,4 mm.
- STL-filer av alle deler ligger også ved, i tilfelle slicer-en ikke leser 3MF.
- `skjold_node_3_volumknapp.stl`: printes med toppen ned. Streken kan få egen farge.
- `skjold_node_4_skjermklemme_x2.stl`: print 2 stk.
- PETG, 0,2 mm lag (de første 2 lagene 0,2), 4 vegger, 20 % infill.

## Porter (egne åpninger per modell)
- Pi 4: bak 2 × USB-stabel + Ethernet (Ethernet øverst); front USB-C, 2 × micro-HDMI (egne hull), 3,5 mm
- Pi 3B/3B+: bak Ethernet (nederst) + 2 × USB-stabel; front micro-USB, full HDMI, 3,5 mm
- Begge: micro-SD på venstre side, 24 mm bred åpning helt ned i bunnen + 4 mm utsparing i gulvet, så kortet kan tas ut med tommelen
- Lufting: 5 spalter i bunnen under SoC og 6 i venstre endevegg

## Montering
1. Pi legges på avstandene i bunnen.
2. Skjermen legges i rammen i lokket, med glasset ned. Den holdes av 2 klemmer med 4 × M2 × 6 selvgjengende.
3. Encoder og knapper monteres med mutrene sine i lokket.
4. Lokket legges på. 4 × M2,5 × 20 skrues inn nedenfra, gjennom bunnen, avstanden og Pi-en, og inn i bossene i lokket. Skruene klemmer Pi-en og holder lokket, og de synes ikke ovenfra.
5. Til slutt settes 4 gummiføtter Ø10 under.

## Komponenter
- Skjerm: 1,8″ ST7735S 128 × 160, SPI. Antatte mål er PCB 53 × 35, glass 45,8 × 34 × 2,4 og aktivt felt 35 × 28. **Mål modulen din.** Endre `S` i `cad/generate_node.js` og kjør på nytt.
- Volum: EC11-encoder anbefales. Hull Ø7,2 med pinne for vridningslås. Et potmeter (RK09) passer i samme hull, men Pi-en har ingen analog inngang, så da trengs en ADS1115.
- Knapper: 4 × 12 mm metall-trykknapper med rundt hode Ø14 foran og 13,1 mm dybde bak panelet. Den sekskantede sølvmutteren (16 mm) sitter under lokket og holder knappen. Hullet er Ø12,2. Senteravstanden er 20 mm, så hodene ikke går i hverandre. Mutteren (M12) skal stå med flatsiden mot veggen. Kanten på lokket er åpen på knappesiden.
- Knappene er RADIO, AIR / BT, ◀◀ og ▶▶. Teksten står over knappene som sort innlegg.
- Logo: SKJOLD-merket oppe til høyre på lokket. Under bunnen står SKJOLD NODE, designer og modell. Begge er sorte innlegg.
- Gummiføtter Ø10: 4 forsenkninger på 0,3 mm i bunnen viser hvor de skal sitte.
- Skjermpinnene: lodd ledninger direkte, eller bruk vinklet stiftlist. Rett stiftlist og dupont-kontakter blir for høye.

## Innkjøp (AliExpress-søk)
- 4 × 12 mm metall-trykknapp, momentan, flat, kort hus (samme som S1): https://www.aliexpress.com/w/wholesale-12mm-metal-push-button-momentary-flat-short.html
- EC11-encoder med trykk, 20 mm aksel, halvflat: https://www.aliexpress.com/w/wholesale-EC11-rotary-encoder-switch-20mm-D-shaft.html
- 1,8″ ST7735S 128 × 160 TFT, SPI, 8 pinner: https://www.aliexpress.com/w/wholesale-1.8-inch-TFT-ST7735S-128x160-SPI.html
- 4 × M2,5 × 20 sort pan head: https://www.aliexpress.com/w/wholesale-M2.5x20-black-pan-head-screw.html
- 4 × M2 × 6 selvgjengende for plast, til skjermklemmene: https://www.aliexpress.com/w/wholesale-M2x6-self-tapping-screw-plastic.html
- 4 × gummiføtter Ø10, selvklebende: https://www.aliexpress.com/w/wholesale-self-adhesive-rubber-feet-10mm-black.html
- Dupont-ledninger hunn–hunn, 10 cm: https://www.aliexpress.com/w/wholesale-dupont-wire-female-female-10cm.html
