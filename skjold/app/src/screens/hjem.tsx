// Skjold-hjem: stedsvelger (topp), Innstillinger → Steder (skyen) og Innstillinger → Skjold-hjem (enheten selv).
import { useEffect, useState } from 'preact/hooks';
import { api, ApiError, PRODUCT_LABEL, type SkyStatus } from '../lib/api';
import { switchRoom, useRooms } from './phone';
import { go, showToast, everyVisible } from '../lib/store';
import {
  hjem, hjemErr, hjemState, loadEnheter, loadSteder, loginUrl, rolleMerke, sameOrigin, selectSted, setSkyUrl, tofaMangler,
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
/** Enhetene på dette nettverket (S1, Touch, Node …): trykk for å styre en annen. */
function LanEnheter({ lukk }: { lukk: () => void }) {
  const rooms = useRooms();
  return <>{rooms.map((r) => (
    <button key={r.key} data-testid="sted-enhet" onClick={() => { lukk(); if (!r.active) void switchRoom(r.base, r.enhet).catch((e) => showToast(msg(e))); }}
      style={`display:flex;align-items:center;gap:10px;min-height:42px;padding:0 14px 0 24px;border:none;border-top:1px solid #1d1d1f;background:transparent;cursor:pointer;text-align:left;color:#f2f2ee`}>
      <i style={`width:7px;height:7px;border-radius:50%;flex-shrink:0;background:${r.active || r.st ? '#6fcf7f' : '#3a3a37'}`} />
      <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:1px"><span style={`font-size:13.5px;${r.active ? 'color:#f0c46a' : ''}`}>{r.name}</span><span style={`${MONO};font-size:10px;color:#8b8b86`}>{PRODUCT_LABEL[r.product]}{r.active ? ' · styres nå' : r.st ? '' : ' · svarer ikke'}</span></span>
      {r.active && <span style={`color:${A};font-size:13px`}>✓</span>}
    </button>))}</>;
}

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
          {!stedId.value && <LanEnheter lukk={() => setOpen(false)} />}
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
export function StederPanel({ utenAdresse = false }: { utenAdresse?: boolean }) {
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
      {!sameOrigin.value && !utenAdresse && <div style={box}>
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
      <ValhallaLenke />
      {st === 'ok' && <div style={box}>
        <span style="font-size:14px;font-weight:600">Nytt sted</span>
        <div class="row gap10"><input value={nytt} onInput={(e) => setNytt(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === 'Enter') void lag(); }} placeholder="For eksempel Hytta" style={fld} data-testid="nytt-sted" /><button onClick={() => void lag()} style={PRIMARY}>Lag</button></div>
      </div>}
    </div>
  );
}

/** Del hjemmet med andre: eieren inviterer med e-post (de ser hjemmet når de logger inn), fjerner og overfører eierskap. */
function Deling({ s }: { s: Sted }) {
  const [l, setL] = useState<{ epost: string; rolle: 'eier' | 'medlem' }[] | null>(null);
  const [ny, setNy] = useState(''), [busy, setBusy] = useState(false), [meg, setMeg] = useState('');
  const last = async () => { try { setL((await hjem.medlemmer(s.id)).medlemmer); } catch { setL([]); } };
  useEffect(() => { void last(); void hjem.meg().then((m) => setMeg(m.epost)).catch(() => undefined); }, [s.id]);
  const run = async (fn: () => Promise<unknown>, ok: string, ut = false) => {
    setBusy(true);
    try { await fn(); showToast(ok); if (ut) { if (s.id === stedId.value) await selectSted(''); await loadSteder(); } else { await last(); await loadSteder(); } }
    catch (e) { showToast(e instanceof ApiError && e.status === 403 ? 'Bare eieren kan gjøre det' : msg(e)); }
    finally { setBusy(false); }
  };
  const eier = s.rolle === 'eier';
  const gyldig = /^[^@\s]+@[^@\s]+\.[a-z]{2,}$/i.test(ny.trim());
  return <>
    <span style={`${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>DELT MED</span>
    <div style="display:flex;flex-direction:column;border-radius:12px;border:1px solid #242426;overflow:hidden" data-testid="deling">
      {(l ?? []).map((m, i) => (
        <div key={m.epost} style={`display:flex;align-items:center;gap:10px;padding:10px 12px;border-top:1px solid ${i ? '#242426' : 'transparent'}`}>
          <span style={`width:30px;height:30px;border-radius:15px;flex-shrink:0;background:${m.rolle === 'eier' ? '#1c170d' : '#1b1b1c'};border:1px solid ${m.rolle === 'eier' ? '#5a4420' : '#2e2e30'};color:${m.rolle === 'eier' ? '#f0c46a' : '#c9c9c4'};display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:600`}>{m.epost[0]?.toUpperCase()}</span>
          <span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0"><span style="font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{m.epost}{m.epost === meg ? ' (deg)' : ''}</span><span style="font-size:11.5px;color:#8b8b86">{m.rolle === 'eier' ? 'Eier' : 'Medlem – kan bruke og styre enhetene'}</span></span>
          {eier && m.rolle !== 'eier' && <button disabled={busy} onClick={() => { if (confirm(`Gjøre ${m.epost} til eier av ${s.navn}? Du blir medlem.`)) void run(() => hjem.nyEier(s.id, m.epost), 'Eierskapet er overført'); }} style={BTN()}>Gjør til eier</button>}
          {eier && m.rolle !== 'eier' && <button disabled={busy} onClick={() => { if (confirm(`Fjerne ${m.epost} fra ${s.navn}?`)) void run(() => hjem.fjernMedlem(s.id, m.epost), 'Fjernet fra hjemmet'); }} style={BTN('#4a2420', '#e05a4a')}>Fjern</button>}
          {!eier && m.epost === meg && <button disabled={busy} onClick={() => { if (confirm(`Forlate ${s.navn}? Du mister tilgangen til enhetene der.`)) void run(() => hjem.fjernMedlem(s.id, m.epost), 'Du har forlatt hjemmet', true); }} style={BTN('#4a2420', '#e05a4a')}>Forlat</button>}
        </div>))}
      {l === null && <span style="padding:10px 12px;font-size:12px;color:#8b8b86">Henter …</span>}
    </div>
    {eier && <div class="row gap10">
      <input type="email" value={ny} onInput={(e) => setNy(e.currentTarget.value)} onKeyDown={(e) => { if (e.key === 'Enter' && gyldig) void run(() => hjem.inviter(s.id, ny.trim()), 'Delt med ' + ny.trim()).then(() => setNy('')); }} placeholder="E-postadressen til den du vil dele med" autoCapitalize="off" autoCorrect="off" spellcheck={false} style={fld} data-testid="inviter-epost" />
      <button disabled={busy || !gyldig} onClick={() => void run(() => hjem.inviter(s.id, ny.trim()), 'Delt med ' + ny.trim()).then(() => setNy(''))} style={PRIMARY}>Del</button>
    </div>}
    {eier && <span style="font-size:11.5px;color:#8b8b86;line-height:1.45">Den du deler med, logger inn på Skjold-hjem med denne e-postadressen (engangskode på e-post eller Google) og ser hjemmet med en gang – i appen og på hjem.skjold-lab.com.</span>}
  </>;
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
        <Deling s={s} />
        {(() => { const auto = s.autoLegg !== false; return (
          <button disabled={busy} role="switch" aria-checked={auto} data-testid="auto-legg" onClick={() => void run(() => hjem.endreSted(s.id, { autoLegg: !auto }), auto ? 'Nye enheter legges ikke til automatisk' : 'Nye enheter legges til automatisk')} style="display:flex;align-items:center;gap:12px;border:none;background:none;padding:2px 0;cursor:pointer;text-align:left;color:#f2f2ee">
            <span style={`position:relative;width:44px;height:26px;flex-shrink:0;border-radius:13px;background:${auto ? A : '#2a2a2c'};transition:background .2s ease`}><span style={`position:absolute;top:3px;left:${auto ? 21 : 3}px;width:20px;height:20px;border-radius:50%;background:#f2f2ee;transition:left .2s ease`} /></span>
            <span style="display:flex;flex-direction:column;gap:2px"><span style="font-size:14px">Legg til nye enheter automatisk</span><span style="font-size:12px;color:#8b8b86;line-height:1.4">Skjold-enheter på samme nett som en enhet i stedet blir med av seg selv, så du når dem overalt. Enheter du fjerner, legges ikke til igjen.</span></span>
          </button>); })()}
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

/** Bare for tjenesteeieren og administratorer: lenke til Skjold Lab Valhalla (kontoer, hjem og deling for hele tjenesten). */
function ValhallaLenke() {
  const [ja, setJa] = useState(false);
  useEffect(() => { void hjem.meg().then((m) => setJa(!!m.valhalla)).catch(() => setJa(false)); }, []);
  if (!ja) return null;
  return <a href={skyUrl() + '/valhalla/'} target="_blank" rel="noreferrer" style="display:flex;align-items:center;gap:12px;padding:14px 16px;border-radius:14px;border:1px solid #5a4420;background:linear-gradient(135deg,#1c170d,#141415);color:#f2f2ee;text-decoration:none">
    <span style="display:flex;gap:3px;align-items:flex-start;height:20px">{[10, 15, 19, 15, 10].map((h, i) => <i key={i} style={`width:3.5px;height:${h}px;border-radius:2px;background:${i === 2 ? '#d9a441' : '#f2f2ee'}`} />)}</span>
    <span style="display:flex;flex-direction:column;gap:1px;flex:1"><span style={`${MONO};font-size:10px;letter-spacing:.16em;color:#f0c46a`}>SKJOLD LAB</span><span style="font-size:15px;font-weight:600">Valhalla – styr tjenesten</span><span style="font-size:11.5px;color:#8b8b86">Kontoer, hjem, deling og sperring</span></span>
    <span style="color:#f0c46a">↗</span></a>;
}

/** Innstillinger → Skjold-hjem på enheten selv: GET/POST /api/sky. */
export function SkyPanel() {
  const [st, setSt] = useState<SkyStatus | null>(null);
  const [kode, setKode] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async () => { try { setSt(await api.sky()); setErr(''); } catch (e) { setErr(e instanceof ApiError && e.status === 404 ? 'Programvaren på enheten kjenner ikke Skjold-hjem ennå – oppdater den.' : msg(e)); } };
  useEffect(() => { void load(); const t = everyVisible(load, 5000); return () => clearInterval(t); }, []);
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



// ---------- Oppsett i tre steg: konto → denne enheten i et hjem → synk ----------
/** Sky-adressen (avansert): bare når web-UI-et ikke allerede er servert fra skyen. */
export function SkyAdresse() {
  const [url, setUrl] = useState(skyUrl());
  if (sameOrigin.value) return <span style="font-size:12.5px;color:#8b8b86">Du bruker Skjold-hjem på {location.host}.</span>;
  return (
    <div style={box}>
      <span style="font-size:14px;font-weight:600">Sky-adresse</span>
      <span style="font-size:12px;color:#a9a9a3;line-height:1.5">Endres bare hvis du kjører din egen Skjold-sky. Standard er {SKY_DEFAULT.replace(/^https?:\/\//, '')}.</span>
      <div class="row gap10"><input value={url} onInput={(e) => setUrl(e.currentTarget.value)} placeholder={SKY_DEFAULT} style={fld} autoCapitalize="off" spellcheck={false} /><button onClick={() => { setSkyUrl(url); void loadSteder(); showToast('Lagret'); }} style={BTN()}>Lagre</button></div>
    </div>);
}

type Steg = 'ferdig' | 'na' | 'senere';
function StegRad({ n, tittel, tekst, steg, children }: { n: number; tittel: string; tekst: string; steg: Steg; children?: preact.ComponentChildren }) {
  const ferdig = steg === 'ferdig', na = steg === 'na';
  return (
    <div style={`display:grid;grid-template-columns:34px minmax(0,1fr);gap:14px;padding:16px 0;border-top:1px solid #242426;opacity:${steg === 'senere' ? 0.55 : 1}`}>
      <span style={`width:34px;height:34px;border-radius:17px;display:flex;align-items:center;justify-content:center;font-weight:700;font-size:14px;${ferdig ? 'background:#6fcf7f;color:#0b0b0c' : na ? 'background:#1c170d;border:1px solid #5a4420;color:#f0c46a' : 'border:1px solid #2e2e30;color:#8b8b86'}`}>{ferdig ? '✓' : n}</span>
      <div style="display:flex;flex-direction:column;gap:8px;min-width:0">
        <span style="font-size:15px;font-weight:600">{tittel}</span>
        <span style="font-size:12.5px;color:#a9a9a3;line-height:1.5">{tekst}</span>
        {children}
      </div>
    </div>);
}

/** Øverst på Innstillinger → Skjold-hjem: hva er satt opp, og neste steg med én knapp. */
export function SkjoldHjemOppsett() {
  const [sky, setSky] = useState<SkyStatus | null>(null), [cloud, setCloud] = useState<{ enabled: boolean; sist_synk: number } | null>(null);
  const [meg, setMeg] = useState<{ epost: string } | null>(null), [valgt, setValgt] = useState(''), [nyttNavn, setNyttNavn] = useState('Hjemme'), [busy, setBusy] = useState(false);
  const st = hjemState.value, innlogget = st === 'ok';
  const last = async () => {
    try { setSky(await api.sky()); } catch { setSky(null); }
    try { setCloud(await api.cloudStatus()); } catch { setCloud(null); }
  };
  useEffect(() => { void loadSteder(); void last(); const t = everyVisible(last, 8000); return () => clearInterval(t); }, []);
  useEffect(() => { if (innlogget) void hjem.meg().then(setMeg).catch(() => setMeg(null)); }, [innlogget]);
  const egne = steder.value.filter((x) => x.rolle === 'eier');
  const mål = valgt || egne[0]?.id || steder.value[0]?.id || '';
  const koblet = !!sky?.koblet, synk = !!cloud?.enabled;
  const kobl = async (stedIdx?: string) => {
    setBusy(true);
    try {
      let id = stedIdx || mål;
      if (!id) { const s = await hjem.nyttSted(nyttNavn.trim() || 'Hjemme'); id = s.id; await loadSteder(); }
      const k = await hjem.kobling(id);
      await api.skyKobl(k.kode);
      showToast('Skjold er koblet til ' + (steder.value.find((x) => x.id === id)?.navn || nyttNavn));
      await last(); await loadSteder();
    } catch (e) { showToast(msg(e)); } finally { setBusy(false); }
  };
  const loggInn = () => { window.open(loginUrl(), '_blank'); };
  const klar = [innlogget, koblet, synk].filter(Boolean).length;
  return (
    <div style={box + ';padding:20px 22px;gap:4px'} data-testid="skjold-hjem-oppsett">
      <div class="row between" style={{ alignItems: 'baseline', gap: '10px', flexWrap: 'wrap' }}>
        <span style="font-size:18px;font-weight:600">Styr Skjold hvor som helst</span>
        <span style={`${MONO};font-size:11px;color:${klar === 3 ? '#6fcf7f' : '#f0c46a'}`}>{klar} AV 3 KLART</span>
      </div>
      <span style="font-size:13px;color:#a9a9a3;line-height:1.5;margin-bottom:6px">Med Skjold-hjem når du enhetene dine fra telefonen også når du ikke er hjemme, deler hjemmet med familien og tar vare på oppsettet. Hjemme på eget nett virker Skjold alltid – også uten dette.</span>
      <StegRad n={1} tittel={innlogget ? 'Logget inn' + (meg ? ' som ' + meg.epost : '') : tofaMangler.value ? 'Bekreft at det er deg' : 'Logg inn eller lag en Skjold-konto'} steg={innlogget ? 'ferdig' : 'na'}
        tekst={innlogget ? 'Skjold-kontoen din. Profil, sikkerhet og deling finner du på konto-siden.' : 'Det tar et halvt minutt: skriv e-postadressen din og koden du får, eller bruk Google. Kom tilbake hit etterpå.'}>
        {innlogget ? <a href={(sameOrigin.value ? '' : skyUrl()) + '/konto'} target={sameOrigin.value ? undefined : '_blank'} rel="noreferrer" style={`font-size:13px;color:${A}`}>Åpne konto-siden ↗</a>
          : <div class="row gap10" style={{ flexWrap: 'wrap' }}><button onClick={loggInn} style={PRIMARY}>{tofaMangler.value ? 'Bekreft' : 'Logg inn / lag konto'}</button><button onClick={() => void loadSteder()} style={BTN()}>Jeg har logget inn</button></div>}
        {st === 'feil' && <span style="font-size:12px;color:#e05a4a">{hjemErr.value}</span>}
      </StegRad>
      <StegRad n={2} tittel={koblet ? 'Denne Skjold er koblet til «' + (sky?.stedNavn || sky?.sted || 'hjemmet') + '»' : 'Koble denne Skjold til hjemmet ditt'} steg={koblet ? 'ferdig' : innlogget ? 'na' : 'senere'}
        tekst={koblet ? (sky?.tilkoblet ? 'På nett via skyen. Nye Skjold-enheter på samme nett blir med av seg selv.' : 'Koblet, men ikke tilkoblet skyen akkurat nå – sjekk internett.') : 'Ett trykk: Skjold lager en kode og kobler enheten til hjemmet. Har du ikke et hjem ennå, lages det.'}>
        {!koblet && innlogget && (steder.value.length ? <div class="row gap10" style={{ flexWrap: 'wrap' }}>
          {steder.value.length > 1 && <select value={mål} onChange={(e) => setValgt(e.currentTarget.value)} style={fld + ';max-width:220px'}>{steder.value.map((x) => <option key={x.id} value={x.id}>{x.navn}</option>)}</select>}
          <button disabled={busy} onClick={() => void kobl()} style={PRIMARY}>{busy ? 'Kobler til …' : 'Koble til ' + (steder.value.find((x) => x.id === mål)?.navn || '')}</button></div>
          : <div class="row gap10" style={{ flexWrap: 'wrap' }}><input value={nyttNavn} onInput={(e) => setNyttNavn(e.currentTarget.value)} placeholder="Navn på hjemmet" style={fld + ';max-width:220px'} /><button disabled={busy} onClick={() => void kobl()} style={PRIMARY}>{busy ? 'Lager …' : 'Lag hjem og koble til'}</button></div>)}
        {koblet && <button onClick={() => { if (confirm('Koble denne Skjold fra Skjold-hjem? Den virker fortsatt hjemme.')) void api.skyKobleFra().then(() => last()); }} style={BTN('#4a2420', '#e05a4a') + ';align-self:flex-start'}>Koble fra</button>}
      </StegRad>
      <StegRad n={3} tittel={synk ? 'Synk mellom hjemmene er på' : 'Synk favoritter og oppsett (valgfritt)'} steg={synk ? 'ferdig' : koblet ? 'na' : 'senere'}
        tekst={synk ? 'Favoritter, rutiner og EQ følger deg mellom hjemmene. Sist synket ' + (cloud?.sist_synk ? new Date(cloud.sist_synk * 1000).toLocaleString('nb-NO') : 'aldri') + '.' : 'Har du Skjold flere steder? Da kan favoritter, rutiner og EQ være like overalt. Alt krypteres – bare enhetene dine kan lese det.'}>
        {koblet && <button onClick={() => document.getElementById('skjold-synk')?.scrollIntoView({ behavior: 'smooth' })} style={BTN() + ';align-self:flex-start'}>{synk ? 'Velg hva som synkes' : 'Slå på synk'}</button>}
      </StegRad>
    </div>);
}
