# Skjold S1, kasse i platemetall (avrundet R9)

Frontplaten printes separat og er ikke med her. Alle skjøter og skruer sitter på undersiden.

## Filer
| Fil | Hva |
|---|---|
| `skjold_s1_platemetall_avrundet.step` | Hele kassen satt sammen, OLED-versjon: omslag, front, bak, bunnplate og 2 skinner |
| `skjold_s1_platemetall_avrundet_tft.step` | Samme, men med større skjermhull i fronten for TFT |
| `skjold_s1_omslag_flatmonster.dxf` | Omslag (topp og sider i ett), 307,3 × 160 mm, 4 bøyer |
| `skjold_s1_panel_front_oled_flatmonster.dxf` / `_tft` | Frontpanel med 10 mm flens nederst, 1 bøy |
| `skjold_s1_panel_bak_flatmonster.dxf` | Bakpanel med 10 mm flens nederst, 1 bøy |
| `skjold_s1_bunnplate.dxf` | Bunnplate, flat, med luftespalter |
| `skjold_s1_skinne_x2.dxf` | Innvendig vinkelskinne, 2 stk, 1 bøy |

Lagene i DXF-filene heter CUT (kuttelinjer) og BEND (bøyelinjer).

## Bestilling
- **Materiale:** aluminium 5052-H32, 1,5 mm
- **Bøyer:**
  - Omslaget har innvendig radius **R7,5**, altså utvendig R9. Skriv det i kommentarfeltet. Mange verksteder bruker R1,5 som standard.
  - Panelene og skinnene har standard R1,5.
- **K-faktor:** 0,44. Flatmønstrene er beregnet med den. La gjerne verkstedet bruke sin egen K-faktor ut fra STEP-filen.
- **Overflate:** pulverlakk eller eloksering, sort eller den fargen du ønsker.
- **Lasermerking:** logo og produktmerking under kassen: `skjold_s1_bunn_gravering.dxf` (lag ENGRAVE), legges som egen DXF under «Surface Treatment». Se `skjold_s1_bunn_gravering.png`.
- **Innpressede gjengedeler (PEM):**
  - CLS-M3-1 (hull Ø4,2): 4 stk i panelflensene og 6 stk i bunnplaten
  - FHS-M3-8 (hull Ø3,0): 4 stk i sideveggene på omslaget, for skinnene. De ligger plant og synes ikke utenfra.

## Montering
1. Press skinnene på piggene i sideveggene og fest med M3-mutter.
2. Skyv bunnplaten inn i omslaget fra den ene enden, slik at den ligger på flensene nederst.
3. Sett inn frontpanelet og bakpanelet i endene. Flensene på panelene skal ligge på flensene til omslaget.
4. Skru 10 × M3 × 6 med flatt hode nedenfra gjennom flensene på omslaget.
5. Hovedkortet monteres på M3-avstandsstykker:
   - 12 mm på skinnene for de to ytterste hullene på hver side
   - 25 mm (PEM SO) på bunnplaten for resten
6. Frontplaten skrus fast med 4 × M3 × 6 innenfra, gjennom hullene på Ø3,4 i frontpanelet.

## Merk
- **Stort hull i bunnen:** det rektangulære hullet på 18 × 16 mm er tatt bort her, fordi det ville kollidert med flensen. Si fra hvis det skal brukes til noe.
- **Spalter i høyre side:** skinnen dekker de nederste 1 mm av spaltene.
