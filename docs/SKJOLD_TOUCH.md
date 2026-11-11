# Skjold Touch – installasjon

Skjold Touch er en 7″ berøringsskjerm i Skjold-serien. Den er en musikkspiller, et smarthus-panel og en nattbordsklokke.
Programvaren er den samme som på S1 og Node (`pi/ki_amp_daemon.py`). Forskjellen er at skjermen viser touch-UI-et
(`skjold/app/src/touch`, 800 × 480) i en kiosk med cage + Chromium.

## Maskinvare

| Del | Hva | Innstilling |
|---|---|---|
| Datamaskin | Raspberry Pi 4 (Pi 3 virker, men er tregere) | Raspberry Pi OS Lite 64-bit |
| Skjerm | Waveshare 7″ DSI, 800 × 480, kapasitiv berøring | Pi OS finner den selv (`display_auto_detect=1`) |
| Lyd ut | Spotpear PCM5122 HiFi DAC HAT (I²S), RCA + 3,5 mm | `dtoverlay=hifiberry-dacplus-std` |
| Mikrofon og høyttaler | ReSpeaker Lite (USB) | valgfritt: `KI_TOUCH_VOICE=1` |
| Volumhjul | EC11 med trykk | valgfritt: `KI_TOUCH_ENC=A,B,SW` |
| Av/på-knapp | GPIO-knapp | ikke satt opp ennå |

## Installere

**Med Skjold Flasher (anbefalt):** velg **Skjold Touch**, skriv kortet og sett det i Pi-en. Første oppstart henter
Skjold og installerer alt. Det tar ca. 15–20 minutter. Deretter starter Pi-en på nytt med Skjold på skjermen.

**For hånd** på en ren Raspberry Pi OS Lite:

```bash
git clone https://github.com/SebastianKristo/pult-forsterker.git && cd pult-forsterker
KI_AMP_BOARD=touch bash pi/install.sh && sudo reboot
```

`KI_AMP_BOARD=touch` gjør dette:
- Skjold kjører som en Node uten GPIO (`KI_AMP_NODE_GPIO=0`) og digitalt volum i CamillaDSP.
- Lyden går ut på PCM5122.
- Produktet heter «touch» (`KI_AMP_PRODUCT=touch`), og spillernavnet er «Skjold Touch».
- `pi/install_touch.sh` setter opp kiosken: cage + Chromium på `http://127.0.0.1:8765/touch.html`, med ekte touch
  via libinput og uten musepeker.

## Sjekk på enheten

Disse innstillingene er ikke gjettet. De ligger som valg i installasjonen:

| Valg | Standard | Når må du endre det? |
|---|---|---|
| `KI_TOUCH_DAC_OVERLAY` | `hifiberry-dacplus-std` | `aplay -l` viser ikke `sndrpihifiberry` |
| `KI_TOUCH_DSI_OVERLAY` | tom (automatisk) | skjermen er svart. Prøv for eksempel `vc4-kms-dsi-7inch` (se Waveshare-wikien for din modell) |
| `KI_TOUCH_ROTATE` | `0` | bildet står opp ned eller på siden (`90`, `180`, `270`) |
| `KI_TOUCH_ENC` | tom (ikke i bruk) | du har loddet på volumhjulet. Skriv BCM-pinnene: `A,B` eller `A,B,SW` |
| `KI_TOUCH_VOICE` | `0` | du vil ha stemmeassistent. Sett `1` |
| `KI_TOUCH_MIC`, `KI_TOUCH_SPK` | `plughw:CARD=Lite,DEV=0` | `arecord -L` og `aplay -L` viser et annet navn på ReSpeaker Lite |
| `KI_TOUCH_SPLASH` | `1` | du vil beholde Raspberry Pi sin vanlige oppstart. Sett `0` |

Slik tester du:

```bash
aplay -l
```

Skal vise `sndrpihifiberry` (PCM5122).

```bash
speaker-test -D hw:sndrpihifiberry -c 2 -t wav
```

Lyd i RCA og 3,5 mm.

```bash
sudo libinput debug-events
```

Skal vise `TOUCH_DOWN` når du trykker, ikke `POINTER_MOTION`.

```bash
systemctl status ki-amp skjold-touch
```

Begge tjenestene skal være `active`.

## Slik brukes skjermen

Menyen til venstre: **Spiller · Hjem · Smarthus · Alarm · Bibliotek · Rom · Oppsett**.

### Smarthus

Viser fliser fra Home Assistant: lys, brytere, porter, varme, sensorer og kamera, og opptil fire scener øverst.
Trykk på en flis slår av eller på. Varme har − og +. Låser og alarmer kan ikke styres med et trykk på en flis.

1. Koble til Home Assistant i appen: **Innstillinger → Rutiner og dørklokke → Dørklokke**. Skriv adressen og et
   langtidstoken. Touch bruker det samme.
2. Velg fliser. Uten valg viser Touch fire lys, én varme, én port og to brytere.

```bash
curl -X POST http://skjold-touch.local:8765/api/touch -H 'Content-Type: application/json' \
  -d '{"tiles":["light.stue","climate.stue","cover.garasje"],"scenes":["scene.kveld"],"lock_entity":"lock.inngang","weather_entity":"weather.hjem","light_entity":"light.soverom"}'
```

`lock_entity` gir knappen «Lås opp» når det ringer på. `weather_entity` og `light_entity` gir linja under klokka når
alarmen ringer («6 °C og overskyet · lyset på soverommet er på 40 %»).

**Homey i stedet for Home Assistant:** lag en API-nøkkel i Homey (Innstillinger → API-nøkler, med tilgang til enheter)
og send den til Touch:

```bash
curl -X POST http://skjold-touch.local:8765/api/touch -H 'Content-Type: application/json' \
  -d '{"hub":"homey","homey_url":"http://homey-xxxx.local","homey_token":"<nøkkelen>"}'
```

Uten valg vises fire lys, én varme og to brytere. Velg selv med `"homey_devices": ["<enhets-ID>", …]`. Lys kan dimmes,
varme justeres, og låser kan ikke styres med et trykk. Scener (Flows) vises ikke ennå. Ikke prøvd mot en ekte Homey.

### Vekkeklokke

Opptil ti alarmer. ‹ og › flytter tiden fem minutter. Trykk på dagene for å bytte mellom hverdager, helg og hver dag,
og på «Vanlig» for å slå på smart vekking (lyden øker over tre minutter). Alarmene er de samme som i appen
(**Plugins → Vekkerklokke**), ligger på enheten og virker uten nett.

Når alarmen ringer, våkner skjermen med **Slumre 9 min** og **Slå av**. Det samme kan gjøres utenfra:

```bash
curl -X POST http://skjold-touch.local:8765/api/alarm -d '{"action":"snooze"}'
```

`action` er `snooze`, `stop` eller `test`. Ingen som slår av? Da gir alarmen seg etter 30 minutter.

### Ringeklokke

**Oppsett → Ringeklokke**: *Vis kamera* (fullskjerm, lukkes etter 30 s), *Bare varsel* (en linje øverst i 5 s, trykk for
kamera) eller *Av*. Ringingen kommer fra `POST /api/doorbell` eller fra entiteten du valgte i appen.

### Standby og nattmodus

Skjermen hviler etter 30 s, 1 min eller 5 min, og viser klokke, cover eller svart. Neste alarm står under klokka.
Nattmodus: *Av*, *Tidsplan* (fra og til stilles på skjermen), *HA/Homey* (bryteren «Nattmodus» i Home Assistant eller
Homey bestemmer) eller *På*. Om natten er klokka rødlig og bakgrunnslyset skrus ned.

### Stemme

Med `KI_TOUCH_VOICE=1` installeres wyoming-satellite og openWakeWord. Legg til enheten i Home Assistant under
**Innstillinger → Enheter og tjenester → Wyoming Protocol** (port 10700). Skjermen viser «Lytter», det du sa og svaret.
Vekkeord og demping av mikrofonen velges under **Oppsett**.

### Fra Home Assistant og Homey

Med MQTT slått på (**Plugins → MQTT-bro**) dukker Touch opp med disse i tillegg til de vanlige:

| Entitet | Hva |
|---|---|
| Alarm ringer | på mens alarmen ringer |
| Slå av alarm, Slumre | knapper |
| Vekk skjermen, Skjerm i standby | knapper |
| Nattmodus | bryter |

Uten MQTT:

```bash
curl -X POST http://skjold-touch.local:8765/api/touch/cmd -d '{"cmd":"page","arg":"alarm"}'
```

`cmd` er `standby`, `wake`, `boot` eller `page` (med `arg`: `now`, `home`, `smart`, `alarm`, `lib`, `rooms`, `set`).

## Status mot designbeskrivelsen (Skjold OS for Touch)

Ferdig:
- Spiller, Hjem, Smarthus, Alarm, Bibliotek, Rom og Oppsett, med valgfri startside.
- Vekkeklokke med slumring, smart vekking og fullskjerm når den ringer.
- Ringeklokke med kamera, varsel og «Lås opp».
- Standby med klokke, cover eller svart. Nattmodus med tidsplan, styring fra HA/Homey og bakgrunnslys.
- Stemmeoverlegg og installasjon av stemmesatellitt.
- Oppstartslogo, volumhjul (når pinnene er oppgitt) og MQTT discovery.
- Radio, Navidrome og YouTube Music. Rom og grupper. Installasjon fra flasheren.

Ikke prøvd på ekte maskinvare ennå (alt er testet mot en simulert Home Assistant på PC):
- Bakgrunnslys på akkurat denne skjermen (`/sys/class/backlight`).
- ReSpeaker Lite sine ALSA-navn, og at wyoming-satellite installerer rent på Pi OS.
- Oppstartslogoen (Plymouth) sammen med kiosken.

Ikke laget ennå:
- Scener (Flows) fra Homey.
- Toveis lyd («Snakk») mot ringeklokka, og direktevideo (kameraet vises som bilde som oppdateres hvert sekund).
- Av/på-knapp på GPIO.
- Lang trykk på en flis for dimmer og farge.
