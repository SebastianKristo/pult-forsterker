# Romlig lyd og høyttalerplassering

## Virtuell surround fra to høyttalere (`pi/skjold_spatial.py`)

Plugin `xtc`, `mode: "surround"` (Lyd → Romlig lyd). Hele kjeden er én symmetrisk 2×2 FIR-matrise
(1024 taps, to unike filtre) i CamillaDSP – samme 2→4→2-oppsett som «Romlig stereo».

1. **Virtuelle høyttalere:** fronter i ±(fysisk vinkel + bredde·(60° − fysisk)), ambiens bak i ±110°
   (`(V − 0,5·H)`, 12 ms forsinket, lavpass 7 kHz).
2. **HRTF:** innebygd kulehode-modell (Brown & Duda 1998: hodeskygge + Woodworth-ITD). Ingen SOFA-fil;
   glatt og robust, men uten pinna-signaler – foran/bak-skillet er svakere enn med en målt HRTF.
3. **Krysstalekansellering:** `skjold_xtc` (Atal–Schroeder, 200 Hz–6 kHz). Kontra-leddene skaleres så «virtuell =
   fysisk» gir nøyaktig vanlig stereo; under 150 Hz går bassen urørt.
4. **Sitteplass:** `offset_cm` gir kanalvis forsinkelse og nivå (Delay/Gain i CamillaDSP). «Finn plassen min med
   mobilen» måler ankomstforskjellen V/H og regner ut forskyvningen.

Innstillinger: `strength` (XTC), `width`, `surround`, `span_cm`, `dist_cm`, `offset_cm`.
Hodetrom: filtrene normaliseres så verste tilfelle (V = ±H) aldri går over 0 dB.
CPU (anslag): 4 × 1024-taps FFT-konvolusjon ≈ 3–5 % av en Pi 4-kjerne, 8–12 % på Pi 3.

## Automatisk plasseringskalibrering (`pi/skjold_placement.py`)

Plugin `placement`. Høyttalerlisten: navn, enhet (tom = denne), kanal (V/H/begge) og rolle (L/C/R/Ls/Rs).
Hver høyttaler spiller en 1 s logaritmisk sweep (200 Hz–16 kHz) i luker på 1,6 s; opptaket dekonvolveres (Farina),
første topp over 50 % av maks per luke = direkte lyd (parabolsk interpolasjon gir under-sample-presisjon).

* **Mobil i lytteposisjon** – `POST /api/placement/start`, ta opp `record_s`, `POST /api/placement/analyze?n=&skip=`.
  Gir relative ankomsttider → forsinkelse og nivå per høyttaler (`align`). Lokale kanaler i stereoparet gir også
  sitteplass (`offset_cm`).
* **Enhetsmikrofoner** – `POST /api/placement/devices` (minst 3 enheter med mikrofon, `SKJOLD_MIC_DEV`): alle spiller
  etter tur og alle tar opp. Toveis tider opphever klokkeforskjeller, `d_ij = c·((T_ij + T_ji) − (T_ii + T_jj))/2`,
  og klassisk MDS gir 2D-posisjoner. Speiling avgjøres av høyttaleren med rolle L, rotasjon av C (ellers snittet).
  Har du målt med mobilen først, plasseres lytteren med TDOA-multilaterasjon. Resultat: vinkler, ITU-R BS.775-avvik
  per rolle og forsinkelse/nivå fra avstand.
* `POST /api/placement/apply` – lokale kanaler → `placement.trims` (Delay/Gain i CamillaDSP); andre enheter →
  `room_delay_ms` i synk-motoren der (+ nivå i deres `placement`).

Tidsluker på tvers av enheter bruker veggklokka: med synk-motoren (skjold_sync) er feilen under 1 ms, med bare NTP
noen få ms – det gir tilsvarende feil i forsinkelsen mellom enheter. Mellom V/H på samme enhet er målingen eksakt.
