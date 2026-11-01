# AVVIK – appen mot `design/app/Skjold App v2.dc.html` (og `web/Skjold S1 Web v3.dc.html`)

Steg 2 i `design/app/OPPGAVE_APP_SYNK.md`. Første kolonne er tilstanden **før** synken (src/ per 01.11.2026),
siste kolonne er tilstanden **etter**. *finnes* = som i designfilen, *mangler* = ikke i appen, *avviker* = finnes, men
ser annerledes ut eller oppfører seg annerledes. «UI finnes, backend mangler» = bygget som i designet, men viser en
ærlig «ikke tilkoblet»/tom tilstand fordi forsterkeren ikke har API for det.

## Betingede visninger (`<sc-if>` i malen, i rekkefølge)

| # | sc-if | Hva | Før | Etter |
|---|---|---|---|---|
| 1 | intro | Intro-animasjon (lyn, fjell, SKJOLD-ord) ved første start | mangler | finnes |
| 2 | welcome | Velkomstside med rullende render (S1/Node), «Kom i gang» uten rulling | mangler | finnes |
| 3 | onboard | Oppsett-skall: kicker «OPPSETT · n AV 4», 4 streker, tittel, tekst | finnes | finnes |
| 4 | obCanBack | «Tilbake» øverst til høyre | finnes | finnes |
| 5 | ob0 | Funne enheter som kort (første gull), «Leter etter flere …», «Skann QR-kode på skjermen» | avviker (ekstra knapp «Skriv inn adresse manuelt» over QR) | finnes (manuell adresse som tekstlenke over QR-knappen, RETTELSER pkt. 8) |
| 6 | obScanView | QR-ramme 190×190 med hjørner og skannelinje, «Leter etter QR-kode …» | avviker (video, ingen bakgrunnsflate #151517) | finnes |
| 7 | ob1 | Wi-Fi-liste (min-høyde 50, ✓), «Annet nettverk …» | avviker (ingen signal/lås, faller til «Tilkoblet» når /api/wifi mangler) | finnes (signal og lås fra GET /api/wifi; uten NetworkManager vises «Tilkoblet» og Neste). Brødteksten sier «Passordet sendes bare til forsterkeren» i stedet for «Sendes kryptert over Blåtann», fordi appen går over hjemmenettet |
| 8 | netIsMan | Hjelpetekst, SSID-felt, WPA2/WPA3/Ingen | finnes | finnes |
| 9 | needPw | Passordfelt | finnes | finnes |
| 10 | ob2 | Romrutenett 2×4 | finnes | finnes |
| 11 | isCustom | «Skriv eget navn»-felt + «Maks 20 tegn …» | finnes | finnes |
| 12 | ob3 | Test høyttalerne L/R (150 px kort), «Hopp over høyttalertest» | mangler | finnes (POST /api/test, ny i daemonen). Designkoden hopper fra trinn 3 rett til 4; appen går 2 → 3b → 4 slik sjekklisten krever, med «Hopp over høyttalertest» |
| 13 | ob4 | Programvare: fremdriftslinje + mono-tekst | avviker (tekst) | finnes |
| 14 | obShowNext | Neste/Koble til/Ferdig (52 px, gull når ok) | finnes | finnes |
| 15 | app | App-skall | finnes | finnes |
| 16 | full | Fullskjermspiller (ark med håndtak, dra ned for å lukke) | finnes | finnes |
| 17 | showArt | Kvadratisk omslag med kicker, stor tittel og visualisering | avviker (kildechips over omslaget) | finnes |
| 18 | art.live | DIREKTE-merke | finnes | finnes |
| 19 | queueOpen | Kø («Neste i køen») i stedet for omslaget | mangler | finnes for Navidrome (køen styres av appen); andre kilder: UI finnes, backend mangler (viser det som spiller + «Køen er tom») |
| 20 | srcOpen | Kildechips når kildenavnet/⋯ trykkes | avviker (alltid synlig øverst) | finnes |
| 21 | isRadio | Radio-favorittchips (n + navn) i spilleren | mangler | finnes |
| 22 | hasProgress | Fremdrift med −gjenstående tid | finnes | finnes |
| 23 | playing / paused | Spill/pause-ikon | finnes | finnes |
| 24 | — | Shuffle / gjenta, kildenavn ▾ + kvalitet, volumrad med høyttalerikon, Kø · rom-pille · ⋯ | mangler (bare VOL-rad og rom-knapp) | finnes (Tilfeldig blander Navidrome-køen; Gjenta: UI finnes, backend mangler – nedtonet) |
| 25 | notFull / hasTitle | Sidetittel (28 px) utenom Hjem | finnes | finnes |
| 26 | tHome | Hjem: logo + pille, romkort, Nylig spilt, Kilder, Radiofavoritter | avviker (kildene mangler YT Music, Navidrome, UPnP/DLNA, Lyrion med ekte logo) | finnes |
| 27 | tRooms | «Alle rom» / «Bare …», romkort med volum og hake | avviker (gruppeknapper gir bare toast) | UI finnes, backend mangler for synk |
| 28 | hasGroup | Gruppekort «Samme musikk / Surround» + forklaring | mangler | UI finnes, backend mangler (lagres lokalt) |
| 29 | rm.showRoles | Roller Stereo/Venstre/Høyre/Bak V/Bak H/Sub | mangler | UI finnes, backend mangler (lagres lokalt) |
| 30 | tSound | Lyd: profil per kilde, forhåndsinnstillinger, kurve, 5 bånd, «HVA BÅNDENE GJØR», tone, loudness | finnes | finnes |
| 31 | tLib | Bibliotek-side (tilbake, søk) | mangler | finnes |
| 32 | libSearching / libResEmpty | Søkeresultater / «Ingen treff» | mangler | finnes (Navidrome: ekte søk via Subsonic) |
| 33 | libNotSearching / libInPl | Spilleliste/album med «Spill» og «Tilfeldig» + låter | mangler | finnes (Navidrome ekte; YT Music: ikke tilkoblet) |
| 34 | libTop | Faner (Hjem/Spillelister/Historikk · Album/Spillelister/Historikk) | mangler | finnes |
| 35 | libShowDisc | Toppkort (miks/nylig lagt til) med prikker | mangler | finnes (Navidrome ekte) |
| 36 | hasMoods | Stemningschips (YT Music) | mangler | UI finnes, backend mangler |
| 37 | sh.hasKicker | Hyller med kicker | mangler | finnes |
| 38 | libShowPl | Spillelisterader | mangler | finnes (Navidrome ekte) |
| 39 | libShowHist / histEmpty | Historikk + «Tøm historikk» | mangler | finnes (lagres på telefonen) |
| 40 | tRadio | Radio oppdag: søk + «Favoritter» | finnes | finnes |
| 41 | rSearching / rHasLoc / rBusyS / rHasOnl / rNone | Søk: NORSKE KANALER, Radio Browser, ★/☆ | finnes | finnes |
| 42 | rNotSearching | Toppkort, sjangerfiltre, hyller | finnes | finnes |
| 43 | tSet / setTop | Enhetschips, maskinvarelinje, kategorier med ikon/tittel/undertekst | avviker (enhetschips mangler; Musikktjenester uten ikon) | finnes (enhetschipsene vises når appen kjenner mer enn én enhet) |
| 44 | setDetail | Tilbake-lenke «Innstillinger» | finnes | finnes |
| 45 | isRadioSet | «Favoritter» øverst i Radio-innstillinger | finnes | finnes |
| 46 | notAdding / s.view / s.edit | Favorittliste, ★ på radioknappen, endre rekkefølge (opp/ned/fjern) | finnes | finnes |
| 47 | adding / rSok / onlBusy / onlHas / onlHint | Legg til kanal: Søk | finnes | finnes |
| 48 | rUrl / uHasDone | Legg til strøm-URL med test | finnes | finnes |
| 49 | isUpd / u.* / bk.can | Oppdatering: installert versjon, kanal, auto, sjekk, utgivelse, backup | avviker (enklere liste) | finnes (sjekk mot GitHub, kanal og «om natten» ekte; installer/backup/gjenoppretting: UI finnes, backend mangler; demo-bryteren «la neste oppdatering feile» er utelatt) |
| 50 | hasClocks | Klokkestil i standby (6 lerret) | finnes | finnes («Vis på forsterkeren» utelatt – ingen API) |
| 51 | notUpd / it.* (hasHint, isBool, isNum, isOpt, isInfo, isAct, isStr, isEq, isLong, isSteps, open) | Innstillingsrader | avviker (isLong/isSteps/isEq manglet) | finnes |
| 52 | hasMini | Minispiller (rom · modell, tittel, artist) over fanelinjen | finnes | finnes |

## Sjekklisten i oppgaven

| Punkt | Før | Etter |
|---|---|---|
| Intro-animasjon + velkomst med rullende S1/Node-render, «Kom i gang» synlig | mangler | finnes (renders/cut/*.png kopiert til public/renders) |
| Oppsett 1: kort, «Leter etter flere …», «Skann QR-kode», «Skriv inn adresse manuelt» | finnes | finnes |
| Oppsett 1: QR-skanner med ramme og skannelinje | avviker | finnes |
| Oppsett 2: Wi-Fi med signal og lås + «Annet nettverk …» (SSID, WPA2/WPA3/Ingen, passord) | avviker | finnes (GET/POST /api/wifi via nmcli, ny i daemonen) |
| Oppsett 3: romrutenett + «Skriv eget navn» | finnes | finnes |
| Oppsett 3b: test høyttalerne L/R | mangler | finnes (POST /api/test, ny i daemonen). Designkoden hopper fra trinn 3 rett til 4; appen går 2 → 3b → 4 slik sjekklisten krever, med «Hopp over høyttalertest» |
| Oppsett 4: programvare/oppdatering | avviker | finnes (versjon fra forsterkeren + GitHub) |
| Hjem: header uten power-knapp | finnes | finnes |
| Hjem: romkort med ikon/navn/modell/maskinvare + «Bytt», ingen overflyt | finnes | finnes |
| Hjem: Nylig spilt | finnes | finnes |
| Hjem: kilder med ekte, fulle logoer (Spotify, YT Music, Navidrome, AirPlay, UPnP/DLNA, Lyrion) + AUX/Radio/Blåtann | avviker | finnes (logo/brands kopiert til public/logo) |
| Hjem: Radiofavoritter + «Administrer» | finnes | finnes |
| Minispiller over fanelinjen | finnes | finnes |
| Fullskjermspiller, bytt kilde, volum | avviker | finnes |
| Kø | mangler | UI finnes, backend mangler |
| Lyd: EQ per kilde med forklaringer | finnes | finnes |
| Rom: Ditt system, grupper, roller og synk | avviker | UI finnes, backend mangler |
| YouTube Music: søk, faner, miks, hyller, spilleliste | mangler | UI finnes, backend mangler (Music Assistant ikke tilkoblet) |
| Navidrome: søk, album, hyller, spilleliste, historikk | mangler | finnes (Subsonic-API direkte fra appen, avspilling via /api/radio/play) |
| Web: bibliotek åpent skjuler «Ditt system» og kø | mangler | finnes |
| Radio oppdag (søk, Favoritter, toppkort, sjangre, hyller) | finnes | finnes |
| Radio søk: norske først, så Radio Browser, ★/☆ | finnes | finnes |
| Spill kanal uten å være favoritt | finnes | finnes |
| Innstillinger: kategorier med ikon, tittel, undertekst på én linje | avviker | finnes |
| Innstillinger → Radio (favoritter, rekkefølge, søk, strøm-URL, knapper og oppstart) | finnes | finnes |
| Innstillinger → Musikktjenester (Spotify Connect, UPnP/DLNA, Chromecast, YT Music via Music Assistant, Navidrome) | avviker (bare Spotify og UPnP) | finnes (Navidrome ekte; Chromecast/MA: UI finnes, backend mangler) |
| Equalizer, Lyd, Tilkobling, Stemme, Skjerm, Strøm, System, Oppdatering | finnes | finnes |

## Web (S1 Web v3, PC-skallet over 900 px)

| Punkt | Før | Etter |
|---|---|---|
| Velg spiller i toppen (pickOpen: liste, «denne», «Eget UI ↗») | mangler | finnes |
| YouTube Music / Navidrome i venstremenyen (når slått på / satt opp) | mangler | finnes |
| Bibliotek åpent: skjul «Ditt system» (showSys) og kø | mangler | finnes |
| Bibliotekside (pgLib) | mangler | finnes (samme komponent som mobil) |
| Rom i høyrekolonnen med grupper/roller | avviker | UI finnes, backend mangler |
| Integrasjoner-siden (pgInt) | mangler | mangler – dekkes av Innstillinger → Musikktjenester |

## Nytt i daemonen (`pi/ki_amp_daemon.py`, dokumentert i docstringen)

- `GET /api/wifi` → `{"networks":[{ssid,signal,security,active}]}` via `nmcli` (503 uten NetworkManager).
- `POST /api/wifi {"ssid","psk"?,"hidden"?}` → kobler til med `nmcli device wifi connect`.
- `POST /api/test {"channel":"L"|"R"}` → 0,8 s 440 Hz-tone i én kanal (WAV lages med `wave`, spilles med `aplay`).

## Ærlig backend-status

- **Ekte:** status, kilder, volum, transport, EQ/innstillinger, radio (favoritter, søk, hyller, spill uten favoritt),
  Wi-Fi og høyttalertest (nye endepunkt), GitHub-sjekk, Navidrome (Subsonic-API fra appen: `ping`, `getAlbumList2`,
  `getAlbum`, `getPlaylists`, `getPlaylist`, `search3`, `getCoverArt`, token = md5(passord + salt); avspilling ved å
  sende `stream`-URL-en til `POST /api/radio/play`, som spiller via Lyrion). Navidrome-innlogging lagres bare på telefonen.
- **UI finnes, backend mangler:** YouTube Music (Music Assistant), Chromecast, UPnP/DLNA-avspilling fra Hjem (åpner
  Musikktjenester), synkroniserte grupper/surround-roller (lagres i appen), kø for AirPlay/Blåtann/Spotify, Gjenta,
  installer oppdatering/backup/gjenoppretting fra appen, «Vis klokke på forsterkeren».
  Navidrome-køen går videre til neste låt bare når du trykker Neste (forsterkeren vet ikke om køen).

## Status (etter)

52 sc-if-linjer + 27 sjekklistepunkt + 6 web-punkt: se kolonnen «Etter». Telling i rapporten.
