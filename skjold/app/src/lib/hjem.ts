// Skjold-hjem (docs/SKJOLD_HJEM.md): steder i skyen, stedsvelger og relé når en enhet ikke nås på LAN.
// Web-UI servert fra skyen bruker relative stier og nettleserens Access-informasjonskapsel. Fra en enhets eget
// web-UI (annen origin) prøves sky-adressen med credentials: 'include' – virker bare hvis skyen tillater CORS
// for den origin-en; ellers vises «Logg inn på Skjold-hjem» som åpner skyen i en ny fane.
import { signal } from '@preact/signals';
import { ApiError, getBase, isAccessBlock, isNative, isRelayBase, probe, setBase } from './api';
import { loadSettings, reconnect } from './store';

export const SKY_DEFAULT = 'https://skjold-styring.smarthjemexperten.no';
const SKY_KEY = 'skjold-sky-url', STED_KEY = 'skjold-sted', LAN_KEY = 'skjold-lan-host', PICK_KEY = 'skjold-sted-enhet:';

export interface Sted { id: string; navn: string; rolle: 'eier' | 'medlem'; enheter: number; online: number | boolean; hoved?: string; reserve?: string[] }
export interface Enhet {
  id: string; navn: string; produkt: string; rom?: string; online: boolean; aktivHoved: boolean; hoved: boolean;
  reserveNr: number | null; lan?: unknown; sist?: number;
}

const ls = {
  get: (k: string): string => { try { return localStorage.getItem(k) ?? ''; } catch { return ''; } },
  set: (k: string, v: string): void => { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch { /* ignore */ } }
};

export const steder = signal<Sted[]>([]);
/** '' = «Dette nettverket» (LAN-oppdagelse som før). */
export const stedId = signal<string>(ls.get(STED_KEY));
export const enheter = signal<Enhet[]>([]);
/** Enheten appen styrer nå i valgt sted. */
export const aktivEnhet = signal<string>('');
export const hjemState = signal<'ukjent' | 'laster' | 'ok' | 'login' | 'feil'>('ukjent');
export const hjemErr = signal('');
/** Web-UI-et er servert fra skyen selv (relative stier). */
export const sameOrigin = signal(false);

export function skyUrl(): string { return ls.get(SKY_KEY) || SKY_DEFAULT; }
export function setSkyUrl(u: string): void { const v = u.trim().replace(/\/+$/, ''); ls.set(SKY_KEY, v && v !== SKY_DEFAULT ? (/^https?:\/\//.test(v) ? v : 'https://' + v) : ''); }
export function skyBase(): string { return sameOrigin.value ? '' : skyUrl(); }
const enc = encodeURIComponent;
export function relayBase(sted: string, id: string): string { return `${skyBase()}/api/hjem/steder/${enc(sted)}/enheter/${enc(id)}`; }
export function loginUrl(): string { return skyUrl() + '/'; }
export function stedNavn(): string { return steder.value.find((s) => s.id === stedId.value)?.navn ?? (stedId.value ? 'Sted' : 'Dette nettverket'); }

async function hj<T>(path: string, init?: RequestInit, timeoutMs = 8000): Promise<T> {
  const ctl = new AbortController(); const t = window.setTimeout(() => ctl.abort(), timeoutMs);
  try {
    let r: Response;
    try {
      r = await fetch(skyBase() + path, {
        cache: 'no-store', credentials: sameOrigin.value ? 'same-origin' : 'include', redirect: 'manual', ...init, signal: ctl.signal,
        ...(init?.body ? { headers: { 'Content-Type': 'application/json' } } : {})
      });
    } catch (e) {
      // Fra en annen origin gir Access-omdirigering/CORS bare «Failed to fetch» – behandles som «logg inn»
      if (!sameOrigin.value && !ctl.signal.aborted) throw new ApiError(401, 'Logg inn på Skjold-hjem');
      throw e instanceof Error ? new ApiError(0, ctl.signal.aborted ? 'Tidsavbrudd' : e.message) : e;
    }
    if (isAccessBlock(r)) throw new ApiError(401, 'Logg inn på Skjold-hjem');
    const ct = r.headers.get('content-type') ?? '';
    if (!r.ok) {
      let msg = 'HTTP ' + r.status;
      try { const j = (await r.json()) as { error?: string; feil?: string }; msg = j.error || j.feil || msg; } catch { /* ingen JSON */ }
      throw new ApiError(r.status, msg);
    }
    if (!ct.includes('json')) throw new ApiError(401, 'Logg inn på Skjold-hjem');   // HTML = Access-innloggingsside
    return (await r.json()) as T;
  } finally { clearTimeout(t); }
}
const body = (method: string, b?: unknown): RequestInit => ({ method, ...(b !== undefined ? { body: JSON.stringify(b) } : {}) });

export const hjem = {
  steder: () => hj<Sted[]>('/api/hjem/steder'),
  nyttSted: (navn: string) => hj<Sted>('/api/hjem/steder', body('POST', { navn })),
  endreSted: (id: string, p: { navn?: string; hoved?: string; reserve?: string[] }) => hj<Sted>('/api/hjem/steder/' + enc(id), body('PATCH', p)),
  slettSted: (id: string) => hj<unknown>('/api/hjem/steder/' + enc(id), body('DELETE')),
  enheter: (id: string) => hj<Enhet[]>('/api/hjem/steder/' + enc(id) + '/enheter'),
  kobling: (id: string) => hj<{ kode: string; utloper: number | string }>('/api/hjem/steder/' + enc(id) + '/kobling', body('POST', {})),
  fjernEnhet: (id: string, enhet: string) => hj<unknown>('/api/hjem/steder/' + enc(id) + '/enheter/' + enc(enhet), body('DELETE'))
};

function fail(e: unknown): void {
  if (e instanceof ApiError && e.status === 401) { hjemState.value = 'login'; hjemErr.value = ''; }
  else { hjemState.value = 'feil'; hjemErr.value = e instanceof Error ? e.message : String(e); }
}

/** Hent stedene (og enhetene i valgt sted). Kalles ved oppstart, når menyen åpnes og etter endringer. */
export async function loadSteder(): Promise<void> {
  if (hjemState.value !== 'ok') hjemState.value = 'laster';
  try {
    steder.value = await hjem.steder(); hjemState.value = 'ok'; hjemErr.value = '';
    if (stedId.value) await loadEnheter();
  } catch (e) { fail(e); }
}
export async function loadEnheter(): Promise<void> {
  const id = stedId.value; if (!id) { enheter.value = []; return; }
  try { const l = await hjem.enheter(id); if (stedId.value === id) enheter.value = l; } catch (e) { fail(e); }
}

/** LAN-adressen skyen kjenner for enheten (`lan`: "ip:port", URL eller {ip,port}). */
export function lanBase(e: Enhet): string | null {
  const l = e.lan as unknown;
  if (!l) return null;
  if (typeof l === 'string') { if (/^https?:\/\//.test(l)) return l.replace(/\/+$/, ''); return 'http://' + (/:\d+$/.test(l) ? l : l + ':8765'); }
  if (typeof l === 'object' && l && 'ip' in l) { const o = l as { ip: string; port?: number }; return `http://${o.ip}:${o.port ?? 8765}`; }
  return null;
}

/** Direkte på LAN hvis enheten svarer innen 1,5 s (ikke fra en https-side – blandet innhold blokkeres), ellers relé. */
export async function baseFor(e: Enhet): Promise<string> {
  const lan = lanBase(e);
  const canHttp = isNative || location.protocol !== 'https:';
  if (lan && canHttp) { const st = await probe(lan, 1500); if (st && (!st.id || st.id === e.id)) return lan; }
  return relayBase(stedId.value, e.id);
}

async function connect(base: string): Promise<void> { setBase(base); reconnect(); await loadSettings(); }

/** Styr en enhet i valgt sted. */
export async function velgEnhet(e: Enhet): Promise<void> {
  aktivEnhet.value = e.id; ls.set(PICK_KEY + stedId.value, e.id);
  await connect(await baseFor(e));
}

/** Bytt sted ('' = Dette nettverket). Valget huskes. */
export async function selectSted(id: string): Promise<void> {
  if (id === stedId.value && (id === '' || enheter.value.length)) return;
  if (!stedId.value) { const b = getBase(); if (!isRelayBase(b)) ls.set(LAN_KEY, b); }
  stedId.value = id; ls.set(STED_KEY, id); enheter.value = []; aktivEnhet.value = '';
  if (!id) { const lan = ls.get(LAN_KEY); setBase(lan || null); reconnect(); await loadSettings(); return; }
  await loadEnheter();
  const list = enheter.value, last = ls.get(PICK_KEY + id);
  const e = list.find((x) => x.id === last) ?? list.find((x) => x.aktivHoved) ?? list.find((x) => x.online) ?? list[0];
  if (e) await velgEnhet(e);
}

let started = false;
/** Oppstart: finn ut om vi er servert fra skyen, hent steder og koble til valgt sted. */
export async function startHjem(): Promise<void> {
  if (started) return; started = true;
  if (!isNative && location.protocol.startsWith('http')) {
    if (location.origin === SKY_DEFAULT || location.origin === skyUrl()) sameOrigin.value = true;
    else {
      try {   // en enhet svarer 404 her; skyen (eller lokal test) svarer med en JSON-liste
        const r = await fetch('/api/hjem/steder', { cache: 'no-store', redirect: 'manual' });
        if (r.ok && (r.headers.get('content-type') ?? '').includes('json')) sameOrigin.value = true;
        else if (isAccessBlock(r)) sameOrigin.value = true;
      } catch { /* ikke skyen */ }
    }
  }
  await loadSteder();
  if (stedId.value) {
    const list = enheter.value, b = getBase(), last = ls.get(PICK_KEY + stedId.value);
    const e = list.find((x) => x.id === last) ?? list.find((x) => x.aktivHoved) ?? list[0];
    // Var vi på relé eller servert fra skyen: velg beste vei på nytt (LAN hvis den svarer)
    if (e && (isRelayBase(b) || sameOrigin.value || !b)) await velgEnhet(e);
    else if (e) aktivEnhet.value = e.id;
  } else if (sameOrigin.value && steder.value.length) {
    // Skyen har ikke noe «Dette nettverket» – velg første sted
    const first = steder.value[0]; if (first) await selectSted(first.id);
  }
  // Hold online/aktiv-merkene ferske
  window.setInterval(() => { if (stedId.value && document.visibilityState === 'visible' && hjemState.value === 'ok') void loadEnheter(); }, 15000);
}

/** Merket for en enhet i romlista. */
export function rolleMerke(e: Enhet): string {
  return e.hoved ? 'Hoved' : e.reserveNr ? 'Reserve ' + e.reserveNr : '';
}
/** Vis stedsvelgeren som tittel på telefon (bare når Skjold-hjem er i bruk). */
export const visSted = (): boolean => !!stedId.value || steder.value.length > 0 || sameOrigin.value;
