// «Alle innstillinger» på Skjold Touch: de samme kategoriene og radene som i web-UI (lib/settings.ts → CATS), med
// kontroller som passer berøringsskjermen. Tekstfelt bruker skjermtastaturet. Det som bare lagres på telefonen
// (innlogginger til musikktjenester) og egne sider i appen (lenker) vises ikke her.
import { useState } from 'preact/hooks';
import { signal } from '@preact/signals';
import { api, type LevelSource } from '../lib/api';
import { act, eqActiveSource, loadSettings, setEqProfile, setSetting, settings, showToast, status } from '../lib/store';
import { CATS, EQ_HZ, EQ_NAMES, fmt, LED_MODE_NAMES, LED_MODES, type Item } from '../lib/settings';
import { Keyboard, MONO, TekstFelt, useTekst } from './ui';

export const alleOpen = signal(false);
export const oppdaterTrykk = signal(0);   // «Oppdatering»-raden åpner oppdateringsarket i main.tsx

const SEG = 'display:flex;gap:4px;padding:3px;border-radius:12px;background:#0f0f10;border:1px solid #242426;align-items:center;flex-shrink:0';
const pillS = (på: boolean) => `height:34px;padding:0 12px;border-radius:9px;border:none;background:${på ? '#2a2a2c' : 'transparent'};color:${på ? '#f2f2ee' : '#8b8b86'};font-size:12px;font-weight:600;white-space:nowrap`;
const STEG = 'width:40px;height:34px;border-radius:9px;border:none;background:transparent;color:#8b8b86;font-size:16px;font-weight:600';

function Steg({ tekst, ned, opp, w = 64 }: { tekst: string; ned: () => void; opp: () => void; w?: number }) {
  return <div style={SEG}><button onClick={ned} aria-label="Mindre" style={STEG}>−</button>
    <span style={`min-width:${w}px;height:34px;padding:0 10px;border-radius:9px;background:#2a2a2c;color:#f2f2ee;font-size:12px;font-weight:600;white-space:nowrap;display:flex;align-items:center;justify-content:center;box-sizing:border-box`}>{tekst}</span>
    <button onClick={opp} aria-label="Mer" style={STEG}>+</button></div>;
}
function Valg({ list, verdi, sett }: { list: string[]; verdi: number; sett: (i: number) => void }) {
  if (list.length <= 4 && list.join('').length <= 34) return <div style={SEG}>{list.map((o, i) => <button key={o + i} onClick={() => sett(i)} style={pillS(i === verdi)}>{o}</button>)}</div>;
  return <Steg tekst={list[verdi] ?? '–'} w={130} ned={() => sett((verdi + list.length - 1) % list.length)} opp={() => sett((verdi + 1) % list.length)} />;
}
function Bryter({ på, sett, navn }: { på: boolean; sett: (v: boolean) => void; navn: string }) {
  return <button onClick={() => sett(!på)} aria-pressed={på} aria-label={navn} style="border:none;background:none;padding:6px;flex-shrink:0">
    <span style={`display:block;width:48px;height:28px;border-radius:14px;background:${på ? '#f0c46a' : '#3a3a3c'};position:relative;transition:background .2s`}><i style={`position:absolute;top:3px;left:${på ? 23 : 3}px;width:22px;height:22px;border-radius:11px;background:#fff;transition:left .2s`} /></span></button>;
}
function Bekreft({ tekst, gjør, trygg }: { tekst: string; gjør: () => void; trygg?: boolean }) {
  const [spør, setSpør] = useState(false);
  if (trygg || !spør) return <div style={SEG}><button onClick={() => (trygg ? gjør() : setSpør(true))} style={pillS(true)}>{tekst}</button></div>;
  return <div style={SEG}><button onClick={() => { setSpør(false); gjør(); }} style="height:34px;padding:0 12px;border-radius:9px;border:none;background:#7a2a20;color:#fff;font-size:12px;font-weight:600">Ja, {tekst.toLowerCase()}</button><button onClick={() => setSpør(false)} style={pillS(false)}>Avbryt</button></div>;
}

const tekstRad = signal<{ k: 'nAux1' | 'nAux2' | 'nUsb1' | 'nUsb2' | 'nameCustom'; n: string; maks: number } | null>(null);
function TekstRedigering() {
  const r = tekstRad.value!;
  const t = useTekst(r.maks, String(settings.value[r.k] ?? ''));
  return (
    <div style="position:absolute;inset:0;z-index:12;background:#0b0b0c;display:flex;flex-direction:column">
      <div style="flex:1;display:flex;flex-direction:column;justify-content:center;gap:10px;padding:0 20px">
        <span style="font-size:15px;font-weight:600">{r.n}</span>
        <div style="display:flex;align-items:center;height:48px;border-radius:12px;border:1px solid #2e2e30;background:#141415;padding:0 14px"><TekstFelt t={t} tom={r.n} size={16} /></div>
      </div>
      <Keyboard enter="Lagre" onKey={t.inn} onBack={t.slett} onFlytt={t.flytt} onEnter={() => { setSetting(r.k, t.v.trim()); tekstRad.value = null; }} />
    </div>);
}

/** Kontrollen for én rad, eller null når raden ikke hører hjemme på Touch. */
function kontroll(it: Item): preact.ComponentChildren | null {
  const st = settings.value, s = status.value;
  switch (it.kind) {
    case 'num': return <Steg tekst={fmt[it.f](st[it.k])} ned={() => setSetting(it.k, Math.max(it.mn, st[it.k] - 1))} opp={() => setSetting(it.k, Math.min(it.mx, st[it.k] + 1))} />;
    case 'opt': return it.k === 'hold' ? null : <Valg list={it.list} verdi={Math.max(0, st[it.k] as number)} sett={(i) => { setSetting(it.k, i); if (it.k === 'name' && st.nameCustom) setSetting('nameCustom', ''); }} />;
    case 'range': return <Steg tekst={st[it.k] + it.unit} ned={() => setSetting(it.k, Math.max(it.mn, st[it.k] - it.step * 5))} opp={() => setSetting(it.k, Math.min(it.mx, st[it.k] + it.step * 5))} />;
    case 'ledMode': return <Valg list={LED_MODE_NAMES} verdi={Math.max(0, LED_MODES.indexOf(st.ledMode))} sett={(i) => setSetting('ledMode', LED_MODES[i] ?? 'press')} />;
    case 'bool': return <Bryter på={!!st[it.k]} navn={it.n} sett={(v) => setSetting(it.k, v)} />;
    case 'str': return <div style={SEG}><button onClick={() => { tekstRad.value = { k: it.k, n: it.n, maks: it.k === 'nameCustom' ? 24 : 14 }; }} style={pillS(true) + ';max-width:170px;overflow:hidden;text-overflow:ellipsis'}>{String(st[it.k] || it.ph)}</button></div>;
    case 'api-bool': {
      if (it.id === 'hpOn' && !s?.hp_switch) return null;
      const m = {
        loudness: [!!s?.loudness, (v: boolean) => act(() => api.loudness(v), { loudness: v })],
        mix: [!!s?.mix, (v: boolean) => act(() => api.mix(v), { mix: v })],
        autoInput: [!!s?.auto_input, (v: boolean) => act(() => api.autoInput(v), { auto_input: v })],
        hpAutomute: [!!s?.hp_automute, (v: boolean) => act(() => api.hpAutomute(v), { hp_automute: v })],
        speakers: [s?.speakers !== false, (v: boolean) => act(() => api.speakerRelay(v), { speakers: v })],
        hpOn: [!!s?.headphones, (v: boolean) => act(() => api.headphones(v), { headphones: v })],
        voiceOn: [!!s?.voice, (v: boolean) => act(() => api.voice({ on: v }), { voice: v })]
      } as const;
      const [på, f] = m[it.id];
      return <Bryter på={på} navn={it.n} sett={(v) => void f(v)} />;
    }
    case 'api-opt':
      if (it.id === 'loudLevel') { const v = s?.loudness_level ?? 5; return <Steg tekst={String(v)} ned={() => void act(() => api.loudness(undefined, Math.max(0, v - 1)), { loudness_level: Math.max(0, v - 1) })} opp={() => void act(() => api.loudness(undefined, Math.min(10, v + 1)), { loudness_level: Math.min(10, v + 1) })} />; }
      if (it.id === 'usbPc') { const n = s?.usb_names?.length ? s.usb_names : [st.nUsb1, st.nUsb2]; return <Valg list={n.slice(0, 2)} verdi={(s?.usb_pc ?? 1) - 1} sett={(i) => void act(() => api.usbsw((i + 1) as 1 | 2), { usb_pc: i + 1 })} />; }
      { const p = Object.entries(s?.voice_profiles ?? {}); if (!p.length) return null;
        return <Valg list={p.map(([, v]) => v)} verdi={Math.max(0, p.findIndex(([k]) => k === s?.voice_profile))} sett={(i) => { const k = p[i]?.[0]; if (k) void act(() => api.voice({ profile: k })); }} />; }
    case 'info': {
      const v: Record<string, string> = { btDev: s?.bt_device || 'Ingen', lyrion: s?.lyrion ? 'Tilkoblet' : 'Ikke funnet', version: s?.version ?? '–', ip: location.host,
        id: s?.id ?? '–', board: s?.board ?? '–', headphones: s?.headphones ? 'Tilkoblet' : 'Ikke tilkoblet', btPairing: s?.bt_pairing ? 'Synlig' : 'Av',
        inputs: (s?.inputs ?? []).join(', '), netName: 'Skjold · ' + (s?.name ?? ''), output: 'RCA og 3,5 mm (PCM5122)', poToken: '–' };
      return <span style={`font-family:${MONO};font-size:12px;color:#c9c9c4;text-align:right;max-width:220px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap`}>{v[it.key] ?? '–'}</span>;
    }
    case 'act': {
      const run: Partial<Record<typeof it.id, () => void>> = {
        btPair: () => void act(() => api.btPairing(), { bt_pairing: true }),
        testVoice: () => void act(() => api.voice({ say: 'bt_pairing' })),
        forget: () => { void api.btForget().then(() => showToast('Blåtann-enhetene er glemt')).catch(() => showToast('Fikk ikke kontakt')); },
        reset: () => { void api.settingsReset().then(() => { void loadSettings(); showToast('Innstillingene er tilbakestilt'); }).catch(() => showToast('Fikk ikke kontakt')); },
        reboot: () => void act(() => api.reboot() as never)
      };
      const f = run[it.id];
      return f ? <Bekreft tekst={it.label} trygg={!!it.safe} gjør={f} /> : null;
    }
    case 'update': return <div style={SEG}><button onClick={() => { oppdaterTrykk.value++; }} style={pillS(true)}>Åpne</button></div>;
    default: return null;   // local, link, svc, test, steps, eq, clocks, levels håndteres egne steder / bare i appen
  }
}

function Nivåer() {
  const s = status.value, lv = s?.levels ?? {};
  const keys = Object.keys(lv);
  if (!keys.length) return null;
  return <div style="display:flex;flex-direction:column;gap:6px">{keys.map((k) => { const v = lv[k] ?? 100; return (
    <div key={k} style="display:flex;align-items:center;gap:10px"><span style={`width:80px;font-family:${MONO};font-size:11px;color:#8b8b86`}>{k.toUpperCase()}</span>
      <Steg tekst={v + ' %'} ned={() => void act(() => api.level(k as LevelSource, Math.max(0, v - 10)), { levels: { ...lv, [k]: Math.max(0, v - 10) } })} opp={() => void act(() => api.level(k as LevelSource, Math.min(100, v + 10)), { levels: { ...lv, [k]: Math.min(100, v + 10) } })} /></div>); })}</div>;
}
function Eq() {
  const src = eqActiveSource.value, p = settings.value.eq[src], eq = p?.eq ?? [0, 0, 0, 0, 0];
  return <div style="display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px">{eq.map((v, i) => (
    <div key={i} style="display:flex;flex-direction:column;align-items:center;gap:6px;padding:10px 4px;border-radius:12px;background:#141415;border:1px solid #242426">
      <span style="font-size:11.5px;font-weight:600">{EQ_NAMES[i]}</span><span style={`font-family:${MONO};font-size:10px;color:#8b8b86`}>{EQ_HZ[i]}</span>
      <button onClick={() => setEqProfile(src, { eq: eq.map((x, j) => (j === i ? Math.min(12, x + 1) : x)) })} style="width:44px;height:34px;border-radius:9px;border:none;background:#242426;color:#f2f2ee;font-size:16px">+</button>
      <span style={`font-family:${MONO};font-size:14px;color:${v ? '#f0c46a' : '#f2f2ee'}`}>{v > 0 ? '+' : ''}{v} dB</span>
      <button onClick={() => setEqProfile(src, { eq: eq.map((x, j) => (j === i ? Math.max(-12, x - 1) : x)) })} style="width:44px;height:34px;border-radius:9px;border:none;background:#242426;color:#f2f2ee;font-size:16px">−</button>
    </div>))}</div>;
}

export function AlleInnstillinger() {
  const [kat, setKat] = useState(CATS[0]?.id ?? '');
  const c = CATS.find((x) => x.id === kat) ?? CATS[0]!;
  const rader = c.items.map((it, i) => {
    if (it.kind === 'eq') return { i, n: it.n + ' – ' + (eqActiveSource.value.toUpperCase()), hint: 'For kilden som spiller nå', blokk: <Eq /> };
    if (it.kind === 'levels') return { i, n: it.n, hint: it.hint, blokk: <Nivåer /> };
    const k = kontroll(it);
    return k === null ? null : { i, n: it.n, hint: 'hint' in it ? it.hint : undefined, k };
  }).filter(Boolean) as { i: number; n: string; hint?: string; k?: preact.ComponentChildren; blokk?: preact.ComponentChildren }[];
  return (
    <div class="inn" style="position:absolute;inset:52px 0 0 0;z-index:6;background:#0b0b0c;display:grid;grid-template-columns:200px minmax(0,1fr)">
      <div class="rull" style="overflow-y:auto;touch-action:pan-y;border-right:1px solid #1f1f21;padding:8px 8px 14px;display:flex;flex-direction:column;gap:2px">
        <button onClick={() => { alleOpen.value = false; }} style="height:44px;border:none;background:none;color:#c9c9c4;text-align:left;padding:0 10px;font-size:14px;display:flex;align-items:center;gap:8px"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 5l-7 7 7 7" /></svg>Tilbake</button>
        {CATS.map((x) => <button key={x.id} onClick={() => setKat(x.id)} style={`min-height:44px;border:none;border-radius:10px;background:${x.id === c.id ? 'rgba(240,196,106,.14)' : 'transparent'};color:${x.id === c.id ? '#f0c46a' : '#f2f2ee'};text-align:left;padding:6px 12px;font-size:13.5px;font-weight:600`}>{x.n}</button>)}
      </div>
      <div class="rull" style="overflow-y:auto;touch-action:pan-y;padding:14px 18px 20px;display:flex;flex-direction:column;gap:2px">
        <span style="font-size:20px;font-weight:600">{c.n}</span>
        <span style="font-size:12px;color:#8b8b86;margin-bottom:8px">{c.sub}</span>
        {rader.map((r) => (
          <div key={r.i} style="display:flex;flex-direction:column;gap:8px;padding:10px 0;border-top:1px solid #1f1f21">
            <div style="display:flex;align-items:center;gap:12px;min-height:40px">
              <span style="display:flex;flex-direction:column;gap:2px;flex:1;min-width:0"><span style="font-size:14px;font-weight:600">{r.n}</span>{r.hint && <span style="font-size:11.5px;color:#8b8b86;line-height:1.35">{r.hint}</span>}</span>
              {r.k}
            </div>
            {r.blokk}
          </div>))}
        {!rader.length && <span style="font-size:13px;color:#8b8b86;padding:12px 0">Disse innstillingene gjøres i Skjold-appen eller web-UI.</span>}
      </div>
      {tekstRad.value && <TekstRedigering />}
    </div>
  );
}
