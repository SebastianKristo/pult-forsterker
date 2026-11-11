/** Platesamling: ta opp vinyl fra AUX side for side, få sporene delt opp og gjenkjent, lagre som FLAC på NAS-en. */
import { useEffect, useState } from 'preact/hooks';
import { everyVisible } from '../lib/store';
import { mmss, vinyl, type VAlbum, type VStatus } from '../lib/vinyl';

const A = '#e8b04a';
const box = 'background:#141415;border:1px solid #242426;border-radius:14px;padding:14px;margin-bottom:12px';
const inp = 'background:#0e0e0f;border:1px solid #2a2a2c;border-radius:8px;color:#f2f2ee;padding:8px 10px;font:inherit;min-width:0';
const btn = (on = false) => `padding:9px 15px;border-radius:9px;border:1px solid ${on ? A : '#2a2a2c'};background:${on ? '#1c170d' : '#1a1a1b'};color:#f2f2ee;cursor:pointer;font:inherit`;
const dim = 'color:#8a8a86;font-size:13px';

export function VinylPage() {
  const [st, setSt] = useState<VStatus | null>(null);
  const [albums, setAlbums] = useState<VAlbum[]>([]);
  const [err, setErr] = useState('');
  const [open, setOpen] = useState<string>('');
  const [showCfg, setShowCfg] = useState(false);

  const load = () => vinyl.status().then(setSt).catch((e) => setErr(String(e.message || e)));
  const loadArc = () => vinyl.archive().then((r) => setAlbums(r.albums)).catch(() => {});
  useEffect(() => { load(); loadArc(); }, []);
  useEffect(() => {
    const busy = st && st.state !== 'idle';
    const t = everyVisible(() => { load(); if (st?.state === 'saving') loadArc(); }, busy ? 1000 : 5000);
    return () => clearInterval(t);
  }, [st?.state]);
  useEffect(() => { if (st?.state === 'idle') loadArc(); }, [st?.state]);

  const act = (p: Promise<VStatus>) => p.then((s) => { setSt(s); setErr(''); }).catch((e) => setErr(String(e.message || e)));
  if (!st) return <div style="padding:16px">{err || 'Laster …'}</div>;
  const lvl = st.now ? Math.max(0, Math.min(100, (st.now.level + 60) * 1.8)) : 0;

  return (
    <div style="padding:16px;max-width:760px">
      <p style={dim}>Spill platen på AUX-inngangen. Skjold tar opp side for side, finner sporene ved pausene, gjenkjenner albumet og lagrer FLAC med omslag på NAS-en (samme deling som Radioopptak).</p>
      {err && <div style="color:#ff7a6b;margin-bottom:10px">{err}</div>}

      <div style={box}>
        {st.state === 'idle' && <>
          <div style="font-weight:600;margin-bottom:8px">Ny plate</div>
          <button style={btn(true)} onClick={() => act(vinyl.start('A'))}>● Start side A</button>
        </>}
        {st.state === 'recording' && st.now && <>
          <div style="font-weight:600">Tar opp side {st.now.side} · {mmss(st.now.secs)}</div>
          <div style="height:8px;background:#0e0e0f;border-radius:4px;margin:10px 0;overflow:hidden"><div style={`height:100%;width:${lvl}%;background:${st.now.level > -3 ? '#ff7a6b' : A}`} /></div>
          <div style={dim}>Senk nålen nå. Trykk «Side ferdig» når siden er spilt ut.</div>
          <button style={btn(true) + ';margin-top:10px'} onClick={() => act(vinyl.stop())}>■ Side ferdig</button>
        </>}
        {(st.state === 'review' || st.state === 'saving') && <Review st={st} act={act} />}
        {st.msg && <div style={dim + ';margin-top:10px'}>{st.msg}</div>}
        {st.state !== 'idle' && st.state !== 'saving' && <button style={btn() + ';margin-top:10px'} onClick={() => confirm('Forkaste opptaket?') && act(vinyl.cancel())}>Avbryt</button>}
      </div>

      <div style="display:flex;align-items:center;justify-content:space-between;margin:18px 0 8px">
        <div style="font-weight:600;font-size:17px">Platesamling ({albums.length})</div>
        <button style={btn()} onClick={() => setShowCfg(!showCfg)}>Oppdeling …</button>
      </div>
      {showCfg && <Cfg st={st} onSaved={load} />}
      {albums.length === 0 && <div style={dim}>Ingen plater ennå.</div>}
      {albums.map((a) => <AlbumRow key={a.id} a={a} open={open === a.id} toggle={() => setOpen(open === a.id ? '' : a.id)} reload={loadArc} />)}
    </div>
  );
}

function Review({ st, act }: { st: VStatus; act: (p: Promise<VStatus>) => void }) {
  const [artist, setArtist] = useState(st.album.artist);
  const [album, setAlbum] = useState(st.album.album);
  const [year, setYear] = useState(st.album.year);
  useEffect(() => { setArtist(st.album.artist); setAlbum(st.album.album); }, [st.album.artist, st.album.album]);
  const saving = st.state === 'saving';
  const nextSide = String.fromCharCode(65 + st.sides.length);
  return <>
    <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
      {st.album.cover && <img src={st.album.cover} style="width:96px;height:96px;border-radius:8px;object-fit:cover" />}
      <div style="display:flex;flex-direction:column;gap:6px;flex:1;min-width:200px">
        <input style={inp} placeholder="Artist" value={artist} onInput={(e) => setArtist((e.target as HTMLInputElement).value)} onBlur={() => act(vinyl.edit({ artist }))} />
        <input style={inp} placeholder="Album" value={album} onInput={(e) => setAlbum((e.target as HTMLInputElement).value)} onBlur={() => act(vinyl.edit({ album }))} />
        <input style={inp + ';width:90px'} placeholder="År" value={year} onInput={(e) => setYear((e.target as HTMLInputElement).value)} onBlur={() => act(vinyl.edit({ year }))} />
      </div>
    </div>
    <div style="margin-top:12px">
      {st.tracks.map((t) => <div key={t.n} style="display:flex;gap:8px;align-items:center;padding:4px 0;border-bottom:1px solid #1e1e20">
        <span style={dim + ';width:44px'}>{t.side}{t.n}</span>
        <input style={inp + ';flex:1;padding:5px 8px'} value={t.title} onBlur={(e) => act(vinyl.edit({ tracks: [{ n: t.n, title: (e.target as HTMLInputElement).value }] }))} />
        <span style={dim}>{mmss(t.end - t.start)}</span>
      </div>)}
    </div>
    {saving ? <div style="margin-top:12px">Lagrer … {Math.round(st.progress * 100)} %</div> :
      <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap">
        <button style={btn()} onClick={() => act(vinyl.start(nextSide))}>Snu platen: ta opp side {nextSide}</button>
        <button style={btn(true)} onClick={() => act(vinyl.save())}>Lagre i platesamlingen</button>
      </div>}
  </>;
}

function Cfg({ st, onSaved }: { st: VStatus; onSaved: () => void }) {
  const [c, setC] = useState(st.cfg);
  const num = (k: 'thresh_db' | 'min_gap' | 'min_track', label: string, hint: string) => <label style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:140px">
    <span>{label}</span><input type="number" step="0.1" style={inp} value={c[k]} onInput={(e) => setC({ ...c, [k]: Number((e.target as HTMLInputElement).value) })} /><span style={dim}>{hint}</span></label>;
  return <div style={box}>
    <div style="display:flex;gap:12px;flex-wrap:wrap">
      {num('thresh_db', 'Stillhetsgrense (dB)', 'Lavere = mer følsom for knaster')}
      {num('min_gap', 'Minste pause (s)', 'Pauser kortere enn dette deler ikke')}
      {num('min_track', 'Korteste spor (s)', 'Kortere biter slås sammen')}
    </div>
    <label style="display:flex;flex-direction:column;gap:4px;margin-top:10px"><span>Opptaksenhet (ALSA, tom = AUX)</span><input style={inp} value={c.device} onInput={(e) => setC({ ...c, device: (e.target as HTMLInputElement).value })} placeholder="plughw:UCA_AUX1" /></label>
    <button style={btn(true) + ';margin-top:10px'} onClick={() => vinyl.settings(c).then(onSaved)}>Lagre</button>
  </div>;
}

function AlbumRow({ a, open, toggle, reload }: { a: VAlbum; open: boolean; toggle: () => void; reload: () => void }) {
  const [titles, setTitles] = useState<Record<number, string>>({});
  return <div style={box}>
    <div style="display:flex;gap:12px;align-items:center;cursor:pointer" onClick={toggle}>
      {a.cover ? <img src={a.cover} style="width:56px;height:56px;border-radius:6px;object-fit:cover" /> : <div style="width:56px;height:56px;border-radius:6px;background:#0e0e0f;display:grid;place-items:center">◉</div>}
      <div style="flex:1;min-width:0"><div style="font-weight:600">{a.album}</div><div style={dim}>{a.artist}{a.year ? ' · ' + a.year : ''} · {a.tracks.length} spor · {mmss(a.secs)} · {a.where === 'smb' ? 'NAS' : 'lokalt'}</div></div>
      <span style={dim}>{open ? '▾' : '▸'}</span>
    </div>
    {open && <div style="margin-top:10px">
      {a.tracks.map((t) => <div key={t.n} style="display:flex;gap:8px;align-items:center;padding:3px 0">
        <span style={dim + ';width:44px'}>{t.side}{t.n}</span>
        <input style={inp + ';flex:1;padding:5px 8px'} value={titles[t.n] ?? t.title} onInput={(e) => setTitles({ ...titles, [t.n]: (e.target as HTMLInputElement).value })} />
        <span style={dim}>{mmss(t.end - t.start)}</span>
      </div>)}
      <div style="display:flex;gap:8px;margin-top:10px">
        <button style={btn(true)} disabled={!Object.keys(titles).length} onClick={() => vinyl.editAlbum(a.id, { tracks: Object.entries(titles).map(([n, title]) => ({ n: Number(n), title })) }).then(() => { setTitles({}); reload(); })}>Lagre titler</button>
        <button style={btn()} onClick={() => confirm('Fjerne platen fra listen? Filene på NAS-en blir liggende.') && vinyl.remove(a.id).then(reload)}>Fjern fra listen</button>
      </div>
    </div>}
  </div>;
}
