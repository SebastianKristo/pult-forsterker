# Skjold S1: logo og lasermerking (til Claude og JLC)

Merkefilene er tegnet for den avrundede platemetallkassen. Merkingen ligger i laget **MARKING** og er fylte konturer, ikke vanlig tekst, så filen er klar for laser.

## Filer
| Fil | Flate | Sett fra |
|---|---|---|
| `skjold_s1_merking_bunnplate.dxf` / `.svg` | Bunnplaten: logo, «Skjold S1», designer og spesifikasjoner | Undersiden (x er speilvendt) |
| `skjold_s1_merking_bakpanel.dxf` / `.svg` | Bakpanelet: L±, R±, BT, AUX, USB-C (PC 1, PC 2, SERV), LAN, DC 19–24 V, GND, I/O | Bakfra |
| `skjold_s1_merking_venstre_side.dxf` / `.svg` | Venstre side på omslaget: USB 1–4 | Fra venstre |
| `../logo/skjold_logo.svg` | Fullt logo: merke, SKJOLD og STREAMING AMPLIFIER | – |
| `../logo/skjold_merke.svg` | Bare merket: 5 streker, 22/33/42/33/22 høye og 4,6 brede | – |

## Lag i DXF-filene
- **OUTLINE:** omrisset av delen.
- **HOLES:** hull og spalter, slik at verkstedet kan plassere merkingen riktig.
- **MARKING:** det som skal lasermerkes. Lukkede polylinjer, og «even-odd» gir hull i bokstaver som O og A.

## Bestilling hos JLC (sheet metal → Surface Treatment)
- Velg **Laser marking** og last opp én DXF per flate. Tegningen viser den ferdige, bøyde flaten, ikke flatmønsteret. Det er slik JLC vil ha det.
- På sort eloksert aluminium blir lasermerkingen lys sølvgrå. Ikke bestill silketrykk i tillegg.
- Minste teksthøyde er 1,6 mm og minste linjetykkelse ca. 0,25 mm. Det er innenfor det lasermerking klarer.

## Typografi
- **Merkefilene:** Helvetica (Helvetiker Bold og Regular fra three.js). Dette er bevisst: de er laget som konturer og krever ingen font.
- **Logoen på skjermen og i SVG-filene:** Sora 600 og IBM Plex Mono 400. Skal logoen være helt lik overalt, bytt fonten i `cad/generate_marking.js` til en konturfont av Sora (for eksempel konvertert til typeface.json) og kjør skriptet på nytt.

## Lage filene på nytt
Kjør `cad/generate_marking.js` med `REVB` fra `revb_features.js`:

```
new Function('REVB','saveFile','log', src)(REVB, (p,d)=>fs.writeFileSync(p,d), console.log)
```

Skriptet henter fontene fra unpkg, og plasseringen leses fra `REVB`. Serienummeret, `SKJ-S1-0001`, er en plassholder. Lag én fil per enhet hvis hver enhet skal ha sitt eget nummer.
