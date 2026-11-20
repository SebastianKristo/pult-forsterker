// Vedlikehold i Skjold Lab Valhalla: banner med nedtelling. Brukes av appen, web-UI-et og konto-siden.
// Skyen svarer 503 { error: "vedlikehold", vedlikehold } – og offentlig GET /api/vedlikehold.
import { useEffect, useState } from 'preact/hooks';

export interface Vedlikehold { aktiv: boolean; melding?: string; til?: number; fra?: number }

export function nedtelling(til: number, naa = Date.now() / 1000): string {
  const s = Math.max(0, Math.round(til - naa));
  if (!s) return 'snart tilbake';
  const t = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sek = s % 60;
  return t ? `${t} t ${String(m).padStart(2, '0')} min` : `${m}:${String(sek).padStart(2, '0')}`;
}

export function VedlikeholdBanner({ v, kompakt = false }: { v: Vedlikehold | null | undefined; kompakt?: boolean }) {
  const [, tikk] = useState(0);
  useEffect(() => { if (!v?.aktiv) return; const id = setInterval(() => tikk((x) => x + 1), 1000); return () => clearInterval(id); }, [v?.aktiv]);
  if (!v?.aktiv) return null;
  const klokke = v.til ? new Date(v.til * 1000).toLocaleTimeString('nb-NO', { hour: '2-digit', minute: '2-digit' }) : '';
  return (
    <div role="status" style={`display:flex;align-items:center;gap:14px;padding:${kompakt ? '10px 14px' : '14px 18px'};border-radius:16px;background:linear-gradient(135deg,#231a0b,#151413 70%);border:1px solid #5a4420;color:#f2f2ee`}>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#f0c46a" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4z" /></svg>
      <span style="flex:1;min-width:0;display:flex;flex-direction:column;gap:2px">
        <b style="font-size:14.5px">Skjold Lab Valhalla har vedlikehold{v.melding ? ' – ' + v.melding : ''}</b>
        <span style="font-size:12.5px;color:#b9b2a4;line-height:1.4">Fjernstyring, deling og Skjold Cloud er borte en stund. Du kan fortsatt bruke Skjold lokalt hjemme – enhetene, appen og web-UI-et på samme nett virker som vanlig.</span>
      </span>
      {v.til ? <span style="display:flex;flex-direction:column;align-items:flex-end;flex-shrink:0">
        <span style="font-family:'IBM Plex Mono',ui-monospace,monospace;font-size:20px;color:#f0c46a;font-variant-numeric:tabular-nums">{nedtelling(v.til)}</span>
        <span style="font-size:11px;color:#8b8b86">tilbake ca. {klokke}</span>
      </span> : null}
    </div>);
}
