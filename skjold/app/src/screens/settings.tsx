// Innstillinger: kategoriliste + detaljside, generert fra CATS i lib/settings.ts.
import { useEffect, useRef, useState } from 'preact/hooks';
import { api, cmpVersion, fetchLatestRelease, hostLabel, isNative, REPO, type LevelSource, type Release } from '../lib/api';
import { act, applied, go, localOnly, mode, product, route, setSetting, settings, settingsSource, showToast, status } from '../lib/store';
import { computed } from '@preact/signals';
import { CAT_TILE, ICONS, catsFor, fmt, type Category, type Item } from '../lib/settings';

export const cats = computed(() => catsFor(product.value, status.value?.inputs ?? []));
import { CLOCKS, drawClock } from '../lib/clocks';
import { Icon, PRODUCT_ICON, Slider, Toggle } from '../components/ui';
import { nbHw, useMinuteTick } from './pages';
import { useRooms, switchRoom } from './phone';
import { ob } from './onboard';
import { getLocal, setLocal } from '../lib/services';
import { ndConfigured, ndError, ndPing } from '../lib/navidrome';
import { RadioFavorites } from './radio';
import { favs } from '../lib/radio';
import { PRODUCT_HW, PRODUCT_LABEL } from '../lib/api';
import { Chevron } from '../components/ui';
import { AppUpdater, canSelfUpdate, fetchLatestAppRelease, installedAppVersion, isNewer, type AppRelease } from '../lib/appUpdate';

export function SettingsPage({ wide = false }: { wide?: boolean }) {
  const cat = cats.value.find((c) => c.id === route.value.cat);
  if (!cat) return <CategoryList />;
  return (
    <>
      {!wide && <button onClick={() => go('settings')} style="align-self:flex-start;display:flex;align-items:center;gap:4px;border:none;background:none;color:#d9a441;font-size:14px;cursor:pointer;padding:0"><Chevron dir="left" />Innstillinger</button>}
      <CategoryDetail cat={cat} wide={wide} />
    </>
  );
}

const A = '#d9a441';
const sel = (b: boolean) => ({ bd: b ? A : '#2e2e30', bg: b ? '#1c170d' : '#141415', fg: b ? '#f0c46a' : '#f2f2ee' });
const CARD = 'display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;flex-shrink:0';

export function CategoryList() {
  const rooms = useRooms();
  const p = product.value;
  return (
    <>
      {rooms.length > 1 && <div class="dsc" style="display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px;flex-shrink:0">
        {rooms.map((r) => { const c = sel(r.active); return (
          <button key={r.key} onClick={() => { if (!r.active) void switchRoom(r.base); }} style={`display:flex;flex-direction:column;align-items:flex-start;gap:1px;padding:8px 12px;border-radius:12px;border:1px solid ${c.bd};background:${c.bg};cursor:pointer;flex-shrink:0;text-align:left`}>
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#c9c9c4" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[r.product]} /></svg>
            <span style={`font-size:13px;color:${c.fg};white-space:nowrap`}>{r.name}</span><span style="font-family:'IBM Plex Mono',monospace;font-size:9.5px;color:#8b8b86;white-space:nowrap">{PRODUCT_LABEL[r.product]}</span>
          </button>
        ); })}
      </div>}
      <span style="font-size:11px;color:#8b8b86">{nbHw(PRODUCT_HW[p])}{p === 'node' ? ' · ingen skjerm eller knapper' : ''}</span>
      <div style={CARD}>
        {cats.value.map((c, i) => (
          <button key={c.id} class="cat-row" onClick={() => go('settings', c.id)} style={`display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;min-height:58px;padding:8px 14px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:transparent;cursor:pointer;text-align:left`}>
            <span style="display:flex;align-items:center;gap:12px;min-width:0">
              <span style={`width:32px;height:32px;border-radius:8px;background:${CAT_TILE[c.id] ?? '#333'};display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#f2f2ee`}>{ICONS[c.id] ? <Icon d={ICONS[c.id] ?? ''} size={18} /> : null}</span>
              <span style="flex:1 1 auto;display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px">{c.n}</span><span style="font-size:11px;color:#8b8b86">{c.sub}</span></span>
            </span>
            <Chevron color="#8b8b86" />
          </button>
        ))}
      </div>
    </>
  );
}

export function CategoryDetail({ cat, wide }: { cat: Category; wide: boolean }) {
  if (cat.id === 'oppdatering') return <><UpdatePanel />{canSelfUpdate && <AppUpdatePanel />}</>;
  const items = cat.items.filter((it) => it.kind !== 'clocks' && it.kind !== 'update');
  const hasClocks = cat.items.some((it) => it.kind === 'clocks');
  return (
    <>
      {cat.id === 'radio' ? <>
        <span style={`flex-shrink:0;font-size:${wide ? '18px' : '17px'};font-weight:600`}>Favoritter</span>
        <RadioFavorites wide={wide} />
        <span style={`flex-shrink:0;font-size:${wide ? '18px' : '17px'};font-weight:600;margin-top:6px`}>Knapper og oppstart</span>
      </> : null}
      {hasClocks && settings.value.clock && <ClockPicker />}
      <div style={CARD}>{items.map((it, i) => <Row key={i} it={it} i={i} />)}</div>
      {settingsSource.value === 'local' && <div class="banner warn"><span>Forsterkeren svarer ikke på /api/settings – endringer lagres bare på denne enheten.</span></div>}
    </>
  );
}

function pending(k: string): string | undefined {
  if (localOnly.value.includes(k)) return 'Lagres på denne enheten';
  if (settingsSource.value === 'api' && applied.value.length && !applied.value.includes(k)) return 'Lagres – styrer ikke forsterkeren ennå';
  return undefined;
}

/** Én innstillingsrad (design: setItems). ctl = kontrollen til høyre, below = det som ligger under (felt, valg, steg). */
function Line({ n, hint, note, i, children, below }: { n: string; hint?: string | undefined; note?: string | undefined; i: number; children?: preact.ComponentChildren; below?: preact.ComponentChildren }) {
  return (
    <div style={`display:flex;flex-direction:column;gap:8px;padding:12px 14px;border-top:1px solid ${i ? '#242426' : 'transparent'}`}>
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;min-height:30px">
        <span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px">{n}</span>{hint && <span style="font-size:11px;color:#8b8b86;text-wrap:pretty">{hint}</span>}{note && <span style="font-size:11px;color:#c9b48a">{note}</span>}</span>
        {children}
      </div>
      {below}
    </div>
  );
}
const BTN = (bd = '#2e2e30', fg = '#f2f2ee') => `height:32px;padding:0 12px;border-radius:8px;border:1px solid ${bd};background:#1b1b1c;color:${fg};font-size:12px;cursor:pointer;white-space:nowrap;flex-shrink:0`;
const VAL = "font-family:'IBM Plex Mono',monospace;font-size:12px;color:#c9c9c4;text-align:right";

function Row({ it, i }: { it: Item; i: number }) {
  const st = settings.value, s = status.value;
  switch (it.kind) {
    case 'num':
      return <Line i={i} n={it.n} hint={it.hint} note={pending(it.k)}><Num value={st[it.k]} min={it.mn} max={it.mx} fmt={fmt[it.f]} onChange={(v) => setSetting(it.k, v)} /></Line>;
    case 'opt': {
      const list = it.k === 'hold' ? favs.value.map((f) => f.title) : it.list;
      const value = it.k === 'hold' ? favs.value.findIndex((f) => f.n - 1 === st.hold) : st[it.k];
      return <Opt i={i} n={it.n} hint={it.hint} note={pending(it.k)} list={list} value={value}
        onPick={(v) => { if (it.k === 'hold') { const f = favs.value[v]; if (f) setSetting('hold', f.n - 1); } else setSetting(it.k, v); if (it.k === 'name' && st.nameCustom) setSetting('nameCustom', ''); }} />;
    }
    case 'bool':
      return <Line i={i} n={it.n} hint={it.hint} note={pending(it.k)}><Toggle on={st[it.k]} label={it.n} onChange={(v) => setSetting(it.k, v)} /></Line>;
    case 'str':
      return <Line i={i} n={it.n} hint={it.hint} note={pending(it.k)}><input value={st[it.k]} placeholder={it.ph} maxLength={it.k === 'nameCustom' ? 24 : 14} data-key={it.k} onChange={(e) => setSetting(it.k, e.currentTarget.value.trim())} style="height:34px;width:130px;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;flex-shrink:0" /></Line>;
    case 'local': {
      const v = getLocal(it.k);
      const inp = (w: string) => <input type={it.secret ? 'password' : 'text'} value={v} placeholder={it.ph} autoCapitalize="off" autoCorrect="off" spellcheck={false} data-key={it.k} onChange={(e) => setLocal(it.k, e.currentTarget.value)} style={`height:${it.long ? 40 : 34}px;width:${w};box-sizing:border-box;padding:0 ${it.long ? 12 : 10}px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;flex-shrink:0`} />;
      return it.long ? <Line i={i} n={it.n} hint={it.hint} below={inp('100%')} /> : <Line i={i} n={it.n} hint={it.hint}>{inp('130px')}</Line>;
    }
    case 'steps':
      return <Line i={i} n={it.n} below={<div style="display:flex;flex-direction:column;gap:8px">{it.steps.map((t, j) => <div key={j} style="display:grid;grid-template-columns:18px minmax(0,1fr);gap:8px;font-size:12px;color:#c9c9c4;line-height:1.45"><span style="font-family:'IBM Plex Mono',monospace;color:#d9a441">{j + 1}</span><span style="text-wrap:pretty">{t}</span></div>)}</div>} />;
    case 'svc':
      return <Line i={i} n={it.n}><SvcTest id={it.id} label={it.label} /></Line>;
    case 'api-bool': {
      const map = {
        loudness: [!!s?.loudness, (v: boolean) => act(() => api.loudness(v), { loudness: v })],
        mix: [!!s?.mix, (v: boolean) => act(() => api.mix(v), { mix: v })],
        autoInput: [!!s?.auto_input, (v: boolean) => act(() => api.autoInput(v), { auto_input: v })],
        hpAutomute: [!!s?.hp_automute, (v: boolean) => act(() => api.hpAutomute(v), { hp_automute: v })],
        voiceOn: [!!s?.voice, (v: boolean) => act(() => api.voice({ on: v }), { voice: v })]
      } as const;
      const [on, fn] = map[it.id];
      return <Line i={i} n={it.n} hint={it.hint}><Toggle on={on} label={it.n} onChange={(v) => void fn(v)} /></Line>;
    }
    case 'api-opt':
      if (it.id === 'loudLevel') return <Line i={i} n={it.n}><Num value={s?.loudness_level ?? 5} min={0} max={10} fmt={(v) => String(v)} onChange={(v) => act(() => api.loudness(undefined, v), { loudness_level: v })} /></Line>;
      if (it.id === 'usbPc') {
        const names = s?.usb_names?.length ? s.usb_names : [st.nUsb1, st.nUsb2];
        return <Opt i={i} n={it.n} hint={it.hint} list={names.slice(0, 2)} value={(s?.usb_pc ?? 1) - 1} onPick={(v) => act(() => api.usbsw((v + 1) as 1 | 2), { usb_pc: v + 1 })} />;
      }
      {
        const prof = Object.entries(s?.voice_profiles ?? {});
        return <Opt i={i} n={it.n} list={prof.map(([, v]) => v)} value={Math.max(0, prof.findIndex(([k]) => k === s?.voice_profile))} onPick={(v) => { const k = prof[v]?.[0]; if (k) void act(() => api.voice({ profile: k })); }} />;
      }
    case 'levels': {
      const lv = s?.levels ?? {};
      return (
        <Line i={i} n={it.n} hint={it.hint} below={
          <div style="display:flex;flex-direction:column;gap:8px">
            {Object.keys(lv).map((k) => (
              <div key={k} style="display:grid;grid-template-columns:64px minmax(0,1fr) 3ch;gap:10px;align-items:center"><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#8b8b86">{k.toUpperCase()}</span>
                <Slider value={lv[k] ?? 100} label={'Nivå ' + k} onCommit={(v) => act(() => api.level(k as LevelSource, v), { levels: { ...lv, [k]: v } })} />
                <span style="font-family:'IBM Plex Mono',monospace;font-size:12px">{lv[k]}</span></div>
            ))}
          </div>} />
      );
    }
    case 'info': {
      const v: Record<typeof it.key, string> = {
        btDev: s?.bt_device || 'Ingen', lyrion: s?.lyrion ? 'Tilkoblet' : 'Ikke funnet', version: s?.version ?? '–', ip: hostLabel(),
        id: s?.id ?? '–', board: ({ s1: 'Skjold S1', node: 'Skjold Node', core: 'Skjold Core' })[product.value] + ' (' + (s?.board ?? '–') + ')', headphones: s?.headphones ? 'Tilkoblet' : 'Ikke tilkoblet', btPairing: s?.bt_pairing ? 'Synlig' : 'Av',
        inputs: (s?.inputs ?? []).join(', '), netName: 'Skjold · ' + (s?.name ?? 'romnavn'), poToken: 'Ikke tilkoblet',
        output: product.value === 'core' ? 'Pi-ens lydutgang (3,5 mm / HDMI / DAC)' : product.value === 'node' ? '3,5 mm' : 'Høyttalerklemmer'
      };
      return <Line i={i} n={it.n} hint={it.hint}><span style={VAL}>{v[it.key]}</span></Line>;
    }
    case 'act': {
      const run: Record<typeof it.id, () => void> = {
        btPair: () => act(() => api.btPairing(), { bt_pairing: true }),
        setup: () => { ob.step.value = 1; mode.value = 'setup'; },
        findDevice: () => { mode.value = 'find'; },
        testVoice: () => act(() => api.voice({ say: 'bt_pairing' })),
        forget: () => showToast('Forsterkeren har ikke API for å glemme Blåtann-enheter ennå'),
        reset: () => showToast('Fabrikkinnstillinger er ikke i API-et ennå'),
        reboot: () => act(() => api.reboot() as never)
      };
      if (it.id === 'findDevice' && !isNative) return null;
      return <Line i={i} n={it.n} hint={it.hint}><Confirm label={it.label} safe={!!it.safe} onConfirm={run[it.id]} /></Line>;
    }
    case 'test':
      return <Line i={i} n={it.n} hint={it.hint}><div style="display:flex;gap:6px"><SpeakerTest /></div></Line>;
    case 'eq':
      return <Line i={i} n={it.n}><button onClick={() => go('eq')} style="border:none;background:none;color:#d9a441;font-size:13px;cursor:pointer;padding:0">Åpne ›</button></Line>;
    case 'clocks': case 'update':
      return null;
  }
}

function Num({ value, min, max, fmt: f, onChange }: { value: number; min: number; max: number; fmt: (v: number) => string; onChange: (v: number) => void }) {
  const b = 'width:32px;height:32px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;cursor:pointer';
  return (
    <div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
      <button aria-label="Mindre" onClick={() => onChange(Math.max(min, value - 1))} style={b}>−</button>
      <span style="min-width:52px;text-align:center;font-family:'IBM Plex Mono',monospace;font-size:12px">{f(value)}</span>
      <button aria-label="Mer" onClick={() => onChange(Math.min(max, value + 1))} style={b}>+</button>
    </div>
  );
}

function Opt({ n, hint, note, list, value, i, onPick }: { n: string; hint?: string | undefined; note?: string | undefined; list: string[]; value: number; i: number; onPick: (v: number) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Line i={i} n={n} hint={hint} note={note} below={open ? (
      <div style="display:flex;gap:6px;flex-wrap:wrap">{list.map((o, j) => { const c = sel(value === j); return <button key={j} onClick={() => { onPick(j); setOpen(false); }} style={`height:34px;padding:0 12px;border-radius:999px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:12px;cursor:pointer;white-space:nowrap`}>{o}</button>; })}</div>
    ) : null}>
      <button onClick={() => setOpen(!open)} style="border:none;background:none;color:#8b8b86;font-size:13px;cursor:pointer;white-space:nowrap;flex-shrink:0;padding:0;max-width:55%;overflow:hidden;text-overflow:ellipsis">{list[value] ?? '–'} {open ? '⌃' : '›'}</button>
    </Line>
  );
}

function Confirm({ label, safe, onConfirm }: { label: string; safe: boolean; onConfirm: () => void }) {
  const [armed, setArmed] = useState(false);
  useEffect(() => { if (!armed) return; const t = setTimeout(() => setArmed(false), 4000); return () => clearTimeout(t); }, [armed]);
  return <button onClick={() => { if (safe || armed) { setArmed(false); onConfirm(); } else setArmed(true); }} style={BTN(armed ? '#e05a4a' : '#2e2e30', armed ? '#ff8a7a' : '#f2f2ee')}>{armed ? 'Trykk igjen' : label}</button>;
}

function SvcTest({ id, label }: { id: 'ytmTest' | 'ndTest'; label: string }) {
  const [r, setR] = useState<[string, string] | null>(null);
  const run = async () => {
    if (id === 'ytmTest') { setR(['Ikke tilkoblet · krever Music Assistant', '#ff8a7a']); return; }
    if (!ndConfigured()) { setR(['Fyll inn server, brukernavn og passord', '#ff8a7a']); return; }
    setR(['Tester …', '#c9c9c4']);
    setR((await ndPing()) ? ['Innlogget', '#6fcf7f'] : [ndError.value || 'Feil', '#ff8a7a']);
  };
  return <button onClick={() => void run()} style={BTN(r && r[1] === '#ff8a7a' ? '#5a2620' : '#2e2e30', r ? r[1] : '#f2f2ee') + ';max-width:60%;overflow:hidden;text-overflow:ellipsis'}>{r ? r[0] : label}</button>;
}

function SpeakerTest() {
  const [res, setRes] = useState<Record<string, string>>({});
  const test = async (ch: 'L' | 'R') => {
    try { await api.speakerTest(ch); setRes((r) => ({ ...r, [ch]: '✓' })); }
    catch { setRes((r) => ({ ...r, [ch]: '–' })); showToast('Forsterkeren kunne ikke spille testtonen'); }
  };
  return <>{(['L', 'R'] as const).map((ch) => <button key={ch} class="btn sm" data-testid={'test-' + ch} onClick={() => void test(ch)}>{ch === 'L' ? 'Venstre' : 'Høyre'}{res[ch] ? ' ' + res[ch] : ''}</button>)}</>;
}

function ClockCanvas({ style, on }: { style: number; on: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const t = useMinuteTick();
  useEffect(() => {
    const c = ref.current; if (!c) return;
    const g = c.getContext('2d'); if (!g) return;
    g.fillStyle = '#000'; g.fillRect(0, 0, c.width, c.height); drawClock(g, c.width, c.height, style, new Date(t), on ? '#e8e8e2' : '#8b8b86');
  }, [style, t, on]);
  return <canvas ref={ref} width={256} height={128} style="width:100%;aspect-ratio:2/1;background:#000;border-radius:6px;display:block" />;
}

function ClockPicker() {
  const cur = settings.value.clockStyle;
  return (
    <div style="display:flex;flex-direction:column;gap:10px;flex-shrink:0">
      <span style="font-size:14px;font-weight:600">Klokkestil i standby</span>
      <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:10px">
        {CLOCKS.map((n, i) => { const on = cur === i; return (
          <button key={n} onClick={() => setSetting('clockStyle', i)} style={`display:flex;flex-direction:column;gap:8px;padding:8px;border-radius:14px;border:1px solid ${on ? A : '#242426'};background:${on ? '#1c170d' : '#141415'};cursor:pointer;text-align:left`}>
            <ClockCanvas style={i} on={on} />
            <span style={`display:flex;justify-content:space-between;align-items:center;font-size:12px;color:${on ? '#f0c46a' : '#c9c9c4'};padding:0 2px`}><span>{n}</span><span>{on ? '✓' : ''}</span></span>
          </button>
        ); })}
      </div>
      <span style="font-size:11px;color:#8b8b86">Vises dempet på skjermen og flytter seg litt hvert minutt for å unngå innbrenning.</span>
    </div>
  );
}

function UpdatePanel() {
  const st = settings.value, s = status.value;
  const [rel, setRel] = useState<Release | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ t: string; bad?: boolean } | null>(null);
  const cur = s?.version ?? '–';
  const check = async () => {
    setBusy(true); setMsg(null);
    try {
      const r = await fetchLatestRelease(st.updChannel === 1);
      const newer = !!r && cmpVersion(r.tag.replace(/^(skjold-)?v?/, ''), cur) > 0;
      setRel(newer ? r : null);
      if (!newer) setMsg({ t: 'Du har siste versjon (' + cur + '). Sjekket ' + new Date().toLocaleString('nb-NO', { dateStyle: 'short', timeStyle: 'short' }) + '.' });
    } catch (e) { setMsg({ t: 'Fikk ikke sjekket GitHub: ' + (e instanceof Error ? e.message : String(e)), bad: true }); }
    finally { setBusy(false); }
  };
  const tog = (on: boolean, fn: () => void) => <button onClick={fn} role="switch" aria-checked={on} style={`width:46px;height:28px;border-radius:999px;border:none;background:${on ? A : '#3a3a37'};position:relative;cursor:pointer;padding:0;flex-shrink:0`}><div style={`position:absolute;top:3px;left:${on ? 21 : 3}px;width:22px;height:22px;border-radius:50%;background:#f2f2ee`} /></button>;
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      <div style="background:#141415;border:1px solid #242426;border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
          <div style="display:flex;flex-direction:column;gap:4px"><span style="font-size:12px;color:#8b8b86">Installert</span><span style="font-size:22px;font-weight:600">Skjold {cur}</span></div>
          <a href={`https://github.com/${REPO}/releases`} target="_blank" rel="noreferrer" style="font-size:12px;white-space:nowrap">github.com/{REPO} ↗</a>
        </div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          {['Stabil', 'Beta'].map((label, i) => { const c = { bd: st.updChannel === i ? A : '#2e2e30', bg: st.updChannel === i ? '#2a2112' : '#1b1b1c', fg: st.updChannel === i ? '#f0c46a' : '#f2f2ee' }; return <button key={label} onClick={() => { setSetting('updChannel', i); setRel(undefined); }} style={`height:32px;padding:0 12px;border-radius:14px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:12px;cursor:pointer;white-space:nowrap`}>{label}</button>; })}
        </div>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px"><span style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Installer automatisk om natten</span>{pending('updAuto') && <span style="font-size:11px;color:#c9b48a">{pending('updAuto')}</span>}</span>{tog(st.updAuto, () => setSetting('updAuto', !st.updAuto))}</div>
        <button onClick={check} disabled={busy} style="height:42px;border-radius:14px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;cursor:pointer">{busy ? 'Sjekker GitHub …' : 'Se etter oppdatering'}</button>
        {msg && <div style={`padding:10px 12px;border-radius:8px;background:${msg.bad ? '#2a1412' : '#16201a'};border:1px solid ${msg.bad ? '#5a2620' : '#2a4a33'};font-size:13px;color:${msg.bad ? '#ff9a8a' : '#9be0a8'};line-height:1.45`}>{msg.t}</div>}
      </div>
      {rel && (
        <div style="background:#1c170d;border:1px solid #5a4420;border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:10px">
          <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px;flex-wrap:wrap"><span style="font-size:16px;font-weight:600">{rel.name}</span><span style="font-family:'IBM Plex Mono',monospace;font-size:11px;color:#c9b48a">{[rel.tag, rel.date, rel.size].filter(Boolean).join(' · ')}</span></div>
          <div style="display:flex;flex-direction:column;gap:4px">{rel.notes.map((t, j) => <span key={j} style="font-size:13px;color:#e8dcc4;line-height:1.45">· {t}</span>)}</div>
          <div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap"><a href={rel.url} target="_blank" rel="noreferrer" style="font-size:12px">Se på GitHub ↗</a></div>
          <span style="font-size:11px;color:#c9b48a">Installering fra appen er ikke koblet til forsterkeren ennå. Oppdater med Skjold Flasher eller fra forsterkerens meny.</span>
        </div>
      )}
      <span style="font-size:14px;font-weight:600">Backup</span>
      <div style="background:#141415;border:1px solid #242426;border-radius:14px;padding:12px 14px"><span style="font-size:12px;color:#8b8b86;line-height:1.45">Backup og gjenoppretting er ikke koblet til forsterkeren ennå.</span></div>
    </div>
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
    <div style="background:#141415;border:1px solid #242426;border-radius:14px;display:flex;flex-direction:column">
      <Line i={0} n="Appen på denne telefonen"><span style={VAL}>{cur || '–'}</span></Line>
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
    </div>
  );
}
