# Skjold S1, frontplate (Creality K2 + CFS)

Bruk `skjold_s1_frontplate_oled.3mf` eller `..._tft.3mf`. Filen er ett objekt med to deler, og den ligger allerede med forsiden ned mot byggeplaten.

| Del | Filament |
|---|---|
| `khaki` (plate) | eSUN PETG-Matte Light Khaki |
| `sort_innlegg` (tekst, ramme, ikon) | Sort PETG |

STL-filene `_khaki.stl` og `_sort_innlegg.stl` er de samme delene, hvis du heller vil sette dem sammen selv. Velg «Load as parts of one object».

## Lag (målt fra byggeplaten)

- 0,0–0,4 mm: forside med sort tekst lagt inn.
- 0,4–0,8 mm: leppe foran akrylen. Skjermvinduet er 69 × 37 mm for OLED og 56 × 37 mm for TFT.
- 0,8–3,0 mm: hulrom for akrylen, 72,6 × 40,6 mm for OLED.
- 3,0–4,0 mm: baksiden med visningsvindu og hull Ø4 for M3-gjengeinnsatser.

## Innstillinger

- **Lagtykkelse:** 0,2 mm. Bruk gjerne 0,1 mm de første 0,4 mm, slik at teksten blir skarp.
- **Byggeplate:** teksturert PEI gir matt front.
- **Prime tower:** på. Bruk Flush into object/infill.
- **Lim og 3D-akryl:** ikke nødvendig.

## Pause for akrylen

1. Høyreklikk på lagslideren ved **Z 3,2 mm**, altså laget etter at hulrommet er ferdig, og velg «Add pause».
2. Når printeren stopper, legg akrylen (røyksort, 2 mm, 72 × 40 mm for OLED) med den blanke siden ned i hulrommet.
3. Fortsett. Printeren legger baksiden over kanten på akrylen og låser den fast.

Mål tykkelsen på akrylen først. Er den over 2,2 mm, treffer dysen. Da må hulrommet gjøres dypere.

## Montering

Press inn fire M3-gjengeinnsatser (Ø4) fra baksiden. Fest platen med M3 × 6 innenfra kassen.
