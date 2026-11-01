// Sider som deles av telefon- og PC-skallet: Hjem, Lyd (EQ) og Rom (etter Skjold App v2 / S1 Web v3).
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, PRODUCT_HW, PRODUCT_LABEL, type InputId } from '../lib/api';
import { act, deviceName, eqActiveSource, go, inputLabel, online, openFull, product, recent, setEqProfile, setSetting, settings, status } from '../lib/store';
import { art, EQ, EQ_DESC, EQ_HZ, EQ_NAMES, fmt, type EqSource } from '../lib/settings';
import { Chip, PRODUCT_ICON, Section, Slider, SrcCircle, Toggle } from '../components/ui';
import { InputChips } from './player';
import { favs, favsLoaded, loadFavs, playFav } from '../lib/radio';

/** Ikke-brytende mellomrom før enheter, som i designet (2 × 50 W). */
export const nbHw = (s: string) => s.replace(/ (×|W\b|kHz|mm)/g, ' $1').replace(/(\d) ×/g, '$1 ×');

// ---------- Hjem ----------
const SRC_ORDER: [InputId, string][] = [['radio', 'Radio'], ['airplay', 'AirPlay'], ['bt', 'Blåtann'], ['spotify', 'Spotify'], ['aux', 'AUX'], ['aux2', 'AUX'], ['usb', 'USB']];

export function HomePage({ wide = false }: { wide?: boolean }) {
  const s = status.value;
  useEffect(() => { if (!favsLoaded.value) void loadFavs(); }, []);
  if (wide) return <HomeWide />;
  const p = product.value;
  const inputs = s?.inputs?.length ? s.inputs : ['airplay', 'bt', 'spotify', 'radio', 'aux', 'aux2', 'usb'];
  const services = SRC_ORDER.filter(([id]) => inputs.includes(id));
  const pickSrc = (id: InputId) => {
    if (id === 'radio') { go('radio'); return; }
    void act(() => api.input(id), { input: id }); openFull();
  };
  const rc = recent.value.slice(0, 8);
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
      {rc.length > 0 && (
        <div class="col gap10">
          <span class="h2">Nylig spilt</span>
          <div class="hscroll">
            {rc.map((x) => {
              const a = art(x.station ? x.title : x.title, x.image);
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
              <SrcCircle label={label} />
              <span>{id === 'aux' || id === 'aux2' ? inputLabel(id) : label}</span>
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
    </>
  );
}

function HomeWide() {
  const s = status.value;
  return (
    <div class="col gap16">
      <Section title="Kilder"><InputChips s={s} /></Section>
      <Section title="Radiofavoritter" action={<button class="link" onClick={() => go('radio')}>Administrer</button>}>
        {favs.value.length ? (
          <div class="grid-fav">
            {favs.value.map((f) => {
              const a = art(f.title, f.image);
              const on = s?.input === 'radio' && (s.radio_now?.n === f.n || s.station === f.title);
              return (
                <button key={f.n} class={'preset' + (on ? ' on' : '')} style={{ background: a.bg, color: a.ink }} onClick={() => playFav(f)}>
                  <span class="n">{f.n}</span><span class="t">{a.logo ? '' : f.title}</span>
                </button>
              );
            })}
          </div>
        ) : <button class="dashed" onClick={() => go('radio')}>Legg til radiokanal</button>}
      </Section>
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
        {EQ.presets.map(([n, v], i) => <button key={n} class={'pchip sm' + (prof.preset === i ? ' on' : '')} onClick={() => setEqProfile(src, { preset: i, eq: [...v] })}>{n}</button>)}
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
              <Slider vertical min={-12} max={12} value={prof.eq[i] ?? 0} label={b + ' Hz'}
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
      </div>
      <div class="list">
        {tone.map(([n, k, mn, mx, f]) => (
          <div class="tone" key={k}>
            <span style={{ fontSize: '13px' }}>{n}</span>
            <Slider min={mn} max={mx} value={st[k]} label={n} onCommit={(v, fin) => { if (fin) setSetting(k, v); }} />
            <span class="mono" style={{ fontSize: '12px', textAlign: 'right' }}>{f(st[k])}</span>
          </div>
        ))}
        <div class="row between" style={{ padding: '12px 14px' }}>
          <div class="col" style={{ gap: '2px' }}><span style={{ fontSize: '13px' }}>Loudness</span><span class="lbl11">Mer bass og diskant ved lavt volum</span></div>
          <Toggle on={prof.loud} label="Loudness" onChange={(v) => setEqProfile(src, { loud: v })} />
        </div>
      </div>
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
