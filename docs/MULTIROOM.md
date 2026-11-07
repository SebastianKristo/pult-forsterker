# Romlig stereo, synkron multiroom og trådløs sub

Tre lydfunksjoner som kjører i Skjold-daemonen uten Lyrion. Alle lagres som Skjold-plugins
(`xtc` og `sync` i `state.settings.plugins`) og deles mellom web og apper via `POST /api/plugins/{id}`.
CamillaDSP-blokkene bygges av `pi/skjold_sync/dspblocks.py` og hektes på i `dsp_config()`.

## 1. Romlig stereo (krysstalekansellering, `pi/skjold_xtc.py`)

- Geometri: høyttalerspenn og lytteavstand gir veiforskjell `d` (samples) og krysstale-gain `g`
  (avstandsforhold × hodeskygge 0,55).
- Atal–Schroeder-rekursjon, 3 iterasjoner: `H_direkte = δ + g²z⁻²ᵈ + g⁴z⁻⁴ᵈ`, `H_kryss = −g z⁻ᵈ − g³z⁻³ᵈ`.
  Korreksjonsleddene båndbegrenses til 200 Hz–6 kHz (regularisering: bass og diskant røres ikke).
- 1024-taps FIR lagres som `xtc_direct.raw`/`xtc_cross.raw` (FLOAT32LE) i `/var/lib/skjold/xtc/` og brukes som
  `Conv`-filtre i egen «xtc»-blokk (Mixer 2→4, fire Conv, Mixer 4→2) etter EQ og loudness.
- Innstillinger: av/på, styrke 0–100 %, spenn 20–200 cm, avstand 30–200 cm. «Lyttetest» (`POST /api/xtc/test`)
  spiller rosa støy som vandrer venstre → midt → høyre.
- UI: Lyd → «Romlig stereo».

## 2. Synkron multiroom (`pi/skjold_sync/`)

| Fil | Innhold |
|---|---|
| `clock.py` | NTP/PTP-lignende synk: 4 tidsstempler → offset + RTT. Beste halvdel (lavest RTT) av siste 64 målinger, lineær regresjon gir offset **og** drift (ppm). UDP 5005. |
| `proto.py` | RTP-lignende pakker (`SKAU`, sekvens, rammenummer, avspillingstid i ledertid, kanaler, rate) og jitterbuffer sortert på rammenummer; tap gir stillhet, duplikater forkastes. `fetch()` resampler asynkront (lineær interpolasjon med forhold 1+drift). |
| `engine.py` | `Leader` sender 10 ms-blokker med avspillingstid = første blokk + buffer (100–500 ms) til følgerne (UDP 5004). `Follower` synker klokken hvert 250 ms og rendrer for en gitt lokal DAC-tid. `python3 -m skjold_sync.engine leader <ip,ip> <buffer_ms>` / `follower <leder-ip> <rom-ms>` bruker arecord/aplay. |
| `dspblocks.py` | CamillaDSP-blokker: lederens egen utgang forsinkes med bufferen (`sync_delay`), pluss per-rom forsinkelse. |

Daemonen starter motoren (`sync_apply`) ved oppstart og ved `POST /api/sync`. UI: Grupper og surround → «Synk-motor».

## 3. Trådløs subwoofer

- En Core/Node settes til «Er sub» (for et rom): mono-sum L+R, LR4 lavpass (24 dB/okt) på delefrekvensen,
  fase 0/180° (invertert Gain), finjustering 0–20 ms (Delay) og nivå −15…+6 dB.
- Hovedenheten settes til «Har sub»: LR4 høypass 60–150 Hz på begge kanaler.
- Sub-enheten er følger i synk-motoren, så lyden kommer fram samtidig; resten justeres med finjusteringen.
- UI: Grupper og surround → Sub (delefrekvens, fase, finjustering, nivå, «Test»).

## 4. Bass management – automatisk sub-innstilling (`pi/skjold_bassmgmt.py`)

Under Grupper og surround → «Bass management (mål med telefonen)» på hovedenheten:

1. Velg sub-enheten. Skjold leser sub-ens nåværende fase/finjustering/nivå og setter den nøytralt (0°, 0 ms, 0 dB).
2. Hold telefonen i lytteposisjonen og trykk «Mål». Hovedenheten og sub-en spiller hver sin sveip i hvert sitt
   tidsvindu (samme timing som høyttalerplassering).
3. Skjold regner ut impulsresponsen for hver, og prøver fase 0/180° og relativ forsinkelse −20…+20 ms i 0,1 ms-steg.
   Den kombinasjonen som gir flattest summert respons rundt delefrekvensen (½–2 × delefrekvensen) vinner.
   Nivået settes fra snittnivået i overgangsbåndet (−15…+6 dB i 0,5 dB-steg).
4. Kommer sub-en for tidlig, forsinkes sub-en (finjustering). Kommer den for sent, forsinkes hovedenheten
   (legges til rommets forsinkelse), fordi sub-ens forsinkelse ikke kan være negativ.
5. Kurven før/etter vises; «Bruk» sender verdiene til sub-en (`/api/sync`), «Avbryt» setter tilbake det som var.

API: `POST /api/bass/start {sub}`, `POST /api/bass/analyze` (opptaket), `POST /api/bass/apply`, `POST /api/bass/avbryt`.

## 5. AirPlay 2 til flere rom (`pi/skjold_airplay.py`)

Hver Skjold er sitt eget AirPlay 2-mål (shairport-sync + nqptp). På iPhone/Mac velger du flere høyttalere i
AirPlay-menyen samtidig, og Apple holder dem synkrone selv – Skjold-grupper trengs ikke for dette.

- **Navn**: AirPlay-navnet er enhetens navn i Skjold («Stue», «Kjøkken»), satt automatisk når navnet endres.
- **Unik ID**: iPhone skiller høyttalere på AirPlay-ID-en. shairport-sync lager den fra MAC-adressen, så klonede
  enheter (samme Proxmox-mal, kopiert SD-kort) kan få samme ID og vises som én. Ved oppstart setter Skjold
  `airplay_device_id` i `general`-blokken i `/etc/shairport-sync.conf` fra en hash av `/etc/machine-id` + MAC +
  vertsnavn (48 bit, «lokalt administrert»), og starter shairport-sync på nytt bare hvis ID-en endret seg.
  Kloner du en maskin: kjør `rm /etc/machine-id && systemd-machine-id-setup` på klonen.
- **Volum**: volumet fra iPhone følger Skjold-volumet per rom.
- **Begrensning**: en Skjold-gruppe er ikke ett samlet AirPlay-mål. Velg rommene enkeltvis på iPhone, eller spill
  til ett rom og bruk Skjold-synk derfra (da styrer Skjold synkroniseringen, ikke Apple).

## Tester (`pi/tests/test_xtc.py`, `test_sync.py`, `test_plugins.py`)

Målt lokalt (spenn 50 cm, avstand 60 cm):
- XTC: ekstra kanalseparasjon i 500–3000 Hz > 35 dB (krav > 10 dB), maks løft ved øret +0,13 dB (krav < 3 dB).
- Klokke med eksponentiell Wi-Fi-jitter (snitt 4 ms hver vei) og 80 ppm drift: feil < 1 ms etter 64 målinger.
- To prosesser over loopback (leder med 137 ms klokkeoffset): klokkefeil ≈ 0,001 ms, krysskorrelasjon av
  avspilt signal mot fasit: 4 samples ≈ 0,08 ms.
- Pakkeomstokking, tap og duplikater i jitterbufferen; YAML for sub/høypass/forsinkelse valideres.
- Bass management (`test_lyd_funksjoner.py`): simulert hoved+sub med LR4 finner forsinkelse (±0,3 ms), invertert
  fase og −6 dB nivå, og forsinker hovedenheten når sub-en kommer for sent. AirPlay: ID-er er unike per MAC,
  og `airplay_device_id` settes inn/oppdateres i repoets `shairport-sync.conf` uten å endre resten.

## Ikke testet ennå

- Ekte Wi-Fi mellom flere Pi-er, og latens i aplay/ALSA (kompenseres manuelt med per-rom forsinkelse).
- Lytting med XTC på ekte høyttalere; sub-delefilter mot ekte subwoofer.
- Bass management med ekte telefonmikrofon og sub over Wi-Fi; AirPlay 2 med flere ekte Skjold-enheter samtidig.
- iOS/Android-appene har ikke fått egne skjermer – bruk web-UI (samme API).
