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

## Panel på høykant (for eksempel 4,58″ som melder 400 × 960)

Noen bar-paneler melder seg som stående over HDMI (`cat /sys/class/drm/card*-HDMI-A-1/modes` gir `400x960`). Legg da inn
i `/etc/ki-amp.env`:

```
SKJOLD_UI_PANEL=400x960
SKJOLD_UI_ROTATE=90
```

Kiosken åpner vinduet i panelets størrelse, og S1-bildet (960 × 320) dreies i nettleseren og sentreres på panelet.
Står bildet opp ned, bruk `SKJOLD_UI_ROTATE=270`. Panelet som melder `400x960` settes opp automatisk av
`install_skjold_ui.sh` (målt på S1: `SKJOLD_UI_H=332`, `SKJOLD_UI_SHIFT=31`), med mindre `SKJOLD_UI_PANEL` alt står i fila. Start på nytt med `sudo systemctl restart skjold-ui`.

`SKJOLD_UI_FIT=stretch` strekker bildet på tvers så det fyller panelets korte side (320 → 400) i stedet for svarte kanter.
Musepekeren skjules med et usynlig pekertema (`pi/tools/blank_cursor.py`, `XCURSOR_THEME=skjold-blank` i tjenesten, og kopiert til
`~/.icons/default` fordi cage ikke alltid leser `XCURSOR_THEME`), `WLR_NO_HARDWARE_CURSORS=1`, og
Chromium startes uten oversettelsestilbud.

Finjustering når kanten av panelet dekker en del av bildet: `SKJOLD_UI_H=380` setter bildets høyde i piksler (overstyrer
`SKJOLD_UI_FIT`), og `SKJOLD_UI_SHIFT=10` flytter bildet 10 piksler opp (negativt tall = ned).

## Skjermsparer i standby

Med «Klokke i standby» på og klokkestil 0–5 viser baren en stille fjord-loop (`web/media/fjord.webm`, 960 × 320, VP9)
med klokka over fjellet til venstre. Et helt bilde skjuler baklyset, som ellers gjør en svart flate grå. Stil 6–15
er designets egne brede skjermer, og nattmodus viser «Nattlys». «Klokke i standby» av gir svart skjerm.

## Skjermen av (sway)

Kiosken kjører i **sway** (standard) i stedet for cage, fordi sway kan slå HDMI-panelet av med DPMS mens bildet og
nettleseren kjører videre. cage avslutter når den eneste skjermen slås av. Med «Klokke i standby» **av** slås panelet
helt av i standby og når «Slukk etter» slår inn, og på igjen ved første knapp, hjul eller endring fra daemonen.
Med klokka på vises klokka/skjermspareren som før. Siden ber om det via `POST /ui/screen {"on": bool}`
(`swaymsg output * power off|on`). Tilbake til cage: `SKJOLD_UI_WM=cage` i `/etc/ki-amp.env`.
