// «Spill noe til …», lydtagger for biblioteket (Innstillinger → Bibliotek), filtre i Navidrome-søket og podkastsammendrag.
import { useEffect, useState } from 'preact/hooks';
import { Toggle } from '../components/ui';
import { ai, MOODS, type AiCfg, type AskResult, type PodSum, type TagFilter, type TagHit, type TagStatus } from '../lib/ai';
import type { NdSong } from '../lib/navidrome';

const sbtn = 'height:34px;padding:0 14px;border-radius:8px;border:1px solid #2e2e30;background:#1a1a1b;color:#f2f2ee;font-size:13px;cursor:pointer;white-space:nowrap';
const pbtn = 'height:34px;padding:0 14px;border-radius:8px;border:none;background:#d9a441;color:#141415;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap';
const card = 'flex-shrink:0;display:flex;flex-direction:column;gap:10px;padding:14px;border-radius:14px;background:#141415;border:1px solid #242426';
const inp = 'height:36px;padding:0 12px;border-radius:8px;border:1px solid #2e2e30;background:#0f0f10;color:#f2f2ee;font-size:14px;outline:none;min-width:0';
const muted = 'font-size:12px;color:#8b8b86;line-height:1.5';
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));
const EXAMPLES = ['rolig jazz til middag', 'energisk for trening', 'noe norsk fra 80-tallet'];

// ---------------------------------------------------------------- «Spill noe til …»
export function AskBox({ compact = false }: { compact?: boolean }) {
  const [text, setText] = useState(''), [busy, setBusy] = useState(false), [res, setRes] = useState<AskResult | null>(null), [err, setErr] = useState('');
  const go = async (t = text) => {
    if (!t.trim()) return;
    setBusy(true); setErr(''); setRes(null);
    try { setRes(await ai.ask(t.trim())); } catch (e) { setErr(errText(e)); }
    setBusy(false);
  };
  return (
    <div style={compact ? 'display:flex;flex-direction:column;gap:6px' : card}>
      {!compact && <span style="font-size:16px;font-weight:600">Spill noe til …</span>}
      <form onSubmit={(e) => { e.preventDefault(); void go(); }} style="display:flex;gap:8px">
        <input value={text} onInput={(e) => setText(e.currentTarget.value)} placeholder="f.eks. rolig jazz til middag" style={inp + ';flex:1'} />
        <button type="submit" disabled={busy || !text.trim()} style={pbtn}>{busy ? 'Finner …' : 'Spill'}</button>
      </form>
      {!compact && !res && !err && (
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          {EXAMPLES.map((x) => <button key={x} onClick={() => { setText(x); void go(x); }} style={sbtn}>{x}</button>)}
        </div>
      )}
      {res && <span style={muted}>{res.ok ? `▶ ${res.summary}${res.playing ? ` – ${res.playing}` : ''} (${res.source === 'tags' ? 'fra lydtaggene' : res.source === 'radio' ? 'nettradio' : res.source}${res.how === 'llm' ? ', tolket av KI' : ''})` : `${res.error} (${res.summary})`}</span>}
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    </div>
  );
}

// ---------------------------------------------------------------- Innstillinger → Bibliotek
export function LibraryTagsPanel() {
  const [s, setS] = useState<TagStatus | null>(null), [err, setErr] = useState('');
  const load = () => ai.tags().then((x) => { setS(x); setErr(''); }).catch((e) => setErr(errText(e)));
  useEffect(() => { void load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);
  const act = async (a: 'start' | 'pause') => { try { setS(await ai.tagsAction(a)); } catch (e) { setErr(errText(e)); } };
  const pct = s ? Math.round((s.progress || 0) * 100) : 0;
  return (
    <div style={card}>
      <span style="font-size:16px;font-weight:600">Lydbeskrivelse av biblioteket</span>
      <span style={muted}>Skjold lytter gjennom Navidrome-biblioteket i bakgrunnen og finner tempo, energi, stemning, akustisk/elektronisk og instrumental/vokal. Lav prioritet – på Pi 3 tar den pause mens noe spiller. Ingenting skrives tilbake til Navidrome.</span>
      {s && <>
        <div style="height:8px;border-radius:4px;background:#242426;overflow:hidden"><div style={`height:100%;width:${pct}%;background:#d9a441`} /></div>
        <span style={muted}>{s.done} av {s.total || '?'} låter ({pct} %){s.errors ? ` · ${s.errors} feil` : ''}{s.running ? (s.paused ? ' · pauset' : ' · jobber') : ''}{s.current ? ` · ${s.current}` : ''}</span>
        {s.moods && Object.keys(s.moods).length > 0 && <span style={muted}>{Object.entries(s.moods).map(([m, n]) => `${m}: ${n}`).join(' · ')}</span>}
        <div style="display:flex;gap:8px">
          {s.running && !s.paused ? <button onClick={() => void act('pause')} style={sbtn}>Pause</button> : <button onClick={() => void act('start')} style={pbtn}>{s.done ? 'Fortsett' : 'Start'}</button>}
        </div>
        {s.error && <span style="font-size:12px;color:#ff8a7a">{s.error}</span>}
      </>}
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    </div>
  );
}

export function AiSettingsPanel() {
  const [c, setC] = useState<AiCfg | null>(null), [key, setKey] = useState(''), [msg, setMsg] = useState('');
  useEffect(() => { ai.aiCfg().then(setC).catch((e) => setMsg(errText(e))); }, []);
  if (!c) return msg ? <span style={muted}>{msg}</span> : null;
  const up = (p: Partial<AiCfg>) => setC({ ...c, ...p });
  const save = async () => {
    try { setC(await ai.aiSet({ provider: c.provider, ollamaUrl: c.ollamaUrl, ollamaModel: c.ollamaModel, anthropicModel: c.anthropicModel, ...(key ? { anthropicKey: key } : {}) })); setKey(''); setMsg('Lagret'); } catch (e) { setMsg(errText(e)); }
  };
  return (
    <div style={card}>
      <span style="font-size:16px;font-weight:600">KI-tolkning (valgfritt)</span>
      <span style={muted}>Brukes av «Spill noe til …» og podkastsammendraget. Uten KI brukes enkle regler og tittel + første setning.</span>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        {([['', 'Av'], ['ollama', 'Ollama (lokalt)'], ['anthropic', 'Anthropic API']] as const).map(([v, n]) => <button key={v} onClick={() => up({ provider: v })} style={c.provider === v ? pbtn : sbtn}>{n}</button>)}
      </div>
      {c.provider === 'ollama' && <>
        <input value={c.ollamaUrl} onInput={(e) => up({ ollamaUrl: e.currentTarget.value })} placeholder="http://maskin:11434" style={inp} />
        <input value={c.ollamaModel} onInput={(e) => up({ ollamaModel: e.currentTarget.value })} placeholder="modell, f.eks. llama3.2" style={inp} />
      </>}
      {c.provider === 'anthropic' && <>
        <input type="password" value={key} onInput={(e) => setKey(e.currentTarget.value)} placeholder={c.hasKey ? `Lagret nøkkel ${c.anthropicKey}` : 'API-nøkkel'} style={inp} />
        <input value={c.anthropicModel} onInput={(e) => up({ anthropicModel: e.currentTarget.value })} placeholder="modell" style={inp} />
      </>}
      <div style="display:flex;gap:8px;align-items:center"><button onClick={() => void save()} style={pbtn}>Lagre</button>{msg && <span style={muted}>{msg}</span>}</div>
    </div>
  );
}

// ---------------------------------------------------------------- filtre i Navidrome-søket
const toSong = (h: TagHit): NdSong => ({ id: h.id, title: h.title, artist: h.artist, album: h.album, duration: h.duration, coverArt: h.cover || undefined });

export function TagFilterBar({ onResults }: { onResults: (l: NdSong[] | null) => void }) {
  const [f, setF] = useState<TagFilter>({}), [err, setErr] = useState('');
  const active = Object.values(f).some(Boolean);
  useEffect(() => {
    if (!active) { onResults(null); return; }
    ai.search(f).then((r) => { setErr(''); onResults(r.items.map(toSong)); }).catch((e) => { setErr(errText(e)); onResults([]); });
  }, [f.mood, f.energy, f.acoustic, f.instrumental, f.bpm]);
  const sel = (k: keyof TagFilter, opts: [string, string][], label: string) => (
    <select value={f[k] ?? ''} onChange={(e) => setF({ ...f, [k]: e.currentTarget.value })} style={inp + ';height:32px;font-size:13px'}>
      <option value="">{label}</option>
      {opts.map(([v, n]) => <option key={v} value={v}>{n}</option>)}
    </select>
  );
  return (
    <div style="flex-shrink:0;display:flex;gap:6px;flex-wrap:wrap;align-items:center">
      {sel('mood', MOODS.map((m) => [m, m.charAt(0).toUpperCase() + m.slice(1)]), 'Stemning')}
      {sel('energy', [['lav', 'Lav'], ['middels', 'Middels'], ['høy', 'Høy']], 'Energi')}
      {sel('acoustic', [['1', 'Akustisk'], ['0', 'Elektronisk']], 'Lyd')}
      {sel('instrumental', [['1', 'Instrumental'], ['0', 'Med vokal']], 'Vokal')}
      {sel('bpm', [['60-90', '60–90 BPM'], ['90-120', '90–120 BPM'], ['120-140', '120–140 BPM'], ['140-200', '140+ BPM']], 'Tempo')}
      {active && <button onClick={() => setF({})} style={sbtn}>Nullstill</button>}
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
    </div>
  );
}

// ---------------------------------------------------------------- Plugins → Podkastsammendrag
export function PodsumPanel() {
  const [p, setP] = useState<PodSum | null>(null), [msg, setMsg] = useState(''), [kind, setKind] = useState<'rss' | 'nrk'>('rss'), [id, setId] = useState(''), [busy, setBusy] = useState(false);
  useEffect(() => { ai.podsum().then(setP).catch((e) => setMsg(errText(e))); }, []);
  if (!p) return msg ? <span style={muted}>{msg}</span> : null;
  const save = async (b: Partial<PodSum>) => { try { setP(await ai.podsumSet(b)); setMsg(''); } catch (e) { setMsg(errText(e)); } };
  const preview = async () => { setBusy(true); try { const last = await ai.podsumPreview(); setP({ ...p, last }); } catch (e) { setMsg(errText(e)); } setBusy(false); };
  const morgen = async () => { try { setP(await ai.podsumSet({ action: 'morgen' })); setMsg('Lagt til i Morgen-rutinen'); } catch (e) { setMsg(errText(e)); } };
  return (
    <div style="display:flex;flex-direction:column;gap:12px">
      <div style="display:flex;gap:10px;align-items:center"><Toggle on={p.enabled} onChange={(v) => void save({ enabled: v })} /><span>Les opp hver dag kl.</span>
        <input type="time" value={p.time} onChange={(e) => void save({ time: e.currentTarget.value })} style={inp + ';width:110px'} /></div>
      <div style="display:flex;gap:10px;align-items:center"><Toggle on={p.llm} onChange={(v) => void save({ llm: v })} /><span>Oppsummer med KI {p.llmReady ? '' : '(ikke satt opp – bruker tittel + første setning)'}</span></div>
      <div style="display:flex;gap:10px;align-items:center"><span>Stemmevolum</span>
        <input type="range" min={0.2} max={1.5} step={0.1} value={p.voiceVol} onChange={(e) => void save({ voiceVol: Number(e.currentTarget.value) })} /></div>
      <span style="font-weight:600">Podkaster du følger</span>
      {p.follow.length === 0 && <span style={muted}>Ingen ennå. Legg til en RSS-adresse eller en NRK-podkast (ID, f.eks. «abels-taarn»).</span>}
      {p.follow.map((f, i) => (
        <div key={f.kind + f.id} style="display:flex;gap:8px;align-items:center">
          <span style="font-size:11px;color:#d9a441;text-transform:uppercase">{f.kind}</span>
          <span class="ellip" style="flex:1;font-size:13px">{f.title || f.id}</span>
          <button onClick={() => void save({ follow: p.follow.filter((_, j) => j !== i) })} style={sbtn}>Fjern</button>
        </div>
      ))}
      <form onSubmit={(e) => { e.preventDefault(); if (id.trim()) { void save({ follow: [...p.follow, { kind, id: id.trim(), title: '' }] }); setId(''); } }} style="display:flex;gap:6px">
        <select value={kind} onChange={(e) => setKind(e.currentTarget.value as 'rss' | 'nrk')} style={inp}><option value="rss">RSS</option><option value="nrk">NRK</option></select>
        <input value={id} onInput={(e) => setId(e.currentTarget.value)} placeholder={kind === 'rss' ? 'https://…/feed.xml' : 'NRK-podkast-ID'} style={inp + ';flex:1'} />
        <button type="submit" style={sbtn}>Følg</button>
      </form>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button disabled={busy} onClick={() => void preview()} style={sbtn}>{busy ? 'Lager …' : 'Forhåndsvis'}</button>
        <button onClick={() => { void ai.podsumRun().then(() => setMsg('Leser opp …')); }} style={pbtn}>Les opp nå</button>
        <button onClick={() => void morgen()} style={sbtn}>Legg til i Morgen-rutinen</button>
      </div>
      {p.last?.text && <span style={muted}>{p.last.text}</span>}
      {p.last?.items?.map((it, i) => (
        <div key={i} style="display:flex;gap:8px;align-items:center">
          <span class="ellip" style="flex:1;font-size:13px">{it.show} – {it.title}</span>
          <button onClick={() => { void ai.podsumPlay(i).then((r) => setMsg('Spiller ' + r.playing)).catch((e) => setMsg(errText(e))); }} style={sbtn}>Spill</button>
        </div>
      ))}
      {msg && <span style={muted}>{msg}</span>}
    </div>
  );
}
