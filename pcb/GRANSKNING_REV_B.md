# Uavhengig granskning av produksjonsfilene – hovedkort rev B

Granskningen ble gjort på de **ferdige** filene (gerber, drill, BOM, CPL) etter at kortet var fryst (commit `9ae80c2`),
av to granskere som ikke hadde sett kildekoden: én for gerber/DFM, én for BOM/CPL. En tredje slo opp LCSC-koder.
Alt under «Rettet» er gjort i kilden og filene er regenerert uten ny ruting (kobberet er uendret bortsett fra de to punktene
som er merket *kobber*).

## Gerber / DFM (JLCPCB 2 lag)

Verifisert i orden: komplett lagsett og format, lukket kortkant 180 × 100, alle 520 hull + 12 slisser midt i pads/vias,
minste spor 0,2 mm, minste klaring 0,152 mm (mål 0,2; alt over JLCPCBs 0,127), kobber ≥ 0,5 mm fra kant, loddemaske og
pasta på riktig sted (734 pasta-åpninger = 734 SMD-pads, ingen på THT), vias tildekket, alle nett sammenhengende i
gerber-kobberet, ingen isolerte nettdeler, polaritetsmerker på dioder/elektrolytter/IC-er.

| Funn | Alvor | Status |
|---|---|---|
| 4 GND-vias lå inni 0603-pads (C14, R82, C106, R49) – tinn kan suges ned i viaen ved reflow | bør fikses | **Rettet** (*kobber*): eksporten setter aldri stitching-vias inni pads og fjerner slike til slutt |
| 2 via-par med 0,45 mm hull-til-hull (JLCPCB vil ha 0,5) | bør fikses | **Rettet** (*kobber*): regel 0,5 mm i KiCad + automatisk forskyvning av via-par |
| 24V_AMP til TPA3116 går gjennom to Ø0,5-vias i serie (≈ 2,5 A) | bør fikses | **Rettet** (*kobber*): viaene er nå Ø1,3/0,75 + en ekstra via på toppen |
| Høyttalersporene OUT*/SPK_* har 0,4–0,5 mm-strekninger (≈ 1,2–2 A ved 10 K, 1 oz) | virker, varmt ved full effekt | Ikke mulig å utvide uten ny ruting. **Anbefaling: bestill 2 oz kobber.** |
| 5V_USB til USB-A-portene 0,4 mm (≈ 30 K ved 2 A) | lett | Som over (2 oz) |
| NPTH-hull (Pi-hull H5–H8, USB-C-styrepinner) har 0,25 mm til jordplanet | info | Innenfor JLCPCB; ikke endret |
| Ingen referansebetegnelser på silketrykket (bare på F.Fab) | info | Bevisst – kortet er tett. Bruk `produksjon/board_top.png` ved feilsøking |
| Courtyard-overlapp (6), starved thermal (11), silk-varsler | støy | Målt: pad-til-pad ≥ 0,2 mm overalt; THT-GND-pads har både eike og rutet GND-spor |

## BOM / CPL (JLCPCB PCBA)

Verifisert i orden: 255 SMD-rader, ingen duplikater, alle koordinater = footprint-senter (0,000 mm avvik), alle på Top,
pastemaske stemmer 100 %.

| Funn | Alvor | Status |
|---|---|---|
| 14 LCSC-koder pekte på **feil del** (L1 = PTC-sikring, C2/C3/C43 = 22 µH-spole, C8–C10 = 22 µF 0805, C49–C52 = 33 nF 0402, C23/C24 = 150 pF, R21–R24 = 2,4 kΩ, R5/R16/R64/R65 = 0402-motstander, R3/R6/R75 feil/uverifisert) | **blokkerer** | **Rettet** med verifiserte koder (se tabell under) |
| J5 var hunn-header (C50982) | bør fikses | **Rettet** → C50980 (hann) |
| J11/J12 var en annen produsents USB-C enn footprinten (C2765186) | bør fikses | **Rettet** → HRO TYPE-C-31-M-12 (C165948) |
| J8/J9 uverifisert kode | bør fikses | **Rettet** → B5B-XH-A C157991 |
| THT-deler lå i BOM/CPL med pinne-1-koordinat (ville blitt feilplassert om JLCPCB monterte dem) | bør fikses | **Rettet**: THT er ute av BOM/CPL, egen liste `ki_pultforsterker_main_tht_handlodding.csv` |
| CPL-rotasjon var rå KiCad-vinkel (SOT-23, SOIC/TSSOP/QFN, elektrolytter, USB-C) | bør fikses | **Rettet**: KiBot/JLCKicadTools-tabellen er lagt på. Kontroller likevel i forhåndsvisningen |
| R18 (DNP) hadde pastaåpning | bør fikses | **Rettet**: DNP-deler får ikke pasta |
| C87/C88 «20p» med 22 pF-kode, R2 «51k» med 49,9 k-kode | info | **Rettet** (verdiene i BOM stemmer nå med kodene) |
| Reserve-oscillator i README var en krystall | info | **Rettet** → C789111 / C253724 |

### Koder som er byttet (alle sett på lcsc.com eller jlcpcb.com)

| Del | Før | Nå | Hva |
|---|---|---|---|
| C2, C3, C43 | C76838 (22 µH!) | C170099 | Samsung CL32B475KBUYNNE 4,7 µF 50 V X7R 1210 |
| C8–C10 | C45783 (22 µF 0805) | C77101 | Murata GRM32ER61C476KE15L 47 µF 16 V 1210 |
| C49–C52 | C13594 (33 nF 0402) | C1881 | FH 1206B684K500NT 680 nF 50 V 1206 |
| C23, C24 | C1594 (150 pF) | C1604 | FH 0603B222K500NT 2,2 nF 50 V (Basic) |
| C32–C35 | C45790 (uverifisert) | C5378 | Samsung CL21B224KBFNNNE 220 nF 50 V 0805 (Basic) |
| C40, C41, C72 | C134754 (uverifisert) | C190286 | 220 µF 50 V 10 × 10,5 SMD-elektrolytt |
| L2–L5 | C182272 (uverifisert) | C241221 | CEC SMRH125-100M 10 µH 4 A 12 × 12 |
| R3 | C22999 | C667189 | 243 kΩ 0,1 % 0603 |
| R4, R5 | C23206 / C25744 (10 k 0402) | C4216 / C4260 | 33 kΩ / 6,2 kΩ 0603 (Basic) – buck gir 5,06 V |
| R6 | C22791 | C22797 | 13 kΩ 0603 (Basic) |
| R16 | C25765 (0402) | C4184 | 20 kΩ 0603 (Basic) |
| R64, R65 | C25092 (0402) | C23345 | 22 Ω 0603 (Basic) |
| R75 | C25772 (0402?) | C13167 | 2,7 kΩ 0603 (Basic) |
| J5 | C50982 (hunn) | C50980 | 2 × 20 hann 2,54 mm |
| J8, J9 | C144396 | C157991 | JST B5B-XH-A |
| J11, J12 | C2765186 | C165948 | HRO TYPE-C-31-M-12 |
| L1 | C135446 (PTC-sikring!) | C2042471 | Bourns SRP1245A-100M (alt. C241221 CEC SMRH125-100M, passer på padene) |
| D2 | C32569 (uverifisert) | *(tom)* | SS56 SMB – velges i JLC-UI (SMA-utgaven C65009 passer på padene) |
| R21–R24 | C17949 (2,4 kΩ) | *(tom)* | 18 Ω 1206 – velges i JLC-UI |
| F1 | C70283 (uverifisert) | *(tom)* | THT, kjøpes selv (Keystone 3512 / C3130) |

## Ikke verifisert av granskningen

- Lagerstatus og pris per kode (endrer seg daglig).
- JLCPCBs faktiske 0°-orientering per LCSC-del (varierer med produsentens tape) – derfor punkt C5 i sjekklisten.
- Mekanisk passform av SMRH125-100M på L1-footprinten hvis SRP1245A ikke finnes (pads er 12 × 12-klassen, men ikke målt).
- Skjema-riktighet (nettliste) – det ble gjort i de tidligere granskningene før frysen, ikke i denne.

## Sluttkontroll (tre nye uavhengige granskere på de regenererte filene)

| Funn | Alvor | Status |
|---|---|---|
| PGA2311 hadde VD+ på alltid-på 5 V, men VA+/VA− på 5V_SW: i standby 5 V differanse mellom forsyningene, og DAC-en (alltid på) driver inn i en strømløs analogdel | **kritisk** | **Rettet**: FB1 (VA+), LM2662 (VA−) og MUTE-pullup flyttet til alltid-på 5 V; PGA mutes i programvare i standby (daemonen gjorde det allerede) |
| Buck 5,28 V > 5,25 V-grensen for PGA2311/PCM1808/USB | bør fikses | **Rettet**: 33 k/6,2 k (Basic-deler) → 5,06 V |
| VIN24 (hele forsterkerstrømmen) gjennom én Ø0,5-via | bør fikses | **Rettet**: Ø1,3/0,75 + parallell via |
| Ekstra 24V_AMP-via overlappet skinnen bare 0,1 mm | info | **Rettet**: skinnen forlenget over viaen |
| J6 (5 V-terminal) sto rett over Pi-ens USB3-blokk (1–2 mm margin til metallskallet) | bør fikses | **Rettet**: J6 flyttet/rotert så pinnene står ved x = 82 (utenfor blokken, som dekker x 84,5–104,5) |
| J5-flatkabel 10 cm er for kort (Pi-header → rundt bakkanten → J5 ≈ 115–120 mm) | bør fikses | Dokumentert: bruk 15–20 cm kabel |
| MCP23017 INTA (push-pull) på GPIO 14 = UART TXD | bør fikses | Allerede håndtert: daemonen setter INTA open-drain, install.sh setter `enable_uart=0` |
| Kabinett: USB-C-panelkontakter PC1/PC2 kolliderer med høyttalerpolenes muttere og med kortkant/C110; USB-A-vinduene i venstre side er speilvendt (for/bak); POWER-knapp/KCD1/12 mm-knapper har for lite dybde; stolpehøyde 25 mm gir z 28,0; 15 mm kjøleribbe treffer lokket | **kritisk for kassen, ikke for kortet** | Ikke rettet her – se `kabinett/skjold-s1/` (må rettes før kassen produseres) |
| Alle øvrige punkter: pinne-for-pinne for alle IC-er, Pi-header, strømvei, polaritet, USB, gerber (hull-til-hull 0,52, ingen via-i-pad, alle nett sammenhengende), BOM/CPL (24 koder stikkprøvd) | – | Verifisert OK |

Etter rettelsene er kortet rutet på nytt og alle automatiske kontroller (DRC, hull-til-hull, via-i-pad, flaskehals) kjørt igjen.

**Kontroll av den nye rutingen (commit `d5abd91`), målt i gerberne:** alle 189 nett sammenhengende (ingen øyer), hull-til-hull min. 0,516 mm,
ingen via-i-pad (nærmeste via-hull 0,285 mm fra pad-kobber), min. klaring 0,144 mm (JLCPCB-grense 0,127), kobber til kant 0,74 mm,
pasta på alle 730 SMD-pads unntatt R18 (DNP) og U6 EP (bevisst), BOM = CPL = 230 SMD-deler, 6 linjer uten kode (velges i JLC-UI).
Flaskehalser: 24V_IN 2,0 · 24V_F 1,85 · VIN24 1,3 · 24V_AMP 1,3 (pinnestubber 0,4) · 5 V til Pi 1,5 mm.
