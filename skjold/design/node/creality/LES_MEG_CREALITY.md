# Skjold Node – utskrift på Creality (sort PETG + grønn PLA)

Kassen og teksten printes i sort PETG og lokket i grønn PLA. Filene er laget for Creality Print 5/6 med CFS (flerfarge). Tallet på filamentet er allerede satt i 3MF-filene:
- **Filament 1 = sort PETG**
- **Filament 2 = grønn PLA**

## Filer
| Fil | Filament | Print |
|---|---|---|
| `1_bunn_pi4_PETG_sort.3mf` / `1_bunn_pi3_…` | 1 | Bunnen ned. Teksten under er gravert 0,6 mm, fordi sort tekst ikke synes på sort bunn. |
| `2_lokk_TFT_PLA_gronn_tekst_PETG_sort.3mf` | 2 + 1 | Forsiden ned. Logoen og knappeteksten i sort ligger i de første 0,6 mm. |
| `2_lokk_OLED_PLA_gronn_tekst_PETG_sort.3mf` | 2 + 1 | Det samme, for 0,91″ OLED. Den sorte rammen rundt vinduet er også PETG. |
| `3_volumknapp_PETG_sort_strek_PLA_gronn.3mf` | 1 + 2 | Toppen ned. Streken blir grønn. |
| `4_skjermklemme_TFT_x2` / `_OLED_x2` | 1 | Print 2 stk. Bruk den som passer til lokket ditt. |

## Innstillinger
- Lag 0,2 mm, 4 vegger, 20 % infill. Bruk teksturert PEI-plate.
- **Platetemperatur 70 °C** for alle deler. Det fungerer for både PETG og PLA.
- Dyse: PETG 240 °C, PLA 215 °C. Creality Print bytter selv per filament.
- Lokket: slå på «Prime tower» og sett flushing til minst 150 mm³, så sort ikke blander seg inn i det grønne.
- Kjøl PLA 100 %, PETG 30–50 %.

## PETG og PLA i samme del
PETG og PLA fester dårlig til hverandre. Bokstavene står fast fordi PLA-en omslutter dem på sidene, men tynne deler (prikker, små hakk) kan løsne hvis du skraper hardt. Vil du ha det helt sikkert: print lokk-innlegget i sort PLA i stedet. Da trenger du ikke endre noe annet.

## Uten CFS (Ender, K1 uten flerfarge)
Bruk STL-filene i `node/`. Print lokket i grønn PLA og legg inn en pause ved 0,6 mm. Bytt så filament til sort, print to lag, pause og bytt tilbake. Eller bare print lokket helt grønt.
