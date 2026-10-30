# Skjold – bygg, release og installasjon, steg for steg

Alt under `skjold/` bygges av GitHub Actions (`.github/workflows/skjold-release.yml`) på GitHubs egne Mac-, Windows- og
Linux-maskiner. Du trenger ikke Xcode, Android Studio eller en Mac for å lage filene – bare for å *signere* dem (se del 4).

| Fil | Hva | Lages av |
|---|---|---|
| `skjold-app-<tag>.apk` | Android-appen (debug-signert, installerbar) | ubuntu-runner |
| `skjold-app-<tag>-usignert.ipa` | iOS-appen, usignert | macos-runner |
| `skjold-web-<tag>.zip` | Web-UI-et som Pi-en serverer på `http://<navn>.local:8765/` | ubuntu-runner |
| `Skjold Flasher-<ver>.dmg` / `.exe` / `.AppImage` | SD-kort-flasheren for Mac / Windows / Linux | én runner per OS |
| `Skjold_S1_Bruksanvisning.pdf` | Bruksanvisningen | ubuntu-runner |

## 1. Lag en release

1. Sørg for at `main` er pushet og grønn.
2. Lag en tag som begynner med `skjold-v` og push den:
   ```bash
   git tag skjold-v1.0.0
   git push origin skjold-v1.0.0
   ```
3. Gå til **GitHub → Actions → «Skjold release»** og følg jobben (10–20 min; iOS- og Mac-jobbene er tregest).
4. Når alle jobber er grønne ligger filene under **GitHub → Releases → «Skjold skjold-v1.0.0»**. Release-notatene
   genereres fra commit-meldingene; rediger dem gjerne.

Vil du bygge uten å lage tag: **Actions → Skjold release → Run workflow**. Da lages artefaktene (last ned fra jobben),
men ingen Release.

Feiler en jobb: åpne loggen. De vanligste årsakene er en `package-lock.json` som ikke er oppdatert (`npm install` lokalt og
commit) eller at Capacitor-plattformmappen mangler (`npx cap add android` / `ios`).

## 2. Installere appen

### Android (APK)
1. Last ned `skjold-app-<tag>.apk` på telefonen (åpne Release-siden i Chrome).
2. Trykk på filen → «Installer». Første gang: tillat «Installer ukjente apper» for Chrome/Filer når Android spør.
3. Åpne **Skjold**. Appen leter etter forsterkeren på `skjold.local` og `pultamp.local`; finner den ikke, skriv inn
   IP-adressen (står på forsterkerens skjerm og i ruteren).

APK-en er signert med en debug-nøkkel. Det betyr: den kan installeres og oppdateres over seg selv så lenge den bygges
av samme workflow, men den kan ikke legges i Google Play. Vil du til Play: lag en keystore (`keytool -genkey …`), legg
den som secret i GitHub og bytt `assembleDebug` med `assembleRelease` + signering i workflow-en.

### iPhone / iPad (IPA)
Apple krever at alle apper er signert. Det finnes tre veier, fra enklest til mest permanent:

**A. Sideloadly / AltStore (gratis Apple-ID, 7 dagers signatur)**
1. Installer [Sideloadly](https://sideloadly.io) (Mac/Windows) og koble iPhonen til med kabel.
2. Dra `skjold-app-<tag>-usignert.ipa` inn i Sideloadly, skriv inn Apple-ID-en din, trykk **Start**.
3. På iPhonen: *Innstillinger → Generelt → VPN og enhetsadministrering* → stol på utvikler-ID-en din.
4. Appen virker i 7 dager med gratis konto, og signeres på nytt ved å gjenta steg 2 (AltStore gjør dette automatisk
   når Mac-en er på samme nett). Med betalt utviklerkonto (99 USD/år) varer signaturen ett år.

**B. Xcode (gratis Apple-ID, 7 dager – eller betalt konto, 1 år)**
1. På en Mac: `cd skjold/app && npm ci && npm run build && npx cap sync ios && npx cap open ios`.
2. I Xcode: velg prosjektet **App → Signing & Capabilities → Team = din Apple-ID**. Xcode lager en gratis provisioning
   profile.
3. Koble til iPhonen, velg den som mål, trykk ▶︎. Første gang: stol på utvikleren på telefonen (som i A3).

**C. TestFlight (betalt utviklerkonto)**
1. Opprett appen i App Store Connect med bundle-ID `no.kristo.skjold`.
2. I Xcode: *Product → Archive → Distribute → TestFlight*. Da kan du og opptil 100 testere installere via
   TestFlight-appen, 90 dager per build, uten kabel.
3. Vil du automatisere: legg sertifikat og provisioning profile som secrets (`fastlane match`) og bytt den usignerte
   byggingen i workflow-en med `xcodebuild -exportArchive`.

### Web-UI (ingen installasjon)
Forsterkeren serverer samme app selv: åpne `http://<navn>.local:8765/` på hva som helst. På iPhone: Del → **Legg til på
Hjem-skjerm**, så får du den som app-ikon uten App Store. Dette er den anbefalte veien for alle som ikke vil drive med
signering – funksjonene er de samme.

For å oppdatere web-UI-et på Pi-en: `skjold-web-<tag>.zip` pakkes ut til `/usr/local/share/ki-amp/webapp/` på Pi-en
(`pi/update.sh` gjør det automatisk når `skjold/app/dist` ligger i repoet).

## 3. Skjold Flasher (SD-kort)

### macOS
1. Last ned `Skjold Flasher-<ver>-arm64.dmg` (Apple Silicon) eller `-x64.dmg` (Intel).
2. Åpne dmg-en og dra **Skjold Flasher** til Programmer.
3. Appen er ikke notarisert av Apple. Første gang: **høyreklikk → Åpne → Åpne** (eller *Systeminnstillinger → Personvern
   og sikkerhet → Åpne likevel*). Deretter åpnes den vanlig.
4. Appen ber om administratorpassord når den skal skrive til SD-kortet (det krever macOS).

### Windows
1. Last ned `Skjold Flasher Setup <ver>.exe` og kjør den.
2. SmartScreen: **Mer info → Kjør likevel** (programmet er ikke kodesignert).
3. Windows spør om administratortilgang når kortet skrives.

### Linux
1. Last ned `Skjold Flasher-<ver>.AppImage`, `chmod +x` og kjør. Skriving krever `pkexec`/sudo – appen spør.

### Bruk
1. **Bilde:** velg «Siste Skjold-bilde» (hentes fra GitHub Releases) eller en lokal `.img`/`.img.xz`.
2. **SD-kort:** bare flyttbare kort vises. Alt på kortet slettes.
3. **Forhåndsvalg (valgfritt):** Wi-Fi-navn og passord, forsterkerens navn/rom, språk, SSH. Dette skrives til
   boot-partisjonen (`skjold-setup.json`, `ssh`, `userconf.txt`) så forsterkeren kobler seg til nettet ved første
   oppstart uten skjerm og tastatur.
4. **Skriv** – kortet skrives og verifiseres (SHA-256).
5. QR-koden på siste side åpner `http://<navn>.local:8765/` på telefonen når forsterkeren er oppe.

## 4. Signering – hvis du vil at ting skal se «ferdig» ut

| Plattform | Hva trengs | Kostnad |
|---|---|---|
| iOS App Store / TestFlight | Apple Developer Program | 99 USD/år |
| macOS notarisering (ingen advarsel) | Samme Apple-konto + Developer ID-sertifikat | inkludert |
| Windows uten SmartScreen | Code-signing-sertifikat (OV/EV) | ca. 2–4 000 kr/år |
| Android Google Play | Google Play Console | 25 USD én gang |

Workflow-en er laget slik at signering kan legges til som secrets uten å endre byggetrinnene (`CSC_LINK`/`CSC_KEY_PASSWORD`
for electron-builder, `APPLE_ID`/`APPLE_APP_SPECIFIC_PASSWORD`/`APPLE_TEAM_ID` for notarisering, keystore for Android).
