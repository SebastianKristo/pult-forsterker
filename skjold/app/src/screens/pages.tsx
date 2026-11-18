// Sider som deles av telefon- og PC-skallet: Hjem, Lyd (EQ) og Rom (etter Skjold App v2 / S1 Web v3).
import { swLibs } from '../lib/subwave';
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, PRODUCT_HW, PRODUCT_LABEL, type InputId } from '../lib/api';
import { act, deviceName, eqActiveSource, go, inputLabel, online, openFull, product, recent, setEqProfile, setSetting, settings, status } from '../lib/store';
import { art, EQ, EQ_DESC, EQ_HZ, EQ_NAMES, fmt, type EqSource } from '../lib/settings';
import { vises } from '../lib/meny';
import { Chip, PRODUCT_ICON, Slider, SrcCircle, Toggle } from '../components/ui';
import { favs, favsLoaded, loadFavs, playFav } from '../lib/radio';
import { ndConfigured } from '../lib/navidrome';
import { Transport, artFor, nowTitle, sourceLine, subLine } from './player';
import { useRooms } from './phone';
import { SpatialCard } from './advaudio';
import { SpeakerCard } from './speakers';
import { confirmTap, hapticsOn, setHapticsOn, tick } from '../lib/haptics';

/** Ikke-brytende mellomrom før enheter, som i designet (2 × 50 W). */
export const nbHw = (s: string) => s.replace(/ (×|W\b|kHz|mm)/g, ' $1').replace(/(\d) ×/g, '$1 ×');

// ---------- Hjem ----------
const SRC_ORDER: [InputId, string][] = [['radio', 'Radio'], ['airplay', 'AirPlay'], ['bt', 'Blåtann'], ['spotify', 'Spotify'], ['plex', 'Plex'], ['aux', 'AUX'], ['aux2', 'AUX'], ['usb', 'USB']];

export function HomePage({ wide = false }: { wide?: boolean }) {
  const s = status.value;
  useEffect(() => { if (!favsLoaded.value) void loadFavs(); }, []);
  if (wide) return <HomeWide />;
  const p = product.value;
  void s;
  return (
    <>
      <div class="home-hdr">
        <div class="logo"><div class="bars">{[8, 12, 16, 12, 8].map((h, i) => <i key={i} style={{ height: h + 'px' }} />)}</div><span class="word">SKJOLD</span></div>
        <button class="sys-pill" onClick={() => go('rooms')}><i class={online.value ? '' : 'off'} />{deviceName.value}</button>
      </div>
      <button class="act-room" onClick={() => go('rooms')} data-testid="device-card">
        <div class="ico"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[p]} /></svg></div>
        <div class="col" style={{ gap: '2px', minWidth: 0 }}>
          <span class="n">{deviceName.value}</span>
          <span class="m">{PRODUCT_LABEL[p]}</span>
          <span class="hw">{nbHw(PRODUCT_HW[p])}</span>
        </div>
        <span class="bytt">Bytt</span>
      </button>
      <HomeBody />
    </>
  );
}

/** Nylig spilt, Kilder (inkl. musikktjenester) og Radiofavoritter – felles for mobil og PC (designet tHome). */
function HomeBody({ wide = false }: { wide?: boolean }) {
  const s = status.value;
  const inputs = s?.inputs?.length ? s.inputs : ['airplay', 'bt', 'spotify', 'radio', 'aux', 'aux2', 'usb'];
  const services = SRC_ORDER.filter(([id]) => inputs.includes(id));
  const st0 = settings.value;
  const libs: [string, string][] = [...(st0.ytmEn ? [['ytm', 'YouTube Music'] as [string, string]] : []), ...(st0.ndEn || ndConfigured() ? [['nd', 'Navidrome'] as [string, string]] : []), ...swLibs()].filter(([id]) => vises(id));
  const pickSrc = (id: InputId) => {
    if (id === 'radio') { go('radio'); return; }
    void act(() => api.input(id), { input: id }); openFull();
  };
  const rc = recent.value.slice(0, wide ? 10 : 8);
  return (
    <div class={'col ' + (wide ? 'gap16 home-wide' : 'gap16')} style={wide ? undefined : { display: 'contents' }}>
      {rc.length > 0 && (
        <div class="col gap10">
          <span class="h2">Nylig spilt</span>
          <div class="hscroll">
            {rc.map((x) => {
              const fav = x.station && !x.image ? favs.value.find((f) => f.title === x.title) : undefined;   // eldre oppføringer uten bilde: bruk favorittens logo
              const a = art(x.title, x.image || fav?.image || fav?.icon);
              return (
                <button key={x.key} class="rc" onClick={() => {
                  if (x.station) { const f = favs.value.find((f) => f.title === x.title); if (f) playFav(f); else if (x.url) void act(() => api.radioPlay({ url: x.url!, title: x.title }), { input: 'radio' }); else go('radio'); }
                  else { void act(() => api.input(x.input), { input: x.input }); }
                  openFull();
                }}>
                  <div class="sq" style={{ background: a.bg, color: a.ink, borderRadius: x.station ? '50%' : '10px' }}>{a.logo ? '' : x.big}</div>
                  <span class="t">{x.title}</span>
                  <span class="k">{x.kind}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
      <div class="col gap10">
        <span class="h2">Kilder</span>
        <div class="hscroll" style={{ gap: '14px' }} data-testid="inputs">
          {services.map(([id, label]) => (
            <button key={id} class="svc" onClick={() => pickSrc(id)}>
              <SrcCircle label={label} size={wide ? 76 : 64} />
              <span>{id === 'aux' || id === 'aux2' ? inputLabel(id) : label}</span>
            </button>
          ))}
          {libs.map(([id, label]) => (
            <button key={id} class="svc" onClick={() => go('lib', id)}>
              <SrcCircle label={label} size={wide ? 76 : 64} />
              <span>{label}</span>
            </button>
          ))}
        </div>
      </div>
      <div class="col gap10">
        <div class="row between" style={{ alignItems: 'baseline' }}><span class="h2">Radiofavoritter</span><button class="link0" onClick={() => go('radio')}>Administrer</button></div>
        {favs.value.length ? (
          <div class="hscroll">
            {favs.value.map((f) => {
              const a = art(f.title, f.image);
              return (
                <button key={f.n} class="ft" onClick={() => { playFav(f); openFull(); }}>
                  <div class="sq" style={{ background: a.bg, color: a.ink }}><span class="n">{f.n}</span><span class="t">{a.logo ? '' : f.title}</span></div>
                  <span class="k">{f.genre || f.title}</span>
                </button>
              );
            })}
          </div>
        ) : favsLoaded.value ? <button class="dashed" onClick={() => go('radio')}>Legg til radiokanal</button> : null}
      </div>
    </div>
  );
}

/** PC-hjem som dashbord: fliser i ulike størrelser (Nå spilles, Ditt system, Radiofavoritter, Lyd nå, Kilder, Nylig spilt). */
function HomeWide() {
  const s = status.value, t = nowTitle(s), a = artFor(s);
  const rooms = useRooms();
  const inputs = s?.inputs?.length ? s.inputs : ['airplay', 'bt', 'spotify', 'radio', 'aux', 'aux2', 'usb'];
  const services = SRC_ORDER.filter(([id]) => inputs.includes(id));
  const st0 = settings.value;
  const libs: [string, string][] = [...(st0.ytmEn ? [['ytm', 'YouTube Music'] as [string, string]] : []), ...(st0.ndEn || ndConfigured() ? [['nd', 'Navidrome'] as [string, string]] : []), ...swLibs()].filter(([id]) => vises(id));
  const pickSrc = (id: InputId) => { if (id === 'radio') { go('radio'); return; } void act(() => api.input(id), { input: id }); openFull(); };
  const eqSrc = eqActiveSource.value, eq = st0.eq[eqSrc]?.eq ?? [0, 0, 0, 0, 0];
  const live = s?.input === 'radio' && !s.source_label && s.playing;
  const rc = recent.value.slice(0, 8);
  const online2 = rooms.filter((x) => x.st).length;
  return (
    <div class="bento" data-testid="dashboard">
      <section class="card t now" style={{ gridColumn: 'span 4', gridRow: 'span 3' }}>
        <button class="now-cover" style={{ background: a.bg, color: a.ink }} onClick={() => go('play')} aria-label="Åpne spilleren">{!a.img && <span class="big">{t.title}</span>}</button>
        <div class="now-txt">
          <div class="col" style={{ gap: '8px', minWidth: 0 }}>
            <span class="lbl">{live ? <span class="live">DIREKTE</span> : sourceLine(s).toUpperCase()}</span>
            <h2 class="now-t">{t.title}</h2>
            <span class="muted ellip2">{subLine(t) || sourceLine(s)}</span>
          </div>
          <Transport s={s} />
        </div>
      </section>
      <section class="card t" style={{ gridColumn: 'span 2', gridRow: 'span 3' }}>
        <div class="row between"><h3 class="th">Ditt system</h3><span class="lbl">{online2}/{rooms.length}</span></div>
        <div class="col" style={{ gap: '8px', overflowY: 'auto', minHeight: 0 }}>
          {rooms.map((x) => (
            <button key={x.key} class={'mini-room' + (x.active ? ' on' : '')} onClick={() => go('rooms')}>
              <span class="ri"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[x.product]} /></svg></span>
              <span class="col" style={{ minWidth: 0, gap: '2px' }}><span class="row between" style={{ gap: '8px' }}><b class="ellip">{x.name}</b><span class="mono muted" style={{ fontSize: '12px' }}>{x.st ? x.st.volume : '–'}</span></span><span class="muted ellip" style={{ fontSize: '12px' }}>{PRODUCT_LABEL[x.product]}{x.st ? ' · ' + nowTitle(x.st).title : ' · frakoblet'}</span></span>
            </button>
          ))}
        </div>
        <button class="link0" style={{ marginTop: 'auto', alignSelf: 'flex-start' }} onClick={() => go('grp')}>Grupper og surround ›</button>
      </section>
      <section class="card t" style={{ gridColumn: 'span 4', gridRow: 'span 2' }}>
        <div class="row between"><h3 class="th">Radiofavoritter</h3><button class="link0" onClick={() => go('radio')}>Administrer</button></div>
        {favs.value.length ? (
          <div class="fav-grid">
            {favs.value.slice(0, 6).map((f) => { const fa = art(f.title, f.image); const on = s?.input === 'radio' && s.preset === f.n; return (
              <button key={f.n} class={'fav' + (on ? ' on' : '')} style={{ background: fa.bg, color: fa.ink }} onClick={() => playFav(f)}><em>{f.n}</em><b>{fa.logo ? '' : f.title}</b></button>
            ); })}
          </div>
        ) : favsLoaded.value ? <button class="dashed" onClick={() => go('radio')}>Legg til radiokanal</button> : null}
      </section>
      <section class="card t" style={{ gridColumn: 'span 2', gridRow: 'span 2' }}>
        <div class="row between"><h3 class="th">Lyd nå</h3><button class="link0" onClick={() => go('eq')}>EQ ›</button></div>
        <div class="eq-mini">
          {eq.map((v, i) => <div key={i} class="b"><span style={{ height: Math.max(6, 40 + v * 3.2) + 'px' }} /><em>{EQ.bands[i]}</em></div>)}
        </div>
        <span class="muted" style={{ fontSize: '12px' }}>{EQ.sources.find((x) => x[0] === eqSrc)?.[1] ?? ''}</span>
      </section>
      <section class="card t srcs" style={{ gridColumn: 'span 6', gridRow: 'span 1' }}>
        <h3 class="th" style={{ flexShrink: 0 }}>Kilder</h3>
        {services.map(([id, label]) => <button key={id} class="svc" onClick={() => pickSrc(id)}><SrcCircle label={label} size={48} /><span>{id === 'aux' || id === 'aux2' ? inputLabel(id) : label}</span></button>)}
        {libs.map(([id, label]) => <button key={id} class="svc" onClick={() => go('lib', id)}><SrcCircle label={label} size={48} /><span>{label}</span></button>)}
      </section>
      {rc.length > 0 && <section class="card t" style={{ gridColumn: 'span 6', gridRow: 'span 2' }}>
        <h3 class="th">Nylig spilt</h3>
        <div class="hscroll">
          {rc.map((x) => { const ra = art(x.title, x.image); return (
            <button key={x.key} class="rc" onClick={() => { if (x.station) { const f = favs.value.find((f) => f.title === x.title); if (f) playFav(f); else if (x.url) void act(() => api.radioPlay({ url: x.url!, title: x.title }), { input: 'radio' }); else go('radio'); } else void act(() => api.input(x.input), { input: x.input }); }}>
              <div class="sq" style={{ background: ra.bg, color: ra.ink, borderRadius: x.station ? '50%' : '10px' }}>{ra.logo ? '' : x.big}</div>
              <span class="t">{x.title}</span><span class="k">{x.kind}</span>
            </button>
          ); })}
        </div>
      </section>}
    </div>
  );
}

// ---------- Lyd (EQ) ----------
const EQ_MAX = 12;
/** Jevn kurve gjennom båndpunktene (x i 0–1000, y i 0–H), med flate ender ut mot kantene. */
function eqPath(pts: [number, number][], W: number): string {
  let d = `M0 ${pts[0]![1].toFixed(1)} L${pts[0]![0]} ${pts[0]![1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) { const [x0, y0] = pts[i]!, [x1, y1] = pts[i + 1]!, mx = (x0 + x1) / 2; d += ` C${mx} ${y0.toFixed(1)} ${mx} ${y1.toFixed(1)} ${x1} ${y1.toFixed(1)}`; }
  return d + ` L${W} ${pts[pts.length - 1]![1].toFixed(1)}`;
}

/** Interaktiv EQ-kurve: dra punktene opp og ned (mus, finger eller piltaster). Høyden følger skjermen. */
function EqGraph({ eq, onSet }: { eq: number[]; onSet: (i: number, v: number, fin: boolean) => void }) {
  const ref = useRef<SVGSVGElement>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const [live, setLive] = useState<number[] | null>(null);
  const [size, setSize] = useState<[number, number]>([1000, 300]);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    const ro = new ResizeObserver(([e]) => { const r = e!.contentRect; if (r.width > 0 && r.height > 0) setSize([Math.round(r.width), Math.round(r.height)]); });
    ro.observe(el); return () => ro.disconnect();
  }, []);
  const vals = live ?? eq;
  const [W, H] = size, pad = 18, n = vals.length, edge = Math.min(70, W * 0.07);
  const xOf = (i: number) => edge + (i * (W - 2 * edge)) / (n - 1);
  const yOf = (v: number) => pad + ((EQ_MAX - v) / (2 * EQ_MAX)) * (H - 2 * pad);
  const pts = vals.map((v, i) => [xOf(i), yOf(v)] as [number, number]);
  const line = eqPath(pts, W), y0 = yOf(0);
  const valAt = (clientY: number) => { const r = ref.current!.getBoundingClientRect(); const y = ((clientY - r.top) / r.height) * H; return Math.max(-EQ_MAX, Math.min(EQ_MAX, Math.round(EQ_MAX - ((y - pad) / (H - 2 * pad)) * 2 * EQ_MAX))); };
  const move = (e: PointerEvent, i: number, fin: boolean) => { const v = valAt(e.clientY); const nx = [...vals]; if (nx[i] !== v) { nx[i] = v; setLive(nx); onSet(i, v, false); if (!fin) tick(); } if (fin) { onSet(i, v, true); setLive(null); setDrag(null); } };
  return (
    <svg ref={ref} class="eqg" viewBox={`0 0 ${W} ${H}`} role="group" aria-label="Equalizer-kurve"
      onPointerMove={(e) => { if (drag !== null) move(e as unknown as PointerEvent, drag, false); }}
      onPointerUp={(e) => { if (drag !== null) move(e as unknown as PointerEvent, drag, true); }}
      onPointerCancel={() => { setDrag(null); setLive(null); }}>
      <defs><linearGradient id="eqfill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d9a441" stop-opacity=".32" /><stop offset="1" stop-color="#d9a441" stop-opacity="0" /></linearGradient></defs>
      {[12, 6, 0, -6, -12].map((d) => <g key={d}><line x1="0" x2={W} y1={yOf(d)} y2={yOf(d)} class={d === 0 ? 'g0' : 'g'} vector-effect="non-scaling-stroke" /></g>)}
      {vals.map((_, i) => <line key={'v' + i} x1={xOf(i)} x2={xOf(i)} y1={pad} y2={H - pad} class="gv" vector-effect="non-scaling-stroke" />)}
      <path d={`${line} L${W} ${y0} L0 ${y0} Z`} fill="url(#eqfill)" />
      <path d={line} class="ln" vector-effect="non-scaling-stroke" />
      {pts.map(([x, y], i) => (
        <g key={i} class={'nd' + (drag === i ? ' on' : '')} tabIndex={0} role="slider" aria-label={EQ_NAMES[i] + ' ' + EQ.bands[i] + ' Hz'} aria-valuemin={-EQ_MAX} aria-valuemax={EQ_MAX} aria-valuenow={vals[i]}
          onPointerDown={(e) => { (e.currentTarget as Element).closest('svg')!.setPointerCapture(e.pointerId); setDrag(i); setLive([...vals]); }}
          onKeyDown={(e) => { const d = e.key === 'ArrowUp' ? 1 : e.key === 'ArrowDown' ? -1 : 0; if (d) { e.preventDefault(); onSet(i, Math.max(-EQ_MAX, Math.min(EQ_MAX, (vals[i] ?? 0) + d)), true); } }}>
          <rect x={x - (W - 2 * edge) / (2 * (n - 1))} y={0} width={(W - 2 * edge) / (n - 1)} height={H} fill="transparent" />
          <circle cx={x} cy={y} r="10" class="dot" />
        </g>))}
    </svg>
  );
}

/** Bass, diskant og balanse: fylles fra midten (0), med verdien i en egen brikke. Loudness i samme kort. */
function ToneRow({ n, k, mn, mx, f }: { n: string; k: 'bass' | 'treb' | 'bal'; mn: number; mx: number; f: (v: number) => string }) {
  const v0 = settings.value[k];
  const [live, setLive] = useState<number | null>(null);
  const v = live ?? v0, pct = (v - mn) / (mx - mn);
  return (
    <div class="tn-row">
      <div class="tn-hd"><span>{n}</span><button class={'tn-v' + (v ? ' on' : '')} title="Tilbake til midten" onClick={() => { if (v) { confirmTap(); setSetting(k, 0); } }}>{f(v)}</button></div>
      <div class="tn-sl">
        <i class="tn-tr" /><i class="tn-mid" />
        <i class="tn-fill" style={{ left: `calc(10px + (100% - 20px) * ${Math.min(pct, 0.5)})`, width: `calc((100% - 20px) * ${Math.abs(pct - 0.5)})` }} />
        <Slider className="range bi" haptic min={mn} max={mx} value={v0} label={n} onCommit={(x, fin) => { setLive(fin ? null : x); if (fin) setSetting(k, x); }} />
      </div>
      <div class="tn-ends"><span>{k === 'bal' ? 'V' : mn}</span><span>{k === 'bal' ? 'H' : '+' + mx}</span></div>
    </div>);
}

function ToneCard({ src, loud }: { src: EqSource; loud: boolean }) {
  return (
    <section class="tn-card">
      <div class="tn-top"><span class="kicker">TONE</span><span class="lbl11">Gjelder alle innganger</span></div>
      <ToneRow n="Bass" k="bass" mn={-6} mx={6} f={fmt.dB} />
      <ToneRow n="Diskant" k="treb" mn={-6} mx={6} f={fmt.dB} />
      <ToneRow n="Balanse" k="bal" mn={-5} mx={5} f={fmt.bal} />
      <div class="tn-loud">
        <div class="col" style={{ gap: '2px', minWidth: 0 }}><span style={{ fontSize: '14px', fontWeight: 600 }}>Loudness</span><span class="lbl11">Mer bass og diskant ved lavt volum</span></div>
        <Toggle on={loud} label="Loudness" onChange={(v) => setEqProfile(src, { loud: v })} />
      </div>
    </section>);
}

export function EqPage() {
  const act0 = eqActiveSource.value;
  const [src, setSrc] = useState<EqSource>(act0);
  const prof = settings.value.eq[src];
  const name = (k: EqSource) => EQ.sources.find((x) => x[0] === k)?.[1] ?? '';
  const setBand = (i: number, v: number, fin: boolean) => { if (!fin) return; const eq = [...prof.eq]; eq[i] = v; setEqProfile(src, { eq, preset: -1 }); };
  const step = (i: number, d: number) => { confirmTap(); setBand(i, Math.max(-EQ_MAX, Math.min(EQ_MAX, (prof.eq[i] ?? 0) + d)), true); };
  const presetName = prof.preset >= 0 ? EQ.presets[prof.preset]?.[0] : 'Egendefinert';
  return (
    <div class="eqx">
      <div class="eqx-main">
        <div class="eqx-src">
          <span class="lbl11">Profil for</span>
          <div class="hscroll" style={{ gap: '6px' }}>
            {EQ.sources.map(([k, n]) => <button key={k} class={'pchip' + (src === k ? ' on' : '')} onClick={() => setSrc(k)}><span>{n}</span><i style={{ background: act0 === k ? '#6fcf7f' : 'transparent' }} /></button>)}
          </div>
          <span class="lbl11">{src === act0 ? 'Aktiv nå · følger inngangen automatisk' : 'Aktiv nå er ' + name(act0) + ' · du redigerer ' + name(src)}</span>
        </div>
        <section class="eqx-card">
          <div class="eqx-hd">
            <span class="col" style={{ gap: '2px', minWidth: 0 }}><span class="kicker">{name(src).toUpperCase()}</span><b>{presetName}</b></span>
            <button class="pchip sm" onClick={() => { confirmTap(); setEqProfile(src, { preset: 0, eq: [...EQ.presets[0]![1]] }); }} disabled={prof.eq.every((v) => v === 0)}>Nullstill</button>
          </div>
          <div class="eqx-graph">
            <span class="eqx-db" aria-hidden="true"><i>+12</i><i>+6</i><i>0</i><i>−6</i><i>−12</i></span>
            <EqGraph eq={prof.eq} onSet={setBand} />
          </div>
          <div class="eqx-bands">
            {EQ.bands.map((b, i) => { const v = prof.eq[i] ?? 0; return (
              <div class="eqx-band" key={b}>
                <span class="nm">{EQ_NAMES[i]}</span>
                <span class="hz">{b} Hz</span>
                <div class="st"><button onClick={() => step(i, -1)} aria-label={'Mindre ' + EQ_NAMES[i]}>−</button><span class={'v' + (v ? ' on' : '')}>{v > 0 ? '+' : v < 0 ? '−' : ''}{Math.abs(v)}</span><button onClick={() => step(i, 1)} aria-label={'Mer ' + EQ_NAMES[i]}>+</button></div>
              </div>); })}
          </div>
          <div class="eqx-presets">{EQ.presets.map(([n, v], i) => <button key={n} class={'pchip sm' + (prof.preset === i ? ' on' : '')} onClick={() => { confirmTap(); setEqProfile(src, { preset: i, eq: [...v] }); }}>{n}</button>)}</div>
        </section>
      </div>
      <aside class="eqx-side">
        <ToneCard src={src} loud={prof.loud} />
        <details class="eqx-help">
          <summary>Hva båndene gjør</summary>
          <div class="eq-what" style={{ borderTop: 'none', paddingTop: '6px' }}>
            {EQ.bands.map((b, i) => (
              <div class="w" key={b}><span class="row" style={{ gap: '6px', alignItems: 'baseline' }}><span class="nm">{EQ_NAMES[i]}</span><span class="hz">{EQ_HZ[i]}</span></span><span class="d">{EQ_DESC[i]}</span></div>
            ))}
          </div>
          <HapticToggle />
        </details>
        <SpatialCard />
        <SpeakerCard />
      </aside>
    </div>
  );
}

/** Hjelpekrok for å holde en lerret-tegning oppdatert hvert minutt. */
export function useMinuteTick(): number { useTick(30000); return Math.floor(Date.now() / 30000) * 30000; }
/** Teller som øker hvert ms (0 = stoppet). */
export function useTick(ms: number): number {
  const [t, setT] = useState(0);
  const ref = useRef(0);
  useEffect(() => { if (!ms) return; ref.current = window.setInterval(() => setT((x) => x + 1), ms); return () => clearInterval(ref.current); }, [ms]);
  return t;
}
export { Chip };


function HapticToggle() {
  const [on, setOn] = useState(hapticsOn());
  return (
    <label class="row between" style={{ padding: '10px 2px 0', fontSize: '13px', color: '#c9c9c4', gap: '12px' }}>
      <span>Haptikk på glidebrytere <span style={{ color: '#8a8a86' }}>(Android)</span></span>
      <Toggle on={on} label="Haptikk på glidebrytere" onChange={(v) => { setOn(v); setHapticsOn(v); }} />
    </label>
  );
}
