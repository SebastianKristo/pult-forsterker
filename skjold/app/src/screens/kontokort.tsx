// «Lag en Skjold-konto»-kortet på Hjem (mobil, PC og web-UI): vises når du ikke er logget inn på Skjold-hjem.
// «Ikke nå» skjuler kortet for godt (kontoen kan lages senere fra Innstillinger → Skjold-hjem).
import { signal } from '@preact/signals';
import { useEffect as useEff, useState } from 'preact/hooks';
import { hjem, hjemState, sameOrigin, skyUrl, tofaMangler, vedlikehold } from '../lib/hjem';
import { VedlikeholdBanner } from '../lib/vedlikehold';
import { KONTO_HOPPET } from './onboard';

export function KontoKort() {
  const [skjult, setSkjult] = useState(() => { try { return !!localStorage.getItem(KONTO_HOPPET); } catch { return false; } });
  if (vedlikehold.value?.aktiv) return <VedlikeholdBanner v={vedlikehold.value} />;
  if (tofaMangler.value) return (
    <a href={skyUrl() + '/konto?fra=app'} target="_blank" rel="noreferrer" style="display:flex;align-items:center;gap:14px;padding:14px 18px;border-radius:16px;border:1px solid #5a4420;background:linear-gradient(135deg,#1c170d,#141415 70%);color:#f2f2ee;text-decoration:none" data-testid="konto-2fa">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#f0c46a" stroke-width="1.7"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /></svg>
      <span style="flex:1;display:flex;flex-direction:column;gap:2px"><b style="font-size:14.5px">Bekreft at det er deg</b><span style="font-size:12.5px;color:#a9a9a3">Skjold-kontoen har totrinnsbekreftelse. Bekreft med passkey, kode eller fra en annen enhet for å styre hjemmefra.</span></span>
      <span style="color:#f0c46a;font-size:20px">›</span>
    </a>);
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

// ---------- Profilbildet øverst til høyre: Skjold-kontoen (eller «Logg inn») ----------
const kontoInfo = signal<{ navn: string; bilde: string; epost: string } | null>(null);
let hentet = 0;
export function KontoAvatar({ px = 36 }: { px?: number }) {
  const ok = hjemState.value === 'ok';
  useEff(() => {
    if (!ok || Date.now() - hentet < 60000) return;
    hentet = Date.now();
    void hjem.konto().then((k) => { kontoInfo.value = k; }).catch(() => { kontoInfo.value = null; });
  }, [ok]);
  const k = ok ? kontoInfo.value : null;
  const url = (sameOrigin.value ? '' : skyUrl()) + '/konto' + (k ? '' : '?fra=app');
  const tittel = k ? (k.navn ? k.navn + ' · ' : '') + k.epost + ' – Skjold-konto' : tofaMangler.value ? 'Bekreft at det er deg' : 'Logg inn på Skjold-kontoen';
  return (
    <a href={url} target={sameOrigin.value ? undefined : '_blank'} rel="noreferrer" title={tittel} aria-label={tittel} data-testid="konto-avatar"
      style={`width:${px}px;height:${px}px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;overflow:hidden;text-decoration:none;${k ? 'box-shadow:0 0 0 2px #0b0b0c,0 0 0 3px #5a4420' : 'border:1px solid #2e2e30;background:#141415;color:#8b8b86'}`}>
      {k ? (k.bilde ? <img src={k.bilde} alt="" style="width:100%;height:100%;object-fit:cover" />
        : <span style={`width:100%;height:100%;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#f3cf7f,#d9a441);color:#0b0b0c;font-weight:600;font-size:${Math.round(px * 0.42)}px`}>{(k.navn || k.epost || '?')[0]?.toUpperCase()}</span>)
        : <svg width={px * 0.55} height={px * 0.55} viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"><path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0" /></svg>}
    </a>);
}
