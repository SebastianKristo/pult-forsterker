// Plex og Jellyfin som musikkilder (daemonen: /api/medialib, pi/skjold_medialib.py). Oppsett + bla, søk og spill.
import { useEffect, useState } from 'preact/hooks';
import { apiPost, apiReq } from '../lib/api';

type Kind = 'plex' | 'jellyfin';
interface Conf { configured: boolean; url: string }
interface Album { id: string; name: string; artist: string; year?: number; cover: string; songCount?: number }
interface Track { id: string; title: string; artist: string; album: string; duration: number; cover: string; url: string }
interface Playlist { id: string; name: string; songCount: number; cover: string }

const A = '#d9a441';
const card = 'display:flex;flex-direction:column;gap:12px;padding:16px;border-radius:14px;background:#141415;border:1px solid #242426';
const muted = 'font-size:12px;color:#8f8f8a;line-height:1.45';
const inp = 'height:36px;padding:0 12px;border-radius:8px;border:1px solid #2e2e30;background:#0f0f10;color:#f2f2ee;font-size:14px;outline:none;min-width:0';
const btn = (on = false) => `height:34px;padding:0 12px;border-radius:8px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#2a2112' : '#1b1b1c'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:13px;cursor:pointer;white-space:nowrap`;
const NAVN: Record<Kind, string> = { plex: 'Plex', jellyfin: 'Jellyfin' };
const HJELP: Record<Kind, string> = {
  plex: 'Adresse som http://plex.local:32400 og X-Plex-Token (Plex Web → et spor → ⋯ → Hent info → Vis XML: token står i adressen).',
  jellyfin: 'Adresse som http://jellyfin.local:8096 og en API-nøkkel (Dashbord → API-nøkler → +).',
};
const err = (e: unknown): string => (e instanceof Error ? e.message : String(e));

function Setup({ kind, conf, onSaved }: { kind: Kind; conf: Conf; onSaved: (c: Record<Kind, Conf>) => void }) {
  const [url, setUrl] = useState(conf.url), [tok, setTok] = useState(''), [msg, setMsg] = useState('');
  const save = async () => {
    try { onSaved(await apiPost<Record<Kind, Conf>>('/api/medialib', { kind, url, token: tok })); setTok(''); setMsg('Lagret – tester …');
      const t = await apiPost<{ ok: boolean; server?: string; error?: string }>(`/api/medialib/${kind}/test`, {});
      setMsg(t.ok ? `Tilkoblet ${t.server ?? ''}` : t.error ?? 'Feil'); } catch (e) { setMsg(err(e)); }
  };
  return (
    <div style="display:flex;flex-direction:column;gap:8px">
      <span style={muted}>{HJELP[kind]}</span>
      <input value={url} onInput={(e) => setUrl(e.currentTarget.value)} placeholder="Adresse" style={inp} aria-label={`${NAVN[kind]}-adresse`} />
      <input type="password" value={tok} onInput={(e) => setTok(e.currentTarget.value)} placeholder={conf.configured ? 'Lagret (skriv for å bytte)' : kind === 'plex' ? 'X-Plex-Token' : 'API-nøkkel'} style={inp} aria-label={`${NAVN[kind]}-nøkkel`} />
      <div style="display:flex;gap:8px;align-items:center"><button onClick={() => void save()} style={btn(true)}>Lagre og test</button>{msg && <span style={muted}>{msg}</span>}</div>
    </div>
  );
}

function AlbumTile({ a, onPlay }: { a: Album; onPlay: () => void }) {
  return (
    <button onClick={onPlay} style="display:flex;flex-direction:column;gap:6px;width:132px;flex-shrink:0;background:none;border:none;padding:0;text-align:left;color:#f2f2ee;cursor:pointer">
      <div style={`width:132px;height:132px;border-radius:10px;background:#1b1b1c ${a.cover ? `url("${a.cover}") center/cover` : ''}`} />
      <span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{a.name}</span>
      <span style="font-size:12px;color:#8f8f8a;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{a.artist}</span>
    </button>
  );
}

/** Bibliotek-seksjon for Plex og Jellyfin: oppsett når det mangler, ellers nye album, spillelister og søk. */
export function MediaLibSection() {
  const [conf, setConf] = useState<Record<Kind, Conf> | null>(null), [kind, setKind] = useState<Kind>('plex');
  const [albums, setAlbums] = useState<Album[]>([]), [pls, setPls] = useState<Playlist[]>([]), [q, setQ] = useState('');
  const [hits, setHits] = useState<{ albums: Album[]; tracks: Track[] } | null>(null), [msg, setMsg] = useState(''), [setup, setSetup] = useState(false);
  useEffect(() => { apiReq<Record<Kind, Conf>>('/api/medialib').then((c) => { setConf(c); if (!c.plex.configured && c.jellyfin.configured) setKind('jellyfin'); }).catch(() => setConf(null)); }, []);
  const ok = !!conf?.[kind]?.configured;
  useEffect(() => {
    setAlbums([]); setPls([]); setHits(null); setMsg('');
    if (!ok) return;
    apiReq<Album[]>(`/api/medialib/${kind}/albums?type=newest`).then(setAlbums).catch((e) => setMsg(err(e)));
    apiReq<Playlist[]>(`/api/medialib/${kind}/playlists`).then(setPls).catch(() => setPls([]));
  }, [kind, ok]);
  const play = async (b: Record<string, unknown>) => {
    try { const r = await apiPost<{ playing?: string; error?: string }>(`/api/medialib/${kind}/play`, b); setMsg(r.playing ? `Spiller ${r.playing}` : r.error ?? ''); } catch (e) { setMsg(err(e)); }
  };
  const search = async () => { if (!q.trim()) return; try { setHits(await apiReq(`/api/medialib/${kind}/search?q=${encodeURIComponent(q)}`)); } catch (e) { setMsg(err(e)); } };
  if (!conf) return null;
  return (
    <div style={card}>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap">
        <span style="font-size:16px;font-weight:600">Plex og Jellyfin</span>
        <div style="display:flex;gap:6px">
          {(['plex', 'jellyfin'] as Kind[]).map((k) => <button key={k} onClick={() => { setKind(k); setSetup(false); }} style={btn(kind === k)}>{NAVN[k]}{conf[k].configured ? '' : ' ·'}</button>)}
          {ok && <button onClick={() => setSetup(!setup)} style={btn(setup)}>Oppsett</button>}
        </div>
      </div>
      {(!ok || setup) && <Setup kind={kind} conf={conf[kind]} onSaved={(c) => { setConf(c); setSetup(false); }} />}
      {ok && !setup && <>
        <div style="display:flex;gap:8px"><input value={q} onInput={(e) => setQ(e.currentTarget.value)} onKeyDown={(e) => e.key === 'Enter' && void search()} placeholder={`Søk i ${NAVN[kind]}`} style={inp + ';flex:1'} aria-label={`Søk i ${NAVN[kind]}`} /><button onClick={() => void search()} style={btn()}>Søk</button></div>
        {hits && <div style="display:flex;flex-direction:column;gap:8px">
          {hits.albums.length > 0 && <div style="display:flex;gap:12px;overflow-x:auto;padding-bottom:4px">{hits.albums.map((a) => <AlbumTile key={a.id} a={a} onPlay={() => void play({ album: a.id })} />)}</div>}
          {hits.tracks.slice(0, 12).map((t, i) => (
            <button key={t.id} onClick={() => void play({ tracks: hits.tracks, start: i })} style="display:flex;gap:10px;align-items:center;background:none;border:none;border-top:1px solid #242426;padding:8px 0;color:#f2f2ee;text-align:left;cursor:pointer">
              <span style={`width:36px;height:36px;border-radius:6px;flex-shrink:0;background:#1b1b1c ${t.cover ? `url("${t.cover}") center/cover` : ''}`} />
              <span style="display:flex;flex-direction:column;min-width:0"><b style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t.title}</b><span style="font-size:12px;color:#8f8f8a">{t.artist} · {t.album}</span></span>
            </button>))}
          {!hits.albums.length && !hits.tracks.length && <span style={muted}>Ingen treff.</span>}
        </div>}
        {!hits && <>
          <span style="font-size:13px;font-weight:600">Nylig lagt til</span>
          <div style="display:flex;gap:12px;overflow-x:auto;padding-bottom:4px">{albums.map((a) => <AlbumTile key={a.id} a={a} onPlay={() => void play({ album: a.id })} />)}{!albums.length && <span style={muted}>Henter …</span>}</div>
          {pls.length > 0 && <><span style="font-size:13px;font-weight:600">Spillelister</span>
            <div style="display:flex;gap:6px;flex-wrap:wrap">{pls.map((p) => <button key={p.id} onClick={() => void play({ playlist: p.id })} style={btn()}>{p.name}</button>)}</div></>}
        </>}
      </>}
      {msg && <span style={muted}>{msg}</span>}
    </div>
  );
}
