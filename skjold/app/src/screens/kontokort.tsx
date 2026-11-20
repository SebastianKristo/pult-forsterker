// «Lag en Skjold-konto»-kortet på Hjem (mobil, PC og web-UI): vises når du ikke er logget inn på Skjold-hjem.
// Kan hoppes over; da kommer det tilbake etter 30 dager.
import { useState } from 'preact/hooks';
import { hjemState, skyUrl } from '../lib/hjem';
import { KONTO_HOPPET } from './onboard';

export function KontoKort() {
  const [skjult, setSkjult] = useState(() => { try { return Date.now() - Number(localStorage.getItem(KONTO_HOPPET) || 0) < 30 * 86400000; } catch { return false; } });
  if (skjult || hjemState.value !== 'login') return null;
  const hopp = () => { try { localStorage.setItem(KONTO_HOPPET, String(Date.now())); } catch { /* privat modus */ } setSkjult(true); };
  return (
    <div style="display:flex;align-items:center;gap:16px;padding:16px 18px;border-radius:16px;border:1px solid #5a4420;background:linear-gradient(135deg,#1c170d,#141415 70%)" data-testid="konto-kort">
      <span style="display:flex;gap:3px;align-items:flex-start;height:22px;flex-shrink:0">{[11, 16, 21, 16, 11].map((h, i) => <i key={i} style={`width:3.6px;height:${h}px;border-radius:2px;background:${i === 2 ? '#d9a441' : '#f2f2ee'}`} />)}</span>
      <span style="display:flex;flex-direction:column;gap:2px;flex:1;min-width:0">
        <span style="font-size:15px;font-weight:600">Lag en Skjold-konto</span>
        <span style="font-size:12.5px;color:#a9a9a3;line-height:1.4">Styr Skjold hjemmefra, del hjemmet med familien og ta vare på oppsettet i Skjold Lab Valhalla.</span>
      </span>
      <a href={skyUrl() + '/konto?velkommen=1&fra=app'} target="_blank" rel="noreferrer" style="height:40px;padding:0 16px;border-radius:20px;background:#f0c46a;color:#0b0b0c;font-size:13.5px;font-weight:600;display:flex;align-items:center;text-decoration:none;white-space:nowrap;flex-shrink:0">Lag konto</a>
      <button onClick={hopp} aria-label="Ikke nå" style="border:none;background:none;color:#8b8b86;font-size:13px;cursor:pointer;flex-shrink:0">Ikke nå</button>
    </div>
  );
}
