// HTTP-klient mot ki_amp_daemon.py (port 8765). Samme origin på web, konfigurerbar vert i appen.
import { Capacitor } from '@capacitor/core';

export type InputId = 'radio' | 'airplay' | 'bt' | 'aux' | 'aux2' | 'usb';
export const INPUT_LABEL: Record<InputId, string> = { radio: 'Radio', airplay: 'AirPlay', bt: 'Blåtann', aux: 'AUX 1', aux2: 'AUX 2', usb: 'USB' };
export type LevelSource = 'airplay' | 'bt' | 'usb' | 'radio' | 'aux' | 'aux2';

export interface Preset { n: number; title: string }
export interface FullPreset { title: string; url: string; icon?: string }

export interface Status {
  power: boolean; input: InputId; volume: number; mute: boolean; bt_pairing: boolean;
  loudness: boolean; loudness_level: number; voice: boolean; voice_profile: string; voice_profiles: Record<string, string>;
  presets: Preset[]; preset: number; auto_input: boolean; mix: boolean; usb_pc: number; usb_names: string[];
  headphones: boolean; hp_automute: boolean; overtemp: boolean; levels: Record<string, number>;
  playing: boolean; paused: boolean; source: string; cover: string; title: string; artist: string; album: string;
  duration: number; position: number; bt_device: string; name: string; version: string; id: string;
  inputs: InputId[]; board: string; lyrion: boolean; station: string;
}

export const isNative = Capacitor.isNativePlatform();
const HOST_KEY = 'skjold-host';
export const CANDIDATE_HOSTS = ['http://skjold.local:8765', 'http://pultamp.local:8765'];

/** Base URL for the API. Web build: same origin (''), unless ?host= or a stored host is set. App: stored host. */
export function getBase(): string {
  try {
    const q = new URLSearchParams(location.search).get('host');
    if (q) { const u = normHost(q); localStorage.setItem(HOST_KEY, u); return u; }
    const s = localStorage.getItem(HOST_KEY);
    if (s) return s;
  } catch { /* storage blocked */ }
  return isNative || location.protocol === 'file:' ? '' : '';
}
export function needsHost(): boolean {
  return (isNative || location.protocol === 'file:') && !getBase();
}
export function setBase(url: string | null): void {
  try { if (url) localStorage.setItem(HOST_KEY, normHost(url)); else localStorage.removeItem(HOST_KEY); } catch { /* ignore */ }
}
export function normHost(h: string): string {
  let u = h.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(u)) u = 'http://' + u;
  if (!/:\d+$/.test(u.replace(/^https?:\/\//i, ''))) u += ':8765';
  return u;
}
export function hostLabel(): string {
  const b = getBase();
  if (b) return b.replace(/^https?:\/\//i, '');
  return location.host || 'skjold.local';
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function req<T>(path: string, init?: RequestInit, base = getBase(), timeoutMs = 6000): Promise<T> {
  const ctl = new AbortController();
  const t = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(base + path, { cache: 'no-store', ...init, signal: ctl.signal });
    if (!r.ok) {
      let msg = r.statusText;
      try { const j = (await r.json()) as { error?: string }; if (j.error) msg = j.error; } catch { /* no body */ }
      throw new ApiError(r.status, msg || 'HTTP ' + r.status);
    }
    return (await r.json()) as T;
  } finally { clearTimeout(t); }
}
const post = <T = Status>(path: string, body: unknown) => req<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });

export const api = {
  status: () => req<Status>('/api/status'),
  statusAt: (base: string, timeoutMs = 2500) => req<Status>('/api/status', undefined, base, timeoutMs),
  power: (on: boolean) => post('/api/power', { on }),
  toggle: () => post('/api/toggle', {}),
  input: (input: InputId) => post('/api/input', { input }),
  volume: (volume: number) => post('/api/volume', { volume }),
  volumeDelta: (delta: number) => post('/api/volume', { delta }),
  mute: (mute: boolean) => post('/api/mute', { mute }),
  btPairing: () => post('/api/bt', { pairing: true }),
  loudness: (on?: boolean, level?: number) => post('/api/loudness', { ...(on !== undefined ? { on } : {}), ...(level !== undefined ? { level } : {}) }),
  transport: (action: 'play' | 'pause' | 'playpause' | 'next' | 'previous' | 'stop') => post('/api/transport', { action }),
  voice: (b: { on?: boolean; profile?: string; say?: string }) => post('/api/voice', b),
  presets: () => req<{ presets: (FullPreset | null)[]; active: number; lyrion: boolean }>('/api/presets'),
  playPreset: (n: number) => post('/api/preset', { n }),
  savePreset: (n: number) => post('/api/preset', { n, save: true }),
  setPresets: (presets: (FullPreset | null)[]) => post<{ presets: (FullPreset | null)[]; active: number }>('/api/presets', { presets }),
  importPresets: () => post<{ presets: (FullPreset | null)[]; active: number }>('/api/presets', { import: true }),
  autoInput: (on: boolean) => post('/api/auto_input', { on }),
  mix: (on: boolean) => post('/api/mix', { on }),
  usbsw: (pc: 1 | 2) => post('/api/usbsw', { pc }),
  level: (source: LevelSource, level: number) => post('/api/level', { source, level }),
  hpAutomute: (on: boolean) => post('/api/hp_automute', { on }),
  // Nytt endepunkt (legges til i daemonen): GET/POST /api/settings
  getSettings: () => req<{ settings: Record<string, unknown>; applied?: string[]; schema_version: number }>('/api/settings'),
  setSettings: (patch: Record<string, unknown>) => post<{ settings: Record<string, unknown>; applied?: string[]; schema_version: number }>('/api/settings', patch),
  // Endepunkt som ennå ikke finnes i daemonen – brukes av oppsettet og svarer 404 i dag
  wifiScan: () => req<{ networks: { ssid: string; security?: string; signal?: number }[] }>('/api/wifi', undefined, getBase(), 8000),
  wifiConnect: (ssid: string, psk: string) => post<{ ok: boolean }>('/api/wifi', { ssid, psk }),
  speakerTest: (channel: 'L' | 'R') => post<{ ok: boolean }>('/api/test', { channel }),
  reboot: () => post<{ ok: boolean }>('/api/reboot', {}),
  factoryReset: () => post<{ ok: boolean }>('/api/reset', {}),
  forgetBt: () => post<{ ok: boolean }>('/api/bt', { forget: true })
};

export function coverUrl(st: Status | null): string | null {
  if (!st || !st.cover) return null;
  return getBase() + '/api/cover?v=' + encodeURIComponent(st.cover);
}

export interface Release { tag: string; name: string; date: string; notes: string[]; url: string; prerelease: boolean; size: string }
export const REPO = 'SebastianKristo/pult-forsterker';

export async function fetchLatestRelease(includePre: boolean): Promise<Release | null> {
  const url = includePre ? `https://api.github.com/repos/${REPO}/releases?per_page=5` : `https://api.github.com/repos/${REPO}/releases/latest`;
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 8000);
  try {
    const r = await fetch(url, { headers: { Accept: 'application/vnd.github+json' }, signal: ctl.signal });
    if (r.status === 404) return null;
    if (!r.ok) throw new ApiError(r.status, 'GitHub svarte ' + r.status);
    const j = (await r.json()) as unknown;
    const rel = (Array.isArray(j) ? j.find((x) => !(x as { draft?: boolean }).draft) : j) as Record<string, unknown> | undefined;
    if (!rel || !rel['tag_name']) return null;
    const assets = (rel['assets'] as { size?: number }[] | undefined) ?? [];
    const bytes = assets.reduce((a, x) => a + (x.size ?? 0), 0);
    const body = String(rel['body'] ?? '');
    const notes = body.split(/\r?\n/).map((l) => l.replace(/^[-*•]\s*/, '').trim()).filter((l) => l && !l.startsWith('#')).slice(0, 6);
    return {
      tag: String(rel['tag_name']), name: String(rel['name'] || rel['tag_name']),
      date: String(rel['published_at'] ?? '').slice(0, 10), notes, url: String(rel['html_url'] ?? `https://github.com/${REPO}/releases`),
      prerelease: !!rel['prerelease'], size: bytes ? (bytes / 1048576).toFixed(1).replace('.', ',') + ' MB' : ''
    };
  } finally { clearTimeout(t); }
}

/** Sammenlign "v1.2.3" / "2.0" – returnerer >0 hvis a er nyere enn b. */
export function cmpVersion(a: string, b: string): number {
  const pa = a.replace(/^v/i, '').split(/[.-]/).map((x) => parseInt(x, 10)), pb = b.replace(/^v/i, '').split(/[.-]/).map((x) => parseInt(x, 10));
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    const x = pa[i] ?? 0, y = pb[i] ?? 0;
    if (Number.isNaN(x) || Number.isNaN(y)) continue;
    if (x !== y) return x - y;
  }
  return 0;
}
