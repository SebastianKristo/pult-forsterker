// YouTube Music innebygd i Skjold (pi/skjold_ytm.py): bibliotek, album/spillelister og søk via Skjold-enheten.
// Låtene har en ferdig strøm-URL (/api/ytm/stream/<id>.m4a) som spilles via /api/radio/play som Navidrome-låter.
import { apiReq, ApiError, getBase } from './api';
import type { NdAlbum, NdSong } from './navidrome';

export interface YtmStatus { available: boolean; signed_in: boolean; missing: string[]; error: string | null }
export interface YtmHome { newest: NdAlbum[]; other: NdAlbum[]; frequent: NdAlbum[]; playlists: NdAlbum[] }

type Obj = Record<string, unknown>;
const list = (x: unknown): Obj[] => (Array.isArray(x) ? x.filter((o): o is Obj => !!o && typeof o === 'object') : []);
const str = (o: Obj, k: string): string => (o[k] == null ? '' : String(o[k]));

/** Samlinger {id, name, artist, cover, count, playlist} → samme form som Navidrome-album (coverArt = bilde-URL). */
export const ytmColls = (x: unknown): NdAlbum[] => list(x).map((o) => ({
  id: str(o, 'id'), name: str(o, 'name'), artist: str(o, 'artist'), songCount: Number(o['count'] ?? 0) || 0, duration: 0,
  ...(str(o, 'cover') ? { coverArt: str(o, 'cover') } : {}), playlist: o['playlist'] === true
})).filter((c) => c.id);

/** Låter {id, title, artist, album, dur, cover, stream} → NdSong med stream. Låter uten strøm tas ikke med. */
export const ytmSongs = (x: unknown): NdSong[] => list(x).map((o) => ({
  id: str(o, 'id'), title: str(o, 'title'), artist: str(o, 'artist'), album: str(o, 'album'), duration: Number(o['dur'] ?? 0) || 0,
  ...(str(o, 'cover') ? { coverArt: str(o, 'cover') } : {}), stream: str(o, 'stream')
})).filter((s) => s.stream);

export const ytmStatus = () => apiReq<YtmStatus>('/api/ytm/status');
export async function ytmHome(fresh = false): Promise<YtmHome> {
  const o = await apiReq<Obj>('/api/ytm/home' + (fresh ? '?fresh=1' : ''), undefined, undefined, 20000);
  return { newest: ytmColls(o['newest']), other: ytmColls(o['other']), frequent: ytmColls(o['frequent']), playlists: ytmColls(o['playlists']) };
}
/** Forsiden bufres per Skjold-enhet til den hentes på nytt (Prøv igjen, Test innlogging eller ny cookie). */
let cache: { base: string; p: Promise<YtmHome> } | null = null;
export function ytmHomeCached(force = false): Promise<YtmHome> {
  const base = getBase();
  if (force || !cache || cache.base !== base) {
    const p = ytmHome();
    cache = { base, p };
    p.catch(() => { if (cache?.p === p) cache = null; });
  }
  return cache.p;
}
export function ytmForget(): void { cache = null; }
export async function ytmTracks(id: string): Promise<NdSong[]> {
  return ytmSongs((await apiReq<Obj>('/api/ytm/tracks?id=' + encodeURIComponent(id), undefined, undefined, 20000))['tracks']);
}
/** Søk som også gir album (artistsiden og «trykk på albumet» i spilleren). */
export async function ytmSearchAll(q: string): Promise<{ tracks: NdSong[]; albums: NdAlbum[] }> {
  const r = await apiReq<Obj>('/api/ytm/search?q=' + encodeURIComponent(q), undefined, undefined, 15000);
  return { tracks: ytmSongs(r['tracks']), albums: ytmColls(r['albums']).filter((a) => !a.playlist) };
}
export async function ytmSearch(q: string): Promise<NdSong[]> {
  return ytmSongs((await apiReq<Obj>('/api/ytm/search?q=' + encodeURIComponent(q), undefined, undefined, 15000))['tracks']);
}

export type YtmSong = NdSong & { plays?: string };
export interface YtmArtist {
  id: string; name: string; description: string; image: string; subscribers: string; views: string; allSongs: string;
  songs: YtmSong[]; albums: NdAlbum[]; singles: NdAlbum[]; videos: YtmSong[]; related: { id: string; name: string; cover: string; subscribers: string }[]
}
const medAar = (x: unknown): NdAlbum[] => { const l = list(x); return ytmColls(l).map((c, i) => { const y = Number(str(l[i] ?? {}, 'year')); return y ? { ...c, year: y } : c; }); };
/** Artistsiden fra YouTube Music: bilde, biografi, populære låter, album, singler, videoer og lignende artister. */
export async function ytmArtist(q: { name?: string; id?: string }): Promise<YtmArtist> {
  const o = await apiReq<Obj>('/api/ytm/artist?' + (q.id ? 'id=' + encodeURIComponent(q.id) : 'q=' + encodeURIComponent(q.name ?? '')), undefined, undefined, 20000);
  const sanger = (x: unknown, k: string): YtmSong[] => { const l = list(x); return ytmSongs(l).map((s) => ({ ...s, plays: str(l.find((o2) => str(o2, 'id') === s.id) ?? {}, k) })); };
  return {
    id: str(o, 'id'), name: str(o, 'name'), description: str(o, 'description'), image: str(o, 'image'), subscribers: str(o, 'subscribers'), views: str(o, 'views'), allSongs: str(o, 'allSongs'),
    songs: sanger(o['songs'], 'plays'), albums: medAar(o['albums']), singles: medAar(o['singles']), videos: sanger(o['videos'], 'views'),
    related: list(o['related']).map((r) => ({ id: str(r, 'id'), name: str(r, 'name'), cover: str(r, 'cover'), subscribers: str(r, 'subscribers') })).filter((r) => r.id)
  };
}

/** Lesbar feilmelding når biblioteket ikke kunne hentes: gammel programvare, manglende pakker eller feilen fra tjenesten. */
export async function ytmWhy(e: unknown): Promise<string> {
  let st: YtmStatus | null = null;
  try { st = await ytmStatus(); } catch { /* enheten har ikke endepunktet */ }
  if (!st) return e instanceof ApiError && e.status !== 404 && e.status !== 0 ? 'YouTube Music svarte ikke: ' + e.message : 'Skjold-enheten har ikke YouTube Music ennå. Oppdater Skjold-programvaren.';
  if (st.missing?.length) return 'YouTube Music mangler ' + st.missing.join(', ') + ' på enheten. Oppdater Skjold-programvaren.';
  return 'YouTube Music svarte ikke: ' + (st.error || (e instanceof Error ? e.message : 'ukjent feil'));
}

/** «Test innlogging»: [tekst, ok]. */
export async function ytmTest(): Promise<[string, boolean]> {
  let st: YtmStatus;
  try { st = await ytmStatus(); } catch { return ['Oppdater Skjold-programvaren', false]; }
  if (st.missing?.length) return ['Mangler ' + st.missing.join(', '), false];
  let home: YtmHome;
  try { home = await ytmHome(true); } catch (e) { return [st.error ? 'Feil: ' + st.error : e instanceof Error && e.message ? 'Feil: ' + e.message : 'Svarer ikke', false]; }
  cache = { base: getBase(), p: Promise.resolve(home) };
  const n = home.playlists.length;
  return [st.signed_in ? (n > 1 ? 'Innlogget · ' + n + ' spillelister' : 'Innlogget') : 'Tilkoblet uten innlogging (søk virker)', true];
}
