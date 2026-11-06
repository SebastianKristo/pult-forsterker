// Roon, Plexamp, automatisk standby, backup/gjenoppretting og Skjold Wrapped (daemonens skjold_extras).
import { useEffect, useRef, useState } from 'preact/hooks';
import { credFor, getBase } from '../lib/api';
import { go } from '../lib/store';

const A = '#d9a441';
const pbtn = `height:38px;padding:0 16px;border-radius:999px;border:none;background:${A};color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap`;
const sbtn = 'height:38px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:13px;cursor:pointer;white-space:nowrap';
const inp = 'height:38px;padding:0 12px;border-radius:10px;border:1px solid #2e2e30;background:#121213;color:#f2f2ee;font-size:13px';
const hint = 'font-size:12.5px;color:#a9a9a3;line-height:1.5';
const CARD = 'display:flex;flex-direction:column;gap:12px;padding:16px;border-radius:16px;background:#141415;border:1px solid #242426';

async function call<T = any>(path: string, body?: unknown, timeoutMs = 15000): Promise<T> {
  const base = getBase();
  const ac = new AbortController();
  const tm = setTimeout(() => ac.abort(), timeoutMs);
  try {
    const r = await fetch(base + path, { credentials: credFor(base), signal: ac.signal, ...(body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }) });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j as any).error || 'HTTP ' + r.status);
    return j as T;
  } finally { clearTimeout(tm); }
}

interface SvcStatus { installed: boolean; running?: boolean; state?: string; signed_in?: boolean; playing?: boolean; job?: { running: boolean; ok: boolean | null; log: string[]; what?: string } | null; [k: string]: unknown }

function useSvc(path: string) {
  const [st, setSt] = useState<SvcStatus | null>(null);
  const [err, setErr] = useState('');
  const load = async () => { try { setSt(await call<SvcStatus>(path)); setErr(''); } catch (e) { setErr(String((e as Error).message)); } };
  useEffect(() => { void load(); const t = setInterval(() => void load(), 3000); return () => clearInterval(t); }, [path]);
  const act = async (b: Record<string, unknown>) => { try { setSt(await call<SvcStatus>(path, b, 30000)); setErr(''); } catch (e) { setErr(String((e as Error).message)); } };
  return { st, err, act };
}

function JobLog({ st }: { st: SvcStatus | null }) {
  const j = st?.job;
  if (!j || !j.log?.length) return null;
  return <pre style="margin:0;max-height:180px;overflow:auto;padding:10px;border-radius:10px;background:#0b0b0c;font-size:11px;color:#a9a9a3;white-space:pre-wrap">{j.log.slice(-40).join('\n')}{j.running ? '\n…' : j.ok === false ? '\nFeilet.' : j.ok ? '\nFerdig.' : ''}</pre>;
}

function SvcButtons({ st, act }: { st: SvcStatus; act: (b: Record<string, unknown>) => void }) {
  return <div style="display:flex;gap:8px;flex-wrap:wrap">
    {st.running ? <button style={sbtn} onClick={() => act({ action: 'stop' })}>Stopp</button> : <button style={sbtn} onClick={() => act({ action: 'start' })}>Start</button>}
    <button style={sbtn} onClick={() => act({ action: 'restart' })}>Start på nytt</button>
  </div>;
}

export function RoonPanel() {
  const { st, err, act } = useSvc('/api/roon');
  const busy = !!st?.job?.running;
  return <>
    <span style={hint}>RoonBridge gjør Skjold til et Roon Ready-endepunkt. Roon Core må kjøre et annet sted i nettet. Når Roon spiller, bytter Skjold kilde til «Roon» av seg selv.</span>
    {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    {st && !st.installed && <button style={pbtn} disabled={busy} onClick={() => act({ action: 'install' })}>{busy ? 'Installerer …' : 'Installer RoonBridge'}</button>}
    {st?.installed && <>
      <span style="font-size:13px">{st.running ? 'Kjører' : 'Stoppet'}{st.playing ? ' · spiller nå' : ''}</span>
      <SvcButtons st={st} act={act} />
      <span style={hint}>I Roon: Innstillinger → Lyd → finn Skjold → velg enheten <b>skjold_roon</b> og aktiver den.</span>
    </>}
    <JobLog st={st} />
  </>;
}

export function PlexampPanel({ name }: { name: string }) {
  const { st, err, act } = useSvc('/api/plexamp');
  const [code, setCode] = useState('');
  const [nm, setNm] = useState(name || 'Skjold');
  const busy = !!st?.job?.running;
  return <>
    <span style={hint}>Plexamp headless spiller fra Plex-biblioteket ditt og styres fra Plexamp-appen på telefonen.</span>
    {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    {st && !st.installed && <button style={pbtn} disabled={busy} onClick={() => act({ action: 'install' })}>{busy ? 'Installerer …' : 'Installer Plexamp'}</button>}
    {st?.installed && !st.signed_in && <>
      <span style={hint}>Hent en kode på <a href="https://plex.tv/claim" target="_blank" rel="noreferrer" style={`color:${A}`}>plex.tv/claim</a> (gyldig i 4 min) og lim den inn.</span>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <input style={inp + ';width:200px'} placeholder="claim-…" value={code} onInput={(e) => setCode((e.target as HTMLInputElement).value.trim())} />
        <input style={inp + ';width:140px'} placeholder="Navn" value={nm} onInput={(e) => setNm((e.target as HTMLInputElement).value)} />
        <button style={pbtn} disabled={busy || !code.startsWith('claim-')} onClick={() => act({ action: 'claim', code, name: nm })}>Koble til</button>
      </div>
    </>}
    {st?.installed && st.signed_in && <>
      <span style="font-size:13px">Pålogget · {st.running ? 'kjører' : 'stoppet'}</span>
      <SvcButtons st={st} act={act} />
      <span style={hint}>Velg «{nm}» som spiller i Plexamp, eller åpne <a href="https://listen.plex.tv" target="_blank" rel="noreferrer" style={`color:${A}`}>listen.plex.tv</a>.</span>
    </>}
    <JobLog st={st} />
  </>;
}

export function AutoStandbyPanel({ d, up, save, msg }: { d: Record<string, any>; up: (k: string, v: unknown) => void; save: (x?: Record<string, unknown>) => void; msg: string }) {
  const opts = [0, 5, 10, 15, 30, 60];
  return <>
    <span style={hint}>Skjold går i standby når det ikke har spilt noe på en stund. Den våkner igjen når en kilde begynner å spille.</span>
    <div style="display:flex;gap:6px;flex-wrap:wrap">{opts.map((m) => {
      const on = m === 0 ? false : d.minutes === m;
      return <button key={m} style={on ? pbtn : sbtn} onClick={() => m === 0 ? save({ enabled: false }) : save({ minutes: m, enabled: true })}>{m === 0 ? 'Av' : m + ' min'}</button>;
    })}</div>
    <label style="display:flex;gap:8px;align-items:center;font-size:13px"><input type="checkbox" checked={!!d.pause_counts} onChange={(e) => { up('pause_counts', (e.target as HTMLInputElement).checked); save({ pause_counts: (e.target as HTMLInputElement).checked }); }} />Pause teller som stillhet</label>
    {msg && <span style="font-size:12px;color:#8b8b86">{msg}</span>}
  </>;
}

/* ---------- Backup ---------- */

function download(name: string, blob: Blob) {
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

export function BackupPanel() {
  const [info, setInfo] = useState<any>(null);
  const [pass, setPass] = useState('');
  const [msg, setMsg] = useState('');
  const [file, setFile] = useState<any>(null);
  const [prev, setPrev] = useState<any>(null);
  const [mode, setMode] = useState<'settings' | 'all'>('settings');
  const [rpass, setRpass] = useState('');
  const load = async () => { try { setInfo(await call('/api/backup?info=1')); } catch { /* eldre daemon */ } };
  useEffect(() => { void load(); }, []);
  const get = async () => {
    setMsg('Lager backup …');
    try {
      const q = pass ? '?secrets=encrypt&pass=' + encodeURIComponent(pass) : '?secrets=exclude';
      const j = await call('/api/backup' + q);
      download(`skjold-backup-${new Date().toISOString().slice(0, 10)}.json`, new Blob([JSON.stringify(j, null, 1)], { type: 'application/json' }));
      setMsg('Lastet ned');
    } catch (e) { setMsg('Feil: ' + (e as Error).message); }
  };
  const pick = async (f: File | undefined) => {
    if (!f) return;
    try {
      const b = JSON.parse(await f.text()); setFile(b);
      setPrev(await call('/api/restore', { backup: b, mode, dry_run: true })); setMsg('');
    } catch (e) { setFile(null); setPrev(null); setMsg('Feil: ' + (e as Error).message); }
  };
  useEffect(() => { if (file) void call('/api/restore', { backup: file, mode, dry_run: true }).then(setPrev).catch(() => {}); }, [mode]);
  const restore = async () => {
    setMsg('Gjenoppretter …');
    try { await call('/api/restore', { backup: file, mode, passphrase: rpass }); setMsg('Gjenopprettet. Enheten bruker de nye innstillingene nå.'); setFile(null); setPrev(null); }
    catch (e) { setMsg('Feil: ' + (e as Error).message); }
  };
  const now = async () => { setMsg('Tar backup …'); try { const r = await call('/api/backup', { action: 'now' }, 60000); setMsg(r.msg || 'Lagret'); void load(); } catch (e) { setMsg('Feil: ' + (e as Error).message); } };
  return <div style={CARD}>
    <b style="font-size:14px">Backup og gjenoppretting</b>
    <span style={hint}>Innstillinger, favoritter, plugins og nivåer. Passord tas bare med hvis du velger en passfrase (minst 6 tegn), og da krypteres de.</span>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <input type="password" style={inp + ';width:200px'} placeholder="Passfrase (valgfri)" value={pass} onInput={(e) => setPass((e.target as HTMLInputElement).value)} />
      <button style={pbtn} onClick={() => void get()}>Last ned backup</button>
    </div>
    <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
      <label style={sbtn + ';display:inline-flex;align-items:center'}>Gjenopprett fra fil …<input type="file" accept="application/json,.json" style="display:none" onChange={(e) => void pick((e.target as HTMLInputElement).files?.[0])} /></label>
      <button style={sbtn} onClick={() => void now()}>Ta backup nå</button>
    </div>
    {info && <span style="font-size:12px;color:#8b8b86">Nattlig backup kl. 03 (pluginen «Backup»){info.last ? ' · siste ' + new Date(info.last * 1000).toLocaleString('nb-NO') : ''}{info.msg ? ' · ' + info.msg : ''} <a href="#" onClick={(e) => { e.preventDefault(); go('plug'); }} style={`color:${A}`}>Endre i Plugins</a></span>}
    {prev && <div style="display:flex;flex-direction:column;gap:8px;padding:12px;border-radius:12px;background:#0f0f10">
      <span style="font-size:13px">Fra «{prev.device?.name || 'ukjent'}»{prev.created ? ', ' + new Date(prev.created * 1000).toLocaleString('nb-NO') : ''}</span>
      <div style="display:flex;gap:6px">
        <button style={mode === 'settings' ? pbtn : sbtn} onClick={() => setMode('settings')}>Bare innstillinger</button>
        <button style={mode === 'all' ? pbtn : sbtn} onClick={() => setMode('all')}>Alt</button>
      </div>
      <span style="font-size:12px;color:#a9a9a3;white-space:pre-line">{(prev.changes || []).length ? (prev.changes as string[]).slice(0, 30).join('\n') : 'Ingen endringer.'}</span>
      {prev.has_secrets && <input type="password" style={inp + ';width:200px'} placeholder="Passfrase for passord" value={rpass} onInput={(e) => setRpass((e.target as HTMLInputElement).value)} />}
      <div style="display:flex;gap:8px"><button style={pbtn} onClick={() => void restore()}>Gjenopprett</button><button style={sbtn} onClick={() => { setFile(null); setPrev(null); }}>Avbryt</button></div>
    </div>}
    {msg && <span style={`font-size:12px;color:${msg.startsWith('Feil') ? '#ff8a7a' : '#8b8b86'}`}>{msg}</span>}
  </div>;
}

/* ---------- Wrapped ---------- */

interface Ranked { name: string; count?: number; minutes?: number }
interface WrappedSum { year: number; empty?: boolean; minutes: number; plays: number; artists: Ranked[]; tracks: (Ranked & { artist?: string })[]; stations: Ranked[]; by_input: Ranked[]; rooms: number; days?: number; busiest_day?: { date: string; minutes: number }; busiest_hour?: { hour: number }; longest_session?: number; years?: number[] }

export const wrappedSeason = (d = new Date()): boolean => d.getMonth() === 11 || d.getMonth() === 0;
const wrappedYear = (d = new Date()): number => d.getMonth() === 0 ? d.getFullYear() - 1 : d.getFullYear();

async function savePng(s: WrappedSum) {
  const c = document.createElement('canvas');
  c.width = 1080; c.height = 1350;
  const g = c.getContext('2d'); if (!g) return;
  const gr = g.createLinearGradient(0, 0, 1080, 1350); gr.addColorStop(0, '#2a1d08'); gr.addColorStop(1, '#0b0b0c');
  g.fillStyle = gr; g.fillRect(0, 0, 1080, 1350);
  g.fillStyle = A; g.font = '600 40px sans-serif'; g.fillText('SKJOLD WRAPPED ' + s.year, 80, 130);
  g.fillStyle = '#f2f2ee'; g.font = '700 150px sans-serif'; g.fillText(Math.round(s.minutes).toLocaleString('nb-NO'), 80, 320);
  g.font = '400 44px sans-serif'; g.fillStyle = '#a9a9a3'; g.fillText('minutter med musikk', 80, 385);
  const list = (t: string, xs: Ranked[], y: number) => {
    g.fillStyle = A; g.font = '600 34px sans-serif'; g.fillText(t, 80, y);
    xs.slice(0, 5).forEach((x, i) => { g.fillStyle = '#f2f2ee'; g.font = '400 40px sans-serif'; g.fillText(`${i + 1}. ${x.name}`.slice(0, 40), 80, y + 60 + i * 56); });
  };
  list('TOPPARTISTER', s.artists, 500);
  list(s.stations.length ? 'TOPPKANALER' : 'TOPPLÅTER', s.stations.length ? s.stations : s.tracks, 880);
  c.toBlob((b) => { if (b) download(`skjold-wrapped-${s.year}.png`, b); }, 'image/png');
}

function Top({ title, xs, unit }: { title: string; xs: Ranked[]; unit: string }) {
  if (!xs?.length) return null;
  return <div style={CARD}>
    <span style={`font-size:11px;letter-spacing:.12em;color:${A}`}>{title}</span>
    {xs.slice(0, 5).map((x, i) => <div key={x.name} style="display:flex;gap:10px;font-size:14px"><span style="color:#6a6a65;width:16px">{i + 1}</span><span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{x.name}</span><span style="color:#8b8b86">{x.count ?? Math.round(x.minutes ?? 0)} {unit}</span></div>)}
  </div>;
}

export function WrappedPage() {
  const [year, setYear] = useState(wrappedYear());
  const [s, setS] = useState<WrappedSum | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { setS(null); call<WrappedSum>('/api/wrapped?year=' + year).then(setS).catch((e) => setErr(String(e.message))); }, [year]);
  if (err) return <span style="font-size:12px;color:#ff8a7a">{err}</span>;
  if (!s) return <span style="font-size:13px;color:#8b8b86">Henter …</span>;
  const years = s.years?.length ? s.years : [year];
  return <div style="display:flex;flex-direction:column;gap:12px">
    {years.length > 1 && <div style="display:flex;gap:6px">{years.map((y) => <button key={y} style={y === year ? pbtn : sbtn} onClick={() => setYear(y)}>{y}</button>)}</div>}
    {s.empty ? <span style={hint}>Ingen lytting registrert for {year} ennå. Skjold teller når pluginen er på.</span> : <>
      <div style={CARD + ';background:linear-gradient(135deg,#2a1d08,#141415)'}>
        <span style={`font-size:11px;letter-spacing:.12em;color:${A}`}>SKJOLD WRAPPED {s.year}</span>
        <b style="font-size:44px;line-height:1">{Math.round(s.minutes).toLocaleString('nb-NO')}</b>
        <span style="font-size:13px;color:#a9a9a3">minutter · {s.plays} låter · {s.rooms} rom{s.days ? ` · ${s.days} dager` : ''}</span>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px">
        <Top title="TOPPARTISTER" xs={s.artists} unit="spill" />
        <Top title="TOPPLÅTER" xs={s.tracks} unit="spill" />
        <Top title="TOPPKANALER" xs={s.stations} unit="spill" />
        <Top title="KILDER" xs={s.by_input} unit="min" />
      </div>
      <div style={CARD}>
        {s.busiest_day && <span style="font-size:13px">Travleste dag: {s.busiest_day.date} ({Math.round(s.busiest_day.minutes)} min)</span>}
        {s.busiest_hour && <span style="font-size:13px">Favorittime: kl. {String(s.busiest_hour.hour).padStart(2, '0')}</span>}
        {!!s.longest_session && <span style="font-size:13px">Lengste økt: {Math.round(s.longest_session)} min</span>}
      </div>
      <button style={pbtn} onClick={() => void savePng(s)}>Last ned som bilde</button>
    </>}
  </div>;
}

/** Kort på Hjem i desember og januar. */
export function WrappedTeaser() {
  const [s, setS] = useState<WrappedSum | null>(null);
  const done = useRef(false);
  useEffect(() => { if (!wrappedSeason() || done.current) return; done.current = true; call<WrappedSum>('/api/wrapped?year=' + wrappedYear()).then(setS).catch(() => {}); }, []);
  if (!s || s.empty) return null;
  return <button onClick={() => go('plug')} style={`${CARD};cursor:pointer;text-align:left;background:linear-gradient(135deg,#2a1d08,#141415);color:#f2f2ee`}>
    <span style={`font-size:11px;letter-spacing:.12em;color:${A}`}>SKJOLD WRAPPED {s.year}</span>
    <b style="font-size:22px">{Math.round(s.minutes).toLocaleString('nb-NO')} minutter med musikk</b>
    <span style="font-size:13px;color:#a9a9a3">{s.artists[0] ? `Mest spilt: ${s.artists[0].name}` : 'Se året ditt'} ›</span>
  </button>;
}
