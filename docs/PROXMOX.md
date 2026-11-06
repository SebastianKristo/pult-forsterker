# Skjold på Proxmox

Kjør Skjold Core i en LXC-container på Proxmox, og bruk PC-ens egen lydutgang (analog linje-ut, hodetelefon/AUX,
HDMI eller et USB-lydkort) som høyttalerutgang. Du får det samme som på en Raspberry Pi: AirPlay 2, Spotify Connect,
Lyrion-radio, web-UI på port 8765, appene, Home Assistant, Homey og Apple Hjem.

## Én kommando

Åpne **Shell** på Proxmox-verten (ikke i en container) og kjør:

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/SebastianKristo/pult-forsterker/main/pi/proxmox/skjold-lxc.sh)"
```

Skriptet spør om noen få ting (med forslag du kan godta med Enter):

1. **Lydutgang** – lydkortene verten har. `PCH` eller `Generic` er PC-ens analoge utgang (grønn 3,5 mm-kontakt bak,
   eller hodetelefonutgangen foran). HDMI-utgangene ligger som egne enheter (ofte 3, 7, 8).
2. **Container-ID, navn, lagring og nettverksbro.** Broen må være på samme nett som telefonene, ellers finner ikke
   AirPlay og appen enheten (mDNS går ikke gjennom rutere).
3. **Privilegert eller upriviligert.** Privilegert anbefales: lyd, AirPlay 2 og mDNS virker uten mer oppsett.

Deretter gjør skriptet dette:

- laster `snd-aloop` på verten (en intern «miks-kabel» Skjold bruker til å blande kildene) og husker det ved omstart,
- laster ned Debian-malen og lager containeren (2 kjerner, 1 GB RAM, 8 GB disk, starter med verten),
- sender vertens lydkort inn i containeren (`/dev/snd`, major 116),
- installerer Skjold Core med `pi/install_x86.sh` (tar 5–15 minutter, AirPlay 2 bygges fra kilde),
- skriver ut adressen til web-UI-et.

Uten spørsmål (f.eks. i et eget skript):

```bash
SKJOLD_YES=1 SKJOLD_CARD=PCH SKJOLD_PCM=0 SKJOLD_NAME="Skjold Stue" SKJOLD_CTID=210 \
  bash -c "$(curl -fsSL https://raw.githubusercontent.com/SebastianKristo/pult-forsterker/main/pi/proxmox/skjold-lxc.sh)"
```

## Oppdatering

Som på en Pi: **Innstillinger → Oppdatering** i appen eller web-UI-et. Eller i containeren:

```bash
cd /opt/skjold-src && git pull && bash pi/update.sh
```

## Viktig om lydkortet

- Et lydkort kan bare brukes av én om gangen. Verten må ikke spille på det samme kortet (Proxmox har normalt ingen
  PulseAudio/PipeWire, så det er sjelden et problem), og bare én container kan bruke det.
- Volumet styres digitalt i Skjold (CamillaDSP). Sett kortets egen utgang høyt én gang:
  `pct exec <id> -- alsamixer` (F6 for å velge kort), eller `amixer -c PCH sset Master 90% unmute`.
- Vil du ha flere rom fra samme PC, bruk ett USB-lydkort per container.

## Alternativ: virtuell maskin

En VM kan ikke låne vertens innebygde lydkort trygt, men et **USB-lydkort** kan sendes inn: VM → Hardware → Add →
USB Device → velg lydkortet. Installer Debian 12/13 i VM-en og kjør:

```bash
git clone https://github.com/SebastianKristo/pult-forsterker.git && sudo KI_AMP_CARD=Device bash pult-forsterker/pi/install_x86.sh
```

(`cat /proc/asound/cards` viser navnet på kortet; i VM-en kan `snd-aloop` lastes direkte.)

## Feilsøking

| Problem | Sjekk |
|---|---|
| Ingen lyd | `pct exec <id> -- aplay -l` skal vise vertens kort. Test: `pct exec <id> -- speaker-test -D plughw:PCH,0 -c 2 -t sine -l 1` |
| «Loopback finnes ikke» | På verten: `modprobe snd-aloop` og `cat /proc/asound/cards` |
| «Device or resource busy» | Noe annet bruker kortet (verten eller en annen container) |
| «Permission denied» på /dev/snd | Upriviligert container: idmap for audio-gruppen (gid 29) må stå i `/etc/pve/lxc/<id>.conf` og `root:29:1` i `/etc/subgid` |
| AirPlay vises ikke | Containeren må være på samme nett/VLAN som telefonen; nqptp bruker UDP 319 og 320 (privilegert container anbefales) |
| Feil utgang (HDMI i stedet for analog) | Sett `KI_AMP_DSP_PLAYBACK=plughw:PCH,0` i `/etc/ki-amp.env` og `systemctl restart camilladsp ki-amp`, eller kjør `pi/install_x86.sh` på nytt med `KI_AMP_CARD`/`KI_AMP_PCM` |

Blåtann, knapper, skjerm og USB-lydkort-modus (Pi som lydkort for PC) finnes ikke i containeren.
