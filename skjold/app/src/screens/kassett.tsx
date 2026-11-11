/** Skjold Kassett: NFC-kassetter koblet til radio, NRK, Navidrome, Music Assistant eller rutiner. */
import { useEffect, useState } from 'preact/hooks';
import { everyVisible } from '../lib/store';
import { api, getBase, type NfcCard, type NfcDeling, type NfcHandling, type NfcOppsett, type NfcStats, type NfcStatus, type NfcVentende, type Routine, type Spoler } from '../lib/api';
import { QR } from './platform';
import { HyllePanel } from './hylle';
import { HjulPanel } from './hjul';
import { ndCover, ndConfigured, ndPlaylists, ndSearch } from '../lib/navidrome';

const A = '#e8b04a';
const box = 'background:#141415;border:1px solid #242426;border-radius:14px;padding:14px';
const inp = 'background:#0e0e0f;border:1px solid #2a2a2c;border-radius:8px;color:#f2f2ee;padding:8px 10px;font:inherit';
const btn = (on = false) => `padding:8px 14px;border-radius:9px;border:1px solid ${on ? A : '#2a2a2c'};background:${on ? '#1c170d' : '#1a1a1b'};color:#f2f2ee;cursor:pointer;font:inherit`;
const LABEL: Record<NfcHandling, string> = { preset: 'Radio', play_url: 'Strøm', nrk: 'NRK', ma_uri: 'Music Assistant', navidrome_album: 'Navidrome-album', navidrome_playlist: 'Navidrome-spilleliste', routine: 'Rutine', album: 'Album' };
const KILDE: Record<string, string> = { navidrome: 'Navidrome', ytmusic: 'YouTube Music', ma: 'Music Assistant' };
/** Relative bilder fra Skjold (/api/nfc/cover, /api/logo) må ha enhetens adresse foran når appen kjører et annet sted. */
const img = (u: string) => (u && u.startsWith('/') ? getBase() + u : u);

type Src = 'nå' | 'album' | 'radio' | 'nrk' | 'nd' | 'ma' | 'rutine';
interface Hit { navn: string; undertittel: string; omslag: string; handling: NfcHandling; verdi: unknown }

async function search(src: Src, q: string, routines: Routine[]): Promise<Hit[]> {
  if (src === 'radio') {
    const r = await api.radioSearch(q);
    return [...r.norway, ...r.world].slice(0, 30).map((s) => ({ navn: s.name, undertittel: 'Radio', omslag: s.image || '', handling: 'play_url' as const, verdi: s.url }));
  }
  if (src === 'nrk') {
    const r = await api.nrkSearch(q);
    return [...r.series.map((s) => ({ navn: s.title, undertittel: s.subtitle || 'NRK', omslag: s.image, handling: 'nrk' as const, verdi: { series: s.id } })),
      ...r.episodes.map((e) => ({ navn: e.title, undertittel: e.series || 'NRK', omslag: e.image, handling: 'nrk' as const, verdi: { episode: e.id } }))];
  }
  if (src === 'ma') {
    const r = await api.maSearch(q);
    return (['albums', 'playlists', 'artists', 'radio', 'tracks', 'podcasts', 'audiobooks'] as const).flatMap((k) => r[k] || [])
      .slice(0, 40).map((m) => ({ navn: m.name, undertittel: m.artist || m.kind, omslag: m.image, handling: 'ma_uri' as const, verdi: m.uri }));
  }
  if (src === 'nd') {
    if (!ndConfigured()) return [];
    const ql = q.toLowerCase();
    const [songs, pls] = await Promise.all([q ? ndSearch(q) : Promise.resolve([]), ndPlaylists()]);
    const seen = new Set<string>(); const albums: Hit[] = [];
    for (const s of songs) if (s.albumId && !seen.has(s.albumId)) { seen.add(s.albumId); albums.push({ navn: s.album, undertittel: s.artist, omslag: ndCover(s.coverArt), handling: 'navidrome_album', verdi: s.albumId }); }
    const pl = pls.filter((p) => !ql || p.name.toLowerCase().includes(ql)).map((p) => ({ navn: p.name, undertittel: 'Spilleliste', omslag: ndCover(p.coverArt), handling: 'navidrome_playlist' as const, verdi: p.id }));
    return [...albums, ...pl];
  }
  if (src === 'rutine') {
    const ql = q.toLowerCase();
    return routines.filter((r) => !ql || r.navn.toLowerCase().includes(ql)).map((r) => ({ navn: r.navn, undertittel: 'Rutine', omslag: '', handling: 'routine' as const, verdi: r.id }));
  }
  return [];
}

/** Ferdig A4-ark fra Skjold (GET /api/nfc/label): samme mål og kuttlinjer som kabinett/kassett, cover bakt inn. */
function printLabels(cards: NfcCard[], start = 0): void {
  const uids = cards.map((c) => c.uid).filter(Boolean).join(',');
  const url = `${getBase()}/api/nfc/label?uids=${encodeURIComponent(uids)}&start=${start}`;
  const w = window.open('', '_blank'); if (!w) { location.href = url; return; }
  w.document.write(`<!doctype html><meta charset="utf-8"><title>Kassett-etiketter</title><style>@page{size:A4;margin:0}body{margin:0}img{width:210mm;height:297mm;display:block}</style><img src="${url}" onload="setTimeout(()=>print(),300)">`);
  w.document.close();
}

function Editor({ init, onDone }: { init: NfcCard | null; onDone: () => void }) {
  const [src, setSrc] = useState<Src>(init ? 'radio' : 'nå');
  const [q, setQ] = useState('');
  const [hits, setHits] = useState<Hit[]>([]);
  const [busy, setBusy] = useState(false);
  const [pick, setPick] = useState<Hit | null>(init ? { navn: init.navn, undertittel: init.undertittel, omslag: init.omslag, handling: init.handling, verdi: init.verdi } : null);
  const [navn, setNavn] = useState(init?.navn ?? '');
  const [rom, setRom] = useState((init?.rom ?? []).join(', '));
  const [vol, setVol] = useState<string>(init?.volum != null ? String(init.volum) : '');
  const [uttak, setUttak] = useState<'pause' | 'ingenting'>(init?.ved_uttak ?? 'pause');
  const [routines, setRoutines] = useState<Routine[]>([]);
  const [learn, setLearn] = useState<'' | 'venter' | 'ok' | string>('');
  const [err, setErr] = useState('');
  const initAlbum = init?.handling === 'album' ? (init.verdi as { artist?: string; album?: string }) : null;
  const [artist, setArtist] = useState(initAlbum?.artist ?? '');
  const [album, setAlbum] = useState(initAlbum?.album ?? '');
  const [forslag, setForslag] = useState<{ artist: string; album: string; kilde: string }[]>([]);
  const [kilde, setKilde] = useState('');
  useEffect(() => { if (initAlbum) setSrc('album'); }, []);
  useEffect(() => {
    if (src !== 'album') return;
    setPick(album.trim() ? { navn: album.trim(), undertittel: artist.trim(), omslag: `/api/nfc/cover?artist=${encodeURIComponent(artist.trim())}&album=${encodeURIComponent(album.trim())}`, handling: 'album', verdi: { artist: artist.trim(), album: album.trim() } } : null);
    setKilde('');
    const q = `${artist} ${album}`.trim();
    if (q.length < 2) { setForslag([]); return; }
    const t = setTimeout(() => {
      api.nfcSok(q).then((r) => setForslag(r.treff.slice(0, 10))).catch(() => setForslag([]));
      if (album.trim()) api.nfcFinn(artist.trim(), album.trim()).then((r) => setKilde(r.kilde || 'ikke funnet')).catch(() => setKilde(''));
    }, 450);
    return () => clearTimeout(t);
  }, [src, artist, album]);
  useEffect(() => { api.routines().then((r) => setRoutines(Array.isArray(r) ? r : r.routines ?? [])).catch(() => {}); }, []);
  useEffect(() => {
    if (src === 'nå' || src === 'album' || (src !== 'rutine' && src !== 'nd' && q.trim().length < 2)) { setHits([]); return; }
    const t = setTimeout(() => { setBusy(true); search(src, q.trim(), routines).then(setHits).catch(() => setHits([])).finally(() => setBusy(false)); }, 350);
    return () => clearTimeout(t);
  }, [src, q, routines]);

  const card = (): NfcCard | null => {
    if (src === 'nå' && !init) return null;
    if (!pick) return null;
    return { navn: navn || pick.navn, undertittel: pick.undertittel, omslag: pick.omslag, handling: pick.handling, verdi: pick.verdi,
      rom: rom.split(',').map((s) => s.trim()).filter(Boolean), volum: vol === '' ? null : Math.max(0, Math.min(100, +vol)), ved_uttak: uttak };
  };
  const extras = { rom: rom.split(',').map((s) => s.trim()).filter(Boolean), volum: vol === '' ? null : +vol, ved_uttak: uttak, ...(navn ? { navn } : {}) };

  async function save() {
    setErr('');
    try {
      if (init?.uid) { const c = card(); if (!c) { setErr('Velg hva som skal spilles.'); return; } await api.nfcSave({ ...c, uid: init.uid }); onDone(); return; }
      const draft = src === 'nå' ? (Object.keys(extras).length ? extras : null) : card();
      if (src !== 'nå' && !draft) { setErr('Velg hva som skal spilles.'); return; }
      const before = (await api.nfc()).last?.t ?? 0;
      await api.nfcLearn(draft as Partial<NfcCard> | null);
      setLearn('venter');
      const until = Date.now() + 60000;
      while (Date.now() < until) {
        await new Promise((r) => setTimeout(r, 1000));
        const s = await api.nfc();
        if (s.last && s.last.t > before && s.last.known) { setLearn('ok'); setTimeout(onDone, 1200); return; }
        if (!s.learning) break;
      }
      setLearn('Fant ingen kassett. Prøv igjen.');
    } catch (e) { setErr(String((e as Error).message || e)); setLearn(''); }
  }

  if (learn === 'venter') return <div style={box + ';text-align:center;padding:40px'}><div style={`font-size:22px;color:${A}`}>Sett inn kassetten nå</div><p style="color:#9a9a96">Venter på NFC-brikken (60 s) …</p><button style={btn()} onClick={() => { void api.nfcLearnStop(); setLearn(''); }}>Avbryt</button></div>;
  if (learn === 'ok') return <div style={box + ';text-align:center;padding:40px;color:' + A}>✓ Kassetten er koblet</div>;

  const SRC: [Src, string][] = [['nå', 'Det som spiller nå'], ['album', 'Album (Navidrome / YouTube Music)'], ['radio', 'Radio'], ['nrk', 'NRK'], ['nd', 'Navidrome'], ['ma', 'Music Assistant'], ['rutine', 'Rutine']];
  return (
    <div style={box + ';display:flex;flex-direction:column;gap:12px'}>
      <b>{init?.uid ? 'Rediger kassett' : 'Koble ny kassett'}</b>
      <div style="display:flex;flex-wrap:wrap;gap:6px">{SRC.filter(([k]) => !(init?.uid && k === 'nå')).map(([k, t]) => <button key={k} style={btn(src === k)} onClick={() => { setSrc(k); setHits([]); }}>{t}</button>)}</div>
      {src === 'album' && <>
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <input style={inp + ';flex:1;min-width:140px'} placeholder="Artist" value={artist} onInput={(e) => setArtist((e.target as HTMLInputElement).value)} />
          <input style={inp + ';flex:1;min-width:140px'} placeholder="Album" value={album} onInput={(e) => setAlbum((e.target as HTMLInputElement).value)} />
        </div>
        <small style="color:#9a9a96">Har du albumet i Navidrome, spilles det derfra. Ellers fra YouTube Music (via Music Assistant). Skjold sjekker igjen hvert døgn om du har lastet det ned.</small>
        {kilde && <small style={'color:' + (kilde === 'ikke funnet' ? '#e06c5a' : A)}>{kilde === 'ikke funnet' ? 'Fant det ikke i Navidrome eller YouTube Music nå – kassetten lagres likevel og prøver igjen når den settes inn.' : 'Spilles fra ' + kilde}</small>}
        {forslag.length > 0 && <div style="display:flex;flex-wrap:wrap;gap:6px">{forslag.map((f, i) => <button key={i} style={btn(f.album === album && f.artist === artist)} onClick={() => { setArtist(f.artist); setAlbum(f.album); if (!navn) setNavn(f.album); }}>{f.album} <small style="color:#9a9a96">· {f.artist} · {f.kilde}</small></button>)}</div>}
      </>}
      {src !== 'nå' && src !== 'album' && <input style={inp} placeholder="Søk …" value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />}
      {src === 'nd' && !ndConfigured() && <small style="color:#9a9a96">Navidrome er ikke satt opp.</small>}
      {busy && <small style="color:#9a9a96">Søker …</small>}
      {hits.length > 0 && <div style="max-height:260px;overflow:auto;display:flex;flex-direction:column;gap:4px">{hits.map((h, i) => (
        <button key={i} style={btn(pick?.verdi === h.verdi) + ';display:flex;gap:10px;align-items:center;text-align:left'} onClick={() => { setPick(h); if (!navn) setNavn(h.navn); }}>
          {h.omslag ? <img src={img(h.omslag)} style="width:36px;height:36px;border-radius:6px;object-fit:cover" /> : <span style="width:36px;height:36px;border-radius:6px;background:#222" />}
          <span><div>{h.navn}</div><small style="color:#9a9a96">{h.undertittel} · {LABEL[h.handling]}</small></span>
        </button>))}</div>}
      {pick && src !== 'nå' && src !== 'album' && <small style={'color:' + A}>Valgt: {pick.navn} ({LABEL[pick.handling]})</small>}
      <label>Navn på etiketten<br /><input style={inp + ';width:100%'} value={navn} placeholder={src === 'nå' ? 'Tas fra det som spiller' : ''} onInput={(e) => setNavn((e.target as HTMLInputElement).value)} /></label>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <label>Rom (kommaliste, tom = dette)<br /><input style={inp} value={rom} onInput={(e) => setRom((e.target as HTMLInputElement).value)} /></label>
        <label>Volum (0–100)<br /><input style={inp + ';width:90px'} type="number" min={0} max={100} value={vol} onInput={(e) => setVol((e.target as HTMLInputElement).value)} /></label>
        <label>Når kassetten tas ut<br /><select style={inp} value={uttak} onChange={(e) => setUttak((e.target as HTMLSelectElement).value as 'pause' | 'ingenting')}><option value="pause">Pause</option><option value="ingenting">Fortsett å spille</option></select></label>
      </div>
      {err && <small style="color:#e06c5a">{err}</small>}
      {learn && learn !== 'venter' && <small style="color:#e06c5a">{learn}</small>}
      <div style="display:flex;gap:8px"><button style={btn(true)} onClick={() => void save()}>{init?.uid ? 'Lagre' : 'Koble – sett inn kassetten'}</button><button style={btn()} onClick={onDone}>Avbryt</button></div>
    </div>
  );
}

/** Spolene i vinduet på Kassett-spilleren: av/på, fart ved avspilling og ved spoling. */
function SpolerPanel() {
  const [s, setS] = useState<Spoler | null>(null);
  const [err, setErr] = useState('');
  const load = () => api.spoler().then((x) => { setS(x); setErr(''); }).catch((e) => setErr(String((e as Error).message || e)));
  useEffect(() => { void load(); const t = everyVisible(load, 3000); return () => clearInterval(t); }, []);
  const set = (b: Partial<Spoler>) => { if (s) setS({ ...s, ...b }); void api.spolerSett(b).then(setS).catch((e) => setErr(String((e as Error).message || e))); };
  if (!s) return err ? <small style="color:#e06c5a">Spolene: {err}</small> : null;
  const MODUS = { spill: 'Spiller', spol: 'Spoler fremover', tilbake: 'Spoler tilbake', stopp: 'Står stille' } as const;
  return (
    <div style={box + ';display:flex;flex-direction:column;gap:10px'}>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <b style="flex:1">Spoler i vinduet</b>
        <small style={'color:' + (s.modus && s.modus !== 'stopp' ? A : '#9a9a96')}>{MODUS[s.modus ?? 'stopp']}</small>
        <button style={btn(s['på'])} onClick={() => set({ 'på': !s['på'] })}>{s['på'] ? 'På' : 'Av'}</button>
      </div>
      <small style="color:#9a9a96">Spolene i kassetten går rundt mens musikken spiller, står stille på pause og spoler når du hopper i låten eller bytter låt.</small>
      <label style="display:flex;gap:10px;align-items:center">Fart <input type="range" min={0.1} max={1.5} step={0.05} value={s.fart} onChange={(e) => set({ fart: +e.currentTarget.value })} style="flex:1" /> <span style="width:70px;text-align:right">{s.fart.toFixed(2)} o/s</span></label>
      <label style="display:flex;gap:10px;align-items:center">Spoling <input type="range" min={0.5} max={3} step={0.1} value={s.spol} onChange={(e) => set({ spol: +e.currentTarget.value })} style="flex:1" /> <span style="width:70px;text-align:right">{s.spol.toFixed(1)} o/s</span></label>
      <label style="display:flex;gap:10px;align-items:center" title="Ved neste/forrige fra appen eller Touch står lyden mens spolene spoler">Vent ved neste <input type="range" min={0} max={6} step={0.5} value={s.vent ?? 2.5} onChange={(e) => set({ vent: +e.currentTarget.value })} style="flex:1" /> <span style="width:70px;text-align:right">{(s.vent ?? 2.5) ? (s.vent ?? 2.5).toFixed(1) + ' s' : 'av'}</span></label>
      <label style="display:flex;gap:8px;align-items:center"><input type="checkbox" checked={s.bare_kassett} onChange={(e) => set({ bare_kassett: e.currentTarget.checked })} /> Bare når en kassett står i spilleren</label>
    </div>
  );
}

/** Paring (hvilken Skjold spiller kassettene) og import av albumlister («Artist - Album» per linje). */
const ventNavn = (v: NfcVentende) => v.navn || v.album || ((v.verdi as { album?: string } | undefined)?.album ?? 'Kassett');
const ventUnder = (v: NfcVentende) => v.undertittel || v.artist || ((v.verdi as { artist?: string } | undefined)?.artist ?? (v.handling ? LABEL[v.handling] : ''));
const tid = (s: number) => { const m = Math.round(s / 60); return m < 60 ? `${m} min` : `${Math.floor(m / 60)} t ${m % 60} min`; };
const dato = (t: number) => (t ? new Date(t * 1000).toLocaleDateString('nb-NO', { day: 'numeric', month: 'short', year: 'numeric' }) : 'aldri');
const MND = ['jan', 'feb', 'mar', 'apr', 'mai', 'jun', 'jul', 'aug', 'sep', 'okt', 'nov', 'des'];

async function kopier(t: string): Promise<boolean> { try { await navigator.clipboard.writeText(t); return true; } catch { return false; } }

/** Del kassetter: kort kode via Skjold Cloud (kryptert, 14 dager, passer i QR), eller en lengre kode uten sky. */
function DelDialog({ uids, onClose }: { uids: string[]; onClose: () => void }) {
  const [d, setD] = useState<NfcDeling | null>(null);
  const [msg, setMsg] = useState('');
  const lag = (sky: boolean) => { setD(null); setMsg(''); void api.nfcShare(uids, sky).then(setD).catch((e) => {
    const m = String((e as Error).message || e);
    if (sky) { setMsg(`Skjold Cloud svarte ikke (${m}) – viser kode uten sky.`); void api.nfcShare(uids, false).then(setD).catch((e2) => setMsg(String((e2 as Error).message || e2))); }
    else setMsg(m);
  }); };
  useEffect(() => { lag(true); }, [uids.join(',')]);
  const qrTekst = d && d.lenke.length <= 78 ? d.lenke : '';
  return (
    <div style="position:fixed;inset:0;background:rgba(0,0,0,.6);display:grid;place-items:center;z-index:50;padding:16px" onClick={onClose}>
      <div style={box + ';max-width:420px;width:100%;display:flex;flex-direction:column;gap:10px'} onClick={(e) => e.stopPropagation()}>
        <b>Del {uids.length > 1 ? `${uids.length} kassetter` : 'kassett'}</b>
        <small style="color:#9a9a96">Vennen skanner QR-koden med Skjold-appen (eller telefonkameraet) eller limer inn koden under «Motta kassett». Den blir en ventende kassett hos dem, klar til å kobles til en NFC-brikke. Albumet slås opp i deres eget Navidrome eller YouTube Music – ingen passord eller private ID-er deles.</small>
        {!d && !msg && <small>Lager kode …</small>}
        {msg && <small style="color:#e0a35a">{msg}</small>}
        {d && <>
          {qrTekst ? <div style="display:grid;place-items:center"><QR text={qrTekst} size={200} label="QR-kode for kassettdeling" /></div>
            : <small style="color:#9a9a96">Koden er for lang for QR – send lenken eller koden i en melding{!d.sky ? ', eller del via Skjold Cloud for en kort kode' : ''}.</small>}
          <small style="color:#9a9a96">{d.delt} kassett{d.delt === 1 ? '' : 'er'} delt{d.hoppet_over ? ` · ${d.hoppet_over} kunne ikke deles (radiofavoritter, rutiner og Navidrome-spillelister er lokale)` : ''}{d.sky && d.utloper ? ` · gyldig til ${dato(Math.round(d.utloper / 1000))}` : ''}</small>
          <input readOnly style={inp + ';font-family:monospace;font-size:12px'} value={d.lenke} onFocus={(e) => (e.currentTarget as HTMLInputElement).select()} />
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button style={btn(true)} onClick={() => void kopier(d.lenke).then((ok) => setMsg(ok ? 'Lenken er kopiert' : 'Marker og kopier lenken'))}>Kopier lenke</button>
            <button style={btn()} onClick={() => void kopier(d.kode).then((ok) => setMsg(ok ? 'Koden er kopiert' : 'Marker og kopier koden'))}>Kopier kode</button>
            <button style={btn()} onClick={() => lag(!d.sky)}>{d.sky ? 'Uten sky' : 'Via Skjold Cloud'}</button>
            <button style={btn()} onClick={onClose}>Lukk</button>
          </div>
        </>}
      </div>
    </div>
  );
}

/** Motta kassett: lim inn delingskode eller lenke. */
function MottaPanel({ onDone }: { onDone: () => void }) {
  const [kode, setKode] = useState('');
  const [msg, setMsg] = useState('');
  useEffect(() => {   // åpnet fra en delingslenke (…#kassett-del=<kode>)
    const m = /kassett-del=([A-Za-z0-9_.-]+)/.exec(location.hash);
    if (m) setKode(m[1]!);
  }, []);
  return (
    <div style={box + ';display:flex;flex-direction:column;gap:8px'}>
      <b>Motta kassett</b>
      <small style="color:#9a9a96">Fått en kassett av en venn? Lim inn lenken eller koden. Den havner blant ventende kassetter – sett inn en ny NFC-brikke for å koble den.</small>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <input style={inp + ';flex:1;min-width:180px'} placeholder="skjold://kassett/del?d=…" value={kode} onInput={(e) => setKode((e.target as HTMLInputElement).value)} />
        <button style={btn(true)} disabled={!kode.trim()} onClick={() => void api.nfcShareImport(kode.trim()).then((r) => {
          setMsg(r.lagt_til ? `${r.lagt_til} kassett${r.lagt_til === 1 ? '' : 'er'}${r.fra ? ` fra ${r.fra}` : ''} venter på en NFC-brikke` : 'Du har disse kassettene fra før');
          setKode(''); onDone();
        }).catch((e) => setMsg(String((e as Error).message || e)))}>Legg til</button>
      </div>
      {msg && <small style={'color:' + A}>{msg}</small>}
    </div>
  );
}

/** Kassett-Wrapped: mest spilt, lyttetid, glemte kassetter og spilt per måned (GET /api/nfc/stats). */
export function KassettWrapped({ kompakt = false }: { kompakt?: boolean }) {
  const [p, setP] = useState<'uke' | 'mnd' | 'år' | 'alt'>('år');
  const [s, setS] = useState<NfcStats | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { setS(null); api.nfcStats(p).then(setS).catch((e) => setErr(String((e as Error).message || e))); }, [p]);
  if (err) return <small style="color:#e06c5a">{err}</small>;
  if (!s) return <small style="color:#9a9a96">Henter kassettstatistikk …</small>;
  const maks = Math.max(1, ...s.per_maned.map((m) => m.spilt));
  const Omslag = ({ r, size }: { r: { omslag: string }; size: number }) => r.omslag
    ? <img src={img(r.omslag)} style={`width:${size}px;height:${size}px;border-radius:8px;object-fit:cover;flex-shrink:0`} />
    : <div style={`width:${size}px;height:${size}px;border-radius:8px;background:#111;color:${A};display:grid;place-items:center;font-size:9px;flex-shrink:0`}>SKJOLD</div>;
  return (
    <div style="display:flex;flex-direction:column;gap:12px">
      <div style={box + ';background:linear-gradient(135deg,#2a1d08,#141415);display:flex;flex-direction:column;gap:6px'}>
        <span style={`font-size:11px;letter-spacing:.12em;color:${A}`}>KASSETT-WRAPPED</span>
        <div style="display:flex;gap:6px;flex-wrap:wrap">{(['uke', 'mnd', 'år', 'alt'] as const).map((x) => <button key={x} style={btn(p === x)} onClick={() => setP(x)}>{{ uke: 'Uke', mnd: '30 dager', år: 'År', alt: 'Alt' }[x]}</button>)}</div>
        {s.totalt.spilt ? <>
          <b style="font-size:40px;line-height:1">{s.totalt.spilt}</b>
          <span style="font-size:13px;color:#a9a9a3">avspillinger · {tid(s.totalt.lyttetid)} med kassetter i spilleren · {s.totalt.brukt} av {s.totalt.kassetter} kassetter brukt</span>
          {s.favoritt && <div style="display:flex;gap:10px;align-items:center;margin-top:6px"><Omslag r={s.favoritt} size={56} /><div><small style="color:#9a9a96">Mest spilte kassett</small><div><b>{s.favoritt.navn}</b></div><small style="color:#9a9a96">{s.favoritt.undertittel} · {s.favoritt.spilt}×</small></div></div>}
        </> : <span style="font-size:13px;color:#a9a9a3">Ingen kassetter spilt i perioden ennå.</span>}
      </div>
      {s.topp.length > 0 && <div style={box + ';display:flex;flex-direction:column;gap:8px'}>
        <b>Mest spilt</b>
        {s.topp.slice(0, kompakt ? 3 : 5).map((r, i) => <div key={r.uid} style="display:flex;gap:10px;align-items:center">
          <span style={`width:18px;color:${A};font-variant-numeric:tabular-nums`}>{i + 1}</span><Omslag r={r} size={40} />
          <div style="flex:1;min-width:0"><div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r.navn}</div><small style="color:#9a9a96">{r.undertittel}{r.kilde ? ` · ${r.kilde}` : ''}</small></div>
          <small style="color:#9a9a96;text-align:right;font-variant-numeric:tabular-nums">{r.spilt}×<br />{tid(r.lyttetid ?? 0)}</small>
        </div>)}
      </div>}
      {s.glemte.length > 0 && <div style={box + ';display:flex;flex-direction:column;gap:8px'}>
        <b>Glemte kassetter</b>
        <small style="color:#9a9a96">Ikke satt inn på {s.glemt_uker} uker eller mer{s.aldri_brukt ? ` · ${s.aldri_brukt} aldri brukt` : ''}.</small>
        {s.glemte.slice(0, kompakt ? 3 : 8).map((r) => <div key={r.uid} style="display:flex;gap:10px;align-items:center">
          <Omslag r={r} size={36} /><div style="flex:1;min-width:0"><div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r.navn}</div><small style="color:#9a9a96">{r.aldri ? 'aldri brukt' : `sist ${dato(r.sist)} · ${r.uker_siden} uker siden`}</small></div>
        </div>)}
      </div>}
      {!kompakt && s.per_maned.length > 1 && <div style={box + ';display:flex;flex-direction:column;gap:8px'}>
        <b>Per måned</b>
        <div style="display:flex;gap:6px;align-items:flex-end;height:90px" role="img" aria-label="Kassettavspillinger per måned">
          {s.per_maned.map((m) => <div key={m.mnd} style="flex:1;display:flex;flex-direction:column;align-items:center;gap:4px;height:100%;justify-content:flex-end">
            <small style="color:#9a9a96;font-variant-numeric:tabular-nums">{m.spilt}</small>
            <div style={`width:100%;max-width:28px;height:${Math.max(3, (m.spilt / maks) * 60)}px;background:${A};border-radius:4px 4px 0 0`} />
            <small style="color:#9a9a96">{MND[+m.mnd.slice(5) - 1]}</small>
          </div>)}
        </div>
      </div>}
    </div>
  );
}

function AlbumPanel() {
  const [o, setO] = useState<NfcOppsett | null>(null);
  const [tekst, setTekst] = useState('');
  const [msg, setMsg] = useState('');
  const load = () => api.nfcOppsett().then(setO).catch(() => {});
  useEffect(() => { void load(); }, []);
  if (!o) return null;
  const set = (b: Partial<NfcOppsett>) => void api.nfcSettOppsett(b).then(setO).catch((e) => setMsg(String((e as Error).message || e)));
  return (
    <div style={box + ';display:flex;flex-direction:column;gap:10px'}>
      <b>Spilles på</b>
      <small style="color:#9a9a96">Par kassettspilleren med en Skjold (Touch, Node, S1, Core): kassettene spilles der, og spolene følger den enhetens avspilling. Pause, neste og volum styrer du som vanlig på den enheten.</small>
      <select style={inp} value={o.paret} onChange={(e) => set({ paret: (e.target as HTMLSelectElement).value })}>
        <option value="">Denne Skjold-enheten</option>
        {(o.enheter ?? []).filter((x) => !x.her).map((x) => <option key={x.navn} value={x.navn}>{x.navn}</option>)}
        {o.paret && !(o.enheter ?? []).some((x) => x.navn === o.paret) && <option value={o.paret}>{o.paret} (ikke funnet nå)</option>}
      </select>
      <b style="margin-top:6px">Importer album</b>
      <small style="color:#9a9a96">Én per linje: «Artist - Album» (samme som album.txt). De blir ventende kassetter: neste nye NFC-brikke du setter inn blir neste album i lista.</small>
      <textarea style={inp + ';min-height:90px;font-family:inherit'} placeholder={'Linkin Park - Meteora\nAdele - 25'} value={tekst} onInput={(e) => setTekst((e.target as HTMLTextAreaElement).value)} />
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <button style={btn(true)} disabled={!tekst.trim()} onClick={() => void api.nfcImport(tekst).then((r) => { setO(r); setTekst(''); setMsg(`${r.lagt_til} lagt til${r.hoppet_over ? `, ${r.hoppet_over} fantes fra før` : ''}`); })}>Importer</button>
        <label style="display:flex;gap:6px;align-items:center"><input type="checkbox" checked={o.koble_ventende} onChange={(e) => set({ koble_ventende: e.currentTarget.checked })} /> Koble nye brikker til ventende album</label>
        {msg && <small style={'color:' + A}>{msg}</small>}
      </div>
      {o.ventende.length > 0 && <div style="display:flex;flex-direction:column;gap:4px">
        <small style="color:#9a9a96">Ventende ({o.ventende.length}) – sett inn en ny brikke for å koble den første:</small>
        {o.ventende.map((v, i) => <div key={i} style="display:flex;gap:8px;align-items:center"><span style="flex:1">{i === 0 ? '▶ ' : ''}{ventNavn(v)} <small style="color:#9a9a96">· {ventUnder(v)}{v.fra ? ` · fra ${v.fra}` : ''}</small></span><button style={btn()} onClick={() => set({ ventende: o.ventende.filter((_, j) => j !== i) })}>Fjern</button></div>)}
      </div>}
    </div>
  );
}

export function KassettPage() {
  const [tab, setTab] = useState<'k' | 'h' | 'w' | 'y'>(() => (/kassett-del=/.test(location.hash) ? 'k' : 'k'));
  const [del, setDel] = useState<string[] | null>(null);
  const [st, setSt] = useState<NfcStatus | null>(null);
  const [edit, setEdit] = useState<NfcCard | null | 'ny'>(null);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [err, setErr] = useState('');
  const load = () => api.nfc().then((s) => { setSt(s); setErr(''); }).catch((e) => setErr(String((e as Error).message || e)));
  useEffect(() => { void load(); const t = everyVisible(load, 4000); return () => clearInterval(t); }, []);
  const cards = st?.cards ?? [];
  const toggle = (u: string) => { const n = new Set(sel); n.has(u) ? n.delete(u) : n.add(u); setSel(n); };

  if (edit) return <Editor init={edit === 'ny' ? null : edit} onDone={() => { setEdit(null); void load(); }} />;
  const tabs = <div style="display:flex;gap:6px;flex-wrap:wrap"><button style={btn(tab === 'k')} onClick={() => setTab('k')}>Kassetter</button><button style={btn(tab === 'w')} onClick={() => setTab('w')}>Kassett-Wrapped</button><button style={btn(tab === 'h')} onClick={() => setTab('h')}>Skjold Hjul</button><button style={btn(tab === 'y')} onClick={() => setTab('y')}>Kassetthylle</button></div>;
  if (tab === 'y') return <div style="display:flex;flex-direction:column;gap:12px">{tabs}<HyllePanel cards={cards} /></div>;
  if (tab === 'h') return <div style="display:flex;flex-direction:column;gap:12px">{tabs}<HjulPanel cards={cards} /></div>;
  if (tab === 'w') return <div style="display:flex;flex-direction:column;gap:12px">{tabs}<KassettWrapped /></div>;
  return (
    <div style="display:flex;flex-direction:column;gap:12px">
      {tabs}
      <small style="color:#9a9a96">Lag kassetter uten leser: velg «Lag kassett» i Skjold-appen på mobilen og hold telefonen mot NFC-brikken. Her kan du også koble med Kassett-spilleren (læremodus).</small>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <button style={btn(true)} onClick={() => setEdit('ny')}>+ Koble ny kassett</button>
        <button style={btn()} disabled={!cards.length} onClick={() => printLabels(sel.size ? cards.filter((c) => sel.has(c.uid!)) : cards, Math.max(0, Math.min(14, +(prompt('Hopp over hvor mange ruter på arket? (0 = start øverst)', '0') || 0))))}>Skriv ut etiketter{sel.size ? ` (${sel.size})` : ''}</button>
        <button style={btn()} disabled={!cards.length} onClick={() => setDel(sel.size ? [...sel] : cards.map((c) => c.uid!))}>Del{sel.size ? ` (${sel.size})` : ' alle'}</button>
        {st?.active && <small style={'color:' + A}>I spilleren: {cards.find((c) => c.uid === st.active)?.navn ?? st.active}</small>}
      </div>
      {del && <DelDialog uids={del} onClose={() => setDel(null)} />}
      {err && <small style="color:#e06c5a">Fikk ikke kontakt: {err}</small>}
      <MottaPanel onDone={() => void load()} />
      <AlbumPanel />
      <SpolerPanel />
      {!cards.length && !err && <div style={box + ';color:#9a9a96'}>Ingen kassetter ennå. Bygg en Skjold Kassett-spiller (se kabinett/kassett/LES_MEG.md), og koble den første kassetten her.</div>}
      {st?.last?.uid && !st.last.known && <div style={box}>Ukjent kassett {st.last.uid} ble satt inn. <button style={btn()} onClick={() => setEdit('ny')}>Koble den</button></div>}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px">
        {cards.map((c) => (
          <div key={c.uid} style={box + `;display:flex;gap:10px;align-items:center;${c.uid === st?.active ? 'border-color:' + A : ''}`}>
            <input type="checkbox" checked={sel.has(c.uid!)} onChange={() => toggle(c.uid!)} title="Velg for utskrift" />
            {c.omslag ? <img src={img(c.omslag)} style="width:52px;height:52px;border-radius:8px;object-fit:cover" /> : <div style={`width:52px;height:52px;border-radius:8px;background:#111;color:${A};display:grid;place-items:center;font-size:10px`}>SKJOLD</div>}
            <div style="flex:1;min-width:0">
              <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{c.navn}</div>
              <small style="color:#9a9a96">{c.undertittel || LABEL[c.handling]}{c.fra ? ` · fra ${c.fra}` : ''} · spilt {c.spilt ?? 0}×{c.handling === 'album' ? ' · ' + (c.losning?.kilde ? KILDE[c.losning.kilde] : 'ikke slått opp ennå') : ''}</small>
              <div style="display:flex;gap:6px;margin-top:6px">
                <button style={btn()} onClick={() => setEdit(c)}>Endre</button>
                <button style={btn()} onClick={() => setDel([c.uid!])}>Del</button>
                <button style={btn()} onClick={() => { if (confirm(`Slette «${c.navn}»?`)) void api.nfcDelete(c.uid!).then(load); }}>Slett</button>
              </div>
            </div>
          </div>))}
      </div>
    </div>
  );
}
