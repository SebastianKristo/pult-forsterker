// Intercom («Snakk»), låtgjenkjenning («Hva er dette?») med ønskeliste og vinylmodus, dørklokke-overlegg,
// rutiner (hylle på Hjem + redigering) og innstillinger for disse. Daemon: skjold_intercom/recognize/doorbell/routines.
import { useEffect, useRef, useState } from 'preact/hooks';
import { credFor, getBase } from '../lib/api';
import { status } from '../lib/store';

const A = '#d9a441';
const pbtn = `height:38px;padding:0 16px;border-radius:999px;border:none;background:${A};color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap`;
const sbtn = 'height:38px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:13px;cursor:pointer;white-space:nowrap';
const inp = 'height:38px;padding:0 12px;border-radius:10px;border:1px solid #2e2e30;background:#121213;color:#f2f2ee;font-size:13px;min-width:0';
const hint = 'font-size:12.5px;color:#a9a9a3;line-height:1.5';
const CARD = 'display:flex;flex-direction:column;gap:12px;padding:16px;border-radius:16px;background:#141415;border:1px solid #242426';
const KICK = "font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.12em;color:#8b8b86";

async function call<T = any>(path: string, body?: unknown, opt: { method?: string; raw?: BodyInit; timeout?: number } = {}): Promise<T> {
  const base = getBase();
  const ac = new AbortController();
  const tm = setTimeout(() => ac.abort(), opt.timeout ?? 20000);
  try {
    const init: RequestInit = { credentials: credFor(base), signal: ac.signal };
    if (opt.raw !== undefined) { init.method = 'POST'; init.body = opt.raw; }
    else if (body !== undefined) { init.method = opt.method ?? 'POST'; init.headers = { 'Content-Type': 'application/json' }; init.body = JSON.stringify(body); }
    else if (opt.method) init.method = opt.method;
    const r = await fetch(base + path, init);
    const j = await r.json().catch(() => { if (r.ok) throw new Error('Uventet svar fra Skjold'); return {}; });
    if (!r.ok) throw new Error((j as any).error || 'HTTP ' + r.status);
    return j as T;
  } finally { clearTimeout(tm); }
}
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));

// ---------- Intercom ----------
interface Room { id?: string; name: string }
export function TalkButton({ compact }: { compact?: boolean }) {
  const [open, setOpen] = useState(false);
  const [rooms, setRooms] = useState<Room[]>([]);
  const [to, setTo] = useState('all');
  const [rec, setRec] = useState(false);
  const [msg, setMsg] = useState('');
  const [text, setText] = useState('');
  const mr = useRef<MediaRecorder | null>(null), chunks = useRef<Blob[]>([]);
  useEffect(() => { if (open) call<{ rom?: Room[] }>('/api/rom').then((r) => setRooms(r.rom ?? [])).catch(() => setRooms([])); }, [open]);
  const send = async (blob: Blob | null) => {
    setMsg('Sender …');
    try {
      if (blob) {
        const fd = new FormData(); fd.append('to', to); fd.append('file', blob, 'melding.' + (blob.type.includes('mp4') ? 'm4a' : 'webm'));
        await call('/api/intercom', undefined, { raw: fd });
      } else await call('/api/intercom', { to, text });
      setMsg('Sendt'); setText('');
    } catch (e) { setMsg('Feil: ' + errText(e)); }
  };
  const start = async () => {
    setMsg('');
    try {
      const st = await navigator.mediaDevices.getUserMedia({ audio: true });
      const m = new MediaRecorder(st); chunks.current = [];
      m.ondataavailable = (e) => { if (e.data.size) chunks.current.push(e.data); };
      m.onstop = () => { st.getTracks().forEach((t) => t.stop()); const b = new Blob(chunks.current, { type: m.mimeType || 'audio/webm' }); if (b.size > 2000) void send(b); else setMsg('For kort – hold inne mens du snakker'); };
      m.start(); mr.current = m; setRec(true);
    } catch (e) { setMsg('Får ikke tilgang til mikrofonen: ' + errText(e)); }
  };
  const stop = () => { if (mr.current && mr.current.state !== 'inactive') mr.current.stop(); setRec(false); };
  return (
    <>
      <button onClick={() => setOpen(true)} title="Snakk til et rom" aria-label="Snakk" style={compact ? sbtn + ';width:38px;padding:0;display:grid;place-items:center' : sbtn}>
        {compact ? '🎙' : '🎙 Snakk'}
      </button>
      {open && <div onClick={() => { stop(); setOpen(false); }} style="position:fixed;inset:0;z-index:80;background:rgba(0,0,0,.55);display:flex;align-items:center;justify-content:center;padding:16px">
        <div onClick={(e) => e.stopPropagation()} style={CARD + ';width:360px;max-width:100%'}>
          <span style={KICK}>INTERCOM</span>
          <span style="font-size:18px;font-weight:600">Snakk til</span>
          <div class="row gap8" style={{ flexWrap: 'wrap' }}>
            {[{ id: 'all', name: 'Alle rom' }, { id: 'here', name: 'Dette rommet' }, ...rooms].map((r) => (
              <button key={r.id ?? r.name} onClick={() => setTo(r.id ?? r.name)} style={(to === (r.id ?? r.name) ? pbtn : sbtn) + ';height:32px'}>{r.name}</button>
            ))}
          </div>
          <button onPointerDown={() => void start()} onPointerUp={stop} onPointerLeave={() => rec && stop()}
            style={`height:96px;border-radius:20px;border:none;font-size:15px;font-weight:600;cursor:pointer;touch-action:none;background:${rec ? '#e05a4a' : A};color:#0b0b0c`}>
            {rec ? 'Snakker … slipp for å sende' : 'Hold inne og snakk'}
          </button>
          <div class="row gap8"><input value={text} onInput={(e) => setText(e.currentTarget.value)} placeholder="… eller skriv en melding" style={inp + ';flex:1'} />
            <button disabled={!text.trim()} onClick={() => void send(null)} style={pbtn}>Les opp</button></div>
          {msg && <span style={hint}>{msg}</span>}
          <span style={hint}>Musikken dempes mens meldingen spilles, med et lite «ding» først.</span>
          <button onClick={() => setOpen(false)} style={sbtn}>Lukk</button>
        </div>
      </div>}
    </>
  );
}

// ---------- Låtgjenkjenning + vinyl ----------
interface Hit { title: string; artist?: string; album?: string; art?: string; via?: string; t?: number }
export function RecognizeBox() {
  const s = status.value as any;
  const [busy, setBusy] = useState(false), [msg, setMsg] = useState(''), [hit, setHit] = useState<Hit | null>(null);
  const shown: Hit | null = hit ?? s?.recognized ?? null;
  const run = async () => {
    setBusy(true); setMsg('Lytter i ca. 12 sekunder …');
    try { const r = await call<Hit & { found?: boolean; error?: string }>('/api/recognize', {}, { timeout: 45000 }); if (r && r.title) { setHit(r); setMsg(''); } else setMsg('Fant ingen treff. Prøv igjen litt senere i låten.'); }
    catch (e) { setMsg(errText(e)); } finally { setBusy(false); }
  };
  const wish = async () => { try { const r = await call<{ starred?: boolean; navidrome?: boolean }>('/api/recognize', { wish: shown }); setMsg(r.starred || r.navidrome ? 'Stjernemerket i Navidrome og lagt i ønskelisten' : 'Lagt i ønskelisten'); } catch (e) { setMsg(errText(e)); } };
  const vinyl = s?.vinyl as { tracks?: { n?: number; title: string; length?: number }[]; pos?: number } | undefined;
  return (
    <div class="col gap8">
      <div class="row gap10" style={{ flexWrap: 'wrap', alignItems: 'center' }}>
        <button disabled={busy} onClick={() => void run()} style={sbtn}>{busy ? 'Lytter …' : 'Hva er dette?'}</button>
        {shown && <button onClick={() => void wish()} style={sbtn}>☆ Lagre i ønskeliste</button>}
      </div>
      {shown && <div class="row gap10" style={{ alignItems: 'center' }}>
        {shown.art && <img src={shown.art} alt="" style="width:44px;height:44px;border-radius:8px;object-fit:cover" />}
        <span class="col" style={{ minWidth: 0 }}><b class="ellip">{shown.title}</b><span class="ellip muted" style={{ fontSize: '12px' }}>{[shown.artist, shown.album].filter(Boolean).join(' · ')}{shown.via ? ' · via ' + shown.via : ''}</span></span>
      </div>}
      {msg && <span style={hint}>{msg}</span>}
      {vinyl?.tracks?.length ? <div class="col" style={{ gap: '2px' }}>
        <span style={KICK}>VINYL · SPOR</span>
        {vinyl.tracks.map((t, i) => <span key={i} style={`font-size:13px;padding:3px 0;color:${i === vinyl.pos ? A : '#c9c9c4'}`}>{(t.n ?? i + 1) + '. ' + t.title}</span>)}
      </div> : null}
    </div>
  );
}

export function WishlistPanel() {
  const [list, setList] = useState<Hit[]>([]);
  const load = () => call<{ wishlist: Hit[] }>('/api/recognize').then((r) => setList(r.wishlist ?? [])).catch(() => setList([]));
  useEffect(() => { void load(); }, []);
  return (
    <div style={CARD}>
      <span style="font-size:15px;font-weight:600">Ønskeliste</span>
      {list.length ? list.map((h, i) => <div key={i} class="row between" style={{ alignItems: 'center', gap: '10px' }}>
        <span class="col" style={{ minWidth: 0 }}><b class="ellip">{h.title}</b><span class="ellip muted" style={{ fontSize: '12px' }}>{h.artist}</span></span>
        <button onClick={() => void call('/api/recognize', { remove: i }).then(load)} style={sbtn + ';height:30px'}>Fjern</button>
      </div>) : <span style={hint}>Tom. Bruk «Hva er dette?» i spilleren og «Lagre i ønskeliste».</span>}
    </div>
  );
}

// ---------- Dørklokke ----------
export function DoorbellOverlay() {
  const db = (status.value as any)?.doorbell as { t: number; camera: boolean; seconds: number } | null | undefined;
  const [closed, setClosed] = useState(0);
  const [tick, setTick] = useState(0);
  useEffect(() => { if (!db?.camera) return; const iv = setInterval(() => setTick((x) => x + 1), 1000); return () => clearInterval(iv); }, [db?.t, db?.camera]);
  if (!db || closed === db.t) return null;
  return (
    <div style="position:fixed;inset:0;z-index:90;background:rgba(0,0,0,.72);display:flex;align-items:center;justify-content:center;padding:16px" onClick={() => setClosed(db.t)}>
      <div style={CARD + ';width:640px;max-width:100%;align-items:center;text-align:center'} onClick={(e) => e.stopPropagation()}>
        <span style={KICK}>DØRKLOKKE</span>
        <span style="font-size:24px;font-weight:600">Det ringer på døren</span>
        {db.camera ? <img src={getBase() + '/api/doorbell/camera?t=' + db.t + '-' + tick} alt="Kamera ved døren" style="width:100%;border-radius:12px;background:#0b0b0c;aspect-ratio:16/9;object-fit:cover" />
          : <span style={hint}>Ingen kamera er satt opp.</span>}
        <button onClick={() => setClosed(db.t)} style={pbtn}>Lukk</button>
      </div>
    </div>
  );
}

// ---------- Rutiner ----------
interface Step { type: string; [k: string]: unknown }
interface Routine { id: string; navn: string; ikon?: string; steg: Step[] }
/** Ikonene rutinene kan ha (samme navn som ICONS i pi/skjold_routines.py). */
const ROUTINE_ICON: Record<string, string> = {
  sun: 'M12 4V2M12 22v-2M4 12H2M22 12h-2M5.6 5.6 4.2 4.2M19.8 19.8l-1.4-1.4M5.6 18.4l-1.4 1.4M19.8 4.2l-1.4 1.4M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10z',
  moon: 'M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z',
  music: 'M9 18V5l12-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM21 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z',
  radio: 'M4 9h16v11H4zM8 9l9-5M14 13h3M14 16h3M9.5 12.5a2 2 0 1 0 0 4 2 2 0 0 0 0-4z',
  coffee: 'M4 8h13v6a5 5 0 0 1-5 5H9a5 5 0 0 1-5-5zM17 10h1.5a2.5 2.5 0 0 1 0 5H17M8 2v3M12 2v3',
  bed: 'M3 18V7M3 13h18v5M21 13a3 3 0 0 0-3-3h-7v3M7 11.5a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z',
  home: 'M4 11l8-7 8 7v9H4zM10 20v-5h4v5',
  party: 'M4 20l4.5-12L16 15.5zM14 4l.5 2M19 6l-2 1.5M20 11l-2-.5M11 2.5 11.5 5',
  news: 'M4 5h13v14H6a2 2 0 0 1-2-2zM17 9h3v8a2 2 0 0 1-2 2M8 9h5M8 13h5M8 16h3',
  star: 'M12 3l2.8 5.7 6.2.9-4.5 4.4 1.1 6.2L12 17.3 6.4 20.2l1.1-6.2L3 9.6l6.2-.9z',
};

const ICON_NAME: Record<string, string> = { sun: 'Sol', moon: 'Måne', music: 'Musikk', radio: 'Radio', coffee: 'Kaffe', bed: 'Seng', home: 'Hjem', party: 'Fest', news: 'Nyheter', star: 'Stjerne' };

export function RoutinesShelf() {
  const [rs, setRs] = useState<Routine[]>([]), [msg, setMsg] = useState('');
  useEffect(() => { call<{ routines: Routine[] }>('/api/routines').then((r) => setRs(r.routines ?? [])).catch(() => setRs([])); }, []);
  if (!rs.length) return null;
  const run = async (r: Routine) => { setMsg('Kjører «' + r.navn + '» …'); try { await call('/api/routines/' + encodeURIComponent(r.id) + '/run', {}); setMsg('«' + r.navn + '» startet'); } catch (e) { setMsg(errText(e)); } };
  return (
    <section class="col gap12">
      <div class="row between" style={{ alignItems: 'baseline' }}><span style="font-size:17px;font-weight:600">Rutiner</span>{msg && <span style={hint}>{msg}</span>}</div>
      <div class="row gap10" style={{ flexWrap: 'wrap' }}>
        {rs.map((r) => <button key={r.id} onClick={() => void run(r)} style="display:flex;flex-direction:column;align-items:flex-start;gap:6px;min-width:150px;padding:14px 16px;border-radius:16px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;cursor:pointer;text-align:left">
          <span style="width:36px;height:36px;border-radius:10px;background:#1c170d;border:1px solid #5a4420;color:#f0c46a;display:flex;align-items:center;justify-content:center"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"><path d={ROUTINE_ICON[r.ikon ?? ''] ?? ROUTINE_ICON.star} /></svg></span><b style="font-size:14px">{r.navn}</b><span style={hint}>{r.steg.length} steg</span>
        </button>)}
      </div>
    </section>
  );
}

const STEP_HELP: Record<string, string> = {
  power: '{"on":true}', input: '{"input":"radio"}', preset: '{"n":1}', play_url: '{"url":"https://…"}', nrk: '{"id":"…"}', ma: '{"uri":"…"}',
  volume: '{"volume":25}', wait: '{"s":5}', eq: '{"preset":2}', announce: '{"text":"God morgen"}', room: '{"room":"Kjøkken","steps":[…]}'
};
export function RoutinesPanel() {
  const [d, setD] = useState<{ routines: Routine[]; types: string[]; icons: string[] } | null>(null);
  const [edit, setEdit] = useState<Routine | null>(null), [json, setJson] = useState(''), [msg, setMsg] = useState('');
  const load = () => call('/api/routines').then(setD).catch((e) => setMsg(errText(e)));
  useEffect(() => { void load(); }, []);
  const open = (r: Routine) => { setEdit(r); setJson(JSON.stringify(r.steg, null, 1)); setMsg(''); };
  const save = async () => {
    if (!edit) return;
    try { const steg = JSON.parse(json); await call('/api/routines', { ...edit, steg }); setEdit(null); setMsg('Lagret'); void load(); }
    catch (e) { setMsg('Kunne ikke lagre: ' + errText(e)); }
  };
  return (
    <div style={CARD}>
      <span style="font-size:15px;font-weight:600">Rutiner</span>
      <span style={hint}>Start med ett trykk fra Hjem, med et langt trykk på en S1-knapp, fra Siri/Snarveier, Android-snarveier, Home Assistant (skjold.run_routine) eller Homey.</span>
      {d?.routines.map((r) => <div key={r.id} class="row between" style={{ alignItems: 'center', gap: '8px' }}>
        <span style="display:inline-flex;align-items:center;gap:8px"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f0c46a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d={ROUTINE_ICON[r.ikon ?? ''] ?? ROUTINE_ICON.star} /></svg>{r.navn}<span class="muted" style={{ fontSize: '12px' }}>{' · ' + r.steg.length + ' steg'}</span></span>
        <span class="row gap8">
          <button onClick={() => void call('/api/routines/' + encodeURIComponent(r.id) + '/run', {}).then(() => setMsg('Startet «' + r.navn + '»')).catch((e) => setMsg(errText(e)))} style={sbtn + ';height:30px'}>Kjør</button>
          <button onClick={() => open(r)} style={sbtn + ';height:30px'}>Endre</button>
          <button onClick={() => void call('/api/routines/' + encodeURIComponent(r.id), undefined, { method: 'DELETE' }).then(load)} style={sbtn + ';height:30px'}>Slett</button>
        </span>
      </div>)}
      <button onClick={() => open({ id: '', navn: 'Ny rutine', ikon: 'star', steg: [] })} style={sbtn}>+ Ny rutine</button>
      {edit && <div class="col gap8">
        <div class="row gap8"><select value={edit.ikon ?? 'star'} onChange={(e) => setEdit({ ...edit, ikon: e.currentTarget.value })} style={inp + ';width:110px'} aria-label="Ikon">{Object.keys(ROUTINE_ICON).map((k) => <option key={k} value={k}>{ICON_NAME[k] ?? k}</option>)}</select>
          <input value={edit.navn} onInput={(e) => setEdit({ ...edit, navn: e.currentTarget.value })} style={inp + ';flex:1'} aria-label="Navn" /></div>
        <textarea value={json} onInput={(e) => setJson(e.currentTarget.value)} rows={8} style={inp + ";height:auto;padding:10px;font-family:'IBM Plex Mono',monospace;font-size:12px"} />
        <span style={hint}>Steg som liste. Typer: {(d?.types ?? Object.keys(STEP_HELP)).map((t) => t + (STEP_HELP[t] ? ' ' + STEP_HELP[t] : '')).join(' · ')}</span>
        <div class="row gap8"><button onClick={() => void save()} style={pbtn}>Lagre</button><button onClick={() => setEdit(null)} style={sbtn}>Avbryt</button></div>
      </div>}
      {msg && <span style={hint}>{msg}</span>}
    </div>
  );
}

// ---------- Innstillinger: dørklokke, gjenkjenning, S1-knapper ----------
export function DoorbellPanel() {
  const [c, setC] = useState<Record<string, any> | null>(null), [msg, setMsg] = useState('');
  useEffect(() => { call('/api/doorbell').then(setC).catch((e) => setMsg(errText(e))); }, []);
  if (!c) return <div style={CARD}><span style={hint}>{msg || 'Laster …'}</span></div>;
  const up = (k: string, v: unknown) => setC({ ...c, [k]: v });
  const save = async () => { try { setC(await call('/api/doorbell', c)); setMsg('Lagret'); } catch (e) { setMsg(errText(e)); } };
  const field = (k: string, label: string, ph = '', type = 'text') => (
    <label class="col gap4" style={{ fontSize: '12px', color: '#8b8b86' }}>{label}<input type={type} value={c[k] ?? ''} placeholder={ph} onInput={(e) => up(k, type === 'number' ? +e.currentTarget.value : e.currentTarget.value)} style={inp} /></label>);
  return (
    <div style={CARD}>
      <div class="row between" style={{ alignItems: 'center' }}><span style="font-size:15px;font-weight:600">Dørklokke</span>
        <label class="row gap8" style={{ fontSize: '13px' }}><input type="checkbox" checked={!!c.enabled} onChange={(e) => up('enabled', e.currentTarget.checked)} />På</label></div>
      <span style={hint}>Når noen ringer på, dempes musikken i alle rom, det spilles et signal og kamerabildet vises på Touch. Utløses fra Home Assistant, Homey eller en webhook til {getBase() || 'http://<skjold>:8765'}/api/doorbell.</span>
      {Object.keys(c).filter((k) => k !== 'enabled').map((k) => field(k, k.replace(/_/g, ' '), '', typeof c[k] === 'number' ? 'number' : 'text'))}
      <div class="row gap8"><button onClick={() => void save()} style={pbtn}>Lagre</button><button onClick={() => void call('/api/doorbell', { test: true }).then(() => setMsg('Test sendt')).catch((e) => setMsg(errText(e)))} style={sbtn}>Test ring</button></div>
      {msg && <span style={hint}>{msg}</span>}
    </div>
  );
}

// ---------- Senk musikken og si … (/api/duck) ----------
export function DuckPanel() {
  const [c, setC] = useState<Record<string, any> | null>(null), [msg, setMsg] = useState(''), [rom, setRom] = useState('');
  useEffect(() => { call<Record<string, any>>('/api/duck/innstillinger').then((r) => { setC(r); setRom((r.rom ?? []).join('\n')); }).catch(() => setC(null)); }, []);
  if (!c) return null;
  const set = async (b: Record<string, unknown>) => { try { setC(await call('/api/duck/innstillinger', b)); setMsg('Lagret'); } catch (e) { setMsg(errText(e)); } };
  const box = (k: string, label: string) => <label class="row gap8" style={{ fontSize: '13px' }}><input type="checkbox" checked={!!c[k]} onChange={(e) => void set({ [k]: e.currentTarget.checked })} />{label}</label>;
  return (
    <div style={CARD}>
      <div class="row between" style={{ alignItems: 'center' }}><span style="font-size:15px;font-weight:600">Senk musikken og si …</span>{box('på', 'På')}</div>
      <span style={hint}>Musikken senkes, varselet leses opp eller spilles, og volumet løftes mykt igjen. Brukes av dørklokka, Home Assistant (skjold.duck), Homey («Senk musikken og si …»), appen når telefonen ringer, og {getBase() || 'http://<skjold>:8765'}/api/duck.</span>
      <div class="row gap8" style={{ flexWrap: 'wrap' }}>{box('dørklokke', 'Dørklokke')}{box('ha', 'Home Assistant')}{box('homey', 'Homey')}{box('telefon', 'Telefonsamtaler')}</div>
      <label class="row gap8" style={{ fontSize: '13px', alignItems: 'center' }}>Senk med <input type="range" min={-40} max={-6} step={1} value={c.db} onChange={(e) => void set({ db: +e.currentTarget.value })} style={{ flex: 1 }} /> <span style={{ width: '52px', textAlign: 'right' }}>{c.db} dB</span></label>
      <label class="col gap4" style={{ fontSize: '12px', color: '#8b8b86' }}>Også i disse rommene (adresse per linje, f.eks. http://skjold-kjokken.local:8765)
        <textarea value={rom} onInput={(e) => setRom(e.currentTarget.value)} rows={2} style={inp + ';height:auto;padding:8px 12px'} /></label>
      <div class="row gap8"><button onClick={() => void set({ rom: rom.split(/\s+/).filter(Boolean) })} style={pbtn}>Lagre rom</button>
        <button onClick={() => void call('/api/duck', { tekst: 'Dette er en test fra Skjold', kilde: 'api' }).then(() => setMsg('Test sendt')).catch((e) => setMsg(errText(e)))} style={sbtn}>Test</button></div>
      {msg && <span style={hint}>{msg}</span>}
    </div>
  );
}

export function RecognizeSettingsPanel() {
  const [c, setC] = useState<{ recognize: Record<string, any>; s1_hold: Record<string, string> } | null>(null), [msg, setMsg] = useState('');
  const [rs, setRs] = useState<Routine[]>([]);
  useEffect(() => { call('/api/features').then(setC).catch((e) => setMsg(errText(e))); call<{ routines: Routine[] }>('/api/routines').then((r) => setRs(r.routines ?? [])).catch(() => {}); }, []);
  if (!c) return <div style={CARD}><span style={hint}>{msg || 'Laster …'}</span></div>;
  const r = c.recognize;
  const upR = (k: string, v: unknown) => setC({ ...c, recognize: { ...r, [k]: v } });
  const save = async () => { try { setC(await call('/api/features', c)); setMsg('Lagret'); } catch (e) { setMsg(errText(e)); } };
  const chk = (k: string, l: string) => <label class="row gap8" style={{ fontSize: '13px' }}><input type="checkbox" checked={!!r[k]} onChange={(e) => upR(k, e.currentTarget.checked)} />{l}</label>;
  return (
    <div style={CARD}>
      <span style="font-size:15px;font-weight:600">Låtgjenkjenning og vinylmodus</span>
      <span style={hint}>Gratis nøkkel fra acoustid.org (AcoustID) eller audd.io (AudD, bedre for radio/live).</span>
      <label class="col gap4" style={{ fontSize: '12px', color: '#8b8b86' }}>AcoustID-nøkkel<input value={r.acoustid_key ?? ''} onInput={(e) => upR('acoustid_key', e.currentTarget.value)} style={inp} /></label>
      <label class="col gap4" style={{ fontSize: '12px', color: '#8b8b86' }}>AudD-token<input value={r.audd_token ?? ''} onInput={(e) => upR('audd_token', e.currentTarget.value)} style={inp} /></label>
      <span style={KICK}>VINYLMODUS (GJENKJENN ALBUM AUTOMATISK)</span>
      <div class="row gap16" style={{ flexWrap: 'wrap' }}>{chk('vinyl_aux', 'AUX 1')}{chk('vinyl_aux2', 'AUX 2')}{chk('vinyl_usb', 'USB')}{chk('vinyl_manual', 'Bare når jeg trykker')}</div>
      <span style={KICK}>S1: HOLD KNAPPEN INNE FOR Å KJØRE RUTINE</span>
      {(['aux', 'usb'] as const).map((b) => <label key={b} class="row gap8" style={{ fontSize: '13px', alignItems: 'center' }}>{b.toUpperCase()}
        <select value={c.s1_hold[b] ?? ''} onChange={(e) => setC({ ...c, s1_hold: { ...c.s1_hold, [b]: e.currentTarget.value } })} style={inp}>
          <option value="">Ingen</option>{rs.map((x) => <option key={x.id} value={x.id}>{x.navn}</option>)}
        </select></label>)}
      <div class="row gap8"><button onClick={() => void save()} style={pbtn}>Lagre</button></div>
      {msg && <span style={hint}>{msg}</span>}
    </div>
  );
}
