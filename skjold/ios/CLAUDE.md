# Skjold – iOS-app (SwiftUI)

Fjernkontroll-app for Skjold-lydsystemet: forsterkeren **Skjold S1** (Pi Zero 2 W, OLED, knapper), **Skjold Node** (Raspberry Pi med bare lydutgang) og **Skjold Core** (Lyrion-server). Rom synkroniseres av **Lyrion Music Server**.

**Status:** Hele brukergrensesnittet og app-logikken er ferdig og testet i simulatoren. Alle 20 skjermene fra designet finnes, pluss ekstra funksjoner (se lenger ned). **Det som mangler er koblingen til ekte data.** I dag kommer innholdet fra eksempeldata, og kommandoene sendes til et gjettet API. Jobben videre er å fylle inn de koblingene. Selve utseendet skal ikke endres.

---

## Bygg og kjør

- Xcode-prosjekt: `Skjold.xcodeproj`, scheme `Skjold`, ett mål (iPhone).
- iOS **26.0+** (Liquid Glass-API-ene krever iOS 26), bare iPhone, bare stående modus, bare mørk modus.
- Mappen `Skjold/` er synkronisert med målet, så nye `.swift`-filer der kommer automatisk med i bygget.
- Swift 5-modus med `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor`. Rene hjelpetyper uten UI er derfor merket `nonisolated` (for eksempel `SVGPathParser`, `RadioBrowser` og `PlexAPI`).
- Signering: personlig team `23A28PYU2U`, bundle-id `com.sebastiankristojemtlandpersonalteam.Skjold`.
- Info.plist: fontene ligger under `UIAppFonts`. I tillegg er `NSBonjourServices` satt til `_skjold._tcp`, `NSLocalNetworkUsageDescription` og `NSCameraUsageDescription` er fylt ut, og ATS har `NSAllowsLocalNetworking = true`.
- Bygget gir verken feil eller advarsler, både for simulator og for «Any iOS Device».

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
| `Services.swift` | `RadioBrowser` (ekte søk, logoer og strømtest), `PlexAPI.test` (ekte), `DeviceBrowser` (ekte Bonjour med `NWBrowser`), `DeviceLink` (**gjettet** REST, se under). |
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
| `SettingsView.swift` | 18–20 Innstillinger: kategorier per enhet, items, radiofavoritter, oppdatering/backup, standby-klokker (`ClockFace`), APPEN → valg av fanelinje. |

---

## Hva er ekte og hva er demo

**Ekte (fungerer nå):**
- Radio Browser-søk (`RadioBrowser.search`), logo-henting (`RadioBrowser.logo` / `LogoStore`) og strømtest (`RadioBrowser.testStream`, med AVPlayer).
- Bonjour-søk etter `_skjold._tcp` (`DeviceBrowser`). Funne enheter vises i oppsett steg 1, og velger du en, settes `DeviceLink.shared.host`.
- Plex-tilkoblingstest (`PlexAPI.test`, `GET {server}/library/sections?X-Plex-Token=`).
- Kameraskanning av QR-kode.
- Lagring av all lokal tilstand: radiofavoritter, EQ-profiler, innstillinger, navn, system og oppdatering.
- Hele UI-logikken: grupper, roller, EQ-profiler per kilde, favoritt-rekkefølge, haptikk og så videre.

**Demo, som må erstattes med ekte data:**
- **Rom og spillere:** `SK.sysDefault` (Stue, Kjøkken, Kontor, Hjemmekino), lagret i `sys`.
- **Hva som spiller:** `AppModel.np` bygges fra `SK.tr` (tre faste låter), `SK.nowPlayingMap` (radio) eller biblioteket. Spilleposisjonen telles lokalt i `start()`.
- **Bibliotekene** (YouTube Music, Navidrome, Plex): `SK.lt` og `SK.lib`. Det er de samme 12 demolåtene for alle tre.
- **Cover:** `art()` lager fargeforløp. Ekte omslag må komme fra Lyrion, tjenestene eller AirPlay-metadata.
- **Oppdatering:** `SK.releases` og `runJob` i `AppModel` simulerer GitHub-utgivelser, backup og gjenoppretting.
- **Oppsett:** Wi-Fi-listen (`AppModel.nets`) er fast, og programvaresteget teller bare til 100 %.
- **Innstillinger:** Info-felter som «Parede enheter», «Lyrion: Tilkoblet», IP og serienummer er faste verdier i `SettingsView.info()` og i `SK.cats`.
- **Når ingen enhet finnes:** «Finn forsterker» viser demokortene S1 og Node.
- **Lyrion i Kilder** åpner den faste adressen `http://192.168.1.42:9000/`.

---

## Koblinger som må fylles inn

### 1. Transport: `DeviceLink` (`Services.swift`)

I dag sender `DeviceLink.post(_:)` `POST http://<host>/api/<type>` med meldingen som JSON-kropp. Svar leses ikke. Alle handlinger i `AppModel` går gjennom `post([...])`. Meldingene er de samme som designfilen sendte på sin `BroadcastChannel`:

| Melding | Når |
|---|---|
| `setup {step, name, upd?}` | Steg i oppsettet (0, 1, 2, 3, 4, 6, 7, 8). |
| `setupTest {ch: "L"\|"R"}` | Høyttalertest i oppsettet. |
| `pause`, `next` | Spill/pause og neste låt. «Forrige» sender i dag ingenting. |
| `vol {v}` | Volum på aktivt rom. |
| `wl {v: "air"\|"bt"}` | Bytte til trådløs inngang. |
| `input {i}` | Bytte til fysisk inngang (1 = AUX, 2 = Radio, 3 = USB). |
| `src {v}` | Bytte radiokanal (indeks i favoritter). |
| `play {svc, t}` / `play {name, url}` | Spill fra bibliotek eller vilkårlig radiostrøm. |
| `presets {list}`, `radioSync` | Radiofavoritter endret. |
| `set {k, v}` | Innstilling endret (nøklene i `SK.cats` / `SK.def`, også `hold`). |
| `eqSync {src}` | EQ-profil endret. Profilen ligger i `eqP[src]`. |
| `sysSync` | Rom, grupper, roller eller volum endret (`sys`). |
| `btPair {room}` | Gjør Node eller Core synlig for Blåtann. |
| `previewClock` | Vis standby-klokke på forsterkeren. |
| `updSync {version}` | Etter oppdatering eller gjenoppretting. |
| Øvrige `act`-id-er | Sendes som `{type: id}`: `testSpk`, `testOut`, `forget`, `testVoice`, `ndTest`, `reset`. |

**Hva som trengs:**
- **Ekte API-beskrivelse:** README fra Skjold-prosjektet, eller kilden til webgrensesnittet. Uten den må endepunktene leses ut av enhetens egen kode.
- **Lesing tilbake:** en `GET`/WebSocket for status, i designet `{type:'state', ...}` med `hp`, `btDev`, `err`, `set` og mer. Tilstanden skal oppdatere `AppModel`, for eksempel `headphones`, `sset`, hva som spiller og volum.
- **Feilhåndtering:** frakoblet-tilstand i UI. Systemkortet viser i dag alltid «Tilkoblet».

### 2. Lyrion Music Server (anbefalt for rom, avspilling og synk)

Lyrion har et dokumentert JSON-RPC-API: `POST http://<server>:9000/jsonrpc.js` med `{"id":1,"method":"slim.request","params":[<playerid>, [<cmd>...]]}`. Det kan dekke:

- **Rom:** `players 0 100` gir spillerne, som skal fylle `sys.rooms`. Map `name`, `playerid` og modell til `type`.
- **Hva som spiller:** `status - 1 tags:aAlKdc` gir tittel, artist, album, varighet, tid, cover-URL (`/music/<coverid>/cover.jpg`) og volum. Fyll `np`, `position`, `duration` og `playing`, og bytt ut den lokale telleren i `start()`.
- **Kontroll:** `pause`, `playlist index +1` / `-1` og `mixer volume <n>`.
- **Synk:** `sync <playerid>` og `sync -`. Map til `toggledInGroup`, `groupedAll` og «Bare …».
- **Radio:** `playlist play <url> <title>`.
- **Kilder:** Lyrion-knappen i Kilder skal bruke den konfigurerte serveradressen i stedet for den faste.
- **Serveradresse:** legg inn et innstillingsfelt for adressen, eller finn serveren automatisk (Lyrion svarer på UDP 3483-discovery).

### 3. Bibliotekene (`LibraryView` / `SK.lib`)

- **Plex:** innstillingene `plexUrl`/`plexToken` ligger i `m.names`. Bruk `/library/sections` → `/library/sections/{id}/all?type=9` (album), `/playlists`, `/status/sessions` og `/library/metadata/{id}/children`. Cover hentes fra `{server}{thumb}?X-Plex-Token=`.
- **Navidrome:** Subsonic-API med `ndUrl`/`ndUser` (passord og token mangler i innstillingene). Bruk `getAlbumList2`, `getPlaylists` og `search3`.
- **YouTube Music:** cookie og konto ligger i `ytmUser`/`ytmCookie`. Ifølge designet skjer avspillingen på forsterkeren. Appen trenger bare å vise listene, enten via enhetens API eller via ytmusicapi.
- **Avspilling:** «Spill» i biblioteket skal sende til Lyrion eller enheten, ikke bare oppdatere `lq`/`li` lokalt.

### 4. Oppsett av ny enhet (`OnboardingView`)

- Steg 1: `DeviceBrowser` finner `_skjold._tcp`. Hent detaljer fra TXT-posten eller enhetens API (modell, serienummer, «ikke satt opp»).
- Wi-Fi-overføringen skal ifølge designet gå **kryptert over Blåtann** («Godta på forsterkeren med volumknappen»). Det krever CoreBluetooth og en GATT-tjeneste på enheten. Ingenting av dette er laget.
- Ekte Wi-Fi-liste, romnavn, høyttalertest og programvareoppdatering må gå mot enheten.

### 5. Oppdatering (`UpdateSettingsView` / `AppModel.checkUpdate` …)

Bytt ut simuleringen med GitHub Releases (`https://api.github.com/repos/skjold-audio/skjold-s1/releases`). Selve installasjon og backup må utføres av enheten.

---

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
- `DeviceBrowser` viser enhetsnavnet, men gjetter modellen ut fra navnet.
- `AVVIK.md` er utdatert og bør oppdateres.

## Forslag til rekkefølge

1. Lag `LyrionClient` (JSON-RPC) i `Services.swift`, med serveradresse i innstillingene og autodiscovery.
2. La `AppModel` hente spillere inn i `sys.rooms`, og polle `status` (eller bruke Comet/CLI) for `np`, posisjon, volum og cover.
3. Koble handlingene (`togglePlay`, `next`, `prev`, `setVol`, gruppefunksjonene, `playRadio`, `playLib`) til Lyrion. Behold `post(...)` for Skjold-spesifikke ting: innganger, EQ og innstillinger.
4. Ekte cover i `art()` / `ArtFill`, med URL fra Lyrion eller Plex.
5. Plex og Navidrome som ekte biblioteker.
6. Skjolds eget API når README-en finnes: innstillinger, EQ, innganger, oppsett og oppdatering.
7. Bestem om demodataene skal fjernes eller bli en tydelig merket demomodus.
