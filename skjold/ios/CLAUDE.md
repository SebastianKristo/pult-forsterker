# Skjold – iOS-app (SwiftUI)

Fjernkontroll-app for Skjold-lydsystemet: forsterkeren **Skjold S1** (Pi Zero 2 W, OLED, knapper), **Skjold Node** (Raspberry Pi med bare lydutgang) og **Skjold Core** (Lyrion-server). Rom synkroniseres av **Lyrion Music Server**.

**Status:** Hele brukergrensesnittet er ferdig. Appen er nå koblet til den ekte Skjold-daemonen (`pi/ki_amp_daemon.py`, port 8765), Lyrion, Navidrome, Plex og GitHub Releases. Eksempeldataene brukes bare i **demomodus**, det vil si når appen aldri har funnet eller valgt en Skjold-enhet. Selve utseendet skal ikke endres. **Koblingene er skrevet uten Swift-kompilator (bare syntakssjekket), så første bygg i Xcode må sjekkes.**

---

## Bygg og kjør

- Xcode-prosjekt: `Skjold.xcodeproj`, scheme `Skjold`, ett mål (iPhone).
- iOS **26.0+** (Liquid Glass-API-ene krever iOS 26), bare iPhone, bare stående modus, bare mørk modus.
- Mappen `Skjold/` er synkronisert med målet, så nye `.swift`-filer der kommer automatisk med i bygget.
- Swift 5-modus med `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor`. Rene hjelpetyper uten UI er derfor merket `nonisolated` (for eksempel `SVGPathParser`, `RadioBrowser` og `PlexAPI`).
- Signering: personlig team `23A28PYU2U`, bundle-id `com.sebastiankristojemtlandpersonalteam.Skjold`.
- Info.plist: fontene ligger under `UIAppFonts`. I tillegg er `NSBonjourServices` satt til `_kipultamp._tcp` (det daemonen annonserer) og `_skjold._tcp`, `NSLocalNetworkUsageDescription` og `NSCameraUsageDescription` er fylt ut, og ATS har `NSAllowsLocalNetworking = true`.
- Prosjektfilen er `Skjold.xcodeproj/project.xcproj`: Xcode 27s nye tekstformat (JSON-aktig, `"last-upgrade": "27.0"`), ikke en gammel `project.pbxproj`. Ikke gi den nytt navn.
- Før koblingene ble lagt inn ga bygget verken feil eller advarsler. Etter dem er det ikke bygget ennå (se «Må testes i Xcode»).

## Designkilde

Designfilene ligger i `design/` (kopiert fra den opprinnelige designpakken):

- `design/Skjold App v2.dc.html`: malen og logikken (`class Component`). Ved tvil er det denne som gjelder.
- `design/skjold_settings.js`: innstillingsskjema, radiokatalog, enhetstyper og logoer. Den er portet til `SkjoldData.swift`.
- `design/skjermer/*.png`: skjermbilder i 3x.
- `design/XCODE_BYGG.md`: byggeoppgaven, med tokens og regler.
- **Dette manglet i designpakken:** `README.md` (punkt 3 skulle beskrive enhetens REST/WebSocket-API), `renders/cut/*.png` (produktbildene) og `logo/brands/navidrome.png` og `lyrion_fav.png`.

Kjente avvik fra designet står i `AVVIK.md`. Merk at den filen skal oppdateres.

---

## Arkitektur

En enkelt `@Observable` modell, `AppModel`, opprettes i `MyApp` og sendes ned med `.environment(model)`. Visningene leser `@Environment(AppModel.self) private var m`. Modellen speiler `state` og logikken fra `class Component` i designfilen.

```
MyApp → ContentView (rot: bakgrunn, intro, velkomst/oppsett/app)
          └─ AppShell
               ├─ tabStyle == "glass": system-TabView (Liquid Glass) + tabViewBottomAccessory(NowPlayingAccessory)
               ├─ tabStyle == "classic": egen SKTabBar + SKMiniPlayer
               └─ FullPlayerView (overlay, dra ned / ⌄ for å lukke)
```

### Filer

| Fil | Innhold |
|---|---|
| `MyApp.swift` | Appens inngang. Oppretter `AppModel`. |
| `ContentView.swift` | `ContentView` (rot), `AppShell` (faner: glass og klassisk), `NowPlayingAccessory` (minispilleren i glassmodus). |
| `AppModel.swift` | All tilstand og alle handlinger. Lagrer i UserDefaults via `Store`. Her ligger `post(...)`, se «Koblinger». |
| `SkjoldData.swift` | `SK` med statiske data: innstillingskategorier (`SettingCategory`/`SettingItem`/`SettingKind`), standardverdier (`SK.def`), EQ-presets og -kilder, radiokatalog, enhetstyper, demosystem (`SK.sysDefault`), utgivelser, **demobibliotek** (`SK.tr`, `SK.lt`, `SK.lib`). Inneholder også verdityper: `Station`, `Track`, `Room`, `SystemState`, `EQProfile`, `UpdateState` m.m. |
| `Services.swift` | `RadioBrowser` (søk, logoer, strømtest, `streamURL(for:)`), `PlexAPI.test`, `DeviceBrowser` (Bonjour `_kipultamp._tcp` + `_skjold._tcp` med TXT og oppløsning til `ip:port`), `Net` (HTTP), `DevStatus`/`DevSettings`/`DevPreset` (tolking av daemon-JSON), `DeviceEvents` (SSE), `DeviceLink` (REST mot daemonen). |
| `Backend.swift` | `Lyrion` (JSON-RPC), `Subsonic` (Navidrome), `PlexLib` (Plex-bibliotek), `GitHubReleases` (`skjold-v*`). Alt er `nonisolated` og gir tilbake `Sendable`-verdier (`LibItem`, `LibColl`, `Lyrion.Player` …). |
| `LiveSync.swift` | `extension AppModel`: tilkobling, SSE/polling, status → modell med hold-vindu, kommandoer, rom fra enheter + Lyrion, Lyrion-synk, bibliotekene, innstillinger, oppdatering. `KnownDevice`, `LibData`. |
| `Art.swift` | `art(key)`: cover- og logo-oppslag. Gir NRK-SVG fra Assets, Radio Browser-favicon via `LogoStore`, eller et oklch-fargeforløp. Visningen er `ArtFill`. |
| `Theme.swift` | Farger (`Color.bg`, `.accent` …), `Font.sora`/`Font.plexMono`, modifikatorene `.sora()`, `.mono()`, `.skBorder()`, `.skBox()` og `.topLine()`, `PlainPress`-knappestil (med haptikk), OKLCH og `CSSLinearGradient`. |
| `SVGShape.swift` | SVG-sti-parser (alle kommandoer, også buer) og `SKIcon`. `Icons.*` er ikonene fra designet. |
| `Components.swift` | `SKButton`, `SKField`, `SKChip`, `SKFilterChip`, `SKSegmented`, `SKToggle`, `SKSlider`, `SKCard`, `EdgeScroll`, `FlowLayout`, `SKProgressSteps`, `SourceLogos`/`SourceGlyph`/`SKSourceLogo`, `SKLogo`, `SKTabBar` (klassisk), `SKMiniPlayer` (klassisk), `SKSheet` (dra ned). |
| `Haptics.swift` | `Haptics.tap/thump/tick/bump/success/warning/error`. |
| `IntroView.swift` | Intro-animasjonen (4,7 s) med CSS-nøkkelrammer gjenskapt i `TimelineView`. |
| `WelcomeView.swift` | 01 Velkomst og `HeroCarousel`. |
| `OnboardingView.swift` | 02–08 Oppsett: finn enhet (Bonjour og demokort), QR, Wi-Fi, rom, høyttalertest, programvare. |
| `QRScannerView.swift` | Kameraskanner med VisionKit `DataScannerViewController`. |
| `HomeView.swift` | 09 Hjem: rom-pille, romkort, Nylig spilt, Kilder, Radiofavoritter. |
| `PlayerView.swift` | 10–11 Fullskjermspiller og kø, med topplinje i YouTube Music-stil. |
| `SoundView.swift` | Lyd: kildeprofil, interaktiv `EQGraph`, preset-fliser, tone (`SKCenterSlider`) og loudness. |
| `RoomsView.swift` | Rom («Ditt system»): gruppekort med gruppevolum, `RoomTile`-rutenett (dra sidelengs for volum), surround-plassering. |
| `LibraryView.swift` | YouTube Music, Navidrome og Plex: søk, faner, hero, hyller, spillelister, historikk. |
| `RadioView.swift` | 16–17 Radio: hero, sjangre, hyller, søk (norsk katalog og Radio Browser). |
| `Hjem.swift` | Skjold-hjem (`docs/SKJOLD_HJEM.md`): `HjemAPI` (skyens API, relé-URL-er, CF_Authorization-informasjonskapsel), `HjemSted`/`HjemEnhet`, `extension AppModel` (steder, `selectSted`, `velgEnhet`, `devices`), `StedPicker` (tittel «Hytta ▾» på Hjem/Rom), `HjemBadges`, Innstillinger → Steder (`StederSettingsView`) og → Skjold-hjem (`SkyDeviceView`, `/api/sky`), `HjemLoginView` (WKWebView). |
| `SettingsView.swift` | 18–20 Innstillinger: kategorier per enhet, items, radiofavoritter, oppdatering/backup, standby-klokker (`ClockFace`), APPEN → valg av fanelinje. |

---

## Hva er ekte og hva er demo

**Demomodus** = `known` (lagrede Skjold-enheter, `skjold-known`) er tom. Da brukes designets eksempeldata (`SK.sysDefault`, `SK.tr`, `SK.lt`, `SK.lib`, simulert oppdatering) og ingenting sendes. Så snart Bonjour finner og løser opp en enhet mens appen er i hovedvisningen, kobler appen seg til og forlater demomodus. I «Finn forsterker» står demokortene bare når ingenting er funnet, og de er merket «Demo».

**Ekte (koblet):**
- **Enhet:** `DeviceLink` mot daemonen. Status leses fra `GET /api/events` (SSE, `URLSession.bytes`), med `GET /api/status` hvert 2. s som reserve. Tilstanden (`link`: tilkobler/tilkoblet/frakoblet) vises i rom-pillen på Hjem, i hva som spiller («Frakoblet»), i romkortene og i Innstillinger → System/Tilkobling.
- **Hva som spiller:** tittel, artist, album, cover (`cover_url` → `CoverStore` → `art()`), spiller/pause, posisjon/varighet, volum, inngang, hodetelefoner, `radio_now`, AirPlay-/Blåtann-enhet. Brukerens siste endring holdes en stund (`hold()`, som i `skjold/app/src/lib/store.ts`), og volum sendes med maks én forespørsel i lufta.
- **Rom:** `sys.rooms` bygges av lagrede/funne Skjold-enheter (hver med egen status, polles hvert 4. s) og Lyrion-spillere uten egen daemon. Grupper leses fra Lyrion (`sync_master`/`sync_slaves`) og endres med `sync`. Volum per rom går til daemonen eller til Lyrion (`mixer volume`). Et rom som bare er en Lyrion-spiller styres over JSON-RPC.
- **Radiofavoritter:** hentes fra `GET /api/presets`, lagres med `POST /api/presets {"presets":[…]}` (katalogkanaler uten URL slås opp på Radio Browser først), spilles med `POST /api/presets/{n}/play`. Andre kanaler: `POST /api/radio/play`.
- **Innstillinger og EQ:** `GET/POST /api/settings` (samme nøkler som `skjold_settings.js`, bools som `true/false`, EQ som `{"eq":{src:{preset,eq,loud}}}`). Leses ved tilkobling, ved bytte av enhet og hvert ~30. s.
- **Bibliotekene:** Navidrome (Subsonic: `getAlbumList2` newest/random/frequent, `getPlaylists`, `getAlbum`/`getPlaylist`, `search3`, `getCoverArt`, `stream`) og Plex (`/library/sections`, `…/all?type=9`, `/playlists`, `…/children`, `…/items`, `…/search?type=10`, thumbs via `/photo/:/transcode`). «Spill» sender strøm-URL-en til forsterkeren (`POST /api/radio/play`), som spiller den via Lyrion. Køen ligger i appen: når strømmen er ferdig, sendes neste låt.
- **Oppsett:** ekte enheter i steg 1 (modell fra TXT `product`), QR med adresse, Wi-Fi-liste og tilkobling (`GET/POST /api/wifi`), romnavn (`nameCustom`), høyttalertest (`POST /api/test`), programvaresteget viser installert versjon og nyeste utgivelse, `setupDone` settes til slutt.
- **Oppdatering:** GitHub Releases i `SebastianKristo/pult-forsterker`, bare tagger `skjold-v*` (betaer på Beta-kanalen). Installert versjon = `version` fra daemonen.
- **Lyrion i Kilder** åpner `lyrion_server` fra daemonens status.
- Fra før: Radio Browser, logoer, strømtest, Plex-test, QR-kamera, lokal lagring.

**Fortsatt lokalt, og hvorfor:**
- **YouTube Music:** ingen tjeneste på forsterkeren eller i appen. Biblioteket viser «ikke koblet til», og «Test innlogging» sier «Ikke støttet ennå». Ingen falske data utenom demomodus.
- **UPnP/DLNA:** ingen backend, knappen bytter bare visning.
- **Installering, backup og gjenoppretting** av programvare: daemonen har ikke endepunkter for det. Appen sier fra og viser lenken til utgivelsen. «Demo: la neste oppdatering feile» virker bare i demomodus.
- **Uten endepunkt i daemonen:** `setup`-stegene (ingen visning på skjermen), `previewClock`, `updSync`, `forget` (POST `/api/bt` med `forget` ville startet paring), `reset` (`/api/reset` finnes ikke).
- **Surround-roller og «Samme musikk»/«Surround»-modus:** bare i appen. Lyrion synker grupper, men har ingen roller.
- **Kø, tilfeldig, gjenta og spoling:** i appen. Daemonen har ingen kø eller seek. Køfanen viser bare det som spiller når kilden ikke er et bibliotek.
- **Lyrion-oppdagelse:** via daemonens `lyrion_server`. UDP 3483-broadcast fra iOS krever multicast-entitlement og er ikke laget.
- **Wi-Fi over Blåtann** (designets plan) er ikke laget. Wi-Fi settes via daemonens `/api/wifi`, altså bare når forsterkeren allerede er på nettet.
- **Passord og token** for Navidrome (`ndPass`, nytt felt) og Plex ligger i `names` i UserDefaults, ikke i nøkkelringen, og sendes ikke til forsterkeren.

## Koblinger (meldingene fra designet → daemonen)

Alle handlinger går fortsatt gjennom `AppModel`. I demomodus sendes ingenting. I live-modus:

| Melding / handling | Endepunkt |
|---|---|
| `togglePlay` (`pause`) | `POST /api/transport {"action":"play"\|"pause"}` (Lyrion-rom: `pause 0/1`) |
| `next` / `prev` | `POST /api/transport {"action":"next"\|"previous"}` (bibliotek: neste strøm fra appens kø) |
| `vol {v}` | `POST /api/volume {"volume":v}` (andre rom: deres egen daemon, eller Lyrion `mixer volume`) |
| `wl {v}` / `input {i}` | `POST /api/input {"input":"airplay\|bt\|aux\|radio\|usb"}`; Spotify i Kilder: `{"input":"spotify"}` hvis enheten har det |
| `src {v}` | `POST /api/presets/{n}/play` |
| `play {name,url}` / `play {svc,t}` | `POST /api/radio/play {"url","title","image"?,"genre"?}` |
| `presets` / `radioSync` | `POST /api/presets {"presets":[{title,url,genre,icon}…]}`, deretter `GET /api/presets` |
| `set {k,v}` | `POST /api/settings {k:v}` (tjenestenøkler som `ndUrl`, `plexToken`, `ytmCookie` holdes lokalt; `name` nullstiller `nameCustom`) |
| `eqSync {src}` | `POST /api/settings {"eq":{src:{preset,eq,loud}}}` |
| `sysSync` | Lyrion `sync <pid>` / `sync -`, volum per rom |
| `btPair` | `POST /api/bt {"pairing":true}` |
| `setupTest`, `testSpk`, `testOut` | `POST /api/test {"channel":"L"\|"R"}` |
| `testVoice` | `POST /api/voice {"say":"bt_pairing"}` |
| `ndTest` | Subsonic `ping` (i appen) |
| `setup` steg 2 / 7 | `POST /api/wifi`, `POST /api/settings {"nameCustom"}` / `{"setupDone":true}` |
| `previewClock`, `updSync`, `forget`, `reset`, øvrige `setup`-steg | ingen endepunkt, lokalt |

**Lagt til i daemonen for appen:** `lyrion_server` (`host:port`) og `lyrion_player` (Squeezelite-MAC) i `/api/status` (dokumentert i docstringen).

## Skjold-hjem

- Valgt sted (`stedId`, tom = Dette nettverket) bytter romlista til stedets enheter (`devices` i stedet for `known`). Hver enhet brukes direkte på LAN hvis `lan` svarer innen 1,5 s, ellers via relé `https://<sky>/api/hjem/steder/{sted}/enheter/{id}` – en full URL som `host`, så `Net.url`/`DeviceLink`/SSE virker uendret.
- Innlogging: WKWebView mot skyen; `CF_Authorization` kopieres til `HTTPCookieStorage.shared` (og lagres i UserDefaults for gjenoppretting). ASWebAuthenticationSession deler ikke informasjonskapsler med appen og krever et callback-endepunkt i Workeren. Google-IdP blokkerer innebygde nettlesere – bruk engangskode i Access.
- 401 eller omdirigering til `*.cloudflareaccess.com` gir «Logg inn på Skjold-hjem».

## Må testes i Xcode

1. Bygg. Koden er bare syntakssjekket (tree-sitter-swift), ikke typesjekket. Se særlig `LiveSync.swift`, `Backend.swift`, `Services.swift` og `LibraryView.swift`, og samtidighetsvarsler (`nonisolated`, `Sendable`, `Task`-fangster).
2. Bonjour: at `_kipultamp._tcp` dukker opp i «Finn forsterker», at modellen kommer fra TXT og at adressen løses opp (IPv4).
3. SSE: at status kommer straks ved endring (volumknapp på forsterkeren), og at appen faller tilbake til polling og viser «Frakoblet» når enheten slås av.
4. Volum- og spill/pause-glidere hopper ikke tilbake (hold-vinduet).
5. Rom med to enheter og Lyrion: gruppering (hake), volum per rom, bytte aktivt rom.
6. Navidrome/Plex: lister, cover, avspilling via forsterkeren, neste låt når strømmen er ferdig.
7. Oppdatering: «Se etter oppdatering» mot GitHub.

## Designregler (ikke bryt dem)

- **Fonter:** Sora (300/400/600) og IBM Plex Mono (400/500), aldri systemfont i egne visninger. Unntaket er systemets `TabView`-etiketter i glassmodus.
- **Farger:** bare tokens fra `Theme.swift`, aldri løse hex-verdier i ny kode. Valgt tilstand = `SelStyle.of(true)`.
- **Komponenter:** bruk komponentene i `Components.swift`, ikke `List`, `Form` eller standard `NavigationStack`-titler.
- **Haptikk:** knapper får trykk automatisk gjennom `PlainPress`. Nye kontroller skal bruke `Haptics.*`.
- **Fanelinje:** to design, valgt under Innstillinger → APPEN → Fanelinje (`m.tabStyle`: `"glass"` er standard, `"classic"` er alternativet).

## Kjente småfeil og gjenstående

- Siden hopper til toppen når du bytter fanelinje-design.
- Når fanelinjen er minimert i glassmodus, kommer den bare tilbake når du ruller helt til toppen. Det er systemets oppførsel.
- Produktbildene i velkomstkarusellen: S1-bildet er klippet ut av et skjermbilde (`hero-s1`), og Node vises som strektegning. Legg ekte bilder inn som `hero-01-s1`, `hero-03-s1`, `hero-02-node` og `hero-04-node` i Assets, så brukes de automatisk.
- Navidrome- og Lyrion-logoene er bokstavmerker. Legg inn `brand-navidrome` og `brand-lyrion` i Assets.
- `DeviceBrowser` gjetter modellen ut fra navnet bare når TXT-posten mangler `product`.

## Forslag til videre arbeid

1. Endepunkter i daemonen for oppdatering/backup, `forget`, `reset` og visning av oppsettsteg på skjermen.
2. YouTube Music-tjeneste (for eksempel ytmusicapi på forsterkeren) og UPnP.
3. Kø og seek i daemonen (eller via Lyrion `playlist add`), så køen ikke må ligge i appen.
4. Nøkkelring for Navidrome-passord og Plex-token.
5. Manuell IP-adresse i «Finn forsterker» (`m.connect("192.168.1.5")` finnes allerede).
