#!/usr/bin/env bash
# Skjold-oppstartsskjerm: Skjold-logoen (pi/touch/oppstart.png) på svart fra strømmen kommer på til kiosken er oppe,
# i stedet for regnbuen og tekst fra Linux. Brukes av Skjold Touch og S1 (skjermene). Trygg å kjøre flere ganger:
# gjør ingenting når alt allerede er på plass. KI_SPLASH=0 i /etc/ki-amp.env hopper over.
#   sudo bash pi/install_splash.sh
set -uo pipefail
[ "$(id -u)" = 0 ] || { echo "Kjør som root (sudo)" >&2; exit 1; }
HER="$(cd "$(dirname "$0")" && pwd)"
LOGO="$HER/touch/oppstart.png"
[ -f "$LOGO" ] || { echo "Oppstartsskjerm: mangler $LOGO" >&2; exit 0; }
grep -q '^KI_SPLASH=0' /etc/ki-amp.env 2>/dev/null && { echo "  Oppstartsskjerm: slått av (KI_SPLASH=0)"; exit 0; }

endret=0
if ! command -v plymouth-set-default-theme >/dev/null 2>&1; then
  apt-get install -y -qq plymouth plymouth-themes >/dev/null 2>&1 || { echo "Oppstartsskjerm: fikk ikke installert plymouth – hopper over."; exit 0; }
  endret=1
fi

T=/usr/share/plymouth/themes/skjold
mkdir -p "$T"
if ! cmp -s "$LOGO" "$T/logo.png"; then cp "$LOGO" "$T/logo.png"; endret=1; fi
cat > "$T/skjold.script.ny" <<'P'
// Skjold: logoen midt på svart, og en rolig «pust» så det synes at noe skjer (oppstart og oppdatering)
Window.SetBackgroundTopColor(0, 0, 0);
Window.SetBackgroundBottomColor(0, 0, 0);
logo = Image("logo.png");
skala = Window.GetWidth() / 3 / logo.GetWidth();
if (skala > 1) skala = 1;
if (skala < 0.45) skala = 0.45;
logo = logo.Scale(logo.GetWidth() * skala, logo.GetHeight() * skala);
s = Sprite(logo);
s.SetX(Window.GetWidth() / 2 - logo.GetWidth() / 2);
s.SetY(Window.GetHeight() / 2 - logo.GetHeight() / 2);
t = 0;
fun refresh() {
  t = t + 1;
  s.SetOpacity(0.72 + 0.28 * Math.Sin(t / 22));
}
Plymouth.SetRefreshFunction(refresh);
// ingen tekst, passord- eller meldingsfelt: meldinger fra systemet vises ikke
fun nothing(a, b) { }
Plymouth.SetMessageFunction(nothing);
P
if cmp -s "$T/skjold.script.ny" "$T/skjold.script"; then rm -f "$T/skjold.script.ny"; else mv "$T/skjold.script.ny" "$T/skjold.script"; endret=1; fi
printf '[Plymouth Theme]\nName=Skjold\nDescription=Skjold\nModuleName=script\n\n[script]\nImageDir=%s\nScriptFile=%s/skjold.script\n' "$T" "$T" > "$T/skjold.plymouth"
if [ "$(plymouth-set-default-theme 2>/dev/null)" != skjold ]; then plymouth-set-default-theme skjold >/dev/null 2>&1 || true; endret=1; fi

# Kjernen og systemd skriver ikke til skjermen: meldingene går til tty3, og bare feil logges
CMD=/boot/firmware/cmdline.txt; [ -f "$CMD" ] || CMD=/boot/cmdline.txt
if [ -f "$CMD" ]; then
  gammel="$(cat "$CMD")"
  sed -i 's/\bconsole=tty1\b/console=tty3/' "$CMD"
  for o in quiet splash loglevel=3 rd.udev.log_level=3 systemd.show_status=false plymouth.ignore-serial-consoles logo.nologo vt.global_cursor_default=0 consoleblank=0; do
    grep -qw -- "$o" "$CMD" || sed -i "1 s/\$/ $o/" "$CMD"
  done
  [ "$gammel" = "$(cat "$CMD")" ] || endret=1
fi
CFG=/boot/firmware/config.txt; [ -f "$CFG" ] || CFG=/boot/config.txt
[ -f "$CFG" ] && { grep -q '^disable_splash=' "$CFG" || { echo 'disable_splash=1' >> "$CFG"; endret=1; }; }

# Ingen påloggingstekst på skjermen når kiosken starter på nytt (oppdatering): tom, svart tty1 uten markør
systemctl disable getty@tty1.service >/dev/null 2>&1 || true
mkdir -p /etc/systemd/system/getty@tty1.service.d
printf '[Service]\nExecStart=\nExecStart=-/bin/true\n' > /etc/systemd/system/getty@tty1.service.d/skjold-tom.conf

if [ "$endret" = 1 ]; then
  command -v update-initramfs >/dev/null && update-initramfs -u >/dev/null 2>&1 || true
  echo "  Oppstartsskjerm: Skjold-logoen er satt opp (synes ved neste omstart)"
else
  echo "  Oppstartsskjerm: på plass"
fi
exit 0
