// Global tilstand (Preact signals): status-polling, innstillinger, navigasjon.
import { signal, computed, effect } from '@preact/signals';
import { api, ApiError, needsHost, type Status, type InputId } from './api';
import { DEF, defaultEq, mergeSettings, type Settings, type EqProfiles, type EqSource } from './settings';

export type Page = 'home' | 'play' | 'eq' | 'radio' | 'rooms' | 'settings';
export interface Route { page: Page; cat?: string }

export const status = signal<Status | null>(null);
export const online = signal<boolean>(false);
export const lastError = signal<string>('');
export const route = signal<Route>({ page: 'home' });
export const fullPlayer = signal<boolean>(false);          // telefon: fullskjerm-spiller
export const mode = signal<'find' | 'setup' | 'app'>(needsHost() ? 'find' : 'app');
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

export function go(page: Page, cat?: string): void {
  route.value = cat ? { page, cat } : { page };
  fullPlayer.value = false;
  if (typeof window !== 'undefined') window.scrollTo({ top: 0 });
}

// ---------- polling ----------
let timer = 0, inflight = false, failures = 0;
export async function refresh(): Promise<void> {
  if (inflight) return; inflight = true;
  try {
    const s = await api.status();
    status.value = s; online.value = true; failures = 0; lastError.value = '';
  } catch (e) {
    failures++;
    if (failures >= 2) { online.value = false; lastError.value = e instanceof Error ? e.message : String(e); }
  } finally { inflight = false; }
}
function schedule(): void {
  clearTimeout(timer);
  if (document.visibilityState === 'hidden') return;
  const playing = status.value?.playing;
  timer = window.setTimeout(async () => { await refresh(); schedule(); }, online.value ? (playing ? 1000 : 2000) : 4000);
}
export function startPolling(): void {
  document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'visible') { void refresh(); } schedule(); });
  void refresh().then(schedule);
}
/** Kjør en API-handling, oppdater status med svaret, og vis feil som toast. */
export async function act(fn: () => Promise<Status>, optimistic?: Partial<Status>): Promise<void> {
  if (optimistic && status.value) status.value = { ...status.value, ...optimistic };
  try { status.value = await fn(); online.value = true; }
  catch (e) {
    showToast(e instanceof ApiError ? 'Forsterkeren svarte: ' + e.message : 'Fikk ikke kontakt med forsterkeren');
    void refresh();
  }
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
  const m: Record<InputId, EqSource> = { airplay: 'air', bt: 'bt', radio: 'radio', aux: 'aux', aux2: 'aux', usb: 'usb' };
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
  }
}

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
