# Skjold Røst – fastvare

Røst kjører **squeezelite-esp32** for ESP32-S3 ([sle118/squeezelite-esp32](https://github.com/sle118/squeezelite-esp32)) med Skjold-oppsettet ferdig lagt inn. Høyttaleren blir en vanlig Squeezebox-spiller i Lyrion, så den spiller synkront med S1, Node og Touch.

`skjold-rost-firmware.bin` er én fil som skrives til adresse `0x0`. Den lages av [`lag_firmware.py`](lag_firmware.py) og legges ved hver Skjold-release:

- Det offisielle ESP32-S3-bygget fra squeezelite-esp32, release `S3-i2s.16.1779.master-v4.3`. Versjonen er låst og sjekkes med sha256.
- En NVS-partisjon («settings» på `0x3F0000`, navnerom `config`) med Skjold-oppsettet: lyd, forsterker, skjerm, dreieknapp, knapper og navn. Du trenger ikke taste inn noe i NVS-editoren.

## Installer

**I nettleseren (enklest):** åpne <https://skjold.smarthjemexperten.no/flasher/rost/> i Chrome eller Edge, koble kortet til med USB-C og trykk **Installer på Skjold Røst**.

**Med kommandolinjen:**

```bash
pip install esptool
```

```bash
esptool.py --chip esp32s3 write_flash --erase-all 0x0 skjold-rost-firmware.bin
```

Finner ikke PC-en kortet, holder du **BOOT** inne, trykker **RST** og slipper **BOOT**.

## Første oppstart

1. Røst lager Wi-Fi-nettet **Skjold-Rost** med passord `squeezelite`. Koble til med mobilen. Oppsettsiden åpner seg, ellers gå til `192.168.4.1`. Velg ditt Wi-Fi.
2. Røst dukker opp i Lyrion som **Skjold-Rost** og i Skjold under **Grupper → Skjold Røst**.
3. Velg radiofavorittene for knappene 1–4 under **Grupper → Skjold Røst → Knapper**. Skjold legger dem som Lyrion-favoritter (presets) 1–4 på spilleren.
4. Har du flere Røst, gir du hver sitt navn på Røst-ens egen nettside (fanen «Squeezelite», `-n Skjold-Rost-bad`). Navnet må begynne med «Skjold-Rost» eller «Skjold Røst», så Skjold finner den.
5. For skjermen: installer pluginen **SqueezeESP32** i Lyrion (Innstillinger → Plugins). Under spillerens innstillinger → «Skjerm» velger du hva som vises. Velg **Klokke** som skjermsparer når spilleren er av.

## Betjening

| Handling | Hva skjer | Hvordan |
|---|---|---|
| Drei knappen | Volum | `rotary_config … ,volume` |
| Trykk på knappen | Spill / pause | samme |
| Langt trykk på knappen | Bytter dreieknappen til forrige/neste låt. Langt trykk igjen bytter tilbake. | `longpress` |
| ⏻ | Av / på i Lyrion. Forsterkeren slås av når det er stille. | `ACTRLS_POWER`, `set_GPIO 7=amp` + `-C 30` |
| 1–4 | Spiller favoritt 1–4 | `BCTRLS_PS1–4` → Lyrion «preset_N» |
| Skjermen | Låt, artist og kanal, volum og klokke | Lyrion tegner skjermbildet (SqueezeESP32-pluginen) |

Det finnes ikke noe «hold inne for å lagre» på favorittknappene. squeezelite-esp32 har ingen handling for å lagre presets uten rå-modus (`lms_ctrls_raw`), og rå-modus slår av resten av knappeoppsettet. Favorittene velges derfor i Skjold (punkt 3 over).

## Hva oppsettet består av

[`squeezelite-esp32.txt`](squeezelite-esp32.txt) viser alle nøklene. Nøkkelnavnene og formatet er sjekket mot kildekoden til squeezelite-esp32 (`config_alloc_get(NVS_TYPE_STR, …)` og `PARSE_PARAM`):

- **Tall må være desimale.** squeezelite-esp32 leser dem med `atoi()`, så `address=0x3C` blir 0. Skjermadressen er derfor utelatt; standard er 0x3C.
- **SSD1309 bruker SSD1306-driveren.** Den har samme registre for 128×64.
- **Pinner** (fra `kabinett/rost/LES_MEG.md`):
  - I²S BCK/WS/DO: 4, 5, 6
  - Forsterker (SDZ): 7
  - Skjerm SDA/SCL: 11, 12
  - Knapper: 8, 9, 18, 39, 47
  - Dreieknapp A/B/trykk: 15, 16, 17

  `pi/tests/test_rost_firmware.py` sjekker at de stemmer med koblingstabellen, og at ingen oppstarts-, USB-, flash- eller PSRAM-pinner er brukt.

## Bygg selv

```bash
pip install esptool==4.8.1 esp-idf-nvs-partition-gen==0.3.0
```

```bash
python3 firmware/rost/lag_firmware.py --ut ut
```

Skriptet laster ned upstream-bygget, sjekker sha256, lager NVS-partisjonen og slår alt sammen med `esptool merge_bin`. Det gjør det samme i release-workflowen (jobben `rostfw`).

## Verifisert og ikke verifisert

**Verifisert uten maskinvare:**
- Bygget lages.
- Bootloader, partisjonstabell, recovery og app ligger byte for byte på adressene fra `flash_project_args`.
- Partisjonstabellen har `settings` på `0x3F0000`.
- NVS-partisjonen inneholder oppsettet.
- Nøklene følger kildekoden.

**Bare på ekte maskinvare:**
- Lyd, knapper og dreieknapp.
- At SSD1309-modulen svarer på 0x3C. Står bildet opp ned, legg til `,HFlip,VFlip` i `display_config`. Svarer den ikke, trenger 7-pinners moduler `,reset=13` og RES koblet til GPIO13.
- At «preset_N» spiller favorittene, og at skjermbildet fra Lyrion ser bra ut i 128×64.

## Mikrofon (valgfri)

INMP441 (SCK 41, WS 42, SD 40) er koblet opp for senere bruk. squeezelite-esp32 bruker den ikke.

## Dusj-modus (langt trykk på ⏻)

Hold ⏻ inne i 1,5 sekunder: Røst spiller dusj-favoritten og slår seg av etter valgt tid (standard 15 min), med myk
nedtoning det siste halve minuttet. Fastvaren sender `BCTRLS_PS5` ved langt trykk (squeezelite-esp32: `"long_press": 1500`,
`"longpress": {"pressed": "BCTRLS_PS5"}`), og Skjold legger dusj-favoritten på Lyrion-preset 5 og står for tidtakingen
(`pi/skjold_rost.py`, `Dusj`). Velg favoritt og tid i web-appen: Grupper → Skjold Røst → Dusj-modus.
Kort trykk på ⏻ er av/på som før. Har du flashet en eldre fastvare, må du flashe på nytt (eller legge inn den nye
`knapper`-verdien fra `squeezelite-esp32.txt` i NVS-editoren) for å få langt trykk.
