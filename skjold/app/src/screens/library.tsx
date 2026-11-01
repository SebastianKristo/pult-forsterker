// Biblioteker (Skjold App v2 · tLib): YouTube Music og Navidrome. Malen er portert 1:1 fra designfilen.
// Navidrome er ekte (Subsonic-API direkte fra appen). YouTube Music krever Music Assistant, som ikke finnes ennå:
// da vises samme skall med en tydelig «ikke tilkoblet»-tilstand i stedet for eksempeldata.
import { useEffect, useState } from 'preact/hooks';
import { go, openFull, route } from '../lib/store';
import { art } from '../lib/settings';
import { addToQueue, clearHist, fmtDur, hist, li, LIB_NAME, LIB_TABS, lq, lsvc, playNd, whenText, type LibId } from '../lib/library';
import { ndAlbum, ndAlbumList, ndConfigured, ndCover, ndPlaylist, ndPlaylists, ndSearch, type NdAlbum, type NdPlaylist, type NdSong } from '../lib/navidrome';
import { signal } from '@preact/signals';

/** Tilstand per bibliotek-side (signaler, så tilbake-knappen og skjermbildeskriptet kan styre den). */
export const libUi = { tab: signal(0), pl: signal<{ kind: 'album' | 'pl'; id: string; name: string } | null>(null), q: signal(''), hero: signal(0), mood: signal<number | null>(null) };
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
  return { albums, rnd, freq, pls, err };
}

function NotConnected({ lib, err }: { lib: LibId; err?: string }) {
  const why = lib === 'ytm' ? 'YouTube Music spilles via Music Assistant, som ikke er koblet til forsterkeren ennå.' : err ? 'Fikk ikke kontakt med Navidrome: ' + err + '.' : 'Legg inn adressen til Navidrome-serveren, brukernavn og passord.';
  return (
    <div data-testid="lib-off" style="position:relative;flex-shrink:0;border-radius:16px;overflow:hidden;background:#141415;border:1px solid #242426">
      <div style="position:relative;display:flex;flex-direction:column;gap:10px;padding:16px">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#f0c46a">IKKE TILKOBLET</span>
        <span style="font-size:19px;font-weight:600;line-height:1.15">Ikke tilkoblet – sett opp i Innstillinger → Musikktjenester</span>
        <span style="font-size:12px;color:#c9c9c4;line-height:1.45;text-wrap:pretty">{why}</span>
        <button onClick={() => go('settings', 'tjenester')} style="align-self:flex-start;height:38px;padding:0 16px;border-radius:999px;border:none;background:#d9a441;color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer">Åpne Musikktjenester</button>
      </div>
    </div>
  );
}

function TrackRows({ list, meta, onPick }: { list: NdSong[]; meta?: (s: NdSong, i: number) => string; onPick: (i: number) => void }) {
  const cur = lsvc.value === 'nd' ? lq.value[li.value] : undefined;
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
  useEffect(() => { setSongs(null); (pl.kind === 'album' ? ndAlbum(pl.id).then((r) => r.songs) : ndPlaylist(pl.id)).then(setSongs).catch((e: unknown) => setErr(e instanceof Error ? e.message : String(e))); }, [pl.id]);
  const list = songs ?? [];
  const c = cover(list[0]?.coverArt, pl.name, 300);
  const total = list.reduce((a, x) => a + x.duration, 0);
  const play = (l: NdSong[], i: number) => { playNd(l, i); openFull(); };
  return (
    <>
      <div style="flex-shrink:0;display:grid;grid-template-columns:120px minmax(0,1fr);gap:14px;align-items:end">
        <div style={`width:120px;height:120px;border-radius:12px;background:${c.bg};display:flex;align-items:flex-end;padding:10px;box-sizing:border-box;color:${c.ink};font-size:15px;font-weight:600;line-height:1.05`}>{pl.name}</div>
        <div style="display:flex;flex-direction:column;gap:10px;min-width:0">
          <span style="display:flex;flex-direction:column;gap:3px"><span style="font-size:19px;font-weight:600;line-height:1.15">{pl.name}</span><span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#8b8b86">{songs ? list.length + ' låter · ' + Math.round(total / 60) + ' min' : err || 'Henter …'}</span></span>
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
  const data = useNd();
  const tab = libUi.tab.value, open = libUi.pl.value, q = libUi.q.value.trim();
  const [res, setRes] = useState<NdSong[] | null>(null);
  useEffect(() => {
    if (!nd || q.length < 2) { setRes(null); return undefined; }
    const t = setTimeout(() => { ndSearch(q).then(setRes).catch(() => setRes([])); }, 350);
    return () => clearTimeout(t);
  }, [q, nd]);
  const tabs = LIB_TABS[lib];
  const h = hist.value[lib] ?? [];
  const play = (l: NdSong[], i: number) => { playNd(l, i); openFull(); };
  const albumTile = (al: NdAlbum): Tile => { const c = cover(al.coverArt, al.name); return { key: al.id, name: al.name, meta: al.artist, label: '', bg: c.bg, ink: c.ink, pick: () => { libUi.pl.value = { kind: 'album', id: al.id, name: al.name }; } }; };
  const feat = (data.albums ?? []).slice(0, 5), fi = feat.length ? libUi.hero.value % feat.length : 0, f = feat[fi];
  const off = !nd && (lib === 'ytm' || !ndConfigured() || !!data.err);
  return (
    <>
      <button onClick={() => { if (!libBack()) go('home'); }} style="align-self:flex-start;display:flex;align-items:center;gap:4px;border:none;background:none;color:#d9a441;font-size:14px;cursor:pointer;padding:0;margin-top:-6px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg>{open ? tabs[tab] : 'Hjem'}</button>
      <input value={libUi.q.value} onInput={(e) => { libUi.q.value = e.currentTarget.value; }} placeholder="Søk etter sang, artist eller album" style="flex-shrink:0;height:44px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:#141415;font-size:15px;outline:none" />
      {q ? (
        off ? <NotConnected lib={lib} err={data.err} /> : <>
          {res && !res.length && <span style="font-size:13px;color:#8b8b86">Ingen treff</span>}
          {!res && <span style="font-size:13px;color:#8b8b86">Søker …</span>}
          {res && res.length > 0 && <TrackRows list={res} onPick={(i) => play(res, i)} />}
        </>
      ) : open && nd ? <OpenList lib={lib} /> : <>
        <div style="flex-shrink:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px;padding:3px;border-radius:10px;background:#141415;border:1px solid #242426">
          {tabs.map((n, i) => <button key={n} onClick={() => { libUi.tab.value = i; libUi.pl.value = null; }} style={`height:36px;border-radius:8px;border:none;background:${tab === i ? '#2a2a2c' : 'transparent'};color:${tab === i ? '#f2f2ee' : '#8b8b86'};font-size:13px;font-weight:600;cursor:pointer`}>{n}</button>)}
        </div>
        {tab === 0 && (off ? <>
          <NotConnected lib={lib} err={data.err} />
          {lib === 'ytm' && <div class="dsc" style="flex-shrink:0;display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px;opacity:.45;pointer-events:none">{MOODS.map((n) => <button key={n} style="flex-shrink:0;height:34px;padding:0 14px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;color:#f2f2ee;font-size:13px;white-space:nowrap">{n}</button>)}</div>}
        </> : <>
          {f ? (() => { const c = cover(f.coverArt, f.name, 400); return (
            <div style="position:relative;flex-shrink:0;border-radius:16px;overflow:hidden;background:#141415;border:1px solid #242426">
              <div style={`position:absolute;inset:-40px;background:${c.bg};filter:blur(40px);opacity:.5`} />
              <div style="position:absolute;inset:0;background:linear-gradient(180deg,rgba(11,11,12,.35),rgba(11,11,12,.9))" />
              <div style="position:relative;display:flex;flex-direction:column;gap:14px;padding:16px">
                <div style="display:grid;grid-template-columns:112px minmax(0,1fr);gap:14px;align-items:end">
                  <button onClick={() => { libUi.pl.value = { kind: 'album', id: f.id, name: f.name }; }} style={`width:112px;height:112px;border-radius:10px;border:none;background:${c.bg};color:${c.ink};box-shadow:0 14px 30px rgba(0,0,0,.5);display:flex;align-items:flex-end;padding:10px;box-sizing:border-box;font-size:13px;font-weight:600;line-height:1.05;text-align:left;cursor:pointer`}>{c.ink === 'transparent' ? '' : f.name}</button>
                  <div style="display:flex;flex-direction:column;gap:6px;min-width:0">
                    <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#f0c46a">NYLIG LAGT TIL</span>
                    <span style="font-size:21px;font-weight:600;line-height:1.1">{f.name}</span>
                    <span style="font-size:12px;color:#c9c9c4;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{f.artist}</span>
                    <div style="display:flex;gap:5px;flex-wrap:wrap">{[f.songCount + ' låter', f.year ? String(f.year) : '', Math.round(f.duration / 60) + ' min'].filter(Boolean).map((t) => <span key={t} style="height:20px;padding:0 7px;border-radius:5px;background:rgba(255,255,255,.09);font-family:'IBM Plex Mono',monospace;font-size:9px;display:flex;align-items:center;white-space:nowrap">{t}</span>)}</div>
                  </div>
                </div>
                <div style="display:flex;gap:8px;align-items:center">
                  <button onClick={() => { void ndAlbum(f.id).then((r) => play(r.songs, 0)); }} style="height:38px;padding:0 16px;border-radius:999px;border:none;background:#d9a441;color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer;display:flex;align-items:center;gap:6px"><svg width="12" height="12" viewBox="0 0 24 24" fill="#0b0b0c"><path d={PLAY} /></svg>Spill</button>
                  <button onClick={() => { void ndAlbum(f.id).then((r) => addToQueue(r.songs)); }} style="height:38px;padding:0 14px;border-radius:999px;border:1px solid #3a3a37;background:rgba(11,11,12,.4);font-size:13px;cursor:pointer">Legg i kø</button>
                  <div style="margin-left:auto;display:flex;gap:4px">{feat.map((_, j) => <button key={j} aria-label={'Album ' + (j + 1)} onClick={() => { libUi.hero.value = j; }} style={`width:${j === fi ? 18 : 6}px;height:6px;border-radius:3px;border:none;padding:0;background:${j === fi ? '#d9a441' : '#3a3a37'};cursor:pointer`} />)}</div>
                </div>
              </div>
            </div>
          ); })() : <span style="font-size:13px;color:#8b8b86">{data.albums ? 'Biblioteket er tomt.' : 'Henter biblioteket …'}</span>}
          <Shelf title="Nylig lagt til" tiles={(data.albums ?? []).map(albumTile)} />
          <Shelf title="Oppdag" tiles={data.rnd.map(albumTile)} />
          <Shelf kicker="FRA BIBLIOTEKET" title="Mest spilt" tiles={data.freq.map(albumTile)} />
        </>)}
        {tab === 1 && (off ? <NotConnected lib={lib} err={data.err} /> : (
          <div style="display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;overflow:hidden;flex-shrink:0">
            {data.pls.length === 0 && <span style="font-size:13px;color:#8b8b86;padding:16px">Ingen spillelister på serveren.</span>}
            {data.pls.map((p, i) => (
              <button key={p.id} onClick={() => { libUi.pl.value = { kind: 'pl', id: p.id, name: p.name }; }} style={`display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:12px;align-items:center;min-height:68px;padding:0 12px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:transparent;cursor:pointer;text-align:left;width:100%`}>
                <div style={`width:52px;height:52px;border-radius:8px;background:${cover(p.coverArt, p.name, 120).bg}`} />
                <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:15px">{p.name}</span><span style="font-size:12px;color:#8b8b86">{p.songCount} låter</span></span>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7" /></svg>
              </button>
            ))}
          </div>
        ))}
        {tab === 2 && <>
          {!h.length && <span style="font-size:13px;color:#8b8b86">Ingen historikk ennå</span>}
          {h.length > 0 && <TrackRows list={h.map((x) => x.s)} meta={(_, i) => whenText(h[i]!.at)} onPick={(i) => { if (nd) play(h.map((x) => x.s), i); }} />}
          {h.length > 0 && <button onClick={() => clearHist(lib)} style="align-self:center;border:none;background:none;color:#8b8b86;font-size:13px;cursor:pointer;padding:6px">Tøm historikk</button>}
        </>}
      </>}
    </>
  );
}
export const libTitle = () => LIB_NAME[(route.value.cat === 'ytm' ? 'ytm' : 'nd') as LibId];
