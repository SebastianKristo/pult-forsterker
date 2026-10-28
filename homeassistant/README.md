# Home Assistant

1. Installer integrasjonen:

**Med HACS (anbefalt – får oppdateringer automatisk):**
HACS → ⋮ → *Custom repositories* → `https://github.com/SebastianKristo/pult-forsterker`, type **Integration** → *Add*. Søk «Pultforsterker» → *Download* → start HA på nytt.

**Uten HACS:** kopier `custom_components/ki_pultforsterker` (i roten av repoet) til `<config>/custom_components/`.

2. Start Home Assistant på nytt. Forsterkeren oppdages via mDNS (`_kipultamp._tcp`) og vises under *Innstillinger → Enheter → Oppdaget*. Kan også legges til manuelt med host/port.
3. Entiteter (enhet «Pultforsterker»): `media_player.ki_pultforsterker` (kilde, volum, mute, av/på), `switch.ki_pultforsterker_strom`, `sensor.ki_pultforsterker_kilde/tittel/artist`, `binary_sensor.ki_pultforsterker_spiller`, `button.ki_pultforsterker_start_bluetooth_parring`, `switch.ki_pultforsterker_loudness`, `number.ki_pultforsterker_loudness_styrke`.
4. Valgfritt: `../pi/ki_pultforsterker_package.yaml` i `packages/` gir auto-av etter stillhet og et TTS-skript (alt med «KI»-prefiks).

## Ikon og logo i Home Assistant

HA henter ikoner for integrasjoner fra [home-assistant/brands](https://github.com/home-assistant/brands) – de kan ikke ligge i selve integrasjonen. Filene ligger klare i `brands/ki_pultforsterker/` (`icon.png` 256, `icon@2x.png` 512, `logo.png`, `logo@2x.png`). For å få dem inn:

1. Fork `home-assistant/brands`, kopier mappen til `custom_integrations/ki_pultforsterker/`.
2. Lag en pull request (de merges vanligvis innen noen dager).
3. Etterpå viser HA ikonet automatisk under *Enheter og tjenester* og i enhetsvisningen (ingen endring i integrasjonen).

Inntil PR-en er inne viser HA standard-ikonet. Entitetene har allerede egne `mdi:`-ikoner (speaker, knob, loudness).

## Music Assistant

Pi-en kjører **Squeezelite** (`ki-squeezelite.service`), så forsterkeren dukker opp i Music Assistant som spiller «Pultforsterker» via MAs innebygde Slimproto-leverandør (*Innstillinger → Leverandører → + → Squeezelite (Slimproto)*). Det gir gapless, synkronisering med andre MA-spillere og MAs egen kø/metadata. Lyden går gjennom samme kjede (dmix → CamillaDSP), så loudness og volum fra forsterkeren gjelder også her.

Alternativt finner MAs **AirPlay**-leverandør forsterkeren direkte (Shairport Sync), men Squeezelite er stabilere for MA.

Finner ikke MA spilleren automatisk (annet VLAN): sett `KI_AMP_MA_SERVER=<ip til MA>` i `/etc/ki-amp.env` og `sudo systemctl restart ki-squeezelite`.
