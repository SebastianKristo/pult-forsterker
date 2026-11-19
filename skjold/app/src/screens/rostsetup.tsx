// Legg til enhet → Skjold Røst: appen kobler telefonen kort til Røst sitt oppsettnett «Skjold-Rost», sender Wi-Fi og
// romnavn, kobler tilbake til hjemmenettet og venter til Røst dukker opp i Lyrion (/api/rost på denne Skjold-enheten).
// I nettleseren (ikke appen) vises en manuell veiledning med 192.168.4.1.
import { useEffect, useRef, useState } from 'preact/hooks';
import type { ComponentChildren } from 'preact';
import { signal } from '@preact/signals';
import { apiReq } from '../lib/api';
import { go, mode } from '../lib/store';
import { SkjoldWifi, canJoinWifi, wifiErrCode } from '../lib/skjoldwifi';
import { ROST_AP, rostConnect, rostName, rostReboot, rostRebootHome, rostScan, rostSetName, rostWaitJoin, waitForRost, type RostNet } from '../lib/rostsetup';
import type { RostSpeaker } from './rost';
import { Bars, Lock } from './onboard';

const A = '#d9a441';
const RLIST = ['Stue', 'Kjøkken', 'Soverom', 'Kontor', 'Barnerom', 'Bad', 'Gang', 'Verksted'];
const WAIT_S = 90;

type Step = 'intro' | 'join' | 'form' | 'send' | 'done' | 'guide';
type Task = 'name' | 'wifi' | 'join' | 'boot' | 'home' | 'lyrion';
type TaskState = 'wait' | 'run' | 'ok' | 'warn' | 'fail';

/** Tilstand som signaler (tilbake-knappen og skjermbildeskriptet kan styre den). */
export const rs = {
  step: signal<Step>('intro'), err: signal(''), joined: signal(false),
  nets: signal<RostNet[] | null | undefined>(undefined), pick: signal<number | 'man' | null>(null), ssid: signal(''), pw: signal(''),
  room: signal('Stue'), custom: signal(false),
  tasks: signal<Partial<Record<Task, TaskState>>>({}), left: signal(WAIT_S), found: signal<RostSpeaker | null>(null), ip: signal(''), fail: signal('')
};
let known = new Set<string>();   // Røst-id-er som fantes før oppsettet (for å kjenne igjen den nye)
let busy = false;

function reset(): void {
  rs.step.value = canJoinWifi() ? 'intro' : 'guide'; rs.err.value = ''; rs.joined.value = false; rs.nets.value = undefined;
  rs.pick.value = null; rs.ssid.value = ''; rs.pw.value = ''; rs.tasks.value = {}; rs.left.value = WAIT_S; rs.found.value = null; rs.ip.value = ''; rs.fail.value = '';
}
export function openRostSetup(): void { reset(); mode.value = 'rost'; }

async function release(): Promise<void> { rs.joined.value = false; try { await SkjoldWifi.disconnect(); } catch { /* allerede frakoblet */ } }
function leave(page: 'grp' | 'rooms'): void { void release(); mode.value = 'app'; go(page); }

/** Android-tilbake / Tilbake-knappen. */
export function rostBack(): boolean {
  const s = rs.step.value;
  if (s === 'send' && busy) return true;            // ikke avbryt midt i sendingen
  if (s === 'form' || s === 'join') { void release(); rs.step.value = 'intro'; rs.err.value = ''; return true; }
  leave('rooms');
  return true;
}

function Shell({ n, title, text, children, back = true }: { n: number; title: string; text: ComponentChildren; children: ComponentChildren; back?: boolean }) {
  return (
    <div class="dshell" data-testid="rost-setup">
      <div class="dsc" style="flex:1;display:flex;flex-direction:column;padding:8px 20px 18px;gap:16px;min-height:0;overflow:auto;scrollbar-width:none;color-scheme:dark">
        <div style="display:flex;align-items:center;justify-content:space-between;min-height:28px">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;color:#8b8b86">LEGG TIL RØST{n ? ` · ${n} AV 4` : ''}</span>
          {back && <button onClick={() => rostBack()} style="border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:6px 0">{rs.step.value === 'intro' || rs.step.value === 'guide' ? 'Avbryt' : 'Tilbake'}</button>}
        </div>
        {n > 0 && <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:4px">
          {[1, 2, 3, 4].map((i) => <div key={i} style={`height:3px;border-radius:2px;background:${i <= n ? A : '#2a2a28'}`} />)}
        </div>}
        <h1 style="margin:0;font-size:28px;font-weight:600;line-height:1.15;text-align:left">{title}</h1>
        <p style="margin:0;font-size:13px;color:#a9a9a3;line-height:1.5;text-align:left">{text}</p>
        {children}
      </div>
    </div>
  );
}

const Btn = ({ ok = true, label, onClick, testid }: { ok?: boolean; label: string; onClick: () => void; testid?: string }) => (
  <button onClick={() => { if (ok) onClick(); }} data-testid={testid} style={`height:52px;flex-shrink:0;border-radius:14px;border:none;background:${ok ? A : '#242426'};color:${ok ? '#0b0b0c' : '#8b8b86'};font-size:15px;font-weight:600;cursor:pointer`}>{label}</button>
);
const Ghost = ({ label, onClick }: { label: string; onClick: () => void }) => (
  <button onClick={onClick} style="height:48px;flex-shrink:0;border-radius:14px;border:1px solid #2e2e30;background:transparent;font-size:14px;cursor:pointer;color:#f2f2ee">{label}</button>
);
const Err = ({ children }: { children: ComponentChildren }) => (
  <div data-testid="rost-err" style="padding:12px 14px;border-radius:14px;border:1px solid #3a2a20;background:#1a1210;font-size:13px;color:#ffb4a6;line-height:1.5;flex-shrink:0">{children}</div>
);
const Num = ({ i, children }: { i: number; children: ComponentChildren }) => (
  <div style="display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-top:1px solid #242426">
    <span style={`flex-shrink:0;width:24px;height:24px;border-radius:50%;background:#2a2112;border:1px solid #5a4420;color:#f0c46a;font-size:12px;font-weight:600;display:grid;place-items:center`}>{i}</span>
    <span style="font-size:14px;line-height:1.45;color:#e4e4df">{children}</span>
  </div>
);
const CARD = 'display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;flex-shrink:0;overflow:hidden';
const B = ({ children }: { children: ComponentChildren }) => <b style="color:#f2f2ee;font-weight:600">{children}</b>;

// ---------- 1: slå på ----------
function Intro() {
  useEffect(() => {   // husk hvilke Røst som finnes fra før (telefonen er fortsatt på hjemmenettet)
    apiReq<{ minis?: RostSpeaker[] }>('/api/rost').then((r) => { known = new Set((r.minis ?? []).map((m) => m.id)); }).catch(() => undefined);
  }, []);
  const join = async () => {
    rs.err.value = ''; rs.step.value = 'join';
    try {
      await SkjoldWifi.connect({ ssid: ROST_AP.ssid, password: ROST_AP.password, timeoutMs: 30000 });
      rs.joined.value = true;
      await waitForRost();
      rs.step.value = 'form'; rs.nets.value = undefined;
      rs.nets.value = await rostScan().catch(() => null);
    } catch (e) {
      const code = wifiErrCode(e);
      await release();
      rs.step.value = 'intro';
      rs.err.value = code === 'UNSUPPORTED' ? 'unsupported' : code === 'DENIED' ? 'denied' : code === 'NOT_FOUND' ? 'notfound' : 'noanswer';
    }
  };
  const err = rs.err.value;
  return (
    <Shell n={1} title="Slå på Røst" text="Røst lager sitt eget Wi-Fi-nett når den ikke har fått Wi-Fi ennå. Appen kobler telefonen dit et øyeblikk og sender ditt Wi-Fi.">
      <div style={CARD}>
        <Num i={1}>Sett Røst i strømmen.</Num>
        <Num i={2}>Vent til skjermen viser <B>RECOVERY</B> (ca. 10 sekunder). Da er Røst i oppsettmodus.</Num>
        <Num i={3}>Trykk <B>Koble til Røst</B>. Telefonen spør om den kan koble til <B>{ROST_AP.ssid}</B>. Svar ja.</Num>
      </div>
      <span style="font-size:12px;color:#8b8b86;line-height:1.5">Telefonen er borte fra hjemmenettet i under ett minutt. Hold den nær Røst.</span>
      {err === 'notfound' && <Err>Fant ikke <B>{ROST_AP.ssid}</B>-nettet. Står Røst i oppsettmodus? Skjermen skal vise RECOVERY. Har Røst Wi-Fi fra før, lager den ikke nettet. Prøv igjen nærmere Røst.</Err>}
      {err === 'denied' && <Err>Telefonen fikk ikke lov til å koble til {ROST_AP.ssid}. Trykk Koble til Røst igjen og godta spørsmålet.</Err>}
      {err === 'noanswer' && <Err>Telefonen kom på {ROST_AP.ssid}, men Røst svarte ikke på {ROST_AP.ip}. Trekk ut strømmen, sett den i igjen og prøv på nytt.</Err>}
      {err === 'unsupported' && <Err>Denne telefonen kan ikke bytte Wi-Fi fra appen (krever Android 10 eller nyere). <button onClick={() => { rs.step.value = 'guide'; rs.err.value = ''; }} style="border:none;background:none;color:#d9a441;font-size:13px;padding:0;cursor:pointer;text-decoration:underline">Vis manuell veiledning</button>.</Err>}
      <div style="margin-top:auto;display:flex;flex-direction:column;gap:10px">
        <Btn label={err ? 'Prøv igjen' : 'Koble til Røst'} onClick={() => void join()} testid="rost-join" />
        <button onClick={() => { rs.step.value = 'guide'; rs.err.value = ''; }} style="height:36px;border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer">Sett opp manuelt i stedet</button>
      </div>
    </Shell>
  );
}

function Joining() {
  return (
    <Shell n={2} title="Kobler til Røst" text={<>Telefonen kobler til <B>{ROST_AP.ssid}</B>. Godta spørsmålet hvis telefonen viser det.</>}>
      <div style={CARD}><div style="display:flex;align-items:center;gap:12px;padding:16px 14px"><Spinner /><span style="font-size:14px">{rs.joined.value ? 'Røst svarer, henter nettverk …' : 'Kobler til ' + ROST_AP.ssid + ' …'}</span></div></div>
    </Shell>
  );
}

function Spinner({ size = 18 }: { size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" style="flex-shrink:0;animation:rostspin 0.9s linear infinite"><style>{'@keyframes rostspin{to{transform:rotate(360deg)}}'}</style><circle cx="12" cy="12" r="9" fill="none" stroke="#2e2e30" stroke-width="3" /><path d="M21 12a9 9 0 0 0-9-9" fill="none" stroke={A} stroke-width="3" stroke-linecap="round" /></svg>;
}

// ---------- 3: Wi-Fi og rom ----------
function Form() {
  const nets = rs.nets.value, pick = rs.pick.value, man = pick === 'man';
  const picked = typeof pick === 'number' ? nets?.[pick] : undefined;
  const ssid = man ? rs.ssid.value.trim() : picked?.ssid ?? '';
  const needPw = man ? true : !!picked && !picked.open;
  const room = rs.room.value.trim(), custom = rs.custom.value;
  const ok = !!ssid && (!needPw || rs.pw.value.length >= 8 || (man && rs.pw.value.length === 0)) && !!room;
  const rescan = async () => { rs.nets.value = undefined; rs.nets.value = await rostScan().catch(() => null); };
  const row = (on: boolean, i: number) => `display:flex;justify-content:space-between;align-items:center;gap:10px;min-height:50px;padding:0 14px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:${on ? '#1c170d' : 'transparent'};cursor:pointer;font-size:14px;text-align:left;color:#f2f2ee;width:100%`;
  const fld = 'height:48px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:#141415;font-size:16px;outline:none;flex-shrink:0;color:#f2f2ee';
  const pass = rs.err.value === 'password';
  return (
    <Shell n={3} title="Wi-Fi og rom" text="Velg nettet Røst skal bruke. Røst støtter 2,4 GHz. Passordet sendes bare til Røst.">
      <div class="row between" style="display:flex;justify-content:space-between;align-items:center;flex-shrink:0">
        <span style="font-size:13px;color:#8b8b86">Nett Røst ser</span>
        <button onClick={() => void rescan()} style="border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:4px 0">Søk på nytt</button>
      </div>
      <div style={CARD} data-testid="rost-nets">
        {nets === undefined && <div style={row(false, 0) + ';color:#8b8b86;cursor:default;gap:10px;justify-content:flex-start'}><Spinner size={14} />Røst leter etter nettverk …</div>}
        {nets === null && <div style={row(false, 0) + ';color:#8b8b86;cursor:default'}>Fikk ikke listen fra Røst. Skriv inn navnet under.</div>}
        {(nets ?? []).slice(0, 8).map((n, i) => (
          <button key={n.ssid} onClick={() => { rs.pick.value = i; }} style={row(pick === i, i)}>
            <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0">{n.ssid}</span>
            <span style="display:flex;align-items:center;gap:8px;flex-shrink:0">{!n.open && <Lock />}<Bars sig={n.signal} /><span style="font-size:12px;color:#f0c46a;min-width:9px">{pick === i ? '✓' : ''}</span></span>
          </button>
        ))}
        <button onClick={() => { rs.pick.value = 'man'; }} style={row(man, 1) + ';color:#c9c9c4'}><span>Annet nettverk …</span><span style="font-size:12px;color:#f0c46a">{man ? '✓' : ''}</span></button>
      </div>
      {man && <input value={rs.ssid.value} onInput={(e) => { rs.ssid.value = e.currentTarget.value; }} placeholder="Nettverksnavn (SSID)" autoCapitalize="off" autoCorrect="off" spellcheck={false} style={fld} data-testid="rost-ssid" />}
      {needPw && <input type="password" value={rs.pw.value} onInput={(e) => { rs.pw.value = e.currentTarget.value; if (pass) rs.err.value = ''; }} placeholder={man ? 'Passord (tomt for åpent nett)' : 'Passord'} style={fld + (pass ? ';border-color:#7a3a2e' : '')} data-testid="rost-pw" />}
      {pass && <Err>Røst fikk ikke koblet til «{ssid}». Sjekk passordet og prøv igjen. Røst har lagd {ROST_AP.ssid}-nettet igjen, så telefonen er fortsatt koblet til den.</Err>}
      {rs.err.value === 'send' && <Err>Fikk ikke sendt til Røst{rs.fail.value ? ` (${rs.fail.value})` : ''}. Står telefonen fortsatt på {ROST_AP.ssid}? Prøv igjen.</Err>}
      <span style="font-size:13px;color:#8b8b86;margin-top:4px">Hvilket rom står den i?</span>
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;flex-shrink:0">
        {RLIST.map((r) => { const on = !custom && rs.room.value === r; return (
          <button key={r} onClick={() => { rs.room.value = r; rs.custom.value = false; }} style={`height:38px;padding:0 6px;border-radius:999px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#1c170d' : '#141415'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:12.5px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{r}</button>
        ); })}
      </div>
      <button onClick={() => { if (!custom) { rs.custom.value = true; rs.room.value = ''; } }} style={`display:flex;align-items:center;gap:10px;height:44px;flex-shrink:0;padding:0 14px;border-radius:12px;border:1px dashed ${custom ? A : '#3a3a37'};background:${custom ? '#1c170d' : 'transparent'};color:${custom ? '#f0c46a' : '#c9c9c4'};font-size:14px;cursor:pointer;text-align:left`}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>Skriv eget navn
      </button>
      {custom && <input value={rs.room.value} onInput={(e) => { rs.room.value = e.currentTarget.value.slice(0, 20); }} placeholder="For eksempel Hytta" maxLength={20} style={fld + ';border-color:#d9a441'} data-testid="rost-room" />}
      {!!room && <span style="font-size:12px;color:#8b8b86;line-height:1.5">Vises som <span style="font-family:'IBM Plex Mono',monospace;color:#f0c46a">{rostName(room)}</span> i Lyrion og Skjold.</span>}
      <div style="margin-top:auto;padding-top:4px;display:flex;flex-direction:column"><Btn ok={ok} label="Send til Røst" onClick={() => void send(ssid, needPw ? rs.pw.value : '', rostName(room))} testid="rost-send" /></div>
    </Shell>
  );
}

function setTask(t: Task, s: TaskState): void { rs.tasks.value = { ...rs.tasks.value, [t]: s }; }
const norm = (s: string) => s.toLowerCase().replace(/[-_\s]+/g, ' ').replace('røst', 'rost').trim();

/** 4: send navn og Wi-Fi, vent på at Røst kobler til, start den, koble telefonen tilbake og vent på Lyrion. */
async function send(ssid: string, pwd: string, name: string): Promise<void> {
  if (busy) return;
  busy = true; rs.err.value = ''; rs.fail.value = ''; rs.tasks.value = {}; rs.found.value = null; rs.ip.value = '';
  rs.step.value = 'send';
  try {
    setTask('name', 'run');
    // Nytt forsøk etter feil passord: telefonen kan ha mistet Skjold-Rost underveis – koble til igjen ved behov
    try { await waitForRost(4000); } catch {
      try { await SkjoldWifi.connect({ ssid: ROST_AP.ssid, password: ROST_AP.password, timeoutMs: 30000 }); rs.joined.value = true; await waitForRost(); }
      catch { rs.err.value = 'send'; rs.fail.value = 'fant ikke ' + ROST_AP.ssid; rs.step.value = 'form'; return; }
    }
    try { await rostSetName(name); setTask('name', 'ok'); } catch { setTask('name', 'warn'); }   // navnet kan settes senere
    setTask('wifi', 'run');
    try { await rostConnect(ssid, pwd, name); setTask('wifi', 'ok'); }
    catch (e) { rs.fail.value = e instanceof Error ? e.message : String(e); rs.err.value = 'send'; rs.step.value = 'form'; return; }
    setTask('join', 'run');
    const j = await rostWaitJoin(ssid);
    if (!j.ok && j.why === 'password') { rs.err.value = 'password'; rs.pw.value = ''; rs.step.value = 'form'; return; }
    setTask('join', j.ok ? 'ok' : 'warn');
    if (j.ok) rs.ip.value = j.ip;
    setTask('boot', 'run');
    let booted = await rostReboot();
    setTask('home', 'run');
    await release();
    setTask('home', 'ok');
    if (!booted && rs.ip.value) { await new Promise((r) => setTimeout(r, 3000)); booted = await rostRebootHome(rs.ip.value); }
    setTask('boot', booted ? 'ok' : 'warn');
    await waitLyrion(name);
  } finally { busy = false; }
}

async function waitLyrion(name: string): Promise<void> {
  setTask('lyrion', 'run'); rs.left.value = WAIT_S; rs.fail.value = '';
  const t0 = Date.now(), want = norm(name);
  let lyrion: boolean | null = null;
  while (Date.now() - t0 < WAIT_S * 1000) {
    try {
      const r = await apiReq<{ lyrion?: boolean; minis?: RostSpeaker[] }>('/api/rost');
      lyrion = !!r.lyrion;
      const list = r.minis ?? [];
      const hit = list.find((m) => (!!rs.ip.value && m.ip === rs.ip.value) || norm(m.name) === want) ?? list.find((m) => m.connected && !known.has(m.id));
      if (hit) { rs.found.value = hit; setTask('lyrion', 'ok'); rs.step.value = 'done'; return; }
    } catch { /* telefonen er kanskje ikke tilbake på hjemmenettet ennå */ }
    await new Promise((r) => setTimeout(r, 3000));
    rs.left.value = Math.max(0, WAIT_S - Math.round((Date.now() - t0) / 1000));
  }
  setTask('lyrion', 'fail');
  rs.fail.value = lyrion === false ? 'nolyrion' : 'notfound';
}

const TASKS: [Task, (n: string, s: string) => string][] = [
  ['name', (n) => 'Gir Røst navnet ' + n],
  ['wifi', () => 'Sender Wi-Fi til Røst'],
  ['join', (_, s) => 'Røst kobler til «' + s + '»'],
  ['boot', () => 'Starter Røst'],
  ['home', () => 'Kobler telefonen tilbake til hjemmenettet'],
  ['lyrion', () => 'Venter på Røst i Lyrion']
];

function Sending() {
  const t = rs.tasks.value, man = rs.pick.value === 'man';
  const ssid = man ? rs.ssid.value.trim() : (typeof rs.pick.value === 'number' ? rs.nets.value?.[rs.pick.value]?.ssid : '') ?? '';
  const name = rostName(rs.room.value), fail = rs.fail.value;
  const icon = (s?: TaskState) => s === 'run' ? <Spinner size={16} />
    : s === 'ok' ? <span style="width:16px;text-align:center;color:#6fcf7f;font-size:14px">✓</span>
    : s === 'warn' ? <span style="width:16px;text-align:center;color:#f0c46a;font-size:14px">!</span>
    : s === 'fail' ? <span style="width:16px;text-align:center;color:#ff8a7a;font-size:14px">✕</span>
    : <span style="width:16px;height:16px;display:grid;place-items:center"><span style="width:6px;height:6px;border-radius:50%;background:#3a3a37" /></span>;
  return (
    <Shell n={4} back={!!fail} title={fail ? 'Fant ikke Røst' : 'Setter opp Røst'} text={fail ? 'Røst fikk Wi-Fi-oppsettet, men dukket ikke opp i Lyrion.' : 'Hold appen åpen. Dette tar vanligvis under ett minutt.'}>
      <div style={CARD} data-testid="rost-tasks">
        {TASKS.map(([k, label], i) => (
          <div key={k} style={`display:flex;align-items:center;gap:12px;min-height:46px;padding:0 14px;border-top:1px solid ${i ? '#242426' : 'transparent'};font-size:13.5px;color:${t[k] ? '#f2f2ee' : '#6b6b67'}`}>
            {icon(t[k])}<span style="flex:1;min-width:0">{label(name, ssid)}</span>
            {k === 'lyrion' && t[k] === 'run' && <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#8b8b86">{rs.left.value} s</span>}
          </div>
        ))}
      </div>
      {t.join === 'warn' && !fail && <span style="font-size:12px;color:#8b8b86;line-height:1.5">Telefonen mistet kontakten med Røst mens den koblet til ruteren. Det er vanlig – appen ser etter den i Lyrion.</span>}
      {fail === 'nolyrion' && <Err>Skjold får ikke kontakt med Lyrion. Sjekk at Lyrion kjører (Innstillinger → Tjenester), og prøv igjen.</Err>}
      {fail === 'notfound' && <Err>Røst dukket ikke opp i Lyrion etter {WAIT_S} sekunder. Sjekk at Lyrion kjører, og at Røst og Skjold er på samme nett. Viser telefonen {ROST_AP.ssid}-nettet igjen, var Wi-Fi-passordet feil – start på nytt.</Err>}
      {fail && <div style="margin-top:auto;display:flex;flex-direction:column;gap:10px">
        <Btn label="Vent litt til" onClick={() => { setTask('lyrion', 'run'); void waitLyrion(name); }} />
        <Ghost label="Start på nytt" onClick={() => reset()} />
      </div>}
    </Shell>
  );
}

function Done() {
  const f = rs.found.value;
  return (
    <Shell n={4} back={false} title="Klar" text={<><B>{f?.name ?? rostName(rs.room.value)}</B> er på nettet og står i Lyrion. Velg hvilke radiokanaler knappene 1–4 på Røst skal spille.</>}>
      <div style={CARD + ';align-items:center;padding:22px 14px;gap:10px'} data-testid="rost-done">
        <div style="width:64px;height:64px;border-radius:50%;background:#14261a;border:1px solid #2f5a3a;display:grid;place-items:center"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#6fcf7f" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg></div>
        <span style="font-size:16px;font-weight:600">{f?.name ?? rostName(rs.room.value)}</span>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#8b8b86">{f?.ip || rs.ip.value || 'tilkoblet'} · Lyrion</span>
      </div>
      <div style="margin-top:auto;display:flex;flex-direction:column;gap:10px">
        <Btn label="Velg favorittknappene" onClick={() => leave('grp')} testid="rost-buttons" />
        <Ghost label="Legg til en Røst til" onClick={() => reset()} />
        <button onClick={() => leave('rooms')} style="height:36px;border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer">Ferdig</button>
      </div>
    </Shell>
  );
}

// ---------- nettleser: manuell veiledning ----------
function Guide() {
  const [looking, setLooking] = useState(false);
  const native = canJoinWifi();
  return (
    <Shell n={0} title="Sett opp Røst" text={native ? 'Slik gjør du det for hånd.' : 'I nettleseren kan ikke Skjold bytte Wi-Fi for deg. I Skjold-appen på telefonen gjør appen dette selv. Slik gjør du det for hånd:'}>
      <div style={CARD} data-testid="rost-guide">
        <Num i={1}>Sett Røst i strømmen og vent til skjermen viser <B>RECOVERY</B>.</Num>
        <Num i={2}>Koble telefonen eller PC-en til Wi-Fi-nettet <B>{ROST_AP.ssid}</B>. Passordet er <span style="font-family:'IBM Plex Mono',monospace;color:#f0c46a">{ROST_AP.password}</span>.</Num>
        <Num i={3}>Oppsettsiden åpner seg som regel av seg selv. Hvis ikke, åpne <span style="font-family:'IBM Plex Mono',monospace;color:#f0c46a">http://{ROST_AP.ip}</span>.</Num>
        <Num i={4}>Velg Wi-Fi-nettet ditt og skriv passordet. Vent til siden viser at Røst er tilkoblet.</Num>
        <Num i={5}>Trykk <B>Exit Recovery</B> nederst, så starter Røst som høyttaler.</Num>
        <Num i={6}>Koble deg tilbake til hjemmenettet. Røst dukker opp under Grupper → Skjold Røst. Har du flere, gi hver sitt navn på Røst-siden (fanen Squeezelite, for eksempel <span style="font-family:'IBM Plex Mono',monospace">-n Skjold-Rost-Bad</span>).</Num>
      </div>
      {looking && <SearchOnly onDone={() => setLooking(false)} />}
      <div style="margin-top:auto;display:flex;flex-direction:column;gap:10px">
        {!looking && <Btn label="Jeg er ferdig – se etter Røst" onClick={() => setLooking(true)} testid="rost-look" />}
        <Ghost label="Tilbake til Rom" onClick={() => leave('rooms')} />
      </div>
    </Shell>
  );
}

/** Etter manuelt oppsett: se etter en ny Røst i /api/rost. */
function SearchOnly({ onDone }: { onDone: () => void }) {
  const [left, setLeft] = useState(WAIT_S), [hit, setHit] = useState<RostSpeaker | null>(null), [lyr, setLyr] = useState<boolean | null>(null);
  const stop = useRef(false);
  useEffect(() => {
    stop.current = false;
    void (async () => {
      const t0 = Date.now();
      while (!stop.current && Date.now() - t0 < WAIT_S * 1000) {
        try {
          const r = await apiReq<{ lyrion?: boolean; minis?: RostSpeaker[] }>('/api/rost');
          setLyr(!!r.lyrion);
          const m = (r.minis ?? []).find((x) => x.connected && !known.has(x.id)) ?? (r.minis ?? []).find((x) => x.connected);
          if (m) { setHit(m); return; }
        } catch { /* prøv igjen */ }
        await new Promise((res) => setTimeout(res, 3000));
        setLeft(Math.max(0, WAIT_S - Math.round((Date.now() - t0) / 1000)));
      }
      setLeft(0);
    })();
    return () => { stop.current = true; };
  }, []);
  if (hit) return <div style={CARD + ';padding:14px;gap:10px'}><span style="font-size:14px"><span style="color:#6fcf7f">✓</span> Fant <B>{hit.name}</B></span><Btn label="Velg favorittknappene" onClick={() => leave('grp')} /></div>;
  if (left === 0) return <Err>{lyr === false ? 'Skjold får ikke kontakt med Lyrion. Sjekk at Lyrion kjører.' : `Fant ingen Røst i Lyrion etter ${WAIT_S} sekunder. Sjekk at Lyrion kjører, og at Røst fikk riktig Wi-Fi-passord.`} <button onClick={onDone} style="border:none;background:none;color:#d9a441;padding:0;cursor:pointer;text-decoration:underline">Lukk</button></Err>;
  return <div style={CARD}><div style="display:flex;align-items:center;gap:12px;padding:14px"><Spinner /><span style="font-size:14px;flex:1">Ser etter Røst i Lyrion …</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#8b8b86">{left} s</span></div></div>;
}

export function RostSetup() {
  useEffect(() => {
    if (!canJoinWifi() && rs.step.value === 'intro') rs.step.value = 'guide';
    return () => { if (rs.joined.value) void release(); };   // gå aldri ut av oppsettet med telefonen på Skjold-Rost
  }, []);
  const s = rs.step.value;
  if (s === 'guide') return <Guide />;
  if (s === 'join') return <Joining />;
  if (s === 'form') return <Form />;
  if (s === 'send') return <Sending />;
  if (s === 'done') return <Done />;
  return <Intro />;
}
