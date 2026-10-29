# Handoff: Ugreen USB 2.0-switch i Pultforsterker v2

Tillegg til `README.md`. Beskriver USB-switchen (2 PC → 4 USB) som er bygget inn i kassen. Raspberry Pi-en styrer den, og den betjenes med en knapp foran. Åpne `Pultforsterker v2.html` og trykk «USB-switch: Montert» for å se oppførselen.

## Oppgave for Claude Code
1. **Pi-tjeneste** (Python 3, `gpiozero`, systemd): pulser Ugreen-knappen via optokobler, leser hvilken PC som er aktiv, og eksponerer tilstanden til skjerm-UI-et.
2. **Knappelogikk:** omfordeling av de to øverste inngangsknappene når switchen er montert (se under).
3. **Skjerm:** overlegg og PC-indikator på OLED (128×64) eller TFT (320×240).
4. **Kabinett** (valgfritt i CAD): nye mål, vindu i venstre sidevegg og bosser for ampkortet.

## Komponent
- **Ugreen USB 2.0 sharing switch:** 2 USB-B inn (PC 1, PC 2), 4 USB-A ut, én trykknapp, 5 V fra USB.
- **Mål:** 100 × 53 × 16 mm (oppgitt 3,94 × 2,09 × 0,63″). Kontroller dette mot den innkjøpte enheten.
- USB-A-portene sitter på den ene langsiden, USB-B på den motsatte, og knappen på toppen. Kontroller dette også før du låser hullene.

## Plassering i kassen
- **Kasse:** 215 × 150 × 48 mm (60 mm høy med TFT-skjerm). Veggene er 2,7 mm og bunnen 2,5 mm.
- **Ugreen** ligger flatt mot **venstre** sidevegg, med USB-A-siden flush i veggen:
  - Senter x = −(107,5 − 27,5) = −80, y = 0, z = bunn + 10,5.
- **Vindu i venstre vegg:** y ±35, z fra bunn + 6 til bunn + 15 (70 × 9 mm). Etiketten «USB» står over vinduet.
- **Bakpanel:** 2 × panelmontert USB-B («PC 1» ved x −8, «PC 2» ved x 8), z = bunn + 10, med hull 12,2 × 11. Kort USB-B-hann → USB-B-hunn-kabel fra hver port til Ugreen-switchen.
- **Optokoblerkort:** 18 × 14 mm, på toppen av Ugreen ved y +32.
- **Ampkort:** 150 × 100 × 1,6 mm, senter x 25, y 0, på fire 5 mm bosser (Ø7, hull Ø2,6 for M3) 4 mm inn fra hjørnene.
- **Fri høyde over ampkortet:** ca. 33 mm i 48 mm-kassen og ca. 45 mm i 60 mm-kassen. Sjekk den høyeste komponenten.

## Kobling
**Styring:** Pi GPIO → PC817 → Ugreen-knappen.
- Pi GPIO17 → 330 Ω → PC817 pinne 1 (anode). Pinne 2 (katode) → GND.
- PC817 pinne 4 (kollektor) og 3 (emitter) loddes over Ugreen-knappens to pads. Mål med multimeter hvilken pad som ligger mot 5 V/pull-up, og koble kollektoren dit.
- Pulsen er 150 ms høy. Vent minst 500 ms mellom pulser.

**Avlesning av aktiv PC (anbefalt):** Ugreen-LED «PC 1» → PC817 nr. 2 → Pi GPIO27 (input, intern pull-up).
- LED-en lyser = GPIO27 lav = PC 1. Ellers PC 2.
- Uten avlesning lagres antatt tilstand i en fil, og den kan bli feil hvis noen trykker på knappen på selve Ugreen-switchen.

Galvanisk skille via optokobler holder USB-jord og Pi-jord adskilt, slik at det ikke blir brum i lydkjeden.

**Merk:** Hovedfastvaren i `README.md` kjører på ESP32. Hvis frontknappene leses av ESP32 og ikke av Pi, må ESP32 sende «bytt PC» til Pi-en over UART eller MQTT, eller pulse optokobleren selv. Velg én løsning og dokumenter den.

## Knapper (når switchen er montert)
Frontens 2×2-knapper omfordeles:

| Posisjon   | Uten switch | Med switch |
|------------|-------------|------------|
| Oppe venstre | AIRPLAY (hold 2 s = BT av/på) | **PC 1/2**: kort trykk bytter PC |
| Oppe høyre   | BT | **AIRPLAY/BT**: kort trykk veksler AirPlay ↔ BT (kun hvis BT er tilkoblet), hold 2 s = BT av/på |
| Nede venstre | AUX | AUX |
| Nede høyre   | USB | USB |

- **Etiketter på frontplaten:** «PC 1/2» og «AIRPLAY/BT». Det betyr at det trengs en egen frontplate-variant, eller at etikettene trykkes etter monteringen.
- **LED-ring på PC 1/2:** svakt lys (ca. 30 % PWM) hele tiden mens enheten er på.
- **LED-ring på AIRPLAY/BT:** lyser når AirPlay eller BT er aktiv inngang, og pulserer under parring.
- Hold-logikken for BT er den samme som `holdDown/holdUp` i JS-filen. Den sitter nå bare på knappen oppe til høyre.
- I prototypen veksler kort trykk på AIRPLAY/BT til BT bare hvis BT er tilkoblet. Ellers velges AirPlay.

## Skjerm
- **Overlegg ved PC-bytte (2,2 s):** USB-ikon (64,17), «USB → PC N» (fet 10 px, y=39), «Tastatur, disk og USB-lyd fulgte med» (6 px dim, y=50). Se `drawO()`, `ov.type === 'usb_sw'`.
- **Hovedskjerm:** når USB er aktiv inngang, er underteksten «PC N · 48 kHz». På TFT vises i tillegg «PC N» høyrejustert i fanelinjen.
- Ugreen-LED-ene speiles i prototypen (`ugLed`).

## Pi-tjeneste (forslag)
```
pultforsterker-usbsw.service
  GPIO17 out (puls), GPIO27 in (LED-avlesning, debounce 50 ms)
  state: {pc: 1|2}          → /run/pultforsterker/usbsw.json
  kommandoer: toggle | set 1 | set 2   (Unix-socket eller MQTT topic pultforsterker/usbsw/set)
  ved oppstart: les GPIO27, skriv state
  set N: puls kun hvis pc != N, les GPIO27 etter 300 ms, prøv én gang til hvis den ikke byttet
```
- Etter et bytte publiseres en hendelse til skjerm-UI-et, som viser overlegget.
- Lyrion er upåvirket. USB-lyd fra PC-en går via den USB-A-porten som er koblet til forsterkerens USB-lydinngang, internt eller via porten bak.

## Tilstand (tillegg til README)
```
usbSw     bool     (maskinvarekonfig: switch montert)
usbPc     1 | 2
overlay   … | usbSw   (2,2 s)
```

## Filer
- `pultforsterker_v2.js`:
  - `SIDE`, `sideWin`: vindu i venstre vegg
  - `usbSide`: Ugreen-switchen, porter og LED-er
  - `usbToggle()`: PC-bytte
  - `holdDown/holdUp` med `hb`: hvilken knapp som eier BT-hold
  - `drawO()` og `drawTFT()`: skjermtegning
- `Pultforsterker v2.html`: panelet «USB-switch» med Montert, PC 1 og PC 2
