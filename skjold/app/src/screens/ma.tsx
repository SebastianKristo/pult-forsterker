// Music Assistant som kilde: ett bibliotek for TIDAL, Qobuz, Deezer, Spotify, YouTube Music, Plex, Jellyfin og
// podkaster. Daemonen snakker med MA (/api/ma/*) og ber MA spille på denne Skjold-en.
import { signal } from '@preact/signals';
import { useEffect, useState } from 'preact/hooks';
import { api, type MaItem, type MaSearch } from '../lib/api';
import { go, settings, showToast, trackSub } from '../lib/store';
import { art } from '../lib/settings';

const MONO = "'IBM Plex Mono',monospace";
const TABS: [string, string][] = [['recent', 'Utforsk'], ['albums', 'Album'], ['artists', 'Artister'], ['playlists', 'Spillelister'], ['podcasts', 'Podkaster']];
const maTab = signal(0);
const maOpen = signal<MaItem | null>(null);
trackSub(maOpen, () => { maOpen.value = null; });
const maQ = signal('');

export const maConfigured = (): boolean => !!(settings.value.maUrl || '').trim();

/** Leverandørens merkefarge (liten pille på flisene). */
const PCOL: Record<string, string> = { TIDAL: '#e8e8e8', Qobuz: '#4aa8e8', Deezer: '#a238ff', Spotify: '#1ed760', 'YouTube Music': '#ff3b30', Plex: '#e5a00d', Jellyfin: '#aa5cc3', Navidrome: '#4a90e2', Podkast: '#c89cff' };

function Badge({ p }: { p: string }) {
  if (!p) return null;
  return <span style={`font-family:${MONO};font-size:9.5px;letter-spacing:.06em;padding:2px 6px;border-radius:999px;border:1px solid ${PCOL[p] ?? '#3a3a37'};color:${PCOL[p] ?? '#a9a9a3'};white-space:nowrap`}>{p.toUpperCase()}</span>;
}

function Cover({ it, size, round }: { it: MaItem; size: number; round?: boolean }) {
  const a = art(it.name, it.image);
  return <div style={{ width: size + 'px', height: size + 'px', borderRadius: round ? '50%' : '12px', background: a.bg, flexShrink: 0, display: 'grid', placeItems: 'center', color: a.ink, fontWeight: 600, fontSize: Math.round(size / 4) + 'px' }}>{a.logo ? '' : (it.name || '?').slice(0, 1)}</div>;
}

async function play(it: MaItem, enqueue: 'play' | 'next' | 'add' = 'play') {
  try { await api.maPlay(it.uri, enqueue); showToast(enqueue === 'play' ? 'Spiller ' + it.name : enqueue === 'next' ? 'Spilles neste' : 'Lagt i køen'); }
  catch (e) { showToast(e instanceof Error ? e.message : String(e)); }
}

function Tile({ it, onOpen }: { it: MaItem; onOpen: () => void }) {
  const round = it.kind === 'artist';
  return (
    <button onClick={onOpen} style="display:flex;flex-direction:column;gap:6px;border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;min-width:0">
      <Cover it={it} size={148} round={round} />
      <span style="font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:148px">{it.name}</span>
      <span style="display:flex;gap:6px;align-items:center;max-width:148px;min-width:0"><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{it.artist || (it.kind === 'artist' ? 'Artist' : '')}</span><Badge p={it.provider} /></span>
    </button>
  );
}

function Row({ it, n }: { it: MaItem; n?: number }) {
  const mm = it.duration ? Math.floor(it.duration / 60) + ':' + String(Math.round(it.duration % 60)).padStart(2, '0') : '';
  return (
    <div style="display:grid;grid-template-columns:28px 40px minmax(0,1fr) auto auto;gap:12px;align-items:center;padding:6px 8px;border-radius:10px">
      <span style={`font-family:${MONO};font-size:12px;color:#6a6a65;text-align:right`}>{n ?? ''}</span>
      <Cover it={it} size={40} />
      <button onClick={() => void play(it)} style="border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;min-width:0;display:flex;flex-direction:column;gap:2px">
        <span style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{it.name}</span>
        <span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{[it.artist, it.album].filter(Boolean).join(' · ')}</span>
      </button>
      <span style={`font-family:${MONO};font-size:12px;color:#8b8b86`}>{mm}</span>
      <span style="display:flex;gap:4px">
        <button title="Spill neste" onClick={() => void play(it, 'next')} style="width:30px;height:30px;border-radius:8px;border:1px solid #2e2e30;background:transparent;color:#c9c9c4;cursor:pointer">↪</button>
        <button title="Legg i køen" onClick={() => void play(it, 'add')} style="width:30px;height:30px;border-radius:8px;border:1px solid #2e2e30;background:transparent;color:#c9c9c4;cursor:pointer">+</button>
      </span>
    </div>
  );
}

function Detail({ it }: { it: MaItem }) {
  const [d, setD] = useState<{ item: MaItem; tracks: MaItem[] } | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { setD(null); setErr(''); api.maTracks(it.uri).then(setD).catch((e) => setErr(e instanceof Error ? e.message : String(e))); }, [it.uri]);
  const head = d?.item?.name ? d.item : it;
  return (
    <div class="col gap16">
      <button onClick={() => (maOpen.value = null)} style="align-self:flex-start;border:none;background:none;color:#d9a441;cursor:pointer;padding:0;font-size:13px">‹ Tilbake</button>
      <div style="display:flex;gap:20px;align-items:flex-end;flex-wrap:wrap">
        <Cover it={head} size={180} round={head.kind === 'artist'} />
        <div class="col gap6" style={{ minWidth: 0 }}>
          <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.12em;color:#8b8b86`}>{({ album: 'ALBUM', playlist: 'SPILLELISTE', artist: 'ARTIST', podcast: 'PODKAST' } as Record<string, string>)[head.kind] ?? head.kind.toUpperCase()}</span>
          <span style="font-size:28px;font-weight:600;line-height:1.15">{head.name}</span>
          <span style="display:flex;gap:8px;align-items:center;color:#a9a9a3;font-size:13px">{head.artist}<Badge p={head.provider} /></span>
          <div class="row gap10" style={{ marginTop: '6px' }}>
            <button onClick={() => void play(head)} style="height:40px;padding:0 18px;border-radius:999px;border:none;background:#f2f2ee;color:#0b0b0c;font-weight:600;cursor:pointer">Spill</button>
            <button onClick={() => void play(head, 'add')} style="height:40px;padding:0 16px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;cursor:pointer">Legg i køen</button>
          </div>
        </div>
      </div>
      {err && <span style="color:#ff8a7a;font-size:13px">{err}</span>}
      {!d && !err && <span style="color:#8b8b86;font-size:13px">Henter …</span>}
      {d && <div class="col">{d.tracks.map((t, i) => <Row key={t.uri + i} it={t} n={i + 1} />)}</div>}
      {d && !d.tracks.length && <span style="color:#8b8b86;font-size:13px">Ingen låter å vise.</span>}
    </div>
  );
}

function NotConfigured() {
  return (
    <div style="display:flex;flex-direction:column;gap:12px;padding:20px;border-radius:16px;border:1px solid #242426;background:#121214;max-width:560px">
      <span style="font-size:16px;font-weight:600">Music Assistant er ikke koblet til</span>
      <span style="font-size:13px;color:#a9a9a3;line-height:1.55">Music Assistant samler TIDAL, Qobuz, Deezer, Spotify, YouTube Music, Plex, Jellyfin og podkaster i ett bibliotek. Kjør Music Assistant (for eksempel som Home Assistant-tillegg), og legg inn adressen under Integrasjoner. Skjold må være lagt til som spiller i Music Assistant (Squeezelite-, AirPlay- eller DLNA-provideren).</span>
      <button onClick={() => go('int')} style="align-self:flex-start;height:40px;padding:0 16px;border-radius:10px;border:none;background:#d9a441;color:#0b0b0c;font-weight:600;cursor:pointer">Gå til Integrasjoner</button>
    </div>
  );
}

/** Bibliotekside. provider: vis bare elementer fra én leverandør (brukes av YouTube Music-fanen). */
export function MaPage({ provider }: { provider?: string }) {
  const [items, setItems] = useState<MaItem[] | null>(null);
  const [res, setRes] = useState<MaSearch | null>(null);
  const [err, setErr] = useState('');
  const tab = TABS[maTab.value]![0], q = maQ.value.trim();
  const ok = maConfigured();
  useEffect(() => {
    if (!ok || q) return;
    setItems(null); setErr('');
    const p = tab === 'recent' ? api.maRecent().then((r) => r.items) : api.maLibrary(tab);
    p.then(setItems).catch((e) => setErr(e instanceof Error ? e.message : String(e)));
  }, [tab, ok, q]);
  useEffect(() => {
    if (!ok || !q) { setRes(null); return; }
    const t = setTimeout(() => { api.maSearch(q).then(setRes).catch((e) => setErr(e instanceof Error ? e.message : String(e))); }, 350);
    return () => clearTimeout(t);
  }, [q, ok]);
  if (!ok) return <NotConfigured />;
  if (maOpen.value) return <Detail it={maOpen.value} />;
  const keep = (x: MaItem) => !provider || x.provider === provider;
  const grid = (list: MaItem[]) => <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));gap:18px 16px">{list.filter(keep).map((it) => <Tile key={it.uri} it={it} onOpen={() => (it.kind === 'track' || it.kind === 'radio' ? void play(it) : (maOpen.value = it))} />)}</div>;
  return (
    <div class="col gap16">
      <div class="row gap10" style={{ flexWrap: 'wrap', alignItems: 'center' }}>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          {TABS.map(([, n], i) => <button key={n} onClick={() => { maTab.value = i; maQ.value = ''; }} style={`height:36px;padding:0 14px;border-radius:999px;border:1px solid ${i === maTab.value && !q ? '#f2f2ee' : '#2e2e30'};background:${i === maTab.value && !q ? '#f2f2ee' : 'transparent'};color:${i === maTab.value && !q ? '#0b0b0c' : '#c9c9c4'};font-size:13px;cursor:pointer`}>{n}</button>)}
        </div>
        <input value={maQ.value} onInput={(e) => (maQ.value = (e.currentTarget as HTMLInputElement).value)} placeholder={provider ? 'Søk i ' + provider : 'Søk i alle tjenestene'} style="margin-left:auto;height:38px;width:260px;max-width:100%;padding:0 14px;border-radius:10px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;font-size:14px;outline:none" />
      </div>
      {err && <span style="color:#ff8a7a;font-size:13px">{err}</span>}
      {q ? (res ? (
        <div class="col gap20">
          {res.tracks.filter(keep).length > 0 && <div class="col gap6"><span style="font-size:17px;font-weight:600">Låter</span>{res.tracks.filter(keep).slice(0, 10).map((t, i) => <Row key={t.uri + i} it={t} />)}</div>}
          {(['albums', 'artists', 'playlists', 'podcasts', 'radio'] as const).map((k) => res[k].filter(keep).length > 0 && (
            <div key={k} class="col gap10"><span style="font-size:17px;font-weight:600">{({ albums: 'Album', artists: 'Artister', playlists: 'Spillelister', podcasts: 'Podkaster', radio: 'Radio' } as Record<string, string>)[k]}</span>{grid(res[k].slice(0, 12))}</div>
          ))}
        </div>
      ) : <span style="color:#8b8b86;font-size:13px">Søker …</span>) : items ? (items.filter(keep).length ? grid(items) : <span style="color:#8b8b86;font-size:13px">Ingenting her ennå.</span>) : !err && <span style="color:#8b8b86;font-size:13px">Henter …</span>}
    </div>
  );
}
