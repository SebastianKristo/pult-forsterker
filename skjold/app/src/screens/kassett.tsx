/** Skjold Kassett: NFC-kassetter koblet til radio, NRK, Navidrome, Music Assistant eller rutiner. */
import { useEffect, useState } from 'preact/hooks';
import { api, type NfcCard, type NfcHandling, type NfcStatus, type Routine } from '../lib/api';
import { ndCover, ndConfigured, ndPlaylists, ndSearch } from '../lib/navidrome';

const A = '#e8b04a';
const box = 'background:#141415;border:1px solid #242426;border-radius:14px;padding:14px';
const inp = 'background:#0e0e0f;border:1px solid #2a2a2c;border-radius:8px;color:#f2f2ee;padding:8px 10px;font:inherit';
const btn = (on = false) => `padding:8px 14px;border-radius:9px;border:1px solid ${on ? A : '#2a2a2c'};background:${on ? '#1c170d' : '#1a1a1b'};color:#f2f2ee;cursor:pointer;font:inherit`;
const LABEL: Record<NfcHandling, string> = { preset: 'Radio', play_url: 'Strøm', nrk: 'NRK', ma_uri: 'Music Assistant', navidrome_album: 'Navidrome-album', navidrome_playlist: 'Navidrome-spilleliste', routine: 'Rutine' };

type Src = 'nå' | 'radio' | 'nrk' | 'nd' | 'ma' | 'rutine';
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

function printLabels(cards: NfcCard[]): void {
  const esc = (s: string) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]!));
  const cells = cards.map((c) => `<div class="l">${c.omslag ? `<img src="${esc(c.omslag)}">` : '<div class="ph">SKJOLD</div>'}<b>${esc(c.navn)}</b><i>${esc(c.undertittel || '')}</i></div>`).join('');
  const w = window.open('', '_blank'); if (!w) return;
  w.document.write(`<!doctype html><meta charset="utf-8"><title>Kassett-etiketter</title><style>
@page{size:A4;margin:10mm}body{margin:0;font-family:system-ui,sans-serif}
.g{display:grid;grid-template-columns:repeat(4,44mm);gap:4mm}
.l{width:44mm;height:52mm;border:0.2mm dashed #999;box-sizing:border-box;padding:2mm;display:flex;flex-direction:column;overflow:hidden;break-inside:avoid}
.l img,.ph{width:40mm;height:40mm;object-fit:cover;border-radius:1mm}.ph{background:#111;color:#e8b04a;display:grid;place-items:center;font-weight:700;letter-spacing:2px}
b{font-size:8pt;margin-top:1mm;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}i{font-size:6.5pt;color:#555;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
</style><div class="g">${cells}</div><script>Promise.all([...document.images].map(i=>i.complete?0:new Promise(r=>{i.onload=i.onerror=r}))).then(()=>print())</script>`);
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
  useEffect(() => { api.routines().then((r) => setRoutines(Array.isArray(r) ? r : r.routines ?? [])).catch(() => {}); }, []);
  useEffect(() => {
    if (src === 'nå' || (src !== 'rutine' && src !== 'nd' && q.trim().length < 2)) { setHits([]); return; }
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

  const SRC: [Src, string][] = [['nå', 'Det som spiller nå'], ['radio', 'Radio'], ['nrk', 'NRK'], ['nd', 'Navidrome'], ['ma', 'Music Assistant'], ['rutine', 'Rutine']];
  return (
    <div style={box + ';display:flex;flex-direction:column;gap:12px'}>
      <b>{init?.uid ? 'Rediger kassett' : 'Koble ny kassett'}</b>
      <div style="display:flex;flex-wrap:wrap;gap:6px">{SRC.filter(([k]) => !(init?.uid && k === 'nå')).map(([k, t]) => <button key={k} style={btn(src === k)} onClick={() => { setSrc(k); setHits([]); }}>{t}</button>)}</div>
      {src !== 'nå' && <input style={inp} placeholder="Søk …" value={q} onInput={(e) => setQ((e.target as HTMLInputElement).value)} />}
      {src === 'nd' && !ndConfigured() && <small style="color:#9a9a96">Navidrome er ikke satt opp.</small>}
      {busy && <small style="color:#9a9a96">Søker …</small>}
      {hits.length > 0 && <div style="max-height:260px;overflow:auto;display:flex;flex-direction:column;gap:4px">{hits.map((h, i) => (
        <button key={i} style={btn(pick?.verdi === h.verdi) + ';display:flex;gap:10px;align-items:center;text-align:left'} onClick={() => { setPick(h); if (!navn) setNavn(h.navn); }}>
          {h.omslag ? <img src={h.omslag} style="width:36px;height:36px;border-radius:6px;object-fit:cover" /> : <span style="width:36px;height:36px;border-radius:6px;background:#222" />}
          <span><div>{h.navn}</div><small style="color:#9a9a96">{h.undertittel} · {LABEL[h.handling]}</small></span>
        </button>))}</div>}
      {pick && src !== 'nå' && <small style={'color:' + A}>Valgt: {pick.navn} ({LABEL[pick.handling]})</small>}
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

export function KassettPage() {
  const [st, setSt] = useState<NfcStatus | null>(null);
  const [edit, setEdit] = useState<NfcCard | null | 'ny'>(null);
  const [sel, setSel] = useState<Set<string>>(new Set());
  const [err, setErr] = useState('');
  const load = () => api.nfc().then((s) => { setSt(s); setErr(''); }).catch((e) => setErr(String((e as Error).message || e)));
  useEffect(() => { void load(); const t = setInterval(load, 4000); return () => clearInterval(t); }, []);
  const cards = st?.cards ?? [];
  const toggle = (u: string) => { const n = new Set(sel); n.has(u) ? n.delete(u) : n.add(u); setSel(n); };

  if (edit) return <Editor init={edit === 'ny' ? null : edit} onDone={() => { setEdit(null); void load(); }} />;
  return (
    <div style="display:flex;flex-direction:column;gap:12px">
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <button style={btn(true)} onClick={() => setEdit('ny')}>+ Koble ny kassett</button>
        <button style={btn()} disabled={!cards.length} onClick={() => printLabels(sel.size ? cards.filter((c) => sel.has(c.uid!)) : cards)}>Skriv ut etiketter{sel.size ? ` (${sel.size})` : ''}</button>
        {st?.active && <small style={'color:' + A}>I spilleren: {cards.find((c) => c.uid === st.active)?.navn ?? st.active}</small>}
      </div>
      {err && <small style="color:#e06c5a">Fikk ikke kontakt: {err}</small>}
      {!cards.length && !err && <div style={box + ';color:#9a9a96'}>Ingen kassetter ennå. Bygg en Skjold Kassett-spiller (se kabinett/kassett/LES_MEG.md), og koble den første kassetten her.</div>}
      {st?.last?.uid && !st.last.known && <div style={box}>Ukjent kassett {st.last.uid} ble satt inn. <button style={btn()} onClick={() => setEdit('ny')}>Koble den</button></div>}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px">
        {cards.map((c) => (
          <div key={c.uid} style={box + `;display:flex;gap:10px;align-items:center;${c.uid === st?.active ? 'border-color:' + A : ''}`}>
            <input type="checkbox" checked={sel.has(c.uid!)} onChange={() => toggle(c.uid!)} title="Velg for utskrift" />
            {c.omslag ? <img src={c.omslag} style="width:52px;height:52px;border-radius:8px;object-fit:cover" /> : <div style={`width:52px;height:52px;border-radius:8px;background:#111;color:${A};display:grid;place-items:center;font-size:10px`}>SKJOLD</div>}
            <div style="flex:1;min-width:0">
              <div style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{c.navn}</div>
              <small style="color:#9a9a96">{c.undertittel || LABEL[c.handling]} · spilt {c.spilt ?? 0}×</small>
              <div style="display:flex;gap:6px;margin-top:6px">
                <button style={btn()} onClick={() => setEdit(c)}>Endre</button>
                <button style={btn()} onClick={() => { if (confirm(`Slette «${c.navn}»?`)) void api.nfcDelete(c.uid!).then(load); }}>Slett</button>
              </div>
            </div>
          </div>))}
      </div>
    </div>
  );
}
