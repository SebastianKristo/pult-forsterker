// Plattform: Matter (Integrasjoner → Matter) og Skjold Cloud (Innstillinger → Skjold Cloud).
import { signal } from '@preact/signals';
import { useEffect, useState } from 'preact/hooks';
import { apiPost, apiReq } from '../lib/api';
import { qrMatrix } from '../lib/qr';
import { showToast } from '../lib/store';
import { Toggle } from '../components/ui';

const MONO = "'IBM Plex Mono',monospace";
type Row = { n: string; hint?: string; el: preact.ComponentChildren };
const txt = (v: string) => <span style={`font-family:${MONO};font-size:13px;color:#c9c9c4;text-align:right`}>{v}</span>;
const btn = (label: string, f: () => void) => <button onClick={f} style="height:36px;padding:0 14px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;cursor:pointer;white-space:nowrap;color:#f2f2ee">{label}</button>;
const err = (e: unknown) => (e instanceof Error ? e.message : String(e));

export function QR({ text, size = 168, label = 'QR-kode' }: { text: string; size?: number; label?: string }) {
  let m: boolean[][] = [];
  try { m = qrMatrix(text); } catch { return null; }
  const n = m.length, q = 2;
  let d = '';
  m.forEach((row, y) => row.forEach((on, x) => { if (on) d += `M${x + q} ${y + q}h1v1h-1z`; }));
  return <svg viewBox={`0 0 ${n + 2 * q} ${n + 2 * q}`} width={size} height={size} role="img" aria-label={label} style="display:block;border-radius:10px;background:#fff;shape-rendering:crispEdges"><path d={d} fill="#0b0b0c" /></svg>;
}

// ---------- Matter ----------
export interface MatterInfo {
  enabled: boolean; available: boolean; running: boolean; commissioned: boolean; fabrics: { label: string; vendor: number }[];
  qr: string; manual: string; endpoints: string[]; error?: string;
  installed?: boolean; busy?: '' | 'install' | 'uninstall'; memMB?: number; lowmem?: boolean;
}
export const matter = signal<MatterInfo | null>(null);
const mErr = signal('');
export async function matterLoad(): Promise<void> { try { matter.value = await apiReq<MatterInfo>('/api/matter'); mErr.value = ''; } catch { matter.value = null; } }
async function matterSet(b: { enabled?: boolean; reset?: boolean; install?: boolean; uninstall?: boolean }): Promise<void> {
  try { matter.value = await apiPost<MatterInfo>('/api/matter', b); mErr.value = ''; } catch (e) { mErr.value = err(e); }
}
export function matterStatus(): string {
  const m = matter.value;
  if (m?.busy === 'install') return 'Installerer …';
  if (m?.busy === 'uninstall') return 'Avinstallerer …';
  if (m && m.installed === false) return 'Ikke installert';
  if (!m || !m.enabled) return 'Av';
  if (!m.available) return 'Krever installasjon';
  if (!m.running) return 'Starter …';
  return m.commissioned ? `Paret · ${m.fabrics.length} kontroller${m.fabrics.length === 1 ? '' : 'e'}` : 'Venter på paring';
}
export function matterRows(): Row[] {
  const m = matter.value;
  if (!m) return [{ n: 'Matter', hint: 'Får ikke kontakt med Skjold.', el: btn('Prøv igjen', () => void matterLoad()) }];
  const ram = m.lowmem ? ` Denne enheten har bare ${m.memMB} MB minne – Matter tar ca. 120 MB og kan gjøre resten tregere.` : '';
  if (m.busy) return [{ n: m.busy === 'install' ? 'Installerer Matter-pluginen' : 'Avinstallerer Matter-pluginen', hint: 'Dette tar noen minutter. Du kan lukke siden.', el: txt('…') }];
  if (m.installed === false) return [
    { n: 'Matter-plugin', hint: 'Ikke installert. Installerer Node.js 20 og matter.js (ca. 150 MB på disk, ca. 120 MB minne når den kjører). Kan fjernes helt igjen.' + ram, el: btn('Installer', () => void matterSet({ install: true })) },
    ...(m.error ? [{ n: 'Feil', el: txt(m.error) }] : []),
  ];
  const rows: Row[] = [{ n: 'Vis Skjold i Matter', hint: 'Apple Hjem, Google Home, Alexa, SmartThings og Home Assistant – uten skyen.', el: <Toggle on={m.enabled} onChange={(b) => void matterSet({ enabled: b })} /> }];
  if (!m.enabled) return [...rows, { n: 'Avinstaller Matter-plugin', hint: 'Fjerner matter.js og Node.js igjen.', el: btn('Avinstaller', () => void matterSet({ uninstall: true })) }];
  if (!m.available) return [...rows, { n: 'Matter-tjenesten mangler', hint: m.error || 'Slå på pluginen «Matter» og kjør oppdatering – den installerer Node 20 og matter.js.', el: txt('Krever oppdatering') }];
  rows.push({ n: 'Status', hint: m.error || (m.running ? '' : 'Tjenesten starter …'), el: txt(m.commissioned ? '● Paret' : '○ Venter') });
  if (m.qr) rows.push({ n: 'Paringskode', hint: 'Skann QR-koden i appen (Legg til enhet → Matter), eller skriv inn den manuelle koden. Flere apper kan legges til etter hverandre.', el: <div style="display:flex;flex-direction:column;align-items:flex-end;gap:10px"><QR text={m.qr} label="QR-kode for Matter" /><span style={`font-family:${MONO};font-size:20px;letter-spacing:.06em;color:#f0c46a`}>{m.manual}</span></div> });
  if (m.fabrics.length) rows.push({ n: 'Paret med', el: txt(m.fabrics.map((f) => f.label || `leverandør ${f.vendor}`).join(', ')) });
  rows.push({ n: 'Dette vises', hint: 'Høyttaler: av/på = strøm, nivå = volum (0–100), demp. Pluss én bryter per radiofavoritt 1–6 og en kildevelger.', el: txt(`${m.endpoints.length || 8} endepunkter`) });
  rows.push({ n: 'Glem paringer', hint: 'Fjerner Skjold fra alle Matter-kontrollere og lager ny paringskode.', el: btn('Glem paringer', () => { if (confirm('Glemme alle Matter-paringer?')) void matterSet({ reset: true }); }) });
  if (mErr.value) rows.push({ n: 'Feil', el: txt(mErr.value) });
  rows.push({ n: 'Avinstaller Matter-plugin', hint: 'Stopper tjenesten og fjerner matter.js, paringer og Node.js (hvis Skjold installerte den). Frigjør minne og disk.' + ram, el: btn('Avinstaller', () => { if (confirm('Avinstallere Matter? Paringene i Hjem-appene forsvinner.')) void matterSet({ uninstall: true }); }) });
  return rows;
}

// ---------- Skjold Cloud ----------
interface CloudInfo {
  available: boolean; enabled: boolean; har_frase: boolean; deler: string[]; alle_deler: string[]; sist_synk: number; feil: string;
  konflikter: { del: string; nokkel: string; vant: string; t: number }[]; sky_koblet: boolean; frase?: string; error?: string;
}
const DELNAVN: Record<string, string> = {
  favoritter: 'Radiofavoritter', rutiner: 'Rutiner', innstillinger: 'Innstillinger (uten passord)', eq: 'Equalizer',
  wrapped: 'Skjold Wrapped', historikk: 'Lyttehistorikk (sammendrag)', kassetter: 'Kassetter', plugins: 'Plugins'
};
const card = 'display:flex;flex-direction:column;gap:12px;padding:16px;border-radius:14px;background:#151516;border:1px solid #232325';

export function CloudPanel() {
  const [c, setC] = useState<CloudInfo | null>(null);
  const [frase, setFrase] = useState('');     // vises én gang
  const [inn, setInn] = useState('');
  const [busy, setBusy] = useState(false);
  const load = async () => { try { setC(await apiReq<CloudInfo>('/api/cloud')); } catch { setC(null); } };
  const send = async (b: Record<string, unknown>) => {
    setBusy(true);
    try { const r = await apiPost<CloudInfo>('/api/cloud', b); setC(r); if (r.frase) setFrase(r.frase); return r; }
    catch (e) { showToast(err(e)); return null; } finally { setBusy(false); }
  };
  useEffect(() => { void load(); }, []);
  if (!c) return <div style={card}>Får ikke kontakt med Skjold.</div>;
  if (!c.available) return <div style={card}>{c.error || 'Skjold Cloud krever oppdatering.'}</div>;
  const when = c.sist_synk ? new Date(c.sist_synk * 1000).toLocaleString('nb-NO') : 'aldri';
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      <div style={card}>
        <b>Skjold Cloud</b>
        <span style="color:#a5a5a0;font-size:13px;line-height:1.5">Synk favoritter, rutiner, EQ og innstillinger mellom hjemmene dine. Alt krypteres her på Skjold med en nøkkel fra gjenopprettingsfrasen din før det sendes – skyen kan ikke lese det. Passord synkes aldri.</span>
        {!c.sky_koblet && <span style="color:#e8a55a;font-size:13px">Koble Skjold til Skjold-hjem først (Innstillinger → Skjold-hjem).</span>}
        {!c.enabled ? <>
          <div style="display:flex;gap:8px;flex-wrap:wrap">{btn(busy ? 'Lager …' : 'Slå på og lag ny frase', () => void send({ aktiver: true }))}</div>
          <span style="color:#a5a5a0;font-size:13px">Har du alt Skjold Cloud på et annet hjem? Skriv inn de 12 ordene:</span>
          <div style="display:flex;gap:8px;flex-wrap:wrap"><input value={inn} onInput={(e) => setInn((e.currentTarget as HTMLInputElement).value)} placeholder="12 ord med mellomrom" style={`flex:1;min-width:200px;height:36px;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-family:${MONO};font-size:12px;color:#f2f2ee`} />{btn('Gjenopprett', () => void send({ aktiver: true, frase: inn }).then((r) => { if (r) setInn(''); }))}</div>
        </> : <>
          <div style="display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap"><span>Sist synket: {when}</span>{btn(busy ? 'Synker …' : 'Synk nå', () => void send({ synk: true }))}</div>
          {c.feil && <span style="color:#e86a6a;font-size:13px">{c.feil}</span>}
        </>}
      </div>
      {frase && <div style={card + ';border-color:#d9a441'}>
        <b>Gjenopprettingsfrasen din</b>
        <span style="color:#a5a5a0;font-size:13px">Skriv den ned nå – den vises bare denne ene gangen. Uten den kan ingen (heller ikke vi) lese dataene dine.</span>
        <div style={`font-family:${MONO};font-size:15px;display:grid;grid-template-columns:repeat(auto-fill,minmax(110px,1fr));gap:6px`}>{frase.split(' ').map((w, i) => <span key={i}>{i + 1}. {w}</span>)}</div>
        {btn('Jeg har skrevet den ned', () => setFrase(''))}
      </div>}
      {c.enabled && <div style={card}>
        <b>Hva synkes</b>
        {c.alle_deler.map((d) => <label key={d} style="display:flex;justify-content:space-between;align-items:center;gap:8px"><span>{DELNAVN[d] || d}</span><Toggle on={c.deler.includes(d)} onChange={(b) => void send({ deler: b ? [...c.deler, d] : c.deler.filter((x) => x !== d) })} /></label>)}
      </div>}
      {c.enabled && c.konflikter.length > 0 && <div style={card}>
        <b>Konflikter</b>
        <span style="color:#a5a5a0;font-size:13px">Endret på to hjem samtidig – den siste endringen ble beholdt.</span>
        {c.konflikter.slice().reverse().map((k, i) => <span key={i} style={`font-family:${MONO};font-size:12px`}>{new Date(k.t * 1000).toLocaleString('nb-NO')} · {DELNAVN[k.del] || k.del} · {k.nokkel} · {k.vant === 'lokal' ? 'dette hjemmet vant' : 'et annet hjem vant'}</span>)}
      </div>}
      {c.enabled && <div style={card}>{btn('Slå av Skjold Cloud', () => { if (confirm('Slå av? Frasen glemmes på denne Skjold-en; dataene i skyen blir liggende.')) void send({ deaktiver: true }); })}</div>}
    </div>
  );
}
