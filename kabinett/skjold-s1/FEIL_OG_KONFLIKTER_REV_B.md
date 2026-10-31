# Skjold S1 – dimensjonsfeil og konflikter i kabinettet (mot hovedkort rev B)

Til den som jobber med kabinettet (`revb_features.js`, `SPESIFIKASJON_KABINETT.md`, `cad/`). Funnene kommer fra en
uavhengig mekanisk granskning (31.10.2026) av kortet `pcb/ki_pultforsterker_main.kicad_pcb` (fryst, bestilt-klar) mot
kabinettfilene. **Kortet endres ikke mer** – alt under må løses i kabinettet eller i kabling/valg av deler.

Koordinater: kasse (x, y, z) som i spesifikasjonen; kort (bx, by) med origo i kortets øvre venstre hjørne sett ovenfra,
bakkanten er by = 0. Omregning: `x = bx − 92,3`, `y = 51,7 − by`. Kortets overside ligger på z 27,5 (se punkt 8 – reelt 28,0
med 25 mm stolper på bunnplaten). Kortet er 180 × 100 mm, hull H1–H4 ved kasse (−88,3/83,7, −44,3/47,7).

## A. Må rettes (kolliderer)

| # | Hva | Mål | Krav / forslag |
|---|---|---|---|
| 1 | **USB-C-panelkontaktene PC 1 / PC 2 (bak, x 15, z 34 / 24) treffer kortet og C110.** Hus ~30 mm dypt fra panelets innside → innerenden ved y ≈ 48,5, men kortkanten er y 51,7 (3,2 mm inn over kortet, bx 100,8–113,8). PC 2 (z 19,5–28,5) treffer selve kortet (z 27,5–29,1); PC 1 (z 29,5–38,5) treffer C110 (bx 107–117, by 1,3–11,3, 16 mm høy, topp z 45). «Pi»-kontakten (z 14) går klar under kortet. | Fri dybde bak panelet over kortkanten: **27 mm** (y 51,7 → 78,5) | Mål faktisk dybde på panelkontakten. Alternativer: (a) panelkontakt ≤ 26 mm dyp, (b) legg alle tre USB-C **under kortnivå** (senter z ≤ 22: f.eks. z 20, 9 og én ved siden), (c) flytt dem til en sone uten kort bak: finnes bare ved bx 118–129 (x 25,7–36,7), 11 mm bred. |
| 2 | **Høyttalerpolene L+/L− (x −82,8 / −63,8, z 24) blokkerer USB-C-pluggene i J11/J12 på kortet.** J11/J12 sitter i kortets bakkant ved x −78,8 / −67,3, z 29,1–32,4 med åpningen mot bakpanelet. Polenes M8-gjenge (20 mm) + mutter (Ø13) + Ø19-ring fyller y 58,5–78,5, z 14,5–33,5, x ±9,5 rundt hver pol. En USB-C-hannplugg er 25–35 mm lang → y 51,7–86: rett inn i mutter/gjenge, og rett i bakpanelet (27 mm fri). | Overlapp i x: J11 (−78,8) ligger mellom L+ (−82,8) og L− (−63,8) | **Speil bakpanelet**: poler til høyre (ved J2/J3, kortets skruterminaler x 55,7 / 71,7), DC/KCD1/RJ45 til venstre ved J1 (x −38,3) – eller flytt polene ≥ 25 mm vekk fra x −85 … −60. Uansett: bruk **90°-vinklede USB-C-haler** (rette plugger trenger > 27 mm). |
| 3 | **USB-A-vinduene i venstre side er speilvendt (for/bak).** `left:[-32.1,-14.6,2.9,20.4]` har feil fortegn, og tabellen i spesifikasjonen bruker pad 1 (3,5 mm feil) i stedet for kontaktens senter. Kortets USB-A-sentre (skjermpinner ved by 13,13/26,27 …) ligger ved by 19,7 / 37,2 / 54,7 / 72,2 → **y +32,0 / +14,5 / −3,0 / −20,5**. Feil 11,7 mm → ingen port treffer vinduet. | | `left:[32.0,14.5,-3.0,-20.5].map(y=>r(y,33,14.8,9))`. Høyde: kontakt z 29,1–36,1 (29,6–36,6 med z 28,0), vindu i dag 28,6–36,6 → senter z 33, høyde 9 gir margin. Rett tabellen i spesifikasjonen (y-kolonnen). |
| 4 | **POWER-knapp Ø16 (x −76, z 24) vs. kortets forkant / J23.** Hus Ø16 (z 16–32) × 30 mm → innerende y −48,5; kortkanten er y −48,3 → **0,2 mm margin**, og huset dekker kortets z-nivå. Loddeørene (~8 mm) når y −40,5, rett under J23 (bx 13–26,5, by 94 → y −42,3), som stikker 1,5–2 mm ned under kortet (z 25,5–27,5). | Fri dybde foran kortets forkant: **≤ 30 mm** inkl. ører | Mål knappen. Hus + ører må være < 30 mm, ellers: senk knappen (senter z ≤ 19,5 – men da kolliderer den med hodetelefonjacken ved z 8 → flytt jacken), eller bruk en kortere knapp (16 mm «short body», ~20 mm). J23 kan ikke flyttes. |
| 5 | **KCD1 vippebryter (x 78, z 24).** Kropp z 17,5–30,5 omslutter kortets z 27,5–29,1. Kropp + terminaler ≈ 27 mm → y 51,5 = kortkanten; med faston-hylser/ledning (+6–8 mm) går den 6–8 mm inn over kortets høyre bakhjørne (J3 bx 161,5–171,5, H2 ved bx 176/4). | | Senk KCD1 til senter **z ≤ 20** (topp ≤ 26,5 < 27,5) så terminalene går under kortet, eller bruk loddeterminaler med ledning bøyd rett ned. |
| 6 | **12 mm-knappene øverst (x 22 / 38, z 32,5) vs. J9.** Hus 25 mm → y −53,5 (5,2 mm fri), men loddeørene (~8 mm) når y −45,5. J9-huset (bx 101–114,5, by 97,9 → y −46,2) → **−0,7 mm** for knappen ved x 22 (bx 114,3). Spesifikasjonens «3 mm margin» er regnet til pinnelinjen, ikke huskanten. | | Mål knappen; ørene må ende før y −46,5 – eller flytt knappen ved x 22 til **x 25–26** (3–4 mm mot høyre). |
| 7 | **Kjøleribbe 15 mm (nevnt i README «Sikkerhet») treffer lokket.** 29,1 (kortets overside + TPA3116) + 1,2 (brikke) + 1,5 (tape) + 15 + 1 (pute) = 47,8 > 46,5 (lokkets innside). | | **10 mm ribbe** (gir 41,8 – OK). Maks 12 mm hvis lokket skal brukes som kjøleflate med 2 mm pute. |

## B. Bør rettes (tall som ikke stemmer)

| # | Hva | Mål | Forslag |
|---|---|---|---|
| 8 | **Stolpehøyde.** 25 mm stolper på bunnplaten (overside z 3,0) gir kortets underside på **z 28,0**, ikke 27,5 som alle z-verdier er regnet fra (skinnene RAILZ 15,5 + 12 gir 27,5). | +0,5 mm på alt over kortet | Bruk **24,5 mm** stolper, eller oppdater alle z-verdier (C1-topp 45,6, USB-A-topp 36,6 = vinduskant, ribbe 42,3). |
| 9 | **40-pin flatkabel Pi → J5 er for kort (10 cm).** Pi-headeren ligger under kortet ved by 13–18 (kasse y 38,5), bx 24,6–75,4. J5 står med langsiden langs by 40–88 ved bx 47–49,5; IDC-kabelen går ut sidelengs, 51 mm bred. Korteste vei: Pi-header → bakkanten (15 mm) → opp og over J1 (10,3 høy) og over USB-C-pluggen i J12 → fram til by 38 → 90°-fold (+25 mm) → J5: **≈ 115–120 mm**. Over lokket: J5 + IDC = 40,5, foldet bånd ≈ 43–44 (< 46,5) – kun uten strekkavlaster. | | **15–20 cm kabel**, én fold, IDC-plugg uten strekkavlaster på J5-siden. |
| 10 | **DC-kontakt (x 44, z 34).** ~25 mm dyp → y 53,5; C1 (Ø10, 16 høy) begynner ved by 2 → **3,8 mm** klaring. | | OK, men loddeører/ledning må bøyes sidelengs. Vurder z 36 for 2 mm mer. |
| 11 | **Pi-ens USB3-blokk (bx 84,5–104,5, by 32,9–46,2, topp z 23,4) under kortet.** Kortets J6 er flyttet (se C) så ingen THT-pinner står over blokken lenger; K1-pinnene (relé) står over RJ45 (13,7 høy) med 3,5–4 mm margin. | 4,0 mm fri høyde kort–USB3-blokk | Klipp alle THT-pinner i dette området plant, Kapton på USB3-blokken. **Ikke** bruk Pi-kjøleribbe > 15 mm på SoC-en (treffer J5-pinnene). |

## C. Kortfakta som er endret siden spesifikasjonen ble skrevet

- **J6 (5 V-skruterminal)** står nå ved kort (82, 43) rotert 270°: pinner ved (82, 43,0) og (82, 48,1) → kasse (−10,3, 8,7) og (−10,3, 3,6); kroppen 8 × 10,6 mm, ledningsinngang mot +x (høyre). Tidligere (46/86, 43). 5 V-kabel til Pi-header pinne 2/6: **≈ 10 cm**.
- **F1 sikringsholder** er nå Littelfuse 111-klips (4 runde hull Ø1,3 ved bx 78/83 og 93/98, by 7) – samme plass, 20 mm mellom klipsene, høyde 9,5 med sikring. Tabellens «23,6 × 7,3» → **20 × 6**.
- **C32** er snudd 180° (bare rutingsteknisk).
- **J11/J12** (USB-C på kortet) ved bx 13,5 / 25,0, by 3,9 → kasse x −78,8 / −67,3, y 47,8, åpning mot bakpanelet, hus z 29,1–32,4. Uendret, men se A2.
- Kortets høyeste deler: C1/C110 (1000 µF, ≤ 16 mm) topp z 45,1; K1 relé 15,5 → 44,6; C40/C41/C72 10,5 → 39,6; L1/L2–L5 ≈ 6–8 → 35–37; JST + plugg → 44; ribbe 10 mm → 41,8. Alle < 46,5.

## D. Ikke verifisert (må måles på de fysiske delene)

Dybde på USB-C-panelkontakter, DC-jack, KCD1, 16 mm POWER-knapp og 12 mm-knappene (inkl. loddeører) – tallene over er
spesifikasjonens anslag. Mål dem før panelet lages, og legg målene inn i `SPESIFIKASJON_KABINETT.md`.

## E. Sjekkliste før kassen produseres

- [ ] Bakpanel speilet eller poler flyttet (A2); USB-C-stakk under kortnivå eller kortere kontakter (A1)
- [ ] `left:` i `revb_features.js` rettet til `[32.0,14.5,-3.0,-20.5]`, z 33, høyde 9 (A3); render sjekket mot `pcb/produksjon/board_top.png`
- [ ] POWER-knapp, KCD1 og 12 mm-knapper: målt dybde < fri dybde (A4–A6)
- [ ] 10 mm ribbe (A7); stolper 24,5 mm eller z-tabell oppdatert (B8)
- [ ] 15–20 cm flatkabel (B9); 90°-USB-C-haler
- [ ] Kollisjonskontroll på nytt i `render3d.html`/CAD med kortets nye J6/F1 (C)
