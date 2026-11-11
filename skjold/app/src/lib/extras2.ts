// Smart radio, Oppdag uke, tilstede-modus, vekkelys, spillelister fra radio, plugin-butikk og helsesjekk.
import { credFor, getBase, isRelayBase } from './api';

async function call<T>(path: string, body?: unknown, timeoutMs = 15000): Promise<T> {
  const base = getBase();
  const ctl = new AbortController();
  const t = window.setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const init: RequestInit = { cache: 'no-store', signal: ctl.signal, ...(isRelayBase(base) ? { credentials: credFor(base) } : {}) };
    if (body !== undefined) {
      if (body instanceof FormData) Object.assign(init, { method: 'POST', body });
      else Object.assign(init, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    }
    const r = await fetch(base + path, init);
    const j = (await r.json().catch(() => { if (r.ok) throw new Error('Uventet svar fra Skjold'); return {}; })) as T & { error?: string };
    if (!r.ok) throw new Error(j.error || 'HTTP ' + r.status);
    return j;
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw new Error('Tidsavbrudd');
    throw e;
  } finally { clearTimeout(t); }
}
export const fileUrl = (path: string) => getBase() + path;

export interface SrTrack { id: string; title: string; artist: string; album?: string; src: string; uri?: string }
export interface SmartRadio { active: boolean; label: string; seed: Record<string, string> | null; current: SrTrack | null; next: SrTrack[]; error: string | null }
export interface SrSeed { source?: 'navidrome' | 'ma'; id?: string; uri?: string; title?: string; artist?: string; genre?: string }

export interface DiscoverCfg { enabled: boolean; day: number; time: string; size: number; weeks: number; archive: boolean; sources: string[] }
export interface DiscoverList { name: string; week: number; t: number; tracks: SrTrack[]; navidrome: string | boolean | null; saved?: boolean }
export interface Discover { cfg: DiscoverCfg; current: DiscoverList | null; busy: boolean; error: string | null }

export interface Presence { enabled: boolean; status: string; plan: { start: string; end: string; room: string }[]; now: string }
export interface RadioList { name: string | null; found: number; missing: number; missingList: { title: string; artist: string }[] }

export interface StoreSetting { type?: 'string' | 'number' | 'select' | 'time' | 'password' | 'boolean'; navn?: string; default?: unknown; valg?: string[]; min?: number; max?: number }
export interface StorePlugin {
  id: string; navn: string; versjon: string; forfatter: string; beskrivelse: string; ikon?: string; kategori?: string; minSkjold?: string;
  tillatelser?: string[]; settings?: Record<string, StoreSetting>; settingsValues?: Record<string, unknown>; enabled?: boolean; error?: string;
  installed?: string | null; update?: boolean; compatible?: boolean; events?: string[];
}

export type Level = 'ok' | 'advarsel' | 'feil';
export interface HealthItem { key: string; navn: string; verdi: unknown; niva: Level; forklaring: string }
export interface Health { niva: Level; items: HealthItem[]; uptime: number; errors: string[]; aplay: string; version: string; update: Record<string, unknown> }

export const x2 = {
  smartradio: () => call<SmartRadio>('/api/smartradio'),
  smartradioStart: (seed: SrSeed) => call<SmartRadio>('/api/smartradio', { seed }),
  smartradioStop: () => call<SmartRadio>('/api/smartradio', { stop: true }),
  smartradioSkip: () => call<SmartRadio>('/api/smartradio', { skip: true }),
  discover: () => call<Discover>('/api/discover'),
  discoverPost: (b: { cfg?: Partial<DiscoverCfg>; build?: boolean; play?: boolean; shuffle?: boolean; save?: boolean }) => call<Discover>('/api/discover', b, 180000),
  presence: () => call<Presence>('/api/presence'),
  presenceSet: (on: boolean) => call<Presence>('/api/presence', { on }),
  wakeLight: () => call<{ active: boolean; last: string }>('/api/wakelight'),
  wakeLightStop: () => call<{ active: boolean; last: string }>('/api/wakelight', { stop: true }),
  radioList: () => call<RadioList>('/api/radiolist'),
  radioListBuild: (b: { source: 'recordings' | 'wishlist'; channel?: string; name?: string }) => call<RadioList>('/api/radiolist', b, 180000),
  store: () => call<{ installed: StorePlugin[]; dir: string }>('/api/store'),
  storeCatalog: () => call<{ plugins: StorePlugin[]; error?: string }>('/api/store/catalog'),
  storePost: (b: Record<string, unknown>) => call<{ ok?: boolean; installed?: string; error?: string; actions?: unknown[]; result?: unknown }>('/api/store', b, 60000),
  storeUpload: (f: File, sha256 = '') => { const fd = new FormData(); fd.append('file', f); if (sha256) fd.append('sha256', sha256); return call<{ ok: boolean; installed: string }>('/api/store', fd, 60000); },
  health: () => call<Health>('/api/health', undefined, 20000),
  perf: () => call<Perf>('/api/health/perf', undefined, 10000),
  healthReport: () => call<{ text: string; issue: string }>('/api/health/report?format=json', undefined, 20000),
};

export interface Perf {
  cpu_pct: number | null; cpus: number; load: number[] | null; temp_c: number | null; model: string | null; uptime_s: number | null;
  memory: { total_mb: number; used_mb: number; pct: number } | null; disk: { free_gb: number; total_gb: number; pct: number } | null;
  throttle: { under_voltage: boolean; freq_capped: boolean; throttled: boolean; under_voltage_occurred: boolean; power_problem: boolean } | null;
  services: Record<string, { cpu_pct: number | null; mem_mb: number | null }>;
}
