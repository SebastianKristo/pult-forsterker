// Lyrion Music Server som fjernkontroll: styr alle spillere på serveren (Squeezebox, piCorePlayer, squeezelite,
// Skjold Røst og Skjold-enhetene selv). Med en Skjold-enhet går kallene via den (/api/lms/rpc og /api/lms/img), som
// også virker gjennom Skjold-hjem. Uten Skjold snakker appen rett med serveren (http://server:9000/jsonrpc.js) –
// i Android/iOS-appen går det fint (CapacitorHttp), i nettleseren bare hvis serveren tillater det.
import { signal } from '@preact/signals';
import { apiPost, getBase } from './api';

const DIR_KEY = 'skjold-lms-direkte', SPILLER_KEY = 'skjold-lms-spiller';
const ls = {
  get: (k: string) => { try { return localStorage.getItem(k) ?? ''; } catch { return ''; } },
  set: (k: string, v: string) => { try { if (v) localStorage.setItem(k, v); else localStorage.removeItem(k); } catch { /* privat modus */ } }
};

/** «http://192.168.1.10:9000» når appen snakker direkte med Lyrion, '' = via Skjold-enheten. */
export const lmsDirekte = signal(ls.get(DIR_KEY));
export function settLmsDirekte(adr: string): void { const v = adr.trim() ? normLms(adr) : ''; lmsDirekte.value = v; ls.set(DIR_KEY, v); }
export const lmsSpiller = signal(ls.get(SPILLER_KEY));
export function velgSpiller(id: string): void { lmsSpiller.value = id; ls.set(SPILLER_KEY, id); }

export function normLms(h: string): string {
  let u = h.trim().replace(/\/+$/, '');
  if (!/^https?:\/\//i.test(u)) u = 'http://' + u;
  if (!/:\d+$/.test(u.replace(/^https?:\/\//i, ''))) u += ':9000';
  return u;
}

type Arg = string | number;
/** Én Lyrion-kommando (slim.request). player '' = serverkommando. */
export async function lms<T = Record<string, any>>(player: string, cmd: Arg[], base = lmsDirekte.value): Promise<T> {
  if (base) {
    let t = 0;
    const tid = new Promise<never>((_, rej) => { t = window.setTimeout(() => rej(new Error('Lyrion svarer ikke')), 7000); });
    try {
      const r = await Promise.race([fetch(base + '/jsonrpc.js', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: 1, method: 'slim.request', params: [player, cmd] }) }), tid]);
      if (!r.ok) throw new Error('Lyrion svarte HTTP ' + r.status);
      return ((await r.json()) as { result: T }).result ?? ({} as T);
    } finally { clearTimeout(t); }
  }
  return (await apiPost<{ result: T }>('/api/lms/rpc', { player, cmd })).result ?? ({} as T);
}

export interface Bildekilde { artwork_url?: string; image?: string; icon?: string; coverid?: Arg; artwork_track_id?: Arg; id?: Arg }
/** Bildeadresse for en låt, et album eller et menyvalg fra Lyrion. */
export function lmsBilde(it: Bildekilde | undefined, px = 300): string | undefined {
  if (!it) return undefined;
  let p = String(it.artwork_url || it.image || it.icon || '');
  if (/^https?:\/\//i.test(p)) p = '/imageproxy/' + encodeURIComponent(p) + `/image_${px}x${px}_o`;
  else if (p) { if (!p.startsWith('/')) p = '/' + p; }
  else { const id = it.coverid ?? it.artwork_track_id; if (id === undefined || id === '') return undefined; p = `/music/${id}/cover_${px}x${px}_o`; }
  const d = lmsDirekte.value;
  return d ? d + p : getBase() + '/api/lms/img?p=' + encodeURIComponent(p);
}

export interface LmsSpiller { playerid: string; name: string; model?: string; modelname?: string; isplaying?: number; power?: number; connected?: number; ip?: string }
export interface LmsSpor { id?: Arg; title?: string; artist?: string; album?: string; duration?: number; coverid?: Arg; artwork_url?: string; 'playlist index'?: number; remote?: number }
export interface LmsStatus {
  mode?: 'play' | 'pause' | 'stop'; time?: number; duration?: number; 'mixer volume'?: number; power?: number; 'playlist shuffle'?: number; 'playlist repeat'?: number;
  playlist_cur_index?: string | number; playlist_tracks?: number; current_title?: string; remote?: number; sync_master?: string; sync_slaves?: string;
  playlist_loop?: LmsSpor[]; player_name?: string; remoteMeta?: LmsSpor
}

export async function spillere(base?: string): Promise<{ versjon: string; spillere: LmsSpiller[] }> {
  const r = await lms<{ version?: string; players_loop?: LmsSpiller[] }>('', ['serverstatus', 0, 100], base);
  return { versjon: r.version || '', spillere: r.players_loop || [] };
}
export const status = (id: string) => lms<LmsStatus>(id, ['status', '-', 1, 'tags:aAlcdKNo']);
export const ko = (id: string) => lms<LmsStatus>(id, ['status', 0, 300, 'tags:aAlcdK']);
export async function syncGrupper(): Promise<string[][]> {
  const r = await lms<{ syncgroups_loop?: { sync_members: string }[] }>('', ['syncgroups', '?']);
  return (r.syncgroups_loop || []).map((g) => g.sync_members.split(','));
}
