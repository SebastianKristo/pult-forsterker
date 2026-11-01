# Skjold Node – lokk for taktile knapper (alternativ)

Dette er et alternativ til lokket med 12 mm metallknapper. Bunnen, knotten og skjermen er de samme.

## Deler
- 4 × taktil bryter 12 × 12 mm med rund hette (f.eks. 12×12×7,3 + A24-hette)
- `skjold_node_taktil_2_lokk_*`: lokk med hull Ø11,9 og 3 skruetårn
- `skjold_node_taktil_5_knappeholder`: holderen som bryterne sitter i. Print den flat, med lommene opp.
- 3 × M2 × 8 selvgjengende
- Creality: `…_CREALITY_…` (lokk i grønn PLA og tekst i sort PETG, holderen i sort PETG)

## Montering
1. Legg lokket med forsiden ned. Slipp de 4 hettene ned i hullene. Kanten nederst på hetten (Ø13) hindrer dem i å falle ut.
2. Sett bryterne i lommene på holderen. Beina går ned gjennom spaltene. Lodd ledningene under holderen.
3. Legg holderen over hettene, slik at stammene går inn i hettene. Skru fast med 3 × M2 × 8 i tårnene.
4. Lokket monteres på bunnen som før.

## Mål – sjekk dine
Mål avstanden fra bunnen av bryteren til toppen av hetten (`H`, antatt 13,5 mm), diameteren på toppen av hetten (`capTop`, 11,5) og kanten (`skirt`, 13). Endre `T` i `cad/generate_node_taktil_lokk.js` og kjør på nytt. Hullet i lokket (`hole`) skal være 0,3–0,4 mm større enn `capTop`.

## Merk
Holderen ligger over GPIO-pinnene. Bruk vinklede dupont-kontakter eller lodd ledningene direkte, slik som for metallknappene.
