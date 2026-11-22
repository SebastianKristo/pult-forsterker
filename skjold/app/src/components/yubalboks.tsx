// «Finner du den ikke? Last ned» under Navidrome-søket (app, web-UI og Touch). Viser de beste treffene fra YouTube Music
// slik at du velger riktig låt; bare når både tittel og artist står i søket, lastes den ned uten å spørre (auto).
import { useEffect, useState } from 'preact/hooks';
import { api, type YubalKandidat } from '../lib/api';
import { YB_TEKST, ybAlle, ybLastNed, yubalAuto } from '../lib/yubal';

const MONO = "'IBM Plex Mono',ui-monospace,monospace";
export function YubalBoks({ q, auto = false, ferdig, stor = false }: { q: string; auto?: boolean; ferdig?: () => void; stor?: boolean }) {
  const [k, setK] = useState<YubalKandidat[] | null>(null), [busy, setBusy] = useState(false), [feil, setFeil] = useState('');
  const ned = ybAlle.value[q], her = !!ned;
  const finn = async (automatisk: boolean) => {
    setBusy(true); setFeil('');
    try {
      const r = await api.yubalKandidater(q);
      if (automatisk && yubalAuto() && r.sikker) { void ybLastNed(q, r.sikker, () => ferdig?.()); setK(null); }
      else { setK(r.kandidater); if (!r.kandidater.length) setFeil('Fant ingenting å laste ned for «' + q + '».'); }
    } catch (e) { setFeil(e instanceof Error ? e.message : String(e)); }
    setBusy(false);
  };
  useEffect(() => { setK(null); setFeil(''); if (auto && !her) void finn(true); }, [q, auto]);
  const h = stor ? 56 : 48;
  const boks = 'display:flex;flex-direction:column;gap:8px;padding:12px;border-radius:16px;background:#141415;border:1px solid #2a2a2c;color:#f2f2ee';
  if (her && ned) return (
    <div style={boks + ';display:grid;grid-template-columns:' + h + 'px minmax(0,1fr);gap:14px;align-items:center'}>
      <div style={`width:${h}px;height:${h}px;border-radius:10px;background:${ned.bilde ? 'url("' + ned.bilde.replace(/"/g, '') + '") center / cover, #1b1b1c' : '#1b1b1c'}`} />
      <div style="display:flex;flex-direction:column;gap:6px;min-width:0">
        <span style="font-size:14.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{ned.tittel}{ned.artist ? ' – ' + ned.artist : ''}</span>
        <span style={`font-size:12px;color:${ned.status === 'failed' ? '#ff9a8a' : ned.status === 'completed' ? '#6fcf7f' : '#c9b48a'}`}>{ned.feil || YB_TEKST[ned.status] || ned.status}{ned.status === 'downloading' || ned.status === 'importing' ? ' · ' + ned.fremdrift + ' %' : ''}</span>
        {ned.status !== 'failed' && ned.status !== 'completed' && <div style="height:4px;border-radius:2px;background:#242426;overflow:hidden"><div style={`height:100%;width:${Math.max(4, ned.fremdrift)}%;background:#f0c46a;transition:width .6s ease`} /></div>}
      </div>
    </div>);
  if (k) return (
    <div style={boks}>
      <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.14em;color:#c9b48a`}>HVILKEN MENER DU? · LASTES NED TIL NAVIDROME</span>
      {k.map((x) => (
        <button key={x.vid} class="rip" onClick={() => { setK(null); void ybLastNed(q, x, () => ferdig?.()); }}
          style={`position:relative;overflow:hidden;min-height:${h}px;display:grid;grid-template-columns:${h - 8}px minmax(0,1fr) auto;gap:12px;align-items:center;padding:4px 6px;border:none;border-radius:10px;background:transparent;color:inherit;text-align:left;cursor:pointer`}>
          <span style={`width:${h - 8}px;height:${h - 8}px;border-radius:8px;background:${x.bilde ? 'url("' + x.bilde.replace(/"/g, '') + '") center / cover, #1b1b1c' : '#1b1b1c'}`} />
          <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><b style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.tittel}</b><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{[x.artist, x.album, x.varighet].filter(Boolean).join(' · ')}</span></span>
          <span style="font-size:12px;font-weight:600;color:#f0c46a;white-space:nowrap">Last ned</span>
        </button>))}
      <button onClick={() => setK(null)} style="align-self:flex-start;border:none;background:none;color:#8b8b86;font-size:12.5px;cursor:pointer;padding:4px 6px">Ingen av disse</button>
    </div>);
  return (
    <div style="display:flex;flex-direction:column;gap:6px">
      <button class="rip" disabled={busy} onClick={() => void finn(false)} style={`position:relative;overflow:hidden;align-self:flex-start;height:${stor ? 44 : 38}px;padding:0 16px;border-radius:${stor ? 22 : 19}px;border:1px solid #5a4420;background:#1c170d;color:#f0c46a;font-size:13px;font-weight:600;cursor:pointer`}>
        {busy ? 'Leter …' : 'Finner du den ikke? Last ned «' + q + '» til Navidrome'}</button>
      {feil && <span style="font-size:12px;color:#ff9a8a">{feil}</span>}
    </div>);
}
