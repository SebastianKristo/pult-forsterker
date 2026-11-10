// «Rediger hjemskjerm» (som Plexamp sin Home Screen-editor): dra for å endre rekkefølge, eller bruk opp/ned-knappene,
// og slå seksjoner av og på. Lagres per Skjold-enhet (rom) og synkes til appene.
import { useRef, useState } from 'preact/hooks';
import { HOME_SECTIONS, HOME_SOURCES, homeLabel, homeSources, resetHome, resolveHome, saveHome, saveSources, type HomeItem } from '../lib/homelayout';
import { deviceName, settings } from '../lib/store';
import { Toggle } from '../components/ui';

const ALL = HOME_SECTIONS.map(([id]) => id);

export function HomeEditor() {
  const items = resolveHome(settings.value.homeLayout, ALL);
  const [drag, setDrag] = useState<number | null>(null);
  const [over, setOver] = useState<number | null>(null);
  const list = useRef<HTMLDivElement>(null);
  const move = (from: number, to: number) => {
    if (to < 0 || to >= items.length || from === to) return;
    const next = items.slice(); const [x] = next.splice(from, 1); next.splice(to, 0, x!); saveHome(next);
  };
  const toggle = (i: number, v: boolean) => { const next = items.map((x, j) => (j === i ? { ...x, visible: v } : x)); saveHome(next); };
  const rowAt = (y: number) => {
    const rows = list.current ? Array.from(list.current.querySelectorAll<HTMLElement>('[data-row]')) : [];
    for (let i = 0; i < rows.length; i++) { const r = rows[i]!.getBoundingClientRect(); if (y < r.top + r.height / 2) return i; }
    return rows.length - 1;
  };
  const down = (i: number) => (e: PointerEvent) => { (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); setDrag(i); setOver(i); e.preventDefault(); };
  const moveP = (e: PointerEvent) => { if (drag !== null) setOver(rowAt(e.clientY)); };
  const up = () => { if (drag !== null && over !== null) move(drag, over); setDrag(null); setOver(null); };
  return (
    <div style="display:flex;flex-direction:column;gap:12px">
      <div style="padding:14px 16px;border-radius:14px;border:1px solid #2e2e30;background:#141415">
        <div style="font-size:15px;font-weight:600">Rediger hjemskjerm ({deviceName.value})</div>
        <div style="font-size:12.5px;color:#8b8b86;margin-top:3px">Endringene gjelder dette rommet og vises i appen og på web.</div>
      </div>
      <div ref={list} style="display:flex;flex-direction:column" onPointerMove={moveP} onPointerUp={up} onPointerCancel={up} role="list" aria-label="Seksjoner på hjemskjermen">
        {items.map((it: HomeItem, i) => {
          const ghost = drag === i, target = drag !== null && over === i && drag !== i;
          return (
            <div key={it.id} data-row role="listitem" style={`display:grid;grid-template-columns:32px minmax(0,1fr) auto auto;gap:10px;align-items:center;padding:12px 6px;border-bottom:1px solid #242426;${ghost ? 'opacity:.45;' : ''}${target ? 'box-shadow:inset 0 2px 0 #f0c46a;' : ''}`}>
              <button aria-label={'Dra ' + homeLabel(it.id)} onPointerDown={down(i)} style="touch-action:none;cursor:grab;border:none;background:none;color:#8b8b86;padding:4px;display:flex;justify-content:center">
                <svg width="14" height="20" viewBox="0 0 14 20" fill="currentColor">{[3, 10, 17].map((y) => [3, 11].map((x) => <circle key={x + '-' + y} cx={x} cy={y} r="1.7" />))}</svg>
              </button>
              <span style={`font-size:15px;${it.visible ? '' : 'color:#6b6b67;text-decoration:line-through'}`}>{homeLabel(it.id)}</span>
              <span style="display:flex;gap:2px">
                <button aria-label={'Flytt ' + homeLabel(it.id) + ' opp'} disabled={i === 0} onClick={() => move(i, i - 1)} style={arrow}>↑</button>
                <button aria-label={'Flytt ' + homeLabel(it.id) + ' ned'} disabled={i === items.length - 1} onClick={() => move(i, i + 1)} style={arrow}>↓</button>
              </span>
              <Toggle on={it.visible} onChange={(v: boolean) => toggle(i, v)} label={'Vis ' + homeLabel(it.id)} />
            </div>
          );
        })}
      </div>
      <div style="padding:14px 16px 0;font-size:15px;font-weight:600">Kilder</div>
      <div style="padding:0 16px;font-size:12.5px;color:#8b8b86;margin-top:-8px">Hvilke kilder som vises på Hjem, og i hvilken rekkefølge. Lagres i denne nettleseren.</div>
      <SourceList />
      <button onClick={() => { resetHome(); saveSources([]); }} style="align-self:flex-start;height:36px;padding:0 14px;border-radius:999px;border:1px solid #2e2e30;background:transparent;color:#c9c9c4;font-size:13px;cursor:pointer">Tilbakestill</button>
    </div>
  );
}
/** Kildene på Hjem: opp/ned og vis/skjul (homeSources, lagres lokalt). */
function SourceList() {
  const items = resolveHome(homeSources.value, HOME_SOURCES);
  const move = (from: number, to: number) => {
    if (to < 0 || to >= items.length) return;
    const next = items.slice(); const [x] = next.splice(from, 1); next.splice(to, 0, x!); saveSources(next);
  };
  return (
    <div style="display:flex;flex-direction:column" role="list" aria-label="Kilder på hjemskjermen">
      {items.map((it, i) => (
        <div key={it.id} role="listitem" style="display:grid;grid-template-columns:minmax(0,1fr) auto auto;gap:10px;align-items:center;padding:12px 6px 12px 16px;border-bottom:1px solid #242426">
          <span style={`font-size:15px;${it.visible ? '' : 'color:#6b6b67;text-decoration:line-through'}`}>{it.id}</span>
          <span style="display:flex;gap:2px">
            <button aria-label={'Flytt ' + it.id + ' opp'} disabled={i === 0} onClick={() => move(i, i - 1)} style={arrow}>↑</button>
            <button aria-label={'Flytt ' + it.id + ' ned'} disabled={i === items.length - 1} onClick={() => move(i, i + 1)} style={arrow}>↓</button>
          </span>
          <Toggle on={it.visible} onChange={(v: boolean) => saveSources(items.map((x, j) => (j === i ? { ...x, visible: v } : x)))} label={'Vis ' + it.id} />
        </div>
      ))}
    </div>
  );
}
const arrow = 'width:32px;height:32px;border-radius:8px;border:1px solid #2e2e30;background:transparent;color:#c9c9c4;cursor:pointer;font-size:14px';
