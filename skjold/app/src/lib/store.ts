// Global tilstand (Preact signals): status-polling, innstillinger, navigasjon.
import { signal, computed, effect } from '@preact/signals';
import { api, ApiError, getBase, needsHost, productOf, type Status, type InputId } from './api';
import { DEF, defaultEq, mergeSettings, type Settings, type EqProfiles, type EqSource } from './settings';

export type Page = 'home' | 'play' | 'eq' | 'radio' | 'rooms' | 'settings';
export interface Route { page: Page; cat?: string }

export const status = signal<Status | null>(null);
export const online = signal<boolean>(false);
export const lastError = signal<string>('');
export const route = signal<Route>({ page: 'home' });
export const fullPlayer = signal<boolean>(false);          // telefon: fullskjerm-spiller
export const mode = signal<'find' | 'setup' | 'app'>(typeof location !== 'undefined' && location.hash === '#finn' ? 'find' : typeof location !== 'undefined' && location.hash === '#oppsett' ? 'setup' : needsHost() ? 'find' : 'app');
export const settings = signal<Settings>({ ...DEF, eq: defaultEq() });
export const settingsSource = signal<'api' | 'local' | 'none'>('none');
export const toast = signal<string>('');
/** Nøkler daemonen faktisk bruker (GET /api/settings → applied). Resten lagres bare. */
export const applied = signal<string[]>([]);
/** Nøkler daemonen ikke kjenner (forkastes av POST) – lagres lokalt på denne enheten. */
export const localOnly = signal<string[]>([]);

const LOCAL_KEY = 'skjold-settings-local';
let toastT = 0;
export function showToast(msg: string, ms = 2600): void {
  toast.value = msg; clearTimeout(toastT); toastT = window.setTimeout(() => (toast.value = ''), ms);
}

// ---------- navigasjon med historikk (Android tilbake-sveip / nettleserens tilbake går ett nivå opp i appen) ----------
interface NavState { skjold: true; page: Page; cat?: string; full: boolean }
const navState = (): NavState => ({ skjold: true, page: route.value.page, ...(route.value.cat ? { cat: route.value.cat } : {}), full: fullPlayer.value });
function pushNav(): void { try { history.pushState(navState(), ''); } catch { /* ignore */ } }
export function go(page: Page, cat?: string): void {
  const same = route.value.page === page && route.value.cat === cat && !fullPlayer.value;
  route.value = cat ? { page, cat } : { page };
  fullPlayer.value = false;
  if (!same) pushNav();
  if (typeof window !== 'undefined') window.scrollTo({ top: 0 });
}
export function openFull(): void { if (!fullPlayer.value) { fullPlayer.value = true; pushNav(); } }
/** Lukk fullskjermspilleren: gå tilbake i historikken hvis den ble åpnet med openFull, ellers bare lukk. */
export function closeFull(): void {
  if (!fullPlayer.value) return;
  const st = history.state as NavState | null;
  if (st?.skjold && st.full) history.back(); else fullPlayer.value = false;
}
/** Er vi på «rot» (Hjem uten noe åpent)? Brukes av Android-tilbakeknappen for å avslutte appen der. */
export function atRoot(): boolean { return route.value.page === 'home' && !fullPlayer.value; }
if (typeof window !== 'undefined') {
  try { history.replaceState(navState(), ''); } catch { /* ignore */ }
  window.addEventListener('popstate', (e) => {
    const st = e.state as NavState | null;
    if (st?.skjold) {
      route.value = st.cat ? { page: st.page, cat: st.cat } : { page: st.page };
      fullPlayer.value = st.full;
    } else { route.value = { page: 'home' }; fullPlayer.value = false; }
  });
}

// ---------- synk med forsterkeren ----------
// Brukerens siste handling «holdes» en kort stund: status som kommer inn (polling, SSE, svar på eldre POST) og som
// ennå ikke viser endringen, overstyres så knapper og volum ikke hopper tilbake. Holdet slippes straks status er enig.
const holds = new Map<string, { v: unknown; until: number }>();
export function hold(patch: Partial<Status>, ms = 1500): void {
  const until = Date.now() + ms;
  for (const [k, v] of Object.entries(patch)) holds.set(k, { v, until });
  if ('playing' in patch) holds.set('paused', { v: !patch.playing, until });
}
/** Ta imot status fra forsterkeren (polling, /api/events eller svar på en handling). */
export function applyStatus(incoming: Status): void {
  const now = Date.now();
  const s = { ...incoming } as unknown as Record<string, unknown>;
  for (const [k, h] of holds) {
    if (now > h.until || JSON.stringify(s[k]) === JSON.stringify(h.v)) { if (now > h.until) holds.delete(k); continue; }
    s[k] = h.v;
  }
  status.value = s as unknown as Status; online.value = true; failures = 0; lastError.value = '';
}

let timer = 0, inflight = false, failures = 0;
export const live = signal<boolean>(false);   // /api/events er tilkoblet
export async function refresh(): Promise<void> {
  if (inflight) return; inflight = true;
  try {
    applyStatus(await api.status());
  } catch (e) {
    failures++;
    if (failures >= 2) { online.value = false; lastError.value = e instanceof Error ? e.message : String(e); }
  } finally { inflight = false; }
}
function schedule(): void {
  clearTimeout(timer);
  if (document.visibilityState === 'hidden') return;
  const playing = status.value?.playing;
  // Med /api/events er polling bare en sikkerhetsline
  const ms = live.value ? 15000 : online.value ? (playing ? 1000 : 2000) : 4000;
  timer = window.setTimeout(async () => { await refresh(); schedule(); }, ms);
}

let es: EventSource | null = null, esRetry = 0, esFails = 0;
function connectEvents(): void {
  clearTimeout(esRetry);
  if (es || typeof EventSource === 'undefined' || document.visibilityState === 'hidden') return;
  try { es = new EventSource(getBase() + '/api/events'); } catch { es = null; return; }
  es.onopen = () => { live.value = true; esFails = 0; schedule(); };
  es.onmessage = (e) => { try { applyStatus(JSON.parse(e.data as string) as Status); } catch { /* ignore */ } };
  es.onerror = () => {
    // eldre daemon (404), nett borte eller CORS: tilbake til polling, prøv igjen senere
    es?.close(); es = null; if (live.value) { live.value = false; schedule(); }
    esFails++; esRetry = window.setTimeout(connectEvents, Math.min(60000, 3000 * esFails));
  };
}
function disconnectEvents(): void { clearTimeout(esRetry); es?.close(); es = null; live.value = false; }
/** Ny vert valgt (Finn Skjold / Rom): koble events på nytt. */
export function reconnect(): void { disconnectEvents(); esFails = 0; connectEvents(); void refresh(); }

export function startPolling(): void {
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') { void refresh(); connectEvents(); } else disconnectEvents();
    schedule();
  });
  connectEvents();
  void refresh().then(schedule);
}
/** Kjør en API-handling med optimistisk oppdatering (holdes til forsterkeren er enig), og vis feil som toast. */
export async function act(fn: () => Promise<Status>, optimistic?: Partial<Status>, holdMs = 1500): Promise<void> {
  if (optimistic && status.value) { hold(optimistic, holdMs); status.value = { ...status.value, ...optimistic }; }
  try { applyStatus(await fn()); }
  catch (e) {
    if (optimistic) for (const k of Object.keys(optimistic)) holds.delete(k);
    showToast(e instanceof ApiError ? 'Forsterkeren svarte: ' + e.message : 'Fikk ikke kontakt med forsterkeren');
    void refresh();
  }
}

/** Spill/pause: viser motsatt tilstand straks og holder den til kilden har fulgt etter (maks 3 s). */
export function playPause(): void {
  const s = status.value; if (!s) return;
  void act(() => api.transport(s.playing ? 'pause' : 'play'), { playing: !s.playing, paused: s.playing }, 3000);
}

// Volum: maks 10 POST/s, alltid siste verdi til slutt, og bare én forespørsel om gangen (ingen utdaterte svar)
let volWant: number | null = null, volBusy = false, volLast = 0, volT = 0;
export function setVolume(v: number, final = false): void {
  v = Math.max(0, Math.min(100, Math.round(v)));
  hold({ volume: v }, 1200);
  if (status.value) status.value = { ...status.value, volume: v };
  volWant = v;
  clearTimeout(volT);
  const wait = final ? 0 : Math.max(0, 100 - (Date.now() - volLast));
  volT = window.setTimeout(sendVolume, wait);
}
async function sendVolume(): Promise<void> {
  if (volBusy || volWant === null) return;
  const v = volWant; volWant = null; volBusy = true; volLast = Date.now();
  try {
    const r = await api.volume(v);
    hold({ volume: volWant ?? v }, 800);   // 800 ms etter siste svar ignoreres eldre verdier
    applyStatus(r);
  } catch { showToast('Fikk ikke kontakt med forsterkeren'); }
  finally { volBusy = false; if (volWant !== null) volT = window.setTimeout(sendVolume, Math.max(0, 100 - (Date.now() - volLast))); }
}


// ---------- settings ----------
const MIGRATE_KEYS = ['nameCustom', 'updChannel', 'updAuto', 'setupDone'];
export async function loadSettings(): Promise<void> {
  try {
    const r = await api.getSettings();
    const missing = Object.keys(DEF).filter((k) => !(k in r.settings));
    let loc: Record<string, unknown> = {};
    try { loc = JSON.parse(localStorage.getItem(LOCAL_KEY) || '{}') as Record<string, unknown>; } catch { /* ignore */ }
    const extra: Record<string, unknown> = {};
    for (const k of missing) if (k in loc) extra[k] = loc[k];
    // Nøkler som tidligere bare lå i localStorage (nameCustom, updChannel, updAuto, setupDone) lagres nå i daemonen:
    // flytt en lokal verdi dit én gang hvis daemonen fortsatt har standardverdien.
    const migrate: Record<string, unknown> = {};
    for (const k of MIGRATE_KEYS) {
      if (k in r.settings && k in loc && loc[k] !== (DEF as unknown as Record<string, unknown>)[k] && r.settings[k] === (DEF as unknown as Record<string, unknown>)[k]) migrate[k] = loc[k];
    }
    settings.value = mergeSettings({ ...r.settings, ...extra, ...migrate }); settingsSource.value = 'api';
    applied.value = r.applied ?? []; localOnly.value = missing;
    if (Object.keys(migrate).length) {
      try { settings.value = mergeSettings({ ...(await api.setSettings(migrate)).settings, ...extra }); } catch { /* prøv igjen neste gang */ }
    }
    return;
  } catch (e) {
    if (!(e instanceof ApiError && e.status === 404)) { /* nettverksfeil: prøv lokalt */ }
  }
  try { settings.value = mergeSettings(JSON.parse(localStorage.getItem(LOCAL_KEY) || '{}')); } catch { settings.value = { ...DEF, eq: defaultEq() }; }
  settingsSource.value = 'local';
}
let saveT = 0; let pending: Record<string, unknown> = {};
export function setSetting<K extends keyof Settings>(k: K, v: Settings[K]): void {
  settings.value = { ...settings.value, [k]: v };
  pending[k] = v;
  clearTimeout(saveT);
  saveT = window.setTimeout(flushSettings, 350);
}
export function setEqProfile(src: EqSource, patch: Partial<EqProfiles[EqSource]>): void {
  const eq: EqProfiles = { ...settings.value.eq, [src]: { ...settings.value.eq[src], ...patch } };
  setSetting('eq', eq);
}
function saveLocal(): void { try { localStorage.setItem(LOCAL_KEY, JSON.stringify(settings.value)); } catch { /* ignore */ } }
async function flushSettings(): Promise<void> {
  const patch = pending; pending = {};
  if (localOnly.value.some((k) => k in patch)) saveLocal();
  if (settingsSource.value === 'local') {
    try { localStorage.setItem(LOCAL_KEY, JSON.stringify(settings.value)); } catch { /* ignore */ }
    return;
  }
  try {
    const r = await api.setSettings(patch);
    // behold lokale endringer som kom inn mens vi lagret
    const keep: Record<string, unknown> = {};
    for (const k of localOnly.value) keep[k] = (settings.value as unknown as Record<string, unknown>)[k];
    settings.value = mergeSettings({ ...r.settings, ...keep, ...pending });
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) { settingsSource.value = 'local'; try { localStorage.setItem(LOCAL_KEY, JSON.stringify(settings.value)); } catch { /* ignore */ } }
    else showToast('Innstillingen ble ikke lagret på forsterkeren');
  }
}

// ---------- avledet ----------
export const eqActiveSource = computed<EqSource>(() => {
  const s = status.value;
  if (!s) return 'air';
  if (s.headphones) return 'hp';
  const m: Record<InputId, EqSource> = { airplay: 'air', bt: 'bt', radio: 'radio', aux: 'aux', aux2: 'aux', usb: 'usb', spotify: 'air' };
  return m[s.input] ?? 'air';
});

export function inputLabel(id: InputId): string {
  const st = settings.value;
  switch (id) {
    case 'aux': return st.nAux1 || 'AUX 1';
    case 'aux2': return st.nAux2 || 'AUX 2';
    case 'usb': return 'USB';
    case 'airplay': return 'AirPlay';
    case 'bt': return 'Blåtann';
    case 'radio': return 'Radio';
    case 'spotify': return 'Spotify';
  }
  return id;
}

export const product = computed(() => productOf(status.value));

export const deviceName = computed(() => {
  const st = settings.value;
  // daemonen avgjør navnet (eget navn > valg > KI_AMP_NAME) og bruker det i AirPlay/Spotify/Blåtann
  if (settingsSource.value === 'api' && status.value?.name) return status.value.name;
  if (st.nameCustom) return st.nameCustom;
  const names = ['Skjold S1', 'Stue', 'Kontor', 'Soverom'];
  if (st.name > 0 && names[st.name]) return names[st.name] as string;
  return status.value?.name && status.value.name !== 'Pultforsterker' ? status.value.name : 'Skjold S1';
});

// Lagre siste kjente status i sessionStorage, så første render ikke blinker
effect(() => { const s = status.value; if (s) { try { sessionStorage.setItem('skjold-last', JSON.stringify(s)); } catch { /* ignore */ } } });
try { const j = sessionStorage.getItem('skjold-last'); if (j && !status.value) status.value = JSON.parse(j) as Status; } catch { /* ignore */ }

// ---------- Nylig spilt (lagres på denne enheten, fra det forsterkeren faktisk har spilt) ----------
export interface Recent { key: string; title: string; big: string; kind: string; input: InputId; station: boolean; image?: string; url?: string }
const RECENT_KEY = 'skjold-recent';
export const recent = signal<Recent[]>((() => { try { return JSON.parse(localStorage.getItem(RECENT_KEY) || '[]') as Recent[]; } catch { return []; } })());
effect(() => {
  const s = status.value;
  if (!s || !s.power || !s.playing) return;
  let r: Recent | null = null;
  if (s.input === 'radio') {
    const name = s.radio_now?.name || s.station;
    if (name) r = { key: 'radio:' + name, title: name, big: name, kind: 'Radio · kanal', input: 'radio', station: true, ...(s.radio_now?.image ? { image: s.radio_now.image } : {}), ...(s.radio_now?.url ? { url: s.radio_now.url } : {}) };
  } else if (s.title) {
    r = { key: s.input + ':' + s.title + ':' + s.artist, title: s.title, big: s.artist || s.title, kind: inputLabel(s.input) + ' · låt', input: s.input, station: false };
  }
  if (!r || recent.peek()[0]?.key === r.key) return;
  const next = [r, ...recent.peek().filter((x) => x.key !== r!.key)].slice(0, 12);
  recent.value = next;
  try { localStorage.setItem(RECENT_KEY, JSON.stringify(next)); } catch { /* ignore */ }
});
export function eqActiveProfile(): number[] { return settings.value.eq[eqActiveSource.value]?.eq ?? [0, 0, 0, 0, 0]; }
