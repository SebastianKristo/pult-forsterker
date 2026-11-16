// Innstillinger → Home Assistant: finn servere på nettet, logg inn (Home Assistants egen innloggingsside, eller token),
// og bla i entitetene – kameraer med bilde, ringeknapper/sensorer, lys og brytere. Daemon: pi/skjold_ha.py (/api/ha/…).
import { useEffect, useState } from 'preact/hooks';
import { credFor, getBase } from '../lib/api';

const A = '#d9a441';
const pbtn = `height:38px;padding:0 16px;border-radius:999px;border:none;background:${A};color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap`;
const sbtn = 'height:38px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:13px;cursor:pointer;white-space:nowrap';
const chip = (on: boolean) => `height:32px;padding:0 13px;border-radius:999px;border:1px solid ${on ? '#f2f2ee' : '#2e2e30'};background:${on ? '#f2f2ee' : 'transparent'};color:${on ? '#0b0b0c' : '#f2f2ee'};font-size:12.5px;cursor:pointer;white-space:nowrap`;
const inp = 'height:38px;padding:0 12px;border-radius:10px;border:1px solid #2e2e30;background:#121213;color:#f2f2ee;font-size:13px;min-width:0';
const hint = 'font-size:12.5px;color:#a9a9a3;line-height:1.5';
const CARD = 'display:flex;flex-direction:column;gap:12px;padding:16px;border-radius:16px;background:#141415;border:1px solid #242426';
const KICK = "font-family:'IBM Plex Mono',monospace;font-size:10.5px;letter-spacing:.12em;color:#8b8b86";

async function call<T = any>(path: string, body?: unknown, timeout = 20000): Promise<T> {
  const base = getBase(), ac = new AbortController(), tm = setTimeout(() => ac.abort(), timeout);
  try {
    const init: RequestInit = { credentials: credFor(base), signal: ac.signal };
    if (body !== undefined) { init.method = 'POST'; init.headers = { 'Content-Type': 'application/json' }; init.body = JSON.stringify(body); }
    const r = await fetch(base + path, init);
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error((j as any).error || 'HTTP ' + r.status);
    return j as T;
  } finally { clearTimeout(tm); }
}
const err = (e: unknown) => (e instanceof Error ? e.message : String(e));

interface HaStatus { connected: boolean; url?: string; name?: string; version?: string; error?: string; camera_entity?: string; trigger_entity?: string }
interface Server { name: string; url: string; version?: string }
interface Ent { entity_id: string; domain: string; name: string; state: string; device_class?: string }

const TABS: [string, string, string][] = [
  ['Kameraer', 'camera', ''], ['Ringeknapp', 'binary_sensor,event,sensor', ''], ['Lys', 'light', ''],
  ['Brytere', 'switch,input_boolean', ''], ['Scener', 'scene,script', ''], ['Alle', '', ''],
];

export function HomeAssistantPanel() {
  const [st, setSt] = useState<HaStatus | null>(null), [msg, setMsg] = useState('');
  const [servers, setServers] = useState<Server[] | null>(null), [busy, setBusy] = useState(false);
  const [url, setUrl] = useState(''), [token, setToken] = useState(''), [manual, setManual] = useState(false);
  const [tab, setTab] = useState(0), [q, setQ] = useState(''), [ents, setEnts] = useState<Ent[] | null>(null), [tick, setTick] = useState(0);

  const load = () => call<HaStatus>('/api/ha').then((s) => { setSt(s); if (s.url) setUrl(s.url); }).catch((e) => setMsg(err(e)));
  useEffect(() => {
    void load();
    const p = new URLSearchParams(location.search);   // tilbake fra innloggingssiden
    if (p.get('ha')) setMsg(p.get('ha') === 'ok' ? 'Innlogget i Home Assistant.' : 'Innloggingen feilet. Prøv igjen, eller bruk token.');
  }, []);
  useEffect(() => {
    if (!st?.connected) return;
    setEnts(null);
    const t = setTimeout(() => call<{ entities: Ent[] }>('/api/ha/entities?domains=' + encodeURIComponent(TABS[tab]?.[1] ?? '') + '&q=' + encodeURIComponent(q))
      .then((r) => setEnts(r.entities)).catch((e) => { setEnts([]); setMsg(err(e)); }), q ? 300 : 0);
    return () => clearTimeout(t);
  }, [st?.connected, tab, q]);
  useEffect(() => { if (tab !== 0) return; const iv = setInterval(() => setTick((x) => x + 1), 5000); return () => clearInterval(iv); }, [tab]);

  const find = async () => { setBusy(true); setMsg(''); try { setServers((await call<{ servers: Server[] }>('/api/ha/discover', undefined, 15000)).servers); } catch (e) { setMsg(err(e)); } setBusy(false); };
  const login = (u: string) => { location.href = getBase() + '/api/ha/login?url=' + encodeURIComponent(u) + '&back=' + encodeURIComponent(location.href.split('?')[0] ?? ''); };
  const withToken = async () => { setBusy(true); setMsg(''); try { setSt(await call<HaStatus>('/api/ha', { url, token })); setToken(''); setMsg('Koblet til.'); } catch (e) { setMsg(err(e)); } setBusy(false); };
  const logout = async () => { await call('/api/ha', { logout: true }).catch(() => {}); setSt({ connected: false }); setEnts(null); setMsg('Logget ut.'); };
  const use = async (k: 'camera_entity' | 'trigger_entity', id: string) => {
    try { await call('/api/doorbell', { [k]: id }); setSt((s) => (s ? { ...s, [k]: id } : s)); setMsg(k === 'camera_entity' ? 'Dørkameraet er valgt.' : 'Ringeknappen er valgt.'); } catch (e) { setMsg(err(e)); }
  };

  if (!st) return <div style={CARD}><span style={hint}>{msg || 'Laster …'}</span></div>;
  return (
    <div style={CARD}>
      <div style="display:flex;align-items:center;gap:10px">
        <span style="font-size:15px;font-weight:600">Home Assistant</span>
        <span style={KICK + `;color:${st.connected ? '#6fcf7f' : '#8b8b86'}`}>{st.connected ? 'TILKOBLET' : 'IKKE TILKOBLET'}</span>
        <div style="flex:1" />
        {st.connected && <button onClick={() => void logout()} style={sbtn}>Logg ut</button>}
      </div>

      {st.connected ? (
        <>
          <span style={hint}>{st.name}{st.version ? ' · ' + st.version : ''} · {st.url}</span>
          <div style="display:flex;gap:6px;flex-wrap:wrap">{TABS.map(([n], i) => <button key={n} onClick={() => setTab(i)} style={chip(tab === i)}>{n}</button>)}</div>
          <input value={q} placeholder="Søk i entitetene" onInput={(e) => setQ(e.currentTarget.value)} style={inp} />
          {ents === null && <span style={hint}>Henter …</span>}
          {ents && !ents.length && <span style={hint}>Fant ingen.</span>}
          {ents && tab === 0 && (
            <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:10px">
              {ents.map((e) => { const on = st.camera_entity === e.entity_id; return (
                <div key={e.entity_id} style={`border-radius:12px;overflow:hidden;border:1px solid ${on ? A : '#242426'};background:#0f0f10`}>
                  <img src={getBase() + '/api/ha/camera?entity=' + encodeURIComponent(e.entity_id) + '&t=' + tick} alt={e.name} loading="lazy" style="display:block;width:100%;aspect-ratio:16/9;object-fit:cover;background:#1a1a1c" />
                  <div style="display:flex;align-items:center;gap:8px;padding:10px">
                    <div style="display:flex;flex-direction:column;min-width:0;flex:1"><span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{e.name}</span><span style={KICK}>{e.entity_id}</span></div>
                    <button onClick={() => void use('camera_entity', e.entity_id)} style={on ? pbtn : sbtn}>{on ? 'Dørkamera' : 'Bruk'}</button>
                  </div>
                </div>); })}
            </div>)}
          {ents && tab !== 0 && (
            <div style="display:flex;flex-direction:column">
              {ents.slice(0, 300).map((e) => { const trig = tab === 1, on = trig && st.trigger_entity === e.entity_id; return (
                <div key={e.entity_id} style="display:flex;align-items:center;gap:10px;padding:9px 2px;border-top:1px solid #1f1f21">
                  <div style="display:flex;flex-direction:column;min-width:0;flex:1"><span style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{e.name}</span><span style={KICK}>{e.entity_id}</span></div>
                  <span style="font-size:12px;color:#a9a9a3;white-space:nowrap">{e.state}</span>
                  {trig && <button onClick={() => void use('trigger_entity', e.entity_id)} style={on ? pbtn : sbtn}>{on ? 'Ringeknapp' : 'Bruk'}</button>}
                </div>); })}
              {ents.length > 300 && <span style={hint}>Viser 300 av {ents.length}. Søk for å finne flere.</span>}
            </div>)}
          <span style={hint}>Kameraet vises på Skjold Touch når det ringer på. Ringeknappen er sensoren som utløser dørklokka. Lys og brytere til Smarthus-siden på Touch velges under Innstillinger → Skjold Touch.</span>
        </>
      ) : (
        <>
          <span style={hint}>Finn Home Assistant på nettet og logg inn med kontoen din. Skjold lager et eget langtidstoken, så du slipper å lime inn noe.</span>
          {st.error && <span style={hint + ';color:#ff8a7a'}>{st.error}</span>}
          <div style="display:flex;gap:8px;flex-wrap:wrap"><button disabled={busy} onClick={() => void find()} style={pbtn}>{busy && !servers ? 'Søker …' : 'Finn Home Assistant'}</button>
            <button onClick={() => setManual(!manual)} style={sbtn}>{manual ? 'Skjul' : 'Skriv inn adresse'}</button></div>
          {servers && !servers.length && <span style={hint}>Fant ingen. Skriv inn adressen, f.eks. http://homeassistant.local:8123.</span>}
          {servers?.map((s) => (
            <div key={s.url} style="display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:12px;border:1px solid #242426;background:#0f0f10">
              <div style="display:flex;flex-direction:column;min-width:0;flex:1"><span style="font-size:14px;font-weight:600">{s.name}</span><span style={KICK}>{s.url}{s.version ? ' · ' + s.version : ''}</span></div>
              <button onClick={() => login(s.url)} style={pbtn}>Logg inn</button>
              <button onClick={() => { setUrl(s.url); setManual(true); }} style={sbtn}>Token</button>
            </div>))}
          {manual && (
            <div style="display:flex;flex-direction:column;gap:8px">
              <input value={url} placeholder="http://homeassistant.local:8123" onInput={(e) => setUrl(e.currentTarget.value)} style={inp} />
              <div style="display:flex;gap:8px;flex-wrap:wrap"><button disabled={!url} onClick={() => login(url)} style={pbtn}>Logg inn</button></div>
              <span style={hint}>Eller lim inn et langtidstoken (Home Assistant → profilen din → Sikkerhet → Langtidstilgangstokener).</span>
              <input value={token} type="password" placeholder="Langtidstoken" onInput={(e) => setToken(e.currentTarget.value)} style={inp} />
              <button disabled={busy || !url || !token} onClick={() => void withToken()} style={sbtn}>Koble til med token</button>
            </div>)}
        </>
      )}
      {msg && <span style={hint}>{msg}</span>}
    </div>
  );
}
