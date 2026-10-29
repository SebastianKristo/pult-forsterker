# Programvare – Raspberry Pi Zero 2 W

```bash
# på PC-en
scp -r pi <bruker>@pultamp.local:~
# på Pi-en
bash ~/pi/install.sh      # 20–30 min, bygger Shairport Sync + NQPTP
sudo reboot
```

Etter omstart: `aplay -l` viser `sndrpihifiberry`, `i2cdetect -y 1` viser `3c`, `curl http://pultamp.local:8765/api/status` svarer med JSON.

Logger: `journalctl -u ki-amp -f`, `journalctl -u oled-display -f`.

Innstillinger i `/etc/ki-amp.env` (navn, port, `RELAY_ACTIVE_LOW`). Tilstand (volum, kilde, BT) lagres i `/var/lib/ki-amp/state.json`.

Utvikling uten GPIO: daemonen starter også på en vanlig PC («Kjører uten GPIO») slik at API-et og integrasjonene kan testes.

## Teste programvaren på en Pi 4 uten forsterker

Lyd ut på Pi 4 sin 3,5 mm-kontakt i stedet for DAC-en (alt annet – AirPlay, Bluetooth, USB-lyd, loudness, volum, API, HA/Homey – virker som normalt):

```bash
KI_AMP_OUT=headphones bash install.sh
amixer -c Headphones sset PCM 100%
```

Koble 3,5 mm → AUX på en aktiv høyttaler/forsterker. Knapper/encoder/OLED kan kobles rett på Pi-ens header med Dupont (samme GPIO som modulbygget), eller styres fra Home Assistant/Homey/`curl`. Når hovedkortet kommer: kjør `bash install.sh` på nytt (uten `KI_AMP_OUT`) og sett `KI_AMP_BOARD=main` i `/etc/ki-amp.env`.

Merk: USB-gadget-lyd på Pi 4 går over USB-C-porten (den eneste OTG-porten). Da må Pi-en få strøm fra PC-ens USB-port (holder på en USB 3-port for en headless Pi 4) eller via 5 V på header pinne 2/6.
