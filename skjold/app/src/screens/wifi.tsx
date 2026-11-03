// Innstillinger → Tilkobling → Wi-Fi: bytt nettverk senere (samme valg som Wi-Fi-trinnet i oppsettet).
import { useEffect, useState } from 'preact/hooks';
import { api, getBase, isNative, setBase } from '../lib/api';
import { status } from '../lib/store';
import { Bars, Lock } from './onboard';

type Net = { ssid: string; security?: string; signal?: number; active?: boolean };
const A = '#d9a441';
const CARD = 'display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;flex-shrink:0;overflow:hidden';
const SEC = ['wpa2', 'wpa3', 'open'] as const;

export function WifiPanel({ wide }: { wide: boolean }) {
  const [open, setOpen] = useState(false);
  const [nets, setNets] = useState<Net[] | null | undefined>(undefined);
  const [err, setErr] = useState('');
  const [pick, setPick] = useState<number | 'man' | null>(null);
  const [ssid, setSsid] = useState(''); const [sec, setSec] = useState(0); const [pw, setPw] = useState('');
  const [phase, setPhase] = useState<'' | 'connecting' | 'waiting' | 'done' | 'lost'>('');
  const [alt, setAlt] = useState('');

  const scan = () => {
    setNets(undefined); setErr('');
    api.wifiScan().then((r) => setNets(r.networks ?? [])).catch((e: unknown) => { setNets(null); setErr(e instanceof Error ? e.message : String(e)); });
  };
  useEffect(scan, []);
  const active = nets?.find((n) => n.active)?.ssid;

  const man = pick === 'man';
  const picked = typeof pick === 'number' ? nets?.[pick] : undefined;
  const needPw = man ? sec < 2 : !!picked && (picked.security ?? 'wpa2') !== 'open';
  const ok = phase !== 'connecting' && phase !== 'waiting' && (man ? ssid.trim().length > 0 : !!picked) && (!needPw || pw.length >= 8);

  /** Etter bytte: vent til enheten svarer igjen (samme adresse, ellers <navn>.local) i inntil 60 s. */
  const waitBack = async () => {
    setPhase('waiting');
    const local = status.value?.id ? `http://${status.value.id}.local:8765` : '';
    const t0 = Date.now();
    while (Date.now() - t0 < 60000) {
      await new Promise((r) => setTimeout(r, 3000));
      try { await api.status(); setPhase('done'); scan(); return; } catch { /* ikke tilbake ennå */ }
      if (local && local !== getBase()) {
        try {
          const r = await fetch(local + '/api/status', { cache: 'no-store' });
          if (r.ok) { if (isNative) { setBase(local); setPhase('done'); scan(); } else { setAlt(local); setPhase('lost'); } return; }
        } catch { /* prøv igjen */ }
      }
    }
    setAlt(local); setPhase('lost');
  };

  const connect = async () => {
    setErr(''); setAlt(''); setPhase('connecting');
    const name = man ? ssid.trim() : picked?.ssid ?? '';
    try {
      await api.wifiConnect(name, needPw ? pw : '', man, man ? SEC[sec] : undefined);
      setPw(''); await waitBack();
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // Tidsavbrudd = enheten byttet nett midt i svaret: vent på at den kommer tilbake
      if (/Tidsavbrudd|Failed to fetch|NetworkError|Load failed/i.test(msg)) { await waitBack(); return; }
      setPhase(''); setErr('Fikk ikke koblet til «' + name + '»: ' + msg);
    }
  };

  const row = (on: boolean, i: number) => `display:flex;justify-content:space-between;align-items:center;gap:10px;min-height:50px;padding:0 14px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:${on ? '#1c170d' : 'transparent'};cursor:pointer;font-size:14px;text-align:left;color:#f2f2ee;width:100%`;
  const fld = 'height:44px;padding:0 14px;border-radius:12px;border:1px solid #2e2e30;background:#1b1b1c;font-size:15px;outline:none;width:100%;box-sizing:border-box';
  const pill = (on: boolean) => `flex:1;height:36px;border-radius:999px;border:1px solid ${on ? A : '#2e2e30'};background:${on ? '#1c170d' : '#141415'};color:${on ? '#f0c46a' : '#f2f2ee'};font-size:13px;cursor:pointer`;

  return (
    <div class="col" style="gap:10px;flex-shrink:0" data-testid="wifi-panel">
      <div style={CARD}>
        <button onClick={() => setOpen(!open)} style={row(false, 0)} data-testid="wifi-row">
          <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span>Wi-Fi</span>
            <span style="font-size:11px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{nets === undefined ? 'Henter …' : nets === null ? 'Ikke tilgjengelig' : active ? 'Tilkoblet ' + active : 'Ikke tilkoblet Wi-Fi (kabel eller ukjent)'}</span></span>
          <span style="font-size:13px;color:#d9a441;flex-shrink:0">{open ? 'Lukk' : 'Endre'}</span>
        </button>
      </div>
      {open && <>
        {nets === null ? (
          <div style="padding:12px 14px;border-radius:14px;border:1px solid #3a2a20;background:#1a1210;font-size:12px;color:#ffb4a6;line-height:1.5">
            Enheten kan ikke styre Wi-Fi herfra{err ? ' (' + err + ')' : ''}. Den trenger NetworkManager (Skjold OS / Raspberry Pi OS Bookworm). Wi-Fi kan også settes i Skjold Flasher.
          </div>
        ) : <>
          <div class="row between" style="align-items:center">
            <span style={`font-size:${wide ? '15px' : '14px'};font-weight:600`}>Velg nettverk</span>
            <button onClick={scan} style="border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:4px 0">Oppdater</button>
          </div>
          <div style={CARD} data-testid="wifi-nets">
            {nets === undefined && <div style={row(false, 0) + ';color:#8b8b86;cursor:default'}>Leter etter nettverk …</div>}
            {(nets ?? []).map((n, i) => (
              <button key={n.ssid + i} onClick={() => setPick(i)} style={row(pick === i, i)}>
                <span style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0">{n.ssid}{n.active ? <span style="font-size:11px;color:#6fcf7f"> · tilkoblet</span> : null}</span>
                <span style="display:flex;align-items:center;gap:8px;flex-shrink:0">{n.security !== 'open' && <Lock />}<Bars sig={n.signal ?? 0} /><span style="font-size:12px;color:#f0c46a;min-width:9px">{pick === i ? '✓' : ''}</span></span>
              </button>
            ))}
            <button onClick={() => setPick('man')} style={row(man, 1) + ';color:#c9c9c4'}><span>Annet nettverk …</span><span style="font-size:12px;color:#f0c46a">{man ? '✓' : ''}</span></button>
          </div>
          {man && <>
            <input value={ssid} onInput={(e) => setSsid(e.currentTarget.value)} placeholder="Nettverksnavn (SSID)" autoCapitalize="off" autoCorrect="off" spellcheck={false} style={fld} />
            <div style="display:flex;gap:6px">{['WPA2', 'WPA3', 'Ingen'].map((l, i) => <button key={l} onClick={() => setSec(i)} style={pill(sec === i)}>{l}</button>)}</div>
          </>}
          {needPw && <input type="password" value={pw} onInput={(e) => setPw(e.currentTarget.value)} placeholder="Passord (minst 8 tegn)" style={fld} />}
          <span style="font-size:12px;color:#8b8b86;line-height:1.5">Når enheten bytter nettverk, mister den forbindelsen noen sekunder. Appen kobler til igjen av seg selv. Havner telefonen eller PC-en på et annet nett enn enheten, finner du den ikke før de er på samme nett.</span>
          {err && <span style="font-size:12px;color:#ff8a7a;line-height:1.45">{err}</span>}
          {phase === 'waiting' && <span style="font-size:12px;color:#f0c46a">Bytter nettverk – venter på at enheten svarer igjen …</span>}
          {phase === 'done' && <span style="font-size:12px;color:#6fcf7f">Enheten er tilkoblet og svarer.</span>}
          {phase === 'lost' && <span style="font-size:12px;color:#ff8a7a;line-height:1.45">Enheten svarer ikke på denne adressen.{alt ? <> Prøv <a href={alt} style="color:#d9a441">{alt.replace('http://', '')}</a> når du er på samme nett.</> : ' Koble til samme nett som enheten og åpne den på nytt.'}</span>}
          <button disabled={!ok} onClick={() => void connect()} style={`height:44px;border-radius:12px;border:none;background:${ok ? A : '#2a2a2c'};color:${ok ? '#0b0b0c' : '#6b6b67'};font-weight:600;font-size:14px;cursor:${ok ? 'pointer' : 'default'}`}>{phase === 'connecting' ? 'Kobler til …' : phase === 'waiting' ? 'Venter …' : 'Koble til'}</button>
        </>}
      </>}
    </div>
  );
}
