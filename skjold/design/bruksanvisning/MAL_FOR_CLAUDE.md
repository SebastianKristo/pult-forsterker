# Mal: Skjold S1 byggeanvisning

Bruksanvisningen tegnes fra `innhold.json`. Claude fyller ut eller endrer innholdet der. Designet i `Bruksanvisning.dc.html` skal ikke endres for å legge til steg.

## Regler for innholdet
- Ett steg per side. Hvert steg skal vise alt som trengs for akkurat det steget, som i en LEGO-anvisning.
- Korte setninger. Bildet forklarer, teksten bekrefter.
- `[fylles inn]` og `[bekreft]` markerer det som må hentes fra kretsskjemaet. Ikke gjett pinner.
- Del-ID-er (A1, E1, K1, L1, S1 …) må finnes i `inventory`.
- Bilder: hvert `img` blir en bildeplass med den ID-en. Bildene dras inn i dokumentet.

## Sidetyper
| type | felt |
|---|---|
| cover | lead, img |
| inventory | title, groups[ {name, parts[ {id,name,qty,note} ]} ] (maks ca. 30 deler per side) |
| tools | title, tools[ tekst ], note |
| section | n, title, sub, img |
| step | n, title, parts[ {id,name,qty,note} ] (maks 5), img, wires[ {from,to,color,colorName,awg,len} ] (maks 5), tips[ ] (maks 2), warn |
| check | n, title, checks[ {what,expect} ] (maks 6), img |
| end | title, body, img |

Stegnumre (`n`) går fortløpende gjennom hele boka. Sidetall regnes ut automatisk.
