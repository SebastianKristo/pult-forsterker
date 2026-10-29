# KI Pultforsterker – Homey-app

Installeres som utvikler-app (ikke i App Store):

```bash
npm install -g homey          # Homey CLI
homey login
cd no.kristo.ki-pultforsterker
homey app install             # eller `homey app run` for live-logg
```

Krav: Pi-en i forsterkeren kjører `ki_amp_daemon.py` (port 8765) på samme nett som Homey.

Legg til enhet: Enheter → + → KI Pultforsterker → forsterkeren dukker opp via mDNS. Finner den ikke, sett IP under enhetens innstillinger.

Bildene (forsterkerens front i designfargene) og enhetsikonet `icon.svg` lages av `make_icons.py` (trenger `pip install cairosvg`).

## Test

```bash
npm test          # enhetstester (node --test) mot en innebygd mock av Pi-API-et – ingen Homey eller Pi nødvendig
npm run mock      # starter mock-daemonen på port 8765 på PC-en
```

Testene dekker capabilities (på/av, volum 0–1 ↔ 0–100, mute, kilde, loudness), flytkortene (betingelser, handlinger, triggere ved kildebytte og avspilling), feilhåndtering (API-feil, mistet kontakt → utilgjengelig) og mDNS-adresseendring. `test/stubs/homey` er en liten stubb av Homey SDK v3; `test/mock-daemon.js` etterligner `ki_amp_daemon.py`.

Ende-til-ende på en ekte Homey uten forsterker: kjør `npm run mock` på PC-en, `homey app run`, legg til enheten manuelt med PC-ens IP – da kan du teste flyter og enhetskortet i Homey-appen mot mock-en (den «spiller» av seg selv hvert 15. sekund).
