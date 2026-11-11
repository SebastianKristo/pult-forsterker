// Smart radio, Oppdag uke, tilstede-modus, vekkelys, spillelister fra radio, plugin-butikk og helsesjekk.
import { t as tr } from '../i18n';
import { everyVisible } from '../lib/store';
import { useEffect, useState } from 'preact/hooks';
import { Toggle } from '../components/ui';
import { fileUrl, x2, type Discover, type Health, type Perf, type Level, type Presence, type RadioList, type SmartRadio, type SrSeed, type StorePlugin } from '../lib/extras2';

const MONO = "'IBM Plex Mono',monospace";
const sbtn = 'height:34px;padding:0 14px;border-radius:8px;border:1px solid #2e2e30;background:#1a1a1b;color:#f2f2ee;font-size:13px;cursor:pointer;white-space:nowrap';
const pbtn = 'height:38px;padding:0 18px;border-radius:9px;border:none;background:#d9a441;color:#1a1408;font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap';
const fld = 'height:34px;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;font-size:13px;outline:none';
const card = 'display:flex;flex-direction:column;gap:10px;padding:16px;border-radius:14px;border:1px solid #242426;background:#141415';
const muted = 'font-size:12px;color:#8b8b86;line-height:1.5';
const LVL: Record<Level, string> = { ok: '#6fcf7f', advarsel: '#f0c46a', feil: '#ff8a7a' };
const DAYS = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag', 'Søndag'];
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e));

function Line({ label, hint, children }: { label: string; hint?: string; children: preact.ComponentChildren }) {
  return (
    <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;padding:6px 0">
      <span style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">{label}</span>{hint && <span style="font-size:11.5px;color:#8b8b86">{hint}</span>}</span>
      <span style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">{children}</span>
    </div>
  );
}
const inp = (v: string | number, on: (s: string) => void, w = 120, type = 'text', ph = '') =>
  <input type={type} value={v as string} placeholder={ph} onInput={(e) => on((e.currentTarget as HTMLInputElement).value)} style={fld + `;width:${w}px`} />;

// ---------------------------------------------------------------- Smart radio
/** Boks i Spiller: «Start radio fra denne låten» og status «Smart radio fra …». */
export function SmartRadioBox({ seed }: { seed: SrSeed | null }) {
  const [sr, setSr] = useState<SmartRadio | null>(null), [busy, setBusy] = useState(false), [err, setErr] = useState('');
  const load = () => x2.smartradio().then(setSr).catch(() => setSr(null));
  useEffect(() => { void load(); const t = everyVisible(load, 10000); return () => clearInterval(t); }, []);
  const run = async (f: () => Promise<SmartRadio>) => { setBusy(true); setErr(''); try { setSr(await f()); } catch (e) { setErr(errText(e)); } setBusy(false); };
  if (!sr && !seed) return null;
  return (
    <div style="display:flex;flex-direction:column;gap:6px">
      {sr?.active ? (
        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <span style="font-size:12px;color:#f0c46a">◉ {sr.label}</span>
          {sr.next[0] && <span style={muted}>Neste: {sr.next[0].artist} – {sr.next[0].title}</span>}
          <button disabled={busy} onClick={() => void run(x2.smartradioSkip)} style={sbtn}>Neste</button>
          <button disabled={busy} onClick={() => void run(x2.smartradioStop)} style={sbtn}>Stopp smart radio</button>
        </div>
      ) : seed && (seed.title || seed.artist) ? (
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          <button disabled={busy} onClick={() => void run(() => x2.smartradioStart(seed))} style={sbtn}>{busy ? 'Finner låter …' : '◉ Start radio fra denne låten'}</button>
          {seed.artist && <button disabled={busy} onClick={() => void run(() => x2.smartradioStart({ ...seed, id: undefined, uri: undefined, title: '' }))} style={sbtn}>Fra artisten</button>}
        </div>
      ) : null}
      {(err || sr?.error) && <span style="font-size:12px;color:#ff8a7a">{err || sr?.error}</span>}
    </div>
  );
}

// ---------------------------------------------------------------- Oppdag uke
/** Kort på Hjem: spill / bland / lagre. */
export function DiscoverCard() {
  const [d, setD] = useState<Discover | null>(null), [msg, setMsg] = useState('');
  useEffect(() => { x2.discover().then(setD).catch(() => setD(null)); }, []);
  if (!d || !d.cfg?.enabled) return null;
  const cur = d.current;
  const run = async (b: Parameters<typeof x2.discoverPost>[0], m: string) => { setMsg(m); try { setD(await x2.discoverPost(b)); setMsg(''); } catch (e) { setMsg(errText(e)); } };
  return (
    <section style={card + ';border-color:#3a3220;background:linear-gradient(135deg,#1c170d,#141415)'}>
      <span style={`font-family:${MONO};font-size:10px;color:#d9a441;letter-spacing:.08em`}>UKENTLIG · LAGET TIL DEG</span>
      <span style="font-size:20px;font-weight:600">{cur ? cur.name : 'Oppdag uke'}</span>
      <span style={muted}>{cur ? `${cur.tracks.length} låter du ikke har hørt på en stund – ${cur.tracks.slice(0, 3).map((t) => t.artist).join(', ')} …` : 'Ingen liste ennå. Den lages automatisk ' + DAYS[d.cfg.day]!.toLowerCase() + ' kl. ' + d.cfg.time + '.'}</span>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        {cur ? <>
          <button onClick={() => void run({ play: true }, 'Starter …')} style={pbtn}>Spill</button>
          <button onClick={() => void run({ play: true, shuffle: true }, 'Starter …')} style={sbtn}>Bland</button>
          <button disabled={cur.saved} onClick={() => void run({ save: true }, 'Lagrer …')} style={sbtn}>{cur.saved ? 'Lagret' : 'Lagre'}</button>
        </> : <button disabled={d.busy} onClick={() => void run({ build: true }, 'Lager lista – kan ta et par minutter …')} style={pbtn}>Lag nå</button>}
      </div>
      {(msg || d.error) && <span style="font-size:12px;color:#8b8b86">{msg || d.error}</span>}
    </section>
  );
}

/** Innstillinger for Oppdag uke (plugin-detalj). */
export function DiscoverPanel() {
  const [d, setD] = useState<Discover | null>(null), [msg, setMsg] = useState('');
  useEffect(() => { x2.discover().then(setD).catch((e) => setMsg(errText(e))); }, []);
  if (!d) return <span style={muted}>{msg || 'Henter …'}</span>;
  const c = d.cfg;
  const set = async (p: Partial<typeof c>) => { try { setD(await x2.discoverPost({ cfg: p })); setMsg('Lagret'); } catch (e) { setMsg(errText(e)); } };
  const src = (k: string) => c.sources.includes(k);
  return (
    <>
      <span style={muted}>Hver uke lages en spilleliste fra lyttehistorikken de siste ukene: toppartister, sjangre og lydprofil (tempo og klang). Låter spilt de siste 90 dagene tas ikke med, og høyst to per artist. Lista lagres i Navidrome som «Oppdag uke N».</span>
      <Line label="Lag lista automatisk"><Toggle on={c.enabled} label="Oppdag uke" onChange={(v) => void set({ enabled: v })} /></Line>
      <Line label="Dag og tid"><select value={c.day} onChange={(e) => void set({ day: +(e.currentTarget as HTMLSelectElement).value })} style={fld}>{DAYS.map((n, i) => <option key={i} value={i}>{n}</option>)}</select>{inp(c.time, (v) => /^\d\d:\d\d$/.test(v) && void set({ time: v }), 80, 'time')}</Line>
      <Line label="Lengde" hint="30–40 låter"><input type="range" min={30} max={40} value={c.size} onChange={(e) => void set({ size: +(e.currentTarget as HTMLInputElement).value })} /><span style={`font-family:${MONO};font-size:12px`}>{c.size}</span></Line>
      <Line label="Historikk" hint="Uker tilbake"><select value={c.weeks} onChange={(e) => void set({ weeks: +(e.currentTarget as HTMLSelectElement).value })} style={fld}>{[4, 5, 6, 7, 8].map((n) => <option key={n} value={n}>{n} uker</option>)}</select></Line>
      <Line label="Kilder">{[['navidrome', 'Navidrome'], ['ma', 'Music Assistant']].map(([k, n]) => <button key={k} onClick={() => void set({ sources: src(k!) ? c.sources.filter((x) => x !== k) : [...c.sources, k!] })} style={sbtn + (src(k!) ? ';border-color:#5a4420;color:#f0c46a' : '')}>{n}</button>)}</Line>
      <Line label="Arkiv" hint="Behold de fire siste listene i Navidrome"><Toggle on={c.archive} label="Arkiv" onChange={(v) => void set({ archive: v })} /></Line>
      <div style="display:flex;gap:10px;align-items:center"><button disabled={d.busy} onClick={async () => { setMsg('Lager lista …'); try { setD(await x2.discoverPost({ build: true })); setMsg('Ferdig'); } catch (e) { setMsg(errText(e)); } }} style={pbtn}>Lag ny liste nå</button><span style={muted}>{msg || d.error || (d.current ? `${d.current.name}: ${d.current.tracks.length} låter` : '')}</span></div>
    </>
  );
}

// ---------------------------------------------------------------- Tilstede-modus
export function PresencePanel({ d, up, saveBtn }: { d: Record<string, any>; up: (k: string, v: unknown) => void; saveBtn: preact.ComponentChildren }) {
  const [p, setP] = useState<Presence | null>(null);
  useEffect(() => { x2.presence().then(setP).catch(() => {}); }, []);
  const rooms = (d.rooms as string[]) || [];
  return (
    <>
      <span style={muted}>Når du er bortreist spiller Skjold radio i tilfeldige økter med lavt volum innenfor tidsvinduet, så det høres ut som noen er hjemme. Kan også slås av og på fra Home Assistant (bryter via MQTT eller tjenesten skjold.presence_mode).</span>
      {p && <Line label="Status" hint={p.plan.length ? 'I dag: ' + p.plan.map((s) => `${s.start}–${s.end}`).join(', ') : undefined}><span style="font-size:12.5px;color:#f0c46a">{p.status}</span></Line>}
      <Line label="Kilde"><select value={d.source} onChange={(e) => up('source', (e.currentTarget as HTMLSelectElement).value)} style={fld}><option value="favorites">Tilfeldig radiofavoritt</option><option value="p1">NRK P1</option><option value="talk">Prat (NRK P2)</option></select></Line>
      <Line label="Tidsvindu">{inp(d.start, (v) => up('start', v), 90, 'time')}<span style={muted}>til</span>{inp(d.end, (v) => up('end', v), 90, 'time')}</Line>
      <Line label="Økter" hint="Minutter, tilfeldig mellom">{inp(d.min_on, (v) => up('min_on', +v), 60, 'number')}<span style={muted}>–</span>{inp(d.max_on, (v) => up('max_on', +v), 60, 'number')}</Line>
      <Line label="Pauser" hint="Minutter, tilfeldig mellom">{inp(d.min_off, (v) => up('min_off', +v), 60, 'number')}<span style={muted}>–</span>{inp(d.max_off, (v) => up('max_off', +v), 60, 'number')}</Line>
      <Line label="Volum" hint="Holdes lavt (maks 40)">{inp(d.volume, (v) => up('volume', Math.min(40, +v)), 60, 'number')}</Line>
      <Line label="Rom" hint="Kommaseparert, f.eks. Stue, Kjøkken">{inp(rooms.join(', '), (v) => up('rooms', v.split(',').map((x) => x.trim()).filter(Boolean)), 200)}<Toggle on={!!d.rotate} label="Bytt rom" onChange={(v) => up('rotate', v)} /></Line>
      {saveBtn}
    </>
  );
}

// ---------------------------------------------------------------- Vekking med lys
export function WakeLightPanel({ light, set }: { light: Record<string, any> | undefined; set: (v: Record<string, any>) => void }) {
  const l = { enabled: false, entities: [] as string[], minutes: 10, step: 20, ha_url: '', ha_token: '', ...(light || {}) };
  const [st, setSt] = useState<{ active: boolean; last: string } | null>(null);
  useEffect(() => { x2.wakeLight().then(setSt).catch(() => {}); }, []);
  const up = (k: string, v: unknown) => set({ ...l, [k]: v });
  return (
    <div style="display:flex;flex-direction:column;gap:4px;padding-top:12px;border-top:1px solid #1f1f21">
      <span style="font-size:13px;font-weight:600">Vekking med lys</span>
      <span style={muted}>Lysene i Home Assistant skrus gradvis opp før alarmen: fra 1 % varmt lys (2200 K) til 100 % (4000 K). Stopper når du slår av alarmen.</span>
      <Line label="Vekkelys"><Toggle on={!!l.enabled} label="Vekkelys" onChange={(v) => up('enabled', v)} /></Line>
      <Line label="Lys" hint="Entity-ID-er, kommaseparert">{inp(l.entities.join(', '), (v) => up('entities', v.split(',').map((x) => x.trim()).filter(Boolean)), 260, 'text', 'light.soverom')}</Line>
      <Line label="Start før alarmen" hint="Minutter">{inp(l.minutes, (v) => up('minutes', Math.max(1, Math.min(60, +v || 10))), 60, 'number')}</Line>
      <Line label="Home Assistant" hint="Tom = samme som dørklokka">{inp(l.ha_url, (v) => up('ha_url', v), 200, 'text', 'http://homeassistant.local:8123')}{inp(l.ha_token, (v) => up('ha_token', v), 160, 'password', 'Langtids-token')}</Line>
      {st?.active && <Line label={st.last || 'Vekkelys på'}><button onClick={() => void x2.wakeLightStop().then(setSt)} style={sbtn}>Stopp lyset</button></Line>}
    </div>
  );
}

// ---------------------------------------------------------------- Spillelister fra radio
export function RadioListPanel({ source = 'recordings' }: { source?: 'recordings' | 'wishlist' }) {
  const [ch, setCh] = useState(''), [res, setRes] = useState<RadioList | null>(null), [msg, setMsg] = useState('');
  useEffect(() => { x2.radioList().then((r) => r.name && setRes(r)).catch(() => {}); }, []);
  const build = async () => { setMsg('Søker i Navidrome …'); try { setRes(await x2.radioListBuild({ source, channel: ch })); setMsg(''); } catch (e) { setMsg(errText(e)); } };
  return (
    <div style={card}>
      <span style="font-size:14px;font-weight:600">Lag spilleliste i Navidrome</span>
      <span style={muted}>{source === 'wishlist' ? 'Låtene i ønskelista samles i spillelista «Gjenkjent».' : 'Låtene fra radioopptak og historikken samles i «Fra radio – <kanal>».'} Låter som finnes i biblioteket legges til; resten vises som mangler.</span>
      <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center">
        {source === 'recordings' && inp(ch, setCh, 160, 'text', 'Kanal (tom = alle)')}
        <button onClick={() => void build()} style={pbtn}>Lag spilleliste</button>
        {res?.name && <a href={fileUrl('/api/radiolist?m3u=1')} style={sbtn + ';display:inline-flex;align-items:center;text-decoration:none'} download>Eksporter M3U</a>}
      </div>
      {msg && <span style={muted}>{msg}</span>}
      {res?.name && <span style="font-size:12.5px"><b>{res.name}</b>: <span style="color:#6fcf7f">{res.found} funnet</span> · <span style="color:#f0c46a">{res.missing} mangler</span></span>}
      {res && res.missingList.length > 0 && <details><summary style={muted}>Vis manglende</summary>{res.missingList.map((m, i) => <div key={i} style="font-size:12px;color:#a9a9a3;padding:2px 0">{m.artist} – {m.title}</div>)}</details>}
    </div>
  );
}

// ---------------------------------------------------------------- Plugin-butikk
export function StorePage() {
  const [inst, setInst] = useState<StorePlugin[]>([]), [cat, setCat] = useState<StorePlugin[]>([]), [msg, setMsg] = useState(''), [catErr, setCatErr] = useState('');
  const [url, setUrl] = useState(''), [sha, setSha] = useState(''), [open, setOpen] = useState<string | null>(null);
  const load = async () => {
    try { setInst((await x2.store()).installed); } catch (e) { setMsg('Får ikke kontakt: ' + errText(e)); }
    try { const c = await x2.storeCatalog(); setCat(c.plugins); setCatErr(c.error || ''); } catch (e) { setCatErr(errText(e)); }
  };
  useEffect(() => { void load(); }, []);
  const act = async (b: Record<string, unknown>, m: string) => { setMsg(m); try { const r = await x2.storePost(b); setMsg(r.error || (r.installed ? `Installert: ${r.installed}` : 'Ferdig')); await load(); } catch (e) { setMsg('Feil: ' + errText(e)); } };
  const upload = async (f: File | undefined) => { if (!f) return; setMsg('Laster opp …'); try { const r = await x2.storeUpload(f, sha); setMsg('Installert: ' + r.installed); await load(); } catch (e) { setMsg('Feil: ' + errText(e)); } };
  const installedIds = new Set(inst.map((p) => p.id));
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      <span style={muted}>Plugins fra butikken kjører isolert i egen prosess med tidsgrense, og får bare det de har bedt om (nett, lyd, innstillinger, tidsplan). Alle filer sjekkes mot sha256 før installasjon.</span>
      {msg && <span style={`font-size:12.5px;color:${msg.startsWith('Feil') ? '#ff8a7a' : '#f0c46a'}`}>{msg}</span>}
      <span style="font-size:14px;font-weight:600">Installert</span>
      {!inst.length && <span style={muted}>Ingen plugins fra butikken ennå.</span>}
      {inst.map((p) => <InstalledCard key={p.id} p={p} open={open === p.id} toggle={() => setOpen(open === p.id ? null : p.id)} act={act} />)}
      <span style="font-size:14px;font-weight:600">Butikk</span>
      {catErr && <span style="font-size:12px;color:#ff8a7a">{catErr}</span>}
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px">
        {cat.map((p) => (
          <div key={p.id} style={card}>
            <span style="font-size:15px;font-weight:600">{p.navn}</span>
            <span style={`font-family:${MONO};font-size:10px;color:#8b8b86`}>{p.kategori} · v{p.versjon} · {p.forfatter}</span>
            <span style="font-size:12.5px;color:#a9a9a3;line-height:1.45;flex:1">{p.beskrivelse}</span>
            <span style={muted}>Tillatelser: {(p.tillatelser || []).join(', ') || 'ingen'}</span>
            <div>{!p.compatible ? <span style={muted}>Krever Skjold {p.minSkjold}</span>
              : p.update ? <button onClick={() => void act({ install: p.id }, 'Oppdaterer …')} style={pbtn}>Oppdater til {p.versjon}</button>
              : installedIds.has(p.id) ? <span style="font-size:12px;color:#6fcf7f">Installert</span>
              : <button onClick={() => void act({ install: p.id }, 'Installerer …')} style={pbtn}>Installer</button>}</div>
          </div>))}
      </div>
      <div style={card}>
        <span style="font-size:14px;font-weight:600">Installer fra adresse eller fil</span>
        <span style={muted}>En .zip med plugin.json, eller en adresse til plugin.json. Oppgi sha256 for å sjekke pakken. Installer bare plugins du stoler på.</span>
        <div style="display:flex;gap:8px;flex-wrap:wrap">{inp(url, setUrl, 300, 'text', 'https://…/plugin.zip')}{inp(sha, setSha, 200, 'text', 'sha256 (valgfritt)')}<button disabled={!url} onClick={() => void act({ url, sha256: sha || undefined }, 'Henter …')} style={sbtn}>Installer</button></div>
        <label style={sbtn + ';display:inline-flex;align-items:center;width:max-content'}>Velg .zip-fil<input type="file" accept=".zip" style="display:none" onChange={(e) => void upload((e.currentTarget as HTMLInputElement).files?.[0])} /></label>
      </div>
    </div>
  );
}

function InstalledCard({ p, open, toggle, act }: { p: StorePlugin; open: boolean; toggle: () => void; act: (b: Record<string, unknown>, m: string) => Promise<void> }) {
  const [vals, setVals] = useState<Record<string, unknown>>({ ...(p.settingsValues || {}) });
  useEffect(() => setVals({ ...(p.settingsValues || {}) }), [p.id, open]);
  const schema = Object.entries(p.settings || {});
  return (
    <div style={card}>
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <span style="display:flex;flex-direction:column;flex:1;min-width:0"><b style="font-size:14px">{p.navn}</b><span style={`font-family:${MONO};font-size:10px;color:${p.error ? '#ff8a7a' : '#8b8b86'}`}>{p.error || `v${p.versjon} · ${(p.tillatelser || []).join(', ') || 'ingen tillatelser'}`}</span></span>
        <Toggle on={p.enabled !== false} label={p.navn} onChange={(v) => void act({ id: p.id, settings: { _enabled: v } }, v ? 'Slår på …' : 'Slår av …')} />
        <button onClick={toggle} style={sbtn}>{open ? 'Lukk' : 'Innstillinger'}</button>
      </div>
      {open && <>
        {schema.map(([k, s]) => (
          <Line key={k} label={s.navn || k}>
            {s.type === 'select' ? <select value={String(vals[k] ?? '')} onChange={(e) => setVals({ ...vals, [k]: (e.currentTarget as HTMLSelectElement).value })} style={fld}>{(s.valg || []).map((o) => <option key={o} value={o}>{o}</option>)}</select>
              : s.type === 'boolean' ? <Toggle on={!!vals[k]} label={k} onChange={(v) => setVals({ ...vals, [k]: v })} />
              : inp(String(vals[k] ?? ''), (v) => setVals({ ...vals, [k]: s.type === 'number' ? +v : v }), 160, s.type === 'number' ? 'number' : s.type === 'time' ? 'time' : s.type === 'password' ? 'password' : 'text')}
          </Line>))}
        <div style="display:flex;gap:8px;flex-wrap:wrap">
          {schema.length > 0 && <button onClick={() => void act({ id: p.id, settings: vals }, 'Lagrer …')} style={pbtn}>Lagre</button>}
          {(p.events || []).includes('test') && <button onClick={() => void act({ id: p.id, run: 'test' }, 'Kjører …')} style={sbtn}>Prøv</button>}
          <button onClick={() => { if (confirm(`Fjerne ${p.navn}?`)) void act({ remove: p.id }, 'Fjerner …'); }} style={sbtn + ';color:#ff8a7a'}>Fjern</button>
        </div>
      </>}
    </div>
  );
}

// ---------------------------------------------------------------- Helsesjekk
export function HealthPanel({ compact = false }: { compact?: boolean }) {
  const [h, setH] = useState<Health | null>(null), [err, setErr] = useState(''), [rep, setRep] = useState<{ text: string; issue: string } | null>(null), [msg, setMsg] = useState('');
  const load = () => { setErr(''); x2.health().then(setH).catch((e) => setErr(errText(e))); };
  useEffect(() => { load(); }, []);
  const report = async () => { setMsg('Lager rapport …'); try { setRep(await x2.healthReport()); setMsg(''); } catch (e) { setMsg(errText(e)); } };
  const copy = async () => { try { await navigator.clipboard.writeText(rep!.text); setMsg('Kopiert'); } catch { setMsg('Kunne ikke kopiere – merk teksten under'); } };
  const download = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([rep!.text], { type: 'text/markdown' })); a.download = 'skjold-feilrapport.md'; a.click(); };
  const items = h ? (compact ? h.items.filter((i) => i.niva !== 'ok') : h.items) : [];
  const up = h ? `${Math.floor(h.uptime / 86400)} d ${Math.floor((h.uptime % 86400) / 3600)} t` : '';
  return (
    <div style={card} data-testid="health">
      <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap">
        <span style="font-size:14px;font-weight:600;flex:1">Helsesjekk</span>
        {h && <span style={`font-size:12.5px;color:${LVL[h.niva]}`}>● {h.niva === 'ok' ? 'Alt ser bra ut' : h.niva === 'advarsel' ? 'Noe bør sjekkes' : 'Feil funnet'}</span>}
        <button onClick={load} style={sbtn}>Sjekk igjen</button>
      </div>
      {err && <span style="font-size:12px;color:#ff8a7a">Får ikke hentet helsesjekken: {err}</span>}
      {!h && !err && <span style={muted}>Sjekker …</span>}
      {h && <span style={muted}>Versjon {h.version} · oppe i {up}</span>}
      {items.map((i) => (
        <div key={i.key} style="display:grid;grid-template-columns:10px minmax(0,1fr);gap:10px;align-items:start;padding:6px 0;border-top:1px solid #1f1f21">
          <i style={`width:8px;height:8px;border-radius:50%;margin-top:5px;background:${LVL[i.niva]}`} />
          <span style="display:flex;flex-direction:column;gap:2px"><b style="font-size:13px;font-weight:600">{i.navn}</b><span style="font-size:12px;color:#a9a9a3">{i.forklaring}</span></span>
        </div>))}
      {h && compact && !items.length && <span style="font-size:12.5px;color:#6fcf7f">Alle sjekker er OK.</span>}
      {!compact && <PerfBox />}
      {h && !compact && h.errors.length > 0 && <details><summary style={muted}>Siste feil i loggen ({h.errors.length})</summary><pre style={`font-family:${MONO};font-size:10.5px;color:#a9a9a3;white-space:pre-wrap;max-height:240px;overflow:auto`}>{h.errors.join('\n')}</pre></details>}
      <div style="display:flex;gap:8px;flex-wrap:wrap;padding-top:6px">
        <button onClick={() => void report()} style={pbtn}>Send feilrapport</button>
        {rep && <><button onClick={() => void copy()} style={sbtn}>Kopier</button><button onClick={download} style={sbtn}>Last ned</button><a href={rep.issue} target="_blank" rel="noreferrer" style={sbtn + ';display:inline-flex;align-items:center;text-decoration:none'}>Opprett GitHub-sak ↗</a></>}
        {msg && <span style={muted}>{msg}</span>}
      </div>
      {rep && <><span style={muted}>Passord, tokens og IP-adresser er maskert. Se over teksten før du deler den.</span><textarea readOnly value={rep.text} style={fld + `;height:160px;padding:8px;font-family:${MONO};font-size:11px`} /></>}
    </div>
  );
}


/** Ytelse på maskinen (CPU, temperatur, minne, lagring, strøm og per tjeneste) – oppdateres hvert 5. sekund. */
function PerfBox() {
  const [p, setP] = useState<Perf | null>(null);
  useEffect(() => { let on = true; const f = () => x2.perf().then((v) => on && setP(v)).catch(() => {}); f(); const id = everyVisible(f, 5000); return () => { on = false; clearInterval(id); }; }, []);
  if (!p) return null;
  const tile = (n: string, v: string, warn = false) => (
    <div style="display:flex;flex-direction:column;gap:2px;padding:8px 10px;border-radius:10px;background:#101011;border:1px solid #1f1f21;min-width:0">
      <span style="font-size:10.5px;color:#8b8b86">{tr(n)}</span><b style={`font-size:15px;font-variant-numeric:tabular-nums;color:${warn ? '#f0a35a' : '#f2f2ee'}`}>{v}</b>
    </div>);
  const pw = p.throttle;
  return (
    <div style="display:flex;flex-direction:column;gap:8px;padding-top:8px;border-top:1px solid #1f1f21">
      <span style="font-size:13px;font-weight:600">{tr('Ytelse')}{p.model ? ' · ' + p.model : ''}</span>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:6px">
        {tile('CPU-bruk', p.cpu_pct == null ? '–' : p.cpu_pct.toFixed(0) + ' %', (p.cpu_pct ?? 0) > 85)}
        {tile('CPU-temperatur', p.temp_c == null ? '–' : p.temp_c.toFixed(0) + ' °C', (p.temp_c ?? 0) >= 70)}
        {tile('Last', p.load ? p.load.map((x) => x.toFixed(2)).join(' · ') : '–', !!p.load && (p.load[0] ?? 0) > p.cpus)}
        {tile('Minnebruk', p.memory ? `${p.memory.pct.toFixed(0)} % (${p.memory.used_mb}/${p.memory.total_mb} MB)` : '–', (p.memory?.pct ?? 0) > 85)}
        {tile('Ledig lagring', p.disk ? p.disk.free_gb.toFixed(1) + ' GB' : '–', (p.disk?.pct ?? 0) > 90)}
        {tile('Strømproblem', !pw ? '–' : pw.under_voltage ? tr('For lav spenning') : pw.throttled || pw.freq_capped ? tr('Strupet') : tr('Ingen strømproblemer'), !!pw?.power_problem)}
      </div>
      {Object.keys(p.services).length > 0 && <div style="display:flex;flex-direction:column;gap:2px">
        <span style="font-size:11px;color:#8b8b86">{tr('Tjenester')}</span>
        {Object.entries(p.services).map(([n, u]) => <span key={n} style={`font-family:${MONO};font-size:11px;color:#a9a9a3`}>{n}: {u.cpu_pct == null ? '–' : u.cpu_pct.toFixed(1) + ' %'} CPU · {u.mem_mb == null ? '–' : u.mem_mb.toFixed(0) + ' MB'}</span>)}
      </div>}
    </div>
  );
}
