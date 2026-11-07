# skjold-ui – skjermen på Skjold S1 rev F og Skjold Radio

4,58″ bar-skjerm, 960 × 320, på HDMI0 (driverkort HDMI-RGB21). Aktiveres med `KI_AMP_DISPLAY=bar958` eller
`KI_AMP_BOARD=s1f` i `/etc/ki-amp.env`; da installerer `install.sh`/`update.sh` den via `pi/install_skjold_ui.sh`.

**Hvorfor nettleser og ikke pygame:** skjermen skal være piksel-identisk med designet. Designets tegnekode er
Canvas 2D (`s1/pultforsterker_revb_metall.js`, ~45 kB tett kode + 16 standby-stiler i `skjold_settings.js`).
I stedet for å porte den for hånd (og få avvik) kjører vi *den samme koden* i Chromium i kiosk under cage
(Wayland, ingen X). Python-delen (`__main__.py`) er server, proxy mot daemonen, eier av hilsenen og mottaker av
knappehendelser. Tegnesløyfen kjører 30 fps bare når noe beveger seg; ellers tegnes det ved endring og når klokka går.

| Fil | Hva |
|---|---|
| `extract.py` | Henter tegnekoden ut av designfilen → `web/s1_draw.js`, `web/skjold_settings.js`, `web/skjold_welcome.js`. Kjør på nytt når designet endres. |
| `web/screen.js` | Kobler designets tilstand `S` til daemonen og knappene (se `KONTRAKT.md`). |
| `web/night.js` | Nattmodus-skjermen (`drawNight` mangler i designfilen og er tegnet etter §6.1). |
| `web/qrcode.js` | qrcode-generator 1.4.4 (MIT), lokalt i stedet for esm.sh. |
| `web/layout.js` | Velger oppsett: S1 (960 × 320) eller radio (800 × 480, `?layout=radio` eller ca. 5:3). |
| `web/radio.js`, `web/radio.css` | Skjold Radio-skjermen: nå spilles, favoritt 1–6 over knappene, hjulmeny, standby-klokke (se KONTRAKT.md § 4 og `kabinett/radio/LES_MEG.md`). |
| `test_render.js` | Tegner tilstandene headless til PNG: `node pi/skjold_ui/test_render.js <mappe> [s1\|radio\|alle]` (S1: 32 tilstander, radio: `skjerm-*.png`). |

**Skjold Radio** (4,3″ DSI 800 × 480): `sudo SKJOLD_UI_LAYOUT=radio bash pi/install_skjold_ui.sh`. Se KONTRAKT.md § 4.

Utvikling uten Pi: `python3 -m skjold_ui --no-kiosk` (i `pi/`) og åpne http://127.0.0.1:8766/ (radio: `/?layout=radio`), eller
`web/index.html?demo=1` direkte.

Fonter: «Helvetica Neue»/Arial i designet → Liberation Sans (fonts-liberation, samme metrikk som Arial).
