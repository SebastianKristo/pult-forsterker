# Oppgave for Claude Code: Kobling av skjerm, encoder og knapper i Skjold Node

Lag et komplett koblingsoppsett for Skjold Node. Det skal brukes tre steder:
1. **Bruksanvisningen**, med steg for steg i LEGO-stil, se `../bruksanvisning/MAL_FOR_CLAUDE.md`.
2. **Programvaren**, med en `config`-fil for pinner og en driver i `skjold-ui`.
3. **Device tree-oppsettet** i SD-bildet, i `../sdbilde/pi-gen/stage-skjold/`.

## Maskinvare
| Del | Type | Notat |
|---|---|---|
| Skjerm | 1,8″ ST7735S, 128 × 160, SPI, 8 pinner (VCC, GND, CS, RESET, A0/DC, SDA, SCK, LED) | Står liggende, 160 × 128. Bildet roteres 180° i programvaren, se `cad/generate_node.js` linje 3. |
| Encoder | EC11 med trykk, 20 mm halvflat aksel | A, B, C (felles) + SW + SW |
| Knapper | 4 × 12 mm metall-trykknapp, momentan (NO), eventuelt LED-ring (pinner `+` og `−`) | RADIO, AIR / BT, ◀◀, ▶▶ (fra venstre, sett fra brukeren) |
| Pi | Raspberry Pi 4 eller 3B/3B+ | Lyd går gjennom 3,5 mm/HDMI. Ingen I²S-DAC, så GPIO 18–21 er ledige. |

## Forslag til pinner (må kontrolleres)
| Funksjon | GPIO (BCM) | Fysisk pinne |
|---|---|---|
| TFT VCC | 3V3 | 1 |
| TFT GND | GND | 6 |
| TFT SCK | GPIO11 (SPI0 SCLK) | 23 |
| TFT SDA (MOSI) | GPIO10 (SPI0 MOSI) | 19 |
| TFT CS | GPIO8 (SPI0 CE0) | 24 |
| TFT A0/DC | GPIO25 | 22 |
| TFT RESET | GPIO24 | 18 |
| TFT LED (bakgrunnslys, PWM-dimming) | GPIO18 (PWM0), via NPN/MOSFET hvis modulen trekker mer enn 15 mA | 12 |
| Encoder A | GPIO17 | 11 |
| Encoder B | GPIO27 | 13 |
| Encoder C (felles) | GND | 14 |
| Encoder SW | GPIO22 (+ GND) | 15 |
| Knapp RADIO | GPIO5 (+ GND) | 29 |
| Knapp AIR / BT | GPIO6 (+ GND) | 31 |
| Knapp ◀◀ | GPIO13 (+ GND) | 33 |
| Knapp ▶▶ | GPIO26 (+ GND) | 37 |
| LED-ring RADIO / AIR / ◀◀ / ▶▶ (valgfritt) | GPIO12 / 16 / 20 / 21, via motstand eller transistor | 32 / 36 / 38 / 40 |

Alle innganger bruker intern pull-up og er aktive lave. Bruk felles GND-skinne, for eksempel pinne 9, 20, 25, 30, 34 og 39.

## Det Claude Code skal levere
1. **Sjekk pinnevalget** mot Pi 4 og Pi 3. Pinnene må ikke kollidere med UART-konsoll, I²C (GPIO2 og 3) eller Blåtann/Wi-Fi. Endre der det trengs, og begrunn endringen.
2. **LED-ringene:** finn ut om de er laget for 3–6 V eller 12 V. Pi-en kan bare gi 3,3 V og omtrent 16 mA per pinne. Skriv hvilken motstand som trengs, eller tegn en løsning med en enkel transistor (2N7002 eller BC547) per ring.
3. **Koblingsskjema som SVG** (`node/kabling_node.svg`): Pi-headeren med 40 pinner, skjermen, encoderen og de fire knappene. Fargekod ledningene: rød 3V3, sort GND, gul SPI, blå encoder, grønn knapper, oransje LED.
4. **Kabelliste** (`node/kabelliste.csv`): fra, til, farge, lengde i mm og pluggtype (Dupont hunn–hunn 10 cm, eller loddet). Lengdene finner du i `node/params.json` og `cad/generate_node.js`. Pi-en sitter i bunnen og komponentene sitter i lokket. La ledningene være så lange at lokket kan vippes opp uten å løsne noe.
5. **Driveroppsett:**
   - **Skjerm:** `dtoverlay=fbtft` eller `st7735r` i `config.txt`, eller en Python-driver med `luma.lcd` (st7735, rotate=2). Velg én løsning og begrunn valget.
   - **Encoder:** `dtoverlay=rotary-encoder,pin_a=17,pin_b=27,relative_axis=1` og `gpio-key` for SW.
   - **Knapper:** `dtoverlay=gpio-key` per knapp, med keycodes. Alternativet er `gpiozero` i `skjold-ui`.
   - Lag `config/node_pins.json` som felles kilde for pinner. Både UI-koden og bruksanvisningen skal lese fra den.
6. **Bruksanvisning:** egne steg for Node i `bruksanvisning/innhold.json`:
   - lodd knappene
   - lodd encoderen
   - koble skjermen
   - koble til headeren
   - test

   Bruk ett bilde per steg, med en tegning av handlingen, og samme oppsett som malen.
7. **Testskript** (`skjold-ui/tools/node_selftest.py`): tegner et testbilde på skjermen, viser hvilken knapp som trykkes og hvilken vei encoderen vris, og blinker hver LED-ring.

## Oppførsel (fra prototypen `Skjold Node OS.dc.html`)
- **Volumknappen:** vri endrer volumet, trykk demper lyden, og hold i 3 sekunder åpner innstillingene.
- **RADIO:** trykk går til neste av de seks favorittene, og hold spiller favoritten du har valgt.
- **AIR / BT:** trykk bytter mellom AirPlay og Blåtann, og hold i 2 sekunder starter paring.
- **◀◀ og ▶▶:** gå til forrige eller neste spor. I menyene går de opp og ned. Hold begge for å starte på nytt.
- **Velkomsthilsen:** se `../sdbilde/README.md`. Det første trykket lukker hilsenen og gjør ingenting annet.
