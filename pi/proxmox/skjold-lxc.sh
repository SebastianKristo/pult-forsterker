#!/usr/bin/env bash
# Skjold Core i en Proxmox-LXC, med lyd ut på vertens eget lydkort (analog linje-ut/hodetelefon/AUX, HDMI eller USB).
#
# Kjør på Proxmox-verten (shell som root):
#   bash -c "$(curl -fsSL https://raw.githubusercontent.com/SebastianKristo/pult-forsterker/main/pi/proxmox/skjold-lxc.sh)"
#
# Uten dialoger (alle er valgfrie):
#   SKJOLD_CTID=210 SKJOLD_STORAGE=local-lvm SKJOLD_BRIDGE=vmbr0 SKJOLD_CARD=PCH SKJOLD_PCM=0 \
#   SKJOLD_NAME="Skjold Stue" SKJOLD_UNPRIVILEGED=0 SKJOLD_YES=1 bash skjold-lxc.sh
set -euo pipefail

REPO="${SKJOLD_REPO:-https://github.com/SebastianKristo/pult-forsterker.git}"
BRANCH="${SKJOLD_BRANCH:-main}"
YES="${SKJOLD_YES:-0}"
say() { printf '\033[1;33m== %s\033[0m\n' "$*"; }
die() { printf '\033[1;31mFEIL: %s\033[0m\n' "$*" >&2; exit 1; }
have_ui() { [ "$YES" != 1 ] && command -v whiptail >/dev/null && [ -t 0 ]; }
ask() {   # ask <tittel> <spørsmål> <standard>
  if have_ui; then whiptail --title "Skjold" --inputbox "$2" 10 70 "$3" 3>&1 1>&2 2>&3 || exit 1; else echo "$3"; fi
}

[ "$(id -u)" = 0 ] || die "kjør som root på Proxmox-verten"
command -v pveversion >/dev/null || die "dette er ikke en Proxmox VE-vert (fant ikke pveversion)"
say "Proxmox $(pveversion | head -n1)"

# ---------- lydkort på verten ----------
say "Laster snd-aloop (intern miks-kabel for Skjold) på verten"
modprobe snd-aloop pcm_substreams=1 || die "kunne ikke laste snd-aloop"
grep -qx snd-aloop /etc/modules-load.d/skjold-aloop.conf 2>/dev/null || echo snd-aloop > /etc/modules-load.d/skjold-aloop.conf
[ -f /etc/modprobe.d/skjold-aloop.conf ] || echo "options snd-aloop pcm_substreams=1" > /etc/modprobe.d/skjold-aloop.conf

mapfile -t CARDS < <(awk -F'[][]' '/^ *[0-9]+ \[/ {id=$2; gsub(/ /,"",id); sub(/^[^:]*: */,"",$3); print id "|" $3}' /proc/asound/cards | grep -v '^Loopback|')
[ "${#CARDS[@]}" -gt 0 ] || die "verten har ingen lydkort (cat /proc/asound/cards). Sjekk at snd_hda_intel er lastet, eller sett i et USB-lydkort."
DEF_CARD="${SKJOLD_CARD:-}"
if [ -z "$DEF_CARD" ]; then
  DEF_CARD="${CARDS[0]%%|*}"
  for c in "${CARDS[@]}"; do case "${c%%|*}" in PCH|Generic|Intel|Device|CODEC) DEF_CARD="${c%%|*}"; break ;; esac; done
fi
CARD="$DEF_CARD"
if have_ui && [ -z "${SKJOLD_CARD:-}" ]; then
  MENU=(); for c in "${CARDS[@]}"; do MENU+=("${c%%|*}" "${c#*|}"); done
  CARD=$(whiptail --title "Skjold – lydutgang" --default-item "$DEF_CARD" --menu \
    "Hvilket lydkort skal Skjold spille på?\n(PCH/Generic = PC-ens analoge linje-ut/hodetelefon)" 18 78 8 "${MENU[@]}" 3>&1 1>&2 2>&3) || exit 1
fi
# Utganger på valgt kort fra /proc/asound/pcm (krever ikke alsa-utils/aplay på verten): «00-03: HDMI 0 : HDMI 0 : playback 1»
CNUM=$(awk -v c="$CARD" -F'[][]' '/^ *[0-9]+ \[/ {id=$2; gsub(/ /,"",id); n=$1; gsub(/ /,"",n); if (id==c) {print n; exit}}' /proc/asound/cards)
PCMS=()
if [ -n "$CNUM" ] && [ -r /proc/asound/pcm ]; then
  mapfile -t PCMS < <(awk -v c="$CNUM" -F': ' '$0 ~ /playback/ {split($1,a,"-"); if (a[1]+0==c+0) print a[2]+0 "|" $2}' /proc/asound/pcm)
fi
PCM="${SKJOLD_PCM:-}"
if [ -z "$PCM" ]; then PCM=0; [ "${#PCMS[@]}" -gt 0 ] && PCM="${PCMS[0]%%|*}"; fi
if have_ui && [ -z "${SKJOLD_PCM:-}" ] && [ "${#PCMS[@]}" -gt 1 ]; then
  MENU=(); for p in "${PCMS[@]}"; do MENU+=("${p%%|*}" "${p#*|}"); done
  PCM=$(whiptail --title "Skjold – utgang på $CARD" --menu "Velg utgang (0 er vanligvis analog, 3/7/8 er HDMI):" 16 78 6 "${MENU[@]}" 3>&1 1>&2 2>&3) || exit 1
fi
say "Lydutgang: $CARD, enhet $PCM"
if pgrep -x pulseaudio >/dev/null || pgrep -x pipewire >/dev/null; then
  echo "ADVARSEL: PulseAudio/PipeWire kjører på verten og kan holde lydkortet opptatt. Stopp dem, ellers får Skjold «Device or resource busy»." >&2
fi

# ---------- container ----------
CTID="${SKJOLD_CTID:-$(pvesh get /cluster/nextid)}"
CTID=$(ask "" "Container-ID:" "$CTID")
pct status "$CTID" >/dev/null 2>&1 && die "container $CTID finnes allerede – velg en annen ID (SKJOLD_CTID)"
NAME=$(ask "" "Navn i AirPlay/Spotify/Lyrion:" "${SKJOLD_NAME:-Skjold Core}")
HOST=$(echo "$NAME" | tr '[:upper:] ' '[:lower:]-' | tr -cd 'a-z0-9-'); HOST="${HOST:-skjold}"
STORAGE="${SKJOLD_STORAGE:-$(pvesm status -content rootdir 2>/dev/null | awk 'NR>1 && $3=="active" {print $1; exit}')}"
STORAGE=$(ask "" "Lagring for containeren:" "${STORAGE:-local-lvm}")
BRIDGE=$(ask "" "Nettverksbro (må være på samme nett som telefonene for AirPlay/mDNS):" "${SKJOLD_BRIDGE:-vmbr0}")
UNPRIV="${SKJOLD_UNPRIVILEGED:-0}"
if have_ui && [ -z "${SKJOLD_UNPRIVILEGED:-}" ]; then
  whiptail --title "Skjold" --yesno "Lage en privilegert container?\n\nAnbefalt: lyd, AirPlay 2 (nqptp på port 319/320) og mDNS virker uten ekstra oppsett.\nVelg Nei for upriviligert (lyd via idmap av audio-gruppen)." 13 74 && UNPRIV=0 || UNPRIV=1
fi

say "Henter Debian-mal"
pveam update >/dev/null || true
TPL=$(pveam available --section system | awk '{print $2}' | grep -E '^debian-1[23]-standard_.*amd64' | sort -V | tail -n1)
[ -n "$TPL" ] || die "fant ingen Debian 12/13-mal (pveam available)"
TSTORE="${SKJOLD_TEMPLATE_STORAGE:-local}"
pveam list "$TSTORE" | grep -q "$TPL" || pveam download "$TSTORE" "$TPL"

say "Lager container $CTID ($HOST)"
pct create "$CTID" "$TSTORE:vztmpl/$TPL" --hostname "$HOST" --cores 2 --memory 1024 --swap 512 \
  --rootfs "$STORAGE:8" --net0 "name=eth0,bridge=$BRIDGE,ip=dhcp" --features nesting=1 \
  --unprivileged "$UNPRIV" --onboot 1 --ostype debian --description "Skjold Core – lyd ut på $CARD,$PCM"
CONF=/etc/pve/lxc/$CTID.conf
{
  echo "lxc.cgroup2.devices.allow: c 116:* rwm"
  echo "lxc.mount.entry: /dev/snd dev/snd none bind,optional,create=dir"
} >> "$CONF"
if [ "$UNPRIV" = 1 ]; then   # gi containerens audio-gruppe (gid 29) tilgang til vertens /dev/snd/* (eid av audio = 29)
  grep -q '^root:29:1' /etc/subgid || echo "root:29:1" >> /etc/subgid
  cat >> "$CONF" <<'EOF'
lxc.idmap: u 0 100000 65536
lxc.idmap: g 0 100000 29
lxc.idmap: g 29 29 1
lxc.idmap: g 30 100030 65506
EOF
fi

say "Starter containeren"
pct start "$CTID"
for _ in $(seq 30); do pct exec "$CTID" -- getent hosts deb.debian.org >/dev/null 2>&1 && break; sleep 2; done
pct exec "$CTID" -- bash -c "test -e /dev/snd/controlC0" || echo "ADVARSEL: /dev/snd er ikke synlig i containeren – sjekk $CONF" >&2

say "Installerer Skjold i containeren (tar 5–15 min: AirPlay 2 bygges fra kilde)"
pct exec "$CTID" -- bash -c "export DEBIAN_FRONTEND=noninteractive; apt-get update -qq && apt-get install -y -qq git ca-certificates >/dev/null \
  && git clone -q --depth 50 -b '$BRANCH' '$REPO' /opt/skjold-src \
  && KI_AMP_CARD='$CARD' KI_AMP_PCM='$PCM' KI_AMP_NAME='$NAME' bash /opt/skjold-src/pi/install_x86.sh"

IP=$(pct exec "$CTID" -- hostname -I 2>/dev/null | awk '{print $1}')
echo
say "Ferdig"
echo "  Container:  $CTID ($HOST)"
echo "  Lydutgang:  $CARD, enhet $PCM (plughw:$CARD,$PCM)"
echo "  Web-UI:     http://${IP:-<ip>}:8765    (eller http://$HOST.local:8765)"
echo "  Appen finner «$NAME» automatisk på nettet. Oppdateringer: Innstillinger → Oppdatering i appen."
