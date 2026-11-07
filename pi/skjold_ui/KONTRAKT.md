# skjold-ui – kontrakt mot daemonen og skjold-input

§ 1–3 gjelder S1 (960 × 320). § 4 er Skjold Radio (800 × 480).

skjold-ui (`python3 -m skjold_ui`, port **127.0.0.1:8766**) tegner S1-skjermen. Den leser daemonen og tar imot
knappehendelser. Den eier selv to ting: innstillingsmenyen på skjermen (designets `curList`/`setAct`) og
engangshilsenen. Alt annet (kilde, volum, paring, nattmodus, omstart) eier daemonen og skjold-input.

## 1. Fra daemonen (leses via skjold-ui sin proxy: `/api/status`, `/api/events`, `/api/settings`)
Feltene som brukes (alle valgfrie – mangler de, tegnes det uten):

| Felt | Brukes til |
|---|---|
| `power`, `input` (`airplay`/`bt`/`spotify`/`upnp`/`plex` → AirPlay-brikken, `aux`/`aux2`, `radio`, `usb`), `usb_pc` (1/2) | kildebrikker, AUX 1/2 og PC 1/2 |
| `volume`, `mute`, `headphones` | volum, volumoverlay (vises 2,2 s når `volume` endres), «DEMPET», «HODETELEFON» |
| `playing`, `title`, `artist`, `duration`, `position`, `airplay_device` | tittel, undertekst, fremdriftslinje |
| `presets` [{n,title}], `radio_now` {name, now, n} | favorittbrikker og radio-omslag |
| `hold` {key: knob\|src\|radio\|reboot, p: 0–1, saved?} | hold-ringen (`drawBarSys`); `saved` = «Lagret»-bekreftelse |
| `rebooting` | omstart-animasjonen |
| `bt_pairing` | BT-paring (`drawBarBT`); når den slår seg av: «avbrutt»-visning |
| `night` {on, src, steps:[{name,done}]} | nattmodus-skjermen når `on` endres; månen ved klokka |
| `overtemp`, `lyrion` | feil (overoppheting, Lyrion borte i radio) |
| `input_seq` | nullstiller dimme-tidtakeren |
| `name` | enhetsnavnet i hilsen/standby |
| `home` {weather, sun, cal, photo, caption, alarm} | data til standby-stilene 9, 11, 13, 14, 15 (samme form som `WIDE_DEF` i skjold_settings.js). Mangler data, vises «Dato» (5) i stedet. |
| `/api/settings` → nøklene i `SDEF` | klokkestil, dimming, LED-nivå osv. Endringer i menyen på skjermen sendes tilbake med POST `/api/settings`. |

Daemonens SSE (`/api/events`): en melding med et status-objekt tegnes direkte; alt annet utløser en ny `GET /api/status`.

## 2. Knapper og hjul: skjold-input → skjold-ui
skjold-input sender **hver** fysiske hendelse hit før den gjør noe selv:

```
POST http://127.0.0.1:8766/ui/event
{"ev": "press" | "turn" | "hold" | "back" | "menu_toggle", "src": "knob" | "power" | "air" | "aux" | "radio" | "usb", "d": 1 | -1}
→ {"consumed": true | false}
```

Er `consumed` **true**, skal skjold-input **ikke** utføre handlingen. skjold-ui bruker en hendelse når:
1. **Hilsenen vises** (`/etc/skjold/greeting.json` er `armed`): første `press`/`turn`/`hold` lukker den. Fila skrives
   som `shown` med fsync *før* skjermen bytter. Knappen gjør ikke sin vanlige handling.
2. **Hold volumhjulet 1,5 s** (`{"ev":"hold","src":"knob"}`) eller `menu_toggle`: åpner/lukker innstillingsmenyen.
3. **Menyen er åpen**: `turn`/`press`/`back` fra hjulet navigerer i menyen; et trykk på en kildeknapp = tilbake.

`GET /ui` → `{"menu": bool, "setup": bool, "bday": bool, "greeting": "armed|shown|none"}` for den som vil sjekke selv.
Hjulet styrer volum (daemonen) bare når `consumed` er false.

## 3. Hilsenen
- `GET /greeting` → `{"name","state":"armed|shown|none"}`
- `POST /greeting {"name":"Pappa","state":"armed"}` – web-UI → Innstillinger → Hilsen → Installer
- `POST /greeting/dismiss` – samme som et knappetrykk mens hilsenen vises
Fil: `/etc/skjold/greeting.json` (`SKJOLD_GREETING` overstyrer).

## 4. Skjold Radio (800 × 480, `SKJOLD_UI_LAYOUT=radio`)
**Oppsett.** `web/layout.js` velger oppsett før noe annet lastes: `?layout=radio|s1`, ellers radio når vinduet er ca. 5:3
(forhold 1,45–1,9) og S1 ellers. Med `SKJOLD_UI_LAYOUT=radio` (i `/etc/ki-amp.env`, skrevet av
`SKJOLD_UI_LAYOUT=radio install_skjold_ui.sh`) åpner kiosken `/?layout=radio` i 800 × 480. Radioskjermen er `web/radio.js` + `web/radio.css`.

**Fra daemonen** (bare eksisterende endepunkter, via proxyen): `/api/status` og `/api/events` (`power`, `input`, `inputs`, `volume`,
`mute`, `headphones`, `playing`, `title`, `artist`, `album`, `duration`, `position`, `cover_url`, `airplay_device`, `bt_device`,
`presets` [{n,title,logo}], `preset`, `radio_now` {name, now, n, genre, logo}, `source_label`, `sleep`, `name`, `version`),
`/api/settings` (`bright`, `clock`), `/api/plugins` (sovetimer og vekkerklokke), `/api/radio/browse`, `/api/medialib`, `/api/wifi`.
Handlinger fra menyen og touch: `POST /api/presets/{n}/play`, `/api/radio/play`, `/api/input`, `/api/transport`,
`/api/plugins/sleep`, `/api/plugins/alarm`, `/api/medialib/{kind}/play`, `/api/settings`.

**Knappene** (`skjold_radio_knapper.py`) sender `POST /ui/event` før de gjør noe, med `src` = `wheel` | `preset` | `power` | `volume`:

| Hendelse | Meny lukket | Meny åpen |
|---|---|---|
| `{"ev":"hold","src":"wheel"}` (hold hjulet 0,8 s) | `menu_toggle` → menyen åpnes · brukt | `back` · brukt |
| `{"ev":"turn","src":"wheel","d":±1}` | ikke brukt (knappetjenesten blar i favorittene); skjermen får `{"ev":"browse","d":±1}` | sendes videre · brukt |
| `{"ev":"press","src":"wheel"}` | ikke brukt (spill/pause) | sendes videre (velg) · brukt |
| `{"ev":"press","src":"preset","n":3}` | ikke brukt; skjermen får `{"ev":"preset","n":3}` (blink, lukker menyen) | samme |
| `{"ev":"saved","src":"preset","n":3}` (etter hold 2 s og lagring) | skjermen får `{"ev":"saved","n":3}` («Lagret som favoritt 3») | samme |
| av/på og volum | ikke brukt | ikke brukt |

Hilsenen (§ 3) bruker fortsatt første trykk. Skjermen melder menyen med `POST /ui/state {"menu": bool}` som før.

**Ekstra i skjold-ui for radioen:** `GET /ui/net` → `{"host","ip"}` (Innstillinger → Nettverk) og `POST /ui/backlight {"level": 0–1}`,
som skriver til `/sys/class/backlight/*/brightness` (udev-regelen fra installasjonen gir skrivetilgang). Uten baklys dimmes det med CSS.

**Test og skjermbilder:** `node pi/skjold_ui/test_render.js <mappe> radio` tegner skjermene med en falsk daemon og sjekker at
favorittbrikkene står over knappene, menypunktene og at hjulet navigerer. `pi/tests/test_skjold_ui_radio.py` tester `/ui/event`.
