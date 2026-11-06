# skjold-ui – kontrakt mot daemonen og skjold-input

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
