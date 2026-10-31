// Sider som deles av telefon- og PC-skallet.
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, hostLabel, PRODUCT_HW, PRODUCT_LABEL, PRODUCT_SHORT, productOf, setBase, type FullPreset, type Product } from '../lib/api';
import { act, deviceName, eqActiveSource, go, loadSettings, mode, online, product, reconnect, setEqProfile, settings, showToast, status, applied, settingsSource } from '../lib/store';
import { forget, knownDevices } from '../lib/discover';
import { EQ, eqCurve, type EqSource } from '../lib/settings';
import { Chip, Icon, PRODUCT_ICON, Section, Slider } from '../components/ui';
import { Art, InputChips, PresetTiles, nowTitle, subLine, VolumeRow, Transport } from './player';

// ---------- Hjem ----------
export function HomePage({ wide = false }: { wide?: boolean }) {
  const s = status.value;
  const t = nowTitle(s);
  return (
    <div class="col gap16">
      {!wide && <DeviceCard />}
      {!wide && (
        <div class="card pad col gap12">
          <div class="row gap12">
            <div style={{ width: '64px', flexShrink: 0 }}><Art s={s} size="small" /></div>
            <div class="col grow"><span class="ellip" style={{ fontWeight: 600, fontSize: '16px' }}>{t.title}</span><span class="ellip muted">{subLine(t)}</span></div>
          </div>
          <Transport s={s} />
          <VolumeRow s={s} />
        </div>
      )}
      <Section title="Kilder"><InputChips s={s} /></Section>
      <Section title="Radiofavoritter" action={<button class="link" onClick={() => go('radio')}>Administrer</button>}>
        <PresetTiles cols={wide ? 6 : 3} />
      </Section>
    </div>
  );
}

/** Hjem: aktivt rom, enhetstype og maskinvare. Trykk = Rom. */
export function DeviceCard() {
  const s = status.value, p = product.value;
  return (
    <button class="card dev-card" style={{ textAlign: 'left', color: 'var(--text)' }} onClick={() => go('rooms')} data-testid="device-card">
      <span class="ico"><Icon d={PRODUCT_ICON[p]} size={30} sw={1.2} /></span>
      <span class="col gap4" style={{ minWidth: 0 }}>
        <span class="k">Aktivt rom</span>
        <span class="n ellip">{deviceName.value}</span>
        <span class="hw ellip">{PRODUCT_HW[p]}{s?.version ? ' · v' + s.version : ''}</span>
      </span>
      <span class="col gap6" style={{ alignItems: 'flex-end' }}>
        <span class="type-badge">{PRODUCT_SHORT[p]}</span>
        <span class="muted" style={{ fontSize: '11px' }}><i style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', marginRight: '5px', background: online.value ? 'var(--green)' : 'var(--red)' }} />{online.value ? (s?.power ? 'På' : 'Standby') : 'Frakoblet'}</span>
      </span>
    </button>
  );
}

// ---------- Equalizer ----------
export function EqPage() {
  const [src, setSrc] = useState<EqSource>(eqActiveSource.value);
  const prof = settings.value.eq[src];
  const c = eqCurve(prof.eq, 300, 90);
  const applies = applied.value.includes('eq');
  return (
    <div class="col gap16">
      {!applies && <div class="banner info"><span>Profilene lagres på {settingsSource.value === 'api' ? 'forsterkeren' : 'denne enheten'}. <strong>Kommer:</strong> EQ per kilde i CamillaDSP er ikke koblet til lyden ennå.</span></div>}
      <Section title="Profil for">
        <div class="chips">
          {EQ.sources.map(([k, n]) => <Chip key={k} on={src === k} dot={eqActiveSource.value === k ? true : undefined} onClick={() => setSrc(k)}>{n}</Chip>)}
        </div>
      </Section>
      <div class="eq-wrap">
        <svg viewBox="0 0 300 90" style={{ width: '100%', height: '90px' }} preserveAspectRatio="none">
          <path d={c.area} fill="rgba(217,164,65,0.12)" />
          <line x1="0" x2="300" y1={c.mid} y2={c.mid} stroke="#2e2e30" />
          <path d={c.line} fill="none" stroke="var(--accent)" stroke-width="2" />
        </svg>
        <div class="eq-bands">
          {EQ.bands.map((b, i) => (
            <div class="eq-band" key={b}>
              <span class="v">{(prof.eq[i] ?? 0) > 0 ? '+' : ''}{prof.eq[i] ?? 0}</span>
              <Slider vertical min={-12} max={12} value={prof.eq[i] ?? 0} label={b + ' Hz'}
                onCommit={(v) => { const eq = [...prof.eq]; eq[i] = v; setEqProfile(src, { eq, preset: -1 }); }} />
              <span class="f">{b}</span>
            </div>
          ))}
        </div>
      </div>
      <Section title="Forhåndsvalg">
        <div class="chips">
          {EQ.presets.map(([n, v], i) => <Chip key={n} sq on={prof.preset === i} onClick={() => setEqProfile(src, { preset: i, eq: [...v] })}>{n}</Chip>)}
        </div>
      </Section>
      <div class="list">
        <div class="item"><div><div class="n">Loudness for denne profilen</div><div class="hint">Loudness på forsterkeren styres under Innstillinger → Lyd</div></div>
          <div class="ctl"><button class={'toggle' + (prof.loud ? ' on' : '')} role="switch" aria-checked={prof.loud} onClick={() => setEqProfile(src, { loud: !prof.loud })} /></div></div>
      </div>
    </div>
  );
}

// ---------- Radio ----------
export function RadioPage() {
  const [list, setList] = useState<(FullPreset | null)[] | null>(null);
  const [lyrion, setLyrion] = useState(false);
  const [edit, setEdit] = useState<number | null>(null);
  const [draft, setDraft] = useState<FullPreset>({ title: '', url: '' });
  const load = () => api.presets().then((r) => { setList(r.presets); setLyrion(r.lyrion); }).catch(() => setList([]));
  useEffect(() => { void load(); }, []);
  const s = status.value;
  const save = async (next: (FullPreset | null)[]) => {
    try { const r = await api.setPresets(next); setList(r.presets); showToast('Favorittene er lagret'); } catch { showToast('Kunne ikke lagre favorittene'); }
  };
  const rows = Array.from({ length: 6 }, (_, i) => list?.[i] ?? null);
  return (
    <div class="col gap16">
      {!lyrion && <div class="banner warn"><span>Lyrion Music Server er ikke funnet. Favorittene kan redigeres, men radio spiller ikke før Lyrion kjører på nettet.</span></div>}
      <div class="row gap8">
        <button class="btn sm" onClick={async () => { try { const r = await api.importPresets(); setList(r.presets); showToast('Hentet favoritter fra Lyrion'); } catch { showToast('Fikk ikke hentet fra Lyrion'); } }}>Hent fra Lyrion</button>
        <span class="muted" style={{ fontSize: '12px' }}>Hold radioknappen: favoritt {settings.value.hold + 1}</span>
      </div>
      <div class="list">
        {rows.map((p, i) => edit === i ? (
          <div class="col gap8" style={{ padding: '12px 14px' }} key={i}>
            <input class="field" placeholder="Navn" value={draft.title} onInput={(e) => setDraft({ ...draft, title: e.currentTarget.value })} />
            <input class="field" placeholder="Strøm-URL (http…)" value={draft.url} onInput={(e) => setDraft({ ...draft, url: e.currentTarget.value })} />
            <div class="row gap8">
              <button class="btn sm primary" onClick={() => { const n = [...rows]; n[i] = draft.title || draft.url ? { ...draft } : null; setEdit(null); void save(n); }}>Lagre</button>
              <button class="btn sm" onClick={() => setEdit(null)}>Avbryt</button>
              {p && <button class="btn sm danger" onClick={() => { const n = [...rows]; n[i] = null; setEdit(null); void save(n); }}>Fjern</button>}
            </div>
          </div>
        ) : (
          <div class="item" key={i}>
            <div class="row gap10" style={{ minWidth: 0 }}>
              <span class="mono muted" style={{ width: '14px' }}>{i + 1}</span>
              <div class="col" style={{ minWidth: 0 }}><span class="n ellip">{p?.title || 'Tom plass'}</span>{p?.url && <span class="hint ellip">{p.url}</span>}</div>
            </div>
            <div class="ctl">
              {p && <button class={'btn sm' + (s?.input === 'radio' && s.preset === i + 1 ? ' primary' : '')} onClick={() => act(() => api.playPreset(i + 1), { input: 'radio', preset: i + 1 })}>Spill</button>}
              <button class="btn sm" title="Lagre det som spiller nå" onClick={() => api.savePreset(i + 1).then(() => { showToast('Lagret på plass ' + (i + 1)); void load(); }).catch(() => showToast('Ingenting å lagre'))}>Lagre nå</button>
              <button class="btn sm" onClick={() => { setDraft(p ?? { title: '', url: '' }); setEdit(i); }}>Rediger</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------- Rom ----------
const ADD: [Product, string][] = [
  ['s1', 'Forsterker med skjerm og knapper'],
  ['node', 'Pi med 1,8″ skjerm og knapper'],
  ['core', 'Ren Raspberry Pi – bare lyd']
];
export function RoomsPage() {
  const s = status.value;
  const cur = hostLabel();
  const others = knownDevices().filter((d) => d.base.replace(/^https?:\/\//, '') !== cur);
  const switchTo = async (base: string) => {
    setBase(base); reconnect(); await loadSettings(); showToast('Byttet rom');
  };
  return (
    <div class="col gap16">
      <Section title="Dine rom">
        <div class="list">
          <div class="room-row on">
            <span class="ico"><Icon d={PRODUCT_ICON[product.value]} size={22} sw={1.3} /></span>
            <span class="col" style={{ minWidth: 0 }}><span class="ellip" style={{ fontWeight: 600 }}>{deviceName.value}</span>
              <span class="muted ellip" style={{ fontSize: '12px' }}>{PRODUCT_LABEL[product.value]} · {s ? (s.power ? (s.playing ? 'Spiller' : 'På') + ' · volum ' + s.volume : 'Standby') : 'Ikke tilkoblet'}</span></span>
            <span class="type-badge">Aktiv</span>
          </div>
          {others.map((d) => {
            const p = productOf({ board: '', product: d.product ?? '' });
            return (
              <div class="room-row" key={d.base}>
                <span class="ico"><Icon d={PRODUCT_ICON[p]} size={22} sw={1.3} /></span>
                <button class="col" style={{ minWidth: 0, border: 'none', background: 'none', padding: 0, textAlign: 'left', color: 'var(--text)' }} onClick={() => void switchTo(d.base)}>
                  <span class="ellip" style={{ fontWeight: 600 }}>{d.name}</span>
                  <span class="muted ellip mono" style={{ fontSize: '11px' }}>{PRODUCT_SHORT[p]} · {d.base.replace(/^https?:\/\//, '')}</span>
                </button>
                <span class="row gap6"><button class="btn sm" onClick={() => void switchTo(d.base)}>Bytt</button><button class="btn sm" aria-label="Fjern" onClick={() => { forget(d.base); go('rooms'); showToast('Fjernet'); }}>×</button></span>
              </div>
            );
          })}
        </div>
      </Section>
      <Section title="Legg til enhet">
        <div class="add-grid">
          {ADD.map(([p, d]) => (
            <button key={p} class="add-card" data-testid={'add-' + p} onClick={() => { mode.value = 'find'; }}>
              <span class="ico"><Icon d={PRODUCT_ICON[p]} size={28} sw={1.2} /></span>
              <span class="t">{PRODUCT_LABEL[p]}</span>
              <span class="d">{d}</span>
            </button>
          ))}
        </div>
        <button class="btn primary big" onClick={() => { mode.value = 'find'; }} data-testid="add-device">+ Legg til enhet</button>
      </Section>
      <div class="banner info"><span>Grupper og synkronisert avspilling i flere rom settes opp i Lyrion.</span></div>
    </div>
  );
}

/** Liten hjelpekrok for å holde en lerret-tegning oppdatert hvert minutt. */
export function useMinuteTick(): number {
  const [t, setT] = useState(Date.now());
  const ref = useRef(0);
  useEffect(() => { ref.current = window.setInterval(() => setT(Date.now()), 30000); return () => clearInterval(ref.current); }, []);
  return t;
}
