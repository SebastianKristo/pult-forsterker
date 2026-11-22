// «Populært» på Navidrome-forsiden: det folk hører på akkurat nå, og de største låtene og albumene fra hvert tiår
// (pi/skjold_populaert.py: Apple Music- og Deezer-lister). Har du låten eller albumet i Navidrome, spilles det;
// ellers kan yubal laste det ned rett inn i biblioteket.
import { useEffect, useState } from 'preact/hooks';
import { signal } from '@preact/signals';
import { api, type PopAlbum, type PopSang, type Populaert } from '../lib/api';
import { ndSearch, ndSearchAll, type NdAlbum, type NdSong } from '../lib/navidrome';
import { ybAktiv, ybAlle, ybLastNedAlbum, ybLastNedSang, ybNyttSok, ybTekst, yubalPa } from '../lib/yubal';

const PERIODER: [string, string][] = [['na', 'Akkurat nå'], ['10', '2010-tallet'], ['00', '2000-tallet'], ['90', '90-tallet'], ['80', '80-tallet'], ['70', '70-tallet'], ['60', '60-tallet']];
const MONO = "'IBM Plex Mono',ui-monospace,monospace";
const periode = signal('na');
const lister: Record<string, Populaert> = {};

const norm = (t: string) => t.normalize('NFKC').toLowerCase().replace(/\s*[([].*?[)\]]/g, '').replace(/\s+-\s+.*(remaster|version|edit|live).*$/i, '').replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
const hoved = (a: string) => a.split(/\s*(?:,|&| feat\.? | ft\.? | x | og | and )\s*/i)[0] || a;
const lik = (a: string, b: string) => { const x = norm(a), y = norm(b); return !!x && !!y && (x === y || x.startsWith(y + ' ') || y.startsWith(x + ' ')); };
const artLik = (a: string, b: string) => { const x = norm(hoved(a)), y = norm(hoved(b)); return !!x && !!y && (x.includes(y) || y.includes(x)); };

// Hva finnes i Navidrome? Huskes per låt/album (null = mangler), slås opp igjen etter en nedlasting.
const har = signal<Record<string, NdSong | NdAlbum | null>>({});
const sKey = (s: { tittel: string; artist: string }) => norm(s.artist) + '|' + norm(s.tittel);
let ko: (() => Promise<void>)[] = [], igang = 0;
const kjør = () => { while (igang < 3 && ko.length) { const f = ko.shift()!; igang++; void f().finally(() => { igang--; kjør(); }); } };
function sjekkSang(s: PopSang): void {
  const k = 's:' + sKey(s); if (k in har.value) return;
  har.value = { ...har.value, [k]: null };
  ko.push(async () => {
    try {
      const r = await ndSearch(norm(s.tittel) + ' ' + norm(hoved(s.artist)));
      const x = r.find((y) => lik(y.title, s.tittel) && artLik(y.artist, s.artist)) ?? null;
      har.value = { ...har.value, [k]: x };
    } catch { /* lar den stå som mangler */ }
  }); kjør();
}
function sjekkAlbum(a: PopAlbum): void {
  const k = 'a:' + sKey(a); if (k in har.value) return;
  har.value = { ...har.value, [k]: null };
  ko.push(async () => {
    try {
      const r = await ndSearchAll(norm(a.tittel));
      har.value = { ...har.value, [k]: r.albums.find((y) => lik(y.name, a.tittel) && artLik(y.artist, a.artist)) ?? null };
    } catch { /* mangler */ }
  }); kjør();
}

const bildeBg = (u: string) => u ? `url("${u.replace(/"/g, '')}") center / cover no-repeat, #1b1b1c` : '#1b1b1c';
const NED = 'M12 4v11M7 10l5 5 5-5M5 20h14';
const PLAY = 'M8 5v14l11-7z';
const Ik = ({ d, c = 'currentColor', fyll = false }: { d: string; c?: string; fyll?: boolean }) => <svg width="15" height="15" viewBox="0 0 24 24" fill={fyll ? c : 'none'} stroke={fyll ? 'none' : c} stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg>;

export function PopulaertSeksjon({ spill, apneAlbum, bred = false }: { spill: (l: NdSong[], i: number) => void; apneAlbum: (a: NdAlbum) => void; bred?: boolean }) {
  const p = periode.value;
  const [data, setData] = useState<Populaert | null>(lister[p] ?? null), [feil, setFeil] = useState(''), [flere, setFlere] = useState(false);
  useEffect(() => {
    setFlere(false); setFeil('');
    if (lister[p]) { setData(lister[p]!); return; }
    setData(null);
    let stop = false;
    api.populaert(p).then((r) => { lister[p] = r; if (!stop) setData(r); }).catch((e: unknown) => { if (!stop) setFeil(e instanceof Error ? e.message : String(e)); });
    return () => { stop = true; };
  }, [p]);
  // etter en nedlasting: se på nytt etter det som manglet
  useEffect(() => { if (ybNyttSok.value) { const h = { ...har.value }; for (const k in h) if (!h[k]) delete h[k]; har.value = h; } }, [ybNyttSok.value]);
  const sanger = (data?.sanger ?? []).slice(0, flere ? 50 : bred ? 10 : 8), album = (data?.album ?? []).slice(0, 20);
  useEffect(() => { sanger.forEach(sjekkSang); album.forEach(sjekkAlbum); }, [data, flere, har.value]);
  const yb = yubalPa(), H = har.value, Y = ybAlle.value;

  const trykkSang = (s: PopSang, i: number) => {
    const x = H['s:' + sKey(s)];
    if (x && 'title' in x) {   // spill de populære låtene du har, fra denne
      const mine = sanger.map((y) => H['s:' + sKey(y)]).filter((y): y is NdSong => !!y && 'title' in y);
      spill(mine, Math.max(0, mine.indexOf(x)));
      return;
    }
    if (yb && !ybAktiv(Y['sang:' + sKey(s)])) void ybLastNedSang('sang:' + sKey(s), s.tittel, s.artist, s.bilde);
    void i;
  };
  const trykkAlbum = (a: PopAlbum) => {
    const x = H['a:' + sKey(a)];
    if (x && 'name' in x) { apneAlbum(x); return; }
    if (yb && !ybAktiv(Y['album:' + sKey(a)])) void ybLastNedAlbum('album:' + sKey(a), { album: a.tittel, artist: a.artist, bilde: a.bilde });
  };
  const status = (key: string, finnes: boolean | undefined) => {
    const n = Y[key];
    if (finnes) return { t: 'I biblioteket', c: '#6fcf7f', ik: PLAY, fyll: true };
    if (n) return { t: ybTekst(n), c: n.status === 'failed' ? '#ff9a8a' : n.status === 'completed' ? '#6fcf7f' : '#f0c46a', ik: n.status === 'completed' ? PLAY : NED, fyll: n.status === 'completed' };
    return yb ? { t: 'Last ned', c: '#f0c46a', ik: NED, fyll: false } : { t: 'Ikke i biblioteket', c: '#6b6b67', ik: '', fyll: false };
  };

  return (
    <section style="display:flex;flex-direction:column;gap:14px;flex-shrink:0;min-width:0">
      <div style="display:flex;flex-direction:column;gap:2px">
        <span style={`font-family:${MONO};font-size:10px;letter-spacing:.14em;color:#8b8b86`}>POPULÆRT{data?.kilde ? ' · ' + data.kilde.toUpperCase() : ''}</span>
        <span style={`font-size:${bred ? 22 : 19}px;font-weight:600`}>{p === 'na' ? 'Populært akkurat nå' : 'Populært fra ' + (PERIODER.find((x) => x[0] === p)?.[1] ?? '')}</span>
      </div>
      <div class="dsc" style={`display:flex;gap:8px;overflow-x:auto;scrollbar-width:none;${bred ? '' : 'margin:0 -20px;padding:0 20px'}`}>
        {PERIODER.map(([id, n]) => <button key={id} onClick={() => { periode.value = id; }} style={`flex-shrink:0;height:34px;padding:0 14px;border-radius:17px;border:1px solid ${p === id ? '#f2f2ee' : '#2e2e30'};background:${p === id ? '#f2f2ee' : '#161617'};color:${p === id ? '#0b0b0c' : '#c9c9c4'};font-size:13px;font-weight:600;white-space:nowrap;cursor:pointer`}>{n}</button>)}
      </div>
      {!data && <span style="font-size:13px;color:#8b8b86">{feil ? 'Fikk ikke hentet listene: ' + feil : 'Henter listene …'}</span>}
      {data && sanger.length > 0 && <div style={`display:grid;grid-template-columns:${bred ? 'repeat(2,minmax(0,1fr))' : 'minmax(0,1fr)'};column-gap:20px;row-gap:2px`}>
        {sanger.map((s, i) => {
          const fin = H['s:' + sKey(s)], st = status('sang:' + sKey(s), !!fin);
          return (
            <button key={i} onClick={() => trykkSang(s, i)} title={st.t} style="display:grid;grid-template-columns:26px 46px minmax(0,1fr) auto;gap:10px;align-items:center;min-height:56px;padding:4px 6px;border:none;border-radius:10px;background:transparent;color:inherit;text-align:left;cursor:pointer;min-width:0">
              <span style={`font-family:${MONO};font-size:12px;color:#8b8b86;text-align:right`}>{i + 1}</span>
              <span style={`width:46px;height:46px;border-radius:6px;background:${bildeBg(s.bilde)};opacity:${fin ? 1 : 0.75}`} />
              <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><b style="font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.tittel}</b><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.artist}{s.aar && p !== 'na' ? ' · ' + s.aar : ''}</span></span>
              <span style={`display:flex;align-items:center;gap:6px;font-size:11.5px;color:${st.c};white-space:nowrap;max-width:${bred ? 170 : 120}px;overflow:hidden;text-overflow:ellipsis`}>{st.ik && <Ik d={st.ik} c={st.c} fyll={st.fyll} />}{bred || !fin ? <span style="overflow:hidden;text-overflow:ellipsis">{st.t}</span> : null}</span>
            </button>);
        })}
      </div>}
      {data && (data.sanger.length > sanger.length || flere) && <button onClick={() => setFlere(!flere)} style="align-self:flex-start;height:34px;padding:0 14px;border-radius:17px;border:1px solid #2e2e30;background:#161617;color:#c9c9c4;font-size:13px;cursor:pointer">{flere ? 'Vis færre' : 'Vis alle ' + Math.min(50, data.sanger.length)}</button>}
      {data && album.length > 0 && <>
        <span style="font-size:16px;font-weight:600;margin-top:4px">Populære album</span>
        <div class="dsc" style={`display:flex;gap:14px;overflow-x:auto;scrollbar-width:none;${bred ? '' : 'margin:0 -20px;padding:0 20px'}`}>
          {album.map((a, i) => {
            const fin = H['a:' + sKey(a)], st = status('album:' + sKey(a), !!fin);
            return (
              <button key={i} onClick={() => trykkAlbum(a)} title={st.t} style={`display:flex;flex-direction:column;gap:5px;width:${bred ? 160 : 136}px;flex-shrink:0;border:none;background:none;padding:0;color:inherit;text-align:left;cursor:pointer`}>
                <span style={`position:relative;width:100%;aspect-ratio:1;border-radius:10px;background:${bildeBg(a.bilde)}`}>
                  {st.ik && <span style={`position:absolute;right:8px;bottom:8px;width:32px;height:32px;border-radius:50%;background:rgba(11,11,12,.78);display:flex;align-items:center;justify-content:center`}><Ik d={st.ik} c={fin ? '#f2f2ee' : st.c} fyll={st.fyll} /></span>}
                </span>
                <span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{a.tittel}</span>
                <span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{a.artist}</span>
                <span style={`font-size:11px;color:${st.c};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{fin ? 'I biblioteket' : st.t === 'Last ned' ? 'Last ned albumet' : st.t}</span>
              </button>);
          })}
        </div>
      </>}
    </section>
  );
}
