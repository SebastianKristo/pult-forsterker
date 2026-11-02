# Skjold Node – kabling og drivere (rev C, OLED-utgave)

Felles kilde for alle pinner: **`config/node_pins.json`** (schema 2). SVG og kabelliste er generert fra den.
Kassen: `skjold/design/node/Skjold Node kasse OLED.html` / `… OLED taktil.html` (lokk for 0,91″ OLED; bunn som før).

| Fil | Hva |
|---|---|
| `config/node_pins.json` | Pinner, I²C-adresser, ADS1115/potmeter (`potmeter.metode`, `potmeter.rc`), holdetider, LED-drift. Leses av ki_amp_daemon.py (`KI_AMP_BOARD=node`), Skjold OS, selvtesten og bruksanvisningen. |
| `config/config.txt.node` | Tillegg til `/boot/firmware/config.txt`: I²C på (400 kHz), **SPI av**, 3,5 mm-lyd, startnivå på pinnene. |
| `kabling_node.svg` | Koblingsskjema: header, OLED, ADS1115, potmeter (+ RC-variant: 1 kΩ + kondensator), 4 knapper, 4 LED-ringer. Fargekodet. |
| `kabelliste.csv` | Ledning for ledning: fra, til, nett, farge, lengde, pluggtype. |
| `driver/installer_node.sh` | config-blokken, I²C (`raspi-config nonint do_i2c 0`), i2c-tools, gpiozero/lgpio, luma.oled + smbus2, `SKJOLD_OS_ARGS=--layout node-oled32`, Skjold OS. |
| `tools/lag_kabling.py` | Lager SVG + CSV fra json. Kjør etter hver pinneendring. |
| `tools/sjekk_konsistens.py` | Sjekker json mot csv, svg og config.txt (BCM→pinne, GND/3V3, reserverte GPIO, SPI av). |
| `tools/node_selftest.py` | Testbilde på OLED-en, live potmeter via ADS1115 eller RC (GPIO17), knapper, blinker LED-ringene. `--dry-run` uten Pi. |

```sh
python3 tools/lag_kabling.py && python3 tools/sjekk_konsistens.py
python3 tools/node_selftest.py --dry-run --ut /tmp/st     # PNG-er av skjermbildene (×4)
sudo ./driver/installer_node.sh && sudo reboot              # på Pi-en
i2cdetect -y 1                                              # skal vise 3c (OLED) og 48 (ADS1115; mangler i RC-varianten)
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
| *RC-variant (i stedet for ADS1115):* pot pinne 3 | 3V3 | 17 | rød |
| *RC-variant:* node RC (pot pinne 2 → 1 kΩ → node; node → 220 Ω → GPIO17) | GPIO17 | 11 | blå |
| *RC-variant:* kondensator − (+ på node RC) | GND | 39 | sort |
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
- 3,5 mm-lyden bruker PWM0/1 internt, så LED-ringene dimmes med lgpio-PWM (tx_pwm, 1 kHz) via gpiozero. Ikke legg til `dtoverlay=pwm`.
- Samme pinner på Pi 4, 3B og 3B+. Blåtann/Wi-Fi bruker ingen header-pinner. UART (14/15) og HAT-EEPROM (0/1) er ledige.

## Potmeter (volum)
10 kΩ lineært (B10K): pinne 1 → GND, pinne 2 (glider) → A0, pinne 3 → VDD (3,3 V). ADS1115 i kontinuerlig modus,
±4,096 V, 128 SPS, lest ~20 Hz av ki-amp. 0–3,3 V → volum 0–100 med glatting (0,35), dødsone 1,5 % i endene og hysterese ±2.
Volumet settes **bare når knotten flyttes**: volum fra appen/AirPlay står til knotten vris igjen, og da tar knotten over
fra sin egen posisjon («soft takeover»). Første måling etter oppstart rører ikke volumet. Mangler ADS1115, virker alt annet
(nytt forsøk hvert 10. s). Feil retning: sett `potmeter.inverter=true` eller bytt pinne 1 og 3.

To måter å koble potmeteret på – `potmeter.metode` i `node_pins.json`: `"auto"` (standard: ADS1115 hvis den svarer på 0x48
ved oppstart, ellers RC), `"ads1115"` eller `"rc"`. Daemonen logger hvilken som er aktiv (`journalctl -u ki-amp | grep Potmeter`).

| | ADS1115 (anbefalt, **mest nøyaktig**) | RC-variant (bare én motstand og én kondensator) |
|---|---|---|
| Kobling | som over | Pi pinne 17 (3V3) → pot pinne 3 · pot pinne 2 (glider) → **1 kΩ** → node RC · node RC → Pi pinne 11 (**GPIO17**) · node RC → **kondensator** → Pi pinne 39 (GND) · pot pinne 1 kobles ikke |
| Kondensator | – | 1 µF anbefalt (100 nF–10 µF virker, sett `potmeter.rc.kondensator_f`). Elektrolytt (f.eks. 10 µF): **+ på node RC, − på GND** |
| Måling | 16-bit spenning, ~20 Hz | GPIO17 lav (tømmer C), så inngang uten pull (`gpio=17=ip,pn`) og tid til den leser høy (~1,4 V). Tiden ∝ 1 kΩ + motstanden glider–pinne 3. Median av 5, ~10 Hz, lgpio (ellers RPi.GPIO/gpiozero), egen tråd, ~4 % CPU |
| Kalibrering | ingen | Selvkalibrerende: vri knotten helt rundt én gang. Endepunktene lagres i `/var/lib/ki-amp/node_pot_rc.json` (slett filen for å kalibrere på nytt) |

Glatting, dødsone, hysterese og «bare når knotten flyttes» er felles for begge.

## LED-ringer
Bruk 3–6 V-varianten (innebygd motstand for ca. 5 V). 12 V-varianten lyser ikke på 3,3 V. GPIO → 330 Ω → LED+, LED− → GND:
under 4 mA per ring (rød/grønn/gul). Pi-grense 16 mA per pinne, 50 mA totalt.

**Tips – blå ringer:** blå LED-er har Vf ≈ 2,8–3,0 V. Med 3,3 V og 330 Ω blir strømmen bare (3,3 − 3,0) / 330 ≈ **0,9 mA** –
svakt, ujevnt mellom ringene og flimrete nær terskelen. Bytt til **68–100 Ω**:

| Motstand | Vf 3,0 V | Vf 2,8 V |
|---|---|---|
| 100 Ω | 3,0 mA | 5,0 mA |
| 82 Ω | 3,7 mA | 6,1 mA |
| 68 Ω | 4,4 mA | 7,4 mA |

Hold deg **≤ 8 mA per pinne** (fire ringer ≤ 32 mA, godt under Pi-ens 50 mA). Har ringen egen innebygd motstand, regn den med.

Lysstyrken styres med **LED-lysstyrke 0–100 %** (`ledLevel`) i appen (Skjerm og lys) eller innstillingsmenyen på Node.
Den går gjennom gamma 2,2 (opplevd lysstyrke, så 50 % ser ut som halvparten) og PWM på 1 kHz via lgpio (`tx_pwm`,
gpiozero `LGPIOFactory`) – ingen synlig flimring. Maskinvare-PWM er opptatt av 3,5 mm-lyden. Den gamle innstillingen
`led` (Høy/Middels/Lav/Av) virker fortsatt og blir 100/60/30/0 %.

**LED-modus** (`ledMode`): *Ved trykk* (standard) – ringene er mørke, knappen du trykker lyser fullt og toner ut over
1,2 s, og ringen til ny kilde gløder kort ved kildebytte. *Alltid* – aktiv kilde lyser (som før). *Av*. I «Ved trykk» og
«Alltid» vises fortsatt: AIR·BT pulserer under paring, og ringen til knappen du holder blir sterkere med hold-fremdriften.
Ved omstart/slå av toner ringene ut én etter én.

## Oppstart og avslutning (`early/`)
| Fil | Hva |
|---|---|
| `early/skjold_early.py` | Bare standardbibliotek (rå SSD1306 via /dev/i2c-1, innebygd 5×7-font, lgpio for LED-ene). `--final` = sluttbilde, `--sim DIR` = PNG-rammer |
| `early/skjold-early.service` | Starter like etter kjernen (`DefaultDependencies=no`, `WantedBy=sysinit.target`): «SKJOLD · Strøm på» → «Starter… ca. N s» + fremdrift, LED-jag |
| `early/skjold-shutdown.service` | `ExecStop` helt til slutt ved avslåing: «Slått av – trygt å trekke ut strømmen» (ved omstart: «Starter på nytt · tilbake om ca. N s»), LED-ene av |
| `early/install_early.sh` | Installerer og slår på begge (kalles av `driver/installer_node.sh` og `pi/install.sh`) |

Overlevering: Skjold OS lager `/run/skjold/os-display` når den tar skjermen (skjold-early slutter å tegne) og
`/run/skjold/os-ready` når daemonen svarer. Daemonen sender SIGUSR1 til skjold-early før den tar LED-pinnene og fortsetter
jaget selv til `os-ready`. Oppstartstiden (sekunder fra kjernen til `os-ready`) lagres som glidende snitt i
`/var/lib/skjold/boot_time` og brukes til «ca. N s» både ved oppstart og omstart. Standard før første måling: 45 s.
Ved omstart/slå av viser Skjold OS «Starter på nytt · tilbake om ca. N s» / «Slår av · trygt å trekke ut om 5 s», og
bildet blir stående til skjold-shutdown tegner sluttbildet. OLED-en holder bildet så lenge Pi-en gir 3,3 V etter halt.

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
AIR·BT = AirPlay/Blåtann/Spotify (pulserer under paring), ◀◀/▶▶ = noe spiller (gjelder LED-modus «Alltid»; se LED-ringer). Første trykk når velkomsthilsenen vises lukker den.

## Skjerm (Skjold OS, `--layout node-oled32`)
SSD1306 128×32 via luma.oled (I²C 1, 0x3C, rotate=2 fordi skjermen står opp-ned i lokket), 1-bit. Topplinje: kilde (+ «II»
på pause) og klokke. Tittel stor (ruller når den er lang), artist under. Volum («VOL 42» + stolpe) i 1,5 s når potmeteret vris.
Lysstyrke/dimming = OLED-kontrast. Den gamle ST7735-layouten finnes fortsatt (`--layout node`).

## Må bekreftes på maskinvare
1. `rotate=2` (skjermen opp-ned i lokket) – se testbildet (pil nede til venstre).
2. Potmeterets retning (med klokka = høyere) og at 0/100 nås i endestoppene.
3. At SSD1306-modulen har pull-ups og tåler 400 kHz (de fleste gjør det; ellers `dtparam=i2c_arm_baudrate=100000`).
4. Plassering av ADS1115-modulen under lokket (lengdene på lokk–lokk-ledningene W20–W25 er anslått).
5. RC-varianten: at GPIO17 leser høy ved ~1,3–1,6 V og at 0/100 nås etter én runde (kalibrering).
