# Skjold – Homey-app (Skjold S1, Skjold Node, Skjold Core)

Installeres som utvikler-app (ikke i App Store):

```bash
npm install -g homey          # Homey CLI
homey login
cd no.kristo.ki-pultforsterker
homey app install             # eller `homey app run` for live-logg
```

Krav: Pi-en i forsterkeren kjører `ki_amp_daemon.py` (port 8765) på samme nett som Homey.

Legg til enhet: Enheter → + → Skjold → velg **Skjold S1**, **Skjold Node** eller **Skjold Core**. Første side har «Søk automatisk» (mDNS `_kipultamp._tcp`, filtrert på TXT `product`; eldre daemoner uten `product` spørres om `/api/status`) og et felt for **IP-adresse + port** (8765) når enheten ikke finnes automatisk. Manuell IP sjekkes mot `/api/status`, og velger du feil modell, sier paringen hvilken det er.

Hver driver har egne capabilities:

| | S1 | Node | Core |
|---|---|---|---|
| Strøm, volum, mute, kilde, avspilling/spiller nå, radiofavoritt (inntil 50, fra `/api/presets`), loudness, tale, auto-kilde, miks | ✓ | ✓ | ✓ |
| AUX/USB-kilder, hodetelefoner (+ flytkort), auto-demping, USB-switch (+ flytkort), nivå per kilde inkl. AUX | ✓ | – | – |
| Skjermlysstyrke (+ flytkort) | ✓ | ✓ | – |
| LED-lysstyrke og LED-modus (+ flytkort «Sett LED-ringer») | – | ✓ | – |

Den gamle driveren «Pultforsterker» er merket `deprecated`: den vises ikke ved ny paring, men parede enheter virker som før (produktet følger `status.product`). Felles kode ligger i `lib/SkjoldDevice.js` og `lib/SkjoldDriver.js`.

Bildene til appen og den gamle driveren lages av `make_icons.py`. Driverikonene (`drivers/{s1,node,core}/assets/icon.svg`, strektegning) lages av `make_driver_icons.py`, og driverbildene (small/large/xlarge) av `make_driver_images.py` fra produktrenderne i `skjold/nettside/assets/img` (Core: ikonet på mørk bakgrunn). Begge trenger `pip install cairosvg pillow`.

## Test

```bash
npm test          # enhetstester (inkl. test/drivers.test.js: tre produktdrivere, paring via mDNS og manuell IP) (node --test) mot en innebygd mock av Pi-API-et – ingen Homey eller Pi nødvendig
npm run mock      # starter mock-daemonen på port 8765 på PC-en
```

Testene dekker capabilities (på/av, volum 0–1 ↔ 0–100, mute, kilde, loudness), flytkortene (betingelser, handlinger, triggere ved kildebytte og avspilling), feilhåndtering (API-feil, mistet kontakt → utilgjengelig) og mDNS-adresseendring. `test/stubs/homey` er en liten stubb av Homey SDK v3; `test/mock-daemon.js` etterligner `ki_amp_daemon.py`.

Ende-til-ende på en ekte Homey uten forsterker: kjør `npm run mock` på PC-en, `homey app run`, legg til enheten manuelt med PC-ens IP – da kan du teste flyter og enhetskortet i Homey-appen mot mock-en (den «spiller» av seg selv hvert 15. sekund).
