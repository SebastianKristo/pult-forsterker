// Oppsett av musikktjenester, steg for steg (som oppsettet av en ny telefon): velg tjeneste → ett spørsmål per skjerm →
// Skjold tester tilkoblingen → ferdig. Åpnes med openSetup('ytm' | 'nd' | 'ma' | 'sp' | 'sw') eller openSetup() for oversikten.
// Innloggingene lagres på Skjold-enheten (/api/settings) og deles med de andre Skjold-enhetene på nettet.
import { t } from '../i18n';
import { signal } from '@preact/signals';
import { useEffect, useRef, useState } from 'preact/hooks';
import type { ComponentChildren } from 'preact';
import { api } from '../lib/api';
import { settings, setSetting, deviceName } from '../lib/store';
import { setLocal } from '../lib/services';
import { ndPing } from '../lib/navidrome';
import { ytmTest } from '../lib/ytm';
import { loadSw, swStations } from '../lib/subwave';
import { SubwaveMark } from '../components/brandmarks';

export type SvcId = 'ytm' | 'nd' | 'ma' | 'sp' | 'sw';
/** null = lukket, '' = oversikten, ellers rett inn i én tjeneste. */
export const setupOpen = signal<SvcId | '' | null>(null);
export const openSetup = (svc: SvcId | '' = '') => { setupOpen.value = svc; };

interface Svc { id: SvcId; name: string; mono: string; c1: string; c2: string; what: string }
const SVCS: Svc[] = [
  { id: 'ytm', name: 'YouTube Music', mono: 'YT', c1: '#ff4e45', c2: '#b3121a', what: 'Spillelister, mikser og album fra kontoen din' },
  { id: 'nd', name: 'Navidrome', mono: 'N', c1: '#6aa9ff', c2: '#2b5fb8', what: 'Ditt eget musikkbibliotek på hjemmenettet' },
  { id: 'ma', name: 'Music Assistant', mono: 'MA', c1: '#3cc8f5', c2: '#0b7fb0', what: 'TIDAL, Qobuz, Deezer, Plex og mer i ett' },
  { id: 'sp', name: 'Spotify Connect', mono: 'S', c1: '#3be27a', c2: '#139c48', what: 'Spill fra Spotify-appen rett til Skjold' },
  { id: 'sw', name: 'SUB/WAVE', mono: 'SW', c1: '#26262a', c2: '#111113', what: 'Din egen AI-DJ-radio' },
];

function isOn(id: SvcId): boolean {
  const s = settings.value;
  if (id === 'ytm') return !!s.ytmCookie && s.ytmEn;
  if (id === 'nd') return !!s.ndUrl && s.ndEn;
  if (id === 'ma') return !!s.maUrl;
  if (id === 'sp') return s.spEn;
  return swStations.value.length > 0;
}

// ---------- utseende ----------
const FONT = "-apple-system,BlinkMacSystemFont,'SF Pro Display','Inter','Segoe UI',system-ui,sans-serif";
const css = `
.swz-bg{position:fixed;inset:0;z-index:60;overscroll-behavior:contain;background:rgba(6,6,8,.55);backdrop-filter:blur(22px) saturate(1.3);-webkit-backdrop-filter:blur(22px) saturate(1.3);display:flex;align-items:center;justify-content:center;padding:max(16px,env(safe-area-inset-top)) max(16px,env(safe-area-inset-right)) max(16px,env(safe-area-inset-bottom)) max(16px,env(safe-area-inset-left));animation:swzf .25s ease both}
.swz{position:relative;width:min(560px,100%);max-height:min(760px,100%);display:flex;flex-direction:column;border-radius:30px;background:linear-gradient(180deg,#1c1c1f,#141416);border:1px solid rgba(255,255,255,.08);box-shadow:0 40px 120px rgba(0,0,0,.6),inset 0 1px 0 rgba(255,255,255,.06);color:#f5f5f7;font-family:${FONT};overflow:hidden;animation:swzu .38s cubic-bezier(.2,.9,.25,1) both}
.swz-top{display:flex;align-items:center;justify-content:space-between;padding:18px 18px 0;min-height:44px}
.swz-x{width:34px;height:34px;border-radius:50%;border:none;background:rgba(255,255,255,.08);color:#d1d1d6;display:flex;align-items:center;justify-content:center;cursor:pointer}
.swz-x:hover{background:rgba(255,255,255,.14)}
.swz-back{border:none;background:none;color:#d9a441;font:500 15px ${FONT};cursor:pointer;padding:6px 4px;display:flex;align-items:center;gap:2px}
.swz-dots{display:flex;gap:6px}
.swz-dots i{width:6px;height:6px;border-radius:3px;background:rgba(255,255,255,.18);transition:all .3s}
.swz-dots i.on{width:18px;background:#f5f5f7}
.swz-body{flex:1;min-height:0;overflow-y:auto;overscroll-behavior:contain;padding:8px 36px 8px;display:flex;flex-direction:column;align-items:center;text-align:center}
.swz-step{display:flex;flex-direction:column;align-items:center;width:100%;animation:swzs .35s cubic-bezier(.2,.9,.25,1) both}
.swz-ic{width:84px;height:84px;border-radius:22px;display:flex;align-items:center;justify-content:center;font:700 28px ${FONT};letter-spacing:-.02em;color:#fff;box-shadow:0 14px 34px rgba(0,0,0,.4),inset 0 1px 0 rgba(255,255,255,.25);margin:10px 0 22px}
.swz h2{margin:0;font:600 28px/1.15 ${FONT};letter-spacing:-.02em;text-wrap:balance}
.swz p.sub{margin:10px 0 0;font:400 15px/1.5 ${FONT};color:#a1a1a6;max-width:400px;text-wrap:pretty}
.swz-field{width:100%;margin-top:24px;display:flex;flex-direction:column;gap:10px;text-align:left}
.swz-in{width:100%;box-sizing:border-box;height:52px;padding:0 16px;border-radius:14px;border:1px solid rgba(255,255,255,.1);background:rgba(255,255,255,.05);color:#f5f5f7;font:400 16px ${FONT};outline:none;transition:border-color .2s,background .2s}
.swz-in:focus{border-color:#d9a441;background:rgba(255,255,255,.07)}
textarea.swz-in{height:120px;padding:14px 16px;resize:none;font:400 13px/1.45 ui-monospace,Menlo,monospace}
.swz-lbl{font:500 13px ${FONT};color:#8e8e93;padding:0 4px}
.swz-err{font:400 13px/1.4 ${FONT};color:#ff6961;padding:0 4px}
.swz-foot{padding:16px 36px 28px;display:flex;flex-direction:column;gap:10px}
.swz-btn{height:54px;border-radius:16px;border:none;background:#f5f5f7;color:#0b0b0c;font:600 17px ${FONT};cursor:pointer;transition:transform .12s,opacity .2s}
.swz-btn:active{transform:scale(.98)}
.swz-btn:disabled{opacity:.35;cursor:default}
.swz-link{height:40px;border:none;background:none;color:#d9a441;font:500 15px ${FONT};cursor:pointer}
.swz-list{width:100%;margin-top:22px;display:flex;flex-direction:column;border-radius:18px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);overflow:hidden;text-align:left}
.swz-row{display:flex;align-items:center;gap:14px;padding:12px 14px;border:none;background:none;color:inherit;cursor:pointer;width:100%;text-align:left;font-family:${FONT}}
.swz-row+.swz-row{border-top:1px solid rgba(255,255,255,.06)}
.swz-row:hover{background:rgba(255,255,255,.04)}
.swz-mini{width:42px;height:42px;border-radius:11px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font:700 14px ${FONT};color:#fff}
.swz-ok{width:22px;height:22px;border-radius:50%;background:#30d158;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.swz-num{display:flex;gap:14px;align-items:flex-start;text-align:left;padding:12px 2px}
.swz-num > b{width:26px;height:26px;border-radius:50%;background:rgba(255,255,255,.1);font:600 13px ${FONT};display:flex;align-items:center;justify-content:center;flex-shrink:0}
.swz-num span{font:400 15px/1.45 ${FONT};color:#d1d1d6}
.swz-num span b{font-weight:600;color:#f5f5f7}
.swz-num code{font:500 13px ui-monospace,Menlo,monospace;color:#f5f5f7;background:rgba(255,255,255,.08);padding:1px 6px;border-radius:6px}
.swz-spin{width:54px;height:54px;border-radius:50%;border:3px solid rgba(255,255,255,.12);border-top-color:#f5f5f7;animation:swzr .9s linear infinite;margin:30px 0 22px}
.swz-big-ok{width:84px;height:84px;border-radius:50%;background:#30d158;display:flex;align-items:center;justify-content:center;margin:20px 0 22px;animation:swzp .5s cubic-bezier(.2,1.4,.4,1) both;box-shadow:0 14px 40px rgba(48,209,88,.35)}
.swz-toggle{width:51px;height:31px;border-radius:16px;border:none;cursor:pointer;position:relative;transition:background .25s;flex-shrink:0}
.swz-toggle i{position:absolute;top:2px;width:27px;height:27px;border-radius:50%;background:#fff;box-shadow:0 2px 6px rgba(0,0,0,.3);transition:left .25s cubic-bezier(.3,1.3,.5,1)}
@keyframes swzf{from{opacity:0}}
@keyframes swzu{from{opacity:0;transform:translateY(24px) scale(.97)}}
@keyframes swzs{from{opacity:0;transform:translateX(18px)}}
@keyframes swzr{to{transform:rotate(360deg)}}
@keyframes swzp{from{opacity:0;transform:scale(.4)}}
@media (max-width:520px){.swz{border-radius:26px}.swz-body{padding:8px 22px}.swz-foot{padding:14px 22px 22px}.swz h2{font-size:25px}}
@media (prefers-reduced-motion:reduce){.swz,.swz-bg,.swz-step,.swz-big-ok{animation:none}.swz-spin{animation-duration:2s}}
`;

const Check = ({ size = 13 }: { size?: number }) => <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>;
const Icon = ({ s, big }: { s: Svc; big?: boolean }) => <div class={big ? 'swz-ic' : 'swz-mini'} style={`background:linear-gradient(145deg,${s.c1},${s.c2})`}>{s.id === 'sw' ? <SubwaveMark /> : s.mono}</div>;
const Steps = ({ items }: { items: ComponentChildren[] }) => <div style="width:100%;margin-top:18px">{items.map((t, i) => <div key={i} class="swz-num"><b>{i + 1}</b><span>{t}</span></div>)}</div>;

/** Ett steg: innholdet i midten, hovedknappen nederst. */
interface Step { body: ComponentChildren; next?: string; can?: boolean; onNext?: () => void | Promise<void>; skip?: [string, () => void] }

// ---------- tjenestene ----------
function useFlow(svc: SvcId, done: () => void): Step[] {
  const s = settings.value;
  const [a, setA] = useState(''), [b, setB] = useState(''), [c, setC] = useState(''), [err, setErr] = useState('');
  const [test, setTest] = useState<'' | 'busy' | 'ok' | string>(''), [testMsg, setTestMsg] = useState('');
  const [sw, setSw] = useState<{ name?: string; url?: string; user?: string; password?: string; extra?: Record<string, string>[]; enabled?: boolean } | null>(null);
  const S = SVCS.find((x) => x.id === svc)!;
  useEffect(() => {   // forhåndsutfyll det som allerede er lagret
    setErr(''); setTest('');
    if (svc === 'nd') { setA(s.ndUrl); setB(s.ndUser); setC(s.ndPass); }
    if (svc === 'ma') { setA(s.maUrl); setB(s.maToken); }
    if (svc === 'ytm') { setA(s.ytmCookie); }
    if (svc === 'sw') { setA(''); setB(''); setC(''); api.plugins().then((r) => { const p = r.plugins.find((x) => x.id === 'subwave'); setSw(p ? { ...(p.cfg as object), enabled: p.enabled } : {}); }).catch(() => setSw({})); }
  }, [svc]);
  const intro = (extra?: ComponentChildren): Step => ({
    body: <><Icon s={S} big /><h2>{S.name}</h2><p class="sub">{S.what}.</p>{extra}</>, next: 'Fortsett'
  });
  const testing = (run: () => Promise<[string, boolean]>): Step => ({
    body: test === 'busy' || test === ''
      ? <><div class="swz-spin" /><h2>Kobler til …</h2><p class="sub">Skjold prøver innloggingen.</p></>
      : test === 'ok'
        ? <><div class="swz-big-ok"><Check size={40} /></div><h2>Ferdig</h2><p class="sub">{testMsg || t('{navn} er klar.', { navn: S.name })} Innloggingen deles med de andre Skjold-enhetene på nettet.</p></>
        : <><Icon s={S} big /><h2>Fikk ikke kontakt</h2><p class="sub">{test}</p></>,
    next: test === 'ok' ? 'Ferdig' : test === 'busy' || test === '' ? 'Kobler til …' : 'Prøv igjen',
    can: test !== 'busy' && test !== '',
    onNext: test === 'ok' ? done : async () => { setTest('busy'); const [m, ok] = await run(); setTestMsg(m); setTest(ok ? 'ok' : m); },
    skip: test !== 'ok' && test !== 'busy' && test !== '' ? ['Lagre likevel', done] : undefined,
  });
  const startTest = async (run: () => Promise<[string, boolean]>) => { setTest('busy'); const [m, ok] = await run(); setTestMsg(m); setTest(ok ? 'ok' : m); };

  if (svc === 'ytm') return [
    intro(<p class="sub" style="margin-top:14px">Krever YouTube Premium. Du logger inn én gang med nettleseren på en datamaskin – Skjold husker det.</p>),
    { body: <><h2>Logg inn i nettleseren</h2><p class="sub">Bruk Chrome, Edge eller Firefox på en datamaskin.</p>
      <Steps items={[<>Åpne <a href="https://music.youtube.com" target="_blank" rel="noopener" style="color:#d9a441">music.youtube.com</a> og logg inn med kontoen din.</>,
        <>Trykk <code>⌥⌘I</code> (Mac) eller <code>F12</code> (Windows) for utviklerverktøyene, og velg fanen <b>Network</b>.</>,
        <>Last siden på nytt, og klikk på en forespørsel som heter <code>browse</code>.</>,
        <>Under <b>Request Headers</b>: høyreklikk på <code>cookie</code> og velg <b>Copy value</b>.</>]} /></>, next: 'Jeg har kopiert den' },
    { body: <><h2>Lim inn cookien</h2><p class="sub">Den blir liggende på Skjold-enheten din og sendes bare til YouTube.</p>
      <div class="swz-field"><textarea class="swz-in" placeholder="VISITOR_INFO1_LIVE=…; __Secure-3PAPISID=…; …" value={a} onInput={(e) => { setA(e.currentTarget.value); setErr(''); }} />
        {err && <span class="swz-err">{err}</span>}</div></>,
      next: 'Koble til', can: a.trim().length > 20,
      onNext: () => {
        const v = a.trim().replace(/^cookie:\s*/i, '');
        if (!/__Secure-3PAPISID=|SAPISID=/.test(v)) { setErr('Cookien mangler __Secure-3PAPISID. Kopier hele verdien fra en forespørsel til music.youtube.com mens du er innlogget.'); throw new Error('stopp'); }
        setLocal('ytmCookie', v); setSetting('ytmEn', true);
        setTimeout(() => void startTest(ytmTest), 900);
      } },
    testing(ytmTest),
  ];

  if (svc === 'nd') {
    const norm = (u: string) => { u = u.trim().replace(/\/+$/, ''); return u && !/^https?:\/\//i.test(u) ? 'http://' + u + (/:\d+$/.test(u) ? '' : ':4533') : u; };
    const run = async (): Promise<[string, boolean]> => (await ndPing() ? ['Navidrome svarte – biblioteket ligger under Bibliotek.', true] : ['Sjekk adressen, brukernavnet og passordet. Navidrome bruker vanligvis port 4533.', false]);
    return [
      intro(),
      { body: <><h2>Hvor er serveren?</h2><p class="sub">Adressen til Navidrome på hjemmenettet, for eksempel <b>192.168.1.20</b> eller <b>musikk.local:4533</b>.</p>
        <div class="swz-field"><input class="swz-in" autoFocus inputMode="url" autoCapitalize="off" autoCorrect="off" placeholder="192.168.1.20:4533" value={a} onInput={(e) => setA(e.currentTarget.value)} /></div></>,
        next: 'Fortsett', can: !!a.trim(), onNext: () => { setA(norm(a)); } },
      { body: <><h2>Logg inn</h2><p class="sub">Samme bruker som i Navidrome sin nettside.</p>
        <div class="swz-field"><input class="swz-in" autoFocus autoCapitalize="off" autoCorrect="off" placeholder="Brukernavn" value={b} onInput={(e) => setB(e.currentTarget.value)} />
          <input class="swz-in" type="password" placeholder="Passord" value={c} onInput={(e) => setC(e.currentTarget.value)} /></div></>,
        next: 'Koble til', can: !!b.trim() && !!c,
        onNext: () => { setLocal('ndUrl', norm(a)); setLocal('ndUser', b); setLocal('ndPass', c); setSetting('ndEn', true); setTimeout(() => void startTest(run), 500); } },
      testing(run),
    ];
  }

  if (svc === 'ma') {
    const run = async (): Promise<[string, boolean]> => {
      try { const r = await api.maStatus(); return r.ok ? ['Music Assistant ' + (r.version || '') + ' er koblet til' + (r.player ? ' · spiller ' + r.player : '') + '.', true] : [r.error || 'Music Assistant svarte ikke.', false]; }
      catch (e) { return [e instanceof Error ? e.message : String(e), false]; }
    };
    const finn = async () => { setErr('Leter …'); try { const r = await api.maDiscover(); if (r.found[0]) { setA(r.found[0]); setErr(''); } else setErr('Fant ingen Music Assistant på nettet. Skriv inn adressen.'); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } };
    return [
      intro(),
      { body: <><h2>Finn Music Assistant</h2><p class="sub">Kjører den i Home Assistant, er adressen som regel <b>homeassistant.local:8095</b>.</p>
        <div class="swz-field"><input class="swz-in" inputMode="url" autoCapitalize="off" autoCorrect="off" placeholder="homeassistant.local:8095" value={a} onInput={(e) => { setA(e.currentTarget.value); setErr(''); }} />
          <button class="swz-link" style="align-self:flex-start" onClick={() => void finn()}>Søk på nettet</button>{err && <span class="swz-err" style={err === 'Leter …' ? 'color:#a1a1a6' : ''}>{err}</span>}</div></>,
        next: 'Fortsett', can: !!a.trim() },
      { body: <><h2>Token</h2><p class="sub">Nyere Music Assistant krever en token: <b>Innstillinger → Brukere</b> i Music Assistant. Hopp over hvis du ikke har det.</p>
        <div class="swz-field"><input class="swz-in" type="password" placeholder="Token (valgfritt)" value={b} onInput={(e) => setB(e.currentTarget.value)} /></div></>,
        next: 'Koble til', onNext: () => { setSetting('maUrl', a.trim()); setSetting('maToken', b.trim()); setSetting('maEn', true); setTimeout(() => void startTest(run), 600); } },
      testing(run),
    ];
  }

  if (svc === 'sp') return [
    intro(<p class="sub" style="margin-top:14px">Krever Spotify Premium. Ingen innlogging her – Skjold dukker opp som en høyttaler i Spotify-appen.</p>),
    { body: <><Icon s={S} big /><h2>Slå på Spotify Connect</h2>
      <div class="swz-list" style="margin-top:26px"><div class="swz-row" style="cursor:default"><span style="flex:1;font-size:16px">Spotify Connect</span>
        <button class="swz-toggle" aria-label="Spotify Connect" style={`background:${s.spEn ? '#30d158' : 'rgba(255,255,255,.16)'}`} onClick={() => setSetting('spEn', !s.spEn)}><i style={`left:${s.spEn ? 22 : 2}px`} /></button></div></div></>,
      next: 'Fortsett', can: s.spEn },
    { body: <><div class="swz-big-ok"><Check size={40} /></div><h2>Klar</h2>
      <Steps items={[<>Åpne Spotify på telefonen og start en låt.</>, <>Trykk på høyttalerikonet nederst.</>, <>Velg <b>{deviceName.value || 'Skjold'}</b>.</>]} /></>, next: 'Ferdig', onNext: done },
  ];

  // SUB/WAVE
  const swOk = (u?: string) => /^https?:\/\//.test(String(u ?? '').trim());
  const swHar = !!sw?.enabled && swOk(sw?.url);
  const swAntall = sw ? [sw.url, ...(sw.extra ?? []).map((x) => x.url)].filter(swOk).length : 0;
  const runSw = async (): Promise<[string, boolean]> => {
    try { loadSw(true); const r = swHar ? await api.subwaveAt(swAntall, true) : await api.subwave(true); return r.configured && !r.error ? ['Stasjonen svarer. Den ligger under Bibliotek → SUB/WAVE.', true] : [String(r.error || 'Stasjonen svarte ikke. Sjekk adressen.'), false]; }
    catch (e) { return [e instanceof Error ? e.message : String(e), false]; }
  };
  return [
    intro(<p class="sub" style="margin-top:14px">{swHar ? `Du har ${swAntall} ${swAntall === 1 ? 'stasjon' : 'stasjoner'}. Legg til en til – alle vises under Bibliotek → SUB/WAVE.` : 'Selvhostet radio der en AI-DJ velger låtene. Du trenger adressen til stasjonen din.'}</p>),
    { body: <><h2>{swHar ? 'Ny stasjon' : 'Adressen til stasjonen'}</h2><p class="sub">For eksempel <b>https://radio.eksempel.no</b>.</p>
      <div class="swz-field"><input class="swz-in" placeholder={'Navn, f.eks. ' + (swHar ? 'Morgenradio' : 'SUB/WAVE')} value={c} onInput={(e) => setC(e.currentTarget.value)} />
        <input class="swz-in" autoFocus inputMode="url" autoCapitalize="off" autoCorrect="off" placeholder="https://…" value={a} onInput={(e) => { setA(e.currentTarget.value); setErr(''); }} />
        <input class="swz-in" type="password" placeholder="Admin-passord (valgfritt – for å hoppe over låter)" value={b} onInput={(e) => setB(e.currentTarget.value)} />
        {err && <span class="swz-err">{err}</span>}</div></>,
      next: 'Koble til', can: /^https?:\/\/\S+/.test(a.trim()),
      onNext: async () => {
        try {
          if (swHar && sw) { const ny = { name: c.trim(), url: a.trim(), user: '', password: b }; await api.setPlugin('subwave', { enabled: true, extra: [...(sw.extra ?? []), ny] }); }
          else await api.setPlugin('subwave', { enabled: true, url: a.trim(), ...(c.trim() ? { name: c.trim() } : {}), ...(b ? { password: b } : {}) });
        }
        catch (e) { setErr(e instanceof Error ? e.message : String(e)); throw e; }
        setTimeout(() => void startTest(runSw), 400);
      } },
    testing(runSw),
  ];
}

function Flow({ svc, onBack, onClose }: { svc: SvcId; onBack: () => void; onClose: () => void }) {
  const [i, setI] = useState(0), [busy, setBusy] = useState(false);
  const steps = useFlow(svc, onClose);
  const st = steps[Math.min(i, steps.length - 1)]!;
  const go = async () => {
    if (busy || st.can === false) return;
    setBusy(true);
    try { await st.onNext?.(); if (i < steps.length - 1 && !(st.onNext && i === steps.length - 1)) setI(i + 1); } catch { /* steget sa stopp */ }
    setBusy(false);
  };
  const last = i === steps.length - 1;
  return (
    <>
      <div class="swz-top">
        <button class="swz-back" onClick={() => (i ? setI(i - 1) : onBack())}><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg>{i ? 'Tilbake' : 'Tjenester'}</button>
        <div class="swz-dots" aria-hidden="true">{steps.map((_, k) => <i key={k} class={k === i ? 'on' : ''} />)}</div>
        <button class="swz-x" aria-label="Lukk" onClick={onClose}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
      </div>
      <div class="swz-body"><div class="swz-step" key={svc + i}>{st.body}</div></div>
      <div class="swz-foot">
        <button class="swz-btn" disabled={busy || st.can === false} onClick={() => void (last && !st.onNext ? onClose() : go())}>{st.next ?? 'Fortsett'}</button>
        {st.skip && <button class="swz-link" onClick={st.skip[1]}>{st.skip[0]}</button>}
      </div>
    </>
  );
}

function Overview({ pick, onClose }: { pick: (s: SvcId) => void; onClose: () => void }) {
  useEffect(() => { loadSw(); }, []);
  const n = SVCS.filter((s) => isOn(s.id)).length;
  return (
    <>
      <div class="swz-top"><span /><span /><button class="swz-x" aria-label="Lukk" onClick={onClose}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button></div>
      <div class="swz-body"><div class="swz-step">
        <div class="swz-ic" style="background:linear-gradient(145deg,#f0c46a,#b9832a);color:#0b0b0c"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l12-2v13" /><circle cx="6" cy="18" r="3" /><circle cx="18" cy="16" r="3" /></svg></div>
        <h2>Musikktjenester</h2>
        <p class="sub">{n ? t('{n} av {av} er satt opp. Velg en for å endre den.', { n, av: SVCS.length }) : 'Velg tjenestene du bruker. Det tar et minutt per tjeneste.'}</p>
        <div class="swz-list">
          {SVCS.map((s) => (
            <button key={s.id} class="swz-row" onClick={() => pick(s.id)}>
              <Icon s={s} />
              <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:2px"><span style="font-size:16px;font-weight:500">{s.name}</span><span style="font-size:13px;color:#8e8e93;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.what}</span></span>
              {isOn(s.id) ? <span class="swz-ok"><Check /></span> : <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#636366" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M9 5l7 7-7 7" /></svg>}
            </button>))}
        </div>
      </div></div>
      <div class="swz-foot"><button class="swz-btn" onClick={onClose}>{n ? 'Ferdig' : 'Senere'}</button></div>
    </>
  );
}

/** Legges én gang i roten av appen. */
export function SetupWizard() {
  const v = setupOpen.value;
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (v === null) return;
    const k = (e: KeyboardEvent) => { if (e.key === 'Escape') setupOpen.value = null; };
    // Siden bak skal stå stille mens oppsettet er åpent (hjul og sveip ruller bare innholdet i vinduet)
    const h = document.documentElement, b = document.body, ho = h.style.overflow, bo = b.style.overflow;
    h.style.overflow = 'hidden'; b.style.overflow = 'hidden';
    window.addEventListener('keydown', k);
    return () => { window.removeEventListener('keydown', k); h.style.overflow = ho; b.style.overflow = bo; };
  }, [v === null]);
  if (v === null) return null;
  const close = () => { setupOpen.value = null; };
  return (
    <div class="swz-bg" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <style>{css}</style>
      <div class="swz" ref={ref} role="dialog" aria-modal="true" aria-label="Oppsett av musikktjenester">
        {v ? <Flow key={v} svc={v} onBack={() => { setupOpen.value = ''; }} onClose={close} /> : <Overview pick={(s) => { setupOpen.value = s; }} onClose={close} />}
      </div>
    </div>
  );
}
