# Skjold Mini – fastvare

Mini bruker **squeezelite-esp32** (åpen kildekode, [sle118/squeezelite-esp32](https://github.com/sle118/squeezelite-esp32)). Da blir høyttaleren en vanlig Squeezebox-spiller i Lyrion, akkurat som S1, Node og Touch. Lyrion holder alle spillerne i takt, så Mini spiller synkront med resten uten egen synk-kode.

## Installasjon

1. Flash squeezelite-esp32 for **ESP32-S3** med prosjektets web-installer eller `esptool` (se prosjektets README). Velg en bygg for S3 med PSRAM (N16R8).
2. Koble til Wi-Fi-nettet `squeezelite-xxxx` som ESP-en lager, og legg inn ditt Wi-Fi.
3. Åpne ESP-ens nettside og legg inn innstillingene fra [`squeezelite-esp32.txt`](squeezelite-esp32.txt). Navnet må begynne med «Skjold Mini», for eksempel «Skjold Mini bad».
4. Start på nytt. Mini dukker opp i Lyrion og i Skjold under **Grupper → Skjold Mini**. Trykk **Spill her** for å spille sammen med rommet du står i.

## Betjening

| Handling | Hva skjer |
|---|---|
| Drei knappen | Volum |
| Trykk | Spill / pause |
| Langt trykk | Neste (squeezelite-esp32 `longpress`) |
| Grønt lys | Tilkoblet |
| Rødt lys | Ingen kontakt med Lyrion |

## Alternativ: Snapcast

Bruker du Snapcast-pluginen i stedet for Lyrion, kan Mini kjøre [snapclient for ESP32](https://github.com/CarlosDerSeher/snapclient) med samme pinner (I²S 4/5/6, forsterker på 7). Da styres den fra Snapcast, ikke fra Mini-kortet i Skjold.

## Mikrofon (valgfri)

INMP441 (SCK 41, WS 42, SD 40) er koblet opp for fremtidig stemmestyring og måling med romkorreksjon. squeezelite-esp32 bruker den ikke.
