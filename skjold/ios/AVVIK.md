# Avvik mot designet

Status 2026-11-02. Utseendet er det samme som før; endringene under er logikk og noen få tekster/rader som trengs for ekte data. Etter at koblingene til daemonen ble lagt inn er appen **ikke bygget i Xcode ennå** (bare syntakssjekket). Skjermbildene i `design/skjermer/` er heller ikke sammenlignet med kjørende app.

## Mangler fra designpakken
| Hva | Hvorfor | Midlertidig løsning |
|---|---|---|
| `renders/cut/01–04-*.png` (velkomst-hero) | Ikke med i zip-filen | S1-renderen er klippet ut av `01-velkomst.png` (`hero-s1`). Node-bildene vises som strektegning. Legg ekte renders inn som `hero-01-s1`, `hero-03-s1`, `hero-02-node`, `hero-04-node` i Assets, så brukes de automatisk. |
| `README.md`, punkt 3 (REST/WebSocket-API) | Ikke med i zip-filen | Erstattet av det ekte API-et i `pi/ki_amp_daemon.py` (REST + SSE på port 8765). Se «Koblinger» i `CLAUDE.md`. |
| Logo for NRK Alltid Nyheter | Ikke på static.nrk.no | Hentes via Radio Browser, ellers fargeforløp. |

## Bevisste avvik
- Demokortene (S1 og Node) i «Finn forsterker» vises bare når ingen enhet er funnet, og meta-teksten er «Demo · ingen enhet funnet ennå». Funne enheter viser navn og `ip:port`.
- Wi-Fi settes via forsterkerens nettverk (`/api/wifi`), ikke kryptert over Blåtann som designet beskriver. Steg 2 har en ekstra statuslinje («Henter nettverk …», feilmelding).
- Innstillinger → Musikktjenester har en ny rad «Passord» for Navidrome (Subsonic krever det).
- Info-radene (Programvare, IP, Serienummer, Lyrion, Parede enheter, Navn på nettverket) viser ekte verdier eller «Frakoblet»/«Ikke funnet». «PO-token-tjeneste» viser «Ikke tilgjengelig».
- Rom-pillen på Hjem har rød prikk når forsterkeren er frakoblet, grå mens appen kobler til.
- Bibliotek som ikke er satt opp (eller YouTube Music, som ikke har backend) viser en forklarende tekst i stedet for hyller. «Mest spilt» i Navidrome/Plex er album, ikke låter.
- «Nylig spilt» på Hjem viser bibliotekhistorikk og radiofavoritter (designets AirPlay-/Blåtann-låter finnes ikke uten demomodus).
- Køen viser bare det som spiller når kilden ikke er et bibliotek. Spoling og tilfeldig/gjenta er lokale.
- Installering/backup/gjenoppretting fra Oppdatering gir en melding om at forsterkeren ikke støtter det ennå (simuleringen finnes bare i demomodus).
- QR-skanning bruker kamera der det finnes. Inneholder koden en adresse, kobler appen seg dit. I simulatoren går den videre etter 2,2 s, slik designet gjør.
- Spilleposisjonen går fremover mens det spilles, og rettes av status fra forsterkeren.
- Oppsettet huskes. Etter første fullføring starter appen rett i hovedappen (introen vises fortsatt).
- «7 favoritter» brytes på to linjer i skjermbilde 19. Det ser ut som en layoutfeil i designet, så her står teksten på én linje.
- Statuslinjen og hjemindikatoren er systemets egne, ikke designets attrapper.

## Handoff 45 (2026-11-03)
| Punkt | Status |
|---|---|
| Radio-oppdagside (søk, «Favoritter», toppkort, sjangerfiltre, hyller, ★/☆, spill uten favoritt) | finnes (iOS og Android) |
| Favoritter i Innstillinger → Radio, inntil 50, rekkefølge, strøm-URL | finnes |
| «Annet nettverk …» med SSID/sikkerhet/passord og «Skriv eget navn» | finnes |
| Merkelogoer Navidrome og Lyrion (`logo/brands`) | finnes (lagt inn nå: `brand-navidrome`, `brand-lyrion`, Android `brand_*`) |
| Kategori «Skjold Touch» (rolle, utgang, standby, standby-visning, nattmodus) | finnes (lagt inn nå; samme nøkler som daemon og web, ikke designets tDim/tOff/tBri/tCtl/tWake/tBtn som daemonen ikke har) |
| Lydutgang og Blåtann-paring også for Touch, Spotpear HIFI HAT i I²S-listen | finnes (lagt inn nå) |
| Skjermtyper per rom (`DISPLAYS`, klokker per skjerm) | mangler – daemonen har ikke valg av skjermtype ennå |

## Gjenstår
1. Bygg i Xcode og rett eventuelle kompileringsfeil (se «Må testes i Xcode» i `CLAUDE.md`).
2. Installer iOS 27.2-simulatoren (Xcode → Settings → Components). Ta skjermbilde av alle 20 skjermene på iPhone 15 Pro, sammenlign mot `skjermer/` og legg inn avvikene her.
3. Kontroller linjehøyder: Sora har en annen naturlig linjehøyde enn CSS `line-height`. Bare ekstra linjeavstand er lagt til, ingen negativ.

## Design v4 (App v4.dc.html, platform=ios) – første runde
| Punkt | Status |
|---|---|
| SkjoldTheme.swift med iOS-tokens (titler 32/600, dokk, ark, hyller, iPad-marg) + `skGlass` | finnes |
| Hjem: hjemmets navn 32/600 med pil (stedvelger) + glasskapsel med søk og innstillinger | finnes |
| Sidetitler 32/600, Rom-fanen heter «Rom» | finnes |
| Rom: gruppetekst «Samme musikk i alle rommene, synkronisert ned til millisekunder …» | finnes |
| Lyd: «HVA BÅNDENE GJØR» | finnes |
| Innstillinger → Radio: hint om radioknappen og ★ | finnes |
| «Klokkestil i standby» | finnes |
| iPad (TARGETED_DEVICE_FAMILY 1,2, sidebarAdaptable, bred marg og maks bredde) | finnes |
| Hyller i v4-mål (Nylig spilt 132, Kilder 68 runde, Radio 112), «Dine spillelister» | mangler |
| Mer-arket, Søk-skjerm, kildesider, spilleliste i v4-stil | mangler |
| Grupper og surround, «Spill på»-statuslinje, skjermvelger, Navidrome Utforsk, Touch-kort i oppsett | mangler |
| Sammenligning mot simulator | ikke gjort |

## v4 – UI bygget på nytt fra bunnen (`UI/`)

Fasit: `fasit/v4/*.png` (skjermbilder av «Skjold App v4.dc.html», 390 × 844 og iPad 1180 × 820). Ikke sammenlignet mot simulator ennå (ingen Xcode i byggemiljøet).

| Del | Status |
|---|---|
| Dokk: minispiller (radius 26, glass, mono-linje i gull, volum 6), fanelinje 64/32 med linse (.5 s, overskyting) | finnes |
| Sammenslått dokk ved rulling (>60 ned, <−4 / <20 opp), fremdriftsring 21.5/3 | finnes (matchedGeometryEffect + fjær .45/.8) |
| Hjem: tittel + stedsmeny, søk/innstillinger-kapsel, Nylig spilt 132, Kilder 68, Radiofavoritter 112, Dine spillelister 148, hyller | finnes – hyllene viser bibliotekhistorikk (live) i stedet for designets «Mest spilt i november» |
| Lyd: kildechips, EQ-kurve 196 (gauss, dra), båndfaner, forklaring, sammenlign, nullstill, profiler 104, lydbilde | finnes – 14 profiler (felles med web/daemon) i stedet for 7; Nattmodus og Små høyttalere lagres bare i appen (ingen nøkkel i daemonen) |
| Rom: kort 24 med romfarge fra omslaget, enhetsikoner, volum per rom, sortering, «Fest rom»-ark | finnes |
| Innstillinger: kategoriliste i v4-stil | finnes – undersidene er fortsatt `SettingsView` |
| Nå spilles: gradient, Låt/Kø-linse, omslag 322 → 200 (rom), kø, «Spill på»-panel, bunnrad | finnes – spoling er bare visning (ingen seek i daemonen) |
| «Mer»-ark (glass, 34) og volumknott (−150°…150°) | finnes – «Legg til i spilleliste» og sovetimer har ingen backend |
| Kildeside (glød, status, søk, spillelister, låter / forklaring for innganger) | finnes – Spotify vises som inngang (Spotify Connect har ikke bibliotek) |
| Spilleliste (gradient 560, mosaikk 240) og Søk (#050506, «Søk i»-filter, felt nederst) | finnes |
| iPad: fanekapsel øverst, spillerlinje maks 1000, Nå spilles som panel 400 fra høyre | finnes |
| Sora 700 | mangler fontfila – 700 tegnes som 600 |
