# Pultforsterker – kabinettspesifikasjon (Skjold S1, hovedkort rev B)

Alt som trengs for å lage kabinettfilene (STEP/DXF til PCBWay sheet metal, STL/3MF til print) uten å kollidere med innmaten.
Tallene her er de samme som i `revb_features.js` (geometri), `pcb/build_board.py` (kortet) og `tools/frontplate_metall.py` (frontplaten).
Endre i de filene og generer på nytt (siste avsnitt) – ikke i STEP/DXF-filene.

## 1. Koordinatsystem

- **Kasse:** x mot høyre (sett forfra), y bakover (frontpanelets utside = −80, bakpanelets = +80), z opp (0 = underside av kassen,
  48 = topp). Origo midt under kassen.
- **Frontplate:** (x, y) med origo midt på platen; x som kassen, y = z − 24.
- **Hovedkort:** (bx, by) i mm fra kortets hjørne (KiCad), 180 × 100. Kortet ligger med komponentsiden opp, **bakkanten (by ≈ 6:
  skruterminaler for 24 V og høyttalere) mot bakpanelet**, frontkontaktene (by ≈ 94) mot fronten, USB-A-portene (bx ≈ 0) mot venstre vegg.

  Omregning: **x = bx − 92,3 · y = 51,7 − by · z(kortets underside) = 27,5, overside 29,1** (1,6 mm kort).
  Kortets fire M3-hull (bx, by) = (4, 4), (176, 4), (4, 96), (176, 96) → kasse (−88,3, 47,7), (83,7, 47,7), (−88,3, −44,3), (83,7, −44,3).

## 2. Kassen (platemetall)

| | |
|---|---|
| Utvendig | 190 × 160 × 48 mm (B × D × H) |
| Form | R9 på de fire langsgående kantene (topp og bunn), rette sider z 9 … 39 |
| Materiale | Aluminium 5052-H32, **1,5 mm**. Omslag (topp + to sider) bøyd med innvendig R7,5 (= utvendig R9); front-/bakpanel og skinner R1,5; K-faktor 0,44 |
| Overflate | glassperleblåst + sort eloksert («bead blast + anodized color, black») |
| Deler | omslag med 12 mm flens nederst · frontpanel og bakpanel med 10 mm flens nederst · bunnplate · 2 innvendige vinkelskinner |
| Panelenes flate del | x ±93,3, z 4,5 … 46,3, hjørneradius 7,3 (innenfor omslaget) |
| Bunnplate | 172 × 136,4 (x ±86, y ±68,2), ligger på omslagets flenser: overside z 3,0 |
| Skruer | alle fra undersiden: 10 × M3 × 6 flatt hode gjennom omslagets flenser; PEM CLS-M3-1 (hull Ø4,2) i panelflensene (4) og bunnplaten (6, ved (±80, −60 / 0 / 60)); FHS-M3-8 (hull Ø3,0) ×4 i sideveggene for skinnene |
| Kortfester | M3-avstandsstykker: **25 mm** på bunnplaten (PEM SO) for de fire korthullene → kortets underside z 27,5 (12 mm på skinnene der det brukes) |
| Føtter | 4 × selvklebende gummi Ø12,7 × 3,5 ved (±80, ±65) |
| Innvendig fri høyde | z 3,0 (bunnplate) … 46,5 (omslagets innside) = 43,5 mm |

### Hull i kassen (kasse-koordinater, mm)

**Frontpanel (x, z):**

| Del | Senter | Hull |
|---|---|---|
| Skjermutsparing (OLED 2,42" og TFT, felles) | (−27, 24) | 62 × 39, R2 |
| POWER-knapp 16 mm | (−76, 24) | Ø16,4 |
| Knapp 12 mm BT / RADIO / AUX / USB | (22, 32,5) (38, 32,5) (22, 15,5) (38, 15,5) | Ø12,4 |
| Volumencoder EC11 | (66, 24) | Ø7,4 |
| Hodetelefon PJ-392 (hus Ø8) | (−76, 8) | **åpent spor 8,6 bredt, R1, fra underkant (gjennom bøy og flens) opp til z 12,3** |
| Frontplateskruer (studs i platen) | (±83, 7) (±83, 41) (12, 8,5) (12, 39,5) | Ø3,4 |

**Bakpanel (x, z):**

| Del | Senter | Hull |
|---|---|---|
| KCD1 vippebryter | (78, 24) | 19,4 × 13 |
| RJ45 panelkontakt | (44, 13,5) | 17 × 15,6 + to avlange skruehull 5,3 × 3,3 ved (31, 13,5) og (57, 13,5) |
| DC 5,5/2,5 | (44, 34) | Ø11,4 |
| Jordpunkt M3 | (62, 40) | Ø3,4 |
| Høyttalerpoler L+ L− R+ R− (M8-gjenge, Ø19 isolasjonsring) | (−82,8, 24) (−63,8, 24) (−44,8, 24) (−25,8, 24) | **Ø8,5** – 19 mm deling så ringene (Ø19) ikke berører hverandre; polen skal være isolert fra chassiset: isolasjonsring på begge sider av platen, eller krympestrømpe/elektrikerteip rundt gjengen gjennom hullet. Mål med ohmmeter at ingen pol har kontakt med kassen før første påslag |
| AUX 2 / AUX 1 (PJ-392) | (−11, 24) (−1, 24) | Ø6,4 |
| USB-C panelkontakt PC 1 / PC 2 / Pi | (15, 34) (15, 24) (15, 14) | 9,6 × 3,8 + M3-slisser 5,4 × 3,2 ved x 5,5 og 24,5 (passer panelkontakter med 18–20 mm skruedeling) |

**Venstre side (y, z) – ingen merking:** 4 × USB-A-vindu 14,8 × 8 ved y −32,1 / −14,6 / 2,9 / 20,4, z 32,6 (= kortets USB-A, hus 13,1 × 5,6 bak vinduet).
**Høyre side:** 26 luftespalter 2,4 × 24 ved z 26,5, y fra −43,8 med 3,6 mm deling.
**Bunn (x, y):** 23 luftespalter 2,4 × 40 ved y −14, x fra −55 til 55 med 5 mm deling (under Pi-en); PEM-hull (±80, −60 / 0 / 60).
**Lokk/omslag:** ingen hull i toppen.

## 3. Frontplaten (aluminium, utenpå frontpanelet)

| | |
|---|---|
| Mål | 178 × 46 × **3 mm**, R3, 5052-H32, samme overflate som kassen. Utsiden ligger på y −83 |
| Feste | 6 × FH-M3-8 selvklinkende studs presset inn bakfra (hull Ø3,0) gjennom panelets Ø3,4-hull, M3-mutter innvendig |
| Skjermvindu | 62 × 38, R1,5, senter (−27, 0). Røyksort akryl 2 mm (61,6 × 37,6) limt inn bakfra, 1 mm forsenket |
| POWER | Ø16,4 ved (−76, 0) |
| Knapper | Ø12,4 ved (22, 8,5) (38, 8,5) (22, −8,5) (38, −8,5) |
| Encoder | Ø7,4 ved (66, 0) |
| Hodetelefon | **Ø5,5 gjengebor, gjenges M6×0,5** ved (−76, −16). PJ-392 skrus inn bakfra til den er i plan, Loctite 222, ingen mutter foran. Gjengelengde 4,4 → 1,4 mm stikker ut bak |
| Studs | Ø3,0 ved (±83, ±17) og (12, ±15,5) |
| Merking (laser) | BT, RADIO over og AUX, USB under knappene (Helvetiker Bold 1,8 mm versal), ramme 1,4 mm rundt vinduet, hodetelefon-ikon ved (−68,6, −16), SKJOLD-logo under knotten (x 55 … 77, y −21 … −17). Ingen tekst ved POWER |

## 4. Betjeningsdeler – mål bak panelet (for kollisjonssjekk)

Front: avstanden fra frontpanelets innside (y −78,5) til kortets forkant (y −48,3) er **30 mm**; til frontkontaktene på kortet (JST ved by 94 → y −42,3) **36 mm**.

| Del | Utvendig | Bak panelet | Merknad |
|---|---|---|---|
| Metallknapp 12 mm (hvit LED-ring, 12–24 V) | hode Ø14, 2–4 mm | hus Ø12 × ca. 25 mm + loddeører ~8 → **~33 mm** | de øvre (z 32,5) ligger over kortet (z > 29,1): sjekk mot J7/J8-kontaktene ved y −42,3 |
| Metallknapp 16 mm POWER | hode Ø18 | Ø16 × ca. 30 + ører ~8 → **~38 mm** | ved z 24: kortets forkant ligger 30 mm bak panelet, men kortet er bare 1,6 mm tykt der (z 27,5–29,1) og knappen senteres på z 24 → ok, men hold 24 V-ledninger unna |
| EC11 encoder (20 mm D-aksel) | knott Ø30 × 17 | hus 12 × 12 × ~15 + ben | festes med mutter på gjengehalsen M7 gjennom plate + panel (4,5 mm – sjekk halslengde ≥ 7 mm) |
| PJ-392 hodetelefon | plan med platen | hus Ø8 × 11,8 | sitter i platen; panelsporet gir plass til huset |
| OLED 2,42" SSD1309-modul | aktivt område 55 × 27,5 | modulkort ca. 60 × 38 × 2, pinnerad 7-pol nede/oppe | festes på fire M2-stolper bak panelet, glasset 1–2 mm bak akrylen |
| TFT 2,4"/2,8" ILI9341 + XPT2046 | 2,4": aktivt 48,6 × 36,98 · 2,8": 57,6 × 43,2 | **vanlig modulkort 2,8" er 86 × 50 mm – 50 > innvendig høyde 43,5 → passer ikke stående**; 2,4"-modul 71 × 52 heller ikke | bruk bare skjermpanelet med FPC-breakout, eller monter modulkortet liggende bak panelet med panelet dreid 90° – avklares før bestilling |
| Panelmontert PJ-392 (AUX bak) | mutter Ø8 utvendig | hus Ø8 × 12 | |
| USB-C panelkontakter (3), hunn i panel → hann-hale | flens ca. 24 × 11, M3-skruer 18–20 mm deling | hus ~30 mm + hale 15–20 cm til J11/J12, 25–30 cm til Pi-en | |
| RJ45 panelkontakt | flens 25 × 22 | ~30 mm | |
| DC 5,5/2,5 | mutter Ø14 | ~25 mm | |
| KCD1 vippebryter | ramme 21 × 15 | 25 mm | |
| Høyttalerpoler (4 mm, isolerte) | knott Ø11–12 × 20 + isolasjonsring Ø19 × 3 utvendig | gjenge M8 × 20 + isolasjonsring innvendig + mutter | isolert fra chassiset |

## 5. Innmaten – plassering og høyder

### Hovedkort rev B (180 × 100 × 1,6)

Underside z 27,5, overside z 29,1. Kasse-plassering: x −92,3 … 87,7, y −48,3 … 51,7 (2,7 mm fri til venstre vegg, 7,3 mm til høyre vegg,
30 mm til frontpanelet, 27 mm til bakpanelet). **Fri høyde over kortet: 17,4 mm (til z 46,5).**

Høye deler (høyde over kortets overside → topp i kasse-z). Posisjon i kasse-koordinater:

| Ref | Del | Fotavtrykk | Kasse-x | Kasse-y | Høyde | Topp z | Ok? |
|---|---|---|---|---|---|---|---|
| C1, C110 | 2 × 1000 µF/35 V radial | Ø10, P5 | 41,7 / 19,7 | 44,7 / 45,4 | ≤ 16 (kjøp lavprofil) | ≤ 45,1 | ja (rettet fra én Ø13 × 25) |
| K1 | relé SRD-05VDC | 19 × 15,5 | 7,7 | 31,7 | 15,7 | 44,8 | ja (1,7 mm) |
| U6 + kjøleribbe | TPA3116 + 20 × 20 × 10 ribbe | | 31,7 | 17,7 | 1,2 + 1,5 tape + 10 | 41,8 | ja |
| L2–L5 | 12 × 12 × 8 spoler | | 65,7 / 79,7 | 22,2 / 8,7 | 8 | 37,1 | ja |
| L1 | SRP1245A | 12 × 12 | −8,3 | 21,7 | 4,5 | 33,6 | ja |
| C40, C41, C72 | 220 µF SMD | Ø10 × 10,5 | 33,7 / 47,7 / −58,3 | 31,7 / 31,7 / 35,7 | 10,5 | 39,6 | ja |
| F1 | sikringsholder 5 × 20 | 23,6 × 7,3 | −14,3 … 10,6 | 44,7 | 9,5 (med sikring) | 38,6 | ja |
| J1, J2, J3, J6 | skruterminaler 5,08 | 10,5 × 8 | −38,3 / 55,7 / 71,7 / 0,7 | 45,7 / 45,7 / 45,7 / −42,3 | 10,3 | 39,4 | ja – ledninger inn fra siden |
| J5 | 2 × 20 header + IDC-plugg | 51 × 6 | −45,3 | 11,7 … −38,4 (bx 47, by 38–90) | 8,5 + plugg 6 + kabelbrett ~5 | ~48 | **kabelen må legges flatt sideveis**; bruk vinklet IDC-plugg eller la kabelen bøye rett ved pluggen |
| J7, J8, J9, J10, J21, J23 | JST XH stående + plugg | 2,5 mm deling | front, y −42,3 | | 7 + 8 | 44 | ja |
| J4, J20, J19 | JST XH (høyre kant) | | 83,7 | −6,3 / −18,3 / −32,3 | 15 | 44 | ja |
| J13 | 1 × 14 header + flatkabel | | 26,7 … 61,5 | −42,3 | 8,5 + plugg | ~45 | ja |
| J11, J12 | USB-C på kortet | | −62,3 | −24,3 / −34,3 | 3,3 | 32,4 | kabel 15 cm til panelet |
| J15–J18 | USB-A Molex, liggende | 13,1 × 5,6 | −92,3 … −76,8 | 35,5 / 18,0 / 0,5 / −17,0 | 7 | 36,1 | vindusenter z 32,6 ✓ |
| Øvrig SMD | | | | | ≤ 2 | | |

### Raspberry Pi 4 under kortet

- Skrus fast under kortet med fire **M2,5-avstandsstykker 20 mm** i H5–H8 (kort-koordinater (21, 14), (79, 14), (21, 63), (79, 63)
  → kasse (−71,3, 37,7), (−13,3, 37,7), (−71,3, −11,3), (−13,3, −11,3)). Pi-kortet 85 × 56: kasse x −74,8 … 10,2, y −14,8 … 41,2.
- **Pi-ens overside z 7,5, underside 5,9** → 2,9 mm til bunnplaten (ingen stolper i gulvet). Portene (USB/RJ45, 16 mm høye) mot +x →
  topp z 23,5, 4 mm under hovedkortet. **SD-kortet mot venstre vegg** ved y ≈ 13, z 6: ingen luke i platemetallkassen – kortet byttes
  ved å ta av bunnplaten.
- 40-pin flatkabel (10 cm) fra Pi-headeren (x ≈ −71 … −22, y 38,5, z 7,5–16) opp rundt kortets kant til J5. 5 V fra J6 til Pi-header pinne 2/6.
- Pi-ens USB-C-strøminngang brukes ikke. En USB-A-port på Pi-en brukes til J19 (USB-kodek) med kort kabel, USB-C-panelkontakten «SERV» går med forlenger til Pi-ens egen USB-C-port (OTG – Pi-en er USB-lydkort/UAC2-gadget).
- Luftespaltene i bunnen (y −34 … 6) ligger under Pi-en.

### Ledninger

- 24 V: DC-kontakt bak → KCD1 → J1 (18 AWG). Høyttalerpoler → J2/J3 (18 AWG), ca. 25 cm.
- AUX 1/2: skjermet 2-leder fra PJ-392 bak til J4/J20 (høyre kant). Hodetelefon: 4-leder 5–6 cm fra PJ-392 i fronten til J23 (venstre front).
- Front: J7 knapper (6), J10 LED-ringer (6), J8 encoder (5), J9 OLED (5) eller J13 TFT (14-pol flatkabel), J21 strømknapp bak (2).
- Hold frontkablene i «bunten» langs frontpanelet ved z ≈ 10 (under knappene) så de ikke ligger over J5-flatkabelen.

## 6. Kjente kollisjonsrisikoer – sjekk før bestilling

1. C1 er byttet til 2 × 1000 µF Ø10 (C1 + C110) – kjøp typer med høyde ≤ 16 mm.
2. **TFT-modulkort** (50–52 mm høye) passer ikke stående bak panelet (innvendig 43,5). OLED 2,42"-modulen (38 mm) passer. Velg
   OLED, eller TFT som rent panel med FPC-adapter montert liggende.
3. **J5-flatkabelen**: stående IDC-plugg + kabel krever ~48 mm. Bruk vinklet plugg eller bøy kabelen tett.
4. **12 mm-knappene øverst** (z 32,5) rekker ~33 mm inn fra panelet, kortets JST-kontakter begynner 36 mm inn → 3 mm margin.
5. **EC11-halsen** må være ≥ 7 mm (plate 3 + panel 1,5 + mutter 2).
6. **Hodetelefonkontaktens gjenge**: gjeng M6×0,5 **etter** eloksering (eloksering fyller gjengen), eller be om maskering av hullet.

## 7. Filer og generering

| Hva | Fil(er) | Lages av |
|---|---|---|
| Kasse STEP (hele sammenstillingen, OLED/TFT) + DXF-flatmønstre per del | `platemetall/skjold_s1_avrundet/skjold_s1_platemetall_avrundet[_tft].step`, `skjold_s1_omslag_flatmonster.dxf`, `skjold_s1_panel_front_oled/tft_flatmonster.dxf`, `skjold_s1_panel_bak_flatmonster.dxf`, `skjold_s1_bunnplate.dxf`, `skjold_s1_skinne_x2.dxf` | `node tools/run.mjs .. sheet` (fra `revb_features.js` + `cad/generate_sheet_round.js`) |
| Frontplate alu: kutt + merking | `skjold_s1_frontplate_alu[_tft].dxf`, `skjold_s1_frontplate_alu_merking.dxf` | `python3 tools/frontplate_metall.py` |
| Lasermerking kasse | `marking/skjold_s1_merking_bunnplate.dxf`, `marking/skjold_s1_merking_bakpanel_revb.dxf` | designpakken + `python3 tools/merking_bakpanel.py` |
| Printet frontplate (reserve, to farger) | `print/skjold_s1_frontplate_*.3mf/.stl` | `node tools/run.mjs .. print` |
| CNC-utgave (reserve) | `cnc/*.step` | `node tools/run.mjs .. cnc` |
| Printet kasse (gammel, 215 mm) | `../stl/v2_*_revb*.stl` | `python3 ../tools/build_revb.py` |
| 3D-render | `render/pultforsterker_*.png` | `python3 tools/render_textures.py && python3 tools/render3d.py` |

Oppsett: `cd tools && npm install` (three, manifold-3d, fflate, @fontsource/sora, @fontsource/ibm-plex-mono); Python trenger `fonttools`, `pillow`, `numpy`, `playwright`.
STEP-generatorene skal melde `bad 0`.

### Bestilling hos PCBWay

1. **Sheet Metal Fabrication:** last opp `skjold_s1_platemetall_avrundet.step` (eller `_tft`) + DXF-ene. 5052-H32 1,5 mm, bøyeradier som
   over (skriv R7,5 innvendig for omslaget), bead blast + black anodize, PEM-innsatser som listet. Laser marking: bunn- og
   bakpanel-DXF (lag MARKING).
2. **Sheet Metal / flat part:** frontplaten `skjold_s1_frontplate_alu.dxf`, 3 mm 5052-H32, samme overflate, 6 × FH-M3-8 studs fra
   baksiden, gjenging M6×0,5 i Ø5,5-hullet etter eloksering (eller maskering). Laser marking: `skjold_s1_frontplate_alu_merking.dxf`.
3. Akryl 2 mm røyksort 61,6 × 37,6 R1,3 (laserkuttes lokalt eller bestilles som «acrylic laser cutting»).
