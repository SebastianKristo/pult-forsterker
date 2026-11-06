// «Grupper og surround» (PC, S1 Web v3: grpPage) og «Spill på»-arket i docken (spkSheet).
import { useRef, useState } from 'preact/hooks';
import { PRODUCT_LABEL, type Status } from '../lib/api';
import { go, setVolume } from '../lib/store';
import { PRODUCT_ICON } from '../components/ui';
import { SyncSubCard } from './advaudio';
import { activeKey, setVolAt, useRooms, type Room } from './phone';
import { applyLayout, delayMs, groupAll, groupNone, groups, inGroup, LAYOUTS, members, placeRoom, ROLE_FULL, ROLES, savePreset, setGset, setMembers, setMode, SLOT_POS, toggleMember } from '../lib/groups';

const A = '#d9a441';
const sel = (on: boolean) => ({ bd: on ? A : '#242426', bg: on ? '#1c170d' : '#141415', fg: on ? '#f0c46a' : '#f2f2ee' });
const seg = (on: boolean) => ({ bg: on ? '#2a2112' : 'transparent', fg: on ? '#f0c46a' : '#c9c9c4' });
const nf = (v: number, d: number) => v.toFixed(d).replace('.', ',');
const clamp = (v: number, a: number, b: number) => Math.min(b, Math.max(a, v));
const MONO = "font-family:'IBM Plex Mono',monospace";
const npOf = (st: Status | null) => !st ? 'Ikke tilkoblet' : !st.playing ? 'Ledig' : st.input === 'radio' ? (st.radio_now?.name || st.station || 'Radio') : (st.title || 'Spiller');
const vol = (r: Room, v: number, fin: boolean) => { if (r.active) setVolume(v, fin); else if (fin) void setVolAt(r.base, v); };
const MODES: [('sync' | 'surround'), string, string, string][] = [
  ['sync', 'Synkron', 'Samme musikk i flere rom, i takt. Hvert rom har eget volum.', 'M4 7h6v10H4zM14 7h6v10h-6zM10 12h4'],
  ['surround', 'Surround', 'Flere Skjold i samme rom deler ett lydbilde, med plass, avstand og nivå per høyttaler.', 'M12 13a2 2 0 1 0 0-4a2 2 0 1 0 0 4M4 5h3v4H4zM17 5h3v4h-3zM4 16h3v4H4zM17 16h3v4h-3z']];

function PmBtn({ on, children }: { on: () => void; children: string }) {
  return <button onClick={on} style="width:30px;height:30px;border-radius:8px;border:1px solid #2e2e30;background:#1b1b1c;cursor:pointer;font-size:15px;padding:0">{children}</button>;
}

export function GroupsPage() {
  const rooms = useRooms(), ak = activeKey(), g = groups.value, G = g.gset;
  const act = rooms[0]!;
  const memK = members(ak), mem = rooms.filter((r) => memK.includes(r.key)), has = mem.length > 1, mode = g.mode;
  const [slot, setSlot] = useState<number | null>(null);
  const [test, setTest] = useState<number | null>(null);
  const [cal, setCal] = useState(false);
  const tt = useRef(0);
  const ids = mem.map((r) => r.key).sort().join(',');
  const presets = [{ n: 'Hele huset', pick: () => groupAll(rooms.map((r) => r.key)), on: mem.length === rooms.length && rooms.length > 1 },
    ...g.presets.map((p) => ({ n: p.n, pick: () => setMembers(p.ids.includes(ak) ? p.ids : [ak, ...p.ids]), on: p.ids.slice().sort().join(',') === ids })),
    { n: 'Bare ' + act.name, pick: groupNone, on: !has }];
  const canSave = has && !g.presets.some((p) => p.ids.slice().sort().join(',') === ids) && mem.length !== rooms.length;
  const lead = G.lead && memK.includes(G.lead) ? G.lead : ak;
  const L = LAYOUTS.find((l) => l[0] === G.layout) ?? LAYOUTS[0]!;
  const byRole: Record<number, Room> = {}; mem.forEach((r) => { const ro = g.roles[r.key]; if (ro != null && ro > 0) byRole[ro] = r; });
  const maxD = Math.max(1, ...L[2].map((ro) => byRole[ro] ? (G.dist[byRole[ro]!.key] ?? 3) : 0));
  const miss = L[2].filter((ro) => !byRole[ro]).map((ro) => ROLE_FULL[ro]), idle = mem.filter((r) => { const ro = g.roles[r.key]; return !(ro != null && ro > 0 && L[2].includes(ro)); });
  const surrMsg = miss.length ? 'Mangler: ' + miss.join(', ') + '. Legg flere rom til i gruppen, eller velg et mindre oppsett.' : 'Klar. Forsinkelse og nivå er regnet ut for lytteplassen.' + (idle.length ? ' ' + idle.map((r) => r.name).join(', ') + ' er med i gruppen, men har ingen plass og er stille.' : '');
  const runTest = (ro: number) => { clearTimeout(tt.current); setTest(ro); tt.current = window.setTimeout(() => setTest(null), 1600); };
  const testAll = () => { clearTimeout(tt.current); const seq = L[2].filter((ro) => byRole[ro]); seq.forEach((ro, i) => window.setTimeout(() => setTest(ro), i * 1300)); tt.current = window.setTimeout(() => setTest(null), seq.length * 1300); };
  const card = 'display:flex;flex-direction:column;border-radius:14px;border:1px solid #242426;background:#141415';
  const segWrap = 'gap:4px;padding:3px;border-radius:10px;background:#0b0b0c';
  return (
    <div style="display:flex;flex-direction:column;gap:18px" data-testid="grp-page">
      <section style="display:flex;flex-direction:column;gap:10px">
        <div style="display:flex;justify-content:space-between;align-items:baseline;gap:10px"><span style="font-size:15px;font-weight:600;white-space:nowrap">Rom i gruppen</span><span style="font-size:12px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0;flex:1 1 0;text-align:right">{has ? mem.map((r) => r.name).join(' + ') : act.name}</span></div>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          {presets.map((p) => { const c = seg(p.on); return <button key={p.n} onClick={p.pick} style={`height:34px;padding:0 14px;border-radius:999px;border:1px solid ${p.on ? A : '#2e2e30'};background:${c.bg};color:${c.fg};font-size:12.5px;cursor:pointer;white-space:nowrap`}>{p.n}</button>; })}
          {canSave && <button onClick={() => savePreset(mem.map((r) => r.name).join(' + '), mem.map((r) => r.key))} style="height:34px;padding:0 14px;border-radius:999px;border:1px dashed #5a4420;background:transparent;color:#f0c46a;font-size:12.5px;cursor:pointer;white-space:nowrap">+ Lagre gruppen</button>}
        </div>
        <div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px">
          {rooms.map((r) => {
            const inG = inGroup(r.key, ak), c = sel(inG);
            return (
              <button key={r.key} onClick={() => toggleMember(ak, r.key)} style={`display:grid;grid-template-columns:28px minmax(0,1fr) 22px;gap:8px;align-items:center;min-height:56px;padding:8px 10px;border-radius:12px;border:1px solid ${c.bd};background:${c.bg};cursor:pointer;text-align:left`}>
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#c9c9c4" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[r.product]} /></svg>
                <span style="display:flex;flex-direction:column;gap:1px;min-width:0"><span style={`font-size:13.5px;color:${c.fg};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{r.name}</span><span style={`${MONO};font-size:9.5px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{r.active ? 'STYRER · ' : ''}{PRODUCT_LABEL[r.product]}</span></span>
                <span style={`width:22px;height:22px;border-radius:50%;border:1.5px solid ${inG ? A : '#3a3a3c'};background:${inG ? A : 'transparent'};color:#0b0b0c;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;box-sizing:border-box`}>{inG ? '✓' : ''}</span>
              </button>
            );
          })}
        </div>
      </section>
      <section style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px">
        {MODES.map(([m, n, d, ic]) => { const c = sel(has && mode === m); return (
          <button key={m} onClick={() => { if (has) setMode(m); }} style={`display:flex;flex-direction:column;align-items:flex-start;gap:8px;padding:14px;border-radius:14px;border:1px solid ${c.bd};background:${c.bg};cursor:pointer;text-align:left;opacity:${has ? 1 : 0.45}`}>
            <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke={c.fg} stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d={ic} /></svg>
            <span style={`font-size:15px;font-weight:600;color:${c.fg}`}>{n}</span>
            <span style="font-size:12px;color:#8b8b86;line-height:1.45;text-wrap:pretty">{d}</span>
          </button>); })}
      </section>
      {!has && <span style="font-size:12.5px;color:#8b8b86;line-height:1.5">Velg minst ett rom til for å spille synkront eller sette opp surround.</span>}
      {has && mode === 'sync' && (
        <section style="display:flex;flex-direction:column;gap:12px">
          <div style={card}>
            <div style="display:flex;flex-direction:column;gap:8px;padding:14px">
              <span style="font-size:14px">Volum</span>
              <div style={`display:grid;grid-template-columns:1fr 1fr;${segWrap}`}>{([['rel', 'Felles volum'], ['abs', 'Hvert rom for seg']] as const).map(([k, n]) => { const c = seg(G.vol === k); return <button key={k} onClick={() => setGset({ vol: k })} style={`height:36px;border-radius:8px;border:none;background:${c.bg};color:${c.fg};font-size:12.5px;font-weight:600;cursor:pointer;white-space:nowrap`}>{n}</button>; })}</div>
              <span style="font-size:11.5px;color:#8b8b86;line-height:1.45">{G.vol === 'rel' ? 'Hovedvolumet styrer alle rom. Forholdet mellom rommene beholdes.' : 'Hovedvolumet styrer bare rommet du står i.'}</span>
            </div>
            <div style="display:flex;flex-direction:column;gap:8px;padding:14px;border-top:1px solid #242426">
              <span style="font-size:14px">Buffer</span>
              <div style={`display:grid;grid-template-columns:repeat(3,1fr);${segWrap}`}>{[['Stabil', '500 ms'], ['Normal', '250 ms'], ['Rask', '120 ms']].map(([n, ms], i) => { const c = seg(G.buf === i); return <button key={n} onClick={() => setGset({ buf: i })} style={`height:44px;border-radius:8px;border:none;background:${c.bg};color:${c.fg};cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px`}><span style="font-size:12.5px;font-weight:600">{n}</span><span style={`${MONO};font-size:9.5px;color:#8b8b86`}>{ms}</span></button>; })}</div>
              <span style="font-size:11.5px;color:#8b8b86;line-height:1.45">{['Best på svakt Wi-Fi. Pause og skip høres etter et halvt sekund.', 'Passer de fleste hjem.', 'Raskest respons. Krever godt Wi-Fi eller kabel i alle rom.'][G.buf]}</span>
            </div>
            <div style="display:flex;flex-direction:column;gap:8px;padding:14px;border-top:1px solid #242426">
              <span style="font-size:14px">Klokke for gruppen</span>
              <div style="display:flex;gap:4px;flex-wrap:wrap">{mem.map((r) => { const c = seg(lead === r.key); return <button key={r.key} onClick={() => setGset({ lead: r.key })} style={`height:32px;padding:0 12px;border-radius:8px;border:1px solid #2e2e30;background:${c.bg};color:${c.fg};font-size:12px;cursor:pointer;white-space:nowrap`}>{r.name}</button>; })}</div>
              <span style="font-size:11.5px;color:#8b8b86;line-height:1.45">De andre rommene følger klokken til denne spilleren. Velg den med kabel eller best Wi-Fi.</span>
            </div>
          </div>
          <div style={card}>
            {mem.map((r, i) => { const tr = G.trim[r.key] ?? 0, ld = lead === r.key, v = r.st?.volume ?? 0; return (
              <div key={r.key} style={`display:flex;flex-direction:column;gap:8px;padding:12px 14px;border-top:1px solid ${i ? '#242426' : 'transparent'}`}>
                <div style="display:flex;align-items:center;gap:10px">
                  <div style={`width:8px;height:8px;border-radius:50%;background:${r.st ? '#6fcf7f' : '#e05a4a'};flex-shrink:0`} />
                  <span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0"><span style="font-size:14px">{r.name}</span><span style={`${MONO};font-size:10px;color:#8b8b86;white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{PRODUCT_LABEL[r.product]} · {ld ? 'referanse' : r.st ? 'i takt' : 'ikke tilkoblet'}</span></span>
                  <span style={`${MONO};font-size:9.5px;letter-spacing:.1em;color:#f0c46a`}>{ld ? 'KLOKKE' : ''}</span>
                </div>
                <div style="display:flex;flex-wrap:wrap;gap:10px 14px;align-items:center">
                  <input type="range" min={0} max={100} value={v} onChange={(e) => vol(r, +e.currentTarget.value, true)} style="flex:1 1 140px;min-width:0;accent-color:#d9a441" aria-label={'Volum ' + r.name} />
                  <div style="display:flex;align-items:center;gap:4px"><span style="font-size:11px;color:#8b8b86;margin-right:4px">Forsinkelse</span><PmBtn on={() => setGset({ trim: { ...G.trim, [r.key]: clamp(tr - 5, -200, 200) } })}>−</PmBtn><span style={`${MONO};font-size:11.5px;min-width:54px;text-align:center`}>{(tr > 0 ? '+' : '') + tr} ms</span><PmBtn on={() => setGset({ trim: { ...G.trim, [r.key]: clamp(tr + 5, -200, 200) } })}>+</PmBtn></div>
                </div>
              </div>); })}
          </div>
          <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
            <button onClick={() => { if (cal) return; setCal(true); window.setTimeout(() => { setCal(false); const t: Record<string, number> = {}; mem.forEach((r) => { t[r.key] = r.product === 'node' ? 10 : r.product === 'touch' ? 5 : 0; }); setGset({ trim: t }); }, 2400); }} style="height:40px;padding:0 16px;border-radius:10px;border:1px solid #d9a441;background:#1c170d;color:#f0c46a;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap">{cal ? 'Måler …' : 'Mål forsinkelse automatisk'}</button>
            <span style="flex:1 1 200px;font-size:11.5px;color:#8b8b86;line-height:1.45">{cal ? 'Spiller et klikk i hvert rom etter tur. Hold telefonen midt i rommet.' : 'Bruk dette hvis et rom ligger litt etter. Du kan også justere hvert rom med − og +.'}</span>
          </div>
        </section>
      )}
      {has && mode === 'surround' && (
        <section style="display:flex;flex-direction:column;gap:12px">
          <div style="display:flex;gap:4px;padding:3px;border-radius:10px;background:#0b0b0c;border:1px solid #242426;overflow-x:auto;scrollbar-width:none">
            {LAYOUTS.map(([k, n, slots]) => { const c = seg(G.layout === k); return <button key={k} onClick={() => applyLayout(k)} style={`flex:1 0 auto;height:44px;padding:0 12px;border-radius:8px;border:none;background:${c.bg};color:${c.fg};cursor:pointer;opacity:${mem.length >= slots.length ? 1 : 0.5};display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1px`}><span style="font-size:13px;font-weight:600;white-space:nowrap">{n}</span><span style={`${MONO};font-size:9px;color:#8b8b86;white-space:nowrap`}>{slots.length} høyttalere</span></button>; })}
          </div>
          <div style="position:relative;aspect-ratio:16/10;border-radius:16px;border:1px solid #242426;background:#0f0f10;overflow:hidden">
            <div style="position:absolute;left:30%;right:30%;top:3%;height:3px;border-radius:2px;background:#3a3a3c" />
            <span style={`position:absolute;left:0;right:0;top:5%;text-align:center;${MONO};font-size:9px;letter-spacing:.14em;color:#6b6b67`}>TV / FRONT</span>
            <div style="position:absolute;left:50%;top:58%;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;gap:6px"><div style="width:54px;height:30px;border-radius:10px 10px 6px 6px;border:1.5px solid #3a3a3c;background:#141415" /><span style={`${MONO};font-size:9px;letter-spacing:.12em;color:#6b6b67`}>LYTTEPLASS</span></div>
            {L[2].map((ro) => { const r = byRole[ro], ts = test === ro, pk = slot === ro, [x, y] = SLOT_POS[ro]!; return (
              <button key={ro} onClick={() => setSlot(pk ? null : ro)} style={`position:absolute;left:${x}%;top:${y}%;transform:translate(-50%,-50%);min-width:104px;padding:7px 10px;border-radius:10px;border:1.5px ${r ? 'solid' : 'dashed'} ${ts || pk ? '#f0c46a' : r ? '#3a3a3c' : '#5a4420'};background:${ts ? '#3a2c10' : r ? '#1b1b1c' : '#0f0f10'};box-shadow:${ts ? '0 0 0 6px rgba(240,196,106,.18)' : 'none'};cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:1px;transition:box-shadow .3s,background .3s`}><span style={`${MONO};font-size:9px;letter-spacing:.1em;color:#8b8b86;white-space:nowrap`}>{ROLES[ro]!.toUpperCase()}</span><span style={`font-size:12px;color:${r ? '#f2f2ee' : '#f0c46a'};white-space:nowrap`}>{r ? r.name : 'Tom'}</span></button>); })}
            {slot != null && L[2].includes(slot) && <>
              <div onClick={() => setSlot(null)} style="position:absolute;inset:0;background:rgba(0,0,0,.55)" />
              <div style="position:absolute;left:50%;top:50%;transform:translate(-50%,-50%);width:min(280px,88%);max-height:90%;overflow:auto;border-radius:14px;border:1px solid #2e2e30;background:#18181a;box-shadow:0 20px 50px rgba(0,0,0,.6);padding:8px;display:flex;flex-direction:column;gap:4px;box-sizing:border-box">
                <span style="font-size:13px;font-weight:600;padding:6px 8px">Hvem spiller {ROLE_FULL[slot]!.toLowerCase()}?</span>
                {[...mem.map((r) => { const ro = g.roles[r.key]; return { n: r.name, sub: ro != null && ro > 0 ? ROLE_FULL[ro]! : 'Ikke plassert', on: byRole[slot]?.key === r.key, pick: () => { placeRoom(r.key, slot); setSlot(null); } }; }),
                  { n: 'Ingen', sub: 'La plassen stå tom', on: false, pick: () => { const c = byRole[slot]; if (c) placeRoom(c.key, null); setSlot(null); } }].map((ch) => { const c = sel(ch.on); return (
                  <button key={ch.n} onClick={ch.pick} style={`display:flex;justify-content:space-between;align-items:center;gap:8px;min-height:44px;padding:0 10px;border-radius:9px;border:1px solid ${c.bd};background:${c.bg};cursor:pointer;text-align:left`}><span style={`font-size:13.5px;color:${c.fg}`}>{ch.n}</span><span style="font-size:11px;color:#8b8b86;white-space:nowrap">{ch.sub}</span></button>); })}
              </div>
            </>}
          </div>
          <div style={`padding:10px 12px;border-radius:10px;border:1px solid ${miss.length ? '#5a4420' : '#23402a'};background:${miss.length ? '#1c170d' : '#0f1a12'};font-size:12px;color:${miss.length ? '#f0c46a' : '#8fe0a0'};line-height:1.45`}>{surrMsg}</div>
          <div style={card}>
            <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;padding:12px 14px"><span style="display:flex;flex-direction:column;gap:2px;min-width:0"><span style="font-size:14px">Høyttalere</span><span style="font-size:11.5px;color:#8b8b86">Avstand fra lytteplassen. Forsinkelsen regnes ut selv.</span></span><button onClick={testAll} style="height:34px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:#1b1b1c;font-size:12px;cursor:pointer;white-space:nowrap;flex-shrink:0">Test alle</button></div>
            {L[2].filter((ro) => byRole[ro]).map((ro) => { const r = byRole[ro]!, d = G.dist[r.key] ?? 3, lv = G.lvl[r.key] ?? 0; return (
              <div key={ro} style="display:flex;flex-direction:column;gap:8px;padding:12px 14px;border-top:1px solid #242426">
                <div style="display:flex;align-items:center;gap:10px"><span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0"><span style={`${MONO};font-size:9.5px;letter-spacing:.1em;color:#f0c46a`}>{ROLE_FULL[ro]!.toUpperCase()}</span><span style="font-size:14px">{r.name} <span style="font-size:11px;color:#8b8b86">{PRODUCT_LABEL[r.product]}</span></span></span><button onClick={() => runTest(ro)} style="height:30px;padding:0 12px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#f2f2ee;font-size:12px;cursor:pointer;white-space:nowrap">{test === ro ? 'Spiller …' : 'Test'}</button></div>
                <div style="display:flex;gap:10px 14px;flex-wrap:wrap;align-items:center">
                  <div style="display:flex;align-items:center;gap:4px"><span style="font-size:11px;color:#8b8b86;width:52px">Avstand</span><PmBtn on={() => setGset({ dist: { ...G.dist, [r.key]: clamp(Math.round((d - 0.1) * 10) / 10, 0.5, 8) } })}>−</PmBtn><span style={`${MONO};font-size:11.5px;min-width:48px;text-align:center`}>{nf(d, 1)} m</span><PmBtn on={() => setGset({ dist: { ...G.dist, [r.key]: clamp(Math.round((d + 0.1) * 10) / 10, 0.5, 8) } })}>+</PmBtn></div>
                  <div style="display:flex;align-items:center;gap:4px"><span style="font-size:11px;color:#8b8b86;width:52px">Nivå</span><PmBtn on={() => setGset({ lvl: { ...G.lvl, [r.key]: clamp(lv - 0.5, -10, 10) } })}>−</PmBtn><span style={`${MONO};font-size:11.5px;min-width:56px;text-align:center`}>{(lv > 0 ? '+' : lv < 0 ? '−' : '') + nf(Math.abs(lv), 1)} dB</span><PmBtn on={() => setGset({ lvl: { ...G.lvl, [r.key]: clamp(lv + 0.5, -10, 10) } })}>+</PmBtn></div>
                  <span style={`${MONO};font-size:10.5px;color:#8b8b86`}>Forsinkelse {nf(delayMs(d, maxD), 1)} ms</span>
                </div>
              </div>); })}
          </div>
          {L[2].includes(5) && (
            <div style="display:flex;flex-direction:column;gap:10px;padding:14px;border-radius:14px;border:1px solid #242426;background:#141415">
              <span style="font-size:14px">Sub</span>
              <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center"><span style="font-size:11.5px;color:#8b8b86;width:80px">Delefrekvens</span><div style={`display:flex;${segWrap}`}>{[60, 80, 100, 120].map((v) => { const c = seg(G.xo === v); return <button key={v} onClick={() => setGset({ xo: v })} style={`height:32px;padding:0 10px;border-radius:8px;border:none;background:${c.bg};color:${c.fg};font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap`}>{v} Hz</button>; })}</div></div>
              <div style="display:flex;gap:10px;flex-wrap:wrap;align-items:center"><span style="font-size:11.5px;color:#8b8b86;width:80px">Fase</span><div style={`display:flex;${segWrap}`}>{['0°', '180°'].map((n, i) => { const c = seg(G.phase === i); return <button key={n} onClick={() => setGset({ phase: i })} style={`height:32px;padding:0 12px;border-radius:8px;border:none;background:${c.bg};color:${c.fg};font-size:12px;font-weight:600;cursor:pointer`}>{n}</button>; })}</div></div>
              <span style="font-size:11.5px;color:#8b8b86;line-height:1.45">Bass under delefrekvensen går til suben. Prøv 180° hvis bassen blir svakere når suben er på.</span>
            </div>
          )}
        </section>
      )}
      <span style="font-size:11px;color:#c9b48a;line-height:1.45">Gruppen lagres i appen. Synk-motoren under spiller i takt uten Lyrion.</span>
      <SyncSubCard />
    </div>
  );
}

/** «Spill på»-arket over volumet i docken. */
export function SpeakerButton() {
  const [open, setOpen] = useState(false);
  const rooms = useRooms(), ak = activeKey(), g = groups.value;
  const memK = members(ak), mem = rooms.filter((r) => memK.includes(r.key)), has = mem.length > 1, mode = g.mode;
  const L = has && mode === 'surround' ? (LAYOUTS.find((l) => l[0] === g.gset.layout) ?? LAYOUTS[0]!) : null;
  const miss = L ? L[2].filter((ro) => !mem.some((r) => g.roles[r.key] === ro)).length : 0;
  const hint = !has ? 'Huk av flere rom for å spille samme musikk der, eller for surround.' : mode === 'sync' ? mem.length + ' rom spiller i takt. Volumet styres per rom.' : 'Surround ' + L![1] + (miss ? ' · ' + miss + ' plass' + (miss > 1 ? 'er' : '') + ' mangler' : ' · klar');
  const label = has ? mem.map((r) => r.name).join(' + ') : rooms[0]?.name ?? '';
  const pill = 'height:30px;padding:0 12px;border-radius:999px;border:1px solid #2e2e30;background:#1b1b1c;color:#f2f2ee;font-size:12px;cursor:pointer;white-space:nowrap';
  return (
    <div style="position:relative;display:flex;min-width:0">
      <button onClick={() => setOpen(!open)} aria-label="Høyttalere" data-testid="spk-btn" style={`height:36px;display:flex;align-items:center;gap:8px;padding:0 12px;border-radius:999px;border:1px solid ${open ? A : '#2e2e30'};background:${open ? '#1c170d' : 'transparent'};color:#f2f2ee;cursor:pointer;flex-shrink:1;min-width:0;max-width:220px`}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0"><path d="M6 3h10a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2zM11 17.5a2.5 2.5 0 1 0 0-5a2.5 2.5 0 1 0 0 5M11 8.5h.01" /></svg><span style="font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{label}</span></button>
      {open && (
        <div style="position:absolute;right:0;bottom:56px;width:360px;max-width:calc(100vw - 40px);max-height:70vh;overflow:auto;border-radius:16px;background:#18181a;border:1px solid #2e2e30;box-shadow:0 20px 60px rgba(0,0,0,.6);padding:14px;display:flex;flex-direction:column;gap:12px;box-sizing:border-box">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><span style="font-size:16px;font-weight:600">Spill på</span><div style="display:flex;gap:6px"><button onClick={() => groupAll(rooms.map((r) => r.key))} style={pill}>Alle</button><button onClick={groupNone} style={pill}>Bare denne</button></div></div>
          <div style="display:flex;flex-direction:column;gap:6px">
            {rooms.map((r) => { const inG = inGroup(r.key, ak), ro = g.roles[r.key]; const sub = r.active ? 'Denne' : inG ? (has && mode === 'surround' && ro != null && ro > 0 ? ROLE_FULL[ro] : 'Spiller med') : npOf(r.st); return (
              <div key={r.key} style="display:grid;grid-template-columns:30px minmax(0,1fr) 26px;gap:10px;align-items:center;padding:8px 10px;border-radius:12px;background:#141415;border:1px solid #242426">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#c9c9c4" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><path d={PRODUCT_ICON[r.product]} /></svg>
                <div style="display:flex;flex-direction:column;gap:4px;min-width:0">
                  <button onClick={() => toggleMember(ak, r.key)} style="border:none;background:none;padding:0;cursor:pointer;text-align:left;display:flex;justify-content:space-between;gap:8px;align-items:baseline;min-width:0"><span style={`flex:1 1 auto;min-width:0;font-size:14px;color:${inG ? '#f2f2ee' : '#c9c9c4'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis`}>{r.name}</span><span style="flex-shrink:0;font-size:11px;color:#8b8b86;white-space:nowrap">{sub}</span></button>
                  <input type="range" min={0} max={100} value={r.st?.volume ?? 0} onChange={(e) => vol(r, +e.currentTarget.value, true)} style="width:100%;accent-color:#d9a441;height:20px" aria-label={'Volum ' + r.name} />
                </div>
                <button onClick={() => toggleMember(ak, r.key)} aria-label="Spill her" style={`width:26px;height:26px;border-radius:50%;border:1.5px solid ${inG ? A : '#3a3a3c'};background:${inG ? A : 'transparent'};color:#0b0b0c;cursor:pointer;padding:0;font-size:13px;font-weight:700`}>{inG ? '✓' : ''}</button>
              </div>); })}
          </div>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px;padding:3px;border-radius:10px;background:#0b0b0c;border:1px solid #242426">{([['sync', 'Synkron'], ['surround', 'Surround']] as const).map(([m, n]) => { const on = has && mode === m; return <button key={m} onClick={() => { if (has) setMode(m); }} style={`height:38px;border-radius:8px;border:none;background:${on ? '#2a2112' : 'transparent'};color:${on ? '#f0c46a' : has ? '#c9c9c4' : '#5a5a56'};font-size:13px;font-weight:600;cursor:pointer`}>{n}</button>; })}</div>
          <div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><span style={`font-size:12px;color:${has && mode === 'surround' && miss ? '#f0c46a' : '#8b8b86'};line-height:1.4;min-width:0`}>{hint}</span><button onClick={() => { setOpen(false); go('grp'); }} style="height:32px;padding:0 4px;border:none;background:transparent;color:#f0c46a;font-size:12.5px;cursor:pointer;white-space:nowrap;flex-shrink:0">Gruppeoppsett ›</button></div>
        </div>
      )}
    </div>
  );
}
