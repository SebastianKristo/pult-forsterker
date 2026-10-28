# KI Pultforsterker – totalinstruks

Alt fra tomt SD-kort til ferdig forsterker styrt fra Home Assistant og Homey. Følg kapitlene i rekkefølge; hvert kapittel ender med en sjekk som må være grønn før du går videre. Kommandoer merket **PC** kjøres på Mac/PC, resten på Pi-en over SSH.

Rekkefølgen er lagt opp slik at du kan **teste hele programvaren på Pi 4 før hovedkortet kommer** (kapittel 1–8, lyd ut på Pi-ens 3,5 mm), og så bare bytte til hovedkortet (kapittel 9) uten å installere på nytt.

---

## 0. Du trenger

| | |
|---|---|
| Raspberry Pi 4 B (4 GB) + microSD 16 GB eller mer (A1/A2-klasse) | har |
| USB-C strømforsyning 5 V 3 A til testing (senere 5 V fra hovedkortet) | |
| Nettverkskabel til ruteren (Wi-Fi går også) | |
| PC/Mac med [Raspberry Pi Imager](https://www.raspberrypi.com/software/) | |
| 3,5 mm-kabel til aktiv høyttaler (kun for test før hovedkortet) | |
| Resten av delene: `pcb/DELELISTE_MED_PCB.md` | |

---

## 1. SD-kort (PC)

1. Åpne **Raspberry Pi Imager** → *Choose device*: Raspberry Pi 4 → *Choose OS*: **Raspberry Pi OS Lite (64-bit)** (under «Raspberry Pi OS (other)») → *Choose storage*: SD-kortet.
2. Trykk **Next → Edit settings** og fyll inn:
   - **General**: Hostname `pultamp` · Username `sebastian` + passord · Wireless LAN (bare hvis du ikke bruker kabel) · Locale `Europe/Oslo`, keyboard `no`.
   - **Services**: ✅ *Enable SSH* → *Use password authentication* (eller lim inn din offentlige nøkkel).
   - **Options**: ✅ *Eject media when finished*.
3. **Save → Yes → Yes**. Vent til «Write successful». Sett kortet i Pi-en.

> Tips: ligger `~/.ssh/id_ed25519.pub` på Mac-en, velg *public-key authentication* – da slipper du passord på alle `ssh`/`scp`.

---

## 2. Første oppstart

Koble nettverkskabel og strøm. Første oppstart tar ~1 min (den utvider filsystemet og starter på nytt én gang).

```bash
# PC
ssh sebastian@pultamp.local
# Finner den ikke navnet: se Pi-ens IP i UniFi (klient «pultamp») og bruk ssh sebastian@<ip>
```

Svar `yes` på fingeravtrykket. Når du er inne:

```bash
sudo apt-get update && sudo apt-get -y full-upgrade && sudo reboot
```

Logg inn igjen etter omstart og sjekk:

```bash
cat /proc/device-tree/model      # Raspberry Pi 4 Model B Rev 1.x
hostname -I                       # IP-adressen – noter den
```

**Sjekk:** SSH virker og modellen er Pi 4. ✅

Valgfritt, men lurt: gi Pi-en fast IP i UniFi (Clients → pultamp → Settings → Fixed IP) så HA/Homey alltid finner den.

---

## 3. Hent prosjektet

```bash
sudo apt-get -y install git
git clone https://github.com/SebastianKristo/pult-forsterker.git
cd pult-forsterker/pi
```

Senere oppdateringer: `cd ~/pult-forsterker && git pull && bash pi/install.sh` (skriptet er trygt å kjøre flere ganger).

---

## 4. Installer programvaren

Skriptet gjør alt: config.txt (I2S/I2C/SPI/USB-gadget), ALSA-loopback, CamillaDSP, bygger NQPTP + Shairport Sync (AirPlay 2), bluealsa (Bluetooth), USB-lydkort-gadget, OLED-tjeneste og KI-daemonen. Det tar **20–30 min** (mesteparten er kompilering av Shairport Sync).

**A – test uten hovedkort (nå):** lyd ut på Pi-ens 3,5 mm-kontakt.

```bash
KI_AMP_OUT=headphones bash install.sh
```

**B – ferdig forsterker (når hovedkortet er på plass):**

```bash
bash install.sh
sudo sed -i 's/^#\?KI_AMP_BOARD=.*/KI_AMP_BOARD=main/' /etc/ki-amp.env
```

Etter skriptet:

```bash
sudo reboot
```

**Sjekk etter omstart:**

```bash
systemctl is-active camilladsp nqptp shairport-sync bluealsa bluealsa-aplay ki-amp oled-display ki-usb-audio
#  → alle "active" (oled-display kan være "activating"/feile til OLED-en er koblet – det er greit)
aplay -l             # A: "Headphones"   B: "sndrpihifiberry"  – pluss "Loopback"
curl -s http://localhost:8765/api/status ; echo
#  → {"power": true, "input": "airplay", "volume": 30, ...}
```

Testmodus A: sett jack-volumet én gang: `amixer -c Headphones sset Headphone 100%`. ✅

---

## 5. Test lyden

Koble 3,5 mm (A) eller høyttalerne (B).

```bash
speaker-test -c 2 -t wav -l 1          # «Front left / Front right» gjennom hele kjeden (dmix → loopback → CamillaDSP)
```

**AirPlay 2:** på iPhone/Mac – Kontrollsenter → lyd → velg **Pultforsterker**. Spill noe.

**Bluetooth:** sett Pi-en i parringsmodus (2 min synlig):

```bash
curl -X POST localhost:8765/api/bt -d '{"pairing":true}'
```

Telefon → Bluetooth → **Pultforsterker** → koble til → spill. Bytt kilde på forsterkeren: `curl -X POST localhost:8765/api/input -d '{"input":"bt"}'`.

**USB-lyd fra PC:** koble PC-en til Pi-ens **USB-C**-port (på Pi 4 er det OTG-porten; i testmodus må da Pi-en få strøm derfra – en USB 3-port på PC-en holder – eller via 5 V på header pinne 2/6). PC-en ser lydkortet **«Pultforsterker»**. `curl -X POST localhost:8765/api/input -d '{"input":"usb"}'`.

**Volum, mute, loudness:**

```bash
curl -X POST localhost:8765/api/volume   -d '{"volume":40}'
curl -X POST localhost:8765/api/volume   -d '{"delta":-5}'
curl -X POST localhost:8765/api/mute     -d '{"mute":true}'
curl -X POST localhost:8765/api/loudness -d '{"on":true,"level":6}'
curl -X POST localhost:8765/api/power    -d '{"on":false}'      # standby
curl -X POST localhost:8765/api/toggle
curl -X POST localhost:8765/api/transport -d '{"action":"next"}'   # play | pause | playpause | next | previous | stop (AirPlay/Bluetooth)
```

Logg mens du tester: `journalctl -u ki-amp -f` (Ctrl-C for å avslutte).

**Sjekk:** lyd fra AirPlay, Bluetooth og USB, volum virker fra `curl`. ✅

> AUX-*inngangen* kan ikke testes før hovedkortet er på plass (reléet og den analoge veien sitter der).

---

## 6. Knapper, encoder og OLED (valgfritt før hovedkortet)

Alt kan kobles rett på Pi-ens header med Dupont-ledninger og testes nå. BCM-nummer; pinnenummer i parentes.

| Del | Hovedkort-kart (`KI_AMP_BOARD=main`) | Modul-kart (standard) |
|---|---|---|
| AIRPLAY-knapp | GPIO 5 (29) | GPIO 5 |
| BT-knapp | GPIO 6 (31) | GPIO 6 |
| AUX-knapp | GPIO 14 (8) | GPIO 12 |
| USB-knapp | GPIO 15 (10) | GPIO 13 |
| POWER-knapp | GPIO 16 (36) | GPIO 16 |
| Encoder CLK / DT / SW | GPIO 23 / 24 / 25 (16 / 18 / 22) | samme |
| OLED SDA / SCL / RES | GPIO 2 / 3 / 4 (3 / 5 / 7), VCC 3,3 V (1), GND (6) | samme |
| LED-ringer AIR / BT / AUX / USB / POWER | GPIO 7 / 9 / 17 / 20 / 12 | 7 / 8 / 9 / 10 / 11 |

Knappene kobles mellom GPIO og GND (intern pull-up). LED-ringene trenger driver (MOSFET på hovedkortet) – ikke koble LED rett på GPIO.

```bash
sudo sed -i 's/^#\?KI_AMP_BOARD=.*/KI_AMP_BOARD=main/' /etc/ki-amp.env   # bruk hovedkort-kartet
sudo systemctl restart ki-amp oled-display
i2cdetect -y 1          # OLED svarer på 3c
journalctl -u ki-amp -f # trykk på knappene – du skal se "input airplay", "volume 31" osv.
```

---

## 7. Home Assistant

1. Kopier integrasjonen (fra PC-en, eller via Samba/SSH-tillegget i HA):
   ```bash
   # PC – HA over SSH-tillegget (bytt host)
   scp -r homeassistant/custom_components/ki_pultforsterker root@homeassistant.local:/config/custom_components/
   ```
2. Legg pakken i `packages/` (du bruker allerede packages-oppsett):
   ```bash
   scp pi/ki_pultforsterker_package.yaml root@homeassistant.local:/config/packages/ki_pultforsterker.yaml
   ```
3. Start HA på nytt. **Innstillinger → Enheter og tjenester → Oppdaget → KI Pultforsterker → Konfigurer** (mDNS `_kipultamp._tcp`). Dukker den ikke opp: *+ Legg til integrasjon → KI Pultforsterker* og skriv IP + port 8765.
4. Entiteter: `media_player.ki_pultforsterker` (kilde, volum, mute, på/av), `switch.ki_pultforsterker_strom`, `switch.ki_pultforsterker_loudness`, `number.ki_pultforsterker_loudness_styrke`, `sensor.ki_pultforsterker_kilde/tittel/artist`, `binary_sensor.ki_pultforsterker_spiller`, `button.ki_pultforsterker_start_bluetooth_parring`. Pakken gir `input_boolean.ki_pultforsterker_auto_av`, `input_number.ki_pultforsterker_av_etter_min`, automasjonene «KI Pultforsterker – på ved AirPlay» / «– av etter stillhet» og TTS-skriptet.
5. Kort til dashbordet – eksempel med vanlig `media-control` (legg stil som per-kort override, ikke i button_card_templates):
   ```yaml
   type: media-control
   entity: media_player.ki_pultforsterker
   ```

**Sjekk:** media_player viser kilde og volum, og volumslideren i HA flytter tallet i `curl …/api/status`. ✅

---

## 8. Homey

```bash
# PC
npm install -g homey
homey login
cd homey/no.kristo.ki-pultforsterker
npm install
homey app install            # eller: homey app run  (live-logg i terminalen)
```

Homey-appen → *Enheter → + → KI Pultforsterker* → forsterkeren finnes via mDNS (ellers skriv IP i enhetsinnstillingene). Flytkort: *på/av*, *velg kilde*, *sett volum*, *loudness* (`ki_set_loudness`), *start Bluetooth-parring*, og triggere på kilde/avspilling.

**Sjekk:** «Sett volum 20» i en flyt endrer volumet. ✅

---

## 9. Bytte til hovedkortet

Når PCBWay-kortet er montert i kassen (se `docs/byggeveiledning.md` for mekanikken og `pcb/DELELISTE_MED_PCB.md` for pluggene):

1. Pi 4 på gulvet, hovedkortet 25 mm over på stolpene, 40-pin flatkabel (10 cm) J5 → Pi (rød stripe mot pinne 1 begge steder), 5 V fra **J6** til Pi header pinne 2 (5 V) og 6 (GND) med 18 AWG. **Ikke** USB-C-strøm i Pi-en samtidig.
2. JST: J7 knapper, J10 LED-ringer, J8 encoder, J9 OLED, J4 AUX. Skruterminaler: J1 24 V (via KCD1 fra DC-099), J2/J3 høyttalere. Ethernet- og USB-C-forlengere fra Pi-en til bakveggen.
3. På Pi-en:
   ```bash
   cd ~/pult-forsterker && git pull
   bash pi/install.sh                      # uten KI_AMP_OUT → config.txt/ALSA tilbake til I2S-DAC
   sudo sed -i 's/^#\?KI_AMP_BOARD=.*/KI_AMP_BOARD=main/' /etc/ki-amp.env
   sudo reboot
   ```
4. Sjekk:
   ```bash
   aplay -l                   # sndrpihifiberry
   i2cdetect -y 1             # 3c (OLED)
   journalctl -u ki-amp -n 30 # ingen "Kjører uten GPIO"-feil
   speaker-test -c 2 -t wav -l 1   # start lavt: curl -X POST localhost:8765/api/volume -d '{"volume":15}'
   curl -X POST localhost:8765/api/input -d '{"input":"aux"}'   # reléet klikker, AUX-lyd gjennom
   ```

Første gang: mål 5 V på J6 og at hovedkortet trekker < 0,2 A i standby på 24 V før du kobler høyttalerne.

---

## 10. Daglig bruk og vedlikehold

| | |
|---|---|
| Innstillinger | `/etc/ki-amp.env` (navn, port, GPIO-kart `KI_AMP_BOARD`, `KI_AMP_MAX_TAP`, DSP-enheter). `sudo systemctl restart ki-amp` etterpå. |
| Tilstand | `/var/lib/ki-amp/state.json` (volum, kilde, loudness) – overlever omstart |
| Loudness-kurve | `/etc/camilladsp/config.yml` (`reference_level`, `high_boost`, `low_boost`), `sudo systemctl restart camilladsp` |
| AirPlay-navn | `/etc/shairport-sync.conf` → `name` |
| Oppdatere | `cd ~/pult-forsterker && git pull && bash pi/install.sh` |
| Logger | `journalctl -u ki-amp -f`, `-u shairport-sync`, `-u camilladsp`, `-u bluealsa-aplay`, `-u oled-display` |
| Status | `curl -s pultamp.local:8765/api/status` |

---

## 11. Feilsøking

| Symptom | Sjekk |
|---|---|
| `ssh pultamp.local` finner ikke host | Bruk IP fra UniFi; mDNS kan være blokkert mellom VLAN. |
| Ingen lyd, alt «active» | `aplay -l` – finnes riktig kort? `speaker-test -D hw:Headphones` (A) / `-D hw:sndrpihifiberry` (B) rett på kortet; så `-D default` gjennom kjeden. `journalctl -u camilladsp -n 50` – «Capture device … busy» betyr at snd-aloop mangler: `lsmod \| grep aloop`. |
| AirPlay vises ikke | `systemctl status nqptp shairport-sync`; Pi og telefon på samme nett/VLAN (mDNS). |
| Bluetooth kobler ikke | `bluetoothctl show` – *Discoverable: yes* mens parring er aktiv; `systemctl status bluealsa bluealsa-aplay`. Glem enheten på telefonen og prøv igjen. |
| USB-lydkort vises ikke på PC | `ls /sys/kernel/config/usb_gadget/` skal vise `pultamp`; `journalctl -u ki-usb-audio`. På Pi 4 må kabelen stå i **USB-C**, ikke USB-A. Full speed er med vilje (USB-isolatoren). |
| OLED svart | `i2cdetect -y 1` → `3c`; sjekk at `dtparam=i2c_arm=on` står i `/boot/firmware/config.txt`; `journalctl -u oled-display`. |
| Knapper virker ikke | `journalctl -u ki-amp -f` og trykk; feil GPIO-kart → `KI_AMP_BOARD`. Testmodus: seriell konsoll må være av for GPIO 14/15 (`sudo raspi-config nonint do_serial_hw 1`). |
| HA finner ikke forsterkeren | Legg til manuelt med IP:8765. `curl pultamp.local:8765/api/status` fra HA-maskinen. |
| Pi 4 starter på nytt under test med USB-C fra PC | For lite strøm fra PC-porten – bruk USB 3-port eller egen strømforsyning på header pinne 2/6 (aldri begge USB-C og header samtidig). |

---

## 12. Hvis du vil endre koden

| Hva | Hvor | Deploy |
|---|---|---|
| Knapper, volum, API, loudness-logikk | `pi/ki_amp_daemon.py` | `sudo install -m755 ki_amp_daemon.py /usr/local/bin/ && sudo systemctl restart ki-amp` |
| Skjermbildene på OLED | `pi/oled_display.py` | `sudo install -m755 oled_display.py /usr/local/bin/ && sudo systemctl restart oled-display` |
| HA-integrasjon | `homeassistant/custom_components/ki_pultforsterker/` | kopier, restart HA |
| Homey-app | `homey/no.kristo.ki-pultforsterker/` | `homey app install` |
| Kabinett | `kabinett/tools/build_stl.py` (`VARIANT=pcb python3 build_stl.py`) | print STL fra `kabinett/stl/` |
| Hovedkort | `pcb/build_board.py` → `pcb/export.py` | Gerber/BOM/CPL i `pcb/produksjon/` |

Daemonen kjører også på en vanlig PC uten GPIO (`python3 ki_amp_daemon.py` → «Kjører uten GPIO») for å teste API og integrasjoner.
