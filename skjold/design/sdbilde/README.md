# Skjold S1 – SD-bilde og plug-and-play-oppsett

Målet er at brukeren flasher et SD-kort, setter det i, slår på og blir guidet gjennom oppsettet på skjermen og mobilen. Ingen tastatur, ingen SSH.

## 1. Hva bildet inneholder
| Del | Pakke / tjeneste | Rolle |
|---|---|---|
| OS | Raspberry Pi OS Lite (Bookworm, 64-bit) | Grunnsystem, NetworkManager |
| Lyrion | lyrionmusicserver + squeezelite | Radio, favoritter, multirom |
| AirPlay | shairport-sync (AirPlay 2, nqptp) | AirPlay-inngang |
| Blåtann | bluez + bluez-alsa (A2DP sink) | Blåtann-inngang |
| USB-lyd | USB gadget / UAC2 fra hovedkortets USB-hub | PC og Switch |
| Skjold | skjold-ui (skjerm, knapper, encoder), skjold-web (webgrensesnitt + onboarding), skjold-setup (første oppstart), skjold-improv (Wi-Fi over Blåtann) | Alt det egenutviklede |

Alle Skjold-tjenestene ligger i én Python-pakke (`/opt/skjold`) med systemd-enheter. Innstillinger lagres i `/etc/skjold/config.json` – samme nøkler som innstillingsmenyen (bass, treb, bal, vstart, vmax, voice, lang …).

## 1b. Skjold Node (ren Raspberry Pi med bare lydutgang)
Samme SD-bilde. `skjold-setup` finner ut hvilken maskinvare som sitter i ved første oppstart:
- **Ingen OLED på SPI og ingen knappekort på I²C** → Node-modus. `skjold-ui` startes ikke. Skjerm-, knappe- og radioknappinnstillinger skjules i appen og på webgrensesnittet.
- **Støttet:** Raspberry Pi 3B, 3B+ og 4 (1 GB eller mer).
- **Utganger:** 3,5 mm (innebygd), HDMI, USB-DAC eller I²S-kort (HiFiBerry DAC+, DAC2 HD, IQaudio DAC Pro, Allo Boss). Utgangen velges i appen under *Lydutgang*. Da skrives riktig `dtoverlay` til `config.txt`, og Pi-en starter på nytt.
- **Innganger:** AirPlay, Spotify Connect, Blåtann og Lyrion. AUX og USB inn finnes bare på S1.
- **Oppsett uten skjerm:** Node lager Wi-Fi-nettet `Skjold-Node-XXXX` og annonserer seg over Blåtann (Improv). Status vises med den grønne LED-en på Pi-en: blinker sakte = venter på oppsett, blinker raskt = kobler til, lyser fast = klar. Stemmen sier «Skjold er klar» på valgt språk når oppsettet er ferdig.
- **Flere rom:** alle Skjold-enheter er Lyrion-spillere. Grupper i appen synkroniseres med Lyrion, så rommene spiller det samme i takt.
- **Fast volum:** bruk *Volumkontroll → Fast 100 %* når Node går til en forsterker med egen volumknapp.

## 2. Første oppstart (skjold-setup)
1. `/boot/firmware/skjold-setup.json` finnes (lagt der av flasheverktøyet) → bruk forhåndsinnstilt Wi-Fi, navn og språk, hopp rett til steg 5.
2. Ellers: skjermen viser **Sett opp Skjold**. Pi-en starter to oppsettkanaler samtidig:
   - **Wi-Fi-hotspot** `Skjold-Oppsett-XXXX` (NetworkManager, WPA2, passord vises på skjermen). dnsmasq peker alle DNS-oppslag til 10.42.0.1 → telefonen åpner innloggingssiden (captive portal) automatisk.
   - **Improv Wi-Fi over BLE** (åpen standard). Appen eller Chrome på Android/PC finner forsterkeren og sender Wi-Fi-navn og passord direkte.
3. Skjermen viser QR-kode 1: `WIFI:T:WPA;S:Skjold-Oppsett-XXXX;P:<passord>;;` – skann med kamera for å koble til.
4. Når en telefon er koblet til: QR-kode 2 med `http://10.42.0.1/oppsett`, og IP-adressen som tekst.
5. Onboarding-stegene (språk → Wi-Fi → navn/rom → høyttalertest L/R → Lyrion → oppdatering) kjøres fra nettsiden eller appen. Skjermen speiler hvert steg.
6. Når Wi-Fi er koblet: hotspot slås av, skjermen viser ny IP og `http://<navn>.local`, og telefonen sendes videre dit.
7. Fabrikkinnstillinger i menyen sletter `config.json` og Wi-Fi-profiler og starter oppsettet på nytt.

Sikkerhet: hotspot-passordet er tilfeldig per enhet og vises bare på skjermen. Oppsettsiden er bare tilgjengelig mens oppsettet pågår. Improv over BLE krever trykk på volumknappen for å godta.

## 3. Bygging av bildet
Bildet bygges med **pi-gen** (Raspberry Pi sitt offisielle byggeverktøy) med et eget trinn `stage-skjold`. Se `pi-gen/` i denne mappen.

```
git clone https://github.com/RPi-Distro/pi-gen.git
cp -r sdbilde/pi-gen/* pi-gen/
cd pi-gen && ./build-docker.sh
# → deploy/skjold-s1-<dato>.img.xz
```

## 4. Flasheverktøyet (Skjold Flasher)
Egen desktop-app (Tauri eller Electron) for macOS, Windows og Linux:
1. Laster ned siste `skjold-s1-*.img.xz` + SHA-256 fra Skjold sin oppdateringsserver.
2. Brukeren velger SD-kort (bare flyttbare disker vises).
3. Valgfritt: Wi-Fi, navn/rom og språk → skrives til `skjold-setup.json` på boot-partisjonen etter flashing.
4. Flasher og verifiserer (samme fremgangsmåte som Raspberry Pi Imager / etcher-sdk).

Alternativ uten egen app: lag en egen repo-JSON for Raspberry Pi Imager slik at «Skjold S1» dukker opp som eget OS-valg.

## 5. Appene
- **Nettside (PWA):** samme onboarding som captive portal, kan legges på hjemskjermen. Fungerer på alle telefoner.
- **iOS og Android (egne apper):** finner forsterkere med BLE (Improv) og mDNS (`_skjold._tcp`), QR-skanner for oppsettkoden, deretter samme steg som nettsiden. Etter oppsett: fjernkontroll (inngang, volum, radio).
- Anbefalt teknologi: React Native eller Flutter, slik at én kodebase gir begge appene.

## 6. Oppdateringer fra GitHub, backup og gjenoppretting
- **Kilde:** GitHub Releases i `skjold-audio/skjold-s1` (kan endres). `skjold-update` leser `https://api.github.com/repos/<repo>/releases`. Kanalen *Stabil* tar bare vanlige releases. *Beta* tar også pre-releases.
- **Pakke:** hver release har `skjold-<versjon>.tar.zst` og `SHA256SUMS`. Signaturen sjekkes før installering.
- **Backup:** før hver oppdatering lagres `/opt/skjold`, `/etc/skjold` og pakkelisten som `/var/lib/skjold/backup/<versjon>-<dato>.tar.zst`. De 6 siste beholdes. Brukeren kan også ta backup manuelt.
- **Automatisk gjenoppretting:** etter installering startes tjenestene på nytt med en helsesjekk (skjerm, lyd og web svarer innen 90 s). Feiler den, pakkes forrige backup ut og forsterkeren startes på nytt. Feilen logges og vises i appen og i webgrensesnittet.
- **Manuell gjenoppretting:** hvilken som helst backup kan gjenopprettes fra appen eller webgrensesnittet. Det krever to trykk.
- **Nattlig installering:** valgfritt, kl. 03–05 når forsterkeren står i standby.


## Velkomsthilsen før gave (én gang)
Kjør dette over SSH før du pakker inn enheten:
```
ssh pi@skjold.local
sudo skjold-velkomst "Gratulerer med dagen" "Pappa"
sudo poweroff
```
Neste gang enheten får strøm, vises SKJOLD-oppstarten og deretter hilsenen med konfetti. Hilsenen blir stående til noen trykker på en knapp eller volumknappen. Det første trykket lukker bare hilsenen og gjør ingenting annet. Når hilsenen er trykket vekk, er den brukt opp og vises ikke igjen. Går strømmen før den er trykket vekk, vises den igjen ved neste oppstart.
- `sudo skjold-velkomst --vis`: viser hilsenen nå, som test.
- `sudo skjold-velkomst --status` og `--av`: viser status eller slår av hilsenen.
- Gjelder både S1 (OLED og TFT) og Node. Animasjonen ligger i `skjold_welcome.js`.
