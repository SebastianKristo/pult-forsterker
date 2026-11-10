// Biblioteker (Skjold App v2 · tLib): YouTube Music og Navidrome. Malen er portert 1:1 fra designfilen.
// Navidrome er ekte (Subsonic-API direkte fra appen). YouTube Music hentes fra Skjold-enheten (/api/ytm/*, lib/ytm.ts);
// svarer den ikke, vises samme skall med en tydelig «ikke tilkoblet»-tilstand i stedet for eksempeldata.
import { useEffect, useState } from 'preact/hooks';
import { go, openFull, route, trackSub } from '../lib/store';
import { art } from '../lib/settings';
import { addToQueue, clearHist, fmtDur, hist, li, LIB_NAME, LIB_TABS, lq, lsvc, playNd, whenText, type LibId } from '../lib/library';
import { MediaLibSection } from './medialib';
import { LydLenker } from './lyd';
import { ndAlbum, ndAlbumList, ndConfigured, ndCover, ndPlaylist, ndPlaylists, ndSearch, type NdAlbum, type NdPlaylist, type NdSong } from '../lib/navidrome';
import { signal } from '@preact/signals';
import { AskBox, TagFilterBar } from './ai';
import { ytmHomeCached, ytmSearch, ytmTracks, ytmWhy } from '../lib/ytm';

/** Tilstand per bibliotek-side (signaler, så tilbake-knappen og skjermbildeskriptet kan styre den). */
export const libUi = { tab: signal(0), pl: signal<{ kind: 'album' | 'pl'; id: string; name: string } | null>(null), q: signal(''), hero: signal(0), mood: signal<number | null>(null) };
trackSub(libUi.pl, () => { libUi.pl.value = null; });   // album/spilleliste: tilbake lukker den
export function libBack(): boolean { if (libUi.pl.value) { libUi.pl.value = null; return true; } return false; }

const cover = (id: string | undefined, key: string, size = 300) => { const u = ndCover(id, size), a = art(key); return { bg: u ? 'url("' + u.replace(/"/g, '') + '") center / cover no-repeat, ' + a.bg : a.bg, ink: u ? 'transparent' : a.ink }; };
const MOODS = ['Ny energi', 'Godfølelse', 'Avslapping', 'Trening', 'Fest', 'Fokus', 'Søvn'];
const PLAY = 'M8 5v14l11-7z';

function useNd() {
  const [albums, setAlbums] = useState<NdAlbum[] | null>(null);
  const [rnd, setRnd] = useState<NdAlbum[]>([]), [freq, setFreq] = useState<NdAlbum[]>([]);
  const [pls, setPls] = useState<NdPlaylist[]>([]);
  const [err, setErr] = useState('');
  useEffect(() => {
    if (!ndConfigured()) return;
    Promise.all([ndAlbumList('newest', 12), ndAlbumList('random', 12), ndAlbumList('frequent', 12).catch(() => []), ndPlaylists().catch(() => [])])
      .then(([a, r, f, p]) => { setAlbums(a); setRnd(r); setFreq(f); setPls(p); })
      .catch((e: unknown) => setErr(e instanceof Error ? e.message : String(e)));
  }, []);
  return { albums, rnd, freq, pls, err, retry: () => {} };
}

/** YouTube Music fra Skjold-enheten, i samme form som useNd: albums = album, rnd = «Til deg», pls = spillelister + «Til deg». */
export function useYtm(on = true) {
  const [albums, setAlbums] = useState<NdAlbum[] | null>(null);
  const [rnd, setRnd] = useState<NdAlbum[]>([]), [freq, setFreq] = useState<NdAlbum[]>([]);
  const [pls, setPls] = useState<NdAlbum[]>([]);
  const [err, setErr] = useState('');
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!on) return;
    let live = true;
    setErr('');
    ytmHomeCached(n > 0).then((h) => {
      if (!live) return;
      const forYou = uniq([...h.frequent, ...h.other]);
      setAlbums(h.newest); setRnd(forYou); setFreq([]);
      // også «Til deg» (mikser og anbefalte album fra forsiden), så det er noe å spille uten innlogging
      setPls(uniq([...h.playlists, ...h.frequent.slice(0, 8), ...h.other.slice(0, 8)]));
      if (!h.newest.length && !h.playlists.length && !forYou.length) setErr('Fant ingenting i YouTube Music. Legg inn cookien under Innstillinger → Musikktjenester for biblioteket ditt.');
    }).catch(async (e: unknown) => { const why = await ytmWhy(e); if (live) setErr(why); });
    return () => { live = false; };
  }, [on, n]);
  return { albums, rnd, freq, pls, err, retry: () => setN((x) => x + 1) };
}
const uniq = <T extends { id: string },>(l: T[]): T[] => l.filter((x, i) => l.findIndex((y) => y.id === x.id) === i);
/** Låtene i et album/en spilleliste fra riktig bibliotek. */
export const collSongs = (lib: LibId, kind: 'album' | 'pl', id: string): Promise<NdSong[]> =>
  lib === 'ytm' ? ytmTracks(id) : kind === 'album' ? ndAlbum(id).then((r) => r.songs) : ndPlaylist(id);

function NotConnected({ lib, err, retry }: { lib: LibId; err?: string; retry?: () => void }) {
  const why = lib === 'ytm' ? err || 'Henter YouTube Music fra Skjold-enheten …' : err ? 'Fikk ikke kontakt med Navidrome: ' + err + '.' : 'Legg inn adressen til Navidrome-serveren, brukernavn og passord.';
  return (
    <div data-testid="lib-off" style="position:relative;flex-shrink:0;border-radius:16px;overflow:hidden;background:#141415;border:1px solid #242426">
      <div style="position:relative;display:flex;flex-direction:column;gap:10px;padding:16px">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#f0c46a">IKKE TILKOBLET</span>
        <span style="font-size:19px;font-weight:600;line-height:1.15">{lib === 'ytm' ? 'YouTube Music er ikke tilgjengelig' : 'Ikke tilkoblet – sett opp i Innstillinger → Musikktjenester'}</span>
        <span style="font-size:12px;color:#c9c9c4;line-height:1.45;text-wrap:pretty">{why}</span>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button onClick={() => go('settings', 'tjenester')} style="align-self:flex-start;height:38px;padding:0 16px;border-radius:999px;border:none;background:#d9a441;color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer">Åpne Musikktjenester</button>
          {retry && <button onClick={retry} style="height:38px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;font-size:13px;cursor:pointer">Prøv igjen</button>}
        </div>
      </div>
    </div>
  );
}

function TrackRows({ list, meta, onPick }: { list: NdSong[]; meta?: (s: NdSong, i: number) => string; onPick: (i: number) => void }) {
  const cur = lsvc.value ? lq.value[li.value] : undefined;
  return (
    <div style="display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;overflow:hidden;flex-shrink:0">
      {list.map((x, i) => (
        <button key={x.id + i} onClick={() => onPick(i)} style={`display:grid;grid-template-columns:42px minmax(0,1fr) auto;gap:10px;align-items:center;min-height:58px;padding:0 12px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:transparent;cursor:pointer;text-align:left;width:100%`}>
          <div style={`width:42px;height:42px;border-radius:6px;background:${cover(x.coverArt, x.album, 120).bg}`} />
          <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style={`font-size:14px;color:${cur && cur.id === x.id ? '#f0c46a' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{x.title}</span><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.artist}{meta ? '' : ' · ' + x.album}</span></span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#8b8b86;white-space:nowrap">{meta ? meta(x, i) : fmtDur(x.duration)}</span>
        </button>
      ))}
    </div>
  );
}

interface Tile { key: string; name: string; meta: string; label: string; bg: string; ink: string; pick: () => void }
function Shelf({ kicker, title, tiles }: { kicker?: string; title: string; tiles: Tile[] }) {
  if (!tiles.length) return null;
  return (
    <div style="flex-shrink:0;display:flex;flex-direction:column;gap:10px">
      <div style="display:flex;flex-direction:column;gap:2px">{kicker && <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#8b8b86">{kicker}</span>}<span style="font-size:19px;font-weight:600">{title}</span></div>
      <div class="dsc" style="display:flex;gap:12px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px">
        {tiles.map((t) => (
          <button key={t.key} onClick={t.pick} style="display:flex;flex-direction:column;gap:5px;width:136px;flex-shrink:0;border:none;background:none;padding:0;cursor:pointer;text-align:left">
            <div style={`position:relative;width:100%;aspect-ratio:1;box-sizing:border-box;border-radius:10px;background:${t.bg};color:${t.ink};display:flex;align-items:flex-end;padding:10px 44px 10px 10px;font-size:14px;font-weight:600;line-height:1.05`}>{t.label}<div style="position:absolute;right:8px;bottom:8px;width:30px;height:30px;border-radius:50%;background:rgba(11,11,12,.72);display:flex;align-items:center;justify-content:center"><svg width="14" height="14" viewBox="0 0 24 24" fill="#f2f2ee"><path d={PLAY} /></svg></div></div>
            <span style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t.name}</span>
            <span style="font-size:11px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t.meta}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function OpenList({ lib }: { lib: LibId }) {
  const pl = libUi.pl.value!;
  const [songs, setSongs] = useState<NdSong[] | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { setSongs(null); setErr(''); collSongs(lib, pl.kind, pl.id).then(setSongs).catch((e: unknown) => setErr(e instanceof Error ? e.message : String(e))); }, [pl.id]);
  const list = songs ?? [];
  const c = cover(list[0]?.coverArt, pl.name, 300);
  const total = list.reduce((a, x) => a + x.duration, 0);
  const play = (l: NdSong[], i: number) => { playNd(l, i, lib); openFull(); };
  return (
    <>
      <div style="flex-shrink:0;display:grid;grid-template-columns:120px minmax(0,1fr);gap:14px;align-items:end">
        <div style={`width:120px;height:120px;border-radius:12px;background:${c.bg};display:flex;align-items:flex-end;padding:10px;box-sizing:border-box;color:${c.ink};font-size:15px;font-weight:600;line-height:1.05`}>{pl.name}</div>
        <div style="display:flex;flex-direction:column;gap:10px;min-width:0">
          <span style="display:flex;flex-direction:column;gap:3px"><span style="font-size:19px;font-weight:600;line-height:1.15">{pl.name}</span><span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#8b8b86">{songs ? list.length + ' låter' + (total ? ' · ' + Math.round(total / 60) + ' min' : '') : err || 'Henter …'}</span></span>
          <div style="display:flex;gap:8px">
            <button onClick={() => { if (list.length) play(list, 0); }} style="height:38px;padding:0 16px;border-radius:999px;border:none;background:#d9a441;color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer">Spill</button>
            <button onClick={() => { if (list.length) play([...list].sort(() => Math.random() - 0.5), 0); }} style="height:38px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;font-size:13px;cursor:pointer">Tilfeldig</button>
          </div>
        </div>
      </div>
      {list.length > 0 && <TrackRows list={list} onPick={(i) => play(list, i)} />}
      {lib && null}
    </>
  );
}

export function LibraryPage() {
  const lib = (route.value.cat === 'ytm' ? 'ytm' : 'nd') as LibId;
  const nd = lib === 'nd' && ndConfigured();
  const ytm = lib === 'ytm';
  const ndData = useNd(), ytmData = useYtm(ytm);
  const data = ytm ? ytmData : ndData;
  const tab = libUi.tab.value, open = libUi.pl.value, q = libUi.q.value.trim();
  const [res, setRes] = useState<NdSong[] | null>(null), [tagRes, setTagRes] = useState<NdSong[] | null>(null);
  useEffect(() => {
    if ((!nd && !ytm) || q.length < 2) { setRes(null); return undefined; }
    setRes(null);
    const t = setTimeout(() => { (ytm ? ytmSearch(q) : ndSearch(q)).then(setRes).catch(() => setRes([])); }, 350);
    return () => clearTimeout(t);
  }, [q, nd, ytm]);
  const tabs = LIB_TABS[lib];
  const h = hist.value[lib] ?? [];
  const play = (l: NdSong[], i: number) => { playNd(l, i, lib); openFull(); };
  const albumTile = (al: NdAlbum | NdPlaylist): Tile => { const pl = 'playlist' in al && !!al.playlist; const c = cover(al.coverArt, al.name); return { key: al.id, name: al.name, meta: pl ? 'Spilleliste' : 'artist' in al ? al.artist : '', label: '', bg: c.bg, ink: c.ink, pick: () => { libUi.pl.value = { kind: pl ? 'pl' : 'album', id: al.id, name: al.name }; } }; };
  const feat = (ytm ? data.pls : data.albums ?? []).slice(0, 5), fi = feat.length ? libUi.hero.value % feat.length : 0, f = feat[fi];
  const fKind = (f && 'playlist' in f && f.playlist) ? 'pl' as const : 'album' as const;
  const off = ytm ? !!data.err && !data.albums?.length && !data.pls.length : !nd && (!ndConfigured() || !!data.err);
  return (
    <>
      <button onClick={() => { if (!libBack()) go('home'); }} style="align-self:flex-start;display:flex;align-items:center;gap:4px;border:none;background:none;color:#d9a441;font-size:14px;cursor:pointer;padding:0;margin-top:-6px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg>{open ? tabs[tab] : 'Hjem'}</button>
      <input value={libUi.q.value} onInput={(e) => { libUi.q.value = e.currentTarget.value; }} placeholder="Søk etter sang, artist eller album" style="flex-shrink:0;height:44px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:#141415;font-size:15px;outline:none" />
      {nd && !open && <TagFilterBar onResults={setTagRes} />}
      {nd && !open && !q && !tagRes && <AskBox compact />}
      {!q && tagRes ? (
        tagRes.length ? <TrackRows list={tagRes} onPick={(i) => play(tagRes, i)} /> : <span style="font-size:13px;color:#8b8b86">Ingen låter med disse taggene ennå (se Innstillinger → Bibliotek)</span>
      ) : q ? (
        off ? <NotConnected lib={lib} err={data.err} retry={ytm ? data.retry : undefined} /> : <>
          {res && !res.length && <span style="font-size:13px;color:#8b8b86">Ingen treff</span>}
          {!res && <span style="font-size:13px;color:#8b8b86">Søker …</span>}
          {res && res.length > 0 && <TrackRows list={res} onPick={(i) => play(res, i)} />}
        </>
      ) : open && (nd || ytm) ? <OpenList lib={lib} /> : <>
        <div style="flex-shrink:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding:3px;border-radius:10px;background:#141415;border:1px solid #242426">
          {tabs.map((n, i) => <button key={n} onClick={() => { libUi.tab.value = i; libUi.pl.value = null; }} style={`height:36px;border-radius:8px;border:none;background:${tab === i ? '#2a2a2c' : 'transparent'};color:${tab === i ? '#f2f2ee' : '#8b8b86'};font-size:13px;font-weight:600;cursor:pointer`}>{n}</button>)}
        </div>
        {tab === 0 && (off ? <>
          <NotConnected lib={lib} err={data.err} retry={ytm ? data.retry : undefined} />
          {lib === 'ytm' && <div class="dsc" style="flex-shrink:0;display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px;opacity:.45;pointer-events:none">{MOODS.map((n) => <button key={n} style="flex-shrink:0;height:34px;padding:0 14px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;color:#f2f2ee;font-size:13px;white-space:nowrap">{n}</button>)}</div>}
        </> : <>
          {f ? (() => { const c = cover(f.coverArt, f.name, 400); return (
            <div style="position:relative;flex-shrink:0;border-radius:16px;overflow:hidden;background:#141415;border:1px solid #242426">
              <div style={`position:absolute;inset:-40px;background:${c.bg};filter:blur(40px);opacity:.5`} />
              <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,11,12,.35),rgba(11,11,12,.9))" />
              <div style="position:relative;display:flex;flex-direction:column;gap:14px;padding:16px">
                <div style="display:grid;grid-template-columns:112px minmax(0,1fr);gap:14px;align-items:end">
                  <button onClick={() => { libUi.pl.value = { kind: fKind, id: f.id, name: f.name }; }} style={`width:112px;height:112px;border-radius:10px;border:none;background:${c.bg};color:${c.ink};box-shadow:0 14px 30px rgba(0,0,0,.5);display:flex;align-items:flex-end;padding:10px;box-sizing:border-box;font-size:13px;font-weight:600;line-height:1.05;text-align:left;cursor:pointer`}>{c.ink === 'transparent' ? '' : f.name}</button>
                  <div style="display:flex;flex-direction:column;gap:6px;min-width:0">
                    <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#f0c46a">{ytm ? 'UTVALGT' : 'NYLIG LAGT TIL'}</span>
                    <span style="font-size:21px;font-weight:600;line-height:1.1">{f.name}</span>
                    <span style="font-size:12px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{'artist' in f ? f.artist : ''}</span>
                    <div style="display:flex;gap:5px;flex-wrap:wrap">{[f.songCount ? f.songCount + ' låter' : '', 'year' in f && f.year ? String(f.year) : '', f.duration ? Math.round(f.duration / 60) + ' min' : ''].filter(Boolean).map((t) => <span key={t} style="height:20px;padding:0 7px;border-radius:5px;background:rgba(255,255,255,.09);font-family:'IBM Plex Mono',monospace;font-size:9px;display:flex;align-items:center;white-space:nowrap">{t}</span>)}</div>
                  </div>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                  <button onClick={() => { void collSongs(lib, fKind, f.id).then((r) => { if (r.length) play(r, 0); }); }} style="height:38px;padding:0 16px;border-radius:999px;border:none;background:#d9a441;color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:6px"><svg width="12" height="12" viewBox="0 0 24 24" fill="#0b0b0c"><path d={PLAY} /></svg>Spill</button>
                  <button onClick={() => { void collSongs(lib, fKind, f.id).then((r) => { if (r.length) addToQueue(r, lib); }); }} style="height:38px;padding:0 14px;border-radius:999px;border:1px solid #3a3a37;background:rgba(11,11,12,.4);font-size:13px;cursor:pointer">Legg i kø</button>
                  <div style="margin-left:auto;display:flex;gap:4px">{feat.map((_, j) => <button key={j} aria-label={'Album ' + (j + 1)} onClick={() => { libUi.hero.value = j; }} style={`width:${j === fi ? 18 : 6}px;height:6px;border-radius:3px;border:none;padding:0;background:${j === fi ? '#d9a441' : '#3a3a37'};cursor:pointer`} />)}</div>
                </div>
              </div>
            </div>
          ); })() : <span style="font-size:13px;color:#8b8b86">{data.err || (data.albums ? 'Biblioteket er tomt.' : 'Henter biblioteket …')}</span>}
          {ytm ? <>
            <Shelf kicker="YOUTUBE MUSIC" title="Til deg" tiles={data.rnd.map(albumTile)} />
            <Shelf title="Spillelister" tiles={data.pls.filter((p) => 'playlist' in p && p.playlist).map(albumTile)} />
            <Shelf title="Album" tiles={(data.albums ?? []).map(albumTile)} />
          </> : <>
            <Shelf title="Nylig lagt til" tiles={(data.albums ?? []).map(albumTile)} />
            <Shelf title="Oppdag" tiles={data.rnd.map(albumTile)} />
            <Shelf kicker="FRA BIBLIOTEKET" title="Mest spilt" tiles={data.freq.map(albumTile)} />
          </>}
        </>)}
        {tab === 1 && (off ? <NotConnected lib={lib} err={data.err} retry={ytm ? data.retry : undefined} /> : (
          <div style="display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;overflow:hidden;flex-shrink:0">
            {data.pls.length === 0 && <span style="font-size:13px;color:#8b8b86;padding:16px">{ytm && !data.albums ? 'Henter biblioteket …' : 'Ingen spillelister på serveren.'}</span>}
            {data.pls.map((p, i) => (
              <button key={p.id} onClick={() => { libUi.pl.value = { kind: 'playlist' in p && p.playlist === false ? 'album' : 'pl', id: p.id, name: p.name }; }} style={`display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:12px;align-items:center;min-height:68px;padding:0 12px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:transparent;cursor:pointer;text-align:left;width:100%`}>
                <div style={`width:52px;height:52px;border-radius:8px;background:${cover(p.coverArt, p.name, 120).bg}`} />
                <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:15px">{p.name}</span><span style="font-size:12px;color:#8b8b86">{p.songCount ? p.songCount + ' låter' : 'artist' in p && p.artist ? p.artist : 'Spilleliste'}</span></span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7" /></svg>
              </button>
            ))}
          </div>
        ))}
        {tab === 2 && <>
          {!h.length && <span style="font-size:13px;color:#8b8b86">Ingen historikk ennå</span>}
          {h.length > 0 && <TrackRows list={h.map((x) => x.s)} meta={(_, i) => whenText(h[i]!.at)} onPick={(i) => { if (nd || ytm) play(h.map((x) => x.s), i); }} />}
          {h.length > 0 && <button onClick={() => clearHist(lib)} style="align-self:center;border:none;background:none;color:#8b8b86;font-size:13px;cursor:pointer;padding:6px">Tøm historikk</button>}
        </>}
      </>}
      {!q && !open && tab === 0 && <LydLenker />}
      {!q && !open && tab === 0 && <MediaLibSection />}
    </>
  );
}
export const libTitle = () => LIB_NAME[(route.value.cat === 'ytm' ? 'ytm' : 'nd') as LibId];
