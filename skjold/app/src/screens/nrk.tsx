// NRK Radio på forespørsel og podkaster (/api/nrk/*): søk, serier med episoder, «fortsett der du slapp».
import { signal } from '@preact/signals';
import { useEffect, useState } from 'preact/hooks';
import { api, type NrkEpisode, type NrkProg, type NrkSeries } from '../lib/api';
import { showToast, trackSub } from '../lib/store';
import { art } from '../lib/settings';

const MONO = "'IBM Plex Mono',monospace";
const nrkOpen = signal<NrkSeries | null>(null);
trackSub(nrkOpen, () => { nrkOpen.value = null; });
const nrkQ = signal('');
export const nrkContinue = signal<NrkProg[]>([]);

export async function loadNrkContinue(): Promise<void> {
  try { nrkContinue.value = (await api.nrkContinue()).items; } catch { /* daemon uten NRK-støtte */ }
}

const mins = (s: number) => (s >= 3600 ? Math.floor(s / 3600) + ' t ' : '') + Math.round((s % 3600) / 60) + ' min';

async function playEp(e: NrkEpisode | NrkProg, restart = false) {
  try {
    const r = await api.nrkPlay({ id: e.id, title: e.title, series: e.series, image: e.image, duration: 'duration' in e ? e.duration : e.dur, podcast: 'podcast' in e ? e.podcast : undefined, restart });
    showToast(r.resume ? 'Fortsetter fra ' + mins(r.resume) : 'Spiller ' + (e.title || ''));
    void loadNrkContinue();
  } catch (err) { showToast(err instanceof Error ? err.message : String(err)); }
}

function Img({ src, name, size, radius = 12 }: { src?: string; name: string; size: number; radius?: number }) {
  const a = art(name, src);
  return <div style={{ width: size + 'px', height: size + 'px', borderRadius: radius + 'px', background: a.bg, flexShrink: 0 }} />;
}

function Bar({ pos, dur }: { pos?: number; dur?: number }) {
  if (!pos || !dur) return null;
  return <div style="height:3px;border-radius:2px;background:#2e2e30;overflow:hidden;width:100%"><i style={`display:block;height:100%;width:${Math.min(100, (pos / dur) * 100)}%;background:#d9a441`} /></div>;
}

function EpRow({ e }: { e: NrkEpisode }) {
  return (
    <div style="display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:12px;align-items:center;padding:8px;border-radius:12px;background:#121214">
      <Img src={e.image} name={e.series || e.title} size={52} radius={10} />
      <button onClick={() => void playEp(e)} style="border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;min-width:0;display:flex;flex-direction:column;gap:3px">
        <span style={`font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:${e.heard ? '#8b8b86' : '#f2f2ee'}`}>{e.title}</span>
        <span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{[e.date, e.duration ? mins(e.duration) : '', e.heard ? 'Hørt' : e.pos ? 'Fortsett' : ''].filter(Boolean).join(' · ')}</span>
        <Bar pos={e.pos} dur={e.duration} />
      </button>
      {e.pos ? <button title="Spill fra start" onClick={() => void playEp(e, true)} style="height:32px;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:transparent;color:#c9c9c4;cursor:pointer;font-size:12px">Fra start</button> : <span />}
    </div>
  );
}

function SeriesTile({ s }: { s: NrkSeries }) {
  return (
    <button onClick={() => (nrkOpen.value = s)} style="display:flex;flex-direction:column;gap:6px;border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;width:148px;flex-shrink:0">
      <Img src={s.image} name={s.title} size={148} />
      <span style="font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.title}</span>
      <span style={`font-family:${MONO};font-size:10px;letter-spacing:.08em;color:#8b8b86`}>{s.kind === 'podcast' ? 'PODKAST' : 'PROGRAM'}</span>
    </button>
  );
}

function SeriesPage({ s }: { s: NrkSeries }) {
  const [d, setD] = useState<(NrkSeries & { episodes: NrkEpisode[] }) | null>(null);
  const [err, setErr] = useState('');
  useEffect(() => { setD(null); setErr(''); api.nrkSeries(s.id, s.kind).then(setD).catch((e) => setErr(e instanceof Error ? e.message : String(e))); }, [s.id]);
  const h = d ?? s;
  return (
    <div class="col gap16">
      <button onClick={() => (nrkOpen.value = null)} style="align-self:flex-start;border:none;background:none;color:#d9a441;cursor:pointer;padding:0;font-size:13px">‹ Tilbake</button>
      <div style="display:flex;gap:18px;align-items:flex-end;flex-wrap:wrap">
        <Img src={h.image} name={h.title} size={160} />
        <div class="col gap6" style={{ minWidth: 0, maxWidth: '520px' }}>
          <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.12em;color:#8b8b86`}>NRK · {h.kind === 'podcast' ? 'PODKAST' : 'PROGRAM'}</span>
          <span style="font-size:26px;font-weight:600;line-height:1.15">{h.title}</span>
          {h.subtitle && <span style="font-size:13px;color:#a9a9a3;line-height:1.5">{h.subtitle}</span>}
        </div>
      </div>
      {err && <span style="color:#ff8a7a;font-size:13px">{err}</span>}
      {!d && !err && <span style="color:#8b8b86;font-size:13px">Henter episoder …</span>}
      {d && <div class="col gap8">{d.episodes.map((e) => <EpRow key={e.id} e={e} />)}</div>}
      {d && !d.episodes.length && <span style="color:#8b8b86;font-size:13px">Ingen episoder tilgjengelig akkurat nå.</span>}
    </div>
  );
}

/** «Fortsett å lytte» (NRK) – brukes på Hjem og øverst i NRK-fanen. */
export function NrkContinueShelf() {
  useEffect(() => { void loadNrkContinue(); }, []);
  const items = Array.isArray(nrkContinue.value) ? nrkContinue.value : [];
  if (!items.length) return null;
  return (
    <div class="col gap10">
      <span style="font-size:17px;font-weight:600">Fortsett å lytte</span>
      <div class="hscroll">
        {items.map((p) => (
          <button key={p.id} onClick={() => void playEp(p)} style="display:flex;flex-direction:column;gap:6px;border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;width:148px;flex-shrink:0">
            <Img src={p.image} name={p.series || p.title || 'NRK'} size={148} />
            <span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{p.title || 'Episode'}</span>
            <span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{p.series || 'NRK'}</span>
            <Bar pos={p.pos} dur={p.dur} />
          </button>
        ))}
      </div>
    </div>
  );
}

/** NRK-fanen på Radio-siden: «Program og podkaster». */
export function NrkPanel() {
  const [pop, setPop] = useState<NrkSeries[] | null>(null);
  const [res, setRes] = useState<{ series: NrkSeries[]; episodes: NrkEpisode[] } | null>(null);
  const [err, setErr] = useState('');
  const q = nrkQ.value.trim();
  useEffect(() => { api.nrkPopular().then((r) => setPop(r.series)).catch((e) => { setPop([]); setErr(e instanceof Error ? e.message : String(e)); }); }, []);
  useEffect(() => {
    if (!q) { setRes(null); return; }
    const t = setTimeout(() => { api.nrkSearch(q).then((r) => { setRes(r); setErr(''); }).catch((e) => setErr(e instanceof Error ? e.message : String(e))); }, 350);
    return () => clearTimeout(t);
  }, [q]);
  if (nrkOpen.value) return <SeriesPage s={nrkOpen.value} />;
  return (
    <div class="col gap20">
      <input value={nrkQ.value} onInput={(e) => (nrkQ.value = (e.currentTarget as HTMLInputElement).value)} placeholder="Søk i NRK-program og podkaster" style="height:42px;max-width:420px;width:100%;padding:0 14px;border-radius:10px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;font-size:14px;outline:none" />
      {err && <span style="color:#ff8a7a;font-size:13px">{err}</span>}
      {q ? (res ? (
        <div class="col gap20">
          {res.series.length > 0 && <div class="col gap10"><span style="font-size:17px;font-weight:600">Program og podkaster</span><div class="hscroll">{res.series.map((s) => <SeriesTile key={s.id} s={s} />)}</div></div>}
          {res.episodes.length > 0 && <div class="col gap8"><span style="font-size:17px;font-weight:600">Episoder</span>{res.episodes.map((e) => <EpRow key={e.id} e={e} />)}</div>}
          {!res.series.length && !res.episodes.length && <span style="color:#8b8b86;font-size:13px">Fant ingenting hos NRK.</span>}
        </div>
      ) : <span style="color:#8b8b86;font-size:13px">Søker …</span>) : (
        <>
          <NrkContinueShelf />
          {pop && pop.length > 0 && <div class="col gap10"><span style="font-size:17px;font-weight:600">Populært hos NRK</span><div class="hscroll">{pop.map((s) => <SeriesTile key={s.id} s={s} />)}</div></div>}
          {pop && !pop.length && !err && <span style="color:#8b8b86;font-size:13px">Søk etter et program eller en podkast, for eksempel «Abels tårn» eller «Nitimen».</span>}
        </>
      )}
    </div>
  );
}
