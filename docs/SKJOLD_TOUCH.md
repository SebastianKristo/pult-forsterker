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
| Mikrofon og høyttaler | ReSpeaker Lite (USB) | ikke satt opp ennå |
| Volumhjul og av/på | EC11 og GPIO-knapp | ikke satt opp ennå |

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

## Status mot designbeskrivelsen (Skjold OS for Touch)

Ferdig:
- Spiller, Hjem, Bibliotek, Rom og Oppsett.
- Ringeklokke-overlegg og snakkeknapp.
- Radio, Navidrome og YouTube Music.
- Rom og grupper via Lyrion.
- Installasjon fra flasheren.

Ikke laget ennå:
- Alarm og vekkeklokke.
- Nattmodus med bakgrunnslys.
- Stemmesatellitt (wyoming + openWakeWord på ReSpeaker Lite).
- Volumhjul og av/på-knapp på GPIO.
- Oppstartslogo (Plymouth).
- MQTT discovery til Home Assistant.
