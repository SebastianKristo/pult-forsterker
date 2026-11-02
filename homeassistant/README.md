# Home Assistant

1. Installer integrasjonen:

**Med HACS (anbefalt – får oppdateringer automatisk):**
HACS → ⋮ → *Custom repositories* → `https://github.com/SebastianKristo/pult-forsterker`, type **Integration** → *Add*. Søk «Skjold» (tidligere «Pultforsterker») → *Download* → start HA på nytt.

**Uten HACS:** kopier `custom_components/ki_pultforsterker` (i roten av repoet) til `<config>/custom_components/`.

2. Start Home Assistant på nytt. Forsterkeren oppdages via mDNS (`_kipultamp._tcp`) og vises under *Innstillinger → Enheter → Oppdaget*. Kan også legges til manuelt med host/port.
3. Entiteter (enhet «Pultforsterker»): `media_player.ki_pultforsterker` (kilde, volum, mute, av/på), `switch.ki_pultforsterker_strom`, `sensor.ki_pultforsterker_kilde/tittel/artist`, `binary_sensor.ki_pultforsterker_spiller`, `button.ki_pultforsterker_start_bluetooth_parring`, `switch.ki_pultforsterker_loudness`, `number.ki_pultforsterker_loudness_styrke`.
4. Fra 2.13.0 følger kildelista (mediespiller, nivå per kilde) det kortet rapporterer i `inputs` (inkl. **Spotify**); på Skjold Node opprettes ikke AUX/USB, hodetelefon-, overtemperatur- eller USB-switch-entiteter, men en **Skjermlysstyrke**-select. Enheten får navnet fra daemonen (`name`), og det er knapper for **Start på nytt** og **Slå av** (sistnevnte er av som standard).
5. Fra 2.14.0 støttes alle tre produktene – enheten heter **Skjold S1**, **Skjold Node** eller **Skjold Core** (modell i enhetsregisteret, produsent «Skjold», fra `product` i `/api/status`):

   | Entiteter | S1 | Node | Core |
   |---|---|---|---|
   | Mediespiller, strøm, loudness, talemeldinger, auto-kilde, miks, kilde/tittel/artist, spiller, BT-paring, omstart/slå av, radiofavoritt (inntil 50, fra `/api/presets`) | ✓ | ✓ | ✓ |
   | AUX 1/2 og USB i kildelista, hodetelefoner, overtemperatur, auto-demping, USB-switch | ✓ | – | – |
   | Skjermlysstyrke | ✓ | ✓ | – |
   | **LED-lysstyrke** (number 0–100 %) og **LED-modus** (select: ved trykk / alltid / av) | – | ✓ | – |

   Kildelista følger `inputs` (Node/Core: Radio, AirPlay, Bluetooth, Spotify – og Plex når den finnes). `media_player.play_media` med `media_content_type: preset` tar favoritt 1–50.
6. **Manuelt oppsett:** finnes ikke enheten automatisk, velg *Legg til integrasjon → Skjold* og skriv inn IP-adressen (port 8765 som standard). Integrasjonen sjekker `/api/status` og bruker enhetens id (vertsnavnet – samme som mDNS) som unik id, så den ikke dukker opp dobbelt når mDNS finner den senere.
7. Valgfritt: `../pi/ki_pultforsterker_package.yaml` i `packages/` gir auto-av etter stillhet og et TTS-skript (alt med «KI»-prefiks).

## Ikon og logo i Home Assistant

HA henter ikoner for integrasjoner fra [home-assistant/brands](https://github.com/home-assistant/brands) – de kan ikke ligge i selve integrasjonen. Filene ligger klare i `brands/ki_pultforsterker/` (`icon.png` 256, `icon@2x.png` 512, `logo.png`, `logo@2x.png`). For å få dem inn:

1. Fork `home-assistant/brands`, kopier mappen til `custom_integrations/ki_pultforsterker/`.
2. Lag en pull request (de merges vanligvis innen noen dager).
3. Etterpå viser HA ikonet automatisk under *Enheter og tjenester* og i enhetsvisningen (ingen endring i integrasjonen).

Inntil PR-en er inne viser HA standard-ikonet. Entitetene har allerede egne `mdi:`-ikoner (speaker, knob, loudness).


## Radio (Lyrion)

Har du Lyrion Music Server, blir forsterkeren en radiospiller:

1. Sett `KI_AMP_LMS_SERVER=<IP til Lyrion>` i `/etc/ki-amp.env` (tom = finn automatisk) og `sudo systemctl restart ki-squeezelite ki-amp`. Spilleren «Pultforsterker» dukker opp i Lyrion.
2. Kanal 1–6 hentes automatisk fra de seks første radiofavorittene i Lyrion første gang. Lagre en ny kanal: spill den i Lyrion og bruk «Lagre kanal» (API `{"n":3,"save":true}`, Homey-flytkort, eller hold favorittknappen 2 s på Radio Retro).
3. I HA: kilden **Radio** på mediespilleren, `select.pultforsterker_radiokanal`, knappene **Radio 1–6** (navnet følger stasjonen), og `media_player.play_media` med `media_content_type: preset`, `media_content_id: "3"`.
4. Stasjonsbildet (eller albumbildet når stasjonen sender låtinfo) vises som bilde på mediespilleren. ◀◀/▶▶ bytter kanal.

```yaml
# eksempel: KI Morgenradio
action: media_player.play_media
target: { entity_id: media_player.pultforsterker }
data: { media_content_type: preset, media_content_id: "1" }
```
