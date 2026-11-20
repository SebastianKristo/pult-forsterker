// Legg til enhet → «Sett opp Wi-Fi på Skjold Touch / S1 / Node»: enheten har ikke nett og lager oppsett-nettet
// «Skjold-oppsett-XXXX» (pi/skjold_setupnet.py, passord «skjoldoppsett», adresse 10.42.0.1:8765). Appen kobler telefonen
// kort dit (SkjoldWifi-plugin-en), henter nettene enheten ser (GET /api/wifi), sender valgt nett og passord
// (POST /api/wifi) og går tilbake til hjemmenettet, der «Finn enhet» leter etter den.
// Erstatter Bluetooth-veien for iPhone (Safari har ikke Web Bluetooth, så improv-wifi.com virker ikke der).
import { useState } from 'preact/hooks';
import type { ComponentChildren } from 'preact';
import { signal } from '@preact/signals';
import { mode } from '../lib/store';
import { SkjoldWifi, canJoinWifi, wifiErrCode } from '../lib/skjoldwifi';
import { Bars, Lock } from './onboard';

const A = '#d9a441';
const PASS = 'skjoldoppsett', BASE = 'http://10.42.0.1:8765', PREFIX = 'Skjold-oppsett-';
type Net = { ssid: string; signal?: number; security?: string };
type Step = 'intro' | 'join' | 'form' | 'send' | 'done';

export const ew = { step: signal<Step>('intro'), err: signal(''), kode: signal(''), nets: signal<Net[] | null>(null), valgt: signal<Net | null>(null), pw: signal('') };
let joined = false;

export function openEnhetWifi(): void {
  ew.step.value = 'intro'; ew.err.value = ''; ew.nets.value = null; ew.valgt.value = null; ew.pw.value = '';
  mode.value = 'enhetwifi';
}
async function slipp(): Promise<void> { if (joined) { joined = false; try { await SkjoldWifi.disconnect(); } catch { /* allerede frakoblet */ } } }
/** Tilbake-knappen / Android-tilbake. */
export function enhetWifiBack(): boolean {
  const s = ew.step.value;
  if (s === 'send') return true;
  if (s === 'form' || s === 'join') { void slipp(); ew.step.value = 'intro'; return true; }
  void slipp(); mode.value = 'find';
  return true;
}

async function kall<T>(path: string, method: 'GET' | 'POST' = 'GET', body?: unknown, timeoutMs = 8000): Promise<T> {
  const r = await SkjoldWifi.request({ url: BASE + path, method, timeoutMs, ...(body !== undefined ? { body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } } : {}) });
  let j: unknown = {};
  try { j = r.data ? JSON.parse(r.data) : {}; } catch { /* ikke JSON */ }
  if (r.status < 200 || r.status >= 300) throw new Error((j as { error?: string }).error || 'Enheten svarte ' + r.status);
  return j as T;
}

async function koble(): Promise<void> {
  const kode = ew.kode.value.trim().toUpperCase();
  ew.err.value = ''; ew.step.value = 'join';
  try {
    await SkjoldWifi.connect({ ssid: PREFIX + kode, password: PASS, timeoutMs: 30000 });
    joined = true;
    let nets: Net[] | null = null;
    for (let i = 0; i < 8 && !nets; i++) {   // DHCP kan bruke et par sekunder
      try { nets = (await kall<{ networks: Net[] }>('/api/wifi', 'GET', undefined, 5000)).networks; } catch { await new Promise((r) => setTimeout(r, 1500)); }
    }
    if (!nets) throw Object.assign(new Error('svarer ikke'), { code: 'NOANSWER' });
    const sett = new Set<string>();
    ew.nets.value = nets.filter((n) => n.ssid && !n.ssid.startsWith(PREFIX) && !sett.has(n.ssid) && !!sett.add(n.ssid));
    ew.step.value = 'form';
  } catch (e) {
    const c = wifiErrCode(e) || (e as { code?: string }).code || '';
    await slipp();
    ew.step.value = 'intro';
    ew.err.value = c === 'NOT_FOUND' ? `Fant ikke nettet ${PREFIX}${kode}. Sjekk koden på skjermen, og at enheten viser «Med mobilen».`
      : c === 'DENIED' ? 'Telefonen fikk ikke lov til å koble til. Prøv igjen og godta spørsmålet.'
      : c === 'UNSUPPORTED' ? 'Denne telefonen kan ikke bytte Wi-Fi fra appen. Skann QR-koden på skjermen med kameraet i stedet.'
      : `Telefonen kom på oppsett-nettet, men enheten svarte ikke på 10.42.0.1. Prøv igjen.`;
  }
}

async function send(): Promise<void> {
  const n = ew.valgt.value; if (!n) return;
  ew.err.value = ''; ew.step.value = 'send';
  try {
    await kall('/api/wifi', 'POST', { ssid: n.ssid, psk: ew.pw.value }, 15000);
  } catch (e) {
    // Enheten slår av oppsett-nettet mens den bytter, så et brutt svar betyr som regel at den er i gang
    if (!/HTTP|svarer|timed out|tidsavbrudd|network/i.test(String((e as Error).message))) { ew.err.value = (e as Error).message; ew.step.value = 'form'; return; }
  }
  await slipp();
  ew.step.value = 'done';
}

function Shell({ title, text, children }: { title: string; text: ComponentChildren; children: ComponentChildren }) {
  return (
    <div class="dshell">
      <div class="dsc" style="flex:1;display:flex;flex-direction:column;padding:8px 20px 18px;gap:16px;min-height:0;overflow:auto;scrollbar-width:none;color-scheme:dark">
        <div style="display:flex;align-items:center;justify-content:space-between;min-height:28px">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;color:#8b8b86">WI-FI PÅ SKJOLD-ENHET</span>
          {ew.step.value !== 'send' && <button onClick={() => enhetWifiBack()} style="border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:6px 0">{ew.step.value === 'intro' || ew.step.value === 'done' ? 'Lukk' : 'Tilbake'}</button>}
        </div>
        <h1 style="margin:0;font-size:28px;font-weight:600;line-height:1.15">{title}</h1>
        <p style="margin:0;font-size:13px;color:#a9a9a3;line-height:1.5">{text}</p>
        {children}
      </div>
    </div>
  );
}
const Btn = ({ ok = true, label, onClick }: { ok?: boolean; label: string; onClick: () => void }) => (
  <button onClick={() => { if (ok) onClick(); }} style={`height:52px;flex-shrink:0;border-radius:14px;border:none;background:${ok ? A : '#242426'};color:${ok ? '#0b0b0c' : '#8b8b86'};font-size:15px;font-weight:600;cursor:pointer`}>{label}</button>
);
const Err = ({ children }: { children: ComponentChildren }) => <div style="padding:12px 14px;border-radius:14px;border:1px solid #3a2a20;background:#1a1210;font-size:13px;color:#ffb4a6;line-height:1.5;flex-shrink:0">{children}</div>;
const INPUT = 'height:50px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:#141415;font-size:17px;outline:none;color:#f2f2ee';

export function EnhetWifi() {
  const s = ew.step.value;
  const [vis, setVis] = useState(false);
  if (!canJoinWifi()) return (
    <Shell title="Bruk kameraet" text="Appen kan bare bytte Wi-Fi i Skjold-appen på telefonen. Skann QR-koden på skjermen til enheten med kameraet, så åpner oppsettsiden seg."><span /></Shell>);
  if (s === 'intro') {
    const ok = /^[A-Z0-9]{4}$/i.test(ew.kode.value.trim());
    return (
      <Shell title="Sett opp Wi-Fi" text="For Skjold Touch, S1 og Node som ikke er på nett. Appen kobler telefonen et øyeblikk til enhetens oppsett-nett og sender ditt Wi-Fi.">
        <div style="display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;overflow:hidden">
          <span style="padding:12px 14px;font-size:14px;line-height:1.45">1. På enheten: <b>Oppsett → Wi-Fi → Med mobilen → Start</b> (en enhet uten nett viser det av seg selv).</span>
          <span style="padding:12px 14px;border-top:1px solid #242426;font-size:14px;line-height:1.45">2. Skriv de fire tegnene etter <b>{PREFIX}</b> som står på skjermen.</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:14px;color:#8b8b86">{PREFIX}</span>
          <input value={ew.kode.value} maxLength={4} autoCapitalize="characters" autoCorrect="off" spellcheck={false} placeholder="A1B2" onInput={(e) => { ew.kode.value = e.currentTarget.value.toUpperCase(); }} style={INPUT + ";width:110px;font-family:'IBM Plex Mono',monospace;letter-spacing:.12em;text-transform:uppercase"} />
        </div>
        {!!ew.err.value && <Err>{ew.err.value}</Err>}
        <div style="margin-top:auto;display:flex;flex-direction:column;gap:10px">
          <Btn ok={ok} label={ew.err.value ? 'Prøv igjen' : 'Koble til enheten'} onClick={() => void koble()} />
          <span style="font-size:12px;color:#8b8b86;line-height:1.5;text-align:center">Telefonen er borte fra hjemmenettet i under ett minutt.</span>
        </div>
      </Shell>);
  }
  if (s === 'join' || s === 'send') return (
    <Shell title={s === 'join' ? 'Kobler til enheten' : 'Sender Wi-Fi'} text={s === 'join' ? <>Telefonen kobler til <b>{PREFIX + ew.kode.value}</b>. Godta spørsmålet hvis telefonen viser det.</> : <>Enheten kobler til <b>{ew.valgt.value?.ssid}</b>.</>}>
      <span style="font-size:14px;color:#c9c9c4">Et øyeblikk …</span>
    </Shell>);
  if (s === 'done') return (
    <Shell title="Enheten kobler til" text={<>Den kobler til <b>{ew.valgt.value?.ssid}</b> nå. Telefonen er tilbake på hjemmenettet. Går det ikke, kommer oppsett-nettet tilbake på enheten med en melding, og du kan prøve igjen.</>}>
      <div style="margin-top:auto;display:flex;flex-direction:column;gap:10px">
        <Btn label="Finn enheten" onClick={() => { mode.value = 'find'; }} />
      </div>
    </Shell>);
  const v = ew.valgt.value, åpent = (n: Net) => (n.security ?? '') === 'open';
  return (
    <Shell title={v ? 'Passord for ' + v.ssid : 'Velg nett'} text={v ? 'Skriv passordet til hjemmenettet.' : 'Nettene enheten ser.'}>
      {!v ? <div style="display:flex;flex-direction:column;gap:6px">
        {(ew.nets.value ?? []).map((n) => (
          <button key={n.ssid} onClick={() => { ew.valgt.value = n; ew.pw.value = ''; if (åpent(n)) void send(); }} style="min-height:52px;border-radius:12px;border:1px solid #242426;background:#141415;display:flex;align-items:center;gap:12px;padding:0 14px;text-align:left;cursor:pointer">
            <Bars sig={n.signal ?? 0} /><span style="flex:1;min-width:0;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{n.ssid}</span>{!åpent(n) && <Lock />}
          </button>))}
        {!ew.nets.value?.length && <span style="font-size:13px;color:#8b8b86">Enheten fant ingen nett.</span>}
      </div> : <>
        <div style="display:flex;gap:8px">
          <input type={vis ? 'text' : 'password'} value={ew.pw.value} autoCapitalize="off" autoCorrect="off" spellcheck={false} placeholder="Passord" onInput={(e) => { ew.pw.value = e.currentTarget.value; }} style={INPUT + ';flex:1;min-width:0'} />
          <button onClick={() => setVis(!vis)} style="height:50px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:transparent;color:#c9c9c4;font-size:13px;cursor:pointer">{vis ? 'Skjul' : 'Vis'}</button>
        </div>
        {!!ew.err.value && <Err>{ew.err.value}</Err>}
        <div style="margin-top:auto;display:flex;flex-direction:column;gap:10px">
          <Btn ok={ew.pw.value.length >= 8} label="Koble enheten til" onClick={() => void send()} />
          <button onClick={() => { ew.valgt.value = null; ew.err.value = ''; }} style="height:36px;border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer">Velg et annet nett</button>
        </div>
      </>}
    </Shell>
  );
}
