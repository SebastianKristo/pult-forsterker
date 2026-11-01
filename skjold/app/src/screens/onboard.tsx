// Oppsett (Skjold App v2, ob 0–4): finn enhet, Wi-Fi, rom og programvare.
import { useEffect, useRef, useState } from 'preact/hooks';
import type { ComponentChildren } from 'preact';
import { api, cmpVersion, fetchLatestRelease, normHost, probe, productOf, setBase, type Release } from '../lib/api';
import { loadSettings, mode, reconnect, setSetting, settings, status } from '../lib/store';
import { NAMES } from '../lib/settings';
import { PRODUCT_ICON } from '../components/ui';
import { remember, scan, type Found } from '../lib/discover';

const LABEL = (n: number) => 'OPPSETT · ' + n + ' AV 4';

function Shell({ step, back, title, text, children }: { step: number; back?: (() => void) | undefined; title: string; text: string; children: ComponentChildren }) {
  return (
    <div class="ob-shell">
      <div class="ob">
        <div class="row between" style={{ minHeight: '28px' }}>
          <span class="kicker">{LABEL(step + 1)}</span>
          {back && <button class="ob-back" onClick={back}>Tilbake</button>}
        </div>
        <div class="ob-dots">{[0, 1, 2, 3].map((i) => <i key={i} style={{ background: i <= step ? '#d9a441' : '#2a2a28' }} />)}</div>
        <h1>{title}</h1>
        <p>{text}</p>
        {children}
      </div>
    </div>
  );
}

const DEV_ICON_COLOR = ['#f2f2ee', '#c9c9c4'];

export function FindDevice() {
  const [found, setFound] = useState<Found[]>([]);
  const [scanning, setScanning] = useState(false);
  const [manualOpen, setManualOpen] = useState(false);
  const [manual, setManual] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState('');
  const [gen, setGen] = useState(0);
  const [qr, setQr] = useState(false);
  const [pulse, setPulse] = useState(true);
  useEffect(() => {
    setFound([]); setScanning(true); setErr('');
    const h = scan((f) => setFound((l) => [...l, f]), () => undefined);
    void h.done.finally(() => setScanning(false));
    return () => h.cancel();
  }, [gen]);
  useEffect(() => { const t = setInterval(() => setPulse((p) => !p), 900); return () => clearInterval(t); }, []);
  useEffect(() => { if (!scanning) { const t = setTimeout(() => setGen((g) => g + 1), 8000); return () => clearTimeout(t); } return undefined; }, [scanning]);
  const connect = async (b: string) => {
    setErr(''); setBusy(b);
    const st = await probe(b, 4000);
    setBusy('');
    if (!st) { setErr('Fikk ikke svar fra ' + b.replace(/^https?:\/\//, '') + '. Sjekk at telefonen er på samme Wi-Fi.'); return; }
    setBase(b); remember(b, st); status.value = st; reconnect(); await loadSettings();
    mode.value = settings.value.setupDone ? 'app' : 'setup';
  };
  if (qr) return <QrScan onBack={() => setQr(false)} onFound={(h) => { setQr(false); void connect(normHost(h)); }} onFail={() => { setQr(false); setManualOpen(true); setErr('QR-skanning støttes ikke på denne telefonen. Skriv inn adressen som står på skjermen.'); }} />;
  return (
    <Shell step={0} title="Legg til forsterker" text="Slå på forsterkeren. Den dukker opp her.">
      {found.map((f, i) => {
        const p = productOf(f.st);
        const host = f.base.replace(/^https?:\/\//, '').replace(/:8765$/, '');
        return (
          <button key={f.base} class={'ob-dev' + (i === 0 ? ' first' : '')} onClick={() => void connect(f.base)} disabled={!!busy}>
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke={DEV_ICON_COLOR[i === 0 ? 0 : 1]} stroke-width="1.1" stroke-linecap="round" stroke-linejoin="round" style={{ flexShrink: 0 }}><path d={PRODUCT_ICON[p]} /></svg>
            <div class="col" style={{ gap: '2px', flex: 1, minWidth: 0 }}><span style={{ fontSize: '14px' }}>{f.st.name}</span><span class="mono" style={{ fontSize: '10px', color: '#8b8b86' }}>{host} · v{f.st.version}</span></div>
            <span class="go">{busy === f.base ? 'Kobler til …' : 'Sett opp'}</span>
          </button>
        );
      })}
      <div class="ob-pulse"><i style={{ background: pulse ? '#d9a441' : '#3a3a37' }} />{found.length ? 'Leter etter flere …' : 'Leter …'}</div>
      {err && <span style={{ fontSize: '12px', color: '#ff8a7a', lineHeight: 1.45 }}>{err}</span>}
      <div class="col" style={{ gap: '10px', marginTop: 'auto' }}>
        {manualOpen ? (
          <form class="col" style={{ gap: '10px' }} onSubmit={(e) => { e.preventDefault(); if (manual.trim()) void connect(normHost(manual)); }}>
            <input class="ob-field" inputMode="url" autoCapitalize="off" autoCorrect="off" placeholder="192.168.1.50" value={manual} onInput={(e) => setManual(e.currentTarget.value)} data-testid="host" />
            <button class="ob-next" type="submit" style={manual.trim() && !busy ? { background: '#d9a441', color: '#0b0b0c' } : { background: '#242426', color: '#8b8b86' }}>Koble til</button>
          </form>
        ) : <button class="ob-link" onClick={() => setManualOpen(true)}>Skriv inn adresse manuelt</button>}
        <button class="ob-qr" onClick={() => setQr(true)}>Skann QR-kode på skjermen</button>
      </div>
    </Shell>
  );
}

interface BarcodeDetectorLike { detect(src: CanvasImageSource): Promise<{ rawValue: string }[]> }
function QrScan({ onBack, onFound, onFail }: { onBack: () => void; onFound: (host: string) => void; onFail: () => void }) {
  const video = useRef<HTMLVideoElement>(null);
  const [y, setY] = useState(12);
  useEffect(() => {
    const BD = (window as unknown as { BarcodeDetector?: new (o: { formats: string[] }) => BarcodeDetectorLike }).BarcodeDetector;
    if (!BD || !navigator.mediaDevices?.getUserMedia) { onFail(); return; }
    let stream: MediaStream | null = null, stop = false;
    const det = new BD({ formats: ['qr_code'] });
    void (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
        if (!video.current) return;
        video.current.srcObject = stream; await video.current.play();
        while (!stop) {
          const r = await det.detect(video.current).catch(() => []);
          const v = r[0]?.rawValue;
          const m = v && (v.match(/https?:\/\/[^\s]+/) || v.match(/\b\d{1,3}(\.\d{1,3}){3}(:\d+)?\b/) || v.match(/\b[\w-]+\.local(:\d+)?\b/));
          if (m) { onFound(m[0]); return; }
          await new Promise((res) => setTimeout(res, 250));
        }
      } catch { if (!stop) onFail(); }
    })();
    const t = setInterval(() => setY((x) => (x >= 172 ? 12 : x + 4)), 40);
    return () => { stop = true; clearInterval(t); stream?.getTracks().forEach((tr) => tr.stop()); };
  }, []);
  return (
    <Shell step={0} back={onBack} title="Skann QR-koden" text="Hold kameraet mot skjermen på forsterkeren.">
      <div class="ob-scan">
        <div class="frame">
          <video ref={video} muted playsInline />
          <i class="c tl" /><i class="c tr" /><i class="c bl" /><i class="c br" />
          <div class="line" style={{ top: y + 'px' }} />
        </div>
        <span style={{ fontSize: '13px', color: '#c9c9c4' }}>Leter etter QR-kode …</span>
      </div>
    </Shell>
  );
}

const RLIST = ['Stue', 'Kjøkken', 'Soverom', 'Kontor', 'Barnerom', 'Bad', 'Gang', 'Verksted'];

export function Setup() {
  const [ob, setOb] = useState(1);
  const st = settings.value, s = status.value;
  const curName = st.nameCustom || (st.name > 0 ? NAMES[st.name] ?? '' : '');
  const [room, setRoom] = useState(curName && RLIST.includes(curName) ? curName : curName ? '' : 'Stue');
  const [custom, setCustom] = useState(!!curName && !RLIST.includes(curName));
  const [customName, setCustomName] = useState(curName && !RLIST.includes(curName) ? curName : '');
  const [nets, setNets] = useState<{ ssid: string; security?: string }[] | null | undefined>(undefined);
  const [net, setNet] = useState<number | 'man'>(0);
  const [ssid, setSsid] = useState(''); const [pw, setPw] = useState(''); const [sec, setSec] = useState(0);
  const [wifiErr, setWifiErr] = useState(''); const [wifiBusy, setWifiBusy] = useState(false);
  const [rel, setRel] = useState<Release | null | undefined>(undefined);
  useEffect(() => { api.wifiScan().then((r) => setNets(r.networks ?? [])).catch(() => setNets(null)); }, []);
  useEffect(() => { if (ob === 4 && rel === undefined) fetchLatestRelease(st.updChannel === 1).then(setRel).catch(() => setRel(null)); }, [ob]);
  const finish = () => { setSetting('setupDone', true); mode.value = 'app'; };
  const back = ob > 1 ? () => setOb(ob === 4 ? 2 : ob - 1) : () => { mode.value = 'find'; };
  const sel = (on: boolean) => ({ borderColor: on ? '#d9a441' : '#2e2e30', background: on ? '#1c170d' : '#141415', color: on ? '#f0c46a' : '#f2f2ee' });
  const next = (ok: boolean, label: string, fn: () => void) => (
    <button class="ob-next" style={{ marginTop: 'auto', background: ok ? '#d9a441' : '#242426', color: ok ? '#0b0b0c' : '#8b8b86' }} onClick={() => { if (ok) fn(); }}>{label}</button>
  );
  if (ob === 1) {
    if (nets === null || (nets && !nets.length)) {
      return (
        <Shell step={1} back={back} title="Koble til Wi-Fi" text={(s?.name ?? 'Skjold') + ' er allerede på nettet og svarer. Wi-Fi kan også settes i Skjold Flasher når SD-kortet skrives.'}>
          <div class="ob-list"><div class="ob-net on"><span>Tilkoblet</span><span class="mk">✓</span></div></div>
          {next(true, 'Neste', () => setOb(2))}
        </Shell>
      );
    }
    const netMan = net === 'man', needPw = !netMan ? (nets?.[net as number]?.security ?? 'wpa') !== 'open' : sec < 2;
    const ok = (!netMan || ssid.trim().length > 0) && (!needPw || pw.length >= 8) && !wifiBusy;
    return (
      <Shell step={1} back={back} title="Koble til Wi-Fi" text="Velg nettverket forsterkeren skal bruke.">
        <div class="ob-list">
          {(nets ?? []).map((n, i) => <button key={n.ssid} class={'ob-net' + (net === i ? ' on' : '')} style={{ borderTopColor: i ? '#242426' : 'transparent' }} onClick={() => setNet(i)}><span>{n.ssid}</span><span class="mk">{net === i ? '✓' : ''}</span></button>)}
          {nets && <button class={'ob-net' + (netMan ? ' on' : '')} style={{ color: '#c9c9c4' }} onClick={() => setNet('man')}><span>Annet nettverk …</span><span class="mk">{netMan ? '✓' : ''}</span></button>}
        </div>
        {netMan && <>
          <span style={{ fontSize: '12px', color: '#8b8b86', lineHeight: 1.45 }}>Skriv inn navnet hvis nettverket er skjult eller ikke dukker opp. Forsterkeren støtter 2,4 GHz.</span>
          <input class="ob-field" value={ssid} placeholder="Nettverksnavn (SSID)" autoCapitalize="off" autoCorrect="off" spellcheck={false} onInput={(e) => setSsid(e.currentTarget.value)} />
          <div class="row" style={{ gap: '6px' }}>{['WPA2', 'WPA3', 'Ingen'].map((l, i) => <button key={l} class="ob-sec" style={sel(sec === i)} onClick={() => setSec(i)}>{l}</button>)}</div>
        </>}
        {needPw && <input class="ob-field" type="password" value={pw} placeholder="Passord" onInput={(e) => setPw(e.currentTarget.value)} />}
        {wifiErr && <span style={{ fontSize: '12px', color: '#ff8a7a' }}>{wifiErr}</span>}
        {next(ok, wifiBusy ? 'Kobler til …' : 'Koble til', async () => {
          setWifiBusy(true); setWifiErr('');
          try { await api.wifiConnect(netMan ? ssid.trim() : nets?.[net as number]?.ssid ?? '', needPw ? pw : ''); setOb(2); }
          catch { setWifiErr('Fikk ikke koblet til nettverket. Sjekk passordet.'); }
          finally { setWifiBusy(false); }
        })}
      </Shell>
    );
  }
  if (ob === 2) {
    const name = custom ? customName.trim() : room;
    return (
      <Shell step={2} back={back} title="Hvor står den?" text="Navnet vises i AirPlay, Blåtann og Lyrion.">
        <div class="ob-rooms">{RLIST.map((r) => { const on = !custom && room === r; return <button key={r} style={sel(on)} onClick={() => { setRoom(r); setCustom(false); }}><span class="ellip">{r}</span><span class="mk">{on ? '✓' : ''}</span></button>; })}</div>
        <button class="ob-custom" style={{ borderColor: custom ? '#d9a441' : '#3a3a37', background: custom ? '#1c170d' : 'transparent', color: custom ? '#f0c46a' : '#c9c9c4' }} onClick={() => setCustom(true)}>
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>Skriv eget navn
        </button>
        {custom && <>
          <input class="ob-field" style={{ borderColor: '#d9a441' }} value={customName} maxLength={20} placeholder="For eksempel Hytta eller Runes rom" onInput={(e) => setCustomName(e.currentTarget.value.slice(0, 20))} />
          <span style={{ fontSize: '12px', color: '#8b8b86' }}>Maks 20 tegn. Kan endres senere under Innstillinger.</span>
        </>}
        {next(name.length > 0, 'Neste', () => {
          const i = NAMES.indexOf(name);
          if (i > 0) { setSetting('name', i); setSetting('nameCustom', ''); } else setSetting('nameCustom', name);
          setOb(4);
        })}
      </Shell>
    );
  }
  const cur = s?.version ?? '';
  const newer = rel && cur ? cmpVersion(rel.tag.replace(/^skjold-/, ''), cur) > 0 : false;
  const label = rel === undefined ? 'Ser etter oppdatering …' : newer && rel ? cur + ' → ' + rel.tag.replace(/^v/, '') + ' · installeres under Innstillinger → Oppdatering' : (cur || '–') + ' installert';
  return (
    <Shell step={3} back={back} title="Programvare" text={rel === undefined ? 'Ser etter siste versjon.' : newer ? 'En nyere versjon er tilgjengelig.' : 'Forsterkeren har siste versjon.'}>
      <div class="col" style={{ gap: '12px' }}>
        <div class="ob-bar"><i style={{ width: rel === undefined ? '30%' : '100%' }} /></div>
        <span class="mono" style={{ fontSize: '12px', color: '#8b8b86' }}>{label}</span>
      </div>
      {next(rel !== undefined, rel === undefined ? 'Ser etter …' : 'Ferdig', finish)}
    </Shell>
  );
}
