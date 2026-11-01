# OPPGAVE: få mobilappen i takt med designet

**Problem:** Det meste som er lagt til i designet siden forrige bygg, mangler i appen. Det skyldes trolig at appen ble bygget etter de gamle fasitbildene og `RETTELSER_APP_MOBIL.md`, og ikke etter designfilen.

**Regel:** Mobilappen skal være **piksel-identisk** med `app/Skjold App v2.dc.html`. Designfilen gjelder foran alt annet, også foran `RETTELSER_APP_MOBIL.md` og bilder. Ikke tolk, forenkle eller bruk standardkomponenter.

## Gjør dette i rekkefølge
1. **Les hele designfilen.** Malen ligger øverst, og logikken i `class Component` nederst. Les også `skjold_settings.js` (innstillingsmodell, radiokatalog, kanalbilder og logoer).
2. **Lag en avviksliste før du koder.** Gå gjennom hver `<sc-if>` i malen (85 betingede visninger) og hvert punkt under. Merk hver linje i `app/AVVIK.md` som *finnes / mangler / avviker*.
3. **Bygg alt som mangler eller avviker.** Bruk mål, farger og tekst nøyaktig fra koden.
4. **Ta skjermbilder** på 390 pt bredde av alle 20 skjermene i `fasit/v3/`. Legg dem ved siden av designfilen i samme tilstand (se `fasit/README.md`). Rett til det er likt.
5. Oppdater `AVVIK.md` til alt er *finnes*.

## Alt appen skal ha (sjekkliste)
**Start**
- [ ] Intro-animasjon ved første start, så velkomstside med rullende render av Skjold S1 og Node på sort bakgrunn. «Kom i gang» skal synes uten å rulle.

**Oppsett (4 trinn, fremdriftslinje, «Tilbake»)**
- [ ] 1: Funne enheter som kort, «Leter etter flere …», «Skann QR-kode», «Skriv inn adresse manuelt»
- [ ] 1: QR-skanner med ramme og skannelinje
- [ ] 2: Wi-Fi-liste med signal og lås, og **«Annet nettverk …»** med felt for SSID, sikkerhet (WPA2/WPA3/Ingen) og passord
- [ ] 3: Romvalg i rutenett + **«Skriv eget navn»** med eget felt
- [ ] 3b: Test høyttalerne L/R
- [ ] 4: Programvare/oppdatering

**Hjem**
- [ ] Header: logo + pille med rom/gruppe. Ingen power-knapp.
- [ ] Rom-kort med ikon, navn, modell og maskinvare, og «Bytt». Teksten skal ikke flyte ut.
- [ ] Nylig spilt (horisontal)
- [ ] Kilder med **ekte, fulle logoer** (Spotify, YouTube Music, Navidrome, AirPlay, UPnP/DLNA, Chromecast osv.), samt ikoner for AUX, Radio og Blåtann
- [ ] Radiofavoritter + «Administrer»
- [ ] Minispiller over fanelinjen

**Spiller**
- [ ] Fullskjermspiller, bytt kilde og volum
- [ ] Kø

**Lyd**
- [ ] EQ per kilde (AirPlay, BT, radio, AUX, hodetelefoner) med forklaring av hvert bånd og hver forhåndsinnstilling

**Rom**
- [ ] Ditt system, grupper («Alle rom» / «Bare …»), roller og synk

**Biblioteker** (inspirert av YT Music/Navidrome, ikke kopi)
- [ ] YouTube Music: søk, faner, miks, hyller, spilleliste med låter
- [ ] Navidrome: søk, album, hyller, spilleliste og historikk
- [ ] Når et bibliotek er åpent, vises **verken «Ditt system» eller kø** ved siden av (web)

**Radio**
- [ ] Oppdag-side: søk + «Favoritter», toppkort med kanalen som spiller, sjangerfiltre og hyller (Dine favoritter, Populære i Norge, sjangre)
- [ ] Søk: norske kanaler først, så Radio Browser (hele verden). ★/☆ på hver rad.
- [ ] Kanaler kan spilles uten å være favoritt

**Innstillinger**
- [ ] Kategorier med ikon, tittel og undertekst. Undertekst på én linje der det er plass.
- [ ] Equalizer, Lyd, Tilkobling, **Radio** (favoritter øverst: inntil 50, endre rekkefølge, søk og legg til, **legg til strøm-URL**; så knapper og oppstart), **Musikktjenester** (Spotify Connect, UPnP/DLNA-mottaker, Chromecast, YouTube Music via Music Assistant, Navidrome), Stemme, Skjerm, Strøm, System og Oppdatering

## Merk
- Webgrensesnittet (`web/Skjold S1 Web v3.dc.html`) har samme regel. Det åpnes på `<navn>.local`, og spilleren velges på siden. Gjør samme avviksliste for web.
- `RETTELSER_APP_MOBIL.md` er eldre. Punkt 1–9 gjelder fortsatt for safe-area og fanelinje, men designfilen gjelder ved konflikt.
