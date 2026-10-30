# Skjold – overlevering til neste økt

Status 2026-10-31 00:45. Fire byggere ble startet parallelt og **stoppet midt i arbeidet** for å fortsette i en annen økt.
Det som ligger under `skjold/` er derfor delvis – bruk det som utgangspunkt, ikke som ferdig.

## Ferdig og testet
- `skjold/design/` – designpakken (handoff 18) uendret, inkl. `README.md` med oppgavelisten og design-tokens.
- `pi/ki_amp_daemon.py` – `GET/POST /api/settings` (innstillingsmodellen fra `design/felles/skjold_settings.js`, lagres i
  `state.json`; maksvolum, startvolum, stemme/språk og USB-navn anvendes), web-app servert på `/` fra `pi/webapp` eller
  `/usr/local/share/ki-amp/webapp` (`KI_AMP_WEBAPP` overstyrer). Status-JSON har nå `usb_names`, `voice_profiles`, `inputs`, `board`.
- `pi/webapp/` – enkel PWA-fjernkontroll (fungerer, testet mot daemonen i simulering). Erstattes av `skjold/app/dist` når den er ferdig.
- `.github/workflows/skjold-release.yml` – bygger APK, usignert IPA, web-zip, Flasher (dmg/exe/AppImage) og PDF ved tag `skjold-v*`.
  Forutsetter at mappene under har `package.json` med `build`/`dist`-skript og at `skjold/bruksanvisning/render_pdf.py` finnes.
- `skjold/RELEASE.md` – steg-for-steg for release og installasjon (Android, iPhone-sideloading/TestFlight, Mac/Windows/Linux-flasher).

## Påbegynt (stoppet)
| Mappe | Oppgave | Tilstand |
|---|---|---|
| `skjold/app/` | Vite + Preact + TS, én kodebase for web (Pi serverer `/`) og Capacitor-app (iOS/Android), etter `design/app/Skjold App v2`, `Skjold Oppsett` og `design/web/Skjold S1 Web v3` | prosjektoppsett og deler av `src/` finnes; ingen plattformmapper (`npx cap add android/ios`) ennå; ikke bygget |
| `skjold/flasher/` | Electron + etcher-sdk, electron-builder (dmg/exe/AppImage), etter `design/flasher/Skjold Flasher` | prosjektfiler/tsconfig/`src/` påbegynt; ikke bygget |
| `skjold/bruksanvisning/` | `innhold.json` fylt steg for steg (S1 + Node) etter `design/bruksanvisning/MAL_FOR_CLAUDE.md`; `render_pdf.py` | malen kopiert inn; `innhold.json` er fortsatt designerens eksempel |
| `skjold/node/` | pinnevalg, `kabling_node.svg`, `kabelliste.csv`, `config/node_pins.json`, driveroppsett, `tools/node_selftest.py` | bare `config/` påbegynt |

## Ikke påbegynt (fra designerens README)
Skjold OS (tegnemotor for OLED/TFT fra `design/s1/pultforsterker_revb_metall.js` og `design/node/Skjold Node OS.dc.html`),
SD-bilde (`design/sdbilde/pi-gen`), nettside (`design/nettside/` → statisk + Cloudflare Pages Function), backend-utvidelser
(EQ per kilde i CamillaDSP, grupper/synk via Lyrion, standby-klokker, oppdatering fra GitHub Releases).

## Å huske
- API-et på kortet: se docstring øverst i `pi/ki_amp_daemon.py`. Simulering uten maskinvare:
  `cd pi && PATH=/tmp/stubs:$PATH KI_AMP_BOARD=main KI_AMP_PORT=8765 KI_AMP_VOICE=0 python3 ki_amp_daemon.py`
  (`/tmp/stubs` = tomme skript for `amixer aplay systemctl bluetoothctl`).
- Repo-ID for GitHub Releases: `SebastianKristo/pult-forsterker`. App-ID `no.kristo.skjold`, flasher `no.kristo.skjold.flasher`.
- Commit-trailere og `git -c user.name="Sebastian Kristo" -c user.email="sebastian@kristo.no"` som ellers i repoet.
- Kretskortet (`pcb/`) er i **frys** etter sikkerhetsgjennomgangen; siste ruting lå til eksport/DRC – se `pcb/README.md`.
