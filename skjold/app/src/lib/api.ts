// HTTP-klient mot ki_amp_daemon.py (port 8765). Samme origin på web, konfigurerbar vert i appen.
import { Capacitor, CapacitorHttp } from '@capacitor/core';

export type InputId = 'radio' | 'airplay' | 'bt' | 'aux' | 'aux2' | 'usb' | 'spotify' | 'plex' | 'roon';
export const INPUT_LABEL: Record<InputId, string> = { radio: 'Radio', airplay: 'AirPlay', bt: 'Blåtann', aux: 'AUX 1', aux2: 'AUX 2', usb: 'USB', spotify: 'Spotify', plex: 'Plex', roon: 'Roon' };
export type LevelSource = 'airplay' | 'bt' | 'usb' | 'radio' | 'aux' | 'aux2';

export interface Preset { n: number; title: string }
export interface FullPreset { title: string; url: string; icon?: string }

export interface Status {
  kids?: boolean; sleep?: number; subwave?: boolean;
  power: boolean; input: InputId; volume: number; mute: boolean; bt_pairing: boolean; source_label?: string;
  loudness: boolean; loudness_level: number; voice: boolean; voice_profile: string; voice_profiles: Record<string, string>;
  presets: Preset[]; preset: number; auto_input: boolean; mix: boolean; usb_pc: number; usb_names: string[];
  headphones: boolean; hp_automute: boolean; overtemp: boolean; levels: Record<string, number>;
  playing: boolean; paused: boolean; source: string; cover: string; title: string; artist: string; album: string;
  duration: number; position: number; bt_device: string; name: string; version: string; id: string;
  inputs: InputId[]; board: string; lyrion: boolean; station: string;
  /** Nyere daemon: relativ /api/cover?v=<hash> eller full URL (Spotify). */
  cover_url?: string;
  /** Nyere daemon: s1 | node | core (eldre: utledes fra board). */
  product?: string;
  airplay_device?: string;
  presets_count?: number; presets_max?: number;
  radio_now?: RadioNow | null;
}

export interface RadioNow { name: string; genre?: string; now?: string; image?: string; logo?: string; url?: string; n?: number | null; playing?: boolean }
export interface Fav { n: number; title: string; url: string; genre?: string; image?: string; icon?: string; logo?: string }
export interface Station { id?: string; name: string; genre?: string; url: string; image?: string; country?: string; codec?: string; bitrate?: number }
export interface PresetsResp { presets: (Fav | null)[]; items?: Fav[]; count?: number; max?: number; active: number; lyrion: boolean }
export interface Shelf { id: string; title: string; items: Station[] }

export type Product = 's1' | 'node' | 'core' | 'touch';
export const PRODUCT_LABEL: Record<Product, string> = { s1: 'Skjold S1', node: 'Skjold Node', core: 'Skjold Core', touch: 'Skjold Touch' };
export const PRODUCT_SHORT: Record<Product, string> = { s1: 'S1', node: 'Node', core: 'Core', touch: 'Touch' };
export const PRODUCT_HW: Record<Product, string> = { s1: 'Hovedkort rev B · 2 × 40 W', node: 'Raspberry Pi · 1,8″ skjerm · knapper', core: 'Raspberry Pi · bare lyd', touch: 'Raspberry Pi · 7″ berøringsskjerm · RCA' };
export function productOf(s: Pick<Status, 'board' | 'product'> | null | undefined): Product {
  const p = s?.product;
  if (p === 's1' || p === 'node' || p === 'core' || p === 'touch') return p;
  return s?.board === 'node' ? 'node' : 's1';
}

export const isNative = Capacitor.isNativePlatform();
const HOST_KEY = 'skjold-host';
export const CANDIDATE_HOSTS = ['http://skjold.local:8765', 'http://skjold-node.local:8765', 'http://pultamp.local:8765'];

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
  try { if (url) localStorage.setItem(HOST_KEY, isRelayBase(url) ? url.replace(/\/+$/, '') : normHost(url)); else localStorage.removeItem(HOST_KEY); } catch { /* ignore */ }
}
/** Skjold-hjem: relé-base via skyen (`…/api/hjem/steder/{sted}/enheter/{id}`) – base + '/api/status' virker som lokalt. */
export function isRelayBase(base: string): boolean { return base.includes('/api/hjem/steder/'); }
/** Fetch-valg for en base: relé mot en annen origin trenger informasjonskapselen fra Cloudflare Access. */
export function credFor(base: string): RequestCredentials { return isRelayBase(base) && /^https?:/i.test(base) ? 'include' : 'same-origin'; }
/** Svar som betyr at Cloudflare Access vil ha innlogging (401/403, omdirigering eller HTML-innloggingsside). */
export function isAccessBlock(r: Response): boolean {
  if (r.type === 'opaqueredirect' || r.status === 401 || r.status === 403) return true;
  if (r.redirected && /cloudflareaccess\.com|cdn-cgi\/access/.test(r.url)) return true;
  return false;
}
export function normHost(h: string): string {
  let u = h.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(u)) u = 'http://' + u;
  if (!/:\d+$/.test(u.replace(/^https?:\/\//i, ''))) u += ':8765';
  return u;
}
export function hostLabel(): string {
  const b = getBase();
  if (isRelayBase(b)) return 'Skjold-hjem';
  if (b) return b.replace(/^https?:\/\//i, '');
  return location.host || 'skjold.local';
}

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

async function req<T>(path: string, init?: RequestInit, base = getBase(), timeoutMs = 6000): Promise<T> {
  const ctl = new AbortController();
  let t = 0;
  // CapacitorHttp sin fetch-erstatning bryr seg ikke om AbortSignal – tidsavbrudd med race i tillegg
  const timeout = new Promise<never>((_, rej) => { t = window.setTimeout(() => { ctl.abort(); rej(new ApiError(0, 'Tidsavbrudd')); }, timeoutMs); });
  try {
    const relay = isRelayBase(base);
    const r = await Promise.race([fetch(base + path, { cache: 'no-store', ...(relay ? { credentials: credFor(base), redirect: 'manual' as RequestRedirect } : {}), ...init, signal: ctl.signal }), timeout]);
    if (relay && isAccessBlock(r)) throw new ApiError(401, 'Logg inn på Skjold-hjem');
    if (!r.ok) {
      let msg = r.statusText;
      try { const j = (await r.json()) as { error?: string }; if (j.error) msg = j.error; } catch { /* no body */ }
      throw new ApiError(r.status, msg || 'HTTP ' + r.status);
    }
    return (await r.json()) as T;
  } finally { clearTimeout(t); }
}
const post = <T = Status>(path: string, body: unknown) => req<T>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body ?? {}) });

export interface SkyStatus { koblet: boolean; sted?: string | null; stedNavn?: string | null; aktivHoved?: string | null; erHoved?: boolean; tilkoblet?: boolean; error?: string }
export interface RemoteStatus { enabled: boolean; host: string; master: boolean; active: boolean; installed: boolean; busy: boolean; log: string; has_token: boolean }
/** GET/POST /api/update: installert og nyeste skjold-v*-utgivelse, og oppdatering fra appen (git pull + update.sh). */
export type UpdateInfo = { current: string | null; version: string; latest: string | null; available: boolean; running: boolean; result: string | null; log: string[]; can_update: boolean; error: string | null };

/** Plugins (GET/POST /api/plugins): Skjold-egne kjører i daemonen, Lyrion-plugins installeres i Lyrion. */
export interface Plugin { id: string; name: string; src: 'skjold' | 'lyrion' | 'kommer'; cat: string; desc: string; enabled: boolean; status: string; cfg: Record<string, any>; url?: string }
export interface PluginsResp { plugins: Plugin[]; sleep: number; on: number }
export interface Lyrics { enabled: boolean; found: boolean; plain?: string; synced?: { t: number; l: string }[]; title?: string; artist?: string; position?: number; instrumental?: boolean; error?: string | null }
export interface HistItem { t: number; title: string; artist: string; album: string; input: string; source: string; station: string; cover: string }
export interface Recording { name: string; size: number; t: number; recording: boolean; songs?: number | null }
export interface RecSong { artist: string; title: string; dur?: number; t: number; channel: string; file?: string; where?: 'smb' | 'lokalt'; status: 'ok' | 'duplikat' | 'feil'; error?: string }
export interface RecPayload { items: Recording[]; dir: string; songs?: RecSong[]; smb?: { set: boolean; ok: boolean; msg: string; share: string }; error?: string }
export interface SnapClient { id: string; name: string; connected: boolean; latency: number; volume: number; muted: boolean }
/** Music Assistant (/api/ma/*) og NRK på forespørsel (/api/nrk/*). */
export interface MaItem { uri: string; kind: string; id: string; name: string; artist: string; album: string; duration: number; image: string; provider: string; year?: number | null }
export type MaSearch = Record<'tracks' | 'albums' | 'artists' | 'playlists' | 'radio' | 'podcasts' | 'audiobooks', MaItem[]>;
export interface MaStatus { configured: boolean; ok: boolean; version?: string; player?: string | null; player_id?: string | null; players?: { id: string; name: string }[]; error?: string }
export interface NrkSeries { id: string; title: string; subtitle: string; image: string; kind: 'series' | 'podcast' }
export interface NrkEpisode { id: string; title: string; subtitle: string; date: string; duration: number; image: string; series: string; podcast: boolean; pos?: number; heard?: boolean }
export interface NrkProg { id: string; title?: string; series?: string; image?: string; pos: number; dur?: number; t?: number }
export interface HomeKitInfo { enabled: boolean; available: boolean; running: boolean; paired: boolean; pin: string; setup_uri: string; port: number; error: string | null }
export const api = {
  homekit: () => req<HomeKitInfo>('/api/homekit'),
  maStatus: () => req<MaStatus>('/api/ma/status', undefined, undefined, 12000),
  maDiscover: () => req<{ found: string[] }>('/api/ma/discover', undefined, undefined, 10000),
  maSearch: (q: string) => req<MaSearch>('/api/ma/search?q=' + encodeURIComponent(q), undefined, undefined, 15000),
  maLibrary: (kind: string, q = '') => req<MaItem[]>('/api/ma/library/' + kind + (q ? '?q=' + encodeURIComponent(q) : ''), undefined, undefined, 15000),
  maRecent: () => req<{ items: MaItem[] }>('/api/ma/recent', undefined, undefined, 15000),
  maTracks: (uri: string) => req<{ item: MaItem; tracks: MaItem[] }>('/api/ma/tracks?uri=' + encodeURIComponent(uri), undefined, undefined, 15000),
  maPlay: (uri: string, enqueue: 'play' | 'next' | 'add' = 'play') => post<{ ok: boolean }>('/api/ma/play', { uri, enqueue }),
  nrkSearch: (q: string) => req<{ series: NrkSeries[]; episodes: NrkEpisode[] }>('/api/nrk/search?q=' + encodeURIComponent(q), undefined, undefined, 12000),
  nrkPopular: () => req<{ series: NrkSeries[] }>('/api/nrk/popular', undefined, undefined, 12000),
  nrkSeries: (id: string, kind = '') => req<NrkSeries & { episodes: NrkEpisode[] }>('/api/nrk/series/' + encodeURIComponent(id) + (kind ? '?kind=' + kind : ''), undefined, undefined, 15000),
  nrkContinue: () => req<{ items: NrkProg[] }>('/api/nrk/continue'),
  nrkPlay: (e: { id: string; title?: string; series?: string; image?: string; duration?: number; podcast?: boolean; restart?: boolean }) => post<{ ok: boolean; resume: number }>('/api/nrk/play', e),
  setHomekit: (b: { enabled?: boolean; reset?: boolean }) => post<HomeKitInfo>('/api/homekit', b),
  sky: () => req<SkyStatus>('/api/sky'),
  skyKobl: (kode: string) => post<SkyStatus>('/api/sky', { kode }),
  skyKobleFra: () => post<SkyStatus>('/api/sky', { koble_fra: true }),
  remote: () => req<RemoteStatus>('/api/remote'),
  plugins: () => req<PluginsResp>('/api/plugins'),
  setPlugin: (id: string, b: Record<string, unknown>) => post<PluginsResp>('/api/plugins/' + id, b),
  lyrics: () => req<Lyrics>('/api/lyrics', undefined, undefined, 12000),
  history: () => req<{ enabled: boolean; items: HistItem[] }>('/api/history'),
  recordings: () => req<RecPayload>('/api/recordings'),
  recPost: (b: Record<string, unknown>) => post<RecPayload>('/api/recordings', b),
  recShares: (q: Record<string, string>) => post<{ shares: string[] }>('/api/recordings', { smb_shares: q }),
  snapcast: (b?: Record<string, unknown>) => (b ? post<{ ok: boolean; error?: string; clients: SnapClient[]; role: string }>('/api/snapcast', b) : req<{ ok: boolean; error?: string; clients: SnapClient[]; role: string }>('/api/snapcast')),
  roomeqSweep: (b: { level?: number; delay?: number }) => post<{ f1: number; f2: number; dur: number; sr: number; delay: number }>('/api/roomeq/sweep', b),
  subwave: (health = false) => req<Record<string, any>>('/api/subwave' + (health ? '?health=1' : ''), undefined, undefined, 15000),
  subwavePost: (b: Record<string, unknown>) => post<Record<string, any>>('/api/subwave', b),
  setRemote: (b: { enable: boolean; token?: string; host?: string }) => post<RemoteStatus>('/api/remote', b),
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
  presets: () => req<PresetsResp>('/api/presets'),
  addPreset: (b: { title: string; url: string; genre?: string; image?: string }) => post<PresetsResp>('/api/presets', b),
  orderPresets: (order: number[]) => post<PresetsResp>('/api/presets/order', { order }),
  deletePreset: (n: number) => req<PresetsResp>('/api/presets/' + n, { method: 'DELETE' }),
  playFav: (n: number) => post('/api/presets/' + n + '/play', {}),
  radioSearch: (q: string) => req<{ norway: Station[]; world: Station[]; offline?: boolean }>('/api/radio/search?q=' + encodeURIComponent(q), undefined, getBase(), 12000),
  radioBrowse: () => req<{ shelves: Shelf[]; offline?: boolean }>('/api/radio/browse', undefined, getBase(), 12000),
  radioPlay: (b: { url: string; title: string; image?: string; genre?: string; track?: string; artist?: string; album?: string; duration?: number; source?: string }) => post('/api/radio/play', b),
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
  // Oppsett: Wi-Fi via NetworkManager (nmcli) og høyttalertest (aplay) – nyere daemon; eldre svarer 404
  update: (check = true) => req<UpdateInfo>('/api/update' + (check ? '' : '?check=0'), undefined, getBase(), 15000),
  startUpdate: () => req<UpdateInfo>('/api/update', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }, getBase(), 15000),
  wifiScan: () => req<{ networks: { ssid: string; security?: string; signal?: number; active?: boolean }[] }>('/api/wifi', undefined, getBase(), 25000),
  wifiConnect: (ssid: string, psk: string, hidden = false, security?: 'wpa2' | 'wpa3' | 'open') => req<{ ok: boolean }>('/api/wifi', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ssid, psk, hidden, ...(security ? { security } : {}) }) }, getBase(), 50000),
  speakerTest: (channel: 'L' | 'R') => post<{ ok: boolean }>('/api/test', { channel }),
  reboot: () => post<{ ok: boolean }>('/api/reboot', {}),
  factoryReset: () => post<{ ok: boolean }>('/api/reset', {}),
  forgetBt: () => post<{ ok: boolean }>('/api/bt', { forget: true })
};

/** Kanallogo servert av Skjold selv (/api/logo?k=…): samme opphav som API-et, så den virker også over fjernstyring/relé
 *  og uten blandet innhold. Gjøres absolutt mot aktiv enhet. */
export function logoUrl(logo?: string | null): string {
  if (!logo) return '';
  return /^https?:\/\//i.test(logo) ? logo : getBase() + logo;
}

/** Omslag: cover_url fra daemonen (cache-bust med bildets hash), ellers eldre «cover»-felt. */
export function coverUrl(st: Status | null): string | null {
  if (!st) return null;
  const u = st.cover_url ?? '';
  if (/^https?:\/\//i.test(u)) return u;
  if (u.startsWith('/')) return getBase() + u;
  if (!st.cover) { const im = st.input === 'radio' ? (st.radio_now?.logo ? logoUrl(st.radio_now.logo) : st.radio_now?.image ?? '') : ''; return /^(https?:\/\/|\/)/i.test(im) ? im : null; }   // kanallogo når Lyrion ikke har bilde
  if (/^https?:\/\//i.test(st.cover)) return st.cover;
  return getBase() + '/api/cover?v=' + encodeURIComponent(st.cover);
}

/**
 * Rask sjekk om det svarer en Skjold på base (brukes av søket). I appen går den rett via CapacitorHttp med korte
 * tidsavbrudd på tilkoblingen, så et /24-søk ikke henger på adresser som ikke finnes.
 */
export async function probe(base: string, timeoutMs = 1500): Promise<Status | null> {
  try {
    if (isNative) {
      const r = await Promise.race([
        CapacitorHttp.request({ url: base + '/api/status', method: 'GET', connectTimeout: timeoutMs, readTimeout: timeoutMs + 500, responseType: 'json' }),
        new Promise<null>((res) => setTimeout(() => res(null), timeoutMs + 800))
      ]);
      if (!r || r.status !== 200) return null;
      const d = (typeof r.data === 'string' ? JSON.parse(r.data) : r.data) as Status;
      return d && typeof d === 'object' && 'volume' in d && 'input' in d ? d : null;
    }
    const d = await req<Status>('/api/status', undefined, base, timeoutMs);
    return d && 'volume' in d ? d : null;
  } catch { return null; }
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
