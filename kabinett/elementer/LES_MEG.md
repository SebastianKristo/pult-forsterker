# Høyttalerelementer – mal for Røst og Røst Rund

Begge Røst-variantene tegner hullene for elementet fra én mal: `elementer.scad`. Velg et element med
`element = "rs75_4"` øverst i produktfila (eller `-D 'element="frs8_4"'` på kommandolinjen), eller fyll inn ditt eget
under `"egen"`. Røst får utsparing, forsenkning for rammen og skruehull i frontplata fra malen. Røst Rund får en
**utskiftbar elementplate** (92 × 92 × 4 mm) bak frontblokka: bytter du element, printer du bare en ny plate.

## Mål du trenger (skyvelære eller datablad)

| Felt | Hva |
|---|---|
| `utsp` | hullet elementet trenger («baffle cutout») |
| `ramme` | rammens ytre mål (diameter, eller sidekant hvis den er firkantet) |
| `form` | 0 = rund ramme, 1 = firkantet |
| `pcd` | hullsirkelen: avstanden mellom to motstående skruehull, målt senter til senter |
| `antall`, `hull`, `vinkel` | antall skruehull, diameter, og vinkelen til første hull (0 = rett til siden, 45 = på skrå) |
| `dybde` | fra rammen og bakover til enden av magneten |
| `fs` | resonansfrekvensen fra databladet (Hz), for å stemme porten |

Send meg målene (eller en lenke til databladet), så legger jeg elementet inn i malen og lager plata.

## Elementene i malen

| Element | Ω | Utsparing | Mål bekreftet? | Pris (omtrent) |
|---|---|---|---|---|
| Dayton Audio RS75-4 | 4 | 54 mm (ytre 72, hullsirkel 64, dybde 38,5, Fs 177 Hz) | ja | €31–38 |
| Visaton FRS 8 4 Ω | 4 | 73 mm (ytre 78, dybde 35) | hullsirkelen må måles | €15–20 |
| GRS 3FR-4 | 4 | 71,6 mm | ramme, hull og dybde må måles | €6–9 |
| FaitalPRO 3FE22-4F | 4 | 73,6 mm | ramme, hull og dybde må måles | ca. €25 |

**Merk om bassen:** RS75-4 har resonans rundt 177 Hz. Porten i Røst (ca. 83 Hz) og Røst Rund (ca. 74 Hz) er regnet
ut fra kassa, ikke tilpasset elementet, så den gir lite ekstra bass med RS75-4. Legg elementets Thiele/Small-data inn i
WinISD med kammeret og porten, og juster portlengden (`portL`) før du printer.

## Hvor kjøpe (Norge og Sverige)

Jeg fant ingen norsk nettbutikk som fører disse elementene. Det nærmeste:

- **Sverige:** Elfa (elfa.se) og RS Components (se.rs-online.com, ca. 132 kr eks. mva.) har Visaton FRS 8 4 Ω.
  Hifikit.se i Stockholm skal selge løse elementer (nevnt i et forum, ikke sjekket).
- **Danmark:** Proshop.dk har Visaton FRS 8 (var ikke på lager da jeg sjekket).
- **EU, sender til Norge og Sverige:** Soundimports.eu (RS75-4, GRS 3FR-4, Dayton CE78PF-4, Visaton FRS 8) og
  Audiophonics.fr (RS75-4). Regn med frakt, og for Norge mva. og toll.
- **Billig og usikkert:** «3 inch 4 ohm full range» på AliExpress. Målene varierer, så mål før du printer plata.
