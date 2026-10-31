# Skjold Node – kabling og drivere

Felles kilde for alle pinner: **`config/node_pins.json`**. SVG og kabelliste er generert fra den.

| Fil | Hva |
|---|---|
| `config/node_pins.json` | Pinner, keycodes, holdetider, LED-/bakgrunnslysdrift. Leses av skjold-ui, selvtesten og bruksanvisningen. |
| `config/config.txt.node` | Tillegg til `/boot/firmware/config.txt` (SPI, lyd, I²C, startnivå på pinnene). |
| `kabling_node.svg` | Koblingsskjema: header, skjerm, Q1, encoder, 4 knapper, 4 LED-ringer. Fargekodet. |
| `kabelliste.csv` | Ledning for ledning: fra, til, nett, farge, lengde, pluggtype. |
| `driver/installer_node.sh` | Legger config-blokken inn i config.txt, installerer gpiozero/lgpio/luma.lcd. Brukes av pi-gen. |
| `tools/lag_kabling.py` | Lager SVG + CSV fra json. Kjør etter hver pinneendring. |
| `tools/sjekk_konsistens.py` | Sjekker json mot csv, svg og config.txt (BCM→pinne, GND-pinner, reserverte GPIO). |
| `tools/node_selftest.py` | Testbilde, knapper/encoder på skjermen, blinker LED-ringene. `--dry-run` uten Pi. |

```sh
python3 tools/lag_kabling.py && python3 tools/sjekk_konsistens.py
python3 tools/node_selftest.py --dry-run --ut /tmp/st   # PNG-er av skjermbildene
sudo ./driver/installer_node.sh && sudo reboot            # på Pi-en
/opt/skjold/venv/bin/python tools/node_selftest.py
```

## Pinner (BCM / fysisk)
| Funksjon | GPIO | Pinne | Farge |
|---|---|---|---|
| TFT VCC | 3V3 | 17 | rød |
| TFT GND | GND | 20 | sort |
| TFT SCK | GPIO11 SPI0 SCLK | 23 | gul |
| TFT SDA | GPIO10 SPI0 MOSI | 19 | gul |
| TFT CS | GPIO8 SPI0 CE0 | 24 | gul |
| TFT A0/DC | GPIO25 | 22 | gul |
| TFT RESET | GPIO24 | 18 | gul |
| Bakgrunnslys (Q1 gate) | GPIO23 | 16 | oransje |
| Q1 source | 3V3 | 1 | rød |
| Encoder A / B / SW | GPIO17 / 27 / 22 | 11 / 13 / 15 | blå |
| Encoder C (+ SW2) | GND | 9 | sort |
| RADIO / AIR·BT / ◀◀ / ▶▶ | GPIO5 / 6 / 13 / 26 | 29 / 31 / 33 / 37 | grønn |
| Knapper felles C | GND | 39 | sort |
| LED-ring RADIO / AIR·BT / ◀◀ / ▶▶ (valgfri) | GPIO12 / 16 / 20 / 21 | 32 / 36 / 38 / 40 | oransje |
| LED-ringer felles − | GND | 34 | sort |

## Endringer fra forslaget i oppgaven, og hvorfor
- **Bakgrunnslys GPIO18 → GPIO23.** Analog 3,5 mm-lyd bruker PWM0/PWM1, så maskinvare-PWM på GPIO12/13/18/19 er opptatt
  (og `dtoverlay=pwm` ville slått av analog lyd). Dimming gjøres med programvare-PWM, som går på hvilken som helst pinne.
  GPIO18/19 holdes da ledige for et eventuelt I²S-kort.
- **Bakgrunnslyset går via Q1 (AO3401 P-MOSFET, high-side)**, ikke low-side: på 8-pinners ST7735-moduler er LED-katoden
  koblet til GND på kortet, så bare anoden (LED-pinnen) er tilgjengelig. Q1: source ← 3V3, drain → LED, gate ← GPIO23 via 1 kΩ,
  10 kΩ gate→source. GPIO23 lav = lys på (`active_high=False`, `gpio=23=op,dh` i config.txt holder det av ved oppstart).
  Modulen trekker typisk 20–40 mA, over Pi-ens 16 mA per pinne. Under 10 mA kan GPIO23 drive LED direkte.
- **TFT VCC på pinne 17, GND på 20** (ikke 1/6), så alle skjermledninger samles i ett felt (pinne 16–24). Pinne 1 brukes til Q1.
- **GND-skinne:** encoder → 9, skjerm → 20, LED-ringer → 34, knapper → 39. Knappene og ringene lenkes med 20 mm broer, så det
  går én GND-ledning per gruppe.
- Ingen konflikt med I²C (GPIO2/3, holdes på for S1/Node-gjenkjenning), UART (14/15), HAT-EEPROM (0/1), SPI0 CE1/MISO (7/9).
  Blåtann/Wi-Fi på Pi 3/4 bruker ingen header-pinner. Samme pinner på Pi 4, 3B og 3B+.
- **I²S senere:** GPIO18/19 er ledige. LED-ringene ◀◀/▶▶ på GPIO20/21 må da flyttes (se `leds._i2s_merknad`).

## LED-ringer
Bruk 3–6 V-varianten (innebygd motstand for ca. 5 V). 12 V-varianten lyser ikke på 3,3 V. Drift «direkte»: GPIO → 270 Ω → LED+,
LED− → GND gir maks 4,8 mA (rød/grønn/gul). Blå/hvit ring (Vf ≈ 3 V) blir svak; bruk da 100 Ω eller en 2N7002 per ring med LED+ på 5 V.

## Drivervalg
- **Skjerm: luma.lcd** (`st7735`, rotate=2) fra Python, ikke fbtft. fbtft er markert foreldet i kjernen, gir et framebuffer
  som skjold-ui uansett må tegne til via PIL, og låser pinnene. luma gir rotasjon, offset og BGR-valg i kode, deler
  tegnemotor (PIL) med S1-OLED-en og kan testes uten Pi. fbtft-linjen står kommentert i `config.txt.node` for feilsøking.
- **Knapper og encoder: gpiozero** (lgpio) i skjold-ui (alternativ A). Hold-tider og «hold begge» krever egen logikk uansett,
  og koden blir lik S1. `rotary-encoder` + `gpio-key`-overlays med keycodes står som alternativ B (kommentert ut) – aldri begge.

## Oppførsel (skjold-ui)
Encoder: vri = volum, trykk = demp/pause, hold 3 s = innstillinger. RADIO: trykk = neste favoritt, hold = spill valgt.
AIR/BT: trykk = bytt AirPlay/Blåtann, hold 2 s = paring. ◀◀/▶▶: forrige/neste (opp/ned i menyer), hold begge = omstart.
Første trykk når velkomsthilsenen vises lukker den og gjør ingenting annet.

## Må bekreftes
Bekreftet: encoder-trykk = pause/spill; skjermmodulen er 3,3 V; EC11 er 5-pinners, 20 posisjoner (20/20), 15 mm halvflat aksel.

1. Strøm i skjermens LED-pinne (trengs Q1?).
2. ST7735-variant: `h_offset`/`v_offset`/`bgr` – se fargestripene i selvtesten.
3. Hvilken ende av skjerm-PCB-en loddeøyene sitter på (påvirker lengdene litt; alle er ≤ 15 cm).
4. LED-ringens farge (variant 3–6 V er bekreftet).
