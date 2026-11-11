// Sanglek, lydbøker (Audiobookshelf), køhistorikk, sikkerhetsmodus og bass management.
// Daemon: pi/skjold_quiz.py (/api/quiz), skjold_abs.py (/api/abs), skjold_qhist.py (/api/qhist),
// skjold_security.py (/api/security), skjold_bassmgmt.py (/api/bass).
import { useEffect, useRef, useState } from 'preact/hooks';
import { apiPost, apiReq, getBase } from '../lib/api';
import { qrMatrix } from '../lib/qr';
import { recordMic } from '../lib/roomeq';
import { go, everyVisible } from '../lib/store';

const A = '#d9a441';
const card = 'display:flex;flex-direction:column;gap:12px;padding:16px;border-radius:14px;background:#141415;border:1px solid #242426';
const muted = 'font-size:12px;color:#8f8f8a;line-height:1.45';
const inp = 'height:36px;padding:0 12px;border-radius:8px;border:1px solid #2e2e30;background:#0f0f10;color:#f2f2ee;font-size:14px;outline:none;min-width:0';
const btn = (on = false) => `height:34px;padding:0 12px;border-radius:8px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#2a2112' : '#1b1b1c'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:13px;cursor:pointer;white-space:nowrap`;
const pbtn = `height:38px;padding:0 16px;border-radius:999px;border:none;background:${A};color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap`;
const err = (e: unknown): string => (e instanceof Error ? e.message : String(e));
const tid = (s: number) => { const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60); return h ? `${h} t ${m} min` : `${m} min`; };
const klokke = (t: number) => new Date(t * 1000).toLocaleTimeString('nb-NO', { hour: '2-digit', minute: '2-digit' });

function Qr({ text, size = 180 }: { text: string; size?: number }) {
  const m = qrMatrix(text), n = m.length, c = size / (n + 8);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label="QR-kode" style="background:#fff;border-radius:10px">
      {m.flatMap((row, y) => row.map((on, x) => (on ? <rect key={x + ',' + y} x={(x + 4) * c} y={(y + 4) * c} width={c + 0.3} height={c + 0.3} fill="#000" /> : null)))}
    </svg>
  );
}

// ---------- Sanglek ----------
interface QState { aktiv: boolean; runde: number; runder: number; fase: string; sekunder: number; spillere: { navn: string; poeng: number; svart: boolean }[]; svar?: { artist: string; tittel: string; album: string; cover: string }; fasit?: Record<string, string> }

export function QuizPage() {
  const [s, setS] = useState<QState | null>(null), [msg, setMsg] = useState('');
  const [meg, setMeg] = useState(() => { try { return localStorage.getItem('skjold-sanglek-navn') || ''; } catch { return ''; } });
  const [navn, setNavn] = useState(meg), [svar, setSvar] = useState('');
  const [kilde, setKilde] = useState('tilfeldig'), [tiar, setTiar] = useState(1990), [runder, setRunder] = useState(10);
  const vert = !location.hash.includes('spiller');
  const act = async (b: Record<string, unknown>) => { try { setS(await apiPost<QState>('/api/quiz', b)); setMsg(''); } catch (e) { setMsg(err(e)); } };
  useEffect(() => { const f = () => apiReq<QState>('/api/quiz').then(setS).catch(() => {}); f(); const t = everyVisible(f, 1500); return () => clearInterval(t); }, []);
  const lenke = `${location.origin}${location.pathname}#sanglek-spiller`;
  const bliMed = async () => { await act({ action: 'bli_med', navn }); setMeg(navn); try { localStorage.setItem('skjold-sanglek-navn', navn); } catch { /* privat modus */ } };
  if (!s) return <span style={muted}>Henter …</span>;
  const meStatus = s.spillere.find((p) => p.navn === meg);
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      {vert && <div style={card}>
        <span style="font-size:16px;font-weight:600">Sanglek</span>
        <span style={muted}>Skjold spiller {s.sekunder || 10} sekunder av en tilfeldig låt fra Navidrome. Gjett artist og tittel – 1 poeng for hver.</span>
        {!s.aktiv && <>
          <div style="display:flex;gap:6px;flex-wrap:wrap">{([['tilfeldig', 'Tilfeldige låter'], ['tiår', 'Et tiår']] as const).map(([k, n]) => <button key={k} style={btn(kilde === k)} onClick={() => setKilde(k)}>{n}</button>)}</div>
          {kilde === 'tiår' && <div style="display:flex;gap:6px;flex-wrap:wrap">{[1960, 1970, 1980, 1990, 2000, 2010, 2020].map((y) => <button key={y} style={btn(tiar === y)} onClick={() => setTiar(y)}>{String(y).slice(2)}-tallet</button>)}</div>}
          <label style="display:flex;gap:8px;align-items:center;font-size:13px">Runder <input type="number" min={1} max={50} value={runder} onInput={(e) => setRunder(+e.currentTarget.value)} style={inp + ';width:80px'} /></label>
          <button style={pbtn} onClick={() => void act({ action: 'start', kilde, tiår: tiar, runder })}>Start sanglek</button>
        </>}
        {s.aktiv && <>
          <span style="font-size:14px">Runde {s.runde} av {s.runder} · {s.fase === 'spiller' ? 'spiller …' : s.fase === 'gjett' ? 'gjett nå!' : s.fase === 'vist' ? 'svaret er vist' : s.fase}</span>
          <div style="display:flex;gap:8px;flex-wrap:wrap">
            <button style={pbtn} onClick={() => void act({ action: 'spill' })}>{s.runde === 0 ? 'Spill første låt' : s.runde >= s.runder && s.fase === 'vist' ? 'Ferdig' : 'Neste låt'}</button>
            {s.runde > 0 && <button style={btn()} onClick={() => void act({ action: 'spill', igjen: true })}>Spill igjen</button>}
            {s.runde > 0 && s.fase !== 'vist' && <button style={btn(true)} onClick={() => void act({ action: 'vis' })}>Vis svar</button>}
            <button style={btn()} onClick={() => void act({ action: 'slutt' })}>Avslutt</button>
          </div>
        </>}
        {s.svar && <div style="display:flex;gap:12px;align-items:center">{s.svar.cover && <img src={s.svar.cover} width={72} height={72} style="border-radius:8px;object-fit:cover" alt="" />}<div style="display:flex;flex-direction:column"><b style="font-size:16px">{s.svar.tittel}</b><span>{s.svar.artist}</span><span style={muted}>{s.svar.album}</span></div></div>}
        <div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap"><Qr text={lenke} size={150} /><span style={muted}>Spillerne skanner koden og svarer fra mobilen.<br />{lenke}</span></div>
      </div>}
      <div style={card}>
        <span style="font-size:14px;font-weight:600">{vert ? 'Spillere' : 'Sanglek'}</span>
        {!meStatus ? <div style="display:flex;gap:8px"><input value={navn} placeholder="Navnet ditt" onInput={(e) => setNavn(e.currentTarget.value)} style={inp + ';flex:1'} /><button style={btn(true)} onClick={() => void bliMed()}>Bli med</button></div>
          : s.aktiv && s.fase !== 'vist' && <div style="display:flex;gap:8px"><input value={svar} placeholder="Artist – tittel" onInput={(e) => setSvar(e.currentTarget.value)} style={inp + ';flex:1'} /><button style={btn(true)} onClick={() => void act({ action: 'svar', spiller: meg, svar }).then(() => setSvar(''))}>{meStatus.svart ? 'Endre svar' : 'Svar'}</button></div>}
        {s.spillere.map((p, i) => <div key={p.navn} style="display:flex;justify-content:space-between;font-size:14px"><span>{i + 1}. {p.navn}{p.svart && s.fase !== 'vist' ? ' ✓' : ''}{s.fasit?.[p.navn] ? <span style={muted}> – «{s.fasit[p.navn]}»</span> : null}</span><b>{p.poeng}</b></div>)}
      </div>
      {msg && <span style="font-size:12px;color:#ff8a7a">{msg}</span>}
    </div>
  );
}

// ---------- Lydbøker (Audiobookshelf) ----------
interface Book { id: string; tittel: string; forfatter: string; varighet: number; progresjon: number; ferdig: boolean; cover: string }
interface Now { id: string | null; tittel?: string; kapittel?: string; posisjon?: number | null; varighet?: number; sovetimer?: { modus: string } | null }

export function AbsPage() {
  const [c, setC] = useState<{ konfigurert: boolean; url: string } | null>(null), [url, setUrl] = useState(''), [tok, setTok] = useState('');
  const [books, setBooks] = useState<Book[] | null>(null), [now, setNow] = useState<Now | null>(null), [msg, setMsg] = useState(''), [q, setQ] = useState('');
  const load = () => apiReq<Book[]>('/api/abs/boker', undefined, undefined, 20000).then(setBooks).catch((e) => setMsg(err(e)));
  useEffect(() => { apiReq<{ konfigurert: boolean; url: string }>('/api/abs').then((x) => { setC(x); setUrl(x.url); if (x.konfigurert) void load(); }).catch((e) => setMsg(err(e))); }, []);
  useEffect(() => { const f = () => apiReq<Now>('/api/abs/naa').then(setNow).catch(() => {}); f(); const t = everyVisible(f, 5000); return () => clearInterval(t); }, []);
  const save = async () => { try { const r = await apiPost<{ ok?: boolean; error?: string; konfigurert: boolean; url: string }>('/api/abs', { url, token: tok }); setC(r); setTok(''); setMsg(r.ok ? 'Tilkoblet' : r.error ?? ''); if (r.ok) void load(); } catch (e) { setMsg(err(e)); } };
  const spill = async (id: string, fra_start = false) => { try { setNow(await apiPost<Now>('/api/abs/spill', { id, fra_start })); setMsg(''); } catch (e) { setMsg(err(e)); } };
  const sov = async (modus: string, minutter?: number) => { try { setNow(await apiPost<Now>('/api/abs/sovetimer', { modus, minutter })); } catch (e) { setMsg(err(e)); } };
  if (!c) return <span style={muted}>{msg || 'Henter …'}</span>;
  const vis = (books ?? []).filter((b) => !q || (b.tittel + ' ' + b.forfatter).toLowerCase().includes(q.toLowerCase()));
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      {now?.id && <div style={card}>
        <span style="font-size:14px;font-weight:600">Spiller nå: {now.tittel}</span>
        <span style={muted}>{now.kapittel}{now.posisjon != null && now.varighet ? ` · ${tid(now.posisjon)} av ${tid(now.varighet)}` : ''}{now.sovetimer ? ' · sovetimer på' : ''}</span>
        <div style="display:flex;gap:6px;flex-wrap:wrap"><button style={btn(now.sovetimer?.modus === 'kapittel')} onClick={() => void sov('kapittel')}>Sov etter kapittelet</button>{[15, 30, 60].map((m) => <button key={m} style={btn()} onClick={() => void sov('minutter', m)}>{m} min</button>)}{now.sovetimer && <button style={btn()} onClick={() => void sov('av')}>Av</button>}</div>
      </div>}
      <div style={card}>
        <span style="font-size:16px;font-weight:600">Audiobookshelf</span>
        <span style={muted}>Adresse som http://abs.local:13378 og API-token (Audiobookshelf → Innstillinger → Brukere → din bruker → API-token). Skjold fortsetter der du slapp, og lagrer hvor du er tilbake til Audiobookshelf. Hastighet støttes ikke (Lyrion kan ikke spille raskere).</span>
        <div style="display:flex;gap:8px;flex-wrap:wrap"><input value={url} placeholder="http://abs.local:13378" onInput={(e) => setUrl(e.currentTarget.value)} style={inp + ';flex:1;min-width:200px'} /><input type="password" value={tok} placeholder={c.konfigurert ? 'Token lagret' : 'API-token'} onInput={(e) => setTok(e.currentTarget.value)} style={inp + ';flex:1;min-width:160px'} /><button style={btn(true)} onClick={() => void save()}>Lagre</button></div>
      </div>
      {books && <div style={card}>
        <input value={q} placeholder="Søk i lydbøkene" onInput={(e) => setQ(e.currentTarget.value)} style={inp} />
        {vis.map((b) => (
          <div key={b.id} style="display:flex;gap:12px;align-items:center">
            <img src={b.cover} width={52} height={52} style="border-radius:6px;object-fit:cover;background:#222" alt="" loading="lazy" />
            <div style="flex:1;min-width:0;display:flex;flex-direction:column"><b style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{b.tittel}</b><span style={muted}>{b.forfatter} · {tid(b.varighet)}{b.progresjon > 0 && !b.ferdig ? ` · ${Math.round(b.progresjon * 100)} %` : b.ferdig ? ' · ferdig' : ''}</span></div>
            <button style={btn(true)} onClick={() => void spill(b.id)}>{b.progresjon > 0 && !b.ferdig ? 'Fortsett' : 'Spill'}</button>
            {b.progresjon > 0 && <button style={btn()} onClick={() => void spill(b.id, true)} aria-label="Fra start">↺</button>}
          </div>
        ))}
        {!vis.length && <span style={muted}>Ingen bøker funnet.</span>}
      </div>}
      {msg && <span style="font-size:12px;color:#ff8a7a">{msg}</span>}
    </div>
  );
}

// ---------- Køhistorikk ----------
interface HEntry { t: number; title: string; artist: string; album?: string; station?: string; cover?: string; rom?: string; input?: string; url?: string; base?: string }
interface Okt { rom: string; start: number; slutt: number; spor: HEntry[] }

export function QhistPage() {
  const iDag = new Date(), iGaar = new Date(Date.now() - 86400000);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  const [dag, setDag] = useState(fmt(iGaar)), [fra, setFra] = useState('18:00'), [til, setTil] = useState('02:00'), [rom, setRom] = useState('');
  const [d, setD] = useState<{ rom: string[]; aktiv: boolean; okter: Okt[] } | null>(null), [msg, setMsg] = useState('');
  const load = () => apiReq<{ rom: string[]; aktiv: boolean; okter: Okt[] }>(`/api/qhist?alle=1&dag=${dag}&fra=${fra}&til=${til}${rom ? '&rom=' + encodeURIComponent(rom) : ''}`, undefined, undefined, 15000).then(setD).catch((e) => setMsg(err(e)));
  useEffect(() => { void load(); }, [dag, fra, til, rom]);
  const spill = async (spor: HEntry[], base?: string) => { try { const r = await apiPost<{ antall: number; spiller: string }>('/api/qhist/spill', { spor, ...(base ? { rom: base } : {}) }); setMsg(`Spiller ${r.antall} spor – starter med ${r.spiller}`); } catch (e) { setMsg(err(e)); } };
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      <div style={card}>
        <span style={muted}>Hva spilte i huset? Velg dag og tidsrom (over midnatt går fint, f.eks. 18:00–02:00).</span>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          <button style={btn(dag === fmt(iDag))} onClick={() => setDag(fmt(iDag))}>I dag</button>
          <button style={btn(dag === fmt(iGaar))} onClick={() => setDag(fmt(iGaar))}>I går</button>
          <input type="date" value={dag} onInput={(e) => setDag(e.currentTarget.value)} style={inp} />
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          {([['Morgen', '06:00', '12:00'], ['Dag', '12:00', '18:00'], ['Kveld', '18:00', '02:00'], ['Hele døgnet', '00:00', '24:00']] as const).map(([n, a, b]) => <button key={n} style={btn(fra === a && til === b)} onClick={() => { setFra(a); setTil(b); }}>{n}</button>)}
        </div>
        {d && d.rom.length > 1 && <div style="display:flex;gap:6px;flex-wrap:wrap"><button style={btn(!rom)} onClick={() => setRom('')}>Alle rom</button>{d.rom.map((r) => <button key={r} style={btn(rom === r)} onClick={() => setRom(r)}>{r}</button>)}</div>}
        {d && !d.aktiv && <span style="font-size:12px;color:#f0c46a">Lyttehistorikk er av – slå på pluginen «Lyttehistorikk», så lagres det som spilles.</span>}
      </div>
      {d?.okter.map((o) => (
        <div key={o.rom + o.start} style={card}>
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><b style="font-size:14px">{o.rom || 'Dette rommet'} · {klokke(o.start)}–{klokke(o.slutt)}</b><button style={btn(true)} onClick={() => void spill(o.spor, o.spor[0]?.base)}>Spill hele økta igjen</button></div>
          {o.spor.map((e) => (
            <div key={e.t} style="display:flex;gap:10px;align-items:center">
              <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#8b8b86;width:40px">{klokke(e.t)}</span>
              {e.cover ? <img src={e.cover} width={36} height={36} style="border-radius:4px;object-fit:cover" alt="" loading="lazy" /> : <span style="width:36px;height:36px;border-radius:4px;background:#222" />}
              <div style="flex:1;min-width:0;display:flex;flex-direction:column"><span style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{e.input === 'radio' && e.station ? e.station : e.title}</span><span style={muted}>{e.input === 'radio' ? e.title : e.artist}</span></div>
              <button style={btn()} onClick={() => void spill([e], e.base)}>Spill</button>
            </div>
          ))}
        </div>
      ))}
      {d && !d.okter.length && <span style={muted}>Ingenting spilte i dette tidsrommet.</span>}
      {msg && <span style="font-size:12px;color:#c9c9c4">{msg}</span>}
    </div>
  );
}

// ---------- Sikkerhetsmodus (Innstillinger → Rutiner) ----------
export function SecurityPanel() {
  const [c, setC] = useState<Record<string, any> | null>(null), [rom, setRom] = useState(''), [msg, setMsg] = useState(''), [aktiv, setAktiv] = useState(false);
  useEffect(() => { apiReq<{ aktiv: boolean; cfg: Record<string, any> }>('/api/security').then((r) => { setC(r.cfg); setAktiv(r.aktiv); setRom((r.cfg.rom ?? []).join('\n')); }).catch(() => setC(null)); }, []);
  const set = async (b: Record<string, unknown>) => { try { setC(await apiPost('/api/security/innstillinger', b)); setMsg('Lagret'); } catch (e) { setMsg(err(e)); } };
  const test = async (action: string) => { try { const r = await apiPost<{ aktiv: boolean; error?: string }>('/api/security', { action, grunn: 'test' }); setAktiv(r.aktiv); setMsg(r.error ?? ''); } catch (e) { setMsg(err(e)); } };
  if (!c) return null;
  return (
    <div style={card}>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span style="font-size:16px;font-weight:600">Sikkerhetsmodus</span><button style={btn(c['på'])} onClick={() => void set({ 'på': !c['på'] })}>{c['på'] ? 'På' : 'Av'}</button></div>
      <span style={muted}>Når alarmen utløses (Home Assistant: skjold.security_trigger, Homey: «Utløs sikkerhetsalarm», eller {getBase() || 'http://<skjold>:8765'}/api/security) slår Skjold seg på, setter volumet til full styrke – også på barnerommet – og spiller sirenen og kunngjøringen til alarmen slås av eller tiden er ute.</span>
      <div style="display:flex;gap:6px;flex-wrap:wrap">{([['sirene', 'Sirene'], ['pip', 'Pipelyd']] as const).map(([k, n]) => <button key={k} style={btn(c.lyd === k)} onClick={() => void set({ lyd: k })}>{n}</button>)}</div>
      <input value={c.tekst} onChange={(e) => void set({ tekst: e.currentTarget.value })} style={inp} aria-label="Kunngjøring" />
      <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:13px">
        <label>Volum <input type="number" min={10} max={100} value={c.volum} onChange={(e) => void set({ volum: +e.currentTarget.value })} style={inp + ';width:70px'} /></label>
        <label>Maks varighet <input type="number" min={1} max={30} value={c.maks_min} onChange={(e) => void set({ maks_min: +e.currentTarget.value })} style={inp + ';width:70px'} /> min</label>
      </div>
      <label style="display:flex;flex-direction:column;gap:4px;font-size:13px">Også i disse rommene (én adresse per linje, f.eks. http://kjokken.local:8765)<textarea value={rom} onInput={(e) => setRom(e.currentTarget.value)} onBlur={() => void set({ rom: rom.split(/\s+/).filter(Boolean) })} rows={2} style="border-radius:8px;border:1px solid #2e2e30;background:#0f0f10;color:#f2f2ee;padding:8px" /></label>
      <div style="display:flex;gap:8px"><button style={btn()} disabled={!c['på']} onClick={() => void test('trigger')}>Test (full styrke!)</button>{aktiv && <button style={btn(true)} onClick={() => void test('stop')}>Stopp</button>}</div>
      {msg && <span style="font-size:12px;color:#a9a9a3">{msg}</span>}
    </div>
  );
}

// ---------- Bass management (Grupper og surround) ----------
interface BassRes { sub_phase: number; sub_fine_ms: number; sub_level: number; main_delay_ms: number; flatness_db: number; flatness_before_db: number; freqs: number[]; before: number[]; after: number[]; xover: number }

function Kurve({ r }: { r: BassRes }) {
  const W = 300, H = 120, all = [...r.before, ...r.after], lo = Math.min(...all) - 3, hi = Math.max(...all) + 3;
  const x = (f: number) => (Math.log(f / 20) / Math.log(300 / 20)) * W, y = (v: number) => H - ((v - lo) / (hi - lo)) * H;
  const path = (v: number[]) => v.map((d, i) => `${i ? 'L' : 'M'}${x(r.freqs[i]!).toFixed(1)},${y(d).toFixed(1)}`).join('');
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style="width:100%;height:auto;background:#0f0f10;border-radius:8px" role="img" aria-label="Frekvensrespons før og etter">
      <line x1={x(r.xover)} x2={x(r.xover)} y1={0} y2={H} stroke="#3a3a3c" stroke-dasharray="3 3" />
      <path d={path(r.before)} fill="none" stroke="#6a6a65" stroke-width="1.5" />
      <path d={path(r.after)} fill="none" stroke={A} stroke-width="2" />
    </svg>
  );
}

export function BassCard() {
  const [sub, setSub] = useState(() => { try { return localStorage.getItem('skjold-bass-sub') || ''; } catch { return ''; } });
  const [st, setSt] = useState(''), [res, setRes] = useState<BassRes | null>(null), busy = useRef(false);
  const maal = async () => {
    if (busy.current) return; busy.current = true; setRes(null);
    try { localStorage.setItem('skjold-bass-sub', sub); } catch { /* privat modus */ }
    try {
      let tRec = 0;
      const recP = recordMic(2 + 0.5 + 2 * 1.6 + 2, () => { tRec = Date.now() / 1000; });
      await new Promise((r) => setTimeout(r, 300));
      setSt('Hold mobilen der du sitter – hovedhøyttalerne, så sub-en …');
      const t1 = Date.now() / 1000;
      const s = await apiPost<{ start_at: number; now: number }>('/api/bass/start', { sub });
      const off = s.now - (t1 + Date.now() / 1000) / 2;
      const { data, sr } = await recP;
      setSt('Analyserer …');
      const pcm = new Int16Array(data.length);
      for (let i = 0; i < data.length; i++) pcm[i] = Math.max(-32768, Math.min(32767, Math.round(data[i]! * 32767)));
      setRes(await apiReq<BassRes>(`/api/bass/analyze?sr=${sr}&skip=${Math.max(0, s.start_at - off - tRec).toFixed(3)}`, { method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: pcm.buffer as ArrayBuffer }, undefined, 60000));
      setSt('');
    } catch (e) { setSt(err(e)); } finally { busy.current = false; }
  };
  const bruk = async (apply: boolean) => { try { const r = await apiPost<{ hoved_forsinkelse_ms: number }>(apply ? '/api/bass/apply' : '/api/bass/avbryt', {}); setSt(apply ? 'Brukt' + (r.hoved_forsinkelse_ms ? ` – hovedenheten forsinkes ${r.hoved_forsinkelse_ms} ms` : '') + '.' : 'Tilbakestilt.'); setRes(null); } catch (e) { setSt(err(e)); } };
  return (
    <div style={card} data-testid="bass-card">
      <span style="font-size:13px">Bass management – mål sub-en automatisk</span>
      <span style={muted}>Hovedhøyttalerne og sub-en spiller en sweep etter tur mens mobilen tar opp der du sitter. Skjold finner fase, forsinkelse og nivå som gir jevnest bass rundt delefrekvensen. Krever at denne enheten «Har sub» og sub-enheten «Er sub».</span>
      <input value={sub} placeholder="Sub-enhetens adresse, f.eks. 192.168.1.40" onInput={(e) => setSub(e.currentTarget.value)} style={inp} />
      <button style={pbtn} disabled={!sub.trim()} onClick={() => void maal()}>Mål med mobilen</button>
      {res && <>
        <Kurve r={res} />
        <span style="font-size:13px">Fase {res.sub_phase}° · forsinkelse {String(res.sub_fine_ms).replace('.', ',')} ms · nivå {res.sub_level > 0 ? '+' : ''}{String(res.sub_level).replace('.', ',')} dB{res.main_delay_ms ? ` · hovedenheten +${res.main_delay_ms} ms` : ''}</span>
        <span style={muted}>Ujevnhet rundt delefrekvensen: {res.flatness_before_db} dB → {res.flatness_db} dB (grå = før, gull = etter).</span>
        <div style="display:flex;gap:8px"><button style={btn(true)} onClick={() => void bruk(true)}>Bruk</button><button style={btn()} onClick={() => void bruk(false)}>Avbryt</button></div>
      </>}
      {st && <span style="font-size:12px;color:#a9a9a3">{st}</span>}
    </div>
  );
}

// ---------- snarveier fra Bibliotek ----------
export function LydLenker() {
  return (
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button style={btn()} onClick={() => go('abs')}>Lydbøker</button>
      <button style={btn()} onClick={() => go('qhist')}>Køhistorikk</button>
      <button style={btn()} onClick={() => go('quiz')}>Sanglek</button>
    </div>
  );
}
