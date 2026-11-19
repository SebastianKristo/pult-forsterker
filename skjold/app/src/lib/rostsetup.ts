// Oppsett av en ny Skjold Røst fra appen: snakker med squeezelite-esp32 sitt oppsett-API på 192.168.4.1 over
// SkjoldWifi-plugin-en. API-et er lest i kildekoden til squeezelite-esp32 (tag S3-i2s.16.1779.master-v4.3,
// components/wifi-manager/http_server_handlers.c, network_status.c, webapp/src/js/custom.js):
//   GET  /status.json   {urc, ssid, ip, recovery, version, …}  urc 0 = tilkoblet, 1 = mislyktes, 4 = mislyktes (gammelt nett beholdt)
//   GET  /scan.json     starter et søk (svarer {}), GET /ap.json ~2 s senere: [{ssid, rssi, auth, chan, known, …}]
//   GET  /config.json   {gpio: […], config: {nøkkel: {value, type}}}   type 33 = streng (NVS_TYPE_STR)
//   POST /config.json   {timestamp, config: {nøkkel: {value, type: 33}}}
//   POST /connect.json  {timestamp, ssid, pwd, host_name?}  – «pwd» må alltid være med (fastvaren gjør strlen på den)
//   POST /reboot_ota.json  start squeezelite (fra recovery) / vanlig omstart (fra squeezelite). Venter på NVS-lagring.
import { SkjoldWifi } from './skjoldwifi';

export const ROST_AP = { ssid: 'Skjold-Rost', password: 'squeezelite', ip: '192.168.4.1' } as const;
export const ROST_PREFIX = 'Skjold-Rost-';
const BASE = 'http://' + ROST_AP.ip;

export interface RostStatus { urc?: number; ssid?: string; ip?: string; recovery?: number; version?: string; project_name?: string }
export interface RostNet { ssid: string; signal: number; open: boolean }

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

async function call<T>(path: string, method: 'GET' | 'POST' = 'GET', body?: unknown, timeoutMs = 6000): Promise<T> {
  const r = await SkjoldWifi.request({
    url: BASE + path, method, timeoutMs,
    ...(body !== undefined ? { body: JSON.stringify(body), headers: { 'Content-Type': 'application/json; charset=utf-8' } } : {})
  });
  if (r.status < 200 || r.status >= 300) throw new Error('Røst svarte ' + r.status + (r.data ? ': ' + r.data.slice(0, 120) : ''));
  try { return (r.data ? JSON.parse(r.data) : {}) as T; } catch { return {} as T; }
}

export const rostStatus = () => call<RostStatus>('/status.json', 'GET', undefined, 4000);

/** Vent til oppsettsiden svarer (telefonen har nettopp koblet til, DHCP kan bruke et par sekunder). */
export async function waitForRost(ms = 15000): Promise<RostStatus> {
  const t0 = Date.now();
  let last: unknown;
  while (Date.now() - t0 < ms) {
    try { return await rostStatus(); } catch (e) { last = e; await sleep(1200); }
  }
  throw last instanceof Error ? last : new Error('Røst svarer ikke på ' + ROST_AP.ip);
}

/** RSSI (dBm) → 0–100 %. */
const pct = (rssi: number) => Math.max(0, Math.min(100, 2 * (rssi + 100)));

/** Nettene Røst ser (sterkest først, uten tomme navn og uten sitt eget oppsettnett). */
export async function rostScan(): Promise<RostNet[]> {
  try { await call('/scan.json'); } catch { /* eldre liste fra oppstarten er bedre enn ingen */ }
  await sleep(2500);
  const list = await call<{ ssid?: string; rssi?: number; auth?: number }[]>('/ap.json').catch(() => []);
  const best = new Map<string, RostNet>();
  for (const a of Array.isArray(list) ? list : []) {
    const ssid = String(a.ssid ?? '');
    if (!ssid || ssid === ROST_AP.ssid) continue;
    const n = { ssid, signal: pct(Number(a.rssi ?? -100)), open: Number(a.auth ?? 1) === 0 };
    const o = best.get(ssid);
    if (!o || o.signal < n.signal) best.set(ssid, n);
  }
  return [...best.values()].sort((a, b) => b.signal - a.signal);
}

/** «Bad» → «Skjold-Rost-Bad», «Kjøkken» → «Skjold-Rost-Kjokken». Bare A–Z, 0–9 og bindestrek (vertsnavn og squeezelite -n). */
export function rostName(room: string): string {
  const ascii = room.trim()
    .replace(/[Ææ]/g, (c) => (c === 'Æ' ? 'Ae' : 'ae')).replace(/[Øø]/g, (c) => (c === 'Ø' ? 'O' : 'o')).replace(/[Åå]/g, (c) => (c === 'Å' ? 'A' : 'a'))
    .normalize('NFKD').replace(/[̀-ͯ]/g, '')
    .replace(/[^A-Za-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 20);
  return ROST_PREFIX + (ascii || 'Rom');
}

/** Bytt bare -n i squeezelite-kommandolinjen (resten av Skjold-oppsettet i autoexec1 beholdes). */
export function withPlayerName(autoexec: string, name: string): string {
  const cmd = autoexec.trim() || 'squeezelite -o I2S -b 500:2000 -C 30 -W';
  const re = /(^|\s)-n\s+("[^"]*"|\S+)/;
  return re.test(cmd) ? cmd.replace(re, `$1-n ${name}`) : `${cmd} -n ${name}`;
}

type Cfg = Record<string, { value?: unknown; type?: number }>;

/** Navn: host_name, spillernavnet (-n i autoexec1), AirPlay- og Spotify-navn. Leser gjeldende verdier først. */
export async function rostSetName(name: string): Promise<void> {
  const got = await call<{ config?: Cfg } & Cfg>('/config.json', 'GET', undefined, 8000);
  const cfg: Cfg = got.config ?? got;
  const str = (k: string) => (typeof cfg[k]?.value === 'string' ? (cfg[k]!.value as string) : '');
  const out: Record<string, { value: string; type: 33 }> = {
    host_name: { value: name, type: 33 },
    autoexec1: { value: withPlayerName(str('autoexec1'), name), type: 33 }
  };
  if (cfg['airplay_name']) out['airplay_name'] = { value: name, type: 33 };
  const cspot = str('cspot_config');
  if (cspot) {
    try { const j = JSON.parse(cspot) as Record<string, unknown>; j['deviceName'] = name; out['cspot_config'] = { value: JSON.stringify(j), type: 33 }; } catch { /* la være */ }
  }
  await call('/config.json', 'POST', { timestamp: Date.now(), config: out }, 8000);
}

export async function rostConnect(ssid: string, pwd: string, hostName: string): Promise<void> {
  await call('/connect.json', 'POST', { timestamp: Date.now(), ssid, pwd, host_name: hostName }, 8000);
}

export type JoinResult = { ok: true; ip: string } | { ok: false; why: 'password' | 'lost' | 'timeout' };

/**
 * Følg med i /status.json til Røst er på hjemmenettet (urc 0 og riktig ssid) eller har gitt opp (urc 1/4).
 * Røst kan bytte radiokanal når den kobler til ruteren, så telefonen kan miste oppsettnettet et øyeblikk: feil i
 * kallene tåles hele veien. Gammel urc 1 fra et tidligere forsøk teller ikke de første sekundene.
 */
export async function rostWaitJoin(ssid: string, ms = 45000): Promise<JoinResult> {
  const t0 = Date.now();
  let answered = false;
  while (Date.now() - t0 < ms) {
    await sleep(2000);
    try {
      const s = await rostStatus();
      answered = true;
      if (s.urc === 0 && s.ssid === ssid && s.ip && s.ip !== '0.0.0.0') return { ok: true, ip: s.ip };
      if ((s.urc === 1 || s.urc === 4) && Date.now() - t0 > 12000) return { ok: false, why: 'password' };
    } catch { /* oppsettnettet borte et øyeblikk */ }
  }
  return { ok: false, why: answered ? 'timeout' : 'lost' };
}

/** Start squeezelite (Røst står i «recovery» uten Wi-Fi). Prøver oppsettnettet, så hjemmenettet når vi vet IP-en. */
export async function rostReboot(): Promise<boolean> {
  try { await call('/reboot_ota.json', 'POST', { timestamp: Date.now() }, 5000); return true; } catch { return false; }
}

/** Samme over hjemmenettet (etter at telefonen er tilbake): http://<ip>/reboot_ota.json. */
export async function rostRebootHome(ip: string): Promise<boolean> {
  try {
    const r = await fetch(`http://${ip}/reboot_ota.json`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ timestamp: Date.now() }) });
    return r.ok;
  } catch { return false; }
}
