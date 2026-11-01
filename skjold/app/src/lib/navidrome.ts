// Navidrome via Subsonic-API-et, direkte fra appen (https://www.subsonic.org/pages/api.jsp, API 1.16.1).
// Innlogging med token: t = md5(passord + salt), s = salt. Avspilling: stream-URL-en sendes til forsterkeren
// (POST /api/radio/play {url,title,image}), som spiller den via Lyrion som en direkte strøm.
import { signal } from '@preact/signals';

export interface NdConf { url: string; user: string; pass: string }
export interface NdSong { id: string; title: string; artist: string; album: string; albumId?: string; duration: number; coverArt?: string; suffix?: string; bitRate?: number; samplingRate?: number }
export interface NdAlbum { id: string; name: string; artist: string; songCount: number; duration: number; coverArt?: string; year?: number }
export interface NdPlaylist { id: string; name: string; songCount: number; duration: number; coverArt?: string; owner?: string }

const KEY = 'skjold-navidrome';
function load(): NdConf { try { const j = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<NdConf>; return { url: j.url ?? '', user: j.user ?? '', pass: j.pass ?? '' }; } catch { return { url: '', user: '', pass: '' }; } }
export const ndConf = signal<NdConf>(load());
export function setNdConf(p: Partial<NdConf>): void {
  ndConf.value = { ...ndConf.value, ...p };
  try { localStorage.setItem(KEY, JSON.stringify(ndConf.value)); } catch { /* ignore */ }
  ndStatus.value = 'unknown';
}
export const ndConfigured = (): boolean => !!(ndConf.value.url.trim() && ndConf.value.user.trim() && ndConf.value.pass);
/** unknown = ikke testet, ok = innlogget, bad = feil (ndError forklarer). */
export const ndStatus = signal<'unknown' | 'busy' | 'ok' | 'bad'>('unknown');
export const ndError = signal('');

// ---- MD5 (RFC 1321), liten og synkron, for Subsonic-token ----
function md5(str: string): string {
  const b = new TextEncoder().encode(str);
  const n = (((b.length + 8) >>> 6) + 1) * 16, w = new Array<number>(n).fill(0);
  for (let i = 0; i < b.length; i++) w[i >> 2]! |= (b[i] ?? 0) << ((i % 4) * 8);
  w[b.length >> 2]! |= 0x80 << ((b.length % 4) * 8); w[n - 2] = b.length * 8;
  const K = Array.from({ length: 64 }, (_, i) => Math.floor(Math.abs(Math.sin(i + 1)) * 2 ** 32) | 0);
  const R = [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21];
  let a0 = 0x67452301, b0 = 0xefcdab89 | 0, c0 = 0x98badcfe | 0, d0 = 0x10325476;
  for (let o = 0; o < n; o += 16) {
    let A = a0, B = b0, C = c0, D = d0;
    for (let i = 0; i < 64; i++) {
      const r = i >> 4; let F: number, g: number;
      if (r === 0) { F = (B & C) | (~B & D); g = i; } else if (r === 1) { F = (D & B) | (~D & C); g = (5 * i + 1) % 16; }
      else if (r === 2) { F = B ^ C ^ D; g = (3 * i + 5) % 16; } else { F = C ^ (B | ~D); g = (7 * i) % 16; }
      const s = R[r * 4 + (i % 4)]!, x = (A + F + K[i]! + (w[o + g] ?? 0)) | 0;
      A = D; D = C; C = B; B = (B + ((x << s) | (x >>> (32 - s)))) | 0;
    }
    a0 = (a0 + A) | 0; b0 = (b0 + B) | 0; c0 = (c0 + C) | 0; d0 = (d0 + D) | 0;
  }
  return [a0, b0, c0, d0].map((v) => Array.from({ length: 4 }, (_, i) => ((v >>> (i * 8)) & 255).toString(16).padStart(2, '0')).join('')).join('');
}
export const _md5 = md5;

function base(): string { let u = ndConf.value.url.trim().replace(/\/+$/, ''); if (u && !/^https?:\/\//i.test(u)) u = 'http://' + u; return u; }
function auth(): string {
  const salt = Math.random().toString(36).slice(2, 10);
  const c = ndConf.value;
  return 'u=' + encodeURIComponent(c.user.trim()) + '&t=' + md5(c.pass + salt) + '&s=' + salt + '&v=1.16.1&c=skjold&f=json';
}
export function ndUrl(view: string, params: Record<string, string | number> = {}): string {
  const q = Object.entries(params).map(([k, v]) => k + '=' + encodeURIComponent(String(v))).join('&');
  return base() + '/rest/' + view + '?' + auth() + (q ? '&' + q : '');
}

async function call<T>(view: string, params: Record<string, string | number> = {}): Promise<T> {
  if (!ndConfigured()) throw new Error('Navidrome er ikke satt opp');
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 10000);
  try {
    const r = await fetch(ndUrl(view, params), { signal: ctl.signal, cache: 'no-store' });
    if (!r.ok) throw new Error('Navidrome svarte ' + r.status);
    const j = (await r.json()) as { 'subsonic-response'?: Record<string, unknown> & { status?: string; error?: { message?: string } } };
    const sr = j['subsonic-response'];
    if (!sr) throw new Error('Ikke et Subsonic-svar');
    if (sr.status !== 'ok') throw new Error(sr.error?.message || 'Innlogging feilet');
    return sr as unknown as T;
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw new Error('Tidsavbrudd');
    if (e instanceof TypeError) throw new Error('Får ikke kontakt med serveren');
    throw e;
  } finally { clearTimeout(t); }
}

export async function ndPing(): Promise<boolean> {
  ndStatus.value = 'busy'; ndError.value = '';
  try { await call('ping'); ndStatus.value = 'ok'; return true; }
  catch (e) { ndStatus.value = 'bad'; ndError.value = e instanceof Error ? e.message : String(e); return false; }
}

const arr = <T,>(x: T | T[] | undefined): T[] => (Array.isArray(x) ? x : x ? [x] : []);
const song = (s: Record<string, unknown>): NdSong => ({
  id: String(s['id']), title: String(s['title'] ?? ''), artist: String(s['artist'] ?? ''), album: String(s['album'] ?? ''),
  ...(s['albumId'] ? { albumId: String(s['albumId']) } : {}), duration: Number(s['duration'] ?? 0),
  ...(s['coverArt'] ? { coverArt: String(s['coverArt']) } : {}), ...(s['suffix'] ? { suffix: String(s['suffix']) } : {}),
  ...(s['bitRate'] ? { bitRate: Number(s['bitRate']) } : {}), ...(s['samplingRate'] ? { samplingRate: Number(s['samplingRate']) } : {})
});
const album = (a: Record<string, unknown>): NdAlbum => ({
  id: String(a['id']), name: String(a['name'] ?? a['title'] ?? ''), artist: String(a['artist'] ?? ''), songCount: Number(a['songCount'] ?? 0),
  duration: Number(a['duration'] ?? 0), ...(a['coverArt'] ? { coverArt: String(a['coverArt']) } : {}), ...(a['year'] ? { year: Number(a['year']) } : {})
});

export async function ndAlbumList(type: 'newest' | 'frequent' | 'random' | 'recent', size = 12): Promise<NdAlbum[]> {
  const r = await call<{ albumList2?: { album?: Record<string, unknown>[] } }>('getAlbumList2', { type, size });
  return arr(r.albumList2?.album).map(album);
}
export async function ndAlbum(id: string): Promise<{ album: NdAlbum; songs: NdSong[] }> {
  const r = await call<{ album: Record<string, unknown> & { song?: Record<string, unknown>[] } }>('getAlbum', { id });
  return { album: album(r.album), songs: arr(r.album.song).map(song) };
}
export async function ndPlaylists(): Promise<NdPlaylist[]> {
  const r = await call<{ playlists?: { playlist?: Record<string, unknown>[] } }>('getPlaylists');
  return arr(r.playlists?.playlist).map((p) => ({ id: String(p['id']), name: String(p['name'] ?? ''), songCount: Number(p['songCount'] ?? 0), duration: Number(p['duration'] ?? 0), ...(p['coverArt'] ? { coverArt: String(p['coverArt']) } : {}), ...(p['owner'] ? { owner: String(p['owner']) } : {}) }));
}
export async function ndPlaylist(id: string): Promise<NdSong[]> {
  const r = await call<{ playlist: { entry?: Record<string, unknown>[] } }>('getPlaylist', { id });
  return arr(r.playlist.entry).map(song);
}
export async function ndSearch(q: string): Promise<NdSong[]> {
  const r = await call<{ searchResult3?: { song?: Record<string, unknown>[] } }>('search3', { query: q, songCount: 30, albumCount: 0, artistCount: 0 });
  return arr(r.searchResult3?.song).map(song);
}
export const ndCover = (id?: string, size = 300): string => (id && ndConfigured() ? ndUrl('getCoverArt', { id, size }) : '');
export const ndStream = (id: string): string => ndUrl('stream', { id });
