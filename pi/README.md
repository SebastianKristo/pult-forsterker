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
