# Skjold S1 rev F – maskinvare og logikk

Rev F bygges av ferdigmoduler. Programvaren er den vanlige daemonen (`ki_amp_daemon.py`) med `KI_AMP_BOARD=s1f`:
lyd og strøm går som Skjold Kit, og knapper, volumhjul, LED-ringer, relé, USB-switch og hodetelefondetekt styres av
`skjold_s1f.py`. Skjermen (960 × 320 på HDMI) tegnes av en egen prosess (`skjold-ui`) som leser `/api/status`.

Installer: `KI_AMP_BOARD=s1f bash pi/install.sh` (ny Pi) eller `bash pi/update.sh` (allerede installert).

## Lydbanen

| Fra | Til |
|---|---|
| AirPlay, Blåtann, Radio (Lyrion), Spotify, USB (PC 1/2) | ALSA-loopback → CamillaDSP (EQ, volum) → PCM5102 (I²S) → jordsløyfeisolator → TPA3116 |
| AUX 1 (3,5 mm) | linjeinngang UCA202 #1 → `alsaloop` (ki-aux1) → samme kjede |
| AUX 2 (3,5 mm) | linjeinngang UCA202 #2 → `alsaloop` (ki-aux2) → samme kjede |
| Hodetelefon | UCA202 #1 sin hodetelefonutgang. Når pluggen står i, spiller CamillaDSP til UCA202 #1 i stedet for PCM5102, og reléet slår av høyttalerne. Eget volum når «Eget volum for hodetelefoner» er på. |
| PC 1 / PC 2 | Pi-ens USB-C som USB-lydkort (dwc2-gadget) via UGREEN-switchen. USB-knappen bytter PC og pulser switchens knapp. |

De to UCA202 er like, så de får faste navn etter USB-port: `sudo bash pi/tools/s1f_uca202_udev.sh` lager
`/etc/udev/rules.d/85-skjold-uca202.rules` (`UCA_AUX1` i laveste port, `UCA_AUX2` i den andre). Bytt med `--swap`.
Overstyr med `KI_AMP_AUX1_DEV`, `KI_AMP_AUX2_DEV` og `KI_AMP_HP_DEV` i `/etc/ki-amp.env`.

## Pinner (forslag, `pi/config/s1f_pins.yaml`)

Knapper til GND (intern pull-up), LED-ringer via transistor. Opptatt: I²S 18/19/21, I²C 2/3 og 0/1 holdes ledige.
SPI og UART er av.

| Funksjon | GPIO | Fysisk pinne |
|---|---|---|
| Knapp BT/AirPlay | 5 | 29 |
| Knapp AUX | 6 | 31 |
| Knapp RADIO | 13 | 33 |
| Knapp USB | 16 | 36 |
| Knapp power | 17 | 11 |
| LED BT/AirPlay | 22 | 15 |
| LED AUX | 23 | 16 |
| LED RADIO | 24 | 18 |
| LED USB | 25 | 22 |
| LED power (PWM0) | 12 | 32 |
| Volumhjul A / B / trykk | 9 / 10 / 11 | 21 / 19 / 23 |
| Relé (24 V til forsterker) | 27 | 13 |
| PCM5102 XSMT | 4 | 7 |
| USB-switch puls / avlesning | 14 / 15 | 8 / 10 |
| Hodetelefondetekt | 26 | 37 |

Test uten resten av Skjold: `sudo systemctl stop ki-amp && python3 pi/tools/s1f_inputtest.py`.

## Knapper (fasit: `pultforsterker_revb_metall.js`, `BETJENING.md`)

| Knapp | Trykk | Hold |
|---|---|---|
| Volumhjul | vri = volum (meny: bla) · 1 = demp (meny: velg) · 2 = neste · 3 = forrige | 1,5 s = innstillinger |
| BT/AirPlay | veksle AirPlay ↔ Blåtann; fra annen kilde: sist brukte; under paring: avbryt | 2 s = Blåtann-paring (60 s) |
| AUX | velg AUX, igjen = AUX 1/2 | |
| RADIO | velg radio, igjen = neste favoritt | 3 s = lagre kanalen (ring etter 0,9 s) |
| USB | velg USB, igjen = PC 1/2 + puls til switchen | |
| Power | 1 = standby av/på (etter 380 ms) · 2 = nattmodus | 3 s = omstart |

Hold-ringen vises etter 0,35 s. Første trykk når bursdagshilsenen vises lukker den og gjør ingenting annet.
LED: valgt kilde lyser (lysstyrke fra innstillingene), BT blinker 350 ms under paring, power blinker under omstart og 3 ganger ved nattmodus.

## Status til skjermen (`/api/status`)

```json
"ui": {"screen": "main|standby|settings|pairing|greeting", "sel": 0, "edit": false,
       "hold": {"kind": "pair|save|reboot|settings", "p": 0.42}, "overlay": {"type": "volume"}},
"night": true, "night_ev": {"on": true, "src": "Skjold|Home Assistant|Homey|Appen", "steps": [{"name": "Lys av", "done": true}], "t": 0},
"greeting": {"name": "Pappa", "state": "armed"},
"last_event": {"type": "event", "name": "power_double_press", "action": "nattmodus", "device": "Skjold S1", "seq": 3},
"headphones": false, "hp_volume": 30, "settings_menu": {…}, "hw_rev": "F"
```

`settings_menu` er den eksisterende innstillingsmenyen (rader, valgt rad). `night_ev.t` brukes til å vise
nattmodus-animasjonen én gang per endring.

## Nattmodus

`POST /api/night {"on": true, "src": "Appen"}` (uten `on` = veksle). Dobbelttrykk på power gjør det samme når
«Dobbelttrykk power» = Nattmodus. MQTT-broen (plugin «MQTT») sender HA discovery for:

- `device_trigger` `button_double_press` / `power` (og `button_short_press`) på `skjold/<id>/event/power`
- `event.<navn>_power` med `single_press`, `double_press`, `long_press`
- `button` «Nattmodus» (`skjold/<id>/set/night_trigger`) og `switch` «Nattmodus» (`…/set/night`, tilstand `…/night`, retained)
- steg live på `skjold/<id>/night/steps`: `[{"name": "Lys av", "done": true}]`

Endringer utenfra med samme verdi ignoreres (ingen ekko). Home Assistant-integrasjonen har i tillegg `switch` Nattmodus
og en `event`-entitet for power-knappen, og Homey-appen har `night_mode` og flow-kortene «Power-knappen ble dobbelttrykket»,
«Nattmodus ble slått på/av» og «Start nattmodus».

## WebSocket `/api/ws`

Samme meldinger som prototypen: serveren sender `{"type": "state", …, "status": {…}}` ved hver endring. Klienten kan sende
`input {i}`, `wl {v}`, `src {v}`, `vol {v}`, `mute`, `power`, `pause`, `next`, `set {k, v}`, `presets {list}`, `forget`, `reset`,
`setup`/`setupTest {ch}`, `testVoice`, `previewClock`, `updSync`, `nightMode` og `nightState {on, src, steps}`.

## Bursdagshilsen

`/etc/skjold/greeting.json` `{"name": "Pappa", "state": "armed"|"shown"|"off"}`. `POST /api/greeting {"name": "Pappa", "action": "install"}`
arms den. Status har `greeting` så lenge den skal vises. Første knappetrykk eller vri setter `shown` (skrevet med fsync) før noe annet skjer.
