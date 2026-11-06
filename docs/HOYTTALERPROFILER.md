# Skjold Sertifisert – høyttalerprofiler

EQ-profiler for passive tredjepartshøyttalere. Du kan måle høyttalerne selv, eller hente en profil som andre Skjold-eiere har delt.

| Del | Fil |
|---|---|
| Måling, gating, PEQ-tilpasning, score, sertifisering, DSP-regler, cache og klient | `pi/skjold_speakerprofiles.py` |
| Daemon-API og CamillaDSP-kjede | `pi/ki_amp_daemon.py` (`/api/speakers*`, `speaker_filters()`) |
| Profildatabase (Cloudflare Durable Object `Hoyttalere`) | `skjold/sky/src/index.js` (`/hoyttaler/*`) |
| Web-UI | `skjold/app/src/screens/speakers.tsx` (under Lyd og i Plugins → Skjold Sertifisert) |
| iOS | `skjold/ios/Skjold/UI/V4Speakers.swift` (Lyd → Høyttalerprofil) |
| Android | `skjold/android/.../SpeakerView.kt` (Lyd → Høyttalerprofil) |

## Måling

1. Skjold spiller den samme logaritmiske sweepen som romkorreksjonen bruker (6 s, 20 Hz–20 kHz).
2. Mikrofonen tar opp. Det finnes to typer måling:
   - **Gated** (≈ 1 m på aksen, i høyde med diskanten, minst 1 m fra vegger og gulv). Impulsresponsen hentes ut ved dekonvolusjon (Farinas inversfilter). Vinduet stenges 5 ms etter direktelyden, før første refleksjon. Kurven er gyldig fra ca. 200 Hz og oppover (1/gate).
   - **Nærfelt** (1–2 cm foran basselementet). Den er gyldig under ca. 400 Hz og skjøtes til gated-målingen ved 300 Hz med nivåtilpasning.
3. Mikrofonkorreksjonen trekkes fra. Du kan velge mellom:
   - forhåndsvalg for iPhone, Android og S1/Touch (grove)
   - flat (kalibrert mikrofon)
   - en kalibreringsfil i UMIK/miniDSP/REW-format («frekvens dB»), lastet opp med `POST /api/speakers/calibration`
4. Kurven glattes til 1/6 oktav og normaliseres til snittet mellom 300 Hz og 3 kHz.

## Profil

- **Filtre:** inntil 10 peaking-filtre (RBJ) mellom 60 Hz og 16 kHz, maks +3 dB løft og −12 dB kutt.
- **Målkurver:** «Nøytral» (flat), «Varm» (−1 dB per dekade over 1 kHz) og «Mer bass» (+2 dB hylle under 120 Hz).
- **Kvalitetsscore 0–100:**

  | Del | Poeng |
  |---|---|
  | Signal/støy | 40 |
  | Ikke klippet | 15 |
  | Dekning av frekvensområdet | 25 |
  | Samsvar mellom gjentatte målinger | 20 |

- **Råd:** følsomhet (dB) og impedans (Ω) gir råd for S1, for eksempel advarsel under 4 Ω eller ved lav følsomhet.

## Sammen med romkorreksjonen

Høyttalerfiltrene ligger i CamillaDSP etter brukerens EQ og før romkorreksjonen (`sp0…` og deretter `rq0…`). Forforsterkningen trekkes ned like mye som det største løftet, så kjeden aldri klipper.

Når romkorreksjonen er på, eier den bassen. Høyttalerfiltre under 300 Hz droppes da, så de to aldri retter det samme.

## Profildatabasen (Skjold Cloud)

Databasen er åpen og anonym:

- Den lagrer bare kurven, merke, modell, score, gyldig område, valgfri følsomhet og impedans, og en kilde. Kilden er en hash av enhetens machine-id.
- IP-adresser lagres bare som hash, til grensen per døgn og til flagging.

| Kall | Hva |
|---|---|
| `GET /hoyttaler/sok?q=` | Søk på merke og modell. Sertifiserte profiler vises først. |
| `GET /hoyttaler/profil/<id>` | Profilen: medianen av innsendingene, med `sertifisert`, `antall`, `enige` og `score`. EQ-filtrene regnes ut på Skjold. |
| `POST /hoyttaler/send` | Send inn en måling. Én innsending per kilde og modell (en ny måling erstatter den gamle). Maks 20 innsendinger per IP per døgn. |
| `POST /hoyttaler/flagg` | Meld fra om en feil profil. 3 flagg fra ulike IP-er skjuler profilen. |
| `POST /hoyttaler/moder` | Moderering, med `Authorization: Bearer $MOD_TOKEN`. Handlinger: `vis`, `skjul`, `slett`, `fjern_kilde`. |

**Skjold Sertifisert:** minst 3 ulike kilder må ligge innen 2 dB RMS (100 Hz–10 kHz) av medianen, og snittscoren må være minst 70. Den samme regelen ligger i `certify()` i Python.

**Offline:** profiler du har brukt ligger i `/var/lib/ki-amp/speakerprofiles.json`. Søket faller tilbake til denne cachen når det ikke er nett.

**Deploy:** `wrangler.toml` har fått migrasjonen `v2` (`Hoyttalere`). Sett eventuelt `MOD_TOKEN` som secret.

## Begrensninger

- En telefonmikrofon er unøyaktig over ca. 10 kHz og under ca. 100 Hz. Forhåndsvalgene er grove, så en kalibrert USB-mikrofon (UMIK-1 o.l.) med kalibreringsfil gir langt bedre profiler. Score og sertifisering demper effekten av dårlige enkeltmålinger.
- Gated-målinger i små rom gir kort vindu og dermed høy nedre grense. Nærfelt dekker bassen.
