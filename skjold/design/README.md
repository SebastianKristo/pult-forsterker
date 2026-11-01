# Handoff: Skjold (S1, Node, programvare, nettside og bruksanvisning)

## Oversikt
Skjold er en serie nettverkslydprodukter, designet av Sebastian Kristo Jemtland.
- **Skjold S1:** streamingforsterker i bøyd aluminium, 190 × 160 × 48 mm. Raspberry Pi 4, I²S-DAC (HiFiBerry DAC+), TPA3116 2 × 50 W. Innebygd USB-bryter mellom Pi og PC. 2,42″ OLED eller TFT bak røyksort akryl.
- **Skjold Node:** printet nettverksspiller, 91 × 74 × 34 mm. Pi 4 eller 3B/3B+, 1,8″ ST7735S, EC11-encoder og 4 × 12 mm knapper.
- **Programvare:** Skjold OS (UI på enheten), webgrensesnitt (skjold.local), app for iOS og Android, Skjold Flasher (desktop), SD-bilde (pi-gen).
- **Nettside:** skjold.smarthjemexperten.no, på Cloudflare Pages fra GitHub.

## Om designfilene
Filene i denne pakken er **designreferanser laget i HTML**. Det er prototyper som viser utseende og oppførsel, og de er ikke produksjonskode. Oppgaven er å **gjenskape dem i riktig miljø**:

| Del | Miljø |
|---|---|
| Skjold OS (UI på enheten) | Python (Pillow + luma / pygame) eller C/LVGL på Pi |
| Webgrensesnitt | Lett SPA, f.eks. Svelte/Preact, servert av `skjold-web` på Pi-en |
| App | React Native, Flutter eller native SwiftUI/Compose |
| Flasher | Electron/Tauri. Gjerne fork av Raspberry Pi Imager-logikken. |
| Nettside | Statisk (Astro/11ty eller ren HTML) + Cloudflare Pages Function for interesseskjemaet |

`.dc.html`-filene åpnes direkte i nettleseren. Logikken ligger i `<script data-dc-script>` nederst i hver fil. Malen bruker `{{ }}`-hull, `sc-for` og `sc-if`, og `support.js` er runtime. Les malen for å se layouten og logikk-klassen for å se tilstand og oppførsel.

## Detaljnivå
**High-fidelity.** Farger, typografi, avstander, animasjoner og knappeoppførsel er endelige.

**Krav: mobilappen (`app/Skjold App v2.dc.html`) og web-UI-et (`web/Skjold S1 Web v3.dc.html`) skal bygges piksel-identisk med designfilene.** Samme størrelser, avstander, radier, farger, skrifter, ikoner, tekster og rekkefølge. Ikke bruk standardkomponenter fra rammeverket (Material, Cupertino, Bootstrap e.l.) som endrer utseendet. Ikke «forbedre», forenkle eller legg til noe. Sammenlign skjermbilder side om side ved samme bredde (app: 390 px, web: 1280 px) før hver skjerm regnes som ferdig. Ved tvil er designfilen fasit.

## Mapper
| Mappe | Innhold | Hovedfil |
|---|---|---|
| `nettside/` | 7 sider + felles nav + interesseskjema + Pages Function | `Skjold Nettside.dc.html`, data i `site/skjold_site_data.js`, animasjon i `site/skjold_site_fx.js` |
| `node/` | Node-UI-simulator, 3D-kasse, CAD-skript, **kablingsoppgave** | `Skjold Node OS.dc.html`, `OPPGAVE_KABLING_NODE.md` |
| `s1/` | Interaktiv 3D av S1 med full UI-simulering (OLED/TFT) | `Pultforsterker v2 revB metall.html` + `pultforsterker_revb_metall.js` |
| `app/` | App (iOS/Android) og onboarding | `Skjold App v2.dc.html`, `Skjold Oppsett.dc.html` |
| `web/` | Webgrensesnitt med alle innstillinger | `Skjold S1 Web v3.dc.html` |
| `flasher/` | Desktop-flasher | `Skjold Flasher.dc.html` |
| `felles/` | Innstillingsmodell + klokkestiler (`skjold_settings.js`), velkomsthilsen (`skjold_welcome.js`) | |
| `sdbilde/` | pi-gen-stage, systemd-tjenester, `skjold-velkomst` SSH-kommando | `README.md` |
| `bruksanvisning/` | LEGO-stil mal + innhold som JSON | `MAL_FOR_CLAUDE.md`, `innhold.json` |

## ⚠ Start her for app og web
Les `app/OPPGAVE_APP_SYNK.md` først. Den forrige appen ble bygget etter gamle bilder og mangler det meste. Fasitbildene ligger nå i `app/fasit/v3/`, og de gamle er flyttet til `_utdatert/`.

## Oppgaver for Claude Code, i rekkefølge
1. **Node-kabling:** følg `node/OPPGAVE_KABLING_NODE.md`. Det gir SVG-skjema, kabelliste, `node_pins.json`, driveroppsett og testskript.
2. **Skjold OS:** gjenskap UI-et fra `node/Skjold Node OS.dc.html` (160 × 128) og `s1/pultforsterker_revb_metall.js`:
   - funksjonene `drawOLED0`/`drawTFT0` (128 × 64 / 320 × 240)
   - `overlay`
   - `node_fx.js`: splash, omstart, kildebytte
   - `skjold_welcome.js`

   Lag én tegnemotor med en layout per skjermstørrelse. Knappeoppførselen står i oppgavefilen og i `S1`-logikken: `selectInput`, `holdPair`, `holdReboot`, `holdRadio`.
3. **Backend på Pi:** Lyrion (squeezelite), shairport-sync (AirPlay 2), BlueALSA, librespot (Spotify Connect – **ikke implementert ennå**), USB-bryter-GPIO (S1). Integrasjoner: Home Assistant (mDNS + REST/MQTT media_player) og Homey-app. Lag et lokalt REST- og WebSocket-API som app, web og UI deler. Innstillingsmodellen er `felles/skjold_settings.js`.
4. **Webgrensesnitt og app:** gjenskap `web/` og `app/` mot API-et. Equalizer per kilde (AirPlay, BT, radio, AUX og hodetelefoner), grupper og synk, standby-klokker, oppdateringer.
5. **Flasher:** gjenskap `flasher/`. Den skriver SD-bildet, legger inn Wi-Fi, navn og SSH, og viser en QR-kode for onboarding.
6. **SD-bilde:** bygg ut `sdbilde/pi-gen` slik at det første bootoppsettet viser IP-adresse og QR-kode på skjermen. Se `Skjold Oppsett.dc.html` for flyten: språk, Wi-Fi, navn/rom, høyttalertest L/R, Lyrion, oppdatering.
7. **Bruksanvisning:** fyll `bruksanvisning/innhold.json` etter `MAL_FOR_CLAUDE.md` for både S1 og Node. Lodding, alle koblinger og steg for steg.
8. **Nettside:** gjør `nettside/` om til et statisk nettsted. Publiseringen står i `NETTSIDE_PUBLISERING.md`, og skjemaet bruker `functions/api/interesse.js` med KV `INTERESSE`.
   - **Påstander som må stemme før publisering:** Spotify Connect, Home Assistant og Homey (se pkt. 3).
   - **Baktanke-teksten på Om-siden** er plassholder. Eieren skriver den selv.

## Design-tokens
**Farger**
- Svart `#000000`, kort `#111113`, linje mørk `#26262a`
- Tekst lys `#f5f5f2`, dempet `#a8a8a3` / `#8b8b86`
- Lys flate `#f5f4f0`, studio `#e9e9ec` (S1) / `#ecebe7` (Node)
- Tekst mørk `#1d1d1b`, dempet `#55534c` / `#7a776d`, linje lys `#e3e0d7`
- Aksent khaki `#d8cfb4` / `#8a7f60`

**Kildefarger**
- Radio `#e8893a`
- Blåtann/USB `#4a8cff`
- AirPlay `#f5f5f2`
- AUX `#d8cfb4`
- Spotify `#1ed760`

**Fonter**
- Sora 300/400/600/700 til overskrifter: hero clamp(46–96 px), H2 clamp(34–56 px), letter-spacing −0,02em
- IBM Plex Sans 400/500/600 til brødtekst: 15–21 px, linjehøyde 1,45–1,6
- IBM Plex Mono til etiketter: 12–13 px, letter-spacing 0,1em
- På enheten: Helvetica Neue / Arial

**Radier og avstander**
- Radier: kort 20–28 px, piller 99 px, enhetsskjerm 6 px
- Avstander: seksjoner 110 px vertikalt, innhold maks 1080 px, kolonnemellomrom 12–16 px

**Animasjon på nettsiden**
- Reveal: 0,9 s med cubic-bezier(.2,.7,.2,1), translateY 28 px → 0
- Hero-zoom: scale 0,86 → 1 på scroll
- Sticky bildesekvens: 400 vh, 4 bilder som tones over i hverandre på 0,7 s

**Logo:** fem avrundede stolper med høyder 22/33/42/33/22 og bredde 4,6 (forhold), toppjustert, pluss «SKJOLD» i Sora 600 med letter-spacing 3 px.

## Assets
- `nettside/renders/*.png` er laget fra 3D-modellene: `01–04-s1`, `01–04-node`. Byttes mot foto senere.
- Fonter: Google Fonts (Sora, IBM Plex).
- Ingen tredjepartslogoer er brukt. AirPlay, Spotify, Home Assistant og Homey er nevnt bare med navn. Følg merkevarereglene deres hvis logoene skal brukes.
