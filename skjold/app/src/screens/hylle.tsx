/** Skjold Kassetthylle: ta ut en kassett = spill den (pi/skjold_hylle.py, esphome/skjold-hylle.yaml). */
import { useEffect, useState } from 'preact/hooks';
import { everyVisible } from '../lib/store';
import { apiPost, apiReq, type NfcCard } from '../lib/api';

const A = '#e8b04a';
const box = 'background:#141415;border:1px solid #242426;border-radius:14px;padding:14px';
const inp = 'background:#0e0e0f;border:1px solid #2a2a2c;border-radius:8px;color:#f2f2ee;padding:8px 10px;font:inherit;width:140px';
const btn = 'padding:8px 14px;border-radius:9px;border:1px solid #2a2a2c;background:#1a1a1b;color:#f2f2ee;cursor:pointer;font:inherit';

interface Plass { uid: string; inne: boolean }
interface Hylle { device: string; navn: string; antall?: number; sist: number; ute: string; lys: string; plasser: Record<string, Plass> }

const FARGE: Record<string, [string, string]> = {
  s: [A, 'Spiller nå'], i: ['#cfccc4', 'Står inne'], u: ['#4a7bd0', 'Ukjent brikke'], t: ['#2c2c2e', 'Tom'],
};

export function HyllePanel({ cards }: { cards: NfcCard[] }) {
  const [h, setH] = useState<Hylle[] | null>(null), [err, setErr] = useState('');
  const navnFor = (uid: string) => cards.find((c) => c.uid === uid)?.navn ?? (uid ? 'Ukjent brikke' : '');
  const last = () => apiReq<{ hyller: Hylle[] }>('/api/hylle').then((r) => { setH(r.hyller); setErr(''); }).catch((e) => setErr(String(e)));
  useEffect(() => { void last(); const t = everyVisible(() => void last(), 3000); return () => clearInterval(t); }, []);
  const sett = (b: Record<string, unknown>) => apiPost<{ hyller: Hylle[] }>('/api/hylle', b).then((r) => setH(r.hyller)).catch((e) => setErr(String(e)));
  return (
    <div style={box + ';display:flex;flex-direction:column;gap:12px'}>
      <span style="font-size:16px;font-weight:600">Kassetthylle</span>
      <span style="font-size:13px;color:#8b8b86;line-height:1.5">Ta ut en kassett av hylla, så spilles den på enheten kassettene er paret med. Sett den tilbake, så stopper musikken. Bygg: <code>kabinett/hylle/LES_MEG.md</code>, fastvare: <code>esphome/skjold-hylle.yaml</code>.</span>
      {err && <span style="font-size:12px;color:#ff8a7a">{err}</span>}
      {h && !h.length && <span style="font-size:13px;color:#8b8b86">Ingen hylle har meldt seg ennå. Flash hylla og pek <code>skjold_host</code> hit – den dukker opp her når den starter.</span>}
      {(h ?? []).map((y) => {
        const n = y.antall || y.lys.length || 6;
        return (
          <div key={y.device} style="display:flex;flex-direction:column;gap:10px;border-top:1px solid #242426;padding-top:10px">
            <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
              <input value={y.navn} onChange={(e) => void sett({ device: y.device, navn: e.currentTarget.value })} style={inp} aria-label="Navn på hylla" />
              <span style="font-size:12px;color:#8b8b86">{y.device} · {n} plasser</span>
              <button style={btn} onClick={() => void sett({ device: y.device, glem: true })}>Glem</button>
            </div>
            <div style={`display:grid;grid-template-columns:repeat(${Math.min(n, 6)},minmax(0,1fr));gap:8px`}>
              {Array.from({ length: n }, (_, i) => {
                const p = y.plasser[String(i + 1)], c = y.lys[i] || 't', [farge, tekst] = FARGE[c] ?? FARGE.t ?? ['#2c2c2e', 'Tom'];
                return (
                  <div key={i} style="display:flex;flex-direction:column;gap:6px;align-items:center;padding:10px 6px;border-radius:10px;background:#0e0e0f;min-width:0">
                    <span style={`width:14px;height:14px;border-radius:50%;background:${farge};box-shadow:0 0 10px ${c === 's' ? farge : 'transparent'}`} />
                    <span style="font-size:11px;color:#8b8b86">Plass {i + 1}</span>
                    <span style="font-size:12px;text-align:center;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:100%">{p?.uid ? navnFor(p.uid) : '–'}</span>
                    <span style="font-size:11px;color:#6a6a65">{tekst}</span>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
