// Podkaster (/api/pod/*): alle offentlige podkaster (Apple Podcasts-katalogen), NRK og egne RSS-adresser.
// Favorittene lagres på enheten og vises også på Skjold Touch. Episoder fortsetter der du slapp.
import { signal } from '@preact/signals';
import { useEffect, useState } from 'preact/hooks';
import { api, type NrkSeries, type PodEpisode, type PodProg, type PodShow } from '../lib/api';
import { showToast, trackSub } from '../lib/store';
import { art } from '../lib/settings';
import { NrkContinueShelf } from './nrk';

const MONO = "'IBM Plex Mono',monospace";
const podOpen = signal<PodShow | null>(null);
trackSub(podOpen, () => { podOpen.value = null; });
const podQ = signal('');
const genre = signal(0);
export const podFavs = signal<PodShow[] | null>(null);

export async function loadPodFavs(): Promise<void> {
  try { podFavs.value = (await api.podFavs()).items; } catch { podFavs.value = []; }
}

const mins = (s: number) => (s >= 3600 ? Math.floor(s / 3600) + ' t ' : '') + Math.round((s % 3600) / 60) + ' min';
const SRC_TXT: Record<string, string> = { apple: 'PODKAST', nrk: 'NRK', rss: 'RSS' };
const err2 = (e: unknown) => (e instanceof Error ? e.message : String(e));

export async function playPodEp(e: PodEpisode | PodProg, show?: { id?: string; title?: string; image?: string }, restart = false): Promise<void> {
  try {
    const ep = e as PodEpisode;
    const r = ep.nrk
      ? await api.nrkPlay({ id: ep.id, title: ep.title, series: ep.show, image: ep.image, duration: ep.duration, podcast: ep.podcast, restart })
      : await api.podPlay({ id: e.id, url: e.url ?? '', title: e.title, show: show?.title ?? ep.show ?? (e as PodProg).series, image: e.image || show?.image,
        duration: 'duration' in e ? ep.duration : (e as PodProg).dur, pid: show?.id ?? e.pid, restart });
    showToast(r.resume ? 'Fortsetter fra ' + mins(r.resume) : 'Spiller ' + (e.title || ''));
  } catch (x) { showToast(err2(x)); }
}

export async function toggleFav(s: PodShow, on: boolean): Promise<void> {
  try {
    podFavs.value = (await api.podFav(on ? { add: { id: s.id, title: s.title, author: s.author, image: s.image, kind: s.kind } } : { remove: s.id })).items;
    showToast(on ? 'Lagt til i favorittene – vises også på Skjold Touch' : 'Fjernet fra favorittene');
  } catch (x) { showToast(err2(x)); }
}

function Img({ src, name, size, radius = 12 }: { src?: string; name: string; size: number | string; radius?: number }) {
  const a = art(name, src);
  const sz = typeof size === 'number' ? size + 'px' : size;
  return <div style={{ width: sz, height: typeof size === 'number' ? sz : undefined, aspectRatio: '1', borderRadius: radius + 'px', background: a.bg, flexShrink: 0 }} />;
}

function Bar({ pos, dur }: { pos?: number; dur?: number }) {
  if (!pos || !dur) return null;
  return <div style="height:3px;border-radius:2px;background:#2e2e30;overflow:hidden;width:100%"><i style={`display:block;height:100%;width:${Math.min(100, (pos / dur) * 100)}%;background:#d9a441`} /></div>;
}

const Heart = ({ on }: { on: boolean }) => <svg width="18" height="18" viewBox="0 0 24 24" fill={on ? '#d9a441' : 'none'} stroke={on ? '#d9a441' : 'currentColor'} stroke-width="1.9" stroke-linejoin="round"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" /></svg>;

function Tile({ s, w }: { s: PodShow; w?: number }) {
  return (
    <button onClick={() => (podOpen.value = s)} style={`display:flex;flex-direction:column;gap:6px;border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;min-width:0;${w ? `width:${w}px;flex-shrink:0` : 'width:100%'}`}>
      <Img src={s.image} name={s.title} size={w ?? '100%'} />
      <span style="font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.title}</span>
      <span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{s.author || SRC_TXT[s.src] || ''}</span>
    </button>
  );
}

function EpRow({ e, show }: { e: PodEpisode; show?: PodShow }) {
  return (
    <div style="display:grid;grid-template-columns:52px minmax(0,1fr) auto;gap:12px;align-items:center;padding:8px;border-radius:12px;background:#121214">
      <Img src={e.image} name={e.show || e.title} size={52} radius={10} />
      <button onClick={() => void playPodEp(e, show)} style="border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;min-width:0;display:flex;flex-direction:column;gap:3px">
        <span style={`font-size:14px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;color:${e.heard ? '#8b8b86' : '#f2f2ee'}`}>{e.title}</span>
        <span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{[show ? '' : e.show, e.date, e.duration ? mins(e.duration) : '', e.heard ? 'Hørt' : e.pos ? 'Fortsett' : ''].filter(Boolean).join(' · ')}</span>
        <Bar pos={e.pos} dur={e.duration} />
      </button>
      {e.pos ? <button title="Spill fra start" onClick={() => void playPodEp(e, show, true)} style="height:32px;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:transparent;color:#c9c9c4;cursor:pointer;font-size:12px">Fra start</button> : <span />}
    </div>
  );
}

function ShowPage({ s }: { s: PodShow }) {
  const [d, setD] = useState<(PodShow & { description: string; fav: boolean; episodes: PodEpisode[] }) | null>(null);
  const [err, setErr] = useState('');
  const [n, setN] = useState(40);
  useEffect(() => { setD(null); setErr(''); setN(40); api.podShow(s.id).then(setD).catch((e) => setErr(err2(e))); }, [s.id]);
  const h = d ?? s;
  const fav = (podFavs.value ?? []).some((x) => x.id === s.id);
  const first = d?.episodes[0];
  return (
    <div class="col gap16">
      <button onClick={() => (podOpen.value = null)} style="align-self:flex-start;border:none;background:none;color:#d9a441;cursor:pointer;padding:0;font-size:13px">‹ Tilbake</button>
      <div style="display:flex;gap:18px;align-items:flex-end;flex-wrap:wrap">
        <Img src={h.image} name={h.title} size={160} />
        <div class="col gap6" style={{ minWidth: 0, maxWidth: '560px', flex: '1 1 260px' }}>
          <span style={`font-family:${MONO};font-size:10.5px;letter-spacing:.12em;color:#8b8b86`}>{SRC_TXT[s.src] ?? 'PODKAST'}{h.author && s.src !== 'nrk' ? ' · ' + h.author.toUpperCase() : ''}</span>
          <span style="font-size:26px;font-weight:600;line-height:1.15">{h.title}</span>
          {d?.description && <span style="font-size:13px;color:#a9a9a3;line-height:1.5;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden">{d.description}</span>}
          <div style="display:flex;gap:8px;margin-top:6px;flex-wrap:wrap">
            {first && <button onClick={() => void playPodEp(first, h)} style="height:38px;padding:0 16px;border-radius:999px;border:none;background:#f2f2ee;color:#0b0b0c;font-size:13px;font-weight:600;cursor:pointer">Spill nyeste</button>}
            <button onClick={() => void toggleFav({ ...s, title: h.title, image: h.image, author: h.author }, !fav)} aria-pressed={fav}
              style={`height:38px;padding:0 14px;border-radius:999px;border:1px solid ${fav ? '#d9a441' : '#2e2e30'};background:${fav ? '#1c170d' : 'transparent'};color:${fav ? '#f0c46a' : '#f2f2ee'};font-size:13px;cursor:pointer;display:flex;align-items:center;gap:8px`}>
              <Heart on={fav} />{fav ? 'Favoritt' : 'Legg til i favoritter'}</button>
          </div>
        </div>
      </div>
      {err && <span style="color:#ff8a7a;font-size:13px">{err}</span>}
      {!d && !err && <span style="color:#8b8b86;font-size:13px">Henter episoder …</span>}
      {d && <div class="col gap8">{d.episodes.slice(0, n).map((e) => <EpRow key={e.id} e={e} show={h} />)}</div>}
      {d && d.episodes.length > n && <button onClick={() => setN(n + 60)} style="align-self:flex-start;height:36px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:13px;cursor:pointer">Vis flere episoder ({d.episodes.length - n})</button>}
      {d && !d.episodes.length && <span style="color:#8b8b86;font-size:13px">Ingen episoder tilgjengelig akkurat nå.</span>}
    </div>
  );
}

const H = ({ t, sub }: { t: string; sub?: string }) => <div style="display:flex;align-items:baseline;gap:10px;flex-wrap:wrap"><span style="font-size:17px;font-weight:600">{t}</span>{sub && <span style="font-size:12px;color:#8b8b86">{sub}</span>}</div>;

/** Radio → «Podkaster»: søk i alle podkaster, favoritter, nye episoder, topplister per sjanger og NRK. */
export function PodPanel() {
  const [genres, setGenres] = useState<{ id: number; name: string }[]>([]);
  const [top, setTop] = useState<PodShow[] | null>(null);
  const [nye, setNye] = useState<PodEpisode[] | null>(null);
  const [cont, setCont] = useState<PodProg[]>([]);
  const [nrkPop, setNrkPop] = useState<NrkSeries[]>([]);
  const [res, setRes] = useState<PodShow[] | null>(null);
  const [err, setErr] = useState('');
  const q = podQ.value.trim();
  const favs = podFavs.value ?? [];
  useEffect(() => {
    void loadPodFavs();
    api.podGenres().then((r) => setGenres(r.genres)).catch(() => {});
    api.podContinue().then((r) => setCont(r.items)).catch(() => {});
    api.nrkPopular().then((r) => setNrkPop(r.series)).catch(() => {});
  }, []);
  useEffect(() => { if (podFavs.value !== null) api.podNew().then((r) => setNye(r.items)).catch(() => setNye([])); }, [favs.map((f) => f.id).join()]);
  useEffect(() => { setTop(null); api.podTop(genre.value).then((r) => { setTop(r.shows); setErr(''); }).catch((e) => { setTop([]); setErr(err2(e)); }); }, [genre.value]);
  useEffect(() => {
    if (!q) { setRes(null); return; }
    const t = setTimeout(() => { setRes(null); api.podSearch(q).then((r) => { setRes(r.shows); setErr(''); }).catch((e) => { setRes([]); setErr(err2(e)); }); }, 400);
    return () => clearTimeout(t);
  }, [q]);
  if (podOpen.value) return <ShowPage s={podOpen.value} />;
  const GRID = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));gap:18px 14px';
  return (
    <div class="col gap24">
      <input value={podQ.value} onInput={(e) => (podQ.value = (e.currentTarget as HTMLInputElement).value)} placeholder="Søk i alle podkaster – eller lim inn en RSS-adresse"
        style="height:42px;max-width:520px;width:100%;padding:0 14px;border-radius:10px;border:1px solid #2e2e30;background:#141415;color:#f2f2ee;font-size:14px;outline:none" />
      {err && <span style="color:#ff8a7a;font-size:13px">{err}</span>}
      {q ? (res ? (res.length ? <div class="col gap10"><H t="Treff" sub={res.length + ' podkaster fra Apple Podcasts-katalogen og NRK'} /><div style={GRID}>{res.map((s) => <Tile key={s.id} s={s} />)}</div></div>
        : <span style="color:#8b8b86;font-size:13px">Fant ingen podkaster.</span>) : <span style="color:#8b8b86;font-size:13px">Søker …</span>) : (
        <>
          <div class="col gap10">
            <H t="Favoritter" sub={favs.length ? 'Vises også på Skjold Touch' : undefined} />
            {favs.length ? <div class="hscroll">{favs.slice().reverse().map((s) => <Tile key={s.id} s={s} w={132} />)}</div>
              : <span style="color:#8b8b86;font-size:13px">Ingen favoritter ennå. Åpne en podkast og trykk ♡ «Legg til i favoritter».</span>}
          </div>
          {!!nye?.length && <div class="col gap8"><H t="Nye episoder" sub="Fra favorittene dine" />{nye.slice(0, 8).map((e) => <EpRow key={e.id} e={e} />)}</div>}
          {cont.length > 0 && (
            <div class="col gap10"><H t="Fortsett å lytte" />
              <div class="hscroll">{cont.map((p) => (
                <button key={p.id} onClick={() => void playPodEp(p)} style="display:flex;flex-direction:column;gap:6px;border:none;background:none;padding:0;text-align:left;cursor:pointer;color:inherit;width:132px;flex-shrink:0">
                  <Img src={p.image} name={p.series || p.title || 'Podkast'} size={132} />
                  <span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{p.title || 'Episode'}</span>
                  <span style="font-size:11.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{p.series || ''}</span>
                  <Bar pos={p.pos} dur={p.dur} />
                </button>))}</div>
            </div>)}
          <NrkContinueShelf />
          <div class="col gap10">
            <H t="Topplisten" sub="Mest lyttet i Norge akkurat nå" />
            <div class="hscroll" style="gap:6px">
              {genres.map((g) => { const on = genre.value === g.id; return <button key={g.id} onClick={() => (genre.value = g.id)} style={`height:34px;padding:0 14px;border-radius:999px;border:1px solid ${on ? '#f2f2ee' : '#2e2e30'};background:${on ? '#f2f2ee' : 'transparent'};color:${on ? '#0b0b0c' : '#c9c9c4'};font-size:12.5px;cursor:pointer;white-space:nowrap;flex-shrink:0`}>{g.name}</button>; })}
            </div>
            {top === null ? <span style="color:#8b8b86;font-size:13px">Henter topplisten …</span> : <div style={GRID}>{top.slice(0, 60).map((s, i) => <div key={s.id} style="position:relative;min-width:0"><Tile s={s} /><span style={`position:absolute;left:6px;top:6px;min-width:22px;height:20px;padding:0 5px;border-radius:6px;background:rgba(11,11,12,.78);font-family:${MONO};font-size:10px;color:#f2f2ee;display:flex;align-items:center;justify-content:center;box-sizing:border-box`}>{i + 1}</span></div>)}</div>}
          </div>
          {nrkPop.length > 0 && <div class="col gap10"><H t="Fra NRK" /><div class="hscroll">{nrkPop.map((s) => <Tile key={s.id} s={{ id: 'nrk:' + s.id, title: s.title, author: 'NRK', image: s.image, src: 'nrk', kind: s.kind }} w={132} />)}</div></div>}
        </>
      )}
    </div>
  );
}
