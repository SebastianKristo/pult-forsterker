# Brief til Claude Design: plass til koblingskortet inne i Skjold S1 rev F

Kopier teksten under inn i Claude Design sammen med modellen av S1-kassen.

---

**Oppgave:** Lag en så smal som mulig plass og holder inne i Skjold S1 rev F for et lite koblingskort (stripekort).
Kortet samler ledningene fra frontpanelet: fire kildeknapper, av/på-knappen, LED-ringene og volumhjulet (EC11). Fra kortet
går 14 Dupont-ledninger til Raspberry Pi-ens GPIO-list.

**Kortet**
- Mål: **61,0 × 30,5 × 1,6 mm** (24 × 12 hull med 2,54 mm deling, bakelitt). Ingen skruehull.
- **Komponentsiden** har disse delene:
  - fem stående JST XH-kontakter, ca. 10 mm høye. Pluggene settes rett inn ovenfra, vinkelrett på kortet.
  - en ULN2803A i DIP-18-sokkel, ca. 8 mm høy
  - 14 enkle stifter (2,54 mm) med Dupont-hylser, ca. 23 mm høye med hylse
- **Kobbersiden:** loddepunkter og avklippede bein, opptil 2 mm. Kobberet fører **+24 V og GND**. Ingen metall nærmere enn
  2 mm, og en skillevegg i plast mot kassen.
- Varme: nesten ingen (LED-ringene trekker til sammen under 0,1 A).

**Montering (smalest mulig)**
- Kortet skal **stå på høykant**. Den lange kanten (61 mm) ligger vannrett, og den korte (30,5 mm) står opp, så det tar
  minst mulig gulvplass. Innvendig fri høyde i S1 er 43,5 mm, så det er god plass i høyden.
- Holderen er to stående **spor** (U-skinner) som griper de korte kantene:
  - Spor 1,8 mm bredt og 3 mm dypt.
  - En liten **klikklås eller tapp** øverst holder kortet nede.
  - Holderen festes til bunnplaten med 2 × M3 (eller VHB-tape hvis det ikke er plass til skruer).
- Holderen skal tegnes for 3D-print i PETG, uten støtte.
- **Fri sone:**
  - **Foran komponentsiden: minst 28 mm**, så XH-pluggene og Dupont-hylsene kan settes i og ledningene får bøye seg.
  - **Bak kobbersiden: minst 4 mm**, inkludert plastveggen.
- Fotavtrykket blir ca. **65 × 8 mm** for holderen, pluss fri sone foran. Den frie sonen kan deles med kabelføring.
- Kortet må kunne tas ut ovenfra uten å skru ut noe annet. La det være 12 mm over kortet til fingrene.

**Plassering**
- Helst langs **innsiden av frontpanelet** eller en sidevegg, mellom frontpanelet (knappene, volumhjulet) og Raspberry
  Pi-ens GPIO-list.
  - Ledningene fra knappene er 15–20 cm.
  - Dupont-ledningene til Pi-en er 20 cm.
- Komponentsiden skal vende mot den åpne delen av kassen (mot Pi-en). Da settes pluggene inn fra den siden.
- Hold det unna 24 V-strømledningene til forsterkeren (TPA3116) og lydkablene fra PCM5102, minst 15 mm.
- Ingen kollisjon med knappehusene bak frontpanelet:
  - 12 mm-knapper ca. 33 mm dype
  - 16 mm power-knappen ca. 38 mm dyp
  - EC11 ca. 15 mm pluss knott

**Leveranse**
- Holderen som STL og STEP.
- Et bilde av plasseringen i kassen, med fri sone vist som gjennomsiktig boks.
- Målsatt skisse: avstand til frontpanel, sidevegg og Pi.

---

Tegningen av kortet: `stripekort.png`. Ledningene til Pi-en: `pi_kabler.png`.
