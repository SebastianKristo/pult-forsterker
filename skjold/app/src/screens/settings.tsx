// Innstillinger: kategoriliste + detaljside, generert fra CATS i lib/settings.ts.
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, cmpVersion, fetchLatestRelease, hostLabel, isNative, type LevelSource, type Release } from '../lib/api';
import { act, applied, go, localOnly, mode, product, route, setSetting, settings, settingsSource, showToast, status } from '../lib/store';
import { computed } from '@preact/signals';
import { CAT_TILE, ICONS, catsFor, fmt, type Category, type Item } from '../lib/settings';

export const cats = computed(() => catsFor(product.value, status.value?.inputs ?? []));
import { CLOCKS, drawClock } from '../lib/clocks';
import { ConfirmButton, Icon, Slider, Stepper, Toggle } from '../components/ui';
import { EqPage, RoomsPage, useMinuteTick } from './pages';
import { AppUpdater, canSelfUpdate, fetchLatestAppRelease, installedAppVersion, isNewer, type AppRelease } from '../lib/appUpdate';

export function SettingsPage({ wide = false }: { wide?: boolean }) {
  const cat = cats.value.find((c) => c.id === route.value.cat);
  if (!cat) return <CategoryList />;
  return (
    <div class="col gap12">
      {!wide && <button class="link" style={{ alignSelf: 'flex-start' }} onClick={() => go('settings')}>‹ Innstillinger</button>}
      <CategoryDetail cat={cat} wide={wide} />
    </div>
  );
}

export function CategoryList() {
  return (
    <div class="list">
      {cats.value.map((c) => (
        <button key={c.id} class="cat-row" onClick={() => go('settings', c.id)}>
          <div class="row gap12">
            <span class="ico" style={{ background: CAT_TILE[c.id] }}><Icon d={ICONS[c.id] ?? ''} size={17} /></span>
            <div class="col" style={{ minWidth: 0 }}><span>{c.n}</span><span class="muted ellip" style={{ fontSize: '12px' }}>{c.sub}</span></div>
          </div>
          <span class="muted">›</span>
        </button>
      ))}
    </div>
  );
}

export function CategoryDetail({ cat, wide }: { cat: Category; wide: boolean }) {
  if (cat.id === 'eq') return <EqPage />;
  if (cat.id === 'rom') return <RoomsPage />;
  const items = cat.items.filter((it) => !(it.kind === 'clocks' && !settings.value.clock));
  return (
    <div class="col gap12">
      {wide ? null : <span style={{ fontSize: '22px', fontWeight: 600 }}>{cat.n}</span>}
      <div class="list">{items.map((it, i) => <Row key={i} it={it} />)}</div>
      {settingsSource.value === 'local' && <div class="banner warn"><span>Forsterkeren svarer ikke på /api/settings – endringer lagres bare på denne enheten.</span></div>}
    </div>
  );
}

function pending(k: string): string | undefined {
  if (localOnly.value.includes(k)) return 'Lagres på denne enheten';
  if (settingsSource.value === 'api' && applied.value.length && !applied.value.includes(k)) return 'Lagres – styrer ikke forsterkeren ennå';
  return undefined;
}

function Line({ n, hint, note, children, wideCtl = false }: { n: string; hint?: string | undefined; note?: string | undefined; children?: preact.ComponentChildren; wideCtl?: boolean }) {
  return (
    <div class="item" style={wideCtl ? { gridTemplateColumns: '1fr' } : undefined}>
      <div><div class="n">{n}</div>{hint && <div class="hint">{hint}</div>}{note && <div class="hint" style={{ color: 'var(--accent-text)' }}>{note}</div>}</div>
      <div class="ctl">{children}</div>
    </div>
  );
}

function Row({ it }: { it: Item }) {
  const st = settings.value, s = status.value;
  switch (it.kind) {
    case 'num':
      return <Line n={it.n} hint={it.hint} note={pending(it.k)}><Stepper value={st[it.k]} min={it.mn} max={it.mx} fmt={fmt[it.f]} onChange={(v) => setSetting(it.k, v)} /></Line>;
    case 'opt':
      return (
        <Line n={it.n} hint={it.hint} note={pending(it.k)}>
          <select class="field sm" value={st[it.k]} aria-label={it.n} data-key={it.k} onChange={(e) => { setSetting(it.k, +e.currentTarget.value); if (it.k === 'name' && st.nameCustom) setSetting('nameCustom', ''); }}>
            {it.list.map((o, i) => <option key={i} value={i}>{o}</option>)}
          </select>
        </Line>
      );
    case 'bool':
      return <Line n={it.n} hint={it.hint} note={pending(it.k)}><Toggle on={st[it.k]} label={it.n} onChange={(v) => setSetting(it.k, v)} /></Line>;
    case 'str':
      return <Line n={it.n} hint={it.hint} note={pending(it.k)}><input class="field sm" value={st[it.k]} placeholder={it.ph} maxLength={it.k === 'nameCustom' ? 24 : 16} data-key={it.k} onChange={(e) => setSetting(it.k, e.currentTarget.value.trim())} /></Line>;
    case 'api-bool': {
      const map = {
        loudness: [!!s?.loudness, (v: boolean) => act(() => api.loudness(v), { loudness: v })],
        mix: [!!s?.mix, (v: boolean) => act(() => api.mix(v), { mix: v })],
        autoInput: [!!s?.auto_input, (v: boolean) => act(() => api.autoInput(v), { auto_input: v })],
        hpAutomute: [!!s?.hp_automute, (v: boolean) => act(() => api.hpAutomute(v), { hp_automute: v })],
        voiceOn: [!!s?.voice, (v: boolean) => act(() => api.voice({ on: v }), { voice: v })]
      } as const;
      const [on, fn] = map[it.id];
      return <Line n={it.n} hint={it.hint}><Toggle on={on} label={it.n} onChange={(v) => void fn(v)} /></Line>;
    }
    case 'api-opt':
      if (it.id === 'loudLevel') return <Line n={it.n}><Stepper value={s?.loudness_level ?? 5} min={0} max={10} fmt={(v) => String(v)} onChange={(v) => act(() => api.loudness(undefined, v), { loudness_level: v })} /></Line>;
      if (it.id === 'usbPc') {
        const names = s?.usb_names?.length ? s.usb_names : [st.nUsb1, st.nUsb2];
        return <Line n={it.n} hint={it.hint}>{[1, 2].map((pc) => <button key={pc} class={'btn sm' + (s?.usb_pc === pc ? ' primary' : '')} onClick={() => act(() => api.usbsw(pc as 1 | 2), { usb_pc: pc })}>{names[pc - 1]}</button>)}</Line>;
      }
      return (
        <Line n={it.n}>
          <select class="field sm" value={s?.voice_profile ?? ''} aria-label={it.n} onChange={(e) => act(() => api.voice({ profile: e.currentTarget.value }))}>
            {Object.entries(s?.voice_profiles ?? {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Line>
      );
    case 'levels': {
      const lv = s?.levels ?? {};
      return (
        <Line n={it.n} hint={it.hint} wideCtl>
          <div class="col gap8" style={{ width: '100%' }}>
            {Object.keys(lv).map((k) => (
              <div class="row gap10" key={k}><span class="mono muted" style={{ width: '64px', fontSize: '11px' }}>{k.toUpperCase()}</span>
                <Slider value={lv[k] ?? 100} label={'Nivå ' + k} onCommit={(v) => act(() => api.level(k as LevelSource, v), { levels: { ...lv, [k]: v } })} />
                <span class="mono" style={{ width: '3ch', fontSize: '12px' }}>{lv[k]}</span></div>
            ))}
          </div>
        </Line>
      );
    }
    case 'info': {
      const v: Record<typeof it.key, string> = {
        btDev: s?.bt_device || 'Ingen', lyrion: s?.lyrion ? 'Tilkoblet' : 'Ikke funnet', version: s?.version ?? '–', ip: hostLabel(),
        id: s?.id ?? '–', board: s?.board ?? '–', headphones: s?.headphones ? 'Tilkoblet' : 'Ikke tilkoblet', btPairing: s?.bt_pairing ? 'Synlig' : 'Av',
        inputs: (s?.inputs ?? []).join(', '),
        output: product.value === 'core' ? 'Pi-ens lydutgang (3,5 mm / HDMI / DAC)' : product.value === 'node' ? '3,5 mm' : 'Høyttalerklemmer'
      };
      if (it.key === 'board') return <Line n={it.n}><span class="val">{({ s1: 'Skjold S1', node: 'Skjold Node', core: 'Skjold Core' })[product.value]} ({s?.board ?? '–'})</span></Line>;
      return <Line n={it.n}><span class="val">{v[it.key]}</span></Line>;
    }
    case 'act': {
      const run: Record<typeof it.id, () => void> = {
        btPair: () => act(() => api.btPairing(), { bt_pairing: true }),
        openRadio: () => go('radio'),
        setup: () => { mode.value = 'setup'; },
        findDevice: () => { mode.value = 'find'; },
        testVoice: () => act(() => api.voice({ say: 'bt_pairing' })),
        forget: () => showToast('Kommer: forsterkeren har ikke API for å glemme Blåtann-enheter ennå'),
        reset: () => showToast('Kommer: fabrikkinnstillinger er ikke i API-et ennå'),
        reboot: () => showToast('Kommer: omstart er ikke i API-et ennå')
      };
      if (it.id === 'findDevice' && !isNative) return null;
      return <Line n={it.n} hint={it.hint}><ConfirmButton label={it.label} safe={it.safe} onConfirm={run[it.id]} /></Line>;
    }
    case 'test':
      return <Line n={it.n} hint={it.hint}><SpeakerTest /></Line>;
    case 'clocks':
      return <Line n="Klokkestil" note={pending('clockStyle')} wideCtl><ClockPicker /></Line>;
    case 'update':
      return <><UpdatePanel />{canSelfUpdate && <AppUpdatePanel />}</>;
    case 'eq':
      return null;
  }
}

function SpeakerTest() {
  const [res, setRes] = useState<Record<string, string>>({});
  const test = async (ch: 'L' | 'R') => {
    try { await api.speakerTest(ch); setRes((r) => ({ ...r, [ch]: '✓' })); }
    catch { setRes((r) => ({ ...r, [ch]: '–' })); showToast('Kommer: høyttalertest finnes ikke i API-et ennå'); }
  };
  return <>{(['L', 'R'] as const).map((ch) => <button key={ch} class="btn sm" data-testid={'test-' + ch} onClick={() => void test(ch)}>{ch === 'L' ? 'Venstre' : 'Høyre'}{res[ch] ? ' ' + res[ch] : ''}</button>)}</>;
}

function ClockCanvas({ style }: { style: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const t = useMinuteTick();
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const g = c.getContext('2d'); if (!g) return;
    g.clearRect(0, 0, c.width, c.height); drawClock(g, c.width, c.height, style, new Date(t));
  }, [style, t]);
  return <canvas ref={ref} width={256} height={128} />;
}

function ClockPicker() {
  const cur = settings.value.clockStyle;
  return (
    <div class="clock-grid" style={{ width: '100%' }}>
      {CLOCKS.map((n, i) => <button key={n} class={'clock-btn' + (cur === i ? ' on' : '')} onClick={() => setSetting('clockStyle', i)}><ClockCanvas style={i} /><span>{n}</span></button>)}
    </div>
  );
}

function UpdatePanel() {
  const st = settings.value, s = status.value;
  const [rel, setRel] = useState<Release | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const check = async () => {
    setBusy(true); setErr('');
    try { setRel(await fetchLatestRelease(st.updChannel === 1)); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  };
  const cur = s?.version ?? '0';
  const newer = rel && cmpVersion(rel.tag.replace(/^skjold-/, ''), cur) > 0;
  return (
    <>
      <Line n="Programvare på forsterkeren"><span class="val">{cur}</span></Line>
      <Line n="Kanal" note={pending('updChannel')}>
        <select class="field sm" value={st.updChannel} aria-label="Kanal" onChange={(e) => setSetting('updChannel', +e.currentTarget.value)}><option value={0}>Stabil</option><option value={1}>Beta</option></select>
      </Line>
      <Line n="Oppdater automatisk" note={pending('updAuto')}><Toggle on={st.updAuto} onChange={(v) => setSetting('updAuto', v)} /></Line>
      <div class="col gap10" style={{ padding: '12px 14px' }}>
        <button class="btn" disabled={busy} onClick={check}>{busy ? 'Ser etter …' : 'Se etter oppdatering'}</button>
        {err && <div class="banner bad"><span>{err}</span></div>}
        {rel === null && <div class="banner info"><span>Ingen utgivelser funnet på GitHub.</span></div>}
        {rel && (
          <div class={'banner ' + (newer ? 'warn' : 'ok')}>
            <span><strong>{rel.name}</strong> · {rel.date}{rel.size ? ' · ' + rel.size : ''}<br />{newer ? 'Ny versjon tilgjengelig. Installering fra appen kommer – last ned fra GitHub inntil videre.' : 'Forsterkeren er oppdatert.'}</span>
            <a href={rel.url} target="_blank" rel="noreferrer">Åpne</a>
          </div>
        )}
      </div>
    </>
  );
}

/** Android: last ned og installer ny versjon av selve appen fra GitHub Releases. */
function AppUpdatePanel() {
  const st = settings.value;
  const [cur, setCur] = useState('');
  const [rel, setRel] = useState<AppRelease | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [pct, setPct] = useState<number | null>(null);
  const [err, setErr] = useState('');
  const [needPerm, setNeedPerm] = useState(false);
  useEffect(() => { void installedAppVersion().then(setCur); }, []);
  const check = async () => {
    setBusy(true); setErr('');
    try { setRel(await fetchLatestAppRelease(st.updChannel === 1)); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  };
  const install = async () => {
    if (!rel) return;
    setErr('');
    const { allowed } = await AppUpdater.canInstall();
    if (!allowed) { setNeedPerm(true); await AppUpdater.openInstallSettings(); return; }
    setNeedPerm(false); setPct(0);
    const h = await AppUpdater.addListener('progress', (e) => setPct(e.percent));
    try { await AppUpdater.downloadAndInstall({ url: rel.apkUrl }); showToast('Følg installasjonen på skjermen'); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
    finally { void h.remove(); setPct(null); }
  };
  const newer = rel ? isNewer(rel, cur) : false;
  return (
    <>
      <Line n="Appen på denne telefonen"><span class="val">{cur || '–'}</span></Line>
      <div class="col gap10" style={{ padding: '12px 14px' }}>
        <button class="btn" disabled={busy || pct !== null} onClick={check}>{busy ? 'Ser etter …' : 'Se etter ny app-versjon'}</button>
        {err && <div class="banner bad"><span>{err}</span></div>}
        {rel === null && <div class="banner info"><span>Ingen app-utgivelser funnet på GitHub.</span></div>}
        {rel && (
          <div class={'banner ' + (newer ? 'warn' : 'ok')}>
            <span><strong>{rel.name}</strong> · {rel.date} · {rel.apkSize}<br />{newer ? `Versjon ${rel.version} er klar (du har ${cur || 'ukjent'}).` : 'Appen er oppdatert.'}</span>
          </div>
        )}
        {rel && newer && (
          <button class="btn primary" disabled={pct !== null} onClick={install}>
            {pct !== null ? `Laster ned … ${pct} %` : `Last ned og installer ${rel.version}`}
          </button>
        )}
        {needPerm && <div class="banner info"><span>Tillat «Installer ukjente apper» for Skjold i innstillingene som åpnet seg, gå tilbake og trykk på knappen igjen.</span></div>}
      </div>
    </>
  );
}
