// Skjold Touch – felles byggeklosser laget for fingre: glidebryter, skjermtastatur og ark som glir opp.
import type { ComponentChildren } from 'preact';
import { useEffect, useRef, useState } from 'preact/hooks';

export const MONO = "'IBM Plex Mono',monospace";

/** Glidebryter med 44 px treffflate. Følger fingeren direkte, og knotten vokser mens du drar.
 *  onInput kalles fortløpende, onCommit når fingeren slipper. */
export function Slider({ value, max = 100, onInput, onCommit, color = '#f0c46a', thin, disabled, label }: {
  value: number; max?: number; onInput?: (v: number) => void; onCommit?: (v: number) => void; color?: string; thin?: boolean; disabled?: boolean; label: string;
}) {
  const el = useRef<HTMLDivElement>(null);
  const [drag, setDrag] = useState<number | null>(null);
  const at = (x: number) => { const r = el.current!.getBoundingClientRect(); return Math.max(0, Math.min(1, (x - r.left - 11) / Math.max(1, r.width - 22))) * max; };
  const v = drag ?? value, pct = max > 0 ? Math.max(0, Math.min(1, v / max)) : 0;
  const h = thin ? 4 : 6, knob = drag !== null ? 26 : thin ? 14 : 22;
  return (
    <div ref={el} role="slider" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={Math.round(v)} aria-disabled={disabled}
      onPointerDown={(e) => { if (disabled) return; (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId); const n = at(e.clientX); setDrag(n); onInput?.(n); }}
      onPointerMove={(e) => { if (drag === null) return; const n = at(e.clientX); setDrag(n); onInput?.(n); }}
      onPointerUp={(e) => { if (drag === null) return; const n = at(e.clientX); setDrag(null); onCommit?.(n); }}
      onPointerCancel={() => setDrag(null)}
      style="position:relative;flex:1;min-width:0;height:44px;touch-action:none;display:flex;align-items:center;padding:0 11px;box-sizing:border-box">
      <div style={`position:relative;width:100%;height:${h}px;border-radius:${h / 2}px;background:#2a2a2c`}>
        <div style={`width:${(pct * 100).toFixed(2)}%;height:100%;border-radius:${h / 2}px;background:${color}`} />
        {!disabled && <div style={`position:absolute;top:50%;left:${(pct * 100).toFixed(2)}%;width:${knob}px;height:${knob}px;margin:${-knob / 2}px 0 0 ${-knob / 2}px;border-radius:50%;background:#f2f2ee;box-shadow:0 2px 8px rgba(0,0,0,.5);transition:width .12s ease,height .12s ease,margin .12s ease`} />}
      </div>
    </div>
  );
}

const ROWS = ['qwertyuiopå', 'asdfghjkløæ', 'zxcvbnm'];
const NUM = ['1234567890', '-/:;()&@"', ".,?!'"];
/** Skjermtastatur (norsk). Enheten har ikke noe annet tastatur. */
export function Keyboard({ onKey, onBack, onEnter, enter = 'Søk' }: { onKey: (c: string) => void; onBack: () => void; onEnter: () => void; enter?: string }) {
  const [num, setNum] = useState(false);
  const rows = num ? NUM : ROWS;
  const key = 'height:42px;border-radius:9px;border:none;background:#242426;color:#f2f2ee;font-size:17px;padding:0;flex:1;min-width:0';
  const wide = 'height:42px;border-radius:9px;border:none;background:#1a1a1c;color:#c9c9c4;font-size:12.5px;font-weight:600;padding:0';
  return (
    <div class="kb" style="flex-shrink:0;display:flex;flex-direction:column;gap:5px;padding:8px 10px 10px;background:#101011;border-top:1px solid #1f1f21">
      {rows.map((r, i) => (
        <div key={i + (num ? 'n' : 'a')} style="display:flex;gap:5px">
          {i === 2 && <button onClick={() => setNum(!num)} aria-label={num ? 'Bokstaver' : 'Tall og tegn'} style={wide + ';width:74px;flex-shrink:0'}>{num ? 'abc' : '123'}</button>}
          {[...r].map((c) => <button key={c} onClick={() => onKey(c)} style={key}>{c}</button>)}
          {i === 2 && <button onClick={onBack} aria-label="Slett" style={wide + ';width:74px;flex-shrink:0;display:flex;align-items:center;justify-content:center'}><svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M8 5h12v14H8l-6-7zM12 9.5l5 5M17 9.5l-5 5" /></svg></button>}
        </div>
      ))}
      <div style="display:flex;gap:5px">
        <button onClick={() => onKey(' ')} aria-label="Mellomrom" style={key + ';background:#1a1a1c;font-size:12.5px;color:#8b8b86'}>mellomrom</button>
        <button onClick={onEnter} style="height:42px;width:150px;flex-shrink:0;border-radius:9px;border:none;background:#f0c46a;color:#0b0b0c;font-size:13.5px;font-weight:600;padding:0">{enter}</button>
      </div>
    </div>
  );
}

/** Ark som glir opp fra bunnen over innholdet (kø, dimmer). Trykk utenfor lukker. */
export function Sheet({ title, kicker, onClose, children, height = 300 }: { title: string; kicker?: string; onClose: () => void; children: ComponentChildren; height?: number }) {
  return (
    <div style="position:absolute;inset:0;z-index:8">
      <div onClick={onClose} style="position:absolute;inset:0;background:rgba(0,0,0,.6);animation:tinn .2s ease both" />
      <div style={`position:absolute;left:10px;right:10px;bottom:10px;max-height:${height}px;border-radius:18px;border:1px solid #2e2e30;background:#18181a;box-shadow:0 -10px 40px rgba(0,0,0,.6);display:flex;flex-direction:column;animation:opp .25s cubic-bezier(.2,.8,.2,1) both;overflow:hidden`}>
        <div style="display:flex;align-items:center;gap:10px;padding:8px 8px 6px 18px;flex-shrink:0">
          <span style="display:flex;flex-direction:column;gap:1px;flex:1;min-width:0">
            {kicker && <span style={`font-family:${MONO};font-size:10px;letter-spacing:.12em;color:#8b8b86`}>{kicker}</span>}
            <span style="font-size:16px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">{title}</span>
          </span>
          <button onClick={onClose} aria-label="Lukk" style="width:44px;height:44px;border:none;background:none;color:#8b8b86;display:flex;align-items:center;justify-content:center;padding:0"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M6 6l12 12M18 6L6 18" /></svg></button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Kaller `fn` når fingeren har ligget stille i 450 ms (langt trykk). Returnerer hendelsene som settes på elementet,
 *  og `fired()` som sier om det siste trykket ble et langt trykk (så det vanlige trykket kan hoppes over). */
export function useLongPress(fn: () => void): { on: Record<string, (e: PointerEvent) => void>; fired: () => boolean } {
  const t = useRef(0), hit = useRef(false), xy = useRef<[number, number]>([0, 0]);
  const clear = () => { clearTimeout(t.current); };
  return {
    on: {
      onPointerDown: (e) => { hit.current = false; xy.current = [e.clientX, e.clientY]; clear(); t.current = window.setTimeout(() => { hit.current = true; fn(); }, 450); },
      onPointerMove: (e) => { if (Math.abs(e.clientX - xy.current[0]) + Math.abs(e.clientY - xy.current[1]) > 12) clear(); },
      onPointerUp: clear, onPointerCancel: clear, onPointerLeave: clear
    },
    fired: () => hit.current
  };
}

const WH = 62;      // høyden på én rad i hjulet
/** Rullehjul for tall (time, minutt): dra eller sveip, og det stopper på nærmeste verdi. Trykk på raden over eller under
 *  for å gå ett steg. Tre rader vises, den midterste er valgt. */
export function Wheel({ value, count, onChange, label, pad = 2 }: { value: number; count: number; onChange: (v: number) => void; label: string; pad?: number }) {
  const el = useRef<HTMLDivElement>(null), t = useRef(0), own = useRef(value);
  useEffect(() => { if (el.current && own.current !== value) { own.current = value; el.current.scrollTop = value * WH; } }, [value]);
  useEffect(() => { if (el.current) el.current.scrollTop = value * WH; }, []);
  const settle = () => {
    clearTimeout(t.current);
    t.current = window.setTimeout(() => {
      if (!el.current) return;
      const v = Math.max(0, Math.min(count - 1, Math.round(el.current.scrollTop / WH)));
      if (v !== own.current) { own.current = v; onChange(v); }
    }, 90);
  };
  const go = (v: number) => { if (el.current && v >= 0 && v < count) el.current.scrollTo({ top: v * WH, behavior: 'smooth' }); };
  return (
    <div style={`position:relative;width:118px;height:${WH * 3}px;flex-shrink:0`}>
      <div style={`position:absolute;left:0;right:0;top:${WH}px;height:${WH}px;border-radius:14px;background:#1c170d;border:1px solid #d9a441;pointer-events:none`} />
      <div ref={el} role="spinbutton" aria-label={label} aria-valuemin={0} aria-valuemax={count - 1} aria-valuenow={value} onScroll={settle}
        style={`position:relative;height:100%;overflow-y:scroll;scroll-snap-type:y mandatory;scrollbar-width:none;touch-action:pan-y;overscroll-behavior:contain;-webkit-mask-image:linear-gradient(180deg,transparent,#000 30%,#000 70%,transparent);mask-image:linear-gradient(180deg,transparent,#000 30%,#000 70%,transparent)`}>
        <div style={`height:${WH}px`} />
        {Array.from({ length: count }, (_, i) => (
          <button key={i} class="flat" onClick={() => go(i)} tabIndex={-1}
            style={`display:block;width:100%;height:${WH}px;scroll-snap-align:center;border:none;background:none;padding:0;font-family:${MONO};font-size:44px;font-weight:500;color:${i === value ? '#f2f2ee' : '#6b6b67'}`}>{String(i).padStart(pad, '0')}</button>
        ))}
        <div style={`height:${WH}px`} />
      </div>
    </div>
  );
}

