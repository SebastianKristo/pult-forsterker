// Planlagte programopptak (Radioopptak → «Programmer», vises som podkast) og endringslogg («Hva er nytt»).
import { signal } from '@preact/signals';
import { useEffect, useState } from 'preact/hooks';
import { apiPost, apiReq } from '../lib/api';

const MONO = "'IBM Plex Mono',monospace";
const sbtn = 'height:34px;padding:0 13px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:12.5px;cursor:pointer;white-space:nowrap';
const fld = 'height:36px;padding:0 10px;border-radius:9px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;color:#f2f2ee;min-width:0';
const err = (e: unknown) => (e instanceof Error ? e.message : String(e));

export interface ProgEpisode { file: string; t: number; dur: number; size: number; title: string }
export interface Program { id: string; name: string; channel: string; image: string; episodes: ProgEpisode[] }
export interface GuideShow { title: string; start: number; dur: number; id: string }
export type Schedule = { time: string; days: number[]; minutes: number; program?: string; nrk?: string; url?: string; preset?: number; keep?: number; on?: boolean };

const hm = (t: number) => new Date(t * 1000).toLocaleTimeString('nb-NO', { hour: '2-digit', minute: '2-digit' });
const dur = (s: number) => (s >= 3600 ? `${Math.floor(s / 3600)} t ${Math.round((s % 3600) / 60)} min` : `${Math.round(s / 60)} min`);

/** Velg en sending fra NRKs programguide → gir en ukentlig opptaksplan (samme ukedag og tid). */
export function GuidePicker({ onPick }: { onPick: (s: Schedule) => void }) {
  const [open, setOpen] = useState(false);
  const [ch, setCh] = useState('p1');
  const [date, setDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [shows, setShows] = useState<GuideShow[]>([]);
  const [chans, setChans] = useState<Record<string, string>>({ p1: 'NRK P1', p2: 'NRK P2', p3: 'NRK P3' });
  const [msg, setMsg] = useState('');
  const [keep, setKeep] = useState(8);
  useEffect(() => {
    if (!open) return;
    setMsg('Henter programguiden …'); setShows([]);
    apiReq<{ shows: GuideShow[]; channels: Record<string, string>; error?: string }>(`/api/recordings/guide?ch=${ch}&date=${date}`)
      .then((r) => { setShows(r.shows); setChans(r.channels); setMsg(r.shows.length ? '' : 'Ingen sendinger funnet.'); })
      .catch((e) => setMsg(err(e)));
  }, [open, ch, date]);
  if (!open) return <button onClick={() => setOpen(true)} style={sbtn}>+ Velg program fra NRK</button>;
  return (
    <div style="display:flex;flex-direction:column;gap:8px;padding:10px;border:1px solid #2a2a2c;border-radius:12px">
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        <select value={ch} onChange={(e) => setCh((e.currentTarget as HTMLSelectElement).value)} style={fld}>{Object.entries(chans).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select>
        <input type="date" value={date} onInput={(e) => setDate((e.currentTarget as HTMLInputElement).value)} style={fld} />
        <span style="font-size:12px;color:#8b8b86">Behold</span>
        <input type="number" min={1} max={52} value={keep} onInput={(e) => setKeep(Math.max(1, +(e.currentTarget as HTMLInputElement).value || 8))} style={fld + ';width:64px'} />
        <span style="font-size:12px;color:#8b8b86">episoder</span>
        <button onClick={() => setOpen(false)} style={sbtn}>Lukk</button>
      </div>
      {msg && <span style="font-size:12px;color:#8b8b86">{msg}</span>}
      <div style="display:flex;flex-direction:column;max-height:320px;overflow:auto">
        {shows.map((s) => (
          <button key={s.start + s.title} onClick={() => {
            const d = new Date(s.start * 1000);
            onPick({ time: hm(s.start), days: [(d.getDay() + 6) % 7], minutes: Math.max(1, Math.min(240, Math.round(s.dur / 60) || 60)), program: s.title, nrk: ch, url: '', preset: 0, keep, on: true });
            setOpen(false);
          }} style="display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px 4px;border:none;border-top:1px solid #1f1f21;background:none;color:#f2f2ee;text-align:left;cursor:pointer">
            <span style={`font-family:${MONO};font-size:12px;color:#c9c9c4`}>{hm(s.start)}</span>
            <span style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.title}</span>
            <span style="font-size:11.5px;color:#8b8b86">{dur(s.dur)}</span>
          </button>))}
      </div>
      <span style="font-size:11.5px;color:#8b8b86">Opptaket gjentas samme ukedag og tid hver uke. Husk å lagre.</span>
    </div>
  );
}

/** Opptatte programmer – episoder, avspilling og podkast-feed. */
export function ProgramsPanel({ programs, feed, onChange }: { programs: Program[]; feed: string; onChange: (p: unknown) => void }) {
  const [e, setE] = useState('');
  const post = async (b: Record<string, unknown>) => { setE(''); try { onChange(await apiPost('/api/recordings', b)); } catch (x) { setE(err(x)); } };
  return (
    <>
      <span style="font-size:13px;font-weight:600;padding-top:8px">Programmer (podkast)</span>
      <span style="font-size:12px;color:#8b8b86;line-height:1.5">Planlagte opptak med programnavn lagres som episoder – på NAS i «Programmer/‹navn›/» og som podkast. Abonner på feeden i Podkaster (Lyrion) eller en podkast-app på hjemmenettet:</span>
      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><code style={`font-family:${MONO};font-size:11.5px;color:#f0c46a;word-break:break-all`}>{feed}</code><button onClick={() => { void navigator.clipboard?.writeText(feed); }} style={sbtn}>Kopier</button></div>
      {e && <span style="font-size:12px;color:#ff8a7a">{e}</span>}
      {!programs.length && <span style="font-size:12.5px;color:#8b8b86">Ingen programmer tatt opp ennå.</span>}
      {programs.map((p) => (
        <div key={p.id} style="display:flex;flex-direction:column;gap:2px;padding:8px 0;border-top:1px solid #1f1f21">
          <b style="font-size:13.5px">{p.name} <span style="font-weight:400;color:#8b8b86;font-size:12px">· {p.channel} · {p.episodes.length} episoder</span></b>
          {p.episodes.map((x) => (
            <div key={x.file} style="display:grid;grid-template-columns:minmax(0,1fr) auto;gap:8px;align-items:center;padding:4px 0">
              <span style="font-size:12.5px;color:#c9c9c4">{new Date(x.t * 1000).toLocaleDateString('nb-NO', { weekday: 'short', day: 'numeric', month: 'short' })} · {dur(x.dur)}</span>
              <span style="display:flex;gap:6px"><button onClick={() => void post({ play_episode: { prog: p.id, file: x.file, title: x.title } })} style={sbtn}>Spill</button><button onClick={() => void post({ delete_episode: { prog: p.id, file: x.file } })} style={sbtn}>Slett</button></span>
            </div>))}
        </div>))}
    </>
  );
}

// ---------- Endringslogg ----------
export interface Release { tag: string; name: string; body: string; date: string; url: string; prerelease: boolean }
export interface Changelog { current: string | null; notes: Release | null; history: Release[]; offline: boolean }
const SEEN = 'skjold.seenRelease';
export const whatsNew = signal<Release | null>(null);

/** Kalles ved oppstart: viser «Hva er nytt» én gang når enheten har fått en ny versjon. */
export async function checkWhatsNew() {
  try {
    const c = await apiReq<Changelog>('/api/changelog');
    if (!c.current || !c.notes) return;
    let seen: string | null = null;
    try { seen = localStorage.getItem(SEEN); } catch { /* privat modus */ }
    if (seen === null) { try { localStorage.setItem(SEEN, c.current); } catch { /* */ } return; }   // første gang: ikke vis gamle notater
    if (seen !== c.current) whatsNew.value = c.notes;
  } catch { /* eldre daemon eller offline */ }
}
function markSeen(tag: string) { try { localStorage.setItem(SEEN, tag); } catch { /* */ } }

/** Enkel markdown: ## overskrift, * / - punkt, ellers avsnitt. */
export function Notes({ body }: { body: string }) {
  const lines = body.split('\n').filter((l) => l.trim());
  if (!lines.length) return <span style="font-size:13px;color:#8b8b86">Ingen notater for denne versjonen.</span>;
  return (
    <div style="display:flex;flex-direction:column;gap:5px">
      {lines.map((l, i) => {
        const t = l.replace(/\*\*(.+?)\*\*/g, '$1').replace(/`/g, '');
        if (/^#{1,4}\s/.test(t)) return <b key={i} style="font-size:13.5px;margin-top:6px">{t.replace(/^#+\s*/, '')}</b>;
        if (/^\s*[*-]\s/.test(t)) return <span key={i} style="font-size:13px;line-height:1.45;padding-left:14px;text-indent:-10px">• {t.replace(/^\s*[*-]\s*/, '')}</span>;
        return <span key={i} style="font-size:13px;line-height:1.45;color:#c9c9c4">{t}</span>;
      })}
    </div>
  );
}

export function WhatsNewSheet() {
  const r = whatsNew.value;
  if (!r) return null;
  const close = () => { markSeen(r.tag); whatsNew.value = null; };
  return (
    <div role="dialog" aria-label="Hva er nytt" onClick={close} style="position:fixed;inset:0;z-index:60;background:rgba(0,0,0,.55);display:flex;align-items:flex-end;justify-content:center">
      <div onClick={(e) => e.stopPropagation()} style="width:min(560px,100%);max-height:80vh;overflow:auto;background:#141415;border:1px solid #2a2a2c;border-radius:18px 18px 0 0;padding:20px 18px calc(18px + env(safe-area-inset-bottom));display:flex;flex-direction:column;gap:12px">
        <span style="font-size:12px;color:#d9a441;font-family:'IBM Plex Mono',monospace">{r.tag.replace('skjold-', '')}</span>
        <b style="font-size:20px">Hva er nytt</b>
        <Notes body={r.body} />
        <button onClick={close} style="height:44px;border-radius:999px;border:none;background:#d9a441;color:#0b0b0c;font-size:14px;font-weight:600;cursor:pointer">OK</button>
      </div>
    </div>
  );
}

export function ChangelogPanel() {
  const [c, setC] = useState<Changelog | null>(null), [e, setE] = useState('');
  useEffect(() => { apiReq<Changelog>('/api/changelog').then(setC).catch((x) => setE(err(x))); }, []);
  if (e) return <span style="font-size:13px;color:#8b8b86">Endringsloggen krever nyere Skjold-programvare ({e}).</span>;
  if (!c) return <span style="font-size:13px;color:#8b8b86">Henter …</span>;
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      {c.offline && <span style="font-size:12px;color:#c9b48a">Uten nett – viser lagrede notater.</span>}
      {!c.history.length && <span style="font-size:13px;color:#8b8b86">Ingen release-notater ennå.</span>}
      {c.history.map((r) => (
        <div key={r.tag} style="display:flex;flex-direction:column;gap:6px;padding:14px;border-radius:14px;background:#141415;border:1px solid #232325">
          <div style="display:flex;justify-content:space-between;gap:8px;align-items:baseline">
            <b style="font-size:15px">{r.tag.replace('skjold-', '')}{r.tag === c.current ? ' · installert' : ''}{r.prerelease ? ' · beta' : ''}</b>
            <span style="font-size:11.5px;color:#8b8b86">{r.date ? new Date(r.date).toLocaleDateString('nb-NO', { day: 'numeric', month: 'short', year: 'numeric' }) : ''}</span>
          </div>
          <Notes body={r.body} />
        </div>))}
    </div>
  );
}
