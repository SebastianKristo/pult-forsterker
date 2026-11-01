# Skjold Node – kabling og drivere (rev C, OLED-utgave)

Felles kilde for alle pinner: **`config/node_pins.json`** (schema 2). SVG og kabelliste er generert fra den.
Kassen: `skjold/design/node/Skjold Node kasse OLED.html` / `… OLED taktil.html` (lokk for 0,91″ OLED; bunn som før).

| Fil | Hva |
|---|---|
| `config/node_pins.json` | Pinner, I²C-adresser, ADS1115/potmeter, holdetider, LED-drift. Leses av ki_amp_daemon.py (`KI_AMP_BOARD=node`), Skjold OS, selvtesten og bruksanvisningen. |
| `config/config.txt.node` | Tillegg til `/boot/firmware/config.txt`: I²C på (400 kHz), **SPI av**, 3,5 mm-lyd, startnivå på pinnene. |
| `kabling_node.svg` | Koblingsskjema: header, OLED, ADS1115, potmeter, 4 knapper, 4 LED-ringer. Fargekodet. |
| `kabelliste.csv` | Ledning for ledning: fra, til, nett, farge, lengde, pluggtype. |
| `driver/installer_node.sh` | config-blokken, I²C (`raspi-config nonint do_i2c 0`), i2c-tools, gpiozero/lgpio, luma.oled + smbus2, `SKJOLD_OS_ARGS=--layout node-oled32`, Skjold OS. |
| `tools/lag_kabling.py` | Lager SVG + CSV fra json. Kjør etter hver pinneendring. |
| `tools/sjekk_konsistens.py` | Sjekker json mot csv, svg og config.txt (BCM→pinne, GND/3V3, reserverte GPIO, SPI av). |
| `tools/node_selftest.py` | Testbilde på OLED-en, live potmeter via ADS1115, knapper, blinker LED-ringene. `--dry-run` uten Pi. |

```sh
python3 tools/lag_kabling.py && python3 tools/sjekk_konsistens.py
python3 tools/node_selftest.py --dry-run --ut /tmp/st     # PNG-er av skjermbildene (×4)
sudo ./driver/installer_node.sh && sudo reboot              # på Pi-en
i2cdetect -y 1                                              # skal vise 3c (OLED) og 48 (ADS1115)
sudo systemctl stop ki-amp skjold-os && /opt/skjold/venv/bin/python tools/node_selftest.py
```

## Pinner (BCM / fysisk)
| Funksjon | GPIO | Pinne | Farge |
|---|---|---|---|
| OLED VCC | 3V3 | 1 | rød |
| OLED SDA | GPIO2 (I²C1 SDA) | 3 | gul |
| OLED SCL | GPIO3 (I²C1 SCL) | 5 | gul |
| OLED GND | GND | 9 | sort |
| ADS1115 VDD | 3V3 | 17 | rød |
| ADS1115 GND (ADDR broet til GND → 0x48) | GND | 25 | sort |
| ADS1115 SDA / SCL | kjedet fra OLED-ens SDA / SCL | – | gul |
| Potmeter B10K pinne 1 / 2 (glider) / 3 | ADS GND / ADS A0 / ADS VDD | – | sort / blå / rød |
| Knapp RADIO | GPIO23 | 16 | grønn |
| Knapp AIR / BT | GPIO24 | 18 | grønn |
| Knapp ◀◀ forrige | GPIO25 | 22 | grønn |
| Knapp ▶▶ neste | GPIO7 (SPI0 CE1 – SPI er av) | 26 | grønn |
| Knapper felles C | GND | 30 | sort |
| LED-ring RADIO / AIR·BT / ◀◀ / ▶▶ (via 330 Ω) | GPIO12 / 16 / 20 / 21 | 32 / 36 / 38 / 40 | oransje |
| LED-ringer felles − | GND | 34 | sort |

I²C-adresser: OLED SSD1306 **0x3C**, ADS1115 **0x48**. Begge modulene har egne pull-up-motstander; ingen ekstra trengs.

## Viktige merknader
- **SPI må være AV.** GPIO7 er SPI0 CE1. Med `dtparam=spi=on` tar spidev-driveren pinnen, og knappen ▶▶ gir
  «Device or resource busy». `config.txt.node` har `dtparam=spi=off`, og `installer_node.sh` fjerner gamle `dtparam=spi=on`
  fra rev A/B (TFT).
- **GPIO20/21 = I²S PCM_DIN/DOUT.** LED-ringene ◀◀/▶▶ kolliderer med et I²S-lydkort (HiFiBerry o.l.). Skal Node få I²S-DAC,
  må de to ringene flyttes (f.eks. til GPIO5/6, pinne 29/31) og `node_pins.json` oppdateres. GPIO18/19 holdes ledige.
- **I²C deles:** Skjold OS skriver til OLED-en (luma.oled), ki-amp leser ADS1115 (smbus2). Ingen av dem låser bussen;
  hver overføring er én atomisk transaksjon i kjernen. Ikke legg til `dtoverlay=i2c-gpio` eller andre drivere på 0x3C/0x48.
- 3,5 mm-lyden bruker PWM0/1 internt, så LED-ringene dimmes med programvare-PWM (gpiozero). Ikke legg til `dtoverlay=pwm`.
- Samme pinner på Pi 4, 3B og 3B+. Blåtann/Wi-Fi bruker ingen header-pinner. UART (14/15) og HAT-EEPROM (0/1) er ledige.

## Potmeter (volum)
10 kΩ lineært (B10K): pinne 1 → GND, pinne 2 (glider) → A0, pinne 3 → VDD (3,3 V). ADS1115 i kontinuerlig modus,
±4,096 V, 128 SPS, lest ~20 Hz av ki-amp. 0–3,3 V → volum 0–100 med glatting (0,35), dødsone 1,5 % i endene og hysterese ±2.
Volumet settes **bare når knotten flyttes**: volum fra appen/AirPlay står til knotten vris igjen, og da tar knotten over
fra sin egen posisjon («soft takeover»). Første måling etter oppstart rører ikke volumet. Mangler ADS1115, virker alt annet
(nytt forsøk hvert 10. s). Feil retning: sett `potmeter.inverter=true` eller bytt pinne 1 og 3.

## LED-ringer
Bruk 3–6 V-varianten (innebygd motstand for ca. 5 V). 12 V-varianten lyser ikke på 3,3 V. GPIO → 330 Ω → LED+, LED− → GND:
under 4 mA per ring (rød/grønn/gul). Pi-grense 16 mA per pinne, 50 mA totalt.

## Oppførsel (ki_amp_daemon.py, `KI_AMP_BOARD=node`)
| Knapp | Trykk | Hold |
|---|---|---|
| Potmeter | volum (bare når den flyttes) | – |
| RADIO | radio / neste favoritt (meny på skjermen) | 1 s: spill valgt favoritt (tom plass + radio spiller = lagre) |
| AIR / BT | AirPlay ↔ Blåtann | 2 s: Blåtann-paring av/på |
| ◀◀ | forrige spor / favoritt; avbryter paring | 3 s: innstillinger av/på |
| ▶▶ | neste spor / favoritt | 1 s: spill/pause (ingen encoder-trykk lenger) |
| ◀◀ + ▶▶ | – | 3 s: omstart |

I innstillingene: ◀◀/▶▶ = flytt, RADIO = endre verdi, AIR·BT = lukk (lukkes også etter 20 s). LED-ringer: RADIO = radio,
AIR·BT = AirPlay/Blåtann/Spotify (pulserer under paring), ◀◀/▶▶ = noe spiller. Første trykk når velkomsthilsenen vises lukker den.

## Skjerm (Skjold OS, `--layout node-oled32`)
SSD1306 128×32 via luma.oled (I²C 1, 0x3C, rotate=2 fordi skjermen står opp-ned i lokket), 1-bit. Topplinje: kilde (+ «II»
på pause) og klokke. Tittel stor (ruller når den er lang), artist under. Volum («VOL 42» + stolpe) i 1,5 s når potmeteret vris.
Lysstyrke/dimming = OLED-kontrast. Den gamle ST7735-layouten finnes fortsatt (`--layout node`).

## Må bekreftes på maskinvare
1. `rotate=2` (skjermen opp-ned i lokket) – se testbildet (pil nede til venstre).
2. Potmeterets retning (med klokka = høyere) og at 0/100 nås i endestoppene.
3. At SSD1306-modulen har pull-ups og tåler 400 kHz (de fleste gjør det; ellers `dtparam=i2c_arm_baudrate=100000`).
4. Plassering av ADS1115-modulen under lokket (lengdene W17–W21 er anslått).
