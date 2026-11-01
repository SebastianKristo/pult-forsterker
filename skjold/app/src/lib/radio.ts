// Radiofavoritter (inntil 50) og kanalkatalog fra daemonen: /api/presets*, /api/radio/*.
import { signal, computed } from '@preact/signals';
import { api, ApiError, type Fav, type Shelf, type Station, type Status } from './api';
import { act, applyStatus, showToast } from './store';

export const MAXRADIO = 50;
export const favs = signal<Fav[]>([]);
export const favsLoaded = signal(false);
export const favMax = signal(MAXRADIO);
export const lyrionOk = signal(true);
export const shelves = signal<Shelf[]>([]);
export const browseState = signal<'idle' | 'ok' | 'offline' | 'none'>('idle');

const errMsg = (e: unknown, fallback: string) => (e instanceof ApiError && e.status && e.message ? e.message : fallback);

function takePresets(r: { presets?: (Fav | null)[]; items?: Fav[]; max?: number; lyrion?: boolean }): void {
  const items = r.items ?? (r.presets ?? []).map((p, i) => (p ? { ...p, n: p.n ?? i + 1 } : null)).filter((p): p is Fav => !!p);
  favs.value = items; favsLoaded.value = true;
  if (r.max) favMax.value = r.max;
  if (typeof r.lyrion === 'boolean') lyrionOk.value = r.lyrion;
}
export async function loadFavs(): Promise<void> {
  try { takePresets(await api.presets()); } catch { favsLoaded.value = true; }
}
export async function loadBrowse(): Promise<void> {
  try {
    const r = await api.radioBrowse();
    shelves.value = (r.shelves ?? []).filter((s) => s.items?.length);
    browseState.value = r.offline ? 'offline' : 'ok';
  } catch { browseState.value = 'none'; }
}

export const norm = (s: string) => s.trim().toLowerCase();
export function favOf(name: string, url?: string): Fav | undefined {
  return favs.value.find((f) => (url && f.url === url) || norm(f.title) === norm(name));
}
export const isFull = computed(() => favs.value.length >= favMax.value);

export async function addFav(st: { name: string; url: string; genre?: string; image?: string }): Promise<boolean> {
  if (isFull.value) { showToast('Maks ' + favMax.value + ' favoritter · fjern én først'); return false; }
  try {
    takePresets(await api.addPreset({ title: st.name, url: st.url, ...(st.genre ? { genre: st.genre } : {}), ...(st.image ? { image: st.image } : {}) }));
    return true;
  } catch (e) { showToast(errMsg(e, 'Kunne ikke legge til favoritten')); return false; }
}
export async function removeFav(n: number): Promise<void> {
  try { takePresets(await api.deletePreset(n)); } catch (e) { showToast(errMsg(e, 'Kunne ikke fjerne favoritten')); }
}
/** Flytt favoritt i fra posisjon i til j (indekser i listen). */
export async function moveFav(i: number, j: number): Promise<void> {
  const l = favs.value.slice();
  if (j < 0 || j >= l.length) return;
  const [x] = l.splice(i, 1); if (!x) return; l.splice(j, 0, x);
  favs.value = l;
  try { takePresets(await api.orderPresets(l.map((f) => f.n))); } catch (e) { showToast(errMsg(e, 'Kunne ikke endre rekkefølgen')); void loadFavs(); }
}
export async function toggleFav(st: Station): Promise<void> {
  const f = favOf(st.name, st.url);
  if (f) { if (favs.value.length > 1) await removeFav(f.n); } else await addFav(st);
}

export function playFav(f: Fav): void {
  void act(() => api.playFav(f.n), { input: 'radio', preset: f.n, station: f.title });
}
export function playStation(st: Station): void {
  const f = favOf(st.name, st.url);
  if (f) return playFav(f);
  void act(async () => {
    try { return await api.radioPlay({ url: st.url, title: st.name, ...(st.image ? { image: st.image } : {}), ...(st.genre ? { genre: st.genre } : {}) }); }
    catch (e) { if (e instanceof ApiError && e.status === 404) throw new ApiError(404, 'direkte avspilling støttes ikke ennå'); throw e; }
  }, { input: 'radio', station: st.name });
}

/** Navnet på kanalen som spiller nå (radio), ellers ''. */
export function currentStation(s: Status | null): string {
  if (!s || s.input !== 'radio') return '';
  return s.radio_now?.name || s.station || '';
}

let searchT = 0, searchSeq = 0;
export const searchRes = signal<{ q: string; norway: Station[]; world: Station[]; offline: boolean } | null>(null);
export const searchBusy = signal(false);
export function search(q: string): void {
  clearTimeout(searchT);
  const t = q.trim(), seq = ++searchSeq;
  if (t.length < 2) { searchRes.value = null; searchBusy.value = false; return; }
  searchBusy.value = true;
  searchT = window.setTimeout(async () => {
    try {
      const r = await api.radioSearch(t);
      if (seq === searchSeq) searchRes.value = { q: t, norway: r.norway ?? [], world: r.world ?? [], offline: !!r.offline };
    } catch { if (seq === searchSeq) searchRes.value = { q: t, norway: [], world: [], offline: true }; }
    finally { if (seq === searchSeq) searchBusy.value = false; }
  }, 350);
}

/** Test om en strøm svarer (i nettleseren). */
export function testStream(url: string): Promise<boolean> {
  return new Promise((res) => {
    if (!/^https?:\/\//i.test(url)) return res(false);
    const a = new Audio(); let done = false;
    const fin = (ok: boolean) => { if (done) return; done = true; try { a.pause(); a.removeAttribute('src'); a.load(); } catch { /* ignore */ } res(ok); };
    a.oncanplay = () => fin(true); a.onerror = () => fin(false); setTimeout(() => fin(false), 8000);
    a.preload = 'auto'; a.src = url; a.load();
  });
}
export { applyStatus };
