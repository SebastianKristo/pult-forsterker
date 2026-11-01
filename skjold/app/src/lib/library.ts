// Bibliotekene (YouTube Music, Navidrome): kø, historikk og avspilling. Navidrome er ekte (Subsonic-API + /api/radio/play).
// YouTube Music går via Music Assistant, som forsterkeren ikke har ennå – der vises «ikke tilkoblet».
import { signal } from '@preact/signals';
import { api, ApiError } from './api';
import { act, showToast } from './store';
import { ndCover, ndStream, type NdSong } from './navidrome';

export type LibId = 'ytm' | 'nd';
export const LIB_NAME: Record<LibId, string> = { ytm: 'YouTube Music', nd: 'Navidrome' };
export const LIB_TABS: Record<LibId, string[]> = { ytm: ['Hjem', 'Spillelister', 'Historikk'], nd: ['Album', 'Spillelister', 'Historikk'] };

/** Køen appen styrer (forsterkeren spiller én strøm om gangen; neste/forrige sendes herfra). */
export const lq = signal<NdSong[]>([]);
export const li = signal(0);
export const lsvc = signal<LibId | null>(null);

export interface HistItem { s: NdSong; at: number }
const HKEY = 'skjold-libhist';
function loadHist(): Record<string, HistItem[]> { try { return JSON.parse(localStorage.getItem(HKEY) || '{}') as Record<string, HistItem[]>; } catch { return {}; } }
export const hist = signal<Record<string, HistItem[]>>(loadHist());
function saveHist(): void { try { localStorage.setItem(HKEY, JSON.stringify(hist.value)); } catch { /* ignore */ } }
export function clearHist(lib: LibId): void { hist.value = { ...hist.value, [lib]: [] }; saveHist(); }

export function whenText(at: number): string {
  const d = new Date(at), now = new Date();
  const hm = String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  const days = Math.floor((new Date(now.toDateString()).getTime() - new Date(d.toDateString()).getTime()) / 864e5);
  if (days === 0) return 'I dag ' + hm;
  if (days === 1) return 'I går ' + hm;
  if (days < 7) return ['Søndag', 'Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag'][d.getDay()] ?? '';
  return d.getDate() + '.' + (d.getMonth() + 1) + '.';
}

/** Spill låt i fra listen via forsterkeren. */
export function playNd(list: NdSong[], i: number): void {
  const s = list[i]; if (!s) return;
  lq.value = list; li.value = i; lsvc.value = 'nd';
  const h = (hist.value['nd'] ?? []).filter((x) => x.s.id !== s.id);
  hist.value = { ...hist.value, nd: [{ s, at: Date.now() }, ...h].slice(0, 30) }; saveHist();
  const image = ndCover(s.coverArt, 600);
  void act(async () => {
    try { return await api.radioPlay({ url: ndStream(s.id), title: s.title + (s.artist ? ' – ' + s.artist : ''), ...(image ? { image } : {}), genre: 'Navidrome' }); }
    catch (e) { if (e instanceof ApiError && e.status === 404) throw new ApiError(404, 'forsterkeren kan ikke spille strømmer direkte ennå'); throw e; }
  }, { input: 'radio', station: s.title });
}
export function addToQueue(list: NdSong[]): void {
  if (!lq.value.length || lsvc.value !== 'nd') { playNd(list, 0); return; }
  lq.value = [...lq.value, ...list]; showToast(list.length === 1 ? 'Lagt i køen' : list.length + ' låter lagt i køen');
}
export function libNext(d: 1 | -1): boolean {
  if (lsvc.value !== 'nd' || !lq.value.length) return false;
  playNd(lq.value, (li.value + d + lq.value.length) % lq.value.length); return true;
}
export const fmtDur = (s: number) => Math.floor(s / 60) + ':' + String(Math.floor(s % 60)).padStart(2, '0');
