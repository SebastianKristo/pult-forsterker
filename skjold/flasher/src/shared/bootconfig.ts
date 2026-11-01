/**
 * Filer som legges på boot-partisjonen (FAT, /boot/firmware på Bookworm) før første oppstart.
 *
 * Tre tilfeller, valgt ut fra hva som ligger på boot-partisjonen (se image.ts):
 *  - 'skjold'    ferdig Skjold-bilde (pi-gen, markørfila skjold-image): bare skjold-setup.json – skjold-setup gjør resten.
 *  - 'cloudinit' Raspberry Pi OS Trixie og nyere: user-data + network-config (cloud-init NoCloud, som Raspberry Pi Imager 2).
 *  - 'systemd'   Raspberry Pi OS Bookworm: firstrun.sh startet via systemd.run= i cmdline.txt (som Raspberry Pi Imager 1.8).
 * For de to siste (rent Raspberry Pi OS Lite 64-bit) legges også skjold-install.sh på boot-partisjonen. Den kjøres som
 * systemd-tjeneste etter første oppstart, henter Skjold fra GitHub og kjører pi/install.sh (S1) eller 3,5 mm-oppsett +
 * skjold/node/driver/installer_node.sh (Node), og starter på nytt.
 */
import { pbkdf2Sync } from 'crypto';
import type { SetupOptions, StaticIp } from './types';
import { sha512crypt } from './sha512crypt';

export const LANG_LOCALE: Record<SetupOptions['lang'], { keymap: string; timezone: string; country: string }> = {
  nb: { keymap: 'no', timezone: 'Europe/Oslo', country: 'NO' },
  en: { keymap: 'gb', timezone: 'Europe/London', country: 'GB' },
  sv: { keymap: 'se', timezone: 'Europe/Stockholm', country: 'SE' },
  da: { keymap: 'dk', timezone: 'Europe/Copenhagen', country: 'DK' },
};

/** «Stue» → «skjold-stue». RFC 1123: a–z, 0–9, bindestrek, maks 63 tegn. */
export function hostnameFromName(name: string): string {
  const base = name.toLowerCase()
    .replace(/æ/g, 'ae').replace(/ø/g, 'o').replace(/å/g, 'a').replace(/ä/g, 'a').replace(/ö/g, 'o')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  const h = base ? (base.startsWith('skjold') ? base : `skjold-${base}`) : 'skjold';
  return h.slice(0, 63).replace(/-+$/, '');
}

export function isValidHostname(h: string): boolean {
  return /^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$/.test(h);
}

export function onboardingUrl(hostname: string): string {
  return `http://${hostname}.local:8765/`;
}

/** Gyldig IPv4-adresse (fire oktetter 0–255, uten ledende nuller). */
export function isIPv4(s: string): boolean {
  const p = s.trim().split('.');
  return p.length === 4 && p.every(x => /^(0|[1-9]\d{0,2})$/.test(x) && Number(x) <= 255);
}

/** «192.168.1.50/24» eller «192.168.1.50» (→ /24). null hvis ugyldig. */
export function parseCidr(s: string): { ip: string; prefix: number } | null {
  const m = /^\s*([0-9.]+)(?:\/(\d{1,2}))?\s*$/.exec(s);
  if (!m || !isIPv4(m[1])) return null;
  const prefix = m[2] === undefined ? 24 : Number(m[2]);
  if (prefix < 1 || prefix > 32) return null;
  const first = Number(m[1].split('.')[0]);
  if (first === 0 || first === 127 || first >= 224) return null;
  return { ip: m[1], prefix };
}

export function dnsList(s: string): string[] {
  return s.split(/[\s,;]+/).map(x => x.trim()).filter(Boolean);
}

/** Feilmelding for fast IP, eller null når feltene er gyldige. */
export function validateStatic(st: StaticIp): string | null {
  if (!parseCidr(st.ip)) return 'Ugyldig IP-adresse. Skriv f.eks. 192.168.1.50/24.';
  if (st.gw.trim() && !isIPv4(st.gw)) return 'Ugyldig ruteradresse. Skriv f.eks. 192.168.1.1.';
  if (dnsList(st.dns).some(d => !isIPv4(d))) return 'Ugyldig DNS-adresse. Skriv f.eks. 1.1.1.1.';
  return null;
}

const isEth = (o: SetupOptions) => o.preset && o.net === 'eth';
const isWifi = (o: SetupOptions) => o.preset && o.net !== 'eth';
const staticOf = (o: SetupOptions) => (isEth(o) && o.staticIp ? o.staticIp : null);

export function validate(o: SetupOptions): string | null {
  if (!isValidHostname(o.hostname)) return 'Ugyldig vertsnavn (bare a–z, 0–9 og bindestrek).';
  if (o.preset) {
    if (isWifi(o)) {
      if (!o.ssid.trim() || Buffer.byteLength(o.ssid, 'utf8') > 32) return 'Wi-Fi-navnet må være 1–32 byte.';
      if (o.wifiPassword.length < 8 || o.wifiPassword.length > 63) return 'Wi-Fi-passordet må være 8–63 tegn.';
    }
    const st = staticOf(o);
    if (st) { const e = validateStatic(st); if (e) return e; }
    if (!o.name.trim()) return 'Skriv inn et navn eller rom.';
    if (!/^[A-Z]{2}$/.test(o.country)) return 'Landkode må være to bokstaver (f.eks. NO).';
  }
  if (o.ssh) {
    if (!/^[a-z_][a-z0-9_-]{0,31}$/.test(o.user)) return 'Ugyldig brukernavn.';
    if (o.user === 'root') return 'Brukernavnet kan ikke være root.';
    if (!o.userPassword && !o.sshKey.trim()) return 'SSH krever passord eller offentlig nøkkel.';
    if (o.userPassword && o.userPassword.length < 6) return 'SSH-passordet må være minst 6 tegn.';
    if (o.sshKey.trim() && !/^(ssh-(ed25519|rsa)|ecdsa-sha2-nistp\d+|sk-\S+) [A-Za-z0-9+/=]+( .*)?$/.test(o.sshKey.trim()))
      return 'Den offentlige nøkkelen ser ikke gyldig ut.';
  }
  return null;
}


export type InitMode = 'skjold' | 'cloudinit' | 'systemd';
export interface BootFile { name: string; content: string }

export const REPO = 'SebastianKristo/pult-forsterker';
export const INSTALL_REF = 'main';
/** Legges til i cmdline.txt i systemd-modus. firstrun.sh fjerner alt fra « systemd.run» og ut igjen. */
export const FIRSTRUN_CMDLINE = ' systemd.run=/boot/firmware/firstrun.sh systemd.run_success_action=reboot systemd.unit=kernel-command-line.target';

const sq = (s: string) => `'${s.replace(/'/g, `'\\''`)}'`;          // shell, enkeltfnutter
const yq = (s: string) => JSON.stringify(s);                          // JSON-streng er gyldig YAML

/** WPA-PSK (64 hex) – så klartekstpassordet aldri havner på kortet i systemd-modus. */
export function wpaPsk(ssid: string, password: string): string {
  return pbkdf2Sync(password, Buffer.from(ssid, 'utf8'), 4096, 32, 'sha1').toString('hex');
}

function installScript(): string {
  return `#!/bin/bash
# Skjold – installerer programvaren ved første oppstart. Lagt inn av Skjold Flasher.
# Logg: /var/log/skjold-install.log. Kjøres av skjold-install.service til den lykkes.
set -uo pipefail
exec >>/var/log/skjold-install.log 2>&1
echo "=== $(date -Is) skjold-install starter"
B=/boot/firmware; [ -f $B/skjold-setup.json ] || B=/boot
get() { python3 -c "import json,sys;print(json.load(open('$B/skjold-setup.json')).get(sys.argv[1],sys.argv[2]))" "$1" "$2" 2>/dev/null || echo "$2"; }
DEVICE=$(get device s1); REF=$(get ref ${INSTALL_REF})
for i in $(seq 1 120); do curl -fsI --max-time 10 https://codeload.github.com >/dev/null && break; echo "venter på nett ($i)"; sleep 5; done
D=/opt/skjold/src
rm -rf "$D" && mkdir -p "$D"
curl -fsSL --retry 5 "https://codeload.github.com/${REPO}/tar.gz/$REF" | tar xz -C "$D" --strip-components=1 || { echo "nedlasting feilet"; exit 1; }
export DEBIAN_FRONTEND=noninteractive
cd "$D/pi"
if [ "$DEVICE" = s1 ]; then
  KI_AMP_BOARD=main bash ./install.sh || { echo "install.sh feilet"; exit 1; }
elif [ "$DEVICE" = core ]; then
  KI_AMP_CORE=1 KI_AMP_NAME="$(get name "")" bash ./install.sh || { echo "install.sh feilet"; exit 1; }
else
  KI_AMP_BOARD=node KI_AMP_OUT=headphones KI_AMP_NAME="$(get name "")" bash ./install.sh || { echo "install.sh feilet"; exit 1; }
  bash "$D/skjold/node/driver/installer_node.sh" || echo "ADVARSEL: installer_node.sh feilet"
fi
if [ "$(get lyrion_server False)" = True ]; then
  bash "$D/pi/install_lyrion.sh" || echo "ADVARSEL: Lyrion Music Server ble ikke installert"
fi
touch /var/lib/skjold-installed
systemctl disable skjold-install.service
echo "=== $(date -Is) ferdig – starter på nytt"
systemctl reboot
`;
}

const INSTALL_UNIT = `[Unit]
Description=Skjold – installasjon ved første oppstart
Wants=network-online.target
After=network-online.target time-sync.target
ConditionPathExists=!/var/lib/skjold-installed

[Service]
Type=oneshot
ExecStart=/bin/bash /usr/local/sbin/skjold-install.sh
Restart=on-failure
RestartSec=60
TimeoutStartSec=infinity

[Install]
WantedBy=multi-user.target
`;

/** Felles skallkommandoer som legger inn installasjonstjenesten (brukes av firstrun.sh og cloud-init runcmd). */
function installSetupCmds(boot: string): string[] {
  return [
    `install -m 755 ${boot}/skjold-install.sh /usr/local/sbin/skjold-install.sh`,
    `printf '%s' ${sq(INSTALL_UNIT)} > /etc/systemd/system/skjold-install.service`,
    'systemctl enable skjold-install.service',
  ];
}

function setupJson(o: SetupOptions): string {
  const setup: Record<string, unknown> = { version: 1, device: o.device, hostname: o.hostname, lang: o.lang, ref: INSTALL_REF, lyrion_server: !!o.lyrionServer };
  if (o.preset) {
    setup.name = o.name.trim();
    const st = staticOf(o);
    setup.net = isEth(o) ? 'eth' : 'wifi';
    setup.ssid = isWifi(o) ? o.ssid : '';
    setup.psk = isWifi(o) ? o.wifiPassword : '';
    setup.static = st ? { ip: cidrString(st.ip), gw: st.gw.trim(), dns: dnsList(st.dns).join(',') } : null;
    if (isWifi(o)) setup.wifi = { ssid: o.ssid, password: o.wifiPassword, country: o.country }; // eldre skjold-setup
  }
  return JSON.stringify(setup, null, 2) + '\n';
}

function cidrString(ip: string): string {
  const c = parseCidr(ip)!;
  return `${c.ip}/${c.prefix}`;
}
function staticDns(st: StaticIp): string[] {
  const d = dnsList(st.dns);
  return d.length ? d : st.gw.trim() ? [st.gw.trim()] : [];
}

/** NetworkManager-keyfile for kablet nett med fast IPv4 (systemd/firstrun-modus). */
export function ethKeyfile(st: StaticIp): string {
  const gw = st.gw.trim();
  const dns = staticDns(st);
  return ['[connection]', 'id=skjold-eth', 'type=ethernet', 'interface-name=eth0', 'autoconnect=true', 'autoconnect-priority=10', '',
    '[ethernet]', '', '[ipv4]', 'method=manual', `address1=${cidrString(st.ip)}${gw ? ',' + gw : ''}`,
    ...(dns.length ? [`dns=${dns.join(';')};`] : []), '', '[ipv6]', 'method=auto', ''].join('\n');
}

/** cloud-init network-config (v2) for kablet nett: fast IP eller DHCP. */
export function ethNetworkConfig(st: StaticIp | null): string {
  const L = ['# Skrevet av Skjold Flasher', 'network:', '  version: 2', '  renderer: NetworkManager', '  ethernets:', '    eth0:'];
  if (!st) L.push('      dhcp4: true', '      optional: true');
  else {
    L.push('      dhcp4: false', '      optional: true', '      addresses:', `        - ${yq(cidrString(st.ip))}`);
    if (st.gw.trim()) L.push('      routes:', '        - to: default', `          via: ${yq(st.gw.trim())}`);
    const dns = staticDns(st);
    if (dns.length) L.push('      nameservers:', '        addresses:', ...dns.map(d => `          - ${yq(d)}`));
  }
  return L.join('\n') + '\n';
}

/** Brukerens passord-hash. Uten SSH-passord lages en låst bruker (ingen innlogging med passord). */
function userHash(o: SetupOptions, salt?: string): string | null {
  return o.ssh && o.userPassword ? sha512crypt(o.userPassword, salt) : null;
}
const userName = (o: SetupOptions) => (o.ssh ? o.user : 'skjold');

function firstrun(o: SetupOptions, salt?: string): string {
  const loc = LANG_LOCALE[o.lang];
  const u = userName(o);
  const hash = userHash(o, salt) ?? '!';
  const L: string[] = [
    '#!/bin/bash',
    '# Skrevet av Skjold Flasher – kjøres én gang ved første oppstart (systemd.run i cmdline.txt), sletter seg selv.',
    'set +e',
    'B=/boot/firmware; [ -f $B/cmdline.txt ] || B=/boot',
    `HN=${sq(o.hostname)}`,
    'CUR=$(tr -d " \\t\\n\\r" </etc/hostname)',
    'echo "$HN" >/etc/hostname',
    'sed -i "s/127.0.1.1.*$CUR/127.0.1.1\\t$HN/g" /etc/hosts',
    `U=${sq(u)}; HASH=${sq(hash)}`,
    'if [ -x /usr/lib/userconf-pi/userconf ]; then /usr/lib/userconf-pi/userconf "$U" "$HASH"',
    'else',
    '  OLD=$(getent passwd 1000 | cut -d: -f1)',
    '  if [ -n "$OLD" ] && [ "$OLD" != "$U" ]; then usermod -l "$U" -d "/home/$U" -m "$OLD"; groupmod -n "$U" "$OLD"; fi',
    '  id "$U" >/dev/null 2>&1 || useradd -m -s /bin/bash -G sudo,audio,video,gpio,spi,i2c,netdev,plugdev "$U"',
    '  echo "$U:$HASH" | chpasswd -e',
    'fi',
    'systemctl disable userconfig.service 2>/dev/null; rm -f /etc/ssh/sshd_config.d/rename_user.conf',
  ];
  if (o.ssh) {
    L.push('systemctl enable ssh');
    if (o.sshKey.trim()) L.push(
      'H=$(getent passwd "$U" | cut -d: -f6)', 'install -d -m 700 -o "$U" -g "$U" "$H/.ssh"',
      `echo ${sq(o.sshKey.trim())} >"$H/.ssh/authorized_keys"`, 'chown "$U:$U" "$H/.ssh/authorized_keys"; chmod 600 "$H/.ssh/authorized_keys"');
    if (!o.userPassword) L.push("printf 'PasswordAuthentication no\\n' >/etc/ssh/sshd_config.d/skjold.conf");
  }
  const st = staticOf(o);
  if (st) L.push(
    'install -d /etc/NetworkManager/system-connections',
    `printf '%s' ${sq(ethKeyfile(st))} >/etc/NetworkManager/system-connections/skjold-eth.nmconnection`,
    'chmod 600 /etc/NetworkManager/system-connections/skjold-eth.nmconnection');
  if (isWifi(o)) {
    const ssidBytes = [...Buffer.from(o.ssid, 'utf8')].join(';') + ';';
    const conn = ['[connection]', 'id=skjold-wifi', 'type=wifi', 'autoconnect=true', '', '[wifi]', 'mode=infrastructure', `ssid=${ssidBytes}`, '',
      '[wifi-security]', 'key-mgmt=wpa-psk', `psk=${wpaPsk(o.ssid, o.wifiPassword)}`, '', '[ipv4]', 'method=auto', '', '[ipv6]', 'method=auto', ''].join('\n');
    L.push(
      'install -d /etc/NetworkManager/system-connections',
      `printf '%s' ${sq(conn)} >/etc/NetworkManager/system-connections/skjold-wifi.nmconnection`,
      'chmod 600 /etc/NetworkManager/system-connections/skjold-wifi.nmconnection',
      `command -v raspi-config >/dev/null && raspi-config nonint do_wifi_country ${sq(o.country)}`,
      'rfkill unblock wifi 2>/dev/null; for f in /var/lib/systemd/rfkill/*:wlan; do [ -f "$f" ] && echo 0 >"$f"; done');
  }
  L.push(
    `ln -sf ${sq('/usr/share/zoneinfo/' + loc.timezone)} /etc/localtime; echo ${sq(loc.timezone)} >/etc/timezone`,
    `sed -i 's/^XKBLAYOUT=.*/XKBLAYOUT="${loc.keymap}"/' /etc/default/keyboard 2>/dev/null`,
    ...installSetupCmds('$B'),
    'rm -f $B/firstrun.sh',
    "sed -i 's| systemd.run.*||g' $B/cmdline.txt",
    'exit 0', '');
  return L.join('\n');
}

function cloudInit(o: SetupOptions, salt?: string): BootFile[] {
  const loc = LANG_LOCALE[o.lang];
  const hash = userHash(o, salt);
  const ud: string[] = [
    '#cloud-config', '# Skrevet av Skjold Flasher',
    `hostname: ${yq(o.hostname)}`, 'manage_etc_hosts: true',
    `timezone: ${yq(loc.timezone)}`,
    'keyboard:', `  layout: ${yq(loc.keymap)}`,
    'users:',
    `  - name: ${yq(userName(o))}`,
    '    groups: users,adm,dialout,audio,netdev,video,plugdev,input,gpio,spi,i2c,render,sudo',
    '    shell: /bin/bash',
    "    sudo: 'ALL=(ALL) NOPASSWD:ALL'",
    `    lock_passwd: ${hash ? 'false' : 'true'}`,
  ];
  if (hash) ud.push(`    passwd: ${yq(hash)}`);
  if (o.ssh && o.sshKey.trim()) ud.push('    ssh_authorized_keys:', `      - ${yq(o.sshKey.trim())}`);
  ud.push(`ssh_pwauth: ${o.ssh && hash ? 'true' : 'false'}`);
  ud.push('runcmd:');
  const cmds = [...(o.ssh ? ['systemctl enable --now ssh'] : []), 'rfkill unblock wifi || true', ...installSetupCmds('/boot/firmware'),
    'systemctl start --no-block skjold-install.service'];
  for (const c of cmds) ud.push(`  - ${yq(c)}`);
  const files: BootFile[] = [{ name: 'user-data', content: ud.join('\n') + '\n' }];
  if (isEth(o)) files.push({ name: 'network-config', content: ethNetworkConfig(staticOf(o)) });
  else if (o.preset) {
    files.push({ name: 'network-config', content: [
      '# Skrevet av Skjold Flasher', 'network:', '  version: 2', '  wifis:', '    renderer: NetworkManager', '    wlan0:',
      '      dhcp4: true', `      regulatory-domain: ${yq(o.country)}`, '      optional: true', '      access-points:',
      `        ${yq(o.ssid)}:`, `          password: ${yq(wpaPsk(o.ssid, o.wifiPassword))}`, ''].join('\n') });
  }
  return files;
}

export function buildBootFiles(o: SetupOptions, mode: InitMode, salt?: string): BootFile[] {
  const files: BootFile[] = [{ name: 'skjold-setup.json', content: setupJson(o) }];
  if (mode === 'skjold') return files;
  files.push({ name: 'skjold-install.sh', content: installScript() });
  if (mode === 'cloudinit') files.push(...cloudInit(o, salt));
  else files.push({ name: 'firstrun.sh', content: firstrun(o, salt) });
  return files;
}

/** Ny cmdline.txt i systemd-modus: én linje, regdom før systemd.run (som firstrun.sh kutter bort). */
export function patchCmdline(cmdline: string, o: SetupOptions): string {
  let c = cmdline.replace(/\r?\n/g, ' ').trim().replace(/ systemd\.run.*$/, '').replace(/ cfg80211\.ieee80211_regdom=\S+/, '');
  if (isWifi(o)) c += ` cfg80211.ieee80211_regdom=${o.country}`;
  return c + FIRSTRUN_CMDLINE + '\n';
}

/**
 * Pi 3B kan ikke starte fra USB før OTP-biten er satt. Et SD-kort for Pi 3 (Node Pi 3B / Core) får derfor
 * `program_usb_boot_mode=1` under [pi3] i config.txt: første oppstart fra kortet slår på USB-oppstart for godt.
 * Pi 3B+ har biten satt fra fabrikk, og [pi3]-filteret gjør at Pi 4 ignorerer linja.
 */
export function needsUsbBootOtp(o: SetupOptions): boolean {
  return (o.device === 'node-pi3' || o.device === 'core') && o.media !== 'usb';
}
export function patchConfigTxt(cfg: string, o: SetupOptions): string {
  if (!needsUsbBootOtp(o) || /^\s*program_usb_boot_mode\s*=\s*1/m.test(cfg)) return cfg;
  return cfg.replace(/\s*$/, '\n') + '\n# Skjold Flasher: slår på USB-oppstart på Pi 3B (engangs OTP-bit)\n[pi3]\nprogram_usb_boot_mode=1\n[all]\n';
}
