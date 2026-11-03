// Skjold-hjem: stedsvelger (topp), Innstillinger → Steder (skyen) og Innstillinger → Skjold-hjem (enheten selv).
import { useEffect, useState } from 'preact/hooks';
import { api, ApiError, type SkyStatus } from '../lib/api';
import { go, showToast } from '../lib/store';
import {
  hjem, hjemErr, hjemState, loadEnheter, loadSteder, loginUrl, rolleMerke, sameOrigin, selectSted, setSkyUrl,
  SKY_DEFAULT, skyUrl, stedId, stedNavn, steder, type Enhet, type Sted
} from '../lib/hjem';

const A = '#d9a441';
const MONO = "font-family:'IBM Plex Mono',monospace";
const msg = (e: unknown) => (e instanceof Error ? e.message : String(e));
const chev = (c = '#8b8b86') => <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke={c} stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6" /></svg>;

/** Merker i romlista: «Hoved», «Reserve n», «aktiv». */
export function RolleMerker({ e }: { e: Enhet }) {
  const r = rolleMerke(e);
  const pill = (t: string, on = false) => <span style={`${MONO};font-size:9.5px;letter-spacing:.04em;padding:2px 6px;border-radius:999px;border:1px solid ${on ? '#5a4420' : '#2e2e30'};color:${on ? '#f0c46a' : '#c9c9c4'};background:${on ? '#1c170d' : 'transparent'};white-space:nowrap`}>{t}</span>;
  return (
    <span style="display:inline-flex;gap:4px;align-items:center;flex-wrap:wrap" data-testid={'merker-' + e.id}>
      <i style={`width:6px;height:6px;border-radius:50%;background:${e.online ? '#6fcf7f' : '#e05a4a'}`} title={e.online ? 'Online' : 'Offline'} />
      {r && pill(r, e.hoved)}
      {e.aktivHoved && pill('aktiv', true)}
      {!e.online && <span style="font-size:10.5px;color:#8b8b86">offline</span>}
    </span>
  );
}

/** Stedsvelger: «Hytta ▾». `big` = tittelrad på telefon (Hjem/Rom), ellers liten (PC-header). */
export function StedPicker({ big = false }: { big?: boolean }) {
  const [open, setOpen] = useState(false);
  const toggle = () => { if (!open) void loadSteder(); setOpen(!open); };
  const pick = (id: string) => { setOpen(false); void selectSted(id).catch((e) => showToast(msg(e))); };
  const row = (id: string, navn: string, sub: string, on: boolean) => (
    <button key={id || 'lan'} onClick={() => pick(id)} data-testid={'sted-' + (id || 'lan')} style={`display:flex;justify-content:space-between;align-items:center;gap:10px;min-height:50px;padding:0 14px;border:none;border-top:1px solid #242426;background:${on ? '#1c170d' : 'transparent'};cursor:pointer;text-align:left`}>
      <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style={`font-size:14px;color:${on ? '#f0c46a' : '#f2f2ee'}`}>{navn}</span><span style={`${MONO};font-size:10.5px;color:#8b8b86`}>{sub}</span></span>
      {on && <span style={`color:${A};font-size:14px`}>✓</span>}
    </button>
  );
  const st = hjemState.value;
  return (
    <span style="position:relative;display:inline-flex;min-width:0">
      <button onClick={toggle} aria-label="Velg sted" data-testid="sted-picker" style={`display:flex;align-items:center;gap:6px;border:none;background:none;padding:0;cursor:pointer;min-width:0;color:#f2f2ee;${big ? 'font-size:28px;font-weight:600' : `height:26px;padding:0 10px;border-radius:999px;border:1px solid #2e2e30;background:#141415;font-size:12px`}`}>
        <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{stedNavn()}</span>{chev(big ? '#c9c9c4' : '#8b8b86')}
      </button>
      {open && <>
        <button onClick={() => setOpen(false)} aria-label="Lukk" style="position:fixed;inset:0;z-index:40;border:none;background:transparent;cursor:default" />
        <div style="position:absolute;top:calc(100% + 8px);left:0;z-index:41;width:300px;max-width:calc(100vw - 40px);background:#141415;border:1px solid #2e2e30;border-radius:14px;box-shadow:0 18px 50px rgba(0,0,0,.55);display:flex;flex-direction:column;overflow:hidden" data-testid="sted-menu">
          <span style={`padding:12px 14px 8px;${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>VELG STED</span>
          {!sameOrigin.value && row('', 'Dette nettverket', 'Skjold-enheter på LAN', !stedId.value)}
          {steder.value.map((s) => row(s.id, s.navn, `${s.enheter} enhet${s.enheter === 1 ? '' : 'er'}${typeof s.online === 'number' ? ' · ' + s.online + ' online' : s.online ? ' · online' : ''}`, s.id === stedId.value))}
          {st === 'laster' && !steder.value.length && <span style="padding:12px 14px;border-top:1px solid #242426;font-size:12px;color:#8b8b86">Henter steder …</span>}
          {st === 'login' && <a href={loginUrl()} target="_blank" rel="noreferrer" onClick={() => setOpen(false)} data-testid="hjem-login" style={`padding:14px;border-top:1px solid #242426;font-size:13px;color:${A}`}>Logg inn på Skjold-hjem ↗</a>}
          {st === 'feil' && <span style="padding:12px 14px;border-top:1px solid #242426;font-size:12px;color:#e05a4a">Skjold-hjem: {hjemErr.value}</span>}
          <button onClick={() => { setOpen(false); go('settings', 'steder'); }} style={`padding:12px 14px;border:none;border-top:1px solid #242426;background:transparent;color:${A};font-size:13px;text-align:left;cursor:pointer`}>Administrer steder …</button>
        </div>
      </>}
    </span>
  );
}

const box = 'display:flex;flex-direction:column;gap:12px;padding:16px;border-radius:16px;border:1px solid #242426;background:#121214';
const fld = 'height:40px;padding:0 12px;border-radius:10px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;width:100%;box-sizing:border-box;color:#f2f2ee';
const BTN = (bd = '#2e2e30', fg = '#f2f2ee') => `height:32px;padding:0 12px;border-radius:8px;border:1px solid ${bd};background:#1b1b1c;color:${fg};font-size:12px;cursor:pointer;white-space:nowrap;flex-shrink:0`;
const PRIMARY = `height:40px;padding:0 16px;border-radius:10px;border:none;background:${A};color:#0b0b0c;font-weight:600;cursor:pointer`;

/** Innstillinger → Steder (skyen). */
export function StederPanel() {
  const [url, setUrl] = useState(skyUrl());
  const [nytt, setNytt] = useState('');
  const [open, setOpen] = useState<string>(stedId.value);
  useEffect(() => { void loadSteder(); }, []);
  const st = hjemState.value;
  const lag = async () => {
    const n = nytt.trim(); if (!n) return;
    try { const s = await hjem.nyttSted(n); setNytt(''); await loadSteder(); if (s?.id) setOpen(s.id); } catch (e) { showToast(msg(e)); }
  };
  return (
    <div class="col gap16" data-testid="steder-panel">
      {!sameOrigin.value && <div style={box}>
        <span style="font-size:15px;font-weight:600">Skjold-hjem</span>
        <p style="margin:0;font-size:12px;color:#a9a9a3;line-height:1.5">Steder samler Skjold-enheter på flere adresser (Hjem, Hytta …). Når en enhet ikke svarer på nettet du er på, går trafikken via skyen.</p>
        <label style="display:flex;flex-direction:column;gap:6px;font-size:12px;color:#8b8b86">Sky-adresse<input value={url} onInput={(e) => setUrl(e.currentTarget.value)} placeholder={SKY_DEFAULT} style={fld} autoCapitalize="off" spellcheck={false} /></label>
        <div class="row gap10">
          <button onClick={() => { setSkyUrl(url); void loadSteder(); }} style={BTN()}>Lagre og hent</button>
          {st === 'login' && <a href={loginUrl()} target="_blank" rel="noreferrer" style={`align-self:center;font-size:13px;color:${A}`}>Logg inn på Skjold-hjem ↗</a>}
        </div>
        {st === 'login' && <span style="font-size:11px;color:#c9b48a;line-height:1.45">Logg inn i fanen som åpnes, og kom tilbake hit. Fra en enhets eget web-UI virker dette bare hvis skyen tillater det (CORS) – ellers bruk {skyUrl().replace(/^https?:\/\//, '')} direkte.</span>}
        {st === 'feil' && <span style="font-size:12px;color:#e05a4a">{hjemErr.value}</span>}
      </div>}
      {steder.value.map((s) => <StedKort key={s.id} s={s} open={open === s.id} onToggle={() => setOpen(open === s.id ? '' : s.id)} />)}
      {st === 'ok' && <div style={box}>
        <span style="font-size:14px;font-weight:600">Nytt sted</span>
        <div class="row gap10"><input value={nytt} onInput={(e) => setNytt(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === 'Enter') void lag(); }} placeholder="For eksempel Hytta" style={fld} data-testid="nytt-sted" /><button onClick={() => void lag()} style={PRIMARY}>Lag</button></div>
      </div>}
    </div>
  );
}

function StedKort({ s, open, onToggle }: { s: Sted; open: boolean; onToggle: () => void }) {
  const [navn, setNavn] = useState(s.navn);
  const [list, setList] = useState<Enhet[]>([]);
  const [kode, setKode] = useState<{ kode: string; utloper: number | string } | null>(null);
  const [busy, setBusy] = useState(false);
  const last = async () => { try { setList(await hjem.enheter(s.id)); } catch (e) { showToast(msg(e)); } };
  useEffect(() => { setNavn(s.navn); }, [s.navn]);
  useEffect(() => { if (open) void last(); }, [open]);
  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true);
    try { await fn(); if (ok) showToast(ok); await Promise.all([last(), loadSteder()]); if (s.id === stedId.value) await loadEnheter(); }
    catch (e) { showToast(e instanceof ApiError && e.status === 403 ? 'Bare eieren kan gjøre det' : msg(e)); }
    finally { setBusy(false); }
  };
  const hoved = list.find((e) => e.hoved)?.id;
  const reserve = list.filter((e) => e.reserveNr).sort((a, b) => (a.reserveNr ?? 0) - (b.reserveNr ?? 0)).map((e) => e.id);
  const setReserve = (r: string[]) => run(() => hjem.endreSted(s.id, { reserve: r }));
  const move = (id: string, d: -1 | 1) => { const r = [...reserve], i = r.indexOf(id), j = i + d; if (i < 0 || j < 0 || j >= r.length) return; [r[i], r[j]] = [r[j]!, r[i]!]; void setReserve(r); };
  const utloper = kode ? (typeof kode.utloper === 'number' ? new Date(kode.utloper < 1e12 ? kode.utloper * 1000 : kode.utloper) : new Date(kode.utloper)) : null;
  return (
    <div style={box} data-testid={'sted-kort-' + s.id}>
      <button onClick={onToggle} style="display:flex;justify-content:space-between;align-items:center;gap:10px;border:none;background:none;padding:0;cursor:pointer;text-align:left;color:#f2f2ee">
        <span style="display:flex;flex-direction:column;gap:2px"><span style="font-size:15px;font-weight:600">{s.navn}{s.id === stedId.value ? <span style={`font-size:11px;color:${A};font-weight:400`}> · valgt</span> : null}</span><span style={`${MONO};font-size:10.5px;color:#8b8b86`}>{s.enheter} enheter · {s.rolle === 'eier' ? 'eier' : 'medlem'}</span></span>
        <span style={`transform:rotate(${open ? 180 : 0}deg);display:flex`}>{chev()}</span>
      </button>
      {open && <>
        <div class="row gap10"><input value={navn} onInput={(e) => setNavn(e.currentTarget.value)} style={fld} aria-label="Navn på sted" data-testid="sted-navn" /><button disabled={busy || !navn.trim() || navn === s.navn} onClick={() => void run(() => hjem.endreSted(s.id, { navn: navn.trim() }), 'Nytt navn lagret')} style={BTN()}>Gi nytt navn</button></div>
        <span style={`${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>ENHETER</span>
        {!list.length && <span style="font-size:12px;color:#8b8b86">Ingen enheter ennå. Trykk «Legg til enhet».</span>}
        <div style="display:flex;flex-direction:column;border-radius:12px;border:1px solid #242426;overflow:hidden">
          {list.map((e, i) => {
            const inR = reserve.includes(e.id), isH = e.id === hoved;
            return (
              <div key={e.id} data-testid={'enhet-' + e.id} style={`display:flex;flex-direction:column;gap:8px;padding:10px 12px;border-top:1px solid ${i ? '#242426' : 'transparent'}`}>
                <div style="display:flex;justify-content:space-between;gap:8px;align-items:center">
                  <span style="display:flex;flex-direction:column;gap:3px;min-width:0"><span style="font-size:14px">{e.navn}{e.rom ? <span style="color:#8b8b86;font-size:12px"> · {e.rom}</span> : null}</span><RolleMerker e={e} /></span>
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap">
                  {!isH && <button disabled={busy} onClick={() => void run(() => hjem.endreSted(s.id, { hoved: e.id, reserve: reserve.filter((x) => x !== e.id) }))} style={BTN('#5a4420', '#f0c46a')}>Gjør til hoved</button>}
                  {!isH && !inR && <button disabled={busy} onClick={() => void setReserve([...reserve, e.id])} style={BTN()}>Legg i reserve</button>}
                  {inR && <><button disabled={busy || reserve.indexOf(e.id) === 0} onClick={() => move(e.id, -1)} aria-label="Flytt opp" style={BTN()}>↑</button><button disabled={busy || reserve.indexOf(e.id) === reserve.length - 1} onClick={() => move(e.id, 1)} aria-label="Flytt ned" style={BTN()}>↓</button><button disabled={busy} onClick={() => void setReserve(reserve.filter((x) => x !== e.id))} style={BTN()}>Ut av reserve</button></>}
                  <button disabled={busy} onClick={() => { if (confirm(`Fjerne ${e.navn} fra ${s.navn}?`)) void run(() => hjem.fjernEnhet(s.id, e.id), 'Enheten er fjernet'); }} style={BTN('#4a2420', '#e05a4a')}>Fjern</button>
                </div>
              </div>
            );
          })}
        </div>
        {kode ? (
          <div style="display:flex;flex-direction:column;align-items:center;gap:8px;padding:16px;border-radius:12px;border:1px solid #5a4420;background:#1c170d" data-testid="kobling-kode">
            <span style={`${MONO};font-size:40px;font-weight:500;letter-spacing:.18em;color:#f0c46a`}>{kode.kode}</span>
            <span style="font-size:13px;color:#f2f2ee;text-align:center;text-wrap:pretty">Tast inn koden på enheten under Innstillinger → Skjold-hjem</span>
            <span style="font-size:11px;color:#8b8b86">{utloper && !isNaN(utloper.getTime()) ? 'Gyldig til ' + utloper.toLocaleTimeString('nb-NO', { hour: '2-digit', minute: '2-digit' }) : 'Gyldig i 10 minutter'}</span>
            <div class="row gap10"><button onClick={() => void last()} style={BTN()}>Oppdater liste</button><button onClick={() => setKode(null)} style={BTN()}>Ferdig</button></div>
          </div>
        ) : (
          <div class="row gap10" style={{ flexWrap: 'wrap' }}>
            <button disabled={busy} data-testid="legg-til-enhet" onClick={async () => { try { setKode(await hjem.kobling(s.id)); } catch (e) { showToast(msg(e)); } }} style={PRIMARY}>Legg til enhet</button>
            {s.id !== stedId.value && <button onClick={() => void selectSted(s.id)} style={BTN()}>Bruk dette stedet</button>}
            {s.rolle === 'eier' && <button disabled={busy} onClick={() => { if (confirm(`Slette ${s.navn}? Enhetene må kobles til på nytt.`)) void (async () => {
              setBusy(true);
              try { await hjem.slettSted(s.id); showToast('Stedet er slettet'); if (s.id === stedId.value) await selectSted(''); await loadSteder(); }
              catch (e) { showToast(e instanceof ApiError && e.status === 403 ? 'Bare eieren kan slette stedet' : msg(e)); }
              finally { setBusy(false); }
            })(); }} style={BTN('#4a2420', '#e05a4a')}>Slett sted</button>}
          </div>
        )}
      </>}
    </div>
  );
}

/** Innstillinger → Skjold-hjem på enheten selv: GET/POST /api/sky. */
export function SkyPanel() {
  const [st, setSt] = useState<SkyStatus | null>(null);
  const [kode, setKode] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async () => { try { setSt(await api.sky()); setErr(''); } catch (e) { setErr(e instanceof ApiError && e.status === 404 ? 'Programvaren på enheten kjenner ikke Skjold-hjem ennå – oppdater den.' : msg(e)); } };
  useEffect(() => { void load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, []);
  const send = async (fn: () => Promise<SkyStatus>) => {
    setBusy(true); setErr('');
    try { setSt(await fn()); setKode(''); } catch (e) { setErr(msg(e)); } finally { setBusy(false); }
  };
  const koblet = !!st?.koblet;
  return (
    <div class="col gap16" data-testid="sky-panel">
      <div style={box}>
        <div class="row between" style={{ alignItems: 'center' }}>
          <span style="font-size:15px;font-weight:600">{koblet ? 'Koblet til ' + (st?.stedNavn || st?.sted || 'Skjold-hjem') : 'Ikke koblet til Skjold-hjem'}</span>
          <span style={`font-size:12px;color:${st?.tilkoblet ? '#3ecf6e' : '#8b8b86'}`}>{st ? (st.tilkoblet ? '● Tilkoblet skyen' : koblet ? '○ Ikke tilkoblet nå' : '') : '…'}</span>
        </div>
        {koblet ? <>
          <span style="font-size:12px;color:#a9a9a3;line-height:1.5">{st?.erHoved ? 'Denne enheten er stedets hovedenhet' : 'Denne enheten er med i stedet'}{st?.aktivHoved ? ` · kontaktpunkt nå: ${st.aktivHoved}` : ''}.</span>
          <div class="row gap10"><button disabled={busy} onClick={() => { if (confirm('Koble enheten fra Skjold-hjem?')) void send(api.skyKobleFra); }} style={BTN('#4a2420', '#e05a4a')}>Koble fra</button></div>
        </> : <>
          <p style="margin:0;font-size:12px;color:#a9a9a3;line-height:1.5">Lag en kode i appen eller på {SKY_DEFAULT.replace(/^https?:\/\//, '')} under Innstillinger → Steder → «Legg til enhet», og tast den inn her.</p>
          <div class="row gap10">
            <input value={kode} onInput={(e) => setKode(e.currentTarget.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6))} placeholder="K7Q2XM" aria-label="Koblingskode" data-testid="sky-kode" style={`${fld};${MONO};font-size:18px;letter-spacing:.2em;text-transform:uppercase`} autoCapitalize="characters" spellcheck={false} />
            <button disabled={busy || kode.length !== 6} onClick={() => void send(() => api.skyKobl(kode))} style={PRIMARY}>Koble til</button>
          </div>
        </>}
        {err && <span style="font-size:12px;color:#e05a4a">{err}</span>}
      </div>
    </div>
  );
}

