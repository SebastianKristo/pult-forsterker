// Innstillinger: kategoriliste + detaljside, generert fra CATS i lib/settings.ts.
import { Fragment } from 'preact';
import { Boundary } from '../components/boundary';
import { langPref, setLang, t, type LangPref } from '../i18n';
import { ChangelogPanel } from './programs';
import { HomeEditor } from './homeedit';
import { useEffect, useRef, useState } from 'preact/hooks';
import { DoorbellPanel, DuckPanel, RecognizeSettingsPanel, RoutinesPanel, WishlistPanel } from './features';
import { SecurityPanel } from './lyd';
import { api, type RemoteStatus, hostLabel, isNative, REPO, type LevelSource, type UpdateInfo } from '../lib/api';
import { act, applied, go, loadSettings, localOnly, mode, product, route, setSetting, settings, settingsSource, showToast, status, everyVisible } from '../lib/store';
import { computed } from '@preact/signals';
import { CAT_ALIAS, CAT_GROUPS, CAT_TILE, ICONS, LED_MODES, LED_MODE_NAMES, catsFor, fmt, type Category, type Item } from '../lib/settings';

export const cats = computed(() => catsFor(product.value, status.value?.inputs ?? []));
import { CLOCKS, drawClock } from '../lib/clocks';
import { Icon, PRODUCT_ICON, Slider, Toggle } from '../components/ui';
import { nbHw, useMinuteTick } from './pages';
import { useRooms, switchRoom } from './phone';
import { ob } from './onboard';
import { WifiPanel } from './wifi';
import { getLocal, setLocal } from '../lib/services';
import { ndConfigured, ndError, ndPing } from '../lib/navidrome';
import { ytmTest } from '../lib/ytm';
import { RadioFavorites } from './radio';
import { SkyPanel, StederPanel } from './hjem';
import { CloudPanel } from './platform';
import { favs } from '../lib/radio';
import { PRODUCT_HW, PRODUCT_LABEL } from '../lib/api';
import { Chevron } from '../components/ui';
import { BackupPanel } from './extras';
import { HealthPanel, RadioListPanel } from './extras2';
import { AiSettingsPanel, LibraryTagsPanel } from './ai';
import { AppUpdater, canSelfUpdate, fetchLatestAppRelease, installedAppVersion, isNewer, type AppRelease } from '../lib/appUpdate';

export function SettingsPage({ wide = false }: { wide?: boolean }) {
  if (status.value?.kids) return <KidsLocked />;
  const id = route.value.cat ? CAT_ALIAS[route.value.cat] ?? route.value.cat : undefined;
  const cat = cats.value.find((c) => c.id === id);
  if (!cat) return <CategoryList wide={wide} />;
  return (
    <>
      {!wide && <button onClick={() => go('settings')} style="align-self:flex-start;display:flex;align-items:center;gap:4px;border:none;background:none;color:#d9a441;font-size:14px;cursor:pointer;padding:0"><Chevron dir="left" />{t('Innstillinger')}</button>}
      <CategoryDetail cat={cat} wide={wide} />
    </>
  );
}

const A = '#d9a441';
const sel = (b: boolean) => ({ bd: b ? A : '#2e2e30', bg: b ? '#1c170d' : '#141415', fg: b ? '#f0c46a' : '#f2f2ee' });
const CARD = 'display:flex;flex-direction:column;border-radius:14px;background:#141415;border:1px solid #242426;flex-shrink:0';

export function CategoryList({ wide = false }: { wide?: boolean } = {}) {
  const rooms = useRooms();
  const p = product.value;
  return (
    <>
      {rooms.length > 1 && <div class="dsc" style="display:flex;gap:6px;overflow-x:auto;scrollbar-width:none;margin:0 -20px;padding:0 20px;flex-shrink:0">
        {rooms.map((r) => { const c = sel(r.active); return (
          <button key={r.key} onClick={() => { if (!r.active) void switchRoom(r.base, r.enhet); }} style={`display:flex;flex-direction:column;align-items:flex-start;gap:1px;padding:8px 12px;border-radius:12px;border:1px solid ${c.bd};background:${c.bg};cursor:pointer;flex-shrink:0;text-align:left`}>
            <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#c9c9c4" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[r.product]} /></svg>
            <span style={`font-size:13px;color:${c.fg};white-space:nowrap`}>{r.name}</span><span style="font-family:'IBM Plex Mono',monospace;font-size:9.5px;color:#8b8b86;white-space:nowrap">{PRODUCT_LABEL[r.product]}</span>
          </button>
        ); })}
      </div>}
      <span style="font-size:11px;color:#8b8b86">{nbHw(PRODUCT_HW[p])}{p === 'node' ? ' · ingen skjerm eller knapper' : ''}</span>
      {!wide && <div style={CARD}>
        {([['int', 'Integrasjoner', 'Lyrion, Spotify, Home Assistant, Homey og API', '#2c3a52', 'M9 3v5M15 3v5M7 8h10v4a5 5 0 0 1-10 0zM12 17v4'], ['plug', 'Plugins', 'Utvidelser for Lyrion og Skjold', '#3a2e52', 'M10 4a2 2 0 1 1 4 0v2h4v4h-2a2 2 0 1 0 0 4h2v4h-4v-2a2 2 0 1 0-4 0v2H6v-4h2a2 2 0 1 0 0-4H6V6h4z']] as const).map(([id, n, sub, tile, d], i) => (
          <button key={id} class="cat-row" onClick={() => go(id)} style={`display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;min-height:58px;padding:8px 14px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:transparent;cursor:pointer;text-align:left`}>
            <span style="display:flex;align-items:center;gap:12px;min-width:0">
              <span style={`width:32px;height:32px;border-radius:8px;background:${tile};display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#f2f2ee`}><Icon d={d} size={18} /></span>
              <span style="flex:1 1 auto;display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px">{t(n)}</span><span style="font-size:11px;color:#8b8b86">{t(sub)}</span></span>
            </span>
            <Chevron color="#8b8b86" />
          </button>
        ))}
      </div>}
      {groupCats(cats.value).map(([title, list]) => (<Fragment key={title}>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;letter-spacing:.12em;color:#8b8b86;margin:6px 0 -4px 4px">{t(title).toUpperCase()}</span>
      <div style={CARD}>
        {list.map((c, i) => (
          <button key={c.id} class="cat-row" onClick={() => go('settings', c.id)} style={`display:grid;grid-template-columns:minmax(0,1fr) auto;gap:10px;align-items:center;min-height:58px;padding:8px 14px;border:none;border-top:1px solid ${i ? '#242426' : 'transparent'};background:transparent;cursor:pointer;text-align:left`}>
            <span style="display:flex;align-items:center;gap:12px;min-width:0">
              <span style={`width:32px;height:32px;border-radius:8px;background:${CAT_TILE[c.id] ?? '#333'};display:flex;align-items:center;justify-content:center;flex-shrink:0;color:#f2f2ee`}>{ICONS[c.id] ? <Icon d={ICONS[c.id] ?? ''} size={18} /> : null}</span>
              <span style="flex:1 1 auto;display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px">{t(c.n)}</span><span style="font-size:11px;color:#8b8b86">{t(c.sub)}</span></span>
            </span>
            <Chevron color="#8b8b86" />
          </button>
        ))}
      </div>
      </Fragment>))}
      <LangPicker />
    </>
  );
}

/** Kategoriene i gruppene fra CAT_GROUPS (i den rekkefølgen), resten i siste gruppe. */
function groupCats(list: Category[]): [string, Category[]][] {
  const used = new Set<string>();
  const out: [string, Category[]][] = CAT_GROUPS.map(([title, ids]) => {
    const g = ids.map((id) => list.find((c) => c.id === id)).filter((c): c is Category => !!c);
    g.forEach((c) => used.add(c.id));
    return [title, g];
  });
  const rest = list.filter((c) => !used.has(c.id));
  if (rest.length) out[out.length - 1]![1].push(...rest);
  return out.filter(([, g]) => g.length > 0);
}

function SubHead({ n, sub }: { n: string; sub?: string }) {
  return <div style="display:flex;flex-direction:column;gap:2px;margin-top:6px"><span style="font-size:16px;font-weight:600">{t(n)}</span>{sub && <span style="font-size:12px;color:#8b8b86">{t(sub)}</span>}</div>;
}

export function CategoryDetail({ cat, wide }: { cat: Category; wide: boolean }) {
  if (cat.id === 'oppdatering') return <div style="display:flex;flex-direction:column;gap:14px"><Boundary><UpdatePanel /></Boundary>{canSelfUpdate && <Boundary><AppUpdatePanel /></Boundary>}<SubHead n="Endringslogg" /><Boundary><ChangelogPanel /></Boundary></div>;
  if (cat.id === 'sky') return (   // Steder, Skjold-hjem, fjernstyring og Skjold Cloud – samme tema, én side
    <div style="display:flex;flex-direction:column;gap:14px">
      <SubHead n="Steder" sub="Hjem, Hytta … og hvilke enheter som hører til hvor" /><Boundary><StederPanel /></Boundary>
      <SubHead n="Denne enheten" sub="Koble denne Skjold til et sted" /><Boundary><SkyPanel /></Boundary>
      <SubHead n="Fjernstyring" sub="Styr Skjold hjemmefra via Cloudflare" /><Boundary><RemotePanel /></Boundary>
      <SubHead n="Skjold Cloud" sub="Kryptert synk av favoritter, rutiner og EQ mellom hjem" /><Boundary><CloudPanel /></Boundary>
    </div>
  );
  if (cat.id === 'rutiner') return <div style="display:flex;flex-direction:column;gap:14px"><Boundary><RoutinesPanel /></Boundary><Boundary><DoorbellPanel /></Boundary><Boundary><DuckPanel /></Boundary><Boundary><SecurityPanel /></Boundary><Boundary><RecognizeSettingsPanel /></Boundary><Boundary><WishlistPanel /></Boundary><Boundary><RadioListPanel source="wishlist" /></Boundary></div>;
  if (cat.id === 'bibliotek') return <div style="display:flex;flex-direction:column;gap:14px"><Boundary><LibraryTagsPanel /></Boundary><Boundary><AiSettingsPanel /></Boundary></div>;
  const extra = cat.id === 'system' ? <><Boundary><HealthPanel /></Boundary><Boundary><BackupPanel /></Boundary></> : null;
  if (cat.id === 'hjemskjerm') return <HomeEditor />;
  const items = cat.items.filter((it) => it.kind !== 'clocks' && it.kind !== 'update');
  const hasClocks = cat.items.some((it) => it.kind === 'clocks');
  return (
    <>
      {cat.id === 'radio' ? <>
        <span style={`flex-shrink:0;font-size:${wide ? '18px' : '17px'};font-weight:600`}>Favoritter</span>
        <RadioFavorites wide={wide} />
        <span style={`flex-shrink:0;font-size:${wide ? '18px' : '17px'};font-weight:600;margin-top:6px`}>Knapper og oppstart</span>
      </> : null}
      {cat.id === 'tilkobling' && <WifiPanel wide={wide} />}
      {hasClocks && settings.value.clock && <ClockPicker />}
      <div style={CARD}>{items.map((it, i) => <Row key={i} it={it} i={i} />)}</div>
      {extra}
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
    case 'range':
      return <Line i={i} n={it.n} hint={it.hint} note={pending(it.k)} below={
        <div style="display:grid;grid-template-columns:minmax(0,1fr) 5ch;gap:10px;align-items:center">
          <Slider value={st[it.k]} min={it.mn} max={it.mx} step={it.step} label={it.n} onCommit={(v) => setSetting(it.k, Math.round(v))} />
          <span style={VAL}>{st[it.k]}{it.unit}</span></div>} />;
    case 'ledMode':
      return <Opt i={i} n={it.n} hint={it.hint} note={pending(it.k)} list={LED_MODE_NAMES} value={Math.max(0, LED_MODES.indexOf(st.ledMode))}
        onPick={(v) => setSetting('ledMode', LED_MODES[v] ?? 'press')} />;
    case 'bool':
      return <Line i={i} n={it.n} hint={it.hint} note={pending(it.k)}><Toggle on={st[it.k]} label={it.n} onChange={(v) => setSetting(it.k, v)} /></Line>;
    case 'str':
      return <Line i={i} n={it.n} hint={it.hint} note={pending(it.k)}><DraftInput value={st[it.k]} placeholder={it.ph} maxLength={it.k === 'nameCustom' ? 24 : 14} data-key={it.k} onCommit={(v) => setSetting(it.k, v.trim())} style="height:34px;width:130px;padding:0 10px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;flex-shrink:0" /></Line>;
    case 'local': {
      const v = getLocal(it.k);
      const inp = (w: string) => <DraftInput type={it.secret ? 'password' : 'text'} value={v} placeholder={it.ph} autoCapitalize="off" autoCorrect="off" spellcheck={false} data-key={it.k} onCommit={(x) => setLocal(it.k, x)} style={`height:${it.long ? 40 : 34}px;width:${w};box-sizing:border-box;padding:0 ${it.long ? 12 : 10}px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;flex-shrink:0`} />;
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
        id: s?.id ?? '–', board: ({ s1: 'Skjold S1', node: 'Skjold Node', core: 'Skjold Core', touch: 'Skjold Touch' })[product.value] + ' (' + (s?.board ?? '–') + ')', headphones: s?.headphones ? 'Tilkoblet' : 'Ikke tilkoblet', btPairing: s?.bt_pairing ? 'Synlig' : 'Av',
        inputs: (s?.inputs ?? []).join(', '), netName: 'Skjold · ' + (s?.name ?? 'romnavn'), poToken: 'Ikke tilkoblet',
        output: product.value === 'core' ? 'Pi-ens lydutgang (3,5 mm / HDMI / DAC)' : product.value === 'node' ? '3,5 mm' : product.value === 'touch' ? 'RCA og 3,5 mm (PCM5122)' : 'Høyttalerklemmer'
      };
      return <Line i={i} n={it.n} hint={it.hint}><span style={VAL}>{v[it.key]}</span></Line>;
    }
    case 'act': {
      const run: Record<typeof it.id, () => void> = {
        btPair: () => act(() => api.btPairing(), { bt_pairing: true }),
        setup: () => { ob.step.value = 1; mode.value = 'setup'; },
        findDevice: () => { mode.value = 'find'; },
        testVoice: () => act(() => api.voice({ say: 'bt_pairing' })),
        forget: () => { void api.btForget().then(() => showToast('Blåtann-enhetene er glemt')).catch(() => showToast('Fikk ikke kontakt med forsterkeren')); },
        reset: () => { void api.settingsReset().then(() => { void loadSettings(); showToast('Innstillingene er tilbakestilt'); }).catch(() => showToast('Fikk ikke kontakt med forsterkeren')); },
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
    if (id === 'ytmTest') {
      // YouTube Music er innebygd i Skjold: enheten svarer med om cookien gir et innlogget bibliotek (uten cookie virker søk)
      const c = getLocal('ytmCookie').trim();
      if (c && !c.includes('__Secure-3PAPISID')) { setR(['Mangler __Secure-3PAPISID · hent på nytt', '#ff8a7a']); return; }
      if (settingsSource.value !== 'api') { setR(['Ingen Skjold-enhet', '#ff8a7a']); return; }
      setR(['Tester …', '#c9c9c4']);
      const [t, ok] = await ytmTest();
      setR([t, ok ? '#6fcf7f' : '#ff8a7a']);
      return;
    }
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
  const st = settings.value;
  const [info, setInfo] = useState<UpdateInfo | null | undefined>(undefined);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<'' | 'running' | 'gone' | 'done' | 'failed'>('');
  const [log, setLog] = useState<string[]>([]);
  const alive = useRef(true);
  useEffect(() => () => { alive.current = false; }, []);
  const load = async (check = true) => {
    setBusy(true); setErr('');
    try { const r = await api.update(check); setInfo(r); setLog(r.log); if (r.running) void follow(); }
    catch (e) { setInfo(null); setErr(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  };
  useEffect(() => { void load(); }, []);
  /** Følg med til oppdateringen er ferdig. Tjenesten starter på nytt underveis – tål inntil 3 min uten svar. */
  const follow = async () => {
    setPhase('running');
    let lastOk = Date.now();
    while (alive.current) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        const r = await api.update(false); lastOk = Date.now(); setLog(r.log);
        if (!r.running) {
          const ok = (r.result ?? '').startsWith('ok');
          setPhase(ok ? 'done' : 'failed');
          try { setInfo(await api.update(true)); } catch { setInfo(r); }
          return;
        }
        setPhase('running');
      } catch {
        setPhase('gone');
        if (Date.now() - lastOk > 180000) { setPhase('failed'); setErr('Enheten har ikke svart på 3 minutter. Den kan fortsatt holde på – prøv igjen litt senere.'); return; }
      }
    }
  };
  const start = async () => {
    setErr(''); setLog([]);
    try { const r = await api.startUpdate(); setLog(r.log); void follow(); }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  };
  const tog = (on: boolean, fn: () => void) => <button onClick={fn} role="switch" aria-checked={on} style={`width:46px;height:28px;border-radius:999px;border:none;background:${on ? A : '#3a3a37'};position:relative;cursor:pointer;padding:0;flex-shrink:0`}><div style={`position:absolute;top:3px;left:${on ? 21 : 3}px;width:22px;height:22px;border-radius:50%;background:#f2f2ee`} /></button>;
  const cur = info?.current && info.current !== 'lokal' ? info.current : info?.current === 'lokal' ? 'Lokal utviklerversjon' : 'Ukjent versjon';
  const working = phase === 'running' || phase === 'gone';
  const mono = "font-family:'IBM Plex Mono',monospace";
  return (
    <div style="display:flex;flex-direction:column;gap:14px">
      <div style="background:#141415;border:1px solid #242426;border-radius:14px;padding:18px;display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
          <div style="display:flex;flex-direction:column;gap:4px"><span style="font-size:12px;color:#8b8b86">Installert</span><span style="font-size:22px;font-weight:600" data-testid="upd-current">{info === undefined ? '…' : cur}</span>
            {info?.latest && <span style={`font-size:11px;color:#8b8b86;${mono}`}>NYESTE: {info.latest}</span>}</div>
          <a href={`https://github.com/${REPO}/releases`} target="_blank" rel="noreferrer" style="font-size:12px;white-space:nowrap">github.com/{REPO} ↗</a>
        </div>
        {info && !working && phase !== 'done' && (info.available
          ? <div style="display:flex;flex-direction:column;gap:8px">
              <span style="font-size:13px;color:#e8dcc4">En ny versjon er klar: <b>{info.latest}</b></span>
              {info.can_update
                ? <button onClick={start} style={`height:44px;border-radius:14px;border:none;background:${A};color:#0b0b0c;font-size:14px;font-weight:600;cursor:pointer`} data-testid="upd-start">Oppdater til {info.latest}</button>
                : <span style="font-size:12px;color:#c9b48a;line-height:1.5">Denne enheten må oppdateres fra terminalen én gang før den kan oppdateres herfra:<br /><code style={`${mono};font-size:11px;color:#f2f2ee`}>git pull && sudo bash pi/update.sh</code></span>}
            </div>
          : <div style="display:flex;align-items:center;gap:8px"><span style="width:8px;height:8px;border-radius:50%;background:#6fcf7f" /><span style="font-size:13px">Skjold er oppdatert</span></div>)}
        {working && <div style="display:flex;align-items:center;gap:8px"><span class="spin" style={`width:14px;height:14px;border-radius:50%;border:2px solid #3a3a37;border-top-color:${A};animation:spin 1s linear infinite`} /><span style="font-size:13px">{phase === 'gone' ? 'Starter Skjold på nytt … venter på enheten' : 'Oppdaterer … ikke slå av enheten'}</span></div>}
        {phase === 'done' && <div style="padding:10px 12px;border-radius:8px;background:#16201a;border:1px solid #2a4a33;font-size:13px;color:#9be0a8">Oppdatert{info?.current ? ' til ' + info.current : ''}. Last siden på nytt for å få det nyeste web-grensesnittet.</div>}
        {phase === 'failed' && <div style="padding:10px 12px;border-radius:8px;background:#2a1412;border:1px solid #5a2620;font-size:13px;color:#ff9a8a">Oppdateringen feilet. Se loggen under.</div>}
        {info?.channel === 'beta' && <span style="font-size:11px;color:#f0c46a">Beta-kanal: får prerelease-versjoner</span>}
        {info?.rolled_back && <span style="font-size:12px;color:#c9b48a">Rullet tilbake til {info.rolled_back}</span>}
        {!working && info?.can_rollback && <button onClick={async () => { if (!confirm('Rull tilbake til forrige versjon?')) return; setErr(''); try { const r = await api.rollback(); setLog(r.log); void follow(); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } }} style="height:38px;border-radius:14px;border:1px solid #5a2620;background:#1b1b1c;color:#ff9a8a;font-size:13px;cursor:pointer" data-testid="upd-rollback">Rull tilbake til forrige versjon</button>}
        {!working && <button onClick={() => { setPhase(''); void load(); }} disabled={busy} style="height:42px;border-radius:14px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;cursor:pointer">{busy ? 'Sjekker …' : 'Se etter oppdateringer'}</button>}
        {(err || info?.error) && <div style="padding:10px 12px;border-radius:8px;background:#2a1412;border:1px solid #5a2620;font-size:13px;color:#ff9a8a;line-height:1.45">{err || info?.error}</div>}
        {log.length > 0 && (working || phase === 'failed' || phase === 'done') && <pre style={`margin:0;max-height:220px;overflow:auto;padding:10px 12px;border-radius:10px;background:#0f0f10;border:1px solid #242426;${mono};font-size:11px;color:#c9c9c4;white-space:pre-wrap;line-height:1.5`}>{log.slice(-30).join('\n')}</pre>}
      </div>
      <div style="background:#141415;border:1px solid #242426;border-radius:14px;padding:14px 18px;display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap"><span style="font-size:13px">Kanal</span><div style="display:flex;gap:6px">
          {['Stabil', 'Beta'].map((label, i) => { const c = { bd: st.updChannel === i ? A : '#2e2e30', bg: st.updChannel === i ? '#2a2112' : '#1b1b1c', fg: st.updChannel === i ? '#f0c46a' : '#f2f2ee' }; return <button key={label} onClick={() => setSetting('updChannel', i)} style={`height:32px;padding:0 12px;border-radius:14px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:12px;cursor:pointer;white-space:nowrap`}>{label}</button>; })}
        </div></div>
        <div style="display:flex;justify-content:space-between;align-items:center;gap:12px"><span style="display:flex;flex-direction:column;gap:2px"><span style="font-size:13px">Installer automatisk om natten</span>{pending('updAuto') && <span style="font-size:11px;color:#c9b48a">{pending('updAuto')}</span>}</span>{tog(st.updAuto, () => setSetting('updAuto', !st.updAuto))}</div>
      </div>
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


/** Tekstfelt som beholder det brukeren skriver: statusoppdateringer (SSE) skriver ikke over feltet mens det har fokus. */
function DraftInput({ value, onCommit, ...rest }: { value: string; onCommit: (v: string) => void } & Record<string, unknown>) {
  const [draft, setDraft] = useState(value ?? '');
  const focused = useRef(false);
  useEffect(() => { if (!focused.current) setDraft(value ?? ''); }, [value]);
  const commit = (v: string) => { if (v !== (value ?? '')) onCommit(v); };
  return <input {...rest} value={draft}
    onFocus={() => { focused.current = true; }}
    onInput={(e) => setDraft(e.currentTarget.value)}
    onBlur={(e) => { focused.current = false; commit(e.currentTarget.value); }}
    onKeyDown={(e) => { if (e.key === 'Enter') { commit(e.currentTarget.value); e.currentTarget.blur(); } }} />;
}


/** Fjernstyring: Cloudflare Tunnel til denne enheten (master). Token fra Cloudflare Zero Trust → Tunnels. */
/** Cloudflare-tunnel-token ut av det brukeren limer inn: selve tokenet, eller hele «cloudflared service install …»-kommandoen. */
function pickToken(raw: string): string {
  const m = raw.match(/eyJ[A-Za-z0-9_\-=.]{40,}/);
  return m ? m[0] : raw.trim();
}
const HOST_RE = /^([a-z0-9-]+\.)+[a-z]{2,}$/i;
const RSTEPS = ['Hva du får', 'Lag tunnel', 'Lim inn token', 'Offentlig adresse', 'Beskytt adressen', 'Slå på'];

function RemotePanel() {
  const [st, setSt] = useState<RemoteStatus | null>(null);
  const [host, setHost] = useState('styring.skjold-lab.com');
  const [raw, setRaw] = useState('');
  const [err, setErr] = useState('');
  const [step, setStep] = useState(-1);          // -1 = oversikt, 0–5 = veiviser
  const [guarded, setGuarded] = useState(false);
  const load = async () => { try { const r = await api.remote(); setSt(r); if (r.host) setHost(r.host); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); } };
  useEffect(() => { void load(); }, []);
  useEffect(() => { if (!st?.busy) return; const t = everyVisible(load, 1500); return () => clearInterval(t); }, [st?.busy]);
  const token = pickToken(raw);
  const tokenOk = /^eyJ[A-Za-z0-9_\-=.]{40,}$/.test(token) || (!raw && !!st?.has_token);
  const hostOk = HOST_RE.test(host.trim());
  const send = async (enable: boolean) => {
    setErr('');
    try { setSt(await api.setRemote({ enable, host: host.trim(), ...(raw ? { token } : {}) })); setRaw(''); if (enable) setStep(5); } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  };
  const on = !!st?.enabled;
  const box = 'display:flex;flex-direction:column;gap:14px;padding:18px;border-radius:16px;border:1px solid #242426;background:#121214';
  const fld = 'height:42px;padding:0 12px;border-radius:10px;border:1px solid #2e2e30;background:#1b1b1c;font-size:13px;outline:none;width:100%;box-sizing:border-box;color:#f2f2ee';
  const pbtn = 'height:42px;padding:0 18px;border-radius:10px;border:none;background:#d9a441;color:#0b0b0c;font-weight:600;cursor:pointer';
  const sbtn = 'height:42px;padding:0 16px;border-radius:10px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;cursor:pointer';
  const p = 'margin:0;font-size:13px;color:#c9c9c4;line-height:1.55';
  const li = (n: number, t: preact.ComponentChildren) => <div style="display:grid;grid-template-columns:24px minmax(0,1fr);gap:10px;align-items:start"><span class="mono" style="width:22px;height:22px;border-radius:50%;border:1px solid #5a4420;color:#f0c46a;font-size:11px;display:grid;place-items:center">{n}</span><span style={p}>{t}</span></div>;
  const code = (t: string) => <span class="mono" style="font-size:12px;background:#0b0b0c;border:1px solid #242426;border-radius:6px;padding:1px 6px;color:#f0c46a">{t}</span>;
  const status = <span style={`font-size:12px;color:${st?.active ? '#6fcf7f' : '#8b8b86'}`}>{st ? (st.busy ? 'Jobber …' : st.active ? '● Tilkoblet Cloudflare' : on ? '○ Venter på Cloudflare' : '○ Av') : '…'}</span>;

  if (step < 0) return (
    <div class="col gap16">
      <div style={box}>
        <div class="row between" style={{ alignItems: 'center', gap: '10px' }}><span style="font-size:16px;font-weight:600">{on ? 'Fjernstyring er på' : 'Styr Skjold hjemmefra'}</span>{status}</div>
        {on ? <>
          <p style={p}>Web-UI-et er tilgjengelig på <b>{st?.host}</b> via en kryptert Cloudflare-tunnel. Ingen porter er åpnet i ruteren.</p>
          <div class="row gap10" style={{ flexWrap: 'wrap' }}>
            {st?.host && <a href={'https://' + st.host} target="_blank" rel="noreferrer" style={pbtn + ';display:inline-flex;align-items:center;text-decoration:none'}>Åpne {st.host} ↗</a>}
            <button onClick={() => setStep(1)} style={sbtn}>Endre oppsett</button>
            <button disabled={st?.busy} onClick={() => void send(false)} style={sbtn}>Slå av</button>
          </div>
        </> : <>
          <p style={p}>Få det samme web-UI-et på mobilen når du er borte, for eksempel på <b>skjold-styring.dittdomene.no</b>. Det tar rundt 10 minutter og er gratis med Cloudflare. Du trenger en Cloudflare-konto og et domene som ligger hos Cloudflare.</p>
          <div class="row gap10"><button onClick={() => setStep(0)} style={pbtn}>Sett opp fjernstyring</button></div>
        </>}
        {(st?.log || err) && <pre style="margin:0;white-space:pre-wrap;font-size:11px;color:#c9c9c4;background:#0b0b0c;border-radius:10px;padding:10px;max-height:180px;overflow:auto">{err || st?.log}</pre>}
      </div>
    </div>
  );

  const canNext = step === 2 ? tokenOk : step === 3 ? hostOk : true;
  return (
    <div class="col gap16">
      <div style={box}>
        <div class="row between" style={{ alignItems: 'center' }}><span class="mono" style="font-size:10.5px;letter-spacing:.12em;color:#8b8b86">TRINN {step + 1} AV {RSTEPS.length}</span><button onClick={() => setStep(-1)} style="border:none;background:none;color:#8b8b86;font-size:12px;cursor:pointer">Avbryt</button></div>
        <div style="display:flex;gap:4px">{RSTEPS.map((_, i) => <i key={i} style={`flex:1;height:3px;border-radius:2px;background:${i <= step ? '#d9a441' : '#2e2e30'}`} />)}</div>
        <span style="font-size:18px;font-weight:600">{RSTEPS[step]}</span>

        {step === 0 && <>
          <p style={p}>Skjold kobler seg ut til Cloudflare med en tunnel. Mobilen din når Skjold via en vanlig nettadresse, uten at du åpner porter i ruteren eller trenger fast IP.</p>
          {li(1, 'Denne enheten blir hovedenheten. Herfra styrer du også de andre rommene.')}
          {li(2, 'Adressen beskyttes med Cloudflare Access, så bare e-postadressen din slipper inn.')}
          {li(3, 'Du kan slå det av her når som helst.')}
        </>}

        {step === 1 && <>
          {li(1, <>Åpne <a href="https://one.dash.cloudflare.com" target="_blank" rel="noreferrer" style="color:#f0c46a">Cloudflare Zero Trust ↗</a> og logg inn.</>)}
          {li(2, <>Gå til <b>Networks → Tunnels</b> og velg <b>Create a tunnel</b>.</>)}
          {li(3, <>Velg <b>Cloudflared</b>, gi tunnelen navnet {code('skjold')} og trykk <b>Save tunnel</b>.</>)}
          {li(4, <>Under <b>Install and run a connector</b>: kopier kommandoen som starter med {code('sudo cloudflared service install eyJ…')}. Du trenger ikke kjøre den – Skjold gjør det.</>)}
        </>}

        {step === 2 && <>
          <p style={p}>Lim inn hele kommandoen eller bare tokenet. Skjold plukker ut tokenet selv.</p>
          <textarea value={raw} onInput={(e) => setRaw(e.currentTarget.value)} placeholder={st?.has_token ? 'Et token er lagret allerede – lim inn bare for å bytte' : 'sudo cloudflared service install eyJh…'} rows={3} style={fld + ';height:auto;padding:10px 12px;font-family:var(--mono);resize:vertical'} autoCapitalize="off" spellcheck={false} />
          <span style={`font-size:12px;color:${raw ? (tokenOk ? '#6fcf7f' : '#ff8a7a') : '#8b8b86'}`}>{raw ? (tokenOk ? `✓ Token funnet (${token.length} tegn)` : 'Fant ikke et token. Det starter med «eyJ» og er langt.') : st?.has_token ? 'Lagret token brukes.' : 'Venter på token.'}</span>
        </>}

        {step === 3 && <>
          {li(1, <>I Cloudflare, gå videre til fanen <b>Public Hostname</b> for tunnelen.</>)}
          {li(2, <>Velg et underdomene, for eksempel {code('skjold-styring')}, og domenet ditt.</>)}
          {li(3, <>Sett <b>Service</b> til {code('HTTP')} og {code('localhost:8765')}, og lagre.</>)}
          <label style="display:flex;flex-direction:column;gap:6px;font-size:12px;color:#8b8b86">Adressen du valgte<input value={host} onInput={(e) => setHost(e.currentTarget.value)} style={fld} autoCapitalize="off" spellcheck={false} placeholder="skjold-styring.dittdomene.no" /></label>
          {!hostOk && host && <span style="font-size:12px;color:#ff8a7a">Skriv bare vertsnavnet, uten https:// og uten skråstrek.</span>}
        </>}

        {step === 4 && <>
          <p style={p}>Uten dette kan alle som finner adressen styre Skjold. Det tar to minutter.</p>
          {li(1, <>I Zero Trust: <b>Access → Applications → Add an application → Self-hosted</b>.</>)}
          {li(2, <>Bruk samme adresse: {code(host.trim() || 'skjold-styring.dittdomene.no')}.</>)}
          {li(3, <>Lag en policy <b>Allow</b> med <b>Emails</b> = e-postadressen din. Du får en engangskode på e-post når du logger inn.</>)}
          <label style="display:flex;gap:10px;align-items:center;font-size:13px;color:#f2f2ee;cursor:pointer"><input type="checkbox" checked={guarded} onChange={(e) => setGuarded(e.currentTarget.checked)} style="width:18px;height:18px;accent-color:#d9a441" />Jeg har beskyttet adressen med Cloudflare Access</label>
          {!guarded && <span style="font-size:12px;color:#c9b48a">Du kan gå videre uten, men vi anbefaler det sterkt.</span>}
        </>}

        {step === 5 && <>
          {!st?.enabled || st?.busy ? <>
            <p style={p}>Skjold installerer Cloudflare-tunnelen og kobler til. Det kan ta et minutt.</p>
            <div class="row gap10"><button disabled={st?.busy || !tokenOk || !hostOk} onClick={() => void send(true)} style={pbtn}>{st?.busy ? 'Kobler til …' : 'Slå på fjernstyring'}</button></div>
          </> : st.active ? <>
            <p style={p}><b style="color:#6fcf7f">Ferdig!</b> Åpne adressen på mobilen og legg den til på hjemskjermen.</p>
            <div class="row gap10" style={{ flexWrap: 'wrap' }}><a href={'https://' + st.host} target="_blank" rel="noreferrer" style={pbtn + ';display:inline-flex;align-items:center;text-decoration:none'}>Åpne {st.host} ↗</a><button onClick={() => setStep(-1)} style={sbtn}>Lukk</button></div>
          </> : <>
            <p style={p}>Tunnelen er installert, men Cloudflare har ikke svart ennå. Sjekk at tokenet er fra riktig tunnel og at Public Hostname peker til {code('localhost:8765')}.</p>
            <div class="row gap10"><button onClick={() => void load()} style={sbtn}>Sjekk igjen</button><button onClick={() => setStep(2)} style={sbtn}>Bytt token</button></div>
          </>}
          {(st?.log || err) && <pre style="margin:0;white-space:pre-wrap;font-size:11px;color:#c9c9c4;background:#0b0b0c;border-radius:10px;padding:10px;max-height:180px;overflow:auto">{err || st?.log}</pre>}
        </>}

        {step < 5 && <div class="row between" style={{ marginTop: '4px' }}>
          <button onClick={() => setStep(step - 1)} style={sbtn}>{step === 0 ? 'Tilbake' : '‹ Forrige'}</button>
          <button disabled={!canNext} onClick={() => setStep(step + 1)} style={pbtn + (canNext ? '' : ';opacity:.45;cursor:default')}>Neste ›</button>
        </div>}
      </div>
    </div>
  );
}

/** Barnerom-modus: innstillingene er skjult til modusen slås av under Plugins (med PIN). */
function KidsLocked() {
  return (
    <div style="display:flex;flex-direction:column;gap:12px;padding:20px;border-radius:16px;border:1px solid #3a3220;background:#121214;max-width:520px">
      <span style="font-size:17px;font-weight:600">Barnerom-modus er på</span>
      <span style="font-size:13px;color:#a9a9a3;line-height:1.5">Innstillingene er skjult. Slå av barnerom-modus under Plugins for å endre dem. Har du satt en PIN-kode, trengs den.</span>
      <div><button class="btn" onClick={() => go('plug')}>Gå til Plugins</button></div>
    </div>
  );
}


/** Språkvalg (lagres i nettleseren): automatisk, norsk eller engelsk. */
function LangPicker() {
  const opts: [LangPref, string][] = [['auto', 'Standard (norsk)'], ['nb', 'Norsk'], ['en', 'Engelsk']];
  return (
    <div style={CARD + ';padding:12px 14px;gap:8px'}>
      <span style="font-size:14px">{t('Språk')}</span>
      <div style="display:flex;gap:6px;flex-wrap:wrap">
        {opts.map(([v, n]) => { const c = sel(langPref.value === v); return (
          <button key={v} onClick={() => setLang(v)} aria-pressed={langPref.value === v} style={`height:34px;padding:0 12px;border-radius:9px;border:1px solid ${c.bd};background:${c.bg};color:${c.fg};font-size:13px;cursor:pointer`}>{t(n)}</button>
        ); })}
      </div>
    </div>
  );
}
