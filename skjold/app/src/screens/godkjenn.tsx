// «Prøver du å logge inn?» – en ny nettleser/telefon ber om godkjenning for Skjold-kontoen (totrinnsbekreftelse).
// Appen er allerede bekreftet, så den spør skyen jevnlig og viser tre tall; riktig tall godkjenner den nye enheten.
import { useEffect, useState } from 'preact/hooks';
import { hjem, hjemState, loadSteder, vedlikehold } from '../lib/hjem';

type Ventende = { rid: string; navn: string; sted: string; t: number; valg: number[] };

export function GodkjennInnlogging() {
  const [l, setL] = useState<Ventende[]>([]), [svart, setSvart] = useState('');
  const pa = hjemState.value === 'ok';
  useEffect(() => {
    if (!pa) return;
    let id = 0, slutt = false;
    const poll = async () => {
      try { const v = await hjem.ventende(); if (!slutt) setL(Array.isArray(v) ? v : []); } catch { /* ikke innlogget / ingen 2FA */ }
      if (!slutt) id = window.setTimeout(() => void poll(), document.hidden ? 20000 : 5000);
    };
    void poll();
    return () => { slutt = true; clearTimeout(id); };
  }, [pa]);
  const vh = !!vedlikehold.value?.aktiv;
  useEffect(() => {   // under vedlikehold: se etter når skyen er tilbake, og last hjemmene igjen
    if (!vh) return;
    const id = window.setInterval(() => void hjem.meg().then((m) => { if (!m.vedlikehold?.aktiv) void loadSteder(); }).catch(() => undefined), 30000);
    return () => clearInterval(id);
  }, [vh]);
  const f = l[0];
  if (svart) return <div style="position:fixed;left:50%;bottom:90px;transform:translateX(-50%);z-index:9999;background:#1c1c1e;border:1px solid #2a2a2c;color:#f2f2ee;padding:12px 18px;border-radius:12px;font-size:14px">{svart}</div>;
  if (!f) return null;
  const svar = async (s: number | 'avvis') => {
    setL(l.slice(1));
    try { const r = await hjem.godkjenn(f.rid, s); setSvart(r.status === 'godkjent' ? 'Innloggingen er godkjent' : 'Innloggingen ble avvist'); }
    catch (e) { setSvart(e instanceof Error ? e.message : 'Feil'); }
    setTimeout(() => setSvart(''), 3000);
  };
  return (
    <div style="position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,.62);backdrop-filter:blur(8px);display:flex;align-items:center;justify-content:center;padding:20px" data-testid="godkjenn">
      <div style="max-width:380px;width:100%;display:flex;flex-direction:column;align-items:center;gap:12px;text-align:center;padding:30px 24px;border-radius:24px;background:#141415;border:1px solid #2a2a2c;color:#f2f2ee">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#f0c46a" stroke-width="1.6"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" /></svg>
        <b style="font-size:20px">Prøver du å logge inn?</b>
        <span style="font-size:12.5px;color:#8b8b86">{f.navn}{f.sted ? ' · ' + f.sted : ''} · {new Date(f.t * 1000).toLocaleTimeString('nb-NO', { hour: '2-digit', minute: '2-digit' })}</span>
        <span style="font-size:14px">Trykk tallet som vises på den andre skjermen.</span>
        <div style="display:flex;gap:12px;margin:4px 0">{f.valg.map((x) => <button key={x} onClick={() => void svar(x)} style="width:74px;height:74px;border-radius:37px;border:1px solid #2a2a2c;background:#1b1b1c;color:#f2f2ee;font:500 26px 'IBM Plex Mono',ui-monospace,monospace;cursor:pointer">{x}</button>)}</div>
        <button onClick={() => void svar('avvis')} style="height:42px;padding:0 18px;border-radius:21px;border:1px solid #3a2a20;background:#1b1b1c;color:#ff9a8a;font-size:14px;font-weight:600;cursor:pointer">Nei, det er ikke meg</button>
        <span style="font-size:11.5px;color:#6b6b66;line-height:1.4">Trykker du feil tall, avvises innloggingen.</span>
      </div>
    </div>);
}
