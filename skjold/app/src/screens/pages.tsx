// Sider som deles av telefon- og PC-skallet.
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, type FullPreset } from '../lib/api';
import { act, eqActiveSource, go, setEqProfile, settings, showToast, status, applied, settingsSource } from '../lib/store';
import { EQ, eqCurve, type EqSource } from '../lib/settings';
import { Chip, Section, Slider } from '../components/ui';
import { Art, InputChips, PresetTiles, nowTitle, VolumeRow, Transport } from './player';

// ---------- Hjem ----------
export function HomePage({ wide = false }: { wide?: boolean }) {
  const s = status.value;
  const t = nowTitle(s);
  return (
    <div class="col gap16">
      {!wide && (
        <div class="card pad col gap12">
          <div class="row gap12">
            <div style={{ width: '64px', flexShrink: 0 }}><Art s={s} size="small" /></div>
            <div class="col grow"><span class="ellip" style={{ fontWeight: 600, fontSize: '16px' }}>{t.title}</span><span class="ellip muted">{t.sub}</span></div>
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
export function RoomsPage() {
  const s = status.value;
  return (
    <div class="col gap16">
      <div class="banner info"><span><strong>Kommer:</strong> grupper og synkronisert avspilling i flere rom (via Lyrion). Forsterkeren har ikke API for dette ennå.</span></div>
      <div class="list">
        <div class="item"><div><div class="n">{s?.name || 'Skjold S1'}</div><div class="hint">{s ? (s.power ? 'Spiller · volum ' + s.volume : 'Standby') : 'Ikke tilkoblet'}</div></div><div class="ctl"><span class="val">Dette rommet</span></div></div>
      </div>
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
