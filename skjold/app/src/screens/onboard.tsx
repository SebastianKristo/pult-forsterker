// Oppsett (Skjold App v2, ob 0–4): finn enhet / QR, Wi-Fi, rom, høyttalertest og programvare.
// Malen er portert 1:1 fra designfilen (inline-stiler med samme mål, farger og tekster).
import { useEffect, useRef, useState } from 'preact/hooks';
import type { ComponentChildren } from 'preact';
import { signal } from '@preact/signals';
import { api, cmpVersion, fetchLatestRelease, normHost, probe, productOf, setBase, type Release } from '../lib/api';
import { loadSettings, mode, reconnect, setSetting, settings, status } from '../lib/store';
import { NAMES } from '../lib/settings';
import { PRODUCT_ICON } from '../components/ui';
import { remember, scan, type Found } from '../lib/discover';

const A = '#d9a441';
const sel = (b: boolean) => ({ bd: b ? A : '#2e2e30', bg: b ? '#1c170d' : '#141415', fg: b ? '#f0c46a' : '#f2f2ee' });
const RLIST = ['Stue', 'Kjøkken', 'Soverom', 'Kontor', 'Barnerom', 'Bad', 'Gang', 'Verksted'];
const OB: [string, string][] = [['Legg til forsterker', 'Slå på forsterkeren. Den dukker opp her.'], ['Koble til Wi-Fi', 'Sendes kryptert over Blåtann. Godta på forsterkeren med volumknappen.'], ['Hvor står den?', 'Navnet vises i AirPlay, Blåtann og Lyrion.'], ['Test høyttalerne', 'Trykk på en side og hør etter.'], ['Programvare', 'Installerer siste versjon.']];

/** Tilstand for oppsettet (signaler, så tilbake-knappen og skjermbildeskriptet kan styre den). */
export const ob = {
  step: signal(1), qr: signal(false), net: signal<number | 'man'>(0), ssid: signal(''), sec: signal(0), pw: signal(''),
  room: signal('Stue'), custom: signal(false), tested: signal<Record<string, 'ok' | 'bad'>>({}), upd: signal(0)
};
export function obBack(): boolean {
  if (mode.value === 'find') { if (ob.qr.value) { ob.qr.value = false; return true; } return false; }
  if (mode.value === 'setup') { const s = ob.step.value; if (s <= 1) mode.value = 'find'; else ob.step.value = s - 1; return true; }
  return false;
}

function Shell({ step, back, title, text, children }: { step: number; back?: (() => void) | undefined; title: string; text: string; children: ComponentChildren }) {
  return (
    <div class="dshell">
      <div class="dsc" style="flex:1;display:flex;flex-direction:column;padding:8px 20px 18px;gap:16px;min-height:0;overflow:auto;scrollbar-width:none;color-scheme:dark">
        <div style="display:flex;align-items:center;justify-content:space-between;min-height:28px">
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;color:#8b8b86">OPPSETT · {Math.min(step, 3) + 1} AV 4</span>
          {back && <button onClick={back} style="border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:6px 0">Tilbake</button>}
        </div>
        <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:4px">
          {[0, 1, 2, 3].map((i) => <div key={i} style={`height:3px;border-radius:2px;background:${i <= Math.min(step, 3) ? A : '#2a2a28'}`} />)}
        </div>
        <h1 style="margin:0;font-size:28px;font-weight:600;line-height:1.15;text-align:left">{title}</h1>
        <p style="margin:0;font-size:13px;color:#a9a9a3;line-height:1.5;text-align:left">{text}</p>
        {children}
      </div>
    </div>
  );
}

function NextBtn({ ok, label, onClick }: { ok: boolean; label: string; onClick: () => void }) {
  return <button onClick={() => { if (ok) onClick(); }} data-testid="ob-next" style={`margin-top:auto;height:52px;flex-shrink:0;border-radius:14px;border:none;background:${ok ? A : '#242426'};color:${ok ? '#0b0b0c' : '#8b8b86'};font-size:15px;font-weight:600;cursor:pointer`}>{label}</button>;
}

export function FindDevice() {
  const [found, setFound] = useState<Found[]>([]);
  const [scanning, setScanning] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState('');
  const [gen, setGen] = useState(0);
  const [pulse, setPulse] = useState(true);
  useEffect(() => {
    setFound([]); setScanning(true); setErr('');
    const h = scan((f) => setFound((l) => [...l, f]), () => undefined);
    void h.done.finally(() => setScanning(false));
    return () => h.cancel();
  }, [gen]);
  useEffect(() => { const t = setInterval(() => setPulse((p) => !p), 420); return () => clearInterval(t); }, []);
  useEffect(() => { if (!scanning) { const t = setTimeout(() => setGen((g) => g + 1), 8000); return () => clearTimeout(t); } return undefined; }, [scanning]);
  const connect = async (b: string) => {
    setErr(''); setBusy(b);
    const st = await probe(b, 4000);
    setBusy('');
    if (!st) { setErr('Fikk ikke svar fra ' + b.replace(/^https?:\/\//, '') + '. Sjekk at telefonen er på samme Wi-Fi.'); return; }
    setBase(b); remember(b, st); status.value = st; reconnect(); await loadSettings();
    if (settings.value.setupDone) mode.value = 'app'; else { ob.step.value = 1; mode.value = 'setup'; }
  };
  if (ob.qr.value) return <QrScan onBack={() => { ob.qr.value = false; }} onFound={(h) => { ob.qr.value = false; void connect(normHost(h)); }} onFail={() => { ob.qr.value = false; setManualOpen(true); setErr('QR-skanning støttes ikke på denne telefonen. Skriv inn adressen som står på skjermen.'); }} />;
  return (
    <Shell step={0} title={OB[0]![0]} text={OB[0]![1]}>
      {found.map((f, i) => {
        const p = productOf(f.st), first = i === 0;
        const host = f.base.replace(/^https?:\/\//, '').replace(/:8765$/, '');
        return (
          <button key={f.base} onClick={() => void connect(f.base)} disabled={!!busy} style={`display:flex;align-items:center;gap:12px;padding:14px;border-radius:14px;background:${first ? '#1c170d' : '#141415'};border:1px solid ${first ? A : '#2e2e30'};cursor:pointer;text-align:left;flex-shrink:0`}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={first ? '#f2f2ee' : '#c9c9c4'} stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d={PRODUCT_ICON[p]} /></svg>
            <div style="display:flex;flex-direction:column;gap:2px;flex:1;min-width:0"><span style="font-size:14px">{f.st.name}</span><span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#8b8b86;overflow-wrap:anywhere">{host} · v{f.st.version}</span></div>
            <span style="font-size:12px;color:#f0c46a;white-space:nowrap;flex-shrink:0">{busy === f.base ? 'Kobler til …' : 'Sett opp'}</span>
          </button>
        );
      })}
      <div style="display:flex;align-items:center;gap:8px;font-size:12px;color:#8b8b86;padding:4px 2px"><div style={`width:8px;height:8px;border-radius:50%;background:${pulse ? A : '#3a3a37'}`} />Leter etter flere …</div>
      {err && <span style="font-size:12px;color:#ff8a7a;line-height:1.45">{err}</span>}
      <div style="display:flex;flex-direction:column;gap:12px;margin-top:auto">
        {manualOpen ? (
          <form style="display:flex;flex-direction:column;gap:10px" onSubmit={(e) => { e.preventDefault(); if (manual.trim()) void connect(normHost(manual)); }}>
            <input inputMode="url" autoCapitalize="off" autoCorrect="off" spellcheck={false} placeholder="192.168.1.50" value={manual} onInput={(e) => setManual(e.currentTarget.value)} data-testid="host" style="height:48px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:#141415;font-size:16px;outline:none" />
            <button type="submit" style={`height:52px;border-radius:14px;border:none;background:${manual.trim() && !busy ? A : '#242426'};color:${manual.trim() && !busy ? '#0b0b0c' : '#8b8b86'};font-size:15px;font-weight:600;cursor:pointer`}>Koble til</button>
          </form>
        ) : <button onClick={() => setManualOpen(true)} style="align-self:center;border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:4px 0">Skriv inn adresse manuelt</button>}
        <button onClick={() => { ob.qr.value = true; }} style="height:50px;border-radius:14px;border:1px solid #2e2e30;background:transparent;font-size:14px;cursor:pointer">Skann QR-kode på skjermen</button>
      </div>
    </Shell>
  );
}

interface BarcodeDetectorLike { detect(src: CanvasImageSource): Promise<{ rawValue: string }[]> }
function QrScan({ onBack, onFound, onFail }: { onBack: () => void; onFound: (host: string) => void; onFail: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [t, setT] = useState(0);
  const [cam, setCam] = useState(false);
  useEffect(() => {
    const iv = setInterval(() => setT((x) => x + 1), 140);
    const BD = (window as unknown as { BarcodeDetector?: new (o: { formats: string[] }) => BarcodeDetectorLike }).BarcodeDetector;
    let stream: MediaStream | null = null, stop = false;
    if (!BD || !navigator.mediaDevices?.getUserMedia) { const f = setTimeout(onFail, 2500); return () => { clearInterval(iv); clearTimeout(f); }; }
    const det = new BD({ formats: ['qr_code'] });
    void (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        if (!video.current) return;
        video.current.srcObject = stream; await video.current.play(); setCam(true);
        while (!stop) {
          const r = await det.detect(video.current).catch(() => []);
          const v = r[0]?.rawValue;
          const m = v && (v.match(/https?:\/\/[^\s]+/) || v.match(/\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b/) || v.match(/\b[\w-]+\.local(:\d+)?\b/));
          if (m) { onFound(m[0]); return; }
          await new Promise((res) => setTimeout(res, 250));
        }
      } catch { if (!stop) onFail(); }
    })();
    return () => { stop = true; clearInterval(iv); stream?.getTracks().forEach((tr) => tr.stop()); };
  }, []);
  const y = 12 + (Math.sin(t * 0.35) * 0.5 + 0.5) * 160;
  const corner = (pos: string, bd: string, r: string) => <div style={`position:absolute;${pos};width:34px;height:34px;${bd};border-radius:${r}`} />;
  return (
    <Shell step={0} back={onBack} title="Skann QR-koden" text="Hold kameraet mot skjermen på forsterkeren.">
      <div style="flex:1;min-height:260px;border-radius:14px;background:#151517;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:16px;position:relative;overflow:hidden">
        <video ref={video} muted playsInline style={`position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:${cam ? 0.55 : 0}`} />
        <div style="width:190px;height:190px;position:relative">
          {corner('left:0;top:0', 'border-left:3px solid #d9a441;border-top:3px solid #d9a441', '14px 0 0 0')}
          {corner('right:0;top:0', 'border-right:3px solid #d9a441;border-top:3px solid #d9a441', '0 14px 0 0')}
          {corner('left:0;bottom:0', 'border-left:3px solid #d9a441;border-bottom:3px solid #d9a441', '0 0 0 14px')}
          {corner('right:0;bottom:0', 'border-right:3px solid #d9a441;border-bottom:3px solid #d9a441', '0 0 14px 0')}
          <div style={`position:absolute;left:12px;right:12px;top:${y}px;height:2px;background:#d9a441;box-shadow:0 0 12px #d9a441`} />
        </div>
        <span style="font-size:13px;color:#c9c9c4;position:relative">Leter etter QR-kode …</span>
      </div>
    </Shell>
  );
}

interface Net { ssid: string; security?: string; signal?: number; active?: boolean }
const Bars = ({ sig }: { sig: number }) => (
  <svg width="16" height="12" viewBox="0 0 16 12" aria-label={'Signal ' + sig + ' %'}>{[0, 1, 2, 3].map((i) => <rect key={i} x={i * 4} y={9 - i * 3} width="3" height={3 + i * 3} rx="0.8" fill={sig >= 15 + i * 22 ? '#c9c9c4' : '#3a3a37'} />)}</svg>
);
const Lock = () => <svg width="11" height="12" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-label="Passord"><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V7a4 4 0 0 1 8 0v4" /></svg>;

function Wifi({ back }: { back: () => void }) {
  const s = status.value;
  const [nets, setNets] = useState<Net[] | null | undefined>(undefined);
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  useEffect(() => { api.wifiScan().then((r) => setNets(r.networks ?? [])).catch(() => setNets(null)); }, []);
  const net = ob.net.value, netMan = net === 'man', sec = ob.sec.value;
  const picked = typeof net === 'number' ? nets?.[net] : undefined;
  const needPw = netMan ? sec < 2 : (picked?.security ?? 'wpa2') !== 'open';
  const ok = (!netMan || ob.ssid.value.trim().length > 0) && (!needPw || ob.pw.value.length >= 8) && !busy && (netMan || !!picked);
  const fld = 'height:48px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:#141415;font-size:16px;outline:none;flex-shrink:0';
  const row = (on: boolean, i: number) => `display:flex;justify-content:space-between;align-items:center;gap:10px;min-height:50px;padding:0 14px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:${on ? '#1c170d' : 'transparent'};cursor:pointer;font-size:14px;text-align:left`;
  // Forsterkeren er allerede på nett (vi snakker med den) og har ikke Wi-Fi-API: si det, og la brukeren gå videre.
  if (nets === null) {
    return (
      <Shell step={1} back={back} title={OB[1]![0]} text={(s?.name ?? 'Skjold') + ' er allerede på nettet og svarer. Wi-Fi kan også settes i Skjold Flasher når minnekortet skrives.'}>
        <div style="display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;flex-shrink:0"><div style={row(true, 0)}><span>Tilkoblet</span><span style="font-size:12px;color:#f0c46a">✓</span></div></div>
        <NextBtn ok label="Neste" onClick={() => { ob.step.value = 2; }} />
      </Shell>
    );
  }
  return (
    <Shell step={1} back={back} title={OB[1]![0]} text="Velg nettverket forsterkeren skal bruke. Passordet sendes bare til forsterkeren.">
      <div style="display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;flex-shrink:0;overflow:hidden" data-testid="nets">
        {nets === undefined && <div style={row(false, 0) + ';color:#8b8b86'}>Leter etter nettverk …</div>}
        {(nets ?? []).map((n, i) => (
          <button key={n.ssid} onClick={() => { ob.net.value = i; }} style={row(net === i, i)}>
            <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0">{n.ssid}</span>
            <span style="display:flex;align-items:center;gap:8px;flex-shrink:0">{n.security !== 'open' && <Lock />}<Bars sig={n.signal ?? 0} /><span style="font-size:12px;color:#f0c46a;min-width:9px">{net === i ? '✓' : ''}</span></span>
          </button>
        ))}
        <button onClick={() => { ob.net.value = 'man'; }} style={row(netMan, 1) + ';color:#c9c9c4'}><span>Annet nettverk …</span><span style="font-size:12px;color:#f0c46a">{netMan ? '✓' : ''}</span></button>
      </div>
      {netMan && <>
        <span style="font-size:12px;color:#8b8b86;line-height:1.45;text-wrap:pretty">Skriv inn navnet hvis nettverket er skjult eller ikke dukker opp. Forsterkeren støtter 2,4 GHz.</span>
        <input value={ob.ssid.value} onInput={(e) => { ob.ssid.value = e.currentTarget.value; }} placeholder="Nettverksnavn (SSID)" autoCapitalize="off" autoCorrect="off" spellcheck={false} style={fld} />
        <div style="display:flex;gap:6px;flex-shrink:0">
          {['WPA2', 'WPA3', 'Ingen'].map((l, i) => { const c = sel(sec === i); return <button key={l} onClick={() => { ob.sec.value = i; }} style={`flex:1;height:38px;border-radius:999px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:13px;cursor:pointer;white-space:nowrap`}>{l}</button>; })}
        </div>
      </>}
      {needPw && <input type="password" value={ob.pw.value} onInput={(e) => { ob.pw.value = e.currentTarget.value; }} placeholder="Passord" style={fld} />}
      {err && <span style="font-size:12px;color:#ff8a7a;line-height:1.45">{err}</span>}
      <NextBtn ok={ok} label={busy ? 'Kobler til …' : 'Koble til'} onClick={async () => {
        setBusy(true); setErr('');
        try {
          await api.wifiConnect(netMan ? ob.ssid.value.trim() : picked?.ssid ?? '', needPw ? ob.pw.value : '', netMan);
          ob.step.value = 2;
        } catch (e) { setErr('Fikk ikke koblet til nettverket' + (e instanceof Error && e.message ? ': ' + e.message : '') + '. Sjekk passordet.'); }
        finally { setBusy(false); }
      }} />
    </Shell>
  );
}

function Room({ back }: { back: () => void }) {
  const custom = ob.custom.value, room = ob.room.value;
  const name = room.trim();
  return (
    <Shell step={2} back={back} title={OB[2]![0]} text={OB[2]![1]}>
      <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;flex-shrink:0">
        {RLIST.map((r) => { const on = !custom && room === r, c = sel(on); return (
          <button key={r} onClick={() => { ob.room.value = r; ob.custom.value = false; }} style={`display:flex;align-items:center;justify-content:space-between;gap:8px;height:50px;padding:0 14px;border-radius:12px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:14px;cursor:pointer;text-align:left`}><span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{r}</span><span style="font-size:12px;color:#f0c46a">{on ? '✓' : ''}</span></button>
        ); })}
      </div>
      <button onClick={() => { if (!custom) { ob.custom.value = true; ob.room.value = RLIST.includes(room) ? '' : room; } }} style={`display:flex;align-items:center;gap:10px;height:50px;flex-shrink:0;padding:0 14px;border-radius:12px;border:1px dashed ${custom ? A : '#3a3a37'};background:${custom ? '#1c170d' : 'transparent'};color:${custom ? '#f0c46a' : '#c9c9c4'};font-size:14px;cursor:pointer;text-align:left`}>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>Skriv eget navn
      </button>
      {custom && <>
        <input value={room} onInput={(e) => { ob.room.value = e.currentTarget.value.slice(0, 20); }} placeholder="For eksempel Hytta eller Runes rom" maxLength={20} style="height:48px;flex-shrink:0;padding:0 14px;border-radius:12px;border:1px solid #d9a441;background:#141415;font-size:16px;outline:none" />
        <span style="font-size:12px;color:#8b8b86">Maks 20 tegn. Kan endres senere under Innstillinger.</span>
      </>}
      <NextBtn ok={name.length > 0} label="Neste" onClick={() => {
        const i = NAMES.indexOf(name);
        if (i > 0) { setSetting('name', i); setSetting('nameCustom', ''); } else setSetting('nameCustom', name);
        ob.step.value = 3;
      }} />
    </Shell>
  );
}

function Test({ back }: { back: () => void }) {
  const t = ob.tested.value;
  const ok = !!t['L'] && !!t['R'];
  return (
    <Shell step={3} back={back} title={OB[3]![0]} text={OB[3]![1]}>
      <button onClick={() => { ob.step.value = 4; }} style="align-self:flex-start;border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:0">Hopp over høyttalertest</button>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;flex-shrink:0">
        {([['L', 'Venstre'], ['R', 'Høyre']] as const).map(([k, label]) => {
          const r = t[k], c = sel(r === 'ok');
          return (
            <button key={k} data-testid={'test-' + k} onClick={async () => {
              try { await api.speakerTest(k); ob.tested.value = { ...ob.tested.value, [k]: 'ok' }; }
              catch { ob.tested.value = { ...ob.tested.value, [k]: 'bad' }; }
            }} style={`height:150px;border-radius:14px;border:1px solid ${r === 'bad' ? '#5a2620' : c.bd};background:${c.bg};cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px`}>
              <span style="font-size:42px;font-weight:300;line-height:1">{k}</span><span style={`font-size:12px;color:${r === 'bad' ? '#ff8a7a' : c.fg}`}>{r === 'ok' ? 'Spilt av' : r === 'bad' ? 'Fikk ikke spilt' : label}</span>
            </button>
          );
        })}
      </div>
      {Object.values(t).includes('bad') && <span style="font-size:12px;color:#8b8b86;line-height:1.45">Forsterkeren kunne ikke spille testtonen. Hopp over og prøv igjen under Innstillinger → Lyd.</span>}
      <NextBtn ok={ok} label="Neste" onClick={() => { ob.step.value = 4; }} />
    </Shell>
  );
}

function Software({ back }: { back: () => void }) {
  const st = settings.value, s = status.value;
  const [rel, setRel] = useState<Release | null | undefined>(undefined);
  useEffect(() => {
    ob.upd.value = 0;
    const iv = setInterval(() => { if (ob.upd.value < 90) ob.upd.value = ob.upd.value + 5; }, 110);
    fetchLatestRelease(st.updChannel === 1).then(setRel).catch(() => setRel(null)).finally(() => { clearInterval(iv); ob.upd.value = 100; });
    return () => clearInterval(iv);
  }, []);
  const cur = s?.version ?? '';
  const nv = rel ? rel.tag.replace(/^(skjold-)?v?/, '') : '';
  const newer = !!rel && !!cur && cmpVersion(nv, cur) > 0;
  const done = ob.upd.value >= 100;
  const label = !done ? (cur || '–') + ' · ser etter oppdatering · ' + ob.upd.value + ' %' : newer ? cur + ' → ' + nv + ' · installeres under Innstillinger → Oppdatering' : (cur || '–') + ' installert';
  return (
    <Shell step={4} back={back} title={OB[4]![0]} text={!done ? 'Ser etter siste versjon.' : newer ? 'En nyere versjon er klar.' : rel === null ? 'Fikk ikke sjekket GitHub. Forsterkeren kjører versjonen under.' : 'Forsterkeren har siste versjon.'}>
      <div style="display:flex;flex-direction:column;gap:12px">
        <div style="height:6px;border-radius:3px;background:#242426;overflow:hidden"><div style={`height:100%;width:${ob.upd.value}%;background:#d9a441`} /></div>
        <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#8b8b86">{label}</span>
      </div>
      <NextBtn ok={done} label={done ? 'Ferdig' : 'Oppdaterer …'} onClick={() => { setSetting('setupDone', true); mode.value = 'app'; }} />
    </Shell>
  );
}

export function Setup() {
  const step = ob.step.value;
  const back = () => { obBack(); };
  useEffect(() => {
    // romnavn fra innstillingene som utgangspunkt
    const st = settings.value, cur = st.nameCustom || (st.name > 0 ? NAMES[st.name] ?? '' : '');
    if (cur && ob.room.value === 'Stue' && !ob.custom.value) { ob.room.value = cur; ob.custom.value = !RLIST.includes(cur); }
  }, []);
  if (step <= 1) return <Wifi back={back} />;
  if (step === 2) return <Room back={back} />;
  if (step === 3) return <Test back={back} />;
  return <Software back={back} />;
}
