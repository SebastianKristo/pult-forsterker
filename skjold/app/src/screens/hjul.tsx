/** Skjold Hjul: ESPHome-fjernkontroll med dreieknapp og 4 favorittknapper (pi/skjold_hjul.py, esphome/skjold-hjul.yaml). */
import { useEffect, useState } from 'preact/hooks';
import { everyVisible } from '../lib/store';
import { apiPost, apiReq, getBase, type NfcCard } from '../lib/api';

const A = '#e8b04a';
const box = 'background:#141415;border:1px solid #242426;border-radius:14px;padding:14px';
const inp = 'background:#0e0e0f;border:1px solid #2a2a2c;border-radius:8px;color:#f2f2ee;padding:8px 10px;font:inherit';
const btn = (on = false) => `padding:8px 14px;border-radius:9px;border:1px solid ${on ? A : '#2a2a2c'};background:${on ? '#1c170d' : '#1a1a1b'};color:#f2f2ee;cursor:pointer;font:inherit`;

type Fav = Omit<NfcCard, 'uid'> | null;
interface HjulDev { navn: string; rom: string; sist?: number; batteri?: number }
interface HjulCfg { favoritter: Fav[]; steg: number; enheter: Record<string, HjulDev>; rom: string[] }

function ago(t?: number): string {
  if (!t) return 'aldri';
  const s = Math.max(0, Date.now() / 1000 - t);
  return s < 90 ? 'nå nettopp' : s < 3600 ? `${Math.round(s / 60)} min siden` : s < 86400 ? `${Math.round(s / 3600)} t siden` : `${Math.round(s / 86400)} d siden`;
}

export function HjulPanel({ cards }: { cards: NfcCard[] }) {
  const [cfg, setCfg] = useState<HjulCfg | null>(null);
  const [err, setErr] = useState('');
  const load = () => apiReq<HjulCfg>('/api/hjul').then((c) => { setCfg(c); setErr(''); }).catch((e) => setErr(String((e as Error).message || e)));
  useEffect(() => { void load(); const t = everyVisible(load, 8000); return () => clearInterval(t); }, []);
  const save = (b: Partial<HjulCfg> & { glem?: string[] }) => apiPost<HjulCfg>('/api/hjul', b).then(setCfg).catch((e) => setErr(String((e as Error).message || e)));
  if (!cfg) return <div style={box + ';color:#9a9a96'}>{err ? 'Fikk ikke kontakt: ' + err : 'Henter …'}</div>;

  const setFav = (i: number, uid: string) => {
    const favs = [...cfg.favoritter];
    const c = cards.find((x) => x.uid === uid);
    favs[i] = c ? { navn: c.navn, handling: c.handling, verdi: c.verdi, rom: [], volum: c.volum, ved_uttak: 'ingenting', omslag: c.omslag, undertittel: c.undertittel } : null;
    void save({ favoritter: favs });
  };
  const devs = Object.entries(cfg.enheter);
  const host = getBase().replace(/^https?:\/\//, '').replace(/\/.*$/, '') || location.host;
  return (
    <div style="display:flex;flex-direction:column;gap:12px">
      <div style={box}>
        <b>Skjold Hjul</b>
        <p style="color:#9a9a96;margin:6px 0 0">Drei for volum · trykk for spill/pause · dobbeltrykk for neste · hold inne for å bytte rom · knapp 1–4 starter favorittene under. Bygg den etter <code>kabinett/hjul/LES_MEG.md</code> og flash <code>esphome/skjold-hjul.yaml</code> med <code>skjold_host: {host}</code>.</p>
      </div>
      {err && <small style="color:#e06c5a">{err}</small>}
      <div style={box + ';display:flex;flex-direction:column;gap:10px'}>
        <b>Favorittknapper</b>
        {!cards.length && <small style="color:#9a9a96">Favorittene velges blant kassettene dine – koble en kassett først (fanen Kassetter), så dukker den opp her.</small>}
        {cfg.favoritter.map((f, i) => (
          <label key={i} style="display:flex;gap:10px;align-items:center">
            <span style={`width:28px;height:28px;border-radius:50%;border:1px solid ${A};color:${A};display:grid;place-items:center`}>{i + 1}</span>
            <select style={inp + ';flex:1'} value={cards.find((c) => f && c.navn === f.navn && JSON.stringify(c.verdi) === JSON.stringify(f.verdi))?.uid ?? ''} onChange={(e) => setFav(i, (e.target as HTMLSelectElement).value)}>
              <option value="">{f ? f.navn + ' (lagret)' : '– ingen –'}</option>
              {cards.map((c) => <option key={c.uid} value={c.uid}>{c.navn}{c.undertittel ? ' · ' + c.undertittel : ''}</option>)}
            </select>
            {f && <button style={btn()} onClick={() => setFav(i, '')}>Fjern</button>}
          </label>))}
        <label>Volumsteg per hakk <input style={inp + ';width:70px'} type="number" min={1} max={10} value={cfg.steg} onChange={(e) => void save({ steg: +(e.target as HTMLInputElement).value })} /></label>
      </div>
      <div style={box + ';display:flex;flex-direction:column;gap:10px'}>
        <b>Hjul i huset</b>
        {!devs.length && <small style="color:#9a9a96">Ingen hjul har meldt seg ennå. Når det er flashet og på Wi-Fi, dukker det opp her etter første trykk.</small>}
        {devs.map(([id, d]) => (
          <div key={id} style="display:flex;gap:10px;align-items:center;flex-wrap:wrap">
            <input style={inp + ';width:160px'} value={d.navn} onChange={(e) => void save({ enheter: { [id]: { ...d, navn: (e.target as HTMLInputElement).value } } })} />
            <select style={inp} value={d.rom} onChange={(e) => void save({ enheter: { [id]: { ...d, rom: (e.target as HTMLSelectElement).value } } })}>
              {cfg.rom.map((r) => <option key={r} value={r}>{r === 'Her' ? 'Dette rommet' : r}</option>)}
            </select>
            <small style="color:#9a9a96">{d.batteri != null ? `🔋 ${d.batteri} % · ` : ''}sist {ago(d.sist)}</small>
            <button style={btn()} onClick={() => { if (confirm(`Glemme «${d.navn}»?`)) void save({ glem: [id] }); }}>Glem</button>
          </div>))}
      </div>
    </div>
  );
}
