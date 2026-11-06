// Platesamling: vinyl til FLAC med sporoppdeling (/api/vinyl/*).
import { credFor, getBase, isRelayBase } from './api';

async function call<T>(path: string, body?: unknown, method?: string): Promise<T> {
  const base = getBase();
  const init: RequestInit = { cache: 'no-store', ...(isRelayBase(base) ? { credentials: credFor(base) } : {}) };
  if (body !== undefined) Object.assign(init, { method: method || 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  else if (method) init.method = method;
  const r = await fetch(base + path, init);
  const j = (await r.json().catch(() => ({}))) as T & { error?: string };
  if (!r.ok) throw new Error(j.error || 'HTTP ' + r.status);
  return j;
}

export interface VTrack { n: number; side: string; title: string; start: number; end: number; file?: string }
export interface VCfg { thresh_db: number; min_gap: number; min_track: number; device: string }
export interface VStatus {
  state: 'idle' | 'recording' | 'review' | 'saving'; id: string; msg: string; progress: number;
  now: { side: string; secs: number; level: number } | null;
  album: { artist: string; album: string; year: string; cover: string };
  tracks: VTrack[]; sides: { name: string; secs: number; spor: number }[]; cfg: VCfg;
}
export interface VAlbum { id: string; artist: string; album: string; year: string; cover: string; where: string; t: number; secs: number; tracks: VTrack[] }

export const vinyl = {
  status: () => call<VStatus>('/api/vinyl'),
  start: (side = '') => call<VStatus>('/api/vinyl/start', { side }),
  stop: () => call<VStatus>('/api/vinyl/stop', {}),
  edit: (c: Partial<VStatus['album']> & { tracks?: { n: number; title: string }[] }) => call<VStatus>('/api/vinyl/edit', c),
  save: () => call<VStatus>('/api/vinyl/save', {}),
  cancel: () => call<VStatus>('/api/vinyl/cancel', {}),
  archive: () => call<{ albums: VAlbum[] }>('/api/vinyl/archive'),
  editAlbum: (id: string, c: Partial<Omit<VAlbum, 'tracks'>> & { tracks?: { n: number; title: string }[] }) => call<VAlbum>('/api/vinyl/archive', { id, ...c }),
  remove: (id: string) => call<{ albums: VAlbum[] }>('/api/vinyl/' + encodeURIComponent(id), undefined, 'DELETE'),
  settings: (c: Partial<VCfg>) => call<VCfg>('/api/vinyl/settings', c),
};

export const mmss = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
