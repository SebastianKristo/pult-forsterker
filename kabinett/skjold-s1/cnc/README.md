# CNC – Pultforsterker v2

## `pultforsterker_v2_kasse_cnc.step`: kassen, frest ut av én blokk
Massiv B-rep (AP214, mm), med ekte plan- og sylinderflater.

- **Ytre mål:** 215 × 150 × 48 mm, vertikale hjørner R6. Origo er i senter av bunnen, z opp, fronten mot −y.
- **Lomme ovenfra:** 209 × 144 mm, R6 i hjørnene. Bunn og vegger er 3 mm.
- **Materiale:** aluminium 6082 (eller massivtre med tykkere vegger). Blokkemne: 220 × 155 × 50.

### Hull
- **Front:**
  - Ett vindu med hakk i hjørnene, x −91…89, z 5…45, R2. Den 3D-printede frontplaten dekker det.
  - 4 × Ø3,4 for M3 innenfra og inn i innpressede gjengeinnsatser i frontplaten, ved (86 / −87,5, z 8,5 / 41,5).
- **Bak** (x-verdier sett forfra, z 24 hvis ikke annet er oppgitt):
  - Vippebryter 19,2 × 12,8 ved x 76
  - DC Ø11,2 ved x 54
  - USB 9,4 × 3,6 ved x 36
  - AUX Ø6,2 ved x 20
  - BT-antenne Ø6,6 ved x −4
  - Høyttalerpoler 4 × Ø5,2 ved x −30, −45, −65, −80
  - USB-B 2 × 12,2 × 11 ved x ±8, z 10
- **Venstre side:** USB-A-vindu 70 × 9 mm, R2, z 6…15.
- **Bunn:** 8 × Ø3,4:
  - ampkortet ved (96 / −46, ±46)
  - avstandsstykker til lokket ved (±97,5, ±65)

### Fresing
- Det trengs 5 oppspenninger: topp (lomme), front, bak, venstre side og bunn. Med 3 akser må emnet snus mellom hver.
- Lommen er 45 mm dyp. Bruk Ø12 fres eller mindre med minst 50 mm arbeidslengde. Hullene i veggene freses med Ø3 eller mindre.
- Snap-in-vippebrytere er ofte laget for 1–2 mm plate. Fres ned bakveggen lokalt innvendig, eller bruk en bryter med mutterfeste.

### Lokk
- Lokket festes med M3 i 45 mm sekskant-avstandsstykker, skrudd fast fra undersiden.
- Skruehullene i lokket stemmer med den printede utgaven (±97,5, ±65).
- Lokkets innerkant må tilpasses: 208,6 × 143,6 mm og R5,8.

## `pultforsterker_v2_frontplate_*.step`
Frontplate, 203 × 46 × 2 mm. Den skal 3D-printes. Sett inn 4 M3-gjengeinnsatser bak, på samme posisjoner som hullene i fronten av kassen.
