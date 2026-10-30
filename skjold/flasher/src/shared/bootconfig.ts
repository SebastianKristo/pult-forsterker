/**
 * Filer som legges på boot-partisjonen (FAT, /boot/firmware på Bookworm) før første oppstart.
 *
 *  - skjold-setup.json  leses av skjold-setup (design/sdbilde: Wi-Fi, navn, språk; slettes etter bruk)
 *  - custom.toml        Raspberry Pi OS Bookworm (raspberrypi-sys-mods init_config, samme format som
 *                       Raspberry Pi Imager): hostname, bruker, SSH, Wi-Fi, locale
 *  - ssh / userconf.txt eldre mekanisme (Bullseye/tidlig Bookworm) – aktiverer SSH og lager bruker
 */
import type { SetupOptions } from './types';
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

export function validate(o: SetupOptions): string | null {
  if (!isValidHostname(o.hostname)) return 'Ugyldig vertsnavn (bare a–z, 0–9 og bindestrek).';
  if (o.preset) {
    if (!o.ssid.trim() || Buffer.byteLength(o.ssid, 'utf8') > 32) return 'Wi-Fi-navnet må være 1–32 byte.';
    if (o.wifiPassword.length < 8 || o.wifiPassword.length > 63) return 'Wi-Fi-passordet må være 8–63 tegn.';
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

const tomlStr = (s: string) => JSON.stringify(s); // TOML basic string godtar JSON-escaping

export interface BootFile { name: string; content: string }

export function buildBootFiles(o: SetupOptions, salt?: string): BootFile[] {
  const files: BootFile[] = [];
  const loc = LANG_LOCALE[o.lang];

  const setup: Record<string, unknown> = { version: 1, device: o.device, hostname: o.hostname, lang: o.lang };
  if (o.preset) {
    setup.name = o.name.trim();
    setup.wifi = { ssid: o.ssid, password: o.wifiPassword, country: o.country };
  }
  files.push({ name: 'skjold-setup.json', content: JSON.stringify(setup, null, 2) + '\n' });

  const t: string[] = ['# Skrevet av Skjold Flasher', 'config_version = 1', '', '[system]', `hostname = ${tomlStr(o.hostname)}`, ''];
  const hash = o.ssh && o.userPassword ? sha512crypt(o.userPassword, salt) : null;
  if (o.ssh) {
    t.push('[user]', `name = ${tomlStr(o.user)}`);
    if (hash) t.push(`password = ${tomlStr(hash)}`, 'password_encrypted = true');
    t.push('');
    t.push('[ssh]', 'enabled = true', `password_authentication = ${hash ? 'true' : 'false'}`);
    if (o.sshKey.trim()) t.push(`authorized_keys = [ ${tomlStr(o.sshKey.trim())} ]`);
    t.push('');
  }
  if (o.preset) {
    t.push('[wlan]', `ssid = ${tomlStr(o.ssid)}`, `password = ${tomlStr(o.wifiPassword)}`, 'password_encrypted = false',
      'hidden = false', `country = ${tomlStr(o.country)}`, '');
  }
  t.push('[locale]', `keymap = ${tomlStr(loc.keymap)}`, `timezone = ${tomlStr(loc.timezone)}`, '');
  files.push({ name: 'custom.toml', content: t.join('\n') });

  if (o.ssh) {
    files.push({ name: 'ssh', content: '' });
    if (hash) files.push({ name: 'userconf.txt', content: `${o.user}:${hash}\n` });
  }
  return files;
}
