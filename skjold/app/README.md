# Skjold-appen (web + iOS/Android)

Én kodebase (Vite + Preact + TypeScript) for:
- **Web-UI** som `ki_amp_daemon.py` serverer på `http://skjold.local:8765/` (samme origin, ingen konfig).
- **Mobilapp** via Capacitor (`no.kristo.skjold`). Brukeren finner forsterkeren (prøver `skjold.local` / `pultamp.local`)
  eller skriver inn adresse/IP; den lagres i `localStorage` (`skjold-host`). `?host=192.168.1.50` virker også på web.

Under 900 px (og alltid i appen) brukes telefonskallet fra `design/app/Skjold App v2`, ellers PC-skallet fra
`design/web/Skjold S1 Web v3`. Oppsettsveiviseren følger `design/app/Skjold Oppsett`.

## Kommandoer
```sh
npm install
npm run dev          # Vite på :5173, /api proxes til 127.0.0.1:8765 (SKJOLD_API overstyrer)
npm run typecheck
npm run build        # -> dist/ (JS og CSS inlinet i index.html, se under)
npm run cap:sync     # build + npx cap sync
npm run cap:android  # åpner Android Studio
npm run cap:ios      # åpner Xcode
```

## Teste mot daemonen uten maskinvare
```sh
mkdir -p /tmp/stubs && for c in amixer aplay systemctl bluetoothctl; do printf '#!/bin/sh\n' >/tmp/stubs/$c; chmod +x /tmp/stubs/$c; done
cd pi && PATH=/tmp/stubs:$PATH KI_AMP_BOARD=main KI_AMP_PORT=8765 KI_AMP_VOICE=0 \
  KI_AMP_WEBAPP=$PWD/../skjold/app/dist python3 ki_amp_daemon.py
```

## Struktur
- `src/lib/api.ts` – klient for API-et (se docstring i `pi/ki_amp_daemon.py`), vertsvalg, GitHub Releases.
- `src/lib/store.ts` – signals: status-polling (1–4 s), `act()` med optimistisk oppdatering, innstillinger (`/api/settings`, debounce 350 ms).
- `src/lib/settings.ts` – innstillingsmodellen portert fra `design/felles/skjold_settings.js`; `clocks.ts` – standby-klokkene.
- `src/screens/` – `player` (omslag, transport, volum, kilder, favoritter), `pages` (Hjem, EQ, Radio, Rom), `settings`, `onboard` (Finn Skjold, Oppsett).
- `src/app.tsx` – telefon- og PC-skall.

## Plattformer
`android/` og `ios/` er generert med `npx cap add` (Capacitor 8) og sjekket inn uten byggeresultater.
Endringer gjort for hånd etter generering:
- Android: `android:usesCleartextTraffic="true"` (forsterkeren snakker http på LAN).
- iOS: `NSAppTransportSecurity` (arbitrary loads + local networking), `NSLocalNetworkUsageDescription`, `NSBonjourServices`.

Lage på nytt: `rm -rf android ios && npm run build && npx cap add android && npx cap add ios`, og legg inn endringene over.
`fetch` går gjennom `CapacitorHttp` i appen, så daemonen trenger ikke CORS.

**NB:** Capacitor 8 lager iOS-prosjektet med Swift Package Manager (`ios/App/App.xcodeproj`, `CapApp-SPM`), ikke CocoaPods.
Release-workflowen må derfor bygge med `xcodebuild -project App.xcodeproj -scheme App …` og droppe `pod install`.

## Kjente begrensninger / API som mangler i daemonen
- Daemonen serverer `index.html` på `/` men resten av mappen under `/app/`. Bygget legger derfor JS/CSS inn i
  `index.html`; ikoner og manifest (`./icons`, `./manifest.webmanifest`) finnes bare under `/app/`. Anbefalt: server mappen
  også på `/` (eller send `/` til `/app/`).
- `/api/settings` forkaster ukjente nøkler: `nameCustom`, `updChannel`, `updAuto`, `setupDone` lagres derfor bare lokalt i appen.
  `applied` i svaret brukes til å merke innstillinger som «lagres – styrer ikke forsterkeren ennå».
- Vises som «kommer»: EQ per kilde i lyden (profilene lagres i `settings.eq`), rom/grupper, Wi-Fi-bytte (`/api/wifi`),
  høyttalertest (`/api/test`), glem Blåtann-enheter, omstart (`/api/reboot`), fabrikkinnstillinger (`/api/reset`),
  installering av oppdatering (appen sjekker bare GitHub Releases og lenker dit).
