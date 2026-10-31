# Skjold OS

Skjerm-UI-et på Skjold Node (1,8″ ST7735S, 160 × 128, liggende). Gjenskapt fra
`skjold/design/node/Skjold Node OS.dc.html`, `node_fx.js`, `felles/skjold_welcome.js` og
klokkestilene i `felles/skjold_settings.js`.

## Ansvarsdeling
| Hvem | Eier |
|---|---|
| `pi/ki_amp_daemon.py` (`KI_AMP_BOARD=node`) | knapper, encoder, LED-ringer (GPIO 5,6,12,13,16,17,20,21,22,26,27), lyd, API på 127.0.0.1:8765 |
| Skjold OS (`skjold-os.service`) | SPI-skjermen (CE0, DC=GPIO25, RST=GPIO24) og bakgrunnslyset GPIO23 (aktiv lav via Q1) |

Skjold OS rører ingen knappe-/LED-pinner. Den poller `GET /api/status` (8 Hz) og `GET /api/settings` (~hvert 3. s),
og `GET /api/cover` når `status.cover` endres.

## Skjermer
| Skjerm | Kilde i status |
|---|---|
| Oppstart (splash) | lokal, 2,6 s ved start |
| Velkomst | `/var/lib/skjold/velkomst.json` (`skjold-velkomst`); lukkes ved første endring i status (= et trykk), fila slettes |
| Spiller nå | `input`, `title`, `artist`, `station`, `preset`/`presets`, `duration`/`position`, `paused`, `bt_device`, cover |
| Volum nederst 1,5 s | endring i `volume`/`mute` |
| Kildebytte-animasjon | endring i `input` (ikonrekkefølge fra `inputs`) |
| Blåtann-paring | `bt_pairing` (fremdrift regnes lokalt over 120 s) |
| Radiomeny | `menu` (hvis daemonen eksponerer den) |
| Innstillinger (skrivebeskyttet oversikt, 15 s) | `ui_event = {"name":"settings","t":…}` |
| Omstart | `rebooting: true` (krever nytt felt) + CRT-kollaps når tjenesten stoppes |
| Standby-klokke | `power=false`, eller ikke spiller og 2 min uten endring; stil = `settings.clockStyle` (0 = Node-designets store klokke, 1–5 = felles stiler) |
| Ingen kontakt | API svarer ikke i 3 s |

Bakgrunnslys: `settings.dim` (Av/30 s/1 min → 25 %), `settings.off` (Av/2 min/5 min → av, ikke mens noe spiller),
`settings.bright` (Auto/Høy/Middels/Lav) hvis den finnes.

## Arkitektur
```
skjold_os/
  gfx.py        tegnemotor: Pillow-lerret i logiske px, 3× supersampling, tokens, DejaVu som Helvetica-erstatning
  fx.py         splash, omstart, kildebytte, velkomst, 6 klokkestiler, kildeikoner
  sources.py    kildenavn/-farger (Spotify #1ed760 osv.)
  app.py        tilstandsmaskin: status → ViewModel → layout; bakgrunnslys; løkke (20 fps under animasjon, 6 ellers, sender bare endrede rammer)
  layouts/      én layout per skjerm: node.py (160×128, ferdig), s1.py (KROK for S1 128×64 OLED / 320×240 TFT – se docstring)
  display.py    luma.lcd st7735 (rotate/bgr/offset fra node_pins.json) eller PNG; gpiozero PWMLED for GPIO23
  api.py        poller (bare standardbiblioteket)
  demo.py       falsk daemon for --demo/--shots
```
Ny skjermstørrelse = ny klasse i `layouts/` med `draw_<screen>(canvas, vm)`; ViewModel-en er felles.

## Kjøring
```
python3 -m skjold_os                       # maskinvare (systemd gjør dette)
python3 -m skjold_os --sim /tmp/ui         # mot daemonen, rammer → /tmp/ui/latest.png (--every N for sekvens)
python3 -m skjold_os --sim /tmp/ui --demo  # uten daemon: sykler gjennom alle tilstandene
python3 -m skjold_os --shots /tmp/shots    # nøkkelskjermene som PNG (+ @4x), pluss live hvis daemonen svarer
  --api http://127.0.0.1:8799  --layout node|s1-oled|s1-tft  --no-boot
```
Pinner leses fra `$SKJOLD_PINS`, `/etc/skjold/node_pins.json` eller repoets `skjold/node/config/node_pins.json`.

## Installasjon
`sudo skjold/os/install.sh` – kopierer til `/opt/skjold/os`, installerer og starter `skjold-os.service`
(`/opt/skjold/venv/bin/python -m skjold_os`, After=ki-amp.service). Ekstra argumenter i `/etc/default/skjold-os`.
Fra `skjold/node/driver/installer_node.sh`: `"$HER/../os/install.sh"`.

## Skjold S1 (`--layout s1-oled` / `s1-tft`)
Fra `skjold/design/s1/pultforsterker_revb_metall.js` (drawOLED0, drawTFT0, overlay()).
- `layouts/s1_oled.py` – 128×64 SSD1309, ren 1-bit på pikselrutenettet (`MonoCanvas`: ingen supersampling,
  DejaVu uten kantutjevning med BASIC-layout, egen 5 px pikselfont for versal-etikettene, prikkede spor).
- `layouts/s1_tft.py` – 320×240; overleggene er de samme 128×64-tegningene skalert 2,5× fra y=40, som i designet.
- `layouts/s1_common.py` – omstart, paring, hold/«Lagret», meny/radiomeny, kildebytte, ingen kontakt, oppstart.
- `display_s1.py` – luma.oled ssd1309 (I²C 1, 0x3C, RST GPIO4; kontrast i stedet for bakgrunnslys) og
  fbtft-framebuffer (RGB565), samme oppsett som `pi/oled_display.py`/`pi/tft_screen.py`.
