# Skjold Røst – fastvare

Røst bruker **squeezelite-esp32** (åpen kildekode, [sle118/squeezelite-esp32](https://github.com/sle118/squeezelite-esp32)). Da blir høyttaleren en vanlig Squeezebox-spiller i Lyrion, akkurat som S1, Node og Touch. Lyrion holder alle spillerne i takt, så Røst spiller synkront med resten uten egen synk-kode.

## Installasjon

1. Flash squeezelite-esp32 for **ESP32-S3**. Prosjektets README sier at S3 krever en egen bygg (ESP-IDF 4.4, se «S3 version» der). Sjekk «Releases» og web-installeren først; finnes ingen S3-bygg, må du bygge selv. Velg oppsett for S3 med PSRAM (N16R8, oktal PSRAM).
2. Koble til Wi-Fi-nettet som ESP-en lager (standard «squeezelite» / «squeezelite»), gå til 192.168.4.1 og legg inn ditt Wi-Fi.
3. Åpne ESP-ens nettside, slå på NVS-editoren («Credits» → «Show NVS editor») og legg inn nøklene fra [`squeezelite-esp32.txt`](squeezelite-esp32.txt). Navnet må begynne med «Skjold Røst» eller «Skjold Rost», for eksempel «Skjold Rost bad». Bruk helst ASCII «Rost» i fastvaren; Skjold viser høyttaleren som Skjold Røst.
4. Start på nytt. Røst dukker opp i Lyrion og i Skjold under **Grupper → Skjold Røst**. Trykk **Spill her** for å spille sammen med rommet du står i, og **Knapper** for å velge hvilke radiofavoritter knappene 1–4 spiller.
5. For egen visning på skjermen (f.eks. VU-meter): installer pluginen **SqueezeESP32** i Lyrion (Innstillinger → Plugins) og velg visning under spillerens innstillinger.

## Betjening

| Handling | Hva skjer |
|---|---|
| Drei knappen | Volum |
| Trykk | Spill / pause |
| Langt trykk | Bytter dreieknappen til forrige/neste (langt trykk igjen bytter tilbake) |
| ⏻ | Av / på |
| 1–4 | Spiller radiofavoritt 1–4 (velges i Skjold) |
| Skjermen | Kanal eller låt, artist og volum (monokrom: tekst og ikoner, ikke cover) |

## Alternativ: Snapcast

Bruker du Snapcast-pluginen i stedet for Lyrion, kan Røst kjøre [snapclient for ESP32](https://github.com/CarlosDerSeher/snapclient) med samme lydpinner (I²S 4/5/6, forsterker på 7). Da styres den fra Snapcast, og skjerm og knapper må settes opp der.

## Mikrofon (valgfri)

INMP441 (SCK 41, WS 42, SD 40) er koblet opp for fremtidig stemmestyring og måling med romkorreksjon. squeezelite-esp32 bruker den ikke.

## Ikke testet

Ingenting er flashet på ekte maskinvare. Nøklene er skrevet etter README-en til squeezelite-esp32, men det er ikke sjekket at S3-bygget godtar alle sammen, at SSD1309-modulen svarer som SSD1306 på adresse 0x3C (eller trenger HFlip/VFlip eller reset-pinne), eller at «hold for å lagre» virker i rå-modus.
