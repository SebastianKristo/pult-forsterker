# Pultforsterker v2

Forsterker med OLED-skjerm, volumknapp med trykk for mute, fire inngangsknapper (2×2), egen POWER-knapp foran og hovedbryter bak. Basert på det opprinnelige lokket (`uploads/pultforsterker_lid.stl`): samme ytre mål (200 × 120 mm), kant, skruehull og kabelutsparing.

Modell: `Pultforsterker v2.html` (STL-nedlasting for lokk, kasse og vindu i panelet oppe til venstre).

## Varianter
- **Frittstående:** lokk uten ører, gummiføtter, antenne rett opp.
- **Pultfeste:** lokk med de opprinnelige ørene/sporene, antenne rett bakover.

## Skjerm
- 2,42" OLED, 128×64, SSD1309 (Snvi, AliExpress)
- Farge: **hvit**
- Grensesnitt: **I2C** (velg I2C-varianten, ellers må motstander flyttes på baksiden)
- Bibliotek: U8g2
- RES-pinnen må kobles til en GPIO eller via en motstand til 3,3 V
- Mål: kort 70 × 40 mm, glass 60,5 × 37 mm, aktivt område 55 × 27,5 mm
- Mål modulen når den kommer, så vinduet og festene kan justeres

## Innganger og avspilling
- **AirPlay**, **Bluetooth**, **AUX** og **USB**, hver med egen metallknapp (2×2). LED-ringen lyser på aktiv inngang.
- **Bluetooth av/på:** hold AIRPLAY-knappen i 2 s. Skjermen viser en fremdriftslinje mens du holder, deretter «Parring …» (synlig som «Pultforsterker»). BT-knappens LED blinker under parring. Når en enhet kobler til vises «Tilkoblet» og inngangen bytter til BT. Hold igjen for å slå av («Bluetooth av»). Når Bluetooth er av, vises BT-feltet stiplet på skjermen, og et trykk på BT gir en melding om å holde AIRPLAY.
- Volumknappen: vri for volum, trykk inn for mute (skjermen viser MUTE)
- **POWER-knapp foran** (egen, større knapp med strømsymbol):
  - Kort trykk: av/på (standby). ESP32 slår skjerm og forsterker av/på via mute/enable-pinnen på forsterkerkortet. Ved oppstart vises en startskjerm («Starter AirPlay / Bluetooth / Klar»).
  - Hold 3 s: omstart. Skjermen viser en ring som fylles mens du holder, deretter «Starter på nytt …». Slipper du før ringen er full, avbrytes omstarten.
  - Symbolet lyser fullt når den er på og dimmes til ca. 10 % (PWM) i standby.
- Vippebryteren bak er hovedbryter og bryter all strøm.
- AirPlay og Bluetooth: fastvaren squeezelite-esp32 på ESP32-WROVER (krever PSRAM). Gir AirPlay 1 og Bluetooth-mottak med metadata (tittel, artist, tid).
- Full AirPlay 2 (multirom) krever Raspberry Pi Zero 2 W med shairport-sync i stedet for ESP32.
- Skjermen viser valgt inngang, tittel og artist (ruller hvis lang), play/pause, fremdrift og tid, og volum. På AUX og USB vises et nivåmeter i stedet for fremdrift.

## Materialer
- **Kasse og lokk:** PLA Matte, antrasitt
- **OLED-vindu:** røykfarget/grå akryl, 1–2 mm, skåret til 70 × 38 mm (ikke printet)
- **Volumknapp:** kjøpt aluminiumsknapp, ca. 38 mm, for 6 mm D-aksel (EC11)
- Hvis kassen blir varm (over ca. 55 °C): bytt til PETG

## Utskrift
- Laghøyde 0,12–0,16 mm på lokket (glatte avrundede kanter)
- Frontpanel med forsiden ned mot glatt/teksturert PEI-plate
- Sørg for lufting rundt forsterkerkortet

## Komponenter
- 2,42" OLED SSD1309 (I2C, hvit)
- EC11 rotary encoder med trykkfunksjon (volum, trykk = mute)
- **POWER-knapp:** 16 mm metall trykknapp, svart oksidert, LED ring + strømsymbol, **momentary** (ikke låsende, siden ESP32 styrer standby), hvit LED, spenning **5 V** (eller 3 V). Hull i front: Ø16 mm. Søk: «16mm Metal Push Button Switch Ring Lamp Power Symbol» (f.eks. LANBOO). https://www.aliexpress.com/w/wholesale-16mm-metal-push-button-switch-led-power.html
- **Inngangsknapper (4 stk):** 12 mm «Ultra Short» metall trykknapp, svart oksidert, LED-ring, momentary/self-reset, hvit LED, **5 V** (eller 3 V). Hull i front: Ø12 mm. Søk: «Ultra Short Metal Button Switch 12mm Ring Lamp Self Reset Momentary». https://www.aliexpress.us/w/wholesale-ring-illuminated-push-button.html
- Bestill gjerne et par ekstra og mål flens og gjenge før endelig utskrift. Frontveggen er 4,7 mm tykk (vegg + frontplate), som passer gjengelengden på disse.
- Vippebryter KCD1, utsparing 19,2 × 12,8 mm (bak)
- DC-kontakt for panelmontering, Ø11 mm (bak)
- USB-C, 3,5 mm AUX, 4 høyttalerterminaler, SMA-antenne (bak)
- ESP32-WROVER med PSRAM (AirPlay + Bluetooth, visning av låttittel/artist/tid)
- I2S DAC, f.eks. PCM5102A, mellom ESP32 og forsterkerkortet
- 4 × M3 senkskruer (lokk til kasse)
