# Sjekkliste før du bestiller hovedkortet (rev B)

Kortet er fryst etter ruting (commit `9ae80c2`) og de ferdige produksjonsfilene er gransket uavhengig
(gerber/DFM og BOM/CPL – se `GRANSKNING_REV_B.md`). Det som står her er det **du** bør se på selv før du trykker
«bestill». Bruk 20–30 minutter. Sett et kryss per punkt.

## A. Åpne kortet i KiCad (`pcb/ki_pultforsterker_main.kicad_pcb`)

- [ ] **A1. DRC i KiCad gir 0 ukoblede og 0 klaringsfeil.** `Inspiser → Design Rules Checker → Run DRC`. Det som er
      igjen skal være: `courtyards_overlap` (6), `starved_thermal` (11), `silk_*`, `lib_footprint_issues` (199). Dukker det opp
      `unconnected_items`, `clearance`, `hole_near_hole` eller `copper_edge_clearance`, er noe endret etter frysen – ikke bestill.
- [ ] **A2. Strømveien ser ut som på tegningen.** Følg med «Highlight net» (`` ` ``-tasten): `24V_IN` fra J1 til begge
      sikringsklipsene F1 (bredt spor øverst), `24V_F` til Q11 (P-MOSFET), `VIN24` under kortet til reléet K1 pinne 3 og til
      bucken U1, `24V_AMP` fra K1 pinne 1 til C40/C41 og TPA3116 (U6), `5V` fra spolen L1 til C8–C11 og J6 («5V PI»).
      Ingen av disse skal gå gjennom tynne (0,2 mm) spor.
- [ ] **A3. Reléets pinner.** K1: pinne 2/5 = spole (til Q8 og 5 V), pinne 1 = COM (`24V_AMP`), pinne 3 = NO (`VIN24`),
      pinne 4 = NC (tom). Hold musen over padene og les nettnavnet.
- [ ] **A4. TPA3116 (U6) er riktig vei.** Pinne 1 øverst til venstre når kortet ses ovenfra (silketrykk-prikken). Pinne
      1–4 er ikke brukt/GND-siden, pinne 17–19 og 31–32 er `24V_AMP`, utgangene 21/23/27/29 går til spolene L2–L5.
- [ ] **A5. Pi-headeren J5.** Pinne 1 (firkantet pad) er nederst til venstre sett ovenfra, pinne 2 og 4 = `5V`,
      pinne 6 = GND, pinne 12 (GPIO18) = `I2S_BCK`, 35 = `I2S_LRCK`, 40 = `I2S_DIN`. Sammenlign med `README.md` → GPIO-kart.
- [ ] **A6. USB-C J11/J12 og USB-A J15–J18 stikker ut riktig vei** (3D-visning, `Alt+3`): åpningene peker mot kortkanten,
      ikke innover.
- [ ] **A7. Festehull.** H1–H4 (Ø3,2) i hjørnene har ikke kobber rundt seg; H5–H8 (Ø2,7) treffer Pi 4-hullene
      (58 × 49 mm, 3,5 mm fra Pi-kanten – mål i 3D-visningen).

## B. JLCPCB – gerber

- [ ] **B1.** Last opp `pcb/produksjon/ki_pultforsterker_main_gerber.zip`. Forhåndsvisningen skal vise 180 × 100 mm,
      2 lag, og **ingen** røde «missing layer»-advarsler. Alle tolv filer (inkl. `.drl` og `-job.gbrjob`) skal være gjenkjent.
- [ ] **B2. Innstillinger:** 2 lag, 1,6 mm, **2 oz ytre kobber** (anbefalt – høyttalersporene er 0,4–0,5 mm på deler av
      veien; 2 oz gir ~65 % mer strøm for samme temperatur), HASL lead-free eller ENIG, grønn/svart, 5 stk.
      «Remove order number: Specify location» hvis du vil ha JLC-nummeret på et bestemt sted (det ligger ikke en
      `JLCJLCJLCJLC`-tekst på kortet, så velg «Yes»/«No» etter smak).
- [ ] **B3.** Snu til bunnsiden i forhåndsvisningen: bare spor og jordplan, ingen komponenter (alt SMD er på toppen).

## C. JLCPCB – montering (PCBA)

- [ ] **C1.** Velg «PCB Assembly», **Top side**, 2 stk (3 kort kommer umontert som reserve/håndlodding).
- [ ] **C2.** Last opp `ki_pultforsterker_main_bom.csv` og `ki_pultforsterker_main_cpl.csv`. **THT-delene er med vilje
      utelatt** (de står i `ki_pultforsterker_main_tht_handlodding.csv` og loddes selv).
- [ ] **C3. Delelisten:** les beskrivelsen JLCPCB viser per linje og sammenlign med «Comment»-kolonnen (verdi + pakke).
      Alle linjer med kode er verifisert mot lcsc.com/jlcpcb.com i granskningen, men lager endrer seg. Mangler en del,
      velg erstatning med **samme verdi, spenning og pakke**; ikke la JLCPCB «auto-velge».
- [ ] **C4. Linjer uten kode** (JLCPCB spør): U14 = SN74LVC1G14DBVR (SOT-23-5), D1 = SMBJ28A (SMB), D5 = BZT52C12
      (SOD-123), Q11 = P-MOSFET TO-252 ≥ 40 V ≥ 10 A (f.eks. AOD4185). Velg selv, ikke hopp over.
- [ ] **C5. Rotasjon/polaritet i forhåndsvisningen** («Component Placement»): kontroller pinne-1-prikken på **alle
      IC-er** (U1–U14), katodestreken på D1/D2/D4/D5–D11, og «+» på de tre store elektrolyttene C40/C41/C72 mot
      silketrykkets «+». CPL-filen har JLCPCBs vanlige rotasjonskorreksjoner (SOT-23 +180°, SOIC/TSSOP/QFN +270°,
      elektrolytter +180°), men JLCPCB viser alltid resultatet – stol på bildet, ikke tallet. Roter i deres editor om nødvendig.
- [ ] **C6.** U6 (TPA3116, HTSSOP-32 med kjøleflate **opp**): bekreft at JLCPCB ikke klager på manglende paste under
      brikken – det er riktig, kjøleribben limes på toppen.

## D. Kjøp selv (ikke i PCBA)

- [ ] **D1.** Alt i `ki_pultforsterker_main_tht_handlodding.csv`: skruterminaler J1–J3/J6, JST XH-kontakter, Pi-header J5
      (2×20 **hann**), J13, sikringsklips F1 + 5 A-sikring 5×20, C1/C110 1000 µF/35 V Ø10 (≤ 16 mm høye), relé K1 (SRD-05VDC),
      USB-A J15–J18, 12,288 MHz-oscillator hvis JLC mangler den.
- [ ] **D2.** Kjøleribbe 20 × 20 × 10 mm + termisk tape, NTC 10 k (B 3950) med ledning til J24, kabelsett (JST XH 3P/5P/6P,
      USB-C panelkabler – se `kabinett/skjold-s1/`).

## E. Når kortene kommer – før Pi og høyttalere kobles til

- [ ] **E1.** Visuell kontroll med lupe: U1, U6, U13 (QFN) og USB-C-kontaktene for loddebroer.
- [ ] **E2.** Multimeter, kortet strømløst: motstand mellom `24V_IN` (J1+) og GND skal være > 10 kΩ (ikke 0),
      mellom `5V` (J6+) og GND > 1 kΩ, mellom `3V3` (J22 pinne 5) og GND > 100 Ω. 0 Ω = kortslutning, ikke sett på strøm.
- [ ] **E3.** Relé: uten strøm skal det være **brudd** mellom K1 pinne 1 og 3.
- [ ] **E4.** 24 V på J1 med strømbegrensning 0,5 A (labforsyning) – mål: 5,0–5,1 V på J6, 3,3 V på J22 pinne 5,
      0 V på J10 pinne 1 (`5V_SW` av). Strømtrekk < 100 mA uten Pi.
- [ ] **E5.** Først nå: Pi inn, start, slå på fra HA → `5V_SW` 5 V, −5 V på C16, 24 V på C40. Høyttalere på, volum 15 %.

Resten av oppstartsprosedyren står i `pcb/README.md` («Første oppstart – sjekkliste») og `pi/README.md`.
