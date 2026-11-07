// Sider som deles av telefon- og PC-skallet: Hjem, Lyd (EQ) og Rom (etter Skjold App v2 / S1 Web v3).
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, PRODUCT_HW, PRODUCT_LABEL, type InputId } from '../lib/api';
import { act, deviceName, eqActiveSource, go, inputLabel, online, openFull, product, recent, setEqProfile, setSetting, settings, status } from '../lib/store';
import { art, EQ, EQ_DESC, EQ_HZ, EQ_NAMES, fmt, type EqSource } from '../lib/settings';
import { Chip, PRODUCT_ICON, Slider, SrcCircle, Toggle } from '../components/ui';
import { favs, favsLoaded, loadFavs, playFav } from '../lib/radio';
import { ndConfigured } from '../lib/navidrome';
import { Transport, artFor, nowTitle, sourceLine, subLine } from './player';
import { useRooms } from './phone';
import { SpatialCard } from './advaudio';
import { SpeakerCard } from './speakers';
import { confirmTap, hapticsOn, setHapticsOn } from '../lib/haptics';

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
  const libs: [string, string][] = [...(st0.ytmEn ? [['ytm', 'YouTube Music'] as [string, string]] : []), ...(st0.ndEn || ndConfigured() ? [['nd', 'Navidrome'] as [string, string]] : [])];
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
  const libs: [string, string][] = [...(st0.ytmEn ? [['ytm', 'YouTube Music'] as [string, string]] : []), ...(st0.ndEn || ndConfigured() ? [['nd', 'Navidrome'] as [string, string]] : [])];
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
function curve(eq: number[]): { line: string; area: string } {
  const xs = [15, 82.5, 150, 217.5, 285], ys = eq.map((v) => 45 - v * 3.2);
  const y = (i: number) => (ys[i] ?? 45).toFixed(1);
  let d = 'M0 ' + y(0) + ' L' + xs[0] + ' ' + y(0);
  for (let i = 0; i < 4; i++) { const mx = ((xs[i] ?? 0) + (xs[i + 1] ?? 0)) / 2; d += ' C' + mx + ' ' + y(i) + ' ' + mx + ' ' + y(i + 1) + ' ' + xs[i + 1] + ' ' + y(i + 1); }
  d += ' L300 ' + y(4);
  return { line: d, area: d + ' L300 45 L0 45 Z' };
}

export function EqPage() {
  const act0 = eqActiveSource.value;
  const [src, setSrc] = useState<EqSource>(act0);
  const prof = settings.value.eq[src];
  const st = settings.value;
  const c = curve(prof.eq);
  const name = (k: EqSource) => EQ.sources.find((x) => x[0] === k)?.[1] ?? '';
  const tone: [string, 'bass' | 'treb' | 'bal', number, number, (v: number) => string][] = [['Bass', 'bass', -6, 6, fmt.dB], ['Diskant', 'treb', -6, 6, fmt.dB], ['Balanse', 'bal', -5, 5, fmt.bal]];
  return (
    <div class="eq-page">
      <div class="col gap8">
        <span class="lbl11">Profil for</span>
        <div class="hscroll" style={{ gap: '6px' }}>
          {EQ.sources.map(([k, n]) => <button key={k} class={'pchip' + (src === k ? ' on' : '')} onClick={() => setSrc(k)}><span>{n}</span><i style={{ background: act0 === k ? '#6fcf7f' : 'transparent' }} /></button>)}
        </div>
        <span class="lbl11">{src === act0 ? 'Aktiv nå · følger inngangen automatisk' : 'Aktiv nå er ' + name(act0) + ' · du redigerer ' + name(src)}</span>
      </div>
      <div class="row" style={{ gap: '6px', flexWrap: 'wrap' }}>
        {EQ.presets.map(([n, v], i) => <button key={n} class={'pchip sm' + (prof.preset === i ? ' on' : '')} onClick={() => { confirmTap(); setEqProfile(src, { preset: i, eq: [...v] }); }}>{n}</button>)}
        {prof.preset < 0 && <button class="pchip sm on">Egendefinert</button>}
      </div>
      <div class="eq-card">
        <svg viewBox="0 0 300 90" style={{ width: '100%', height: '80px', display: 'block' }}>
          <line x1="0" y1="45" x2="300" y2="45" stroke="#2a2a28" stroke-width="1" />
          <path d={c.area} fill="rgba(217,164,65,0.14)" />
          <path d={c.line} fill="none" stroke="#d9a441" stroke-width="2" />
        </svg>
        <div class="eq-bands">
          {EQ.bands.map((b, i) => (
            <div class="eq-band" key={b}>
              <span class="v">{(prof.eq[i] ?? 0) > 0 ? '+' : ''}{prof.eq[i] ?? 0}</span>
              <Slider vertical haptic min={-12} max={12} value={prof.eq[i] ?? 0} label={b + ' Hz'}
                onCommit={(v) => { const eq = [...prof.eq]; eq[i] = v; setEqProfile(src, { eq, preset: -1 }); }} />
              <span class="f">{b}</span>
              <span style="font-size:10px;color:#c9c9c4;white-space:nowrap">{EQ_NAMES[i]}</span>
            </div>
          ))}
        </div>
        <div class="eq-what">
          <span class="kicker">HVA BÅNDENE GJØR</span>
          {EQ.bands.map((b, i) => (
            <div class="w" key={b}><span class="row" style={{ gap: '6px', alignItems: 'baseline' }}><span class="nm">{EQ_NAMES[i]}</span><span class="hz">{EQ_HZ[i]}</span></span><span class="d">{EQ_DESC[i]}</span></div>
          ))}
        </div>
        <HapticToggle />
      </div>
      <div class="list">
        {tone.map(([n, k, mn, mx, f]) => (
          <div class="tone" key={k}>
            <span style={{ fontSize: '13px' }}>{n}</span>
            <Slider haptic min={mn} max={mx} value={st[k]} label={n} onCommit={(v, fin) => { if (fin) setSetting(k, v); }} />
            <span class="mono" style={{ fontSize: '12px', textAlign: 'right' }}>{f(st[k])}</span>
          </div>
        ))}
        <div class="row between" style={{ padding: '12px 14px' }}>
          <div class="col" style={{ gap: '2px' }}><span style={{ fontSize: '13px' }}>Loudness</span><span class="lbl11">Mer bass og diskant ved lavt volum</span></div>
          <Toggle on={prof.loud} label="Loudness" onChange={(v) => setEqProfile(src, { loud: v })} />
        </div>
      </div>
      <SpatialCard />
      <SpeakerCard />
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
