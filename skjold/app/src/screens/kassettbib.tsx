/** Kassett: bla i hele Navidrome-biblioteket og velg en artist, et album eller én låt til kassetten. */
import { useEffect, useRef, useState } from 'preact/hooks';
import type { NfcHandling } from '../lib/api';
import { ndAlbum, ndAlbumsAlpha, ndArtist, ndArtists, ndConfigured, ndCover, ndSearch, type NdAlbum, type NdArtist, type NdSong } from '../lib/navidrome';

export interface BibValg { navn: string; undertittel: string; omslag: string; handling: NfcHandling; verdi: unknown }

const A = '#e8b04a';
const inp = 'background:#0e0e0f;border:1px solid #2a2a2c;border-radius:8px;color:#f2f2ee;padding:8px 10px;font:inherit';
const chip = (on = false) => `padding:7px 13px;border-radius:999px;border:1px solid ${on ? A : '#2a2a2c'};background:${on ? '#1c170d' : '#1a1a1b'};color:#f2f2ee;cursor:pointer;font:inherit;font-size:13px`;
const rad = (on = false) => `display:flex;gap:10px;align-items:center;width:100%;text-align:left;padding:7px 10px;border-radius:10px;border:1px solid ${on ? A : 'transparent'};background:${on ? '#1c170d' : 'transparent'};color:#f2f2ee;cursor:pointer;font:inherit`;
const liste = 'max-height:min(460px,55vh);overflow:auto;display:flex;flex-direction:column;gap:2px;padding-right:4px;overscroll-behavior:contain';
const tid = (s: number) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;
const forbokstav = (n: string) => { const c = n.replace(/^(the|de|den|det)\s+/i, '').charAt(0).toUpperCase(); return /[A-ZÆØÅ]/.test(c) ? c : '#'; };

function Cv({ id, size = 44, round = false }: { id?: string; size?: number; round?: boolean }) {
  const u = ndCover(id, 120);
  return u ? <img src={u} loading="lazy" style={`width:${size}px;height:${size}px;border-radius:${round ? '50%' : '6px'};object-fit:cover;flex-shrink:0;background:#222`} />
    : <span style={`width:${size}px;height:${size}px;border-radius:${round ? '50%' : '6px'};background:#222;flex-shrink:0`} />;
}

type Vis = { t: 'artister' } | { t: 'album' } | { t: 'artist'; a: NdArtist } | { t: 'albumet'; al: NdAlbum; fra?: NdArtist };

export function KassettBibliotek({ valgt, onVelg }: { valgt: BibValg | null; onVelg: (v: BibValg) => void }) {
  const [vis, setVis] = useState<Vis>({ t: 'artister' });
  const [q, setQ] = useState('');
  const [artister, setArtister] = useState<NdArtist[] | null>(null);
  const [alleAlbum, setAlleAlbum] = useState<NdAlbum[]>([]);
  const [merAlbum, setMerAlbum] = useState(true);
  const [artistAlbum, setArtistAlbum] = useState<NdAlbum[] | null>(null);
  const [sanger, setSanger] = useState<NdSong[] | null>(null);
  const [treff, setTreff] = useState<NdSong[]>([]);
  const [feil, setFeil] = useState('');
  const listeRef = useRef<HTMLDivElement>(null);
  const laster = useRef(false);

  const hent = <T,>(p: Promise<T>, ok: (v: T) => void) => { setFeil(''); p.then(ok).catch((e) => setFeil(String((e as Error).message || e))); };
  useEffect(() => { if (ndConfigured()) hent(ndArtists(), setArtister); }, []);
  useEffect(() => { if (vis.t === 'album' && !alleAlbum.length) merAlbumNa(); }, [vis.t]);
  useEffect(() => { if (vis.t === 'artist') { setArtistAlbum(null); hent(ndArtist(vis.a.id), (r) => setArtistAlbum(r.albums)); } }, [vis.t === 'artist' ? vis.a.id : '']);
  useEffect(() => { if (vis.t === 'albumet') { setSanger(null); hent(ndAlbum(vis.al.id), (r) => setSanger(r.songs)); } }, [vis.t === 'albumet' ? vis.al.id : '']);
  useEffect(() => { listeRef.current?.scrollTo(0, 0); }, [vis]);
  useEffect(() => {
    if (q.trim().length < 2) { setTreff([]); return; }
    const t = setTimeout(() => ndSearch(q.trim()).then(setTreff).catch(() => setTreff([])), 350);
    return () => clearTimeout(t);
  }, [q]);

  function merAlbumNa() {
    if (laster.current || !merAlbum) return;
    laster.current = true;
    ndAlbumsAlpha(alleAlbum.length).then((r) => { setAlleAlbum((x) => [...x, ...r]); if (r.length < 120) setMerAlbum(false); })
      .catch((e) => setFeil(String((e as Error).message || e))).finally(() => { laster.current = false; });
  }
  const onScroll = (e: Event) => { const el = e.currentTarget as HTMLDivElement; if (vis.t === 'album' && el.scrollTop + el.clientHeight > el.scrollHeight - 300) merAlbumNa(); };

  if (!ndConfigured()) return <small style="color:#9a9a96">Navidrome er ikke satt opp. Legg det inn under Integrasjoner, så kan du bla i hele biblioteket her.</small>;

  const velgArtist = (a: NdArtist) => onVelg({ navn: a.name, undertittel: `Artist · ${a.albumCount} album`, omslag: ndCover(a.coverArt || a.id, 600), handling: 'navidrome_artist', verdi: a.id });
  const velgAlbum = (al: NdAlbum) => onVelg({ navn: al.name, undertittel: al.artist + (al.year ? ` · ${al.year}` : ''), omslag: ndCover(al.coverArt || al.id, 600), handling: 'navidrome_album', verdi: al.id });
  const velgSang = (s: NdSong) => onVelg({ navn: s.title, undertittel: [s.artist, s.album].filter(Boolean).join(' · '), omslag: ndCover(s.coverArt || s.albumId || s.id, 600), handling: 'navidrome_song', verdi: s.id });
  const er = (h: NfcHandling, id: string) => valgt?.handling === h && valgt.verdi === id;
  const ql = q.trim().toLowerCase();

  const sangRad = (s: NdSong, i: number, medAlbum = false) => (
    <button key={s.id + i} style={rad(er('navidrome_song', s.id))} onClick={() => velgSang(s)}>
      {medAlbum ? <Cv id={s.coverArt || s.albumId} size={36} /> : <span style="width:24px;text-align:right;color:#6a6a65;font-size:12px;font-variant-numeric:tabular-nums">{i + 1}</span>}
      <span style="flex:1;min-width:0"><div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.title}</div>{medAlbum && <small style="color:#9a9a96">{s.artist} · {s.album}</small>}</span>
      <small style="color:#6a6a65;font-variant-numeric:tabular-nums">{tid(s.duration)}</small>
    </button>);

  let innhold;
  if (ql.length >= 2 && (vis.t === 'artister' || vis.t === 'album')) {
    const a = (artister ?? []).filter((x) => x.name.toLowerCase().includes(ql)).slice(0, 12);
    const al = alleAlbum.filter((x) => (x.name + ' ' + x.artist).toLowerCase().includes(ql)).slice(0, 12);
    innhold = <>
      {a.length > 0 && <><small style="color:#6a6a65;letter-spacing:.12em;padding:6px 10px 2px">ARTISTER</small>{a.map((x) => <button key={x.id} style={rad()} onClick={() => { setQ(''); setVis({ t: 'artist', a: x }); }}><Cv id={x.coverArt || x.id} size={36} round /><span style="flex:1">{x.name}</span><small style="color:#6a6a65">›</small></button>)}</>}
      {al.length > 0 && <><small style="color:#6a6a65;letter-spacing:.12em;padding:6px 10px 2px">ALBUM</small>{al.map((x) => <button key={x.id} style={rad()} onClick={() => { setQ(''); setVis({ t: 'albumet', al: x }); }}><Cv id={x.coverArt} size={36} /><span style="flex:1;min-width:0"><div>{x.name}</div><small style="color:#9a9a96">{x.artist}</small></span><small style="color:#6a6a65">›</small></button>)}</>}
      {treff.length > 0 && <><small style="color:#6a6a65;letter-spacing:.12em;padding:6px 10px 2px">LÅTER</small>{treff.map((s, i) => sangRad(s, i, true))}</>}
      {!a.length && !al.length && !treff.length && <small style="color:#9a9a96;padding:10px">Ingen treff på «{q}».</small>}
    </>;
  } else if (vis.t === 'artister') {
    let sist = '';
    innhold = artister === null ? <small style="color:#9a9a96;padding:10px">Henter artister …</small> : artister.map((x) => {
      const b = forbokstav(x.name), ny = b !== sist; sist = b;
      return <div key={x.id}>{ny && <div style={`position:sticky;top:0;background:#141415;color:${A};font-size:12px;font-weight:600;padding:6px 10px 2px;z-index:1`}>{b}</div>}
        <button style={rad(er('navidrome_artist', x.id))} onClick={() => setVis({ t: 'artist', a: x })}><Cv id={x.coverArt || x.id} size={36} round /><span style="flex:1;min-width:0"><div>{x.name}</div><small style="color:#9a9a96">{x.albumCount} album</small></span><small style="color:#6a6a65">›</small></button></div>;
    });
  } else if (vis.t === 'album') {
    innhold = <>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:12px;padding:4px">
        {alleAlbum.map((x) => <button key={x.id} style="border:none;background:none;padding:0;text-align:left;color:#f2f2ee;cursor:pointer;font:inherit;min-width:0" onClick={() => setVis({ t: 'albumet', al: x })}>
          <img src={ndCover(x.coverArt, 300)} loading="lazy" style={`width:100%;aspect-ratio:1;border-radius:8px;object-fit:cover;background:#222;${er('navidrome_album', x.id) ? 'outline:2px solid ' + A : ''}`} />
          <div style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:4px">{x.name}</div>
          <small style="color:#9a9a96;display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.artist}</small></button>)}
      </div>
      {merAlbum && <small style="color:#9a9a96;padding:10px">Henter flere album …</small>}
    </>;
  } else if (vis.t === 'artist') {
    const a = vis.a;
    innhold = <>
      <div style="display:flex;gap:12px;align-items:center;padding:4px 6px 10px">
        <Cv id={a.coverArt || a.id} size={64} round />
        <div style="flex:1;min-width:0"><div style="font-size:18px;font-weight:600">{a.name}</div><small style="color:#9a9a96">{a.albumCount} album · velg et album for å velge en låt</small></div>
        <button style={chip(er('navidrome_artist', a.id))} onClick={() => velgArtist(a)}>{er('navidrome_artist', a.id) ? '✓ Hele artisten' : 'Velg hele artisten'}</button>
      </div>
      {artistAlbum === null ? <small style="color:#9a9a96;padding:10px">Henter album …</small> : artistAlbum.map((x) => (
        <button key={x.id} style={rad(er('navidrome_album', x.id))} onClick={() => setVis({ t: 'albumet', al: x, fra: a })}><Cv id={x.coverArt} size={44} /><span style="flex:1;min-width:0"><div>{x.name}</div><small style="color:#9a9a96">{[x.year, x.songCount + ' låter'].filter(Boolean).join(' · ')}</small></span><small style="color:#6a6a65">›</small></button>))}
    </>;
  } else {
    const al = vis.al;
    innhold = <>
      <div style="display:flex;gap:12px;align-items:center;padding:4px 6px 10px">
        <Cv id={al.coverArt} size={72} />
        <div style="flex:1;min-width:0"><div style="font-size:18px;font-weight:600">{al.name}</div><small style="color:#9a9a96">{al.artist}{al.year ? ' · ' + al.year : ''} · velg hele albumet eller én låt</small></div>
        <button style={chip(er('navidrome_album', al.id))} onClick={() => velgAlbum(al)}>{er('navidrome_album', al.id) ? '✓ Hele albumet' : 'Velg hele albumet'}</button>
      </div>
      {sanger === null ? <small style="color:#9a9a96;padding:10px">Henter låter …</small> : sanger.map((s, i) => sangRad(s, i))}
    </>;
  }

  const tilbake = vis.t === 'albumet' ? (vis.fra ? () => setVis({ t: 'artist', a: vis.fra! }) : () => setVis({ t: 'album' })) : vis.t === 'artist' ? () => setVis({ t: 'artister' }) : null;
  return (
    <div style="display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">
        {tilbake && <button style={chip()} onClick={tilbake}>‹ Tilbake</button>}
        <button style={chip(vis.t === 'artister' || vis.t === 'artist')} onClick={() => setVis({ t: 'artister' })}>Artister</button>
        <button style={chip(vis.t === 'album' || (vis.t === 'albumet' && !vis.fra))} onClick={() => setVis({ t: 'album' })}>Album</button>
        <input style={inp + ';flex:1;min-width:160px'} placeholder="Søk etter artist, album eller låt" value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />
      </div>
      <div ref={listeRef} style={liste + ';background:#141415;border:1px solid #242426;border-radius:12px;padding:6px'} onScroll={onScroll}>{innhold}</div>
      {feil && <small style="color:#e06c5a">{feil}</small>}
    </div>
  );
}
