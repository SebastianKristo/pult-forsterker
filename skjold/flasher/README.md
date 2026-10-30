# Skjold Flasher

Desktop-app (Electron) som skriver Skjold-SD-bildet til et SD-kort, legger inn Wi-Fi, navn og SSH, og viser en
QR-kode for onboarding. Gjenskapt etter `skjold/design/flasher/Skjold Flasher.dc.html`.
App-ID `no.kristo.skjold.flasher`. Bygges til `.dmg` (macOS x64/arm64), `.exe` (NSIS) og `.AppImage` av
`.github/workflows/skjold-release.yml` (`npm ci && npm run dist`, filene havner i `release/`).

## Kom i gang

```bash
npm install          # postinstall bygger native moduler for Electron (feiler mykt uten nett, se under)
npm run typecheck
npm test             # bygger + tester sha512crypt (mot Drepper-vektorer og openssl) og boot-filene
npm start            # bygg og start appen  (npm run dev åpner DevTools)
npm run screenshot   # Playwright: laster dist/renderer med falskt API, skjermbilder av alle steg i screenshots/
npm run dist         # installasjonsfil for denne plattformen i release/  (dist:mac / dist:win / dist:linux)
```

Native moduler (`drivelist`, `mountutils`, `@ronomon/direct-io`) må bygges mot Electron. `npm run dist` gjør det
alltid (`npmRebuild`). Feilet `postinstall` (f.eks. uten tilgang til Electron-headere), kjør `npm run rebuild` senere.

## Flyt

1. **Velg SD-kort** – bilde («Siste Skjold-bilde» fra GitHub Releases, eller lokal `.img`/`.img.xz`/`.zip`/`.gz`),
   enhet (S1 / Node Pi 4 / Node Pi 3B) og SD-kort. Disklisten oppdateres hvert 2. sekund.
2. **Forhåndsinnstill** – Wi-Fi (navn, passord, land), navn/rom, språk, vertsnavn (utledes fra navnet: «Stue» →
   `skjold-stue`), valgfritt SSH med bruker + passord og/eller offentlig nøkkel.
3. **Skriv og verifiser** – laster ned (SHA-256 kontrolleres), pakker ut, legger oppsettfilene inn i bildet,
   ber om administratortilgang, skriver og leser tilbake (etcher-sdk, `verify: true`).
4. **Ferdig** – instruksjoner og QR-kode til `http://<vertsnavn>.local:8765/`. Kortet løses ut.

### Bildet fra GitHub
`src/main/release.ts` leser `https://api.github.com/repos/SebastianKristo/pult-forsterker/releases`, tar nyeste
ikke-pre-release med tag `skjold-v*` og en asset som matcher `skjold-*.img(.xz|.zip|.gz)` (pi-gen lager
`skjold-s1-<dato>.img.xz`). Sjekksum hentes fra `<asset>.sha256` eller `SHA256SUMS` hvis release har det.
Nedlastingen caches i brukerdata-mappen. **NB:** release-workflowen publiserer foreløpig ikke selve SD-bildet –
til det er på plass viser appen «Ingen bilde publisert ennå» og lokal fil må brukes.

### Filer på boot-partisjonen
Skrives inn i en utpakket kopi av bildet (partisjon 1, FAT, via `balena-image-fs`) *før* skriving. Da trengs ingen
montering av kortet etterpå, og verifiseringen dekker også oppsettfilene.

| Fil | Leses av | Innhold |
|---|---|---|
| `skjold-setup.json` | `skjold-setup` (se `design/sdbilde`) | `device`, `hostname`, `lang`, og ved forhåndsinnstilling `name` og `wifi {ssid,password,country}` |
| `custom.toml` | Raspberry Pi OS Bookworm (`raspberrypi-sys-mods`, samme format som Raspberry Pi Imager) | `[system] hostname`, `[user]`/`[ssh]` (ved SSH), `[wlan]` (ved forhåndsinnstilling), `[locale]` |
| `ssh`, `userconf.txt` | eldre Bookworm/Bullseye | SSH på, `bruker:$6$…` (sha512crypt) |

Passord lagres aldri i klartekst for brukeren (sha512crypt, `src/shared/sha512crypt.ts`). Wi-Fi-passordet står i
klartekst i `skjold-setup.json`/`custom.toml` slik Pi-en forventer; `skjold-setup` sletter sin fil etter bruk.

## Rettigheter og sikkerhet

- Bare disker som er flyttbare/USB/kort, 1–256 GB, ikke systemdisk, ikke skrivebeskyttet og uten system-
  monteringspunkt vises (`src/shared/drivefilter.ts`). Den samme sjekken kjøres **på nytt** i skriveprosessen.
- Skrivingen skjer i en egen prosess (`dist/writer/writer.js`, Electron-binæren med `ELECTRON_RUN_AS_NODE=1`).
  Fremdrift sendes som JSON-linjer over en TCP-socket på 127.0.0.1 med et tilfeldig engangstoken.
- **macOS / Windows:** skriveprosessen startes med administratorrettigheter via `sudo-prompt` (passorddialog / UAC)
  bare når kortet skal skrives. Appen selv kjører som vanlig bruker (`requestedExecutionLevel: asInvoker`).
- **Linux:** AppImage-en ligger på en FUSE-montering root ikke kan lese, så Electron kjøres ikke som root. I stedet
  ber appen (via `pkexec`) om å avmontere kortets partisjoner og gi brukeren eierskap til blokkenheten (`chown`).
  Eierskapet forsvinner når kortet tas ut. Enhetsnavnet valideres (`/dev/sdX`, `/dev/mmcblkN`) før kommandoen bygges.

## Struktur

```
src/main/      main.ts (vindu, IPC, flyt), preload.ts, drives.ts, release.ts, image.ts, elevate.ts
src/writer/    writer.ts – privilegert skriving + verifisering
src/shared/    types.ts, bootconfig.ts, sha512crypt.ts, drivefilter.ts
src/renderer/  index.html, styles.css, app.ts (uten rammeverk)
src/test/      crypt.test.ts
scripts/       copy-static.js, postinstall.js, screenshot.js
```

## Testet / ikke testet

- Testet: typecheck, `npm test`, Playwright-skjermbilder av alle fire steg, utpakking av et `.img.xz` med FAT-
  boot-partisjon + innskriving av oppsettfilene (kontrollert med mtools/fsck.fat), `electron-builder --linux --dir`,
  skriveprosessen fra pakket app (laster etcher-sdk fra asar, avviser ukjent disk), oppstart av pakket app i Xvfb.
- **Ikke testet:** skriving til et ekte SD-kort, rettighetsdialogene på macOS/Windows, dmg/nsis-bygg og at Pi-en
  faktisk leser `custom.toml` i det ferdige Skjold-bildet. Gjør en full runde på hver plattform før release.
