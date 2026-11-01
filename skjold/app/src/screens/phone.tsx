// Telefon (Skjold App v2): Hjem, fullskjermspiller med kø, og Rom («Ditt system»). Malen er portert 1:1 fra
// designfilen (samme mål, farger og tekster); dataene kommer fra forsterkeren (/api/status, /api/presets).
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, getBase, PRODUCT_HW, PRODUCT_LABEL, productOf, setBase, type InputId, type Product, type Status } from '../lib/api';
import { act, deviceName, eqActiveProfile, go, inputLabel, loadSettings, mode, online, openFull, closeFull, playPause, product, queueOpen, reconnect, recent, setVolume, showToast, srcOpen, status } from '../lib/store';
import { knownDevices } from '../lib/discover';
import { art } from '../lib/settings';
import { PRODUCT_ICON, SrcCircle, Slider } from '../components/ui';
import { favs, favsLoaded, loadFavs, playFav } from '../lib/radio';
import { groups, groupAll, groupCount, groupNone, inGroup, ROLES, setMode, setRole, toggleMember } from '../lib/groups';
import { fmtDur, libNext, li, lq, lsvc, playNd } from '../lib/library';
import { ndCover } from '../lib/navidrome';
import { artFor, mmss, nowTitle } from './player';
import { useTick, nbHw } from './pages';

const A = '#d9a441';
const sel = (b: boolean) => ({ bd: b ? A : '#2e2e30', bg: b ? '#1c170d' : '#141415', fg: b ? '#f0c46a' : '#f2f2ee' });

// ---------- rom (denne forsterkeren + andre appen kjenner) ----------
export interface Room { key: string; base: string; name: string; product: Product; st: Status | null; active: boolean }
export const activeKey = (): string => getBase() || location.origin;
export function useRooms(): Room[] {
  const s = status.value, cur = getBase();
  const [others, setOthers] = useState<Record<string, Status | null>>({});
  const known = knownDevices().filter((d) => d.base !== cur && d.base !== location.origin && d.base.replace(/^https?:\/\//, '') !== location.host);
  const knownKey = known.map((d) => d.base).join(',');
  useEffect(() => {
    if (!known.length) return undefined;
    let stop = false;
    const poll = async () => {
      const res: Record<string, Status | null> = {};
      await Promise.all(known.map(async (d) => { try { res[d.base] = await api.statusAt(d.base, 2500); } catch { res[d.base] = null; } }));
      if (!stop) setOthers(res);
    };
    void poll(); const t = window.setInterval(poll, 5000);
    return () => { stop = true; clearInterval(t); };
  }, [knownKey]);
  return [
    { key: activeKey(), base: cur, name: deviceName.value, product: product.value, st: s, active: true },
    ...known.map((d) => { const st = others[d.base] ?? null; return { key: d.base, base: d.base, name: st?.name || d.name, product: productOf(st ?? { board: '', product: d.product ?? '' }), st, active: false }; })
  ];
}
export async function switchRoom(base: string): Promise<void> { setBase(base); reconnect(); await loadSettings(); }
export function groupLabel(): string { const n = groupCount(activeKey()); return deviceName.value + (n > 1 ? ' + ' + (n - 1) : ''); }

// ---------- Hjem ----------
type Svc = [string, () => void];
export function HomePhone() {
  const s = status.value, p = product.value;
  useEffect(() => { if (!favsLoaded.value) void loadFavs(); }, []);
  const inputs = s?.inputs?.length ? s.inputs : (['airplay', 'bt', 'spotify', 'radio', 'aux', 'aux2', 'usb'] as InputId[]);
  const pick = (id: InputId) => { void act(() => api.input(id), { input: id }); openFull(); };
  const lyrion = () => { const h = (getBase() || location.origin).replace(/:\d+$/, ''); window.open(h + ':9000/', '_blank'); };
  const services: Svc[] = [
    ['Radio', () => go('radio')],
    ...(inputs.includes('airplay') ? [['AirPlay', () => pick('airplay')] as Svc] : []),
    ...(inputs.includes('bt') ? [['Blåtann', () => pick('bt')] as Svc] : []),
    ['Spotify', () => (inputs.includes('spotify') ? pick('spotify') : go('settings', 'tjenester'))],
    ['UPnP/DLNA', () => go('settings', 'tjenester')],
    ['YT Music', () => go('lib', 'ytm')],
    ['Navidrome', () => go('lib', 'nd')],
    ['Lyrion', lyrion],
    ...(inputs.includes('aux') ? [['AUX', () => pick('aux')] as Svc] : []),
    ...(inputs.includes('usb') ? [['USB', () => pick('usb')] as Svc] : [])
  ];
  const rc = recent.value.slice(0, 8);
  return (
    <>
      <div style="display:flex;align-items:center;justify-content:space-between;flex-shrink:0">
        <div style="display:flex;align-items:center;gap:9px"><div style="display:flex;align-items:flex-end;gap:2px;height:16px">{[8, 12, 16, 12, 8].map((h, i) => <div key={i} style={`width:2.5px;height:${h}px;background:#f2f2ee;border-radius:2px`} />)}</div><span style="font-weight:600;font-size:15px;letter-spacing:0.12em">SKJOLD</span></div>
        <button onClick={() => go('rooms')} style="display:flex;align-items:center;gap:6px;height:32px;padding:0 12px;border-radius:999px;border:1px solid #2e2e30;background:#141415;font-size:12px;cursor:pointer;white-space:nowrap;max-width:60%;overflow:hidden"><div style={`width:6px;height:6px;border-radius:50%;flex-shrink:0;background:${online.value ? '#6fcf7f' : '#e05a4a'}`} /><span style="overflow:hidden;text-overflow:ellipsis">{groupLabel()}</span></button>
      </div>
      <button onClick={() => go('rooms')} data-testid="device-card" style="flex-shrink:0;display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:12px;align-items:center;padding:14px;border-radius:14px;border:1px solid #242426;background:#141415;cursor:pointer;text-align:left;box-sizing:border-box;width:100%">
        <div style="width:44px;height:44px;border-radius:12px;background:#1c170d;border:1px solid #5a4420;color:#f0c46a;display:flex;align-items:center;justify-content:center;box-sizing:border-box"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[p]} /></svg></div>
        <div style="display:flex;flex-direction:column;gap:2px;min-width:0">
          <span style="font-size:15px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{deviceName.value}</span>
          <span style="font-size:12px;color:#f0c46a;font-weight:600">{PRODUCT_LABEL[p]}</span>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;line-height:1.45;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:2px">{nbHw(PRODUCT_HW[p])}</span>
        </div>
        <span style="height:28px;padding:0 12px;border-radius:999px;border:1px solid #2e2e30;font-size:12px;color:#c9c9c4;display:flex;align-items:center">Bytt</span>
      </button>
      {rc.length > 0 && (
        <div style="display:flex;flex-direction:column;gap:10px">
          <span style="font-size:17px;font-weight:600">Nylig spilt</span>
          <div class="dsc" style="display:flex;gap:12px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px">
            {rc.map((x) => {
              const a = art(x.title, x.image);
              return (
                <button key={x.key} onClick={() => {
                  if (x.station) { const f = favs.value.find((f) => f.title === x.title); if (f) playFav(f); else if (x.url) void act(() => api.radioPlay({ url: x.url!, title: x.title }), { input: 'radio' }); else { go('radio'); return; } }
                  else void act(() => api.input(x.input), { input: x.input });
                  openFull();
                }} style="display:flex;flex-direction:column;gap:6px;width:118px;flex-shrink:0;border:none;background:none;padding:0;cursor:pointer;text-align:left">
                  <div style={`width:118px;height:118px;border-radius:${x.station ? '50%' : '10px'};background:${a.bg};display:flex;align-items:flex-end;padding:10px;box-sizing:border-box;color:${a.ink};font-size:14px;font-weight:600;line-height:1.05;overflow:hidden`}>{a.logo ? '' : x.big}</div>
                  <span style="font-size:13px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{x.title}</span>
                  <span style="font-size:11px;color:#8b8b86">{x.kind}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
      <div style="display:flex;flex-direction:column;gap:10px">
        <span style="font-size:17px;font-weight:600">Kilder</span>
        <div class="dsc" style="display:flex;gap:14px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px" data-testid="inputs">
          {services.map(([label, fn]) => (
            <button key={label} onClick={fn} style="display:flex;flex-direction:column;align-items:center;gap:6px;border:none;background:none;padding:0;cursor:pointer;flex-shrink:0">
              <SrcCircle label={label} />
              <span style="font-size:11px;color:#c9c9c4">{label === 'AUX' ? inputLabel('aux') : label}</span>
            </button>
          ))}
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;justify-content:space-between;align-items:baseline"><span style="font-size:17px;font-weight:600">Radiofavoritter</span><button onClick={() => go('radio')} style="border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:0">Administrer</button></div>
        {favs.value.length ? (
          <div class="dsc" style="display:flex;gap:12px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px">
            {favs.value.map((f) => {
              const a = art(f.title, f.image);
              return (
                <button key={f.n} onClick={() => { playFav(f); openFull(); }} style="display:flex;flex-direction:column;gap:6px;width:96px;flex-shrink:0;border:none;background:none;padding:0;cursor:pointer;text-align:left">
                  <div style={`width:96px;height:96px;border-radius:12px;background:${a.bg};display:flex;flex-direction:column;justify-content:space-between;padding:9px;box-sizing:border-box;color:${a.ink}`}><span style="font-family:'IBM Plex Mono',monospace;font-size:9px;opacity:.8">{f.n}</span><span style="font-size:13px;font-weight:600;line-height:1.05">{a.logo ? '' : f.title}</span></div>
                  <span style="font-size:11px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{f.genre || f.title}</span>
                </button>
              );
            })}
          </div>
        ) : favsLoaded.value ? <button onClick={() => go('radio')} style="height:46px;border-radius:14px;border:1px dashed #5a4420;background:transparent;color:#f0c46a;font-size:13px;cursor:pointer">Legg til radiokanal</button> : null}
      </div>
    </>
  );
}

// ---------- minispiller ----------
export function MiniPhone() {
  const s = status.value, t = nowTitle(s), a = artFor(s);
  return (
    <div style="margin:0 10px 8px;border-radius:14px;background:#1b1b1d;border:1px solid #2a2a2c;display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:10px;align-items:center;padding:8px;flex-shrink:0">
      <button onClick={openFull} aria-label="Åpne spilleren" style={`width:44px;height:44px;border-radius:8px;border:none;background:${a.bg};cursor:pointer;padding:0`} />
      <button onClick={openFull} data-testid="mini" style="border:none;background:none;cursor:pointer;text-align:left;padding:0;display:flex;flex-direction:column;gap:1px;min-width:0">
        <span style="font-family:'IBM Plex Mono',monospace;font-size:9.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{groupLabel()} · {PRODUCT_LABEL[product.value]}</span>
        <span style="font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t.title}</span>
        <span style="font-size:11px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{t.album ? [t.sub, t.album].filter(Boolean).join(' · ') : t.sub}</span>
      </button>
      <button onClick={playPause} aria-label="Spill/pause" data-testid="mini-pp" style="width:40px;height:40px;border-radius:50%;border:none;background:transparent;color:#f2f2ee;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0"><PP playing={!!s?.playing} size={22} /></button>
    </div>
  );
}
function PP({ playing, size }: { playing: boolean; size: number }) {
  return playing ? <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4.5" width="4" height="15" rx="1.2" /><rect x="14" y="4.5" width="4" height="15" rx="1.2" /></svg>
    : <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor"><path d="M8 5.2v13.6a1 1 0 0 0 1.52.85l10.6-6.8a1 1 0 0 0 0-1.7L9.52 4.35A1 1 0 0 0 8 5.2z" /></svg>;
}

// ---------- fullskjermspiller ----------
const ALL_INPUTS: InputId[] = ['airplay', 'bt', 'aux', 'radio', 'usb', 'spotify'];
const SRC_NAME: Record<InputId, string> = { airplay: 'AirPlay', bt: 'Blåtann', aux: 'AUX', aux2: 'AUX 2', radio: 'Radio', usb: 'USB-lyd', spotify: 'Spotify' };
/** Spiller forsterkeren Navidrome-låten appen sendte? */
function ndNow(s: Status | null) {
  if (lsvc.value !== 'nd' || !s || s.input !== 'radio') return null;
  const cur = lq.value[li.value];
  return cur && (s.radio_now?.url?.includes('id=' + encodeURIComponent(cur.id)) || (s.station || s.radio_now?.name || '').startsWith(cur.title)) ? cur : null;
}

export function FullSheet() {
  const s = status.value, t = nowTitle(s), a0 = artFor(s);
  const [dy, setDy] = useState(0);
  const start = useRef<number | null>(null), body = useRef<HTMLDivElement>(null), cur = useRef(0);
  const down = (e: PointerEvent) => {
    if ((e.target as HTMLElement).closest('input, button')) return;
    if ((body.current?.scrollTop ?? 0) > 0) return;
    start.current = e.clientY; try { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); } catch { /* ignore */ }
  };
  const move = (e: PointerEvent) => { if (start.current !== null) { cur.current = Math.max(0, e.clientY - start.current); setDy(cur.current); } };
  const up = () => { if (start.current === null) return; start.current = null; if (cur.current > 90) closeFull(); cur.current = 0; setDy(0); };
  const tick = useTick(s?.playing ? 140 : 0);
  const eq = eqActiveProfile();
  const nd = ndNow(s);
  const input = s?.input ?? 'airplay', live = input === 'radio' && !nd, ext = input === 'aux' || input === 'aux2' || input === 'usb';
  const station = s?.radio_now?.name || s?.station || '';
  const big = live ? station || t.title : nd ? nd.title : t.title;
  const kicker = live ? 'RADIO' + (s?.radio_now?.genre ? ' · ' + s.radio_now.genre.toUpperCase() : '') : input === 'aux' || input === 'aux2' ? 'AUX' : input === 'usb' ? 'USB-LYD' : nd ? (nd.artist + ' · ' + nd.album).toUpperCase() : (t.sub || '').toUpperCase();
  const ndImg = nd ? ndCover(nd.coverArt, 600) : '';
  const a = ndImg ? { bg: 'url("' + ndImg.replace(/"/g, '') + '") center / cover no-repeat, ' + art(nd!.album).bg, ink: art(nd!.album).ink, img: ndImg } : a0;
  const viz = Array.from({ length: 12 }, (_, i) => { const e = eq[Math.min(4, Math.floor(i / 2.4))] ?? 0, v = s?.playing ? 0.35 + 0.55 * Math.abs(Math.sin(tick * 0.45 + i * 0.9) * Math.sin(tick * 0.21 + i)) : 0.06; return { h: Math.max(4, Math.min(100, v * 100 + e * 2.5)), o: s?.playing ? 1 : 0.35 }; });
  const dur = nd ? nd.duration : s?.duration ?? 0, pos = Math.min(s?.position ?? 0, dur || 0);
  const quality = live ? 'DIREKTE' : nd ? [nd.suffix?.toUpperCase(), nd.samplingRate ? (nd.samplingRate / 1000).toString().replace('.', ',') + ' kHz' : nd.bitRate ? nd.bitRate + ' kbps' : ''].filter(Boolean).join(' · ') : input === 'airplay' ? 'ALAC · 44,1 kHz' : input === 'aux' || input === 'aux2' ? 'ANALOG' : input === 'usb' ? 'USB-LYD' : input === 'spotify' ? 'OGG VORBIS' : '';
  const srcName = nd ? 'Navidrome' : SRC_NAME[input] ?? 'AirPlay';
  const list = s?.inputs?.length ? s.inputs : ALL_INPUTS;
  const off = !s || !s.power || ext;
  const prev = () => { if (!libNext(-1)) void act(() => api.transport('previous')); };
  const next = () => { if (!libNext(1)) void act(() => api.transport('next')); };
  const curName = station.toLowerCase();
  const icon = (d: string, sz = 20, fill = false) => <svg width={sz} height={sz} viewBox="0 0 24 24" fill={fill ? 'currentColor' : 'none'} stroke={fill ? 'none' : 'currentColor'} stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d={d} /></svg>;
  const rnd = 'width:40px;height:40px;border-radius:50%;border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0';
  const queue = nd ? lq.value.map((x, i) => ({ t: x.title, s: x.artist, bg: art(x.album).bg, img: ndCover(x.coverArt, 120), on: i === li.value, pick: () => { playNd(lq.value, i); queueOpen.value = false; } }))
    : [{ t: big, s: live ? (s?.radio_now?.now || t.sub) : t.sub, bg: a.bg, img: '', on: true, pick: () => { queueOpen.value = false; } }];
  return (
    <div data-testid="full" onPointerDown={down} onPointerMove={move} onPointerUp={up} onPointerCancel={up}
      style={`position:fixed;inset:0;top:calc(var(--sat) + 2px);z-index:50;display:flex;flex-direction:column;min-height:0;border-radius:18px 18px 0 0;overflow:hidden;background:linear-gradient(180deg, rgba(11,11,12,0.15) 0%, rgba(11,11,12,0.55) 55%, rgba(11,11,12,0.8) 100%), ${a.bg};transform:translateY(${dy}px);transition:${dy ? 'none' : 'transform .25s ease'};touch-action:pan-x;color:#f2f2ee;animation:up .25s cubic-bezier(.2,.7,.2,1)`}>
      <div style="display:flex;justify-content:center;padding:6px 0 4px"><button onClick={closeFull} aria-label="Lukk" class="grab-btn" style="width:56px;height:20px;border:none;background:none;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0"><div style="width:36px;height:5px;border-radius:3px;background:rgba(242,242,238,.4)" /></button></div>
      <div ref={body} class="dsc" style="flex:1;overflow:auto;scrollbar-width:none;padding:4px 18px calc(16px + var(--sab));display:flex;flex-direction:column;gap:14px;min-height:0">
        {!queueOpen.value && (
          <div data-testid="art" style={`aspect-ratio:1;border-radius:14px;background:${a.bg};position:relative;overflow:hidden;display:flex;flex-direction:column;justify-content:space-between;padding:20px;box-sizing:border-box;box-shadow:0 18px 40px rgba(0,0,0,.35);flex-shrink:0`}>
            {!a.img && <>
              <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
                <span style={`font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.12em;color:${a.ink};opacity:.8`}>{kicker}</span>
                {live && <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:0.1em;padding:3px 6px;border-radius:4px;background:#e05a4a;color:#fff">DIREKTE</span>}
              </div>
              <span style={`font-size:${big.length > 14 ? '30px' : '40px'};font-weight:600;line-height:1.02;color:${a.ink};text-wrap:balance`}>{big}</span>
              <div style="display:flex;align-items:flex-end;gap:3px;height:22px">{viz.map((v, i) => <div key={i} style={`width:4px;height:${v.h}%;background:${a.ink};border-radius:2px;opacity:${v.o}`} />)}</div>
            </>}
            {a.img && live && <span style="position:absolute;top:16px;right:16px;font-family:'IBM Plex Mono',monospace;font-size:9px;letter-spacing:0.1em;padding:3px 6px;border-radius:4px;background:#e05a4a;color:#fff">DIREKTE</span>}
          </div>
        )}
        {queueOpen.value && (
          <div style="aspect-ratio:1;display:flex;flex-direction:column;gap:6px;flex-shrink:0" data-testid="queue">
            <span style="font-size:15px;font-weight:600">Neste i køen</span>
            <div class="dsc" style="display:flex;flex-direction:column;border-radius:14px;background:rgba(0,0,0,.22);overflow:auto;scrollbar-width:none">
              {queue.map((q, i) => (
                <button key={i} onClick={q.pick} style={`display:grid;grid-template-columns:40px minmax(0,1fr) auto;gap:10px;align-items:center;min-height:56px;padding:0 12px;border:none;border-top:1px solid ${i ? 'rgba(242,242,238,.1)' : 'transparent'};background:transparent;cursor:pointer;text-align:left`}>
                  <div style={`width:40px;height:40px;border-radius:6px;background:${q.img ? 'url("' + q.img + '") center / cover, ' + q.bg : q.bg}`} />
                  <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style={`font-size:14px;color:${q.on ? '#f0c46a' : '#f2f2ee'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{q.t}</span><span style="font-size:12px;color:rgba(242,242,238,.6);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{q.s}</span></span>
                  <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#f0c46a">{q.on ? 'SPILLER' : ''}</span>
                </button>
              ))}
            </div>
            {!nd && <span style="font-size:12px;color:rgba(242,242,238,.6);line-height:1.45">Køen er tom. {SRC_NAME[input]} styrer selv hva som kommer etterpå; kø i appen finnes for Navidrome.</span>}
          </div>
        )}
        {srcOpen.value && (
          <div style="display:flex;gap:6px;flex-wrap:wrap" data-testid="inputs">
            {list.map((id) => { const c = sel(input === id && !nd); return <button key={id} onClick={() => { lsvc.value = null; void act(() => api.input(id), { input: id }); }} style={`padding:8px 12px;border-radius:999px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:12px;cursor:pointer;white-space:nowrap`}>{inputLabel(id)}</button>; })}
          </div>
        )}
        {live && favs.value.length > 0 && (
          <div class="dsc" style="display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;margin:0 -18px;padding:0 18px;flex-shrink:0">
            {favs.value.map((f) => { const c = sel(curName === f.title.toLowerCase()); return <button key={f.n} onClick={() => playFav(f)} style={`display:flex;align-items:center;gap:6px;padding:7px 11px;border-radius:999px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:12px;cursor:pointer;white-space:nowrap;flex-shrink:0`}><span style="font-family:'IBM Plex Mono',monospace;font-size:10px;opacity:.7">{f.n}</span>{f.title}</button>; })}
          </div>
        )}
        <div style="display:flex;flex-direction:column;gap:2px;margin-top:auto">
          <span data-testid="now-title" style="font-size:20px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{nd ? nd.title : live ? (s?.title || s?.radio_now?.now || station || t.title) : t.title}</span>
          <span style="font-size:14px;color:rgba(242,242,238,.65);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{nd ? nd.artist + ' · ' + nd.album : live ? (s?.artist || station) : [t.sub, t.album].filter(Boolean).join(' · ')}</span>
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:10px">
          <button onClick={() => { srcOpen.value = !srcOpen.value; }} style="display:flex;align-items:center;gap:6px;border:none;background:none;padding:0;cursor:pointer;font-size:15px;font-weight:600;color:#f2f2ee">{srcName}<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" style="opacity:.6"><path d="M6 9l6 6 6-6" /></svg></button>
          <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:0.06em;color:rgba(242,242,238,.7)">{quality}</span>
        </div>
        {!live && !ext && dur > 0 && (
          <div style="display:flex;flex-direction:column;gap:6px">
            <div style="height:16px;display:flex;align-items:center"><div style="flex:1;height:5px;border-radius:3px;background:rgba(242,242,238,.22);overflow:hidden"><div style={`height:100%;width:${Math.min(100, (pos / dur) * 100).toFixed(1)}%;background:rgba(242,242,238,.9);border-radius:3px`} /></div></div>
            <div style="display:flex;justify-content:space-between;font-family:'IBM Plex Mono',monospace;font-size:10px;color:rgba(242,242,238,.6)"><span>{mmss(pos)}</span><span>−{mmss(dur - pos)}</span></div>
          </div>
        )}
        <div style="display:flex;align-items:center;justify-content:space-between;padding:0 2px">
          <button aria-label="Tilfeldig" disabled={!nd} title={nd ? 'Bland køen' : 'Ikke støttet av kilden'} onClick={() => { if (!nd) return; const rest = lq.value.filter((_, i) => i !== li.value).sort(() => Math.random() - 0.5); lq.value = [nd, ...rest]; li.value = 0; showToast('Køen er blandet'); }} style={rnd + `;color:rgba(242,242,238,.75);opacity:${nd ? 1 : 0.35}`}>{icon('M16 3h5v5M4 20L21 3M21 16v5h-5M15 15l6 6M4 4l5 5')}</button>
          <button aria-label="Forrige" disabled={off} onClick={prev} style="width:52px;height:52px;border-radius:50%;border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#f2f2ee;padding:0"><svg width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><rect x="4" y="5" width="2.4" height="14" rx="1" /><path d="M20 5.8v12.4a1 1 0 0 1-1.55.83L9.3 12.83a1 1 0 0 1 0-1.66l9.15-6.2A1 1 0 0 1 20 5.8z" /></svg></button>
          <button aria-label={s?.playing ? 'Pause' : 'Spill'} data-testid="playpause" disabled={off} onClick={playPause} style="width:72px;height:72px;border-radius:50%;border:none;background:rgba(242,242,238,.14);color:#f2f2ee;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0"><PP playing={!!s?.playing} size={30} /></button>
          <button aria-label="Neste" disabled={off} onClick={next} style="width:52px;height:52px;border-radius:50%;border:none;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;color:#f2f2ee;padding:0"><svg width="30" height="30" viewBox="0 0 24 24" fill="currentColor"><rect x="17.6" y="5" width="2.4" height="14" rx="1" /><path d="M4 5.8v12.4a1 1 0 0 0 1.55.83l9.15-6.2a1 1 0 0 0 0-1.66l-9.15-6.2A1 1 0 0 0 4 5.8z" /></svg></button>
          <button aria-label="Gjenta" disabled title="Ikke støttet av kilden" style={rnd + ';color:rgba(242,242,238,.75);opacity:.35'}>{icon('M17 2l4 4-4 4M3 11V9a3 3 0 0 1 3-3h15M7 22l-4-4 4-4M21 13v2a3 3 0 0 1-3 3H3')}</button>
        </div>
        <div style="display:grid;grid-template-columns:auto minmax(0,1fr) 2.5ch;gap:12px;align-items:center">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#f2f2ee" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 9h3l5-4v14l-5-4H4zM16 9a4 4 0 0 1 0 6" /></svg>
          <Slider value={s?.volume ?? 0} label="Volum" onCommit={setVolume} className="range white" />
          <span data-testid="vol" style="font-family:'IBM Plex Mono',monospace;font-size:12px;text-align:right;color:rgba(242,242,238,.7)">{s?.volume ?? 0}</span>
        </div>
        <div style="display:grid;grid-template-columns:48px minmax(0,1fr) 48px;gap:12px;align-items:center;padding-top:4px">
          <button aria-label="Kø" onClick={() => { queueOpen.value = !queueOpen.value; }} style={`width:48px;height:48px;border-radius:50%;border:1px solid rgba(242,242,238,.18);background:${queueOpen.value ? 'rgba(242,242,238,.22)' : 'rgba(0,0,0,.18)'};color:#f2f2ee;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0`}>{icon('M10 6h11M10 12h11M10 18h11M3 5l4 3-4 3z')}</button>
          <button onClick={() => { closeFull(); go('rooms'); }} style="justify-self:center;display:flex;align-items:center;gap:8px;height:48px;padding:0 18px;border-radius:999px;border:1px solid rgba(242,242,238,.18);background:rgba(0,0,0,.18);font-size:14px;font-weight:600;cursor:pointer;white-space:nowrap;max-width:100%;overflow:hidden"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><rect x="6" y="3" width="10" height="18" rx="2" /><circle cx="11" cy="15" r="2.5" /><circle cx="11" cy="7.5" r="1" /></svg><span style="overflow:hidden;text-overflow:ellipsis">{groupLabel()}</span></button>
          <button aria-label="Mer" onClick={() => { srcOpen.value = !srcOpen.value; }} style={`width:48px;height:48px;border-radius:50%;border:1px solid rgba(242,242,238,.18);background:${srcOpen.value ? 'rgba(242,242,238,.22)' : 'rgba(0,0,0,.18)'};color:#f2f2ee;cursor:pointer;display:flex;align-items:center;justify-content:center;padding:0`}><svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.8" /><circle cx="12" cy="12" r="1.8" /><circle cx="19" cy="12" r="1.8" /></svg></button>
        </div>
      </div>
    </div>
  );
}
export { fmtDur };

// ---------- Rom («Ditt system») ----------
export function RoomsPhone({ wide = false }: { wide?: boolean }) {
  const rooms = useRooms(), ak = activeKey(), g = groups.value;
  const act0 = rooms[0]!;
  const n = groupCount(ak), surr = n > 1 && g.mode === 'surround';
  const allG = rooms.length > 1 && rooms.every((r) => inGroup(r.key, ak));
  const np = (st: Status | null) => {
    if (!st) return 'Ikke tilkoblet';
    if (!st.power) return 'Standby';
    if (!st.playing) return 'Ingenting spiller';
    if (st.input === 'radio') return st.radio_now?.name || st.station || 'Radio';
    return st.title ? st.title + (st.artist ? ' · ' + st.artist : '') : inputLabel(st.input);
  };
  const setVolAt = async (base: string, v: number) => {
    try { const r = await fetch(base + '/api/volume', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ volume: v }) }); if (!r.ok) throw new Error(); }
    catch { showToast('Fikk ikke kontakt med ' + base.replace(/^https?:\/\//, '')); }
  };
  return (
    <>
      <div style="display:flex;gap:8px;flex-wrap:wrap">
        <button onClick={() => groupAll(rooms.map((r) => r.key))} style={`height:36px;padding:0 14px;border-radius:999px;border:1px solid ${allG ? A : '#2e2e30'};background:${allG ? '#1c170d' : '#141415'};font-size:13px;cursor:pointer;white-space:nowrap`}>Alle rom</button>
        <button onClick={groupNone} style="height:36px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:#141415;font-size:13px;cursor:pointer;white-space:nowrap">Bare {act0.name}</button>
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">
        {n > 1 && (
          <div style="display:flex;flex-direction:column;gap:8px;padding:12px;border-radius:14px;background:#111112;border:1px solid #242426">
            <span style="font-size:12px;color:#8b8b86">Gruppe · {n} spillere synkronisert</span>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:3px;border-radius:10px;background:#0b0b0c">
              {([['sync', 'Samme musikk'], ['surround', 'Surround']] as const).map(([m, label]) => <button key={m} onClick={() => setMode(m)} style={`height:44px;border-radius:8px;border:none;background:${g.mode === m ? '#2a2112' : 'transparent'};color:${g.mode === m ? '#f0c46a' : '#c9c9c4'};font-size:13px;font-weight:600;cursor:pointer`}>{label}</button>)}
            </div>
            <span style="font-size:12px;color:#8b8b86;line-height:1.45;text-wrap:pretty">{surr ? 'Spillerne deler ett lydbilde i samme rom. Velg plassering for hver høyttaler. Tidsforsinkelse justeres automatisk.' : 'Samme musikk i alle rommene, synkronisert ned til millisekunder. Volum styres per rom.'}</span>
            <span style="font-size:11px;color:#c9b48a;line-height:1.45">Gruppen lagres i appen. Synkronisert avspilling via Lyrion er ikke koblet til forsterkeren ennå.</span>
          </div>
        )}
        {rooms.map((r) => {
          const inG = inGroup(r.key, ak), on = r.active, vol = r.st?.volume ?? 0;
          return (
            <div key={r.key} style={`display:grid;grid-template-columns:44px minmax(0,1fr) 32px;gap:12px;align-items:center;padding:12px;border-radius:14px;background:${on ? '#1c170d' : '#141415'};border:1px solid ${on ? '#5a4420' : '#242426'}`}>
              <button onClick={() => { if (!on) void switchRoom(r.base); }} aria-label={'Styr ' + r.name} style="width:44px;height:44px;border-radius:10px;background:#1f1f21;border:none;display:flex;align-items:center;justify-content:center;cursor:pointer;color:#c9c9c4;padding:0"><svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[r.product]} /></svg></button>
              <div style="display:flex;flex-direction:column;gap:6px;min-width:0">
                <button onClick={() => { if (!on) void switchRoom(r.base); }} style="border:none;background:none;padding:0;cursor:pointer;text-align:left;display:flex;justify-content:space-between;gap:8px;align-items:baseline">
                  <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style="font-size:15px">{r.name}</span><span style="font-size:11px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{PRODUCT_LABEL[r.product]} · {np(r.st)}</span></span>
                  <span style="font-family:'IBM Plex Mono',monospace;font-size:12px;color:#c9c9c4">{r.st ? vol : '–'}</span>
                </button>
                <Slider value={vol} label={'Volum ' + r.name} onCommit={(v, fin) => { if (on) setVolume(v, fin); else if (fin) void setVolAt(r.base, v); }} />
              </div>
              <button onClick={() => toggleMember(ak, r.key)} aria-label="Med i gruppen" style={`width:28px;height:28px;border-radius:50%;border:1.5px solid ${inG ? A : '#55554f'};background:${inG ? A : 'transparent'};color:#0b0b0c;cursor:pointer;padding:0;display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700`}>{inG ? '✓' : ''}</button>
              {surr && inG && (
                <div style="grid-column:1 / -1;display:flex;gap:5px;flex-wrap:wrap">
                  {ROLES.map((label, j) => { const o = (g.roles[r.key] ?? 0) === j; return <button key={label} onClick={() => setRole(r.key, j)} style={`height:30px;padding:0 10px;border-radius:8px;border:1px solid ${o ? A : '#2e2e30'};background:${o ? '#2a2112' : '#141415'};color:${o ? '#f0c46a' : '#c9c9c4'};font-size:12px;cursor:pointer;white-space:nowrap`}>{label}</button>; })}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <button onClick={() => { mode.value = 'find'; }} data-testid="add-device" style={`display:grid;grid-template-columns:44px minmax(0,1fr) auto;gap:12px;align-items:center;min-height:68px;padding:12px 14px;border-radius:14px;border:1px solid #3a2e17;background:#141209;cursor:pointer;text-align:left${wide ? ';width:100%' : ''}`}>
        <div style="width:44px;height:44px;border-radius:12px;background:#2a2112;border:1px solid #5a4420;color:#f0c46a;display:flex;align-items:center;justify-content:center"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg></div>
        <div style="display:flex;flex-direction:column;gap:3px;min-width:0"><span style="font-size:15px;font-weight:600;color:#f2f2ee">Legg til enhet</span><span style="font-size:12px;color:#8b8b86">Skjold S1, Node eller Core</span></div>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#8b8b86" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6" /></svg>
      </button>
      <span style="font-size:11px;color:#8b8b86;text-wrap:pretty">Rom med hake spiller det samme, synkronisert av Lyrion. Trykk på et rom for å styre det.</span>
    </>
  );
}
