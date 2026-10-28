# Home Assistant

1. Kopier `custom_components/ki_pultforsterker` til `<config>/custom_components/`.
2. Start Home Assistant på nytt. Forsterkeren oppdages via mDNS (`_kipultamp._tcp`) og vises under *Innstillinger → Enheter → Oppdaget*. Kan også legges til manuelt med host/port.
3. Entiteter (enhet «KI Pultforsterker»): `media_player.ki_pultforsterker` (kilde, volum, mute, av/på), `switch.ki_pultforsterker_strom`, `sensor.ki_pultforsterker_kilde/tittel/artist`, `binary_sensor.ki_pultforsterker_spiller`, `button.ki_pultforsterker_start_bluetooth_parring`, `switch.ki_pultforsterker_loudness`, `number.ki_pultforsterker_loudness_styrke`.
4. Valgfritt: `../pi/ki_pultforsterker_package.yaml` i `packages/` gir auto-av etter stillhet og et TTS-skript (alt med «KI»-prefiks).
